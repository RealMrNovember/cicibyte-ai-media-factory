"""Chatterbox voice server for a machine with a GPU (standard library only, besides Chatterbox itself).

Media Factory sends POST /synthesize {text, language, exaggeration, cfg_weight, reference_b64?} with
`Authorization: Bearer <token>` and gets a 16-bit WAV back. Requests are handled one at a time on the GPU.

    python tts_server.py --host 100.x.y.z --port 8765      # token from MF_TTS_TOKEN

Copy this file and chatterbox_worker.py into the same folder on the GPU machine.
"""

import argparse
import base64
import hashlib
import hmac
import json
import os
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MAX_BODY = 20 * 1024 * 1024  # text plus a reference recording of up to 30 seconds


def make_handler(engine, *, token: str):
    lock = threading.Lock()
    refs = Path(tempfile.mkdtemp(prefix="mf-tts-refs-"))

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # quiet: one line per request is enough
            pass

        def _reply(self, code: int, body: bytes, kind: str = "application/json") -> None:
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _error(self, code: int, message: str) -> None:
            self._reply(code, json.dumps({"error": message}).encode())

        def do_GET(self):  # noqa: N802 - http.server API
            if self.path == "/health":
                return self._reply(200, json.dumps({"ok": True, "device": getattr(engine, "device", "?")}).encode())
            self._error(404, "not found")

        def do_POST(self):  # noqa: N802
            if self.path != "/synthesize":
                return self._error(404, "not found")
            if not hmac.compare_digest(self.headers.get("Authorization", ""), f"Bearer {token}"):
                return self._error(401, "bad token")
            size = int(self.headers.get("Content-Length") or 0)
            if size <= 0 or size > MAX_BODY:
                return self._error(400, "missing or too large body")
            try:
                req = json.loads(self.rfile.read(size))
                text = str(req.get("text") or "").strip()
            except (ValueError, AttributeError):
                return self._error(400, "body must be JSON")
            if not text:
                return self._error(400, "no text")
            job = {"text": text, "language": str(req.get("language") or "en"),
                   "exaggeration": float(req.get("exaggeration", 0.5)), "cfg_weight": float(req.get("cfg_weight", 0.5))}  # fmt: skip
            if req.get("reference_b64"):
                data = base64.b64decode(req["reference_b64"])
                ref = refs / (hashlib.sha256(data).hexdigest()[:24] + ".wav")  # same voice -> same file -> cached conditioning
                if not ref.exists():
                    ref.write_bytes(data)
                job["reference"] = str(ref)
            with tempfile.TemporaryDirectory() as td, lock:
                job["out"] = str(Path(td) / "out.wav")
                try:
                    result = engine.run(job)
                except Exception as exc:  # noqa: BLE001 - report it to the caller
                    return self._error(500, f"{type(exc).__name__}: {exc}"[:400])
                if not result.get("ok", True):
                    return self._error(500, str(result.get("error"))[:400])
                self._reply(200, Path(job["out"]).read_bytes(), "audio/wav")

    return Handler


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    token = os.environ.get("MF_TTS_TOKEN", "")
    if len(token) < 16:
        raise SystemExit("set MF_TTS_TOKEN (at least 16 characters)")
    try:
        from chatterbox_worker import Engine  # next to this file on the GPU machine
    except ImportError:
        from mediafactory.pipeline.chatterbox_worker import Engine
    engine = Engine(int(os.environ.get("MF_TTS_THREADS", "4")), device=os.environ.get("MF_TTS_DEVICE", "auto"))
    print(f"voice server on {args.host}:{args.port} ({engine.device})", flush=True)
    ThreadingHTTPServer((args.host, args.port), make_handler(engine, token=token)).serve_forever()


if __name__ == "__main__":
    main()
