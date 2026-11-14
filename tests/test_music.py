import io
import shutil
import subprocess
import wave

import pytest
from pydantic import ValidationError

from mediafactory.pipeline import music
from mediafactory.pipeline.music import MusicSettings

H = {"X-MF-Client": "1"}


def test_settings_defaults_and_validation():
    s = MusicSettings()
    assert s.track == "none" and s.volume_db == -18 and s.ducking
    with pytest.raises(ValidationError):
        MusicSettings(volume_db=0)
    with pytest.raises(ValidationError):
        MusicSettings(track="../../etc/passwd")
    assert MusicSettings(track="gen:dark").track == "gen:dark"


def test_library_add_list_resolve_remove(tmp_path):
    music.add_track(tmp_path, "My Song (Final).MP3", io.BytesIO(b"id3"), licence="")
    names = [t["name"] for t in music.tracks(tmp_path)]
    assert names == ["My-Song-Final.mp3"]
    assert music.resolve(tmp_path, "My-Song-Final.mp3") is not None and music.resolve(tmp_path, "../x.mp3") is None
    with pytest.raises(ValueError):
        music.add_track(tmp_path, "evil.exe", io.BytesIO(b"x"), licence="")
    assert music.remove_track(tmp_path, "My-Song-Final.mp3") and music.tracks(tmp_path) == []


def test_source_for_choices(tmp_path):
    assert music.source_for(tmp_path, MusicSettings(track="none"), seconds=10) is None
    gen = music.source_for(tmp_path, MusicSettings(track="gen:tension"), seconds=10)
    assert gen[0] == "-f" and "aevalsrc" in gen[-1] and "d=10" in gen[-1]
    assert music.source_for(tmp_path, MusicSettings(track="random"), seconds=10) is None  # empty library
    music.add_track(tmp_path, "a.mp3", io.BytesIO(b"x"), licence="")
    rnd = music.source_for(tmp_path, MusicSettings(track="random"), seconds=10)
    assert rnd[:3] == ["-stream_loop", "-1", "-i"] and rnd[-1].endswith("a.mp3")


def test_audio_graph_with_and_without_ducking():
    g = music.audio_graph(MusicSettings(track="gen:dark", volume_db=-20, ducking=True), total=30.0, music_input=2)
    assert "sidechaincompress" in g and "volume=-20dB" in g and "afade=t=out" in g and g.endswith("[a]")
    g2 = music.audio_graph(MusicSettings(track="gen:dark", ducking=False), total=30.0, music_input=2)
    assert "sidechaincompress" not in g2
    assert music.audio_graph(MusicSettings(), total=30.0, music_input=None).startswith("[1:a]loudnorm")


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")
def test_render_mixes_generated_music(tmp_path):
    from mediafactory.pipeline.qc import measure
    from mediafactory.pipeline.render import render_short

    with wave.open(str(tmp_path / "voice.wav"), "wb") as w:  # 3 s of silence as the "narration"
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(22050)
        w.writeframes(b"\x00\x00" * 22050 * 3)
    (tmp_path / "c.ass").write_text("[Script Info]\nScriptType: v4.00+\n", encoding="utf-8")
    out = render_short(tmp_path, audio="voice.wav", captions_ass="c.ass", duration=3.0,
                       music=MusicSettings(track="gen:mystery", volume_db=-12))  # fmt: skip
    m = measure(out)
    assert m["has_audio"] and m["lufs"] is not None and m["lufs"] > -40  # music is audible over silent narration


def test_music_api_lists_presets_and_uploads(client, tmp_path, monkeypatch):
    from mediafactory.api.routes import music as route

    monkeypatch.setattr(route, "_data", lambda: tmp_path)
    data = client.get("/api/music").json()
    assert {g["id"] for g in data["generated"]} == {"gen:dark", "gen:tension", "gen:mystery"}
    r = client.post("/api/music", headers=H, files={"file": ("calm.mp3", io.BytesIO(b"id3"), "audio/mpeg")})
    assert r.status_code == 201 and r.json()["name"] == "calm.mp3"
    assert [t["name"] for t in client.get("/api/music").json()["tracks"]] == ["calm.mp3"]
    assert client.delete("/api/music/calm.mp3", headers=H).status_code == 200


def test_make_stores_music_settings(client, db):
    from sqlalchemy import select

    from mediafactory.db.models import JobStageRun, SourceItem

    it = SourceItem(source_type="manual", title="m", raw_text="x" * 500, normalized_text="x" * 500, content_hash="mh1")
    db.add(it)
    db.flush()
    body = {"languages": ["en"], "music": {"track": "gen:dark", "volume_db": -20, "ducking": False}}
    assert client.post(f"/api/items/{it.id}/make", json=body, headers=H).status_code == 201
    run = db.scalar(select(JobStageRun).order_by(JobStageRun.id.desc()).limit(1))
    assert run.inputs["music"] == {"track": "gen:dark", "volume_db": -20, "ducking": False}
