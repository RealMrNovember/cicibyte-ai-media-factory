"""Voice cloning: your own voice samples drive Chatterbox; the Chatterbox model stays loaded between jobs."""

import io
import json
import sys
import wave

import pytest
from pydantic import ValidationError

from mediafactory.pipeline import clones, tts
from mediafactory.pipeline.voice import VoiceSettings

H = {"X-MF-Client": "1"}


def _tone_bytes(seconds: float, rate: int = 44100, channels: int = 2) -> bytes:
    import math
    import struct

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels), w.setsampwidth(2), w.setframerate(rate)
        frame = lambda i: struct.pack("<h", int(6000 * math.sin(2 * math.pi * 180 * i / rate))) * channels  # noqa: E731
        w.writeframes(b"".join(frame(i) for i in range(int(rate * seconds))))
    return buf.getvalue()


def _seconds(path) -> float:
    with wave.open(str(path)) as w:
        assert w.getnchannels() == 1 and w.getframerate() == clones.RATE
        return w.getnframes() / w.getframerate()


@pytest.fixture
def data(tmp_path, monkeypatch):
    monkeypatch.setattr(clones, "data_dir", lambda: tmp_path)
    return tmp_path


def test_add_clone_converts_to_mono_reference_and_lists_it(data):
    c = clones.add_clone(data, "me.wav", io.BytesIO(_tone_bytes(8)), label="My voice", consent=True)
    assert clones.CLONE_ID.match(c["id"]) and c["label"] == "My voice"
    assert c["engine"] == "chatterbox" and c["language"] == "any" and c["gender"] == "custom"
    assert abs(_seconds(clones.clone_path(data, c["id"])) - 8) < 0.2
    assert [v["id"] for v in clones.list_clones(data)] == [c["id"]]


def test_long_samples_are_trimmed(data):
    c = clones.add_clone(data, "long.wav", io.BytesIO(_tone_bytes(40, rate=16000, channels=1)), label="x", consent=True)
    assert abs(_seconds(clones.clone_path(data, c["id"])) - clones.MAX_S) < 0.2


@pytest.mark.parametrize("name,secs,consent,msg", [
    ("short.wav", 2, True, "at least"), ("me.wav", 8, False, "permission"), ("me.exe", 8, True, "unsupported"),
])  # fmt: skip
def test_bad_samples_are_refused(data, name, secs, consent, msg):
    with pytest.raises(ValueError, match=msg):
        clones.add_clone(data, name, io.BytesIO(_tone_bytes(secs)), label="x", consent=consent)
    assert clones.list_clones(data) == []


def test_remove_clone_and_reject_bad_ids(data):
    c = clones.add_clone(data, "me.wav", io.BytesIO(_tone_bytes(6)), label="x", consent=True)
    assert clones.clone_path(data, "../etc/passwd") is None and clones.clone_path(data, "clone-zz") is None
    assert clones.remove_clone(data, c["id"]) and clones.list_clones(data) == []
    assert not clones.remove_clone(data, c["id"])


def test_clone_speaks_any_language_only_with_chatterbox(data, monkeypatch):
    c = clones.add_clone(data, "me.wav", io.BytesIO(_tone_bytes(6)), label="x", consent=True)
    monkeypatch.setenv("MF_CHATTERBOX_PYTHON", sys.executable)
    assert tts.voice_for("tr", c["id"]) == c["id"] and tts.voice_for("en", c["id"]) == c["id"]
    assert VoiceSettings(tr=c["id"], en=c["id"]).tr == c["id"]
    monkeypatch.delenv("MF_CHATTERBOX_PYTHON")
    assert tts.voice_for("tr", c["id"]) == "tr_TR-dfki-medium"  # falls back to Piper without Chatterbox
    with pytest.raises(ValidationError):
        VoiceSettings(tr="clone-00000000")  # unknown clone


FAKE_SERVER = """
import json, os, sys, wave
for line in sys.stdin:
    req = json.loads(line)
    w = wave.open(req['out'], 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000)
    w.writeframes(bytes(2) * 24000); w.close()
    print(json.dumps({'ok': True, 'seconds': 1.0, 'pid': os.getpid(), 'reference': req.get('reference')}), flush=True)
"""


def _fake_chatterbox(tmp_path, monkeypatch, body=FAKE_SERVER):
    fake = tmp_path / "fake_server.py"
    fake.write_text(body, encoding="utf-8")
    monkeypatch.setenv("MF_CHATTERBOX_PYTHON", sys.executable)
    monkeypatch.setattr(tts, "WORKER", fake)
    tts.chatterbox_shutdown()


def test_model_stays_loaded_between_requests(tmp_path, monkeypatch):
    _fake_chatterbox(tmp_path, monkeypatch)
    try:
        first = tts.chatterbox_request({"text": "a", "language": "tr", "out": str(tmp_path / "1.wav")})
        second = tts.chatterbox_request({"text": "b", "language": "tr", "out": str(tmp_path / "2.wav")})
        assert first["pid"] == second["pid"]  # one process, model loaded once
        tts.chatterbox_shutdown()
        third = tts.chatterbox_request({"text": "c", "language": "tr", "out": str(tmp_path / "3.wav")})
        assert third["pid"] != first["pid"]
    finally:
        tts.chatterbox_shutdown()


def test_short_keep_and_low_memory_release_the_model(tmp_path, monkeypatch):
    import time

    _fake_chatterbox(tmp_path, monkeypatch)
    monkeypatch.setattr(tts._SERVER, "REAP_S", 0.05)
    try:
        tts.chatterbox_request({"text": "a", "language": "tr", "out": str(tmp_path / "1.wav")}, keep_s=0.2)
        assert tts._SERVER.proc is not None
        time.sleep(1.5)
        assert tts._SERVER.proc is None  # a preview gives the memory back quickly
        tts.chatterbox_request({"text": "a", "language": "tr", "out": str(tmp_path / "1.wav")})  # default: long keep
        time.sleep(0.5)
        assert tts._SERVER.proc is not None
        monkeypatch.setattr(tts, "low_memory", lambda: True)
        time.sleep(1.5)
        assert tts._SERVER.proc is None  # released when the machine runs short of memory
    finally:
        tts.chatterbox_shutdown()


def test_cloned_voice_sends_its_reference(data, monkeypatch):
    c = clones.add_clone(data, "me.wav", io.BytesIO(_tone_bytes(6)), label="x", consent=True)
    _fake_chatterbox(data, monkeypatch)
    seen = {}
    real = tts.chatterbox_request
    monkeypatch.setattr(tts, "chatterbox_request", lambda req, **kw: seen.update(req) or real(req, **kw))
    try:
        secs = tts.synthesize_voice(c["id"], "tr", "Merhaba.", data / "v.wav", models_dir=data)
    finally:
        tts.chatterbox_shutdown()
    assert abs(secs - 1.0) < 0.05 and seen["reference"] == str(clones.clone_path(data, c["id"]))
    assert seen["language"] == "tr"


def test_dead_server_reports_its_error_and_restarts(tmp_path, monkeypatch):
    _fake_chatterbox(tmp_path, monkeypatch, "import sys; sys.stderr.write('CUDA? no: boom'); sys.exit(3)\n")
    try:
        with pytest.raises(RuntimeError, match="boom"):
            tts.chatterbox_request({"text": "a", "language": "tr", "out": str(tmp_path / "1.wav")})
        _fake_chatterbox(tmp_path, monkeypatch)  # fixed install: next request starts a fresh process
        assert tts.chatterbox_request({"text": "a", "language": "tr", "out": str(tmp_path / "1.wav")})["ok"]
    finally:
        tts.chatterbox_shutdown()


def test_clone_api_upload_list_preview_sample_delete(client, data, monkeypatch):
    monkeypatch.setenv("MF_CHATTERBOX_PYTHON", sys.executable)
    files = {"file": ("me.wav", io.BytesIO(_tone_bytes(6)), "audio/wav")}
    r = client.post("/api/voices/clones", headers=H, files=files, data={"label": "Benim sesim", "consent": "false"})
    assert r.status_code == 422
    files = {"file": ("me.wav", io.BytesIO(_tone_bytes(6)), "audio/wav")}
    r = client.post("/api/voices/clones", headers=H, files=files, data={"label": "Benim sesim", "consent": "true"})
    assert r.status_code == 201
    cid = r.json()["id"]
    voices = {v["id"]: v for v in client.get("/api/voices").json()["voices"]}
    assert voices[cid]["label"] == "Benim sesim" and voices[cid]["language"] == "any"
    assert client.get(f"/api/voices/clones/{cid}/audio").status_code == 200
    assert client.delete(f"/api/voices/clones/{cid}", headers=H).status_code == 200
    assert client.delete(f"/api/voices/clones/{cid}", headers=H).status_code == 404


def test_clones_hidden_without_chatterbox(client, data, monkeypatch):
    clones.add_clone(data, "me.wav", io.BytesIO(_tone_bytes(6)), label="x", consent=True)
    monkeypatch.delenv("MF_CHATTERBOX_PYTHON", raising=False)
    data_ = client.get("/api/voices").json()
    assert not any(v["id"].startswith("clone-") for v in data_["voices"]) and data_["cloning"] is False
    assert json.dumps(data_)  # serialisable
