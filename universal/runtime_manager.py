"""Install and supervise the user-writable Node runtime.

The signed app only copies the seed once. After that, Python is the only
writer: evolve goes through the permission gate, then a file write, then a
reload ping. Node never writes plugin files on its own.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx

from universal.exceptions import ConfigError
from universal.paths import get_runtime_dir
from universal.permission_gate import ask_permission

ENV_RUNTIME_PORT = "UNIVERSAL_RUNTIME_PORT"
ENV_NODE = "UNIVERSAL_NODE"
ENV_DISABLE = "UNIVERSAL_RUNTIME"
DEFAULT_PORT = 43126
ALLOWED_PLUGIN_SUFFIX = ".js"


def seed_runtime_dir() -> Path:
    """Read-only seed shipped in the repo or the frozen bundle."""
    if getattr(sys, "frozen", False):
        meipass = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        frozen = meipass / "agent_runtime"
        if frozen.is_dir():
            return frozen
    packaged = Path(__file__).resolve().parent / "agent_runtime_seed"
    if packaged.is_dir() and (packaged / "runtime.js").is_file():
        return packaged
    here = Path(__file__).resolve().parent.parent / "agent_runtime"
    if here.is_dir() and (here / "runtime.js").is_file():
        return here
    raise ConfigError("agent_runtime seed is missing from the install")


def resolve_node_bin() -> Path | None:
    env = os.environ.get(ENV_NODE, "").strip()
    if env and Path(env).is_file():
        return Path(env)
    if getattr(sys, "frozen", False):
        meipass = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        for candidate in (
            meipass / "node" / "bin" / "node",
            meipass / "node" / "node",
        ):
            if candidate.is_file():
                return candidate
    found = shutil.which("node")
    return Path(found) if found else None


def _safe_plugin_path(runtime_dir: Path, target: str) -> Path:
    relative = target.replace("\\", "/").lstrip("/")
    if not relative.startswith("plugins/") or relative.count("..") or relative.endswith("/"):
        raise ConfigError("Only plugins/*.js inside the user runtime can evolve")
    name = Path(relative).name
    if not name.endswith(ALLOWED_PLUGIN_SUFFIX) or name.startswith("."):
        raise ConfigError("Evolution is limited to .js plugin files")
    dest = (runtime_dir / "plugins" / name).resolve()
    try:
        dest.relative_to((runtime_dir / "plugins").resolve())
    except ValueError as exc:
        raise ConfigError("Path escapes the user runtime") from exc
    return dest


class RuntimeManager:
    def __init__(self, *, runtime_dir: Path | None = None, port: int | None = None) -> None:
        self.runtime_dir = runtime_dir or get_runtime_dir()
        self.port = int(port or os.environ.get(ENV_RUNTIME_PORT, DEFAULT_PORT))
        self.process = None
        self.core_url = "http://127.0.0.1:43124"
        self._lock = threading.Lock()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def ensure_installed(self) -> Path:
        seed = seed_runtime_dir()
        dest = self.runtime_dir
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "plugins").mkdir(parents=True, exist_ok=True)
        for name in ("package.json", "runtime.js"):
            target = dest / name
            if not target.exists():
                target.write_text((seed / name).read_text(encoding="utf-8"), encoding="utf-8")
        seed_plugins = seed / "plugins"
        if seed_plugins.is_dir():
            for src in seed_plugins.glob("*.js"):
                target = dest / "plugins" / src.name
                if not target.exists():
                    target.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        self._npm_install()
        return dest

    def _npm_install(self) -> None:
        if (self.runtime_dir / "node_modules" / "express").exists():
            return
        npm = shutil.which("npm")
        if npm is None:
            return
        subprocess.run(
            [npm, "install", "--omit=dev", "--no-fund", "--no-audit"],
            cwd=self.runtime_dir,
            check=False,
            capture_output=True,
            text=True,
            timeout=180,
        )

    def start(self, *, core_url: str) -> None:
        if os.environ.get(ENV_DISABLE, "1").strip() in {"0", "off", "false"}:
            return
        with self._lock:
            if self.process is not None and self.process.poll() is None:
                self.core_url = core_url
                return
            node = resolve_node_bin()
            if node is None:
                return
            self.ensure_installed()
            env = os.environ.copy()
            env["UNIVERSAL_CORE_URL"] = core_url.rstrip("/")
            env["UNIVERSAL_RUNTIME_PORT"] = str(self.port)
            env["UNIVERSAL_RUNTIME_DIR"] = str(self.runtime_dir)
            self.core_url = core_url.rstrip("/")
            self.process = subprocess.Popen(
                [str(node), "runtime.js"],
                cwd=self.runtime_dir,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            self._wait_ready(timeout=8.0)

    def _wait_ready(self, *, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.healthy():
                return
            if self.process is not None and self.process.poll() is not None:
                return
            time.sleep(0.1)

    def stop(self) -> None:
        with self._lock:
            proc = self.process
            self.process = None
        if proc is None:
            return
        try:
            if proc.poll() is None:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                proc.wait(timeout=4)
        except (ProcessLookupError, PermissionError, OSError, ChildProcessError):
            pass

    def healthy(self) -> bool:
        if self.process is None or self.process.poll() is not None:
            return False
        try:
            response = httpx.get(f"{self.url}/health", timeout=0.4)
            return response.status_code == 200 and response.json().get("status") == "ok"
        except Exception:
            return False

    def think(self, *, prompt: str, history: list[dict[str, object]], agent_id: str) -> str:
        if not self.healthy():
            raise ConfigError("Node runtime is not running")
        response = httpx.post(
            f"{self.url}/think",
            json={"prompt": prompt, "history": history, "agent_id": agent_id},
            timeout=90.0,
        )
        data = response.json()
        if response.status_code >= 400 or data.get("status") == "error":
            raise ConfigError(str(data.get("error") or f"runtime think failed ({response.status_code})"))
        return str(data.get("response") or "")

    def reload(self) -> None:
        if not self.healthy():
            return
        try:
            httpx.post(f"{self.url}/reload", timeout=2.0)
        except Exception:
            return

    def apply_evolution(self, *, target_file: str, new_code: str, reason: str, agent: str = "evolution") -> dict[str, object]:
        dest = _safe_plugin_path(self.runtime_dir, target_file)
        decision = ask_permission(
            action=f"Write {dest.name} in the evolvable runtime",
            details=f"{reason}\n\n{new_code[:500]}",
            agent=agent,
            rule_id="ask_before_self_modify",
        )
        if not decision.granted:
            return {"ok": False, "granted": False, "reason": decision.reason, "file": dest.name}
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(new_code, encoding="utf-8")
        self.reload()
        return {"ok": True, "granted": True, "file": str(Path("plugins") / dest.name), "reason": decision.reason}

    def list_plugins(self) -> list[dict[str, str]]:
        if self.healthy():
            try:
                data = httpx.get(f"{self.url}/list_plugins", timeout=1.5).json()
                rows = data.get("plugins")
                if isinstance(rows, list):
                    return [row for row in rows if isinstance(row, dict)]
            except Exception:
                pass
        return self._plugins_from_disk()

    def _plugins_from_disk(self) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        plugins = self.runtime_dir / "plugins"
        if plugins.is_dir():
            for path in sorted(plugins.glob("*.js")):
                rows.append({"name": path.stem, "version": "1.0.0", "description": path.name})
        return rows

    def status(self) -> dict[str, object]:
        """Process + disk only. Never HTTP-probe — /health must stay cheap."""
        node = resolve_node_bin()
        alive = self.process is not None and self.process.poll() is None
        return {
            "ok": alive,
            "url": self.url,
            "dir": str(self.runtime_dir),
            "node": str(node) if node else "",
            "plugins": self._plugins_from_disk(),
        }


_MANAGER: RuntimeManager | None = None


def default_manager() -> RuntimeManager:
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = RuntimeManager()
    return _MANAGER


def reset_manager(manager: RuntimeManager | None = None) -> RuntimeManager:
    global _MANAGER
    if _MANAGER is not None:
        _MANAGER.stop()
    _MANAGER = manager if manager is not None else RuntimeManager()
    return _MANAGER
