"""Desktop app: a native window for a Media Factory server.

All production (database, AI, voice, captions, rendering, scheduling) runs on the server. The app ships the
panel itself and serves it from a private local port; /api requests are forwarded to the server address set
in Settings (kept in %LOCALAPPDATA%\\CiciByteMediaFactory\\config.json). The window always opens — when the
server cannot be reached the panel says so and Settings stays usable.
Powered by CiciByte Technology — https://cicibyte.com
"""

import http.client
import json
import mimetypes
import os
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

APP_NAME = "CiciByte AI Media Factory"
WEB_DIR = Path(__file__).resolve().parent / "web"
mimetypes.add_type("font/woff2", ".woff2")  # not known to Windows' registry
HOP_HEADERS = {"connection", "keep-alive", "transfer-encoding", "upgrade", "host", "proxy-connection", "te", "trailer"}


def app_home() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    home = Path(base) / "CiciByteMediaFactory" if base else Path.home() / ".cicibyte-media-factory"
    home.mkdir(parents=True, exist_ok=True)
    return home


def local_supported() -> bool:
    """The engine runs on this computer only on Windows in v0.5.0; macOS/Linux follow."""
    return sys.platform == "win32"


def normalize(url: str) -> str:
    url = (url or "").strip().rstrip("/")
    if url and "://" not in url:
        url = "http://" + url
    return url


class Config:
    def __init__(self, home: Path):
        self.path = home / "config.json"
        try:
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.data = {}
        self.lock = threading.Lock()
        self.update: dict | None = None  # filled by the background release check
        self.home = home
        self.engine_url = ""  # the local engine's API, once it runs
        self.engine_state: dict = {"state": "stopped", "step": None, "error": None}
        self.on_focus = lambda: None  # set by main(): bring the window forward
        self.shutdown = lambda: None  # set by main(): stop the local engine before the app quits

    @property
    def server_url(self) -> str:
        """The remote Media Factory server the user entered ("" when none: there is no built-in default)."""
        return normalize(os.environ.get("MF_SERVER_URL") or self.data.get("server_url") or "")

    @property
    def mode(self) -> str:
        """"local": run the engine on this computer; "remote": use server_url. Old installs with a saved
        server stay remote; new ones run locally where that is supported."""
        if os.environ.get("MF_SERVER_URL"):
            return "remote"
        chosen = self.data.get("mode")
        if chosen in ("local", "remote"):
            return "local" if chosen == "local" and local_supported() else "remote"
        if self.data.get("server_url"):
            return "remote"
        return "local" if local_supported() else "remote"

    @property
    def target_url(self) -> str:
        return self.engine_url if self.mode == "local" else self.server_url

    def set_server(self, url: str) -> None:
        self.set_option("server_url", normalize(url))

    def set_option(self, key: str, value) -> None:
        with self.lock:
            self.data[key] = value
            self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")


def reachable(url: str, timeout: float = 4.0) -> bool:
    try:
        u = urllib.parse.urlsplit(url)
        conn = (http.client.HTTPSConnection if u.scheme == "https" else http.client.HTTPConnection)(u.netloc, timeout=timeout)
        conn.request("GET", (u.path or "") + "/api/health")
        ok = conn.getresponse().status == 200
        conn.close()
        return ok
    except Exception:
        return False


def make_handler(cfg: Config):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):  # keep the console quiet
            pass

        def _send(self, status: int, body: bytes, ctype: str = "application/json", extra: dict | None = None):
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _json(self, status: int, data: dict, extra: dict | None = None):
            self._send(status, json.dumps(data).encode(), extra=extra)

        def _body(self) -> bytes:
            n = int(self.headers.get("Content-Length") or 0)
            return self.rfile.read(n) if n else b""

        def _desktop_config(self):
            if self.command == "POST":
                if not self.headers.get("X-MF-Client"):
                    return self._json(403, {"detail": "missing X-MF-Client header"})
                try:
                    body = json.loads(self._body() or b"{}")
                except ValueError:
                    body = {}
                if "notifications" in body:
                    cfg.set_option("notifications", bool(body["notifications"]))
                if "server_url" in body:
                    url = normalize(body.get("server_url", ""))
                    if not url.startswith(("http://", "https://")):
                        return self._json(400, {"detail": "invalid address"})
                    cfg.set_server(url)
                if body.get("mode") in ("local", "remote") and body["mode"] != cfg.mode:
                    if body["mode"] == "local" and not local_supported():
                        return self._json(400, {"detail": "running on this computer is not available on this system yet"})
                    cfg.set_option("mode", body["mode"])
                    return self._json(200, {"mode": body["mode"], "restart_required": True})
            from mediafactory import __version__

            local = cfg.mode == "local"
            url = cfg.target_url
            return self._json(200, {"mode": cfg.mode, "local_supported": local_supported(), "server_url": cfg.server_url,
                                    "reachable": (cfg.engine_state["state"] == "running") if local else bool(url) and reachable(url),
                                    "engine": {**cfg.engine_state, "data_dir": str(cfg.home / "data")} if local else None,
                                    "app_version": __version__, "update": cfg.update,
                                    "notifications": cfg.data.get("notifications", True)})  # fmt: skip

        def _desktop_update(self):
            """Download the newer installer (checksum-verified), start it and quit; it reopens the app."""
            from mediafactory import desktop_update

            if not self.headers.get("X-MF-Client"):
                return self._json(403, {"detail": "missing X-MF-Client header"})
            if not cfg.update:
                return self._json(409, {"detail": "no update available"})
            if cfg.update.get("manual"):  # Mac/Linux: open the release page; the user replaces the app
                import webbrowser

                webbrowser.open(cfg.update.get("page") or cfg.update["installer"])
                return self._json(200, {"ok": True, "manual": True, "version": cfg.update["version"]})
            try:
                path = desktop_update.download(cfg.update, cfg.home / "updates")
                desktop_update.launch_installer(path)
            except Exception as exc:
                return self._json(502, {"detail": f"update failed: {exc}"})
            self._json(200, {"ok": True, "version": cfg.update["version"]})

            def _quit():
                cfg.shutdown()  # stop the local engine first: no orphan database or worker
                os._exit(0)

            threading.Timer(1.5, _quit).start()  # let the installer replace our files

        def _proxy(self):
            if cfg.mode == "local" and cfg.engine_state["state"] != "running":
                return self._json(503, {"detail": "the engine is starting", "engine": cfg.engine_state}, {"X-MF-Desktop": "1"})
            if not cfg.target_url:
                return self._json(502, {"detail": "no server address set"}, {"X-MF-Desktop": "1"})
            target = urllib.parse.urlsplit(cfg.target_url)
            body = self._body()
            headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP_HEADERS}
            headers["Host"] = target.netloc
            try:
                conn_cls = http.client.HTTPSConnection if target.scheme == "https" else http.client.HTTPConnection
                conn = conn_cls(target.netloc, timeout=600)
                conn.request(self.command, (target.path or "") + self.path, body=body or None, headers=headers)
                resp = conn.getresponse()
            except Exception as exc:
                return self._json(502, {"detail": f"server unreachable: {exc}"}, {"X-MF-Desktop": "1"})
            self.send_response(resp.status)
            length = resp.getheader("Content-Length")
            for k, v in resp.getheaders():
                if k.lower() not in HOP_HEADERS:
                    self.send_header(k, v)
            if length is None:
                self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            try:
                while chunk := resp.read(64 * 1024):
                    if length is None:
                        self.wfile.write(f"{len(chunk):X}\r\n".encode() + chunk + b"\r\n")
                    else:
                        self.wfile.write(chunk)
                if length is None:
                    self.wfile.write(b"0\r\n\r\n")
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                conn.close()

        def _static(self):
            rel = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path).lstrip("/") or "index.html"
            path = (WEB_DIR / rel).resolve()
            if WEB_DIR not in path.parents or not path.is_file():
                path = WEB_DIR / "index.html"
            ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            if ctype.startswith("text/") or ctype.endswith("javascript"):
                ctype += "; charset=utf-8"
            self._send(200, path.read_bytes(), ctype)

        def _from_server(self) -> bool:
            """Serve the panel from the server when it is reachable, so panel updates need no reinstall.
            The local engine serves the same files as the app, so local mode uses the bundled copy directly."""
            if cfg.mode == "local" or not cfg.server_url:
                return False
            target = urllib.parse.urlsplit(cfg.server_url)
            try:
                conn_cls = http.client.HTTPSConnection if target.scheme == "https" else http.client.HTTPConnection
                conn = conn_cls(target.netloc, timeout=4)
                conn.request("GET", (target.path or "") + self.path, headers={"Host": target.netloc})
                resp = conn.getresponse()
                body = resp.read()
                conn.close()
            except Exception:
                return False
            ctype = resp.getheader("Content-Type", "")
            if resp.status != 200 or not (ctype.startswith(("text/", "image/", "font/")) or "javascript" in ctype):
                return False
            self._send(200, body, ctype)
            return True

        def _focus(self):
            try:
                cfg.on_focus()
            except Exception:  # noqa: BLE001 - the window may be gone
                pass
            return self._json(200, {"ok": True})

        def _route(self):
            if self.path == "/__focus" and self.command == "POST":
                return self._focus()
            if self.path.startswith("/desktop/config"):
                return self._desktop_config()
            if self.path.startswith("/desktop/update") and self.command == "POST":
                return self._desktop_update()
            if self.path.startswith("/api/"):
                return self._proxy()
            if self.command in ("GET", "HEAD"):
                if self._from_server():
                    return None
                return self._static()
            return self._json(405, {"detail": "method not allowed"})

        do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = _route

    return Handler


TITLEBAR_MARK = "pywebview-drag-region"


def panel_has_titlebar(server_url: str) -> bool:
    """True when the panel the app will show draws its own title bar: the server's panel when the server is
    reachable (it may be older than this app), otherwise the copy bundled with the app."""
    if reachable(server_url):
        try:
            u = urllib.parse.urlsplit(server_url)
            conn = (http.client.HTTPSConnection if u.scheme == "https" else http.client.HTTPConnection)(u.netloc, timeout=5)
            conn.request("GET", (u.path or "") + "/app.js")
            body = conn.getresponse().read().decode("utf-8", "replace")
            conn.close()
            return TITLEBAR_MARK in body
        except Exception:
            return False
    try:
        return TITLEBAR_MARK in (WEB_DIR / "app.js").read_text(encoding="utf-8")
    except OSError:
        return False


class JsApi:
    """Called from the panel: window controls for the custom title bar, and opening pages (Google sign-in
    refuses embedded windows) in the real browser."""

    # Only methods may be public: pywebview exposes every public attribute to the page and walks it
    # recursively, and a public window reference sent it into the native window forever (frozen black window).
    def __init__(self):
        self._window = None
        self._maximized = False

    def set_window(self, window) -> None:
        self._window = window

    def minimize(self) -> None:
        self._window.minimize()

    def toggle_maximize(self) -> bool:
        if self._maximized:
            self._window.restore()
        else:
            self._window.maximize()
        self._maximized = not self._maximized
        return self._maximized

    def close(self) -> None:
        self._window.destroy()

    def size(self) -> list[int]:
        return [self._window.width, self._window.height]

    def resize(self, width: int, height: int, anchor: str = "nw") -> None:
        """Resize keeping the opposite side in place (anchor: the corner/side that must not move)."""
        from webview.window import FixPoint

        fix = FixPoint(0)
        for ch, point in (("n", FixPoint.NORTH), ("s", FixPoint.SOUTH), ("w", FixPoint.WEST), ("e", FixPoint.EAST)):
            if ch in anchor:
                fix |= point
        self._window.resize(max(420, int(width)), max(600, int(height)), fix_point=fix or (FixPoint.NORTH | FixPoint.WEST))

    def open_url(self, url: str) -> bool:
        import webbrowser

        if not url.startswith("https://"):
            return False
        return webbrowser.open(url)


def _start_engine(cfg: Config):
    """Start the local engine in the background; the panel shows its progress until it runs."""
    from mediafactory.desktop_engine import Engine, EngineError

    bundled = Path(getattr(sys, "_MEIPASS", "")) / "ffmpeg"
    engine = Engine(cfg.home, ffmpeg_dir=bundled if bundled.is_dir() else None)
    stop = threading.Event()

    def _progress(step: str) -> None:
        cfg.engine_state = {"state": "starting", "step": step, "error": None}

    def _run() -> None:
        try:
            port = engine.start(progress=_progress)
        except EngineError as exc:
            cfg.engine_state = {"state": "failed", "step": None, "error": str(exc)}
            return
        cfg.engine_url = f"http://127.0.0.1:{port}"
        cfg.engine_state = {"state": "running", "step": None, "error": None}
        while not stop.wait(5):
            engine.watch_once()
            if engine.state == "failed":
                cfg.engine_state = {"state": "failed", "step": None, "error": engine.last_error}
                return

    cfg.engine_state = {"state": "starting", "step": "database", "error": None}
    threading.Thread(target=_run, name="engine", daemon=True).start()
    done = threading.Event()

    def _shutdown() -> None:
        if done.is_set():
            return
        done.set()
        stop.set()
        engine.stop()

    return _shutdown


def main() -> None:
    from mediafactory.desktop_engine import SingleInstance

    home = app_home()
    instance = SingleInstance(home)
    if not instance.acquire():  # already open: bring that window forward instead of a second engine
        instance.focus_existing()
        return
    import webview

    webview.settings["ALLOW_DOWNLOADS"] = True  # video, cover and settings downloads from the panel
    webview.settings["DRAG_REGION_DIRECT_TARGET_ONLY"] = True  # title bar buttons must not start a window drag
    cfg = Config(home)

    def _check_updates():
        from mediafactory import desktop_update

        cfg.update = desktop_update.check()

    threading.Thread(target=_check_updates, name="update-check", daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(cfg))
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, name="local-panel", daemon=True).start()
    instance.publish(server.server_address[1])
    if cfg.mode == "local":
        cfg.shutdown = _start_engine(cfg)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    api = JsApi()
    # Frameless: the panel draws its own title bar (live status, window buttons, resizable edges) — but only
    # when the panel we will show has that title bar, otherwise the window would have no close button.
    frameless = True if cfg.mode == "local" else panel_has_titlebar(cfg.server_url)
    window = webview.create_window(APP_NAME, url, js_api=api, width=1320, height=880, min_size=(420, 600),
                                   background_color="#0b0b0e", frameless=frameless, easy_drag=False)  # fmt: skip
    api.set_window(window)

    def _focus():
        window.restore()
        window.show()

    cfg.on_focus = _focus
    from mediafactory.desktop_monitor import Monitor

    icon = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent.parent / "packaging")) / "app.ico"
    Monitor(cfg, window, icon=str(icon) if icon.exists() else None).start()
    smoke = float(os.environ.get("MF_DESKTOP_SMOKE", "0") or 0)
    if smoke:  # CI check: open the window, let the panel (and engine) load, then close and exit 0
        threading.Timer(smoke, window.destroy).start()
    try:
        webview.start(private_mode=False, storage_path=str(home / "webview"))
    finally:
        cfg.shutdown()
        server.shutdown()
        instance.release()
    if smoke and cfg.mode == "local" and cfg.engine_url == "":
        raise SystemExit(f"engine did not start: {cfg.engine_state}")


if __name__ == "__main__":
    main()
