import shutil
import subprocess

import pytest

from mediafactory.pipeline import sfx
from mediafactory.pipeline.captions import cues_for, to_ass
from mediafactory.pipeline.music import MusicSettings, audio_graph
from mediafactory.pipeline.qc import judge
from mediafactory.pipeline.style import CaptionStyle, frame_size
from mediafactory.pipeline.thumbnail import title_ass
from mediafactory.youtube.upload import build_metadata

needs_ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")


def test_effects_are_found_in_english_and_turkish_words():
    assert sfx.effect_for("knocked,") == "knock" and sfx.effect_for("Kalbim") == "heartbeat"
    assert sfx.effect_for("gıcırdadı.") == "creak" and sfx.effect_for("THUNDER!") == "thunder"
    assert sfx.effect_for("house") is None and sfx.effect_for("gök") is None


def test_plan_puts_a_whoosh_under_the_hook_and_spaces_effects_out():
    words = ["Someone", "knocked.", "My", "heart", "raced.", "Then", "a", "scream", "and", "another", "knock."]
    starts = [0.2, 0.6, 1.2, 1.5, 1.8, 5.0, 5.2, 5.4, 9.0, 9.3, 9.6]
    plan = sfx.plan_cues(words, starts)
    assert plan[0] == (0.0, "whoosh")
    # the first knock (0.45 s) is too close to the whoosh; the heart (1.35 s) too; the later knock is fine
    assert [(round(t, 2), e) for t, e in plan] == [(0.0, "whoosh"), (5.25, "hit"), (9.45, "knock")]
    times = [t for t, _ in plan]
    assert all(b - a >= sfx.MIN_GAP_S for a, b in zip(times, times[1:], strict=False))


def test_plan_respects_the_limit_and_the_hook_switch():
    words = ["knock", "heart", "thunder", "scream", "clock", "whisper", "creak"]
    starts = [5.0 * (i + 1) for i in range(len(words))]
    assert len(sfx.plan_cues(words, starts, max_cues=3)) == 3
    assert sfx.plan_cues(words, starts, hook=False)[0][1] == "knock"


def test_effects_track_is_mixed_on_top_without_ducking():
    graph = audio_graph(MusicSettings(track="gen:dark", sfx=True, sfx_volume_db=-6), total=20, music_input=2, sfx_input=3)
    assert "[3:a]aformat=channel_layouts=mono,volume=-6dB[fx]" in graph
    assert graph.count("sidechaincompress") == 1 and graph.endswith("[a]") and graph.count("loudnorm") == 1
    assert audio_graph(MusicSettings(), total=20, music_input=None, sfx_input=2).startswith("[1:a]anull[pre]")


@needs_ffmpeg
def test_effects_track_renders_with_the_right_length(tmp_path):
    out = sfx.build_track(tmp_path, [(0.0, "whoosh"), (3.0, "knock"), (6.5, "heartbeat")], total=10.0, data_dir=tmp_path)
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)],
                         capture_output=True, text=True, check=True).stdout  # fmt: skip
    assert abs(float(dur) - 10.0) < 0.1


@needs_ffmpeg
def test_every_generated_effect_renders(tmp_path):
    plan = [(i * 4.0, name) for i, name in enumerate(sfx.EFFECTS)]
    assert sfx.build_track(tmp_path, plan, total=len(plan) * 4.0, data_dir=tmp_path).stat().st_size > 1000


def test_own_files_replace_generated_effects(tmp_path):
    folder = sfx.library_dir(tmp_path)
    (folder / "old-door-knock.wav").write_bytes(b"RIFF")
    assert sfx.library_file(tmp_path, "knock").name == "old-door-knock.wav"
    assert sfx.library_file(tmp_path, "thunder") is None


def test_landscape_captions_use_the_wide_frame_and_smaller_type():
    cues = cues_for("one two three four", 2.0)
    wide = to_ass(cues, "en", style=CaptionStyle(size=100), width=1920, height=1080)
    assert "PlayResX: 1920\nPlayResY: 1080" in wide and "Montserrat Black,72," in wide
    assert "Montserrat Black,100," in to_ass(cues, "en", style=CaptionStyle(size=100))


def test_format_sizes_and_quality_check():
    assert frame_size("16:9") == (1920, 1080) and frame_size("9:16") == (1080, 1920)
    base = {"duration": 40.0, "has_audio": True, "lufs": -14.0, "true_peak": -2.0, "captions": 10}
    ok = judge({**base, "width": 1920, "height": 1080, "expected_size": (1920, 1080)})
    bad = judge({**base, "width": 1080, "height": 1920, "expected_size": (1920, 1080)})
    assert ok["checks"][0]["ok"] and not bad["checks"][0]["ok"]


def test_landscape_cover_title_is_centred_and_wide():
    ass = title_ass("A very long title about the house at the end of the road", font="F", color="#FFFFFF",
                    size_px=(1280, 720))  # fmt: skip
    assert "PlayResX: 1280\nPlayResY: 720" in ass and r"\pos(640,360)" in ass and ass.count(r"\N") <= 2


def test_youtube_marks_only_vertical_videos_as_shorts():
    assert "#shorts" in build_metadata({"title": "t"}, language="en", privacy="public", publish_at=None)["snippet"]["description"]
    wide = build_metadata({"title": "t"}, language="en", privacy="public", publish_at=None, short=False)
    assert "#shorts" not in wide["snippet"]["description"]
