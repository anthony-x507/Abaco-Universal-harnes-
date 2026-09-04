"""Native desktop window around the existing factory + SPA.

One ``Universal`` root, same ``create_app`` as ``universal serve``.
The window loads the factory URL (SPA + ``/v1`` on one localhost port).
"""

from __future__ import annotations

import argparse
import socket
import threading
import time
from collections.abc import Sequence
from pathlib import Path

import httpx

from universal.exceptions import ConfigError
from universal.paths import user_data_dir
from universal.release import current_version
from universal.server import build_serve_app
from universal.web_dist import resolve_web_dist

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 43124
WINDOW_TITLE = "Abaco Universal Harness"


def desktop_face_url(host: str, port: int, version: str | None = None) -> str:
    """Version the first document so WKWebView cannot reuse a v1.0.0 index.html."""
    return f"http://{host}:{port}/?v={version or current_version()}"


def webview_storage_dir() -> Path:
    path = user_data_dir() / "webview"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _request_macos_microphone() -> None:
    """Trigger the system Microphone prompt from the host process, not WKWebView."""
    try:
        from AVFoundation import AVCaptureDevice, AVMediaTypeAudio  # type: ignore[import-not-found]

        AVCaptureDevice.requestAccessForMediaType_completionHandler_(
            AVMediaTypeAudio, lambda _granted: None
        )
    except Exception:
        return


def _find_wkwebview(view: object) -> object | None:
    if view is None:
        return None
    name = type(view).__name__
    if "WKWebView" in name or hasattr(view, "configuration"):
        return view
    subviews = getattr(view, "subviews", None)
    if callable(subviews):
        try:
            subviews = subviews()
        except Exception:
            return None
    if not subviews:
        return None
    for child in subviews:
        found = _find_wkwebview(child)
        if found is not None:
            return found
    return None


def _enable_webkit_media(window: object) -> None:
    """Turn on WKWebView mediaDevices so Chat can call getUserMedia."""
    try:
        native = getattr(window, "native", None)
        webview_obj = _find_wkwebview(native)
        if webview_obj is None:
            content = getattr(native, "contentView", None)
            if callable(content):
                content = content()
            webview_obj = _find_wkwebview(content)
        if webview_obj is None:
            return
        configuration = getattr(webview_obj, "configuration", None)
        config = configuration() if callable(configuration) else configuration
        if config is None:
            return
        preferences = getattr(config, "preferences", None)
        prefs = preferences() if callable(preferences) else preferences
        if prefs is None:
            return
        setter = getattr(prefs, "setValue_forKey_", None)
        if callable(setter):
            setter(True, "mediaDevicesEnabled")
            setter(True, "mediaStreamEnabled")
    except Exception:
        return


def wait_for_health(url: str, *, timeout: float = 20.0) -> None:
    deadline = time.monotonic() + timeout
    last_error = "no attempt"
    while time.monotonic() < deadline:
        try:
            response = httpx.get(f"{url}/health", timeout=0.5)
            if response.status_code == 200 and response.json().get("status") == "ok":
                return
            last_error = f"HTTP {response.status_code}"
        except Exception as exc:
            last_error = str(exc)
        time.sleep(0.1)
    raise ConfigError(f"Desktop factory did not become healthy at {url}: {last_error}")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((DEFAULT_HOST, 0))
        return int(sock.getsockname()[1])


def start_factory_thread(
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    demo: bool = False,
    persist: bool = True,
) -> threading.Thread:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ConfigError("v1 desktop binds localhost only. Do not pass a public host.")

    import uvicorn

    app = build_serve_app(demo=demo, persist=persist)
    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="universal-factory", daemon=True)
    thread.start()
    return thread


def run_desktop(
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    demo: bool = False,
    open_window: bool = True,
) -> int:
    from universal.plugins.installer import ensure_plugins_installed

    ensure_plugins_installed()
    dist = resolve_web_dist()
    if dist is None:
        raise ConfigError(
            "web/dist is missing. Run `cd web && bun run build` (or scripts/build_macos.sh) first."
        )
    start_factory_thread(host=host, port=port, demo=demo, persist=True)
    url = f"http://{host}:{port}"
    face = desktop_face_url(host, port)
    wait_for_health(url)
    from universal.rules import ensure_rules_file
    from universal.runtime_manager import default_manager

    ensure_rules_file()
    default_manager().start(core_url=url)
    if not open_window:
        return 0
    try:
        import webview
    except ImportError as exc:
        raise ConfigError(
            "pywebview is not installed. pip install 'universal[desktop]'"
        ) from exc
    try:
        webview.settings['ALLOW_DOWNLOADS'] = True
    except Exception:
        pass
    _request_macos_microphone()
    window = webview.create_window(
        WINDOW_TITLE,
        face,
        width=1200,
        height=800,
        resizable=True,
        fullscreen=False,
        min_size=(800, 600),
        background_color="#0B0E14",
    )

    def _after_start() -> None:
        _enable_webkit_media(window)

    # private_mode=True (the default) leaves mediaDevices undefined in WKWebView.
    # Store site data under Application Support so a wipe actually deletes it.
    start_kwargs: dict[str, object] = {
        "func": _after_start,
        "private_mode": False,
        "storage_path": str(webview_storage_dir()),
    }
    try:
        webview.start(**start_kwargs)
    except TypeError:
        webview.start(func=_after_start, private_mode=False)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="universal desktop",
        description="Open the Universal factory in a native window (same localhost serve).",
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Echo provider so the window works without UNIVERSAL_LLM_API_KEY.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the built SPA and factory health without opening a window.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if args.check:
        dist = resolve_web_dist()
        if dist is None:
            print("universal desktop: web/dist not found (run bun run build)", flush=True)
            return 2
        port = _free_port() if args.port == DEFAULT_PORT else args.port
        start_factory_thread(host=args.host, port=port, demo=True, persist=False)
        wait_for_health(f"http://{args.host}:{port}")
        from universal.runtime_manager import default_manager

        runtime = default_manager()
        runtime.start(core_url=f"http://{args.host}:{port}")
        up = runtime.healthy()
        runtime.stop()
        print(
            f"universal desktop: ok  face={dist}  factory=http://{args.host}:{port}  "
            f"runtime={'up' if up else 'off'}"
        )
        return 0
    return run_desktop(host=args.host, port=args.port, demo=args.demo, open_window=True)


if __name__ == "__main__":
    raise SystemExit(main())
