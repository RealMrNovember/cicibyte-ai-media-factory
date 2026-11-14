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


def test_resolve_refuses_paths(tmp_path):
    from mediafactory.pipeline.backgrounds import resolve

    (library_dir(tmp_path) / "a.mp4").write_bytes(b"x")
    assert resolve(tmp_path, "a.mp4").name == "a.mp4"
    assert resolve(tmp_path, "../a.mp4") is None
    assert resolve(tmp_path, "missing.mp4") is None


def test_safe_filename():
    import pytest

    from mediafactory.pipeline.backgrounds import safe_filename

    assert safe_filename("Minecraft Parkour #1 (4K).MP4") == "Minecraft-Parkour-1-4K.mp4"
    with pytest.raises(ValueError):
        safe_filename("evil.exe")


def test_upload_list_delete_via_api(client, tmp_path, monkeypatch):
    import io

    from mediafactory.api.routes import backgrounds as route
    from mediafactory.pipeline import backgrounds as lib

    monkeypatch.setattr(route, "_data", lambda: tmp_path)
    monkeypatch.setattr(lib, "thumbnail", lambda clip: clip)
    h = {"X-MF-Client": "1"}
    r = client.post("/api/backgrounds", headers=h, data={"licence": "Mixkit free licence"},
                    files={"file": ("parkour.mp4", io.BytesIO(b"fake"), "video/mp4")})  # fmt: skip
    assert r.status_code == 201 and r.json()["licence"] == "Mixkit free licence"
    assert [c["name"] for c in client.get("/api/backgrounds").json()["items"]] == ["parkour.mp4"]
    assert client.delete("/api/backgrounds/parkour.mp4", headers=h).status_code == 200
    assert client.get("/api/backgrounds").json()["items"] == []
