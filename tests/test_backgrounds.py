import random

from mediafactory.pipeline.backgrounds import library_dir, pick_background


def test_empty_library_returns_none(tmp_path):
    assert pick_background(tmp_path) is None


def test_never_repeats_last_clip(tmp_path):
    d = library_dir(tmp_path)
    for name in ("a.mp4", "b.mp4"):
        (d / name).write_bytes(b"x")
    (d / "notes.txt").write_text("licence")
    rng = random.Random(1)
    picks = [pick_background(tmp_path, rng=rng).name for _ in range(6)]
    assert all(x != y for x, y in zip(picks, picks[1:], strict=False))
    assert set(picks) == {"a.mp4", "b.mp4"}
