import shutil
import subprocess

import pytest

from mediafactory.pipeline.qc import judge, parse_ffmpeg_report
from mediafactory.pipeline.thumbnail import frame_score, title_ass

REPORT = """
[silencedetect @ 0x1] silence_start: 3.5
[silencedetect @ 0x1] silence_end: 6.9 | silence_duration: 3.4
[blackdetect @ 0x2] black_start:10 black_end:12.5 black_duration:2.5
[Parsed_loudnorm_0 @ 0x3]
{
\t"input_i" : "-15.20",
\t"input_tp" : "-1.60",
\t"input_lra" : "3.00"
}
"""

GOOD = {"width": 1080, "height": 1920, "duration": 41.0, "has_audio": True, "lufs": -14.3, "true_peak": -1.6,
        "silences": [], "blacks": [], "captions": 30}  # fmt: skip


def test_parse_report():
    m = parse_ffmpeg_report(REPORT)
    assert m["lufs"] == -15.2 and m["true_peak"] == -1.6
    assert m["silences"] == [3.4] and m["blacks"] == [2.5]


def test_good_video_passes():
    r = judge(GOOD)
    assert r["passed"] and all(c["ok"] for c in r["checks"])


@pytest.mark.parametrize("change, failing", [
    ({"width": 1920, "height": 1080}, "resolution"),
    ({"duration": 4.0}, "duration"),
    ({"has_audio": False}, "audio"),
    ({"lufs": -31.0}, "loudness"),
    ({"true_peak": 0.4}, "peak"),
    ({"silences": [3.4]}, "silence"),
    ({"blacks": [2.5]}, "black"),
    ({"captions": 0}, "captions"),
])  # fmt: skip
def test_each_problem_is_reported(change, failing):
    r = judge({**GOOD, **change})
    assert not r["passed"]
    assert [c["name"] for c in r["checks"] if not c["ok"]] == [failing]


def test_frame_score_prefers_lively_frames():
    import numpy as np

    flat_dark = np.full((192, 108, 3), 8, dtype=np.uint8)
    rng = np.random.default_rng(1)
    lively = rng.integers(40, 220, size=(192, 108, 3), dtype=np.uint8)
    assert frame_score(lively) > frame_score(flat_dark)


def test_title_ass_wraps_and_escapes():
    ass = title_ass("The {door} opened by itself at three in the morning", font="Bebas Neue", color="#FFD84D", upper=True)
    assert "Bebas Neue" in ass and "{door}" not in ass and "THE (DOOR)" in ass
    assert "\\N" in ass  # long titles are broken into lines


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")
def test_thumbnail_and_measure_on_real_files(tmp_path):
    from mediafactory.pipeline.qc import measure
    from mediafactory.pipeline.style import CaptionStyle
    from mediafactory.pipeline.thumbnail import make_thumbnail

    clip = tmp_path / "clip.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=1280x720:d=4:r=25",
                    "-f", "lavfi", "-i", "sine=f=220:d=4", "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(clip)],
                   check=True)  # fmt: skip
    thumb = make_thumbnail(tmp_path, background=clip, title="Something is in the attic", style=CaptionStyle(), duration=4.0)
    assert thumb.exists() and thumb.stat().st_size > 10_000
    m = measure(clip)
    assert m["width"] == 1280 and m["has_audio"] and m["lufs"] is not None


def test_auto_approve_needs_passing_qc(db, monkeypatch):
    import mediafactory.pipeline.make as make_mod
    from mediafactory.db.models import JobStageRun, ProductionJob
    from mediafactory.pipeline import handlers
    from mediafactory.queue.registry import StageContext

    for qc_ok, expected in ((True, "approved"), (False, "needs_review")):
        monkeypatch.setattr(make_mod, "make_short", lambda s, i, **kw: {"video": "v", "qc": {"passed": qc_ok, "checks": []}})
        job = ProductionJob(status="discovered", language="en", payload={"auto_approve": True})
        db.add(job)
        db.flush()
        run = JobStageRun(job_id=job.id, stage="make_short", job_class="render", inputs={"item_id": 1})
        db.add(run)
        db.flush()
        assert handlers.make_short_stage(StageContext(db, job, run, lambda m: None, lambda: False)).next_status == expected


def test_long_title_shrinks_instead_of_being_cut():
    ass = title_ass("My apartment uses exactly nine gallons of water at three every single night", font="F", color="#FFFFFF")
    assert "NIGHT" in ass and ",150," not in ass
