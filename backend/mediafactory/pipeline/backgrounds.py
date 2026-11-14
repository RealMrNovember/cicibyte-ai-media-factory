"""Background clip library: video files in DATA_DIR/media/backgrounds, licence/origin in a <clip>.json sidecar."""

import json
import random
import re
import shutil
import subprocess
from pathlib import Path

VIDEO_EXT = (".mp4", ".mov", ".mkv", ".webm")
SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def library_dir(data_dir: Path) -> Path:
    d = data_dir / "media" / "backgrounds"
    d.mkdir(parents=True, exist_ok=True)
    return d


def clips(data_dir: Path) -> list[Path]:
    d = library_dir(data_dir)
    return sorted(p for p in d.iterdir() if p.suffix.lower() in VIDEO_EXT and p.is_file())


def resolve(data_dir: Path, name: str) -> Path | None:
    """A clip in the library by file name; None for anything else (no path tricks)."""
    if not name or name != Path(name).name:
        return None
    p = library_dir(data_dir) / name
    return p if p.is_file() and p.suffix.lower() in VIDEO_EXT else None


def info(clip: Path) -> dict:
    side = clip.with_suffix(clip.suffix + ".json")
    meta = json.loads(side.read_text(encoding="utf-8")) if side.exists() else {}
    return {"name": clip.name, "size": clip.stat().st_size, "licence": meta.get("licence", ""),
            "source": meta.get("source", "")}  # fmt: skip


def safe_filename(original: str) -> str:
    stem, ext = Path(original).stem, Path(original).suffix.lower()
    if ext not in VIDEO_EXT:
        raise ValueError(f"unsupported video type {ext or '(none)'}; use {', '.join(VIDEO_EXT)}")
    return (SAFE_NAME.sub("-", stem).strip("-.") or "clip")[:80] + ext


def add_clip(data_dir: Path, filename: str, stream, *, licence: str, source: str = "") -> Path:
    name = safe_filename(filename)
    dest = library_dir(data_dir) / name
    n = 2
    while dest.exists():
        dest = dest.with_name(f"{Path(name).stem}-{n}{Path(name).suffix}")
        n += 1
    with dest.open("wb") as f:
        shutil.copyfileobj(stream, f, length=1024 * 1024)
    dest.with_suffix(dest.suffix + ".json").write_text(
        json.dumps({"licence": licence, "source": source}, ensure_ascii=False), encoding="utf-8"
    )
    return dest


def remove_clip(data_dir: Path, name: str) -> bool:
    clip = resolve(data_dir, name)
    if clip is None:
        return False
    for p in (clip, clip.with_suffix(clip.suffix + ".json"), thumb_path(clip)):
        p.unlink(missing_ok=True)
    return True


def thumb_path(clip: Path) -> Path:
    return clip.parent / ".thumbs" / (clip.name + ".jpg")


def thumbnail(clip: Path) -> Path:
    """A 9:16 still from the clip (cached)."""
    out = thumb_path(clip)
    if out.exists() and out.stat().st_mtime >= clip.stat().st_mtime:
        return out
    out.parent.mkdir(exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", "1", "-i", str(clip), "-frames:v", "1",
         "-vf", "scale=360:640:force_original_aspect_ratio=increase,crop=360:640", "-q:v", "4", str(out)],
        capture_output=True, timeout=60, check=False,
    )  # fmt: skip
    if not out.exists():
        raise RuntimeError("could not read a frame from this clip")
    return out


def pick_background(data_dir: Path, *, rng: random.Random | None = None) -> Path | None:
    """A random clip, avoiding the one used last time. None when the library is empty."""
    found = clips(data_dir)
    if not found:
        return None
    state = library_dir(data_dir) / ".last_used.json"
    last = json.loads(state.read_text(encoding="utf-8")).get("name") if state.exists() else None
    choices = [c for c in found if c.name != last] or found
    chosen = (rng or random).choice(choices)
    state.write_text(json.dumps({"name": chosen.name}), encoding="utf-8")
    return chosen
