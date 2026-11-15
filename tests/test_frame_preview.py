import shutil
import subprocess

import pytest

from mediafactory.pipeline import framepreview
from mediafactory.pipeline.style import CaptionStyle

H = {"X-MF-Client": "1"}
needs_ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")


def _size(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height",
                          "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True).stdout  # fmt: skip
    return tuple(int(x) for x in out.strip().split(","))


def test_sample_cue_shows_the_chosen_words_per_line():
    ass = framepreview.sample_ass("Gece yarısı kapı yavaşça açıldı", CaptionStyle(words_per_cue=2), "tr")
    assert "GECE YARISI" in ass and "KAPI" not in ass.split("Dialogue:")[1]


def test_karaoke_shows_the_first_word_highlighted():
    ass = framepreview.sample_ass("one two three", CaptionStyle(animation="karaoke", words_per_cue=3), "en")
    assert ass.count("Dialogue:") == 1 and "\\c&H" in ass


@needs_ffmpeg
def test_frame_is_rendered_at_the_video_size(tmp_path):
    out = framepreview.render_frame(tmp_path, style=CaptionStyle(), text="It came back tonight", language="en", background=None)
    assert out.suffix == ".jpg" and _size(out) == (1080, 1920)
    wide = framepreview.render_frame(tmp_path, style=CaptionStyle(aspect="16:9"), text="It came back", language="en", background=None)
    assert _size(wide) == (1920, 1080)


@needs_ffmpeg
def test_api_returns_a_jpeg(client):
    r = client.post("/api/studio/frame", json={"style": {"size": 100}, "text": "Merhaba dünya", "language": "tr"}, headers=H)
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg" and r.content[:2] == b"\xff\xd8"


def test_api_rejects_unknown_background(client):
    r = client.post("/api/studio/frame", json={"background": "../../etc/passwd", "text": "x"}, headers=H)
    assert r.status_code == 404
