import wave

import pytest
from pydantic import ValidationError

from mediafactory.pipeline import tts
from mediafactory.pipeline.voice import VoiceSettings

H = {"X-MF-Client": "1"}


def test_catalog_has_both_languages_and_valid_defaults():
    langs = {v["language"] for v in tts.VOICE_CATALOG.values()}
    assert langs == {"en", "tr"}
    for lang, vid in tts.DEFAULT_VOICE.items():
        assert tts.VOICE_CATALOG[vid]["language"] == lang
    assert all(v["gender"] in ("male", "female", "neutral") for v in tts.VOICE_CATALOG.values())


def test_voice_for_language_falls_back_to_default():
    assert tts.voice_for("tr", "en_US-lessac-high") == "tr_TR-dfki-medium"  # wrong language -> default
    assert tts.voice_for("en", "en_GB-cori-high") == "en_GB-cori-high"
    assert tts.voice_for("en", None) == tts.DEFAULT_VOICE["en"]


def test_voice_settings_validate_ranges_and_ids():
    v = VoiceSettings(en="en_GB-alan-medium", speed=1.1, pitch=-3)
    assert v.length_scale == pytest.approx(1 / 1.1)
    with pytest.raises(ValidationError):
        VoiceSettings(speed=2.0)
    with pytest.raises(ValidationError):
        VoiceSettings(pitch=9)
    with pytest.raises(ValidationError):
        VoiceSettings(en="nope")


def _tone(path, seconds=1.0, rate=22050):
    import math
    import struct

    with wave.open(str(path), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * 220 * i / rate))) for i in range(int(rate * seconds))))


def test_pitch_shift_keeps_duration(tmp_path):
    src = tmp_path / "a.wav"
    _tone(src)
    tts.shift_pitch(src, -3)
    with wave.open(str(src)) as w:
        assert abs(w.getnframes() / w.getframerate() - 1.0) < 0.05


def test_voices_api_lists_catalog(client):
    data = client.get("/api/voices").json()
    ids = {v["id"] for v in data["voices"]}
    assert "en_US-ryan-high" in ids and "tr_TR-dfki-medium" in ids and data["defaults"]["tr"] == "tr_TR-dfki-medium"


def test_make_passes_voice_settings(client, db):
    from sqlalchemy import select

    from mediafactory.db.models import JobStageRun, SourceItem

    it = SourceItem(source_type="manual", title="v", raw_text="x" * 500, normalized_text="x" * 500, content_hash="vh1")
    db.add(it)
    db.flush()
    body = {"languages": ["en"], "voice": {"en": "en_GB-cori-high", "speed": 0.9, "pitch": -2}}
    assert client.post(f"/api/items/{it.id}/make", json=body, headers=H).status_code == 201
    run = db.scalar(select(JobStageRun).order_by(JobStageRun.id.desc()).limit(1))
    assert run.inputs["voice"] == {"en": "en_GB-cori-high", "tr": "tr_TR-dfki-medium", "speed": 0.9, "pitch": -2}


def test_chatterbox_hidden_unless_installed(client, monkeypatch):
    monkeypatch.delenv("MF_CHATTERBOX_PYTHON", raising=False)
    ids = {v["id"] for v in client.get("/api/voices").json()["voices"]}
    assert "tr-chatterbox" not in ids
    assert tts.voice_for("tr", "tr-chatterbox") == "tr_TR-dfki-medium"  # falls back when not installed


def test_chatterbox_engine_runs_worker_and_applies_speed(tmp_path, monkeypatch):
    """A fake 'chatterbox python' stands in for the real virtualenv: it writes a 2 s WAV like the worker would."""
    import sys

    fake = tmp_path / "fake_worker_python.py"
    fake.write_text(
        "import json, sys, wave\n"
        "req = json.loads(sys.stdin.read())\n"
        "w = wave.open(req['out'], 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000)\n"
        "w.writeframes(bytes(2) * 48000); w.close()\n"
        "print(json.dumps({'ok': True, 'seconds': 2.0}))\n",
        encoding="utf-8",
    )
    launcher = tmp_path / ("py.cmd" if sys.platform == "win32" else "py.sh")
    if sys.platform == "win32":
        launcher.write_text(f'@"{sys.executable}" "{fake}"\n', encoding="utf-8")
    else:
        launcher.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{fake}"\n', encoding="utf-8")
        launcher.chmod(0o755)
    monkeypatch.setenv("MF_CHATTERBOX_PYTHON", str(launcher))
    monkeypatch.setattr(tts, "WORKER", fake)  # the launcher ignores it; keeps the call shape real
    assert tts.voice_for("tr", "tr-chatterbox") == "tr-chatterbox"
    out = tmp_path / "v.wav"
    secs = tts.synthesize_voice("tr-chatterbox", "tr", "Merhaba.", out, models_dir=tmp_path, speed=1.25)
    assert abs(secs - 1.6) < 0.1  # 2 s sped up 1.25x


def test_chatterbox_failure_is_reported(tmp_path, monkeypatch):
    import sys

    bad = tmp_path / "bad.py"
    bad.write_text("import json; print(json.dumps({'ok': False, 'error': 'model download failed'}))\n", encoding="utf-8")
    monkeypatch.setenv("MF_CHATTERBOX_PYTHON", sys.executable)
    monkeypatch.setattr(tts, "WORKER", bad)
    with pytest.raises(RuntimeError, match="model download failed"):
        tts.synthesize_voice("tr-chatterbox", "tr", "Merhaba.", tmp_path / "x.wav", models_dir=tmp_path)
