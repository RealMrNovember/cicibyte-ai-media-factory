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
    assert all(v["gender"] in ("male", "female") for v in tts.VOICE_CATALOG.values())


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
