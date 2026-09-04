"""Permission-gated Tor fetch. Not a marketplace and not a downloader for arbitrary binaries."""

from __future__ import annotations

import shutil
import subprocess
from urllib.parse import urlparse

from universal.paths import user_data_dir
from universal.permission_gate import ask_permission
from universal.rules import is_enforced

MAX_CHARS = 4000
MAX_BYTES = 2_000_000


def tor_available() -> bool:
    return bool(shutil.which("torsocks") and shutil.which("curl"))


def _safe_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http and https URLs are allowed")
    if not parsed.netloc:
        raise ValueError("URL host is required")
    return parsed.geturl()


def fetch_via_tor(*, url: str, timeout: int = 30, action: str = "fetch") -> dict[str, object]:
    try:
        target = _safe_url(url)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    if is_enforced("no_dark_web_without_permission"):
        decision = ask_permission(
            action="Allow a Tor fetch from the signed core",
            details=f"Action: {action}\nURL: {target}",
            agent="tor_browser",
            rule_id="no_dark_web_without_permission",
        )
        if not decision.granted:
            return {"ok": False, "blocked": True, "error": decision.reason or "Tor fetch blocked"}
    if not tor_available():
        return {
            "ok": False,
            "error": "torsocks and curl are not installed. Install Tor from https://www.torproject.org/download/",
        }
    timeout = max(5, min(int(timeout or 30), 60))
    try:
        result = subprocess.run(
            ["torsocks", "curl", "-sS", "-L", "--max-time", str(timeout), "--max-filesize", str(MAX_BYTES), target],
            capture_output=True,
            text=True,
            timeout=timeout + 5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": f"Tor fetch failed: {exc}"}
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "torsocks curl failed").strip()
        return {"ok": False, "error": err[:400]}
    body = (result.stdout or "")[:MAX_CHARS]
    return {"ok": True, "url": target, "text": body, "truncated": len(result.stdout or "") > MAX_CHARS}


def save_via_tor(*, url: str, timeout: int = 30) -> dict[str, object]:
    fetched = fetch_via_tor(url=url, timeout=timeout, action="save")
    if not fetched.get("ok"):
        return fetched
    dest_dir = user_data_dir() / "tor_downloads"
    dest_dir.mkdir(parents=True, exist_ok=True)
    host = urlparse(str(fetched["url"])).netloc.replace(":", "_")
    dest = dest_dir / f"{host}.txt"
    dest.write_text(str(fetched.get("text") or ""), encoding="utf-8")
    return {"ok": True, "url": fetched["url"], "path": str(dest), "note": "Saved text only, inside the app data dir."}
