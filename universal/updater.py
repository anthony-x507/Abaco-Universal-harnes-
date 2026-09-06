"""Check GitHub Releases for a newer Abaco-Coding-Harness.dmg. Apply only on a packaged Mac app."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx

from universal.exceptions import ConfigError
from universal.release import current_version, load_release

ALLOWED_HOSTS = {
    "github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
}
ENV_ALLOW_INSTALL = "UNIVERSAL_UPDATE_ALLOW_INSTALL"
APP_BUNDLE_NAME = "Abaco Coding Harness.app"
PREVIOUS_BUNDLE_NAME = "Abaco Harness.app"
LEGACY_BUNDLE_NAME = "Universal.app"
DMG_ASSET_NAME = "Abaco-Coding-Harness.dmg"
PREFERRED_DMG_NAMES = (
    DMG_ASSET_NAME,
    "Abaco-Harness.dmg",
    "Universal.dmg",
)
APP_INSTALL = Path("/Applications") / APP_BUNDLE_NAME
PREVIOUS_APP_INSTALL = Path("/Applications") / PREVIOUS_BUNDLE_NAME
LEGACY_APP_INSTALL = Path("/Applications") / LEGACY_BUNDLE_NAME
LEGACY_APP_INSTALLS = (PREVIOUS_APP_INSTALL, LEGACY_APP_INSTALL)
# 1.2.15 / 1.2.16 hard-code /Volumes/Universal/Universal.app. Ship that volume
# name on the transitional DMG so those binaries can apply.
VOLUME_NAMES = ("Universal", "Abaco Coding Harness", "Abaco Harness")
BUNDLE_CANDIDATES = (APP_BUNDLE_NAME, PREVIOUS_BUNDLE_NAME, LEGACY_BUNDLE_NAME)
INSTALL_WARNING = "Abaco Coding Harness should be installed in /Applications/ for auto-updates"
CACHE_GLOBS = (
    "Library/Caches/com.universal*",
    "Library/Caches/Universal",
    "Library/Caches/Abaco Coding Harness",
    "Library/Caches/Abaco Harness",
    "Library/Caches/pywebview",
    "Library/WebKit/com.universal*",
    "Library/WebKit/Universal",
    "Library/WebKit/Abaco Coding Harness",
    "Library/WebKit/Abaco Harness",
    "Library/HTTPStorages/com.universal*",
    "Library/HTTPStorages/Universal",
    "Library/HTTPStorages/Abaco Coding Harness",
    "Library/HTTPStorages/Abaco Harness",
    "Library/Saved Application State/*Universal*",
    "Library/Saved Application State/*Abaco*",
    "Library/Application Support/pywebview",
)


def clear_macos_webview_caches(home: Path | None = None) -> list[str]:
    """Drop leftover WKWebView / HTTP caches so an update cannot show the old Chat face."""
    root = home or Path.home()
    removed: list[str] = []
    for pattern in CACHE_GLOBS:
        for path in root.glob(pattern):
            try:
                if path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
                elif path.exists():
                    path.unlink()
                removed.append(str(path))
            except OSError:
                continue
    return removed


def running_from_applications() -> bool:
    if not getattr(sys, "frozen", False):
        return True
    exe = sys.executable or ""
    return any(
        exe.startswith(str(path))
        for path in (APP_INSTALL, PREVIOUS_APP_INSTALL, LEGACY_APP_INSTALL)
    )


def install_warning() -> str:
    if getattr(sys, "frozen", False) and not running_from_applications():
        return INSTALL_WARNING
    return ""


def parse_version(raw: str) -> tuple[int, ...]:
    text = raw.strip().lstrip("vV")
    parts: list[int] = []
    for chunk in text.split("."):
        digits = ""
        for char in chunk:
            if char.isdigit():
                digits += char
            else:
                break
        parts.append(int(digits or 0))
    return tuple(parts) if parts else (0,)


def is_newer(latest: str, current: str) -> bool:
    return parse_version(latest) > parse_version(current)


def can_apply_install() -> bool:
    if os.environ.get(ENV_ALLOW_INSTALL, "").strip() == "1":
        return True
    return bool(getattr(sys, "frozen", False) and sys.platform == "darwin")


def pick_dmg_asset(assets: object) -> str | None:
    """Prefer the canonical DMG name, then leftover names, then any .dmg."""
    rows: list[dict[str, object]] = [row for row in (assets or []) if isinstance(row, dict)]
    by_name = {str(row.get("name") or ""): row for row in rows}
    chosen = None
    for preferred in PREFERRED_DMG_NAMES:
        if preferred in by_name:
            chosen = by_name[preferred]
            break
    if chosen is None:
        for row in rows:
            if str(row.get("name") or "").endswith(".dmg"):
                chosen = row
                break
    if chosen is None:
        return None
    return str(chosen.get("browser_download_url") or "") or None


@dataclass(frozen=True, slots=True)
class UpdateStatus:
    current: str
    latest: str | None
    available: bool
    url: str | None
    release_notes: str
    repo: str
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "current": self.current,
            "latest": self.latest,
            "available": self.available,
            "url": self.url,
            "release_notes": self.release_notes,
            "repo": self.repo,
            "reason": self.reason,
            "can_apply": can_apply_install(),
            "in_applications": running_from_applications(),
            "install_warning": install_warning(),
        }


class Updater:
    """Talks to the GitHub Releases API. Replaces Abaco Coding Harness.app only.

    User-data (history, registry, ``llm.json``) stays in Application Support
    under the existing ``Universal`` folder so a rename does not split the registry.
    """

    def __init__(self, *, repo: str | None = None, client: httpx.Client | None = None) -> None:
        release = load_release()
        self.repo = (repo or release.get("repo") or "").strip()
        self.current = current_version()
        self._client = client
        self._owns_client = client is None

    def _http(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=15.0)
            self._owns_client = True
        return self._client

    def close(self) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None

    def check(self) -> UpdateStatus:
        if not self.repo or "/" not in self.repo:
            return UpdateStatus(
                current=self.current,
                latest=None,
                available=False,
                url=None,
                release_notes="",
                repo=self.repo,
                reason="version.json has no GitHub repo baked in.",
            )
        url = f"https://api.github.com/repos/{self.repo}/releases/latest"
        try:
            response = self._http().get(
                url,
                headers={"Accept": "application/vnd.github+json", "User-Agent": "Abaco-Coding-Harness-updater"},
            )
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            return UpdateStatus(
                current=self.current,
                latest=None,
                available=False,
                url=None,
                release_notes="",
                repo=self.repo,
                reason=f"Could not reach GitHub Releases: {exc}",
            )
        if not isinstance(data, dict):
            return UpdateStatus(
                current=self.current,
                latest=None,
                available=False,
                url=None,
                release_notes="",
                repo=self.repo,
                reason="GitHub returned a non-object payload.",
            )
        latest = str(data.get("tag_name") or data.get("name") or "").lstrip("v")
        notes = str(data.get("body") or "")
        download = pick_dmg_asset(data.get("assets"))
        available = bool(latest and download and is_newer(latest, self.current))
        reason = ""
        if latest and not download:
            reason = "Latest release has no .dmg asset."
        elif latest and not is_newer(latest, self.current):
            reason = "Already up to date."
        return UpdateStatus(
            current=self.current,
            latest=latest or None,
            available=available,
            url=download if available else None,
            release_notes=notes,
            repo=self.repo,
            reason=reason,
        )

    def apply(self, *, dest_app: Path | None = None) -> str:
        """Download the latest .dmg and replace the app. Packaged macOS only."""
        if not can_apply_install():
            raise ConfigError(
                "Install is only allowed from the packaged Mac app "
                "(or UNIVERSAL_UPDATE_ALLOW_INSTALL=1 in tests)."
            )
        status = self.check()
        if not status.available or not status.url:
            raise ConfigError(status.reason or "No update available.")
        self._assert_safe_url(status.url)
        dest = dest_app or APP_INSTALL
        dmg_path = Path(os.environ.get("TMPDIR", "/tmp")) / "Abaco-Coding-Harness_update.dmg"
        self._download(status.url, dmg_path)
        self._install_dmg(dmg_path, dest)
        self._clear_caches_after_install()
        self._schedule_relaunch(dest)
        return f"Installed {status.latest} to {dest}. The app is relaunching."

    def _clear_caches_after_install(self) -> None:
        """Packaged Mac installs only. Tests call ``clear_macos_webview_caches`` with a fake home."""
        if sys.platform != "darwin" or not getattr(sys, "frozen", False):
            return
        clear_macos_webview_caches()

    def _schedule_relaunch(self, dest: Path) -> None:
        """Open the new app, then exit this process so the user does not quit by hand."""

        def _relaunch() -> None:
            try:
                if sys.platform == "darwin":
                    subprocess.Popen(["open", "-n", str(dest)])
            finally:
                if getattr(sys, "frozen", False) or os.environ.get(ENV_ALLOW_INSTALL, "").strip() == "1":
                    os._exit(0)

        threading.Timer(1.5, _relaunch).start()

    def check_for_updates(self) -> UpdateStatus:
        return self.check()

    @staticmethod
    def _assert_safe_url(url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme != "https" or (parsed.hostname or "") not in ALLOWED_HOSTS:
            raise ConfigError("Update URL is not a GitHub https asset.")

    def _download(self, url: str, dest: Path) -> None:
        with self._http().stream("GET", url, follow_redirects=True) as response:
            response.raise_for_status()
            dest.write_bytes(response.read())

    @staticmethod
    def _mounted_app(volumes_root: Path | None = None) -> tuple[Path | None, Path | None]:
        """Find Abaco Coding Harness.app (or leftover names) on a mounted DMG."""
        root = volumes_root if volumes_root is not None else Path("/Volumes")
        for volume in VOLUME_NAMES:
            mount = root / volume
            if not mount.is_dir():
                continue
            for bundle in BUNDLE_CANDIDATES:
                src = mount / bundle
                if src.is_dir():
                    return mount, src
        return None, None

    def _install_dmg(self, dmg_path: Path, dest_app: Path) -> None:
        subprocess.run(["hdiutil", "attach", str(dmg_path), "-nobrowse"], check=True)
        mount, src = self._mounted_app()
        if mount is None or src is None:
            for volume in VOLUME_NAMES:
                subprocess.run(["hdiutil", "detach", f"/Volumes/{volume}", "-quiet"], check=False)
            raise ConfigError("Mounted image has no Abaco Coding Harness.app")
        if dest_app.exists():
            subprocess.run(["rm", "-rf", str(dest_app)], check=True)
        subprocess.run(["cp", "-R", str(src), str(dest_app)], check=True)
        if dest_app == APP_INSTALL:
            for leftover in LEGACY_APP_INSTALLS:
                if leftover.exists() and leftover != dest_app:
                    subprocess.run(["rm", "-rf", str(leftover)], check=False)
        subprocess.run(["hdiutil", "detach", str(mount), "-quiet"], check=True)
        try:
            dmg_path.unlink()
        except OSError:
            pass
