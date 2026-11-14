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
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

APP_NAME = "CiciByte AI Media Factory"
DEFAULT_SERVER = "http://mediafactory:8080"
WEB_DIR = Path(__file__).resolve().parent / "web"
HOP_HEADERS = {"connection", "keep-alive", "transfer-encoding", "upgrade", "host", "proxy-connection", "te", "trailer"}


def app_home() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    home = Path(base) / "CiciByteMediaFactory" if base else Path.home() / ".cicibyte-media-factory"
    home.mkdir(parents=True, exist_ok=True)
    return home


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

    @property
    def server_url(self) -> str:
        return normalize(os.environ.get("MF_SERVER_URL") or self.data.get("server_url") or DEFAULT_SERVER)

    def set_server(self, url: str) -> None:
        with self.lock:
            self.data["server_url"] = normalize(url)
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
                    url = normalize(json.loads(self._body() or b"{}").get("server_url", ""))
                except ValueError:
                    url = ""
                if not url.startswith(("http://", "https://")):
                    return self._json(400, {"detail": "invalid address"})
                cfg.set_server(url)
            url = cfg.server_url
            from mediafactory import __version__

            return self._json(200, {"server_url": url, "reachable": reachable(url), "app_version": __version__,
                                    "update": cfg.update})  # fmt: skip

        def _desktop_update(self):
            """Download the newer installer (checksum-verified), start it and quit; it reopens the app."""
            from mediafactory import desktop_update

            if not self.headers.get("X-MF-Client"):
                return self._json(403, {"detail": "missing X-MF-Client header"})
            if not cfg.update:
                return self._json(409, {"detail": "no update available"})
            try:
                path = desktop_update.download(cfg.update, cfg.home / "updates")
                desktop_update.launch_installer(path)
            except Exception as exc:
                return self._json(502, {"detail": f"update failed: {exc}"})
            self._json(200, {"ok": True, "version": cfg.update["version"]})
            threading.Timer(1.5, lambda: os._exit(0)).start()  # let the installer replace our files

        def _proxy(self):
            target = urllib.parse.urlsplit(cfg.server_url)
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
            """Serve the panel from the server when it is reachable, so panel updates need no reinstall."""
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
            if resp.status != 200 or not (ctype.startswith(("text/", "image/")) or "javascript" in ctype):
                return False
            self._send(200, body, ctype)
            return True

        def _route(self):
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


class JsApi:
    """Called from the panel: open sign-in pages (Google blocks embedded windows) in the real browser."""

    def open_url(self, url: str) -> bool:
        import webbrowser

        if not url.startswith("https://"):
            return False
        return webbrowser.open(url)


def main() -> None:
    import webview

    cfg = Config(app_home())

    def _check_updates():
        from mediafactory import desktop_update

        cfg.update = desktop_update.check()

    threading.Thread(target=_check_updates, name="update-check", daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(cfg))
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, name="local-panel", daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    webview.create_window(APP_NAME, url, js_api=JsApi(), width=1320, height=880, min_size=(420, 600), background_color="#0b0b0e")
    try:
        webview.start(private_mode=False, storage_path=str(app_home() / "webview"))
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
