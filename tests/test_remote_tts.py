import base64
import io
import json
import threading
import wave
from http.server import ThreadingHTTPServer

import httpx
import pytest
import respx

from mediafactory.pipeline import tts, tts_server

URL = "http://gpu-box:8765"


def _wav_bytes(seconds=0.5, rate=24000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(seconds * rate))
    return buf.getvalue()


@pytest.fixture
def remote(monkeypatch):
    monkeypatch.setenv("MF_CHATTERBOX_URL", URL)
    monkeypatch.setenv("MF_CHATTERBOX_TOKEN", "tok-123")


@respx.mock
def test_remote_request_sends_text_reference_and_token(remote, tmp_path):
    ref = tmp_path / "ref.wav"
    ref.write_bytes(b"RIFFref")
    route = respx.post(f"{URL}/synthesize").mock(return_value=httpx.Response(200, content=_wav_bytes(0.5)))
    out = tmp_path / "out.wav"
    tts.chatterbox_request({"text": "Merhaba", "language": "tr", "out": str(out), "exaggeration": 0.55, "reference": str(ref)})
    req = route.calls[0].request
    body = json.loads(req.content)
    assert req.headers["authorization"] == "Bearer tok-123"
    assert body["text"] == "Merhaba" and body["language"] == "tr" and base64.b64decode(body["reference_b64"]) == b"RIFFref"
    assert "out" not in body and abs(tts.wav_seconds(out) - 0.5) < 0.01


@respx.mock
def test_unreachable_gpu_falls_back_to_the_local_engine(remote, tmp_path, monkeypatch):
    respx.post(f"{URL}/synthesize").mock(side_effect=httpx.ConnectError("down"))
    used = {}
    monkeypatch.setattr(tts._SERVER, "request", lambda req, timeout, keep_s: used.setdefault("local", req) and {"ok": True})
    monkeypatch.setattr(tts, "chatterbox_python", lambda: "/venv/python")
    tts.chatterbox_request({"text": "x", "language": "en", "out": str(tmp_path / "o.wav")})
    assert used["local"]["text"] == "x"


@respx.mock
def test_unreachable_gpu_without_local_engine_is_an_error(remote, tmp_path, monkeypatch):
    respx.post(f"{URL}/synthesize").mock(side_effect=httpx.ConnectError("down"))
    monkeypatch.setattr(tts, "chatterbox_python", lambda: None)
    with pytest.raises(RuntimeError, match="GPU voice server"):
        tts.chatterbox_request({"text": "x", "language": "en", "out": str(tmp_path / "o.wav")})


def test_remote_counts_as_installed(remote, monkeypatch):
    monkeypatch.delenv("MF_CHATTERBOX_PYTHON", raising=False)
    assert tts.chatterbox_ready() and tts.available({"engine": "chatterbox"})


class FakeEngine:
    def __init__(self):
        self.calls = []

    def run(self, req):
        self.calls.append(req)
        with wave.open(req["out"], "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(24000)
            w.writeframes(b"\x00\x00" * 2400)
        return {"ok": True, "seconds": 0.1}


def _serve(engine):
    handler = tts_server.make_handler(engine, token="tok-123")
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def test_server_requires_the_token_and_returns_wav():
    engine = FakeEngine()
    srv, base = _serve(engine)
    try:
        assert httpx.post(f"{base}/synthesize", json={"text": "hi"}).status_code == 401
        ref = base64.b64encode(b"RIFFvoice").decode()
        r = httpx.post(f"{base}/synthesize", json={"text": "hi", "language": "tr", "reference_b64": ref},
                       headers={"Authorization": "Bearer tok-123"})  # fmt: skip
        assert r.status_code == 200 and r.headers["content-type"] == "audio/wav" and r.content[:4] == b"RIFF"
        sent = engine.calls[0]
        assert sent["text"] == "hi" and sent["language"] == "tr" and open(sent["reference"], "rb").read() == b"RIFFvoice"
        assert httpx.get(f"{base}/health").json()["ok"] is True
    finally:
        srv.shutdown()


def test_server_rejects_bad_requests():
    srv, base = _serve(FakeEngine())
    try:
        h = {"Authorization": "Bearer tok-123"}
        assert httpx.post(f"{base}/synthesize", json={"text": ""}, headers=h).status_code == 400
        assert httpx.post(f"{base}/synthesize", content=b"not json", headers=h).status_code == 400
    finally:
        srv.shutdown()
