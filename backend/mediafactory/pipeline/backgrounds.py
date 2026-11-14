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


def _meta(clip: Path) -> dict:
    side = clip.with_suffix(clip.suffix + ".json")
    try:
        return json.loads(side.read_text(encoding="utf-8")) if side.exists() else {}
    except ValueError:
        return {}


def info(clip: Path) -> dict:
    meta = _meta(clip)
    return {"name": clip.name, "size": clip.stat().st_size, "licence": meta.get("licence", ""),
            "source": meta.get("source", ""), "tags": meta.get("tags", [])}  # fmt: skip


def clean_tags(tags) -> list[str]:
    from mediafactory.sources.catalog import CATEGORIES

    allowed = set(CATEGORIES) | {"manual", "other"}
    return sorted({str(t).strip() for t in tags or [] if str(t).strip() in allowed})


def set_tags(data_dir: Path, name: str, tags) -> list[str] | None:
    clip = resolve(data_dir, name)
    if clip is None:
        return None
    meta = {**_meta(clip), "tags": clean_tags(tags)}
    clip.with_suffix(clip.suffix + ".json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return meta["tags"]


def story_category(session, item) -> str | None:
    """The topic of a story (from its source), used to pick a matching background clip."""
    if item is None or item.source_type == "manual" or item.source_id is None:
        return "manual"
    from mediafactory.db.models import SourceConnector
    from mediafactory.sources.catalog import category_for

    c = session.get(SourceConnector, item.source_id)
    return category_for(c.adapter, c.params) if c else None


def safe_filename(original: str) -> str:
    stem, ext = Path(original).stem, Path(original).suffix.lower()
    if ext not in VIDEO_EXT:
        raise ValueError(f"unsupported video type {ext or '(none)'}; use {', '.join(VIDEO_EXT)}")
    return (SAFE_NAME.sub("-", stem).strip("-.") or "clip")[:80] + ext


def add_clip(data_dir: Path, filename: str, stream, *, licence: str, source: str = "", tags=None) -> Path:
    name = safe_filename(filename)
    dest = library_dir(data_dir) / name
    n = 2
    while dest.exists():
        dest = dest.with_name(f"{Path(name).stem}-{n}{Path(name).suffix}")
        n += 1
    with dest.open("wb") as f:
        shutil.copyfileobj(stream, f, length=1024 * 1024)
    dest.with_suffix(dest.suffix + ".json").write_text(
        json.dumps({"licence": licence, "source": source, "tags": clean_tags(tags)}, ensure_ascii=False), encoding="utf-8"
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


def pick_background(data_dir: Path, *, rng: random.Random | None = None, category: str | None = None) -> Path | None:
    """A random clip, avoiding the one used last time. With a category, clips tagged with it are preferred;
    if none is tagged with it, any clip is used. None when the library is empty."""
    found = clips(data_dir)
    if not found:
        return None
    if category:
        tagged = [c for c in found if category in _meta(c).get("tags", [])]
        found = tagged or found
    state = library_dir(data_dir) / ".last_used.json"
    last = json.loads(state.read_text(encoding="utf-8")).get("name") if state.exists() else None
    choices = [c for c in found if c.name != last] or found
    chosen = (rng or random).choice(choices)
    state.write_text(json.dumps({"name": chosen.name}), encoding="utf-8")
    return chosen
