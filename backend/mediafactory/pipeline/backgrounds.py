"""Background clip library: video files in DATA_DIR/media/backgrounds (licence/origin noted in a sidecar)."""

import json
import random
from pathlib import Path

VIDEO_EXT = (".mp4", ".mov", ".mkv", ".webm")


def library_dir(data_dir: Path) -> Path:
    d = data_dir / "media" / "backgrounds"
    d.mkdir(parents=True, exist_ok=True)
    return d


def pick_background(data_dir: Path, *, rng: random.Random | None = None) -> Path | None:
    """A random clip, avoiding the one used last time. None when the library is empty."""
    d = library_dir(data_dir)
    clips = sorted(p for p in d.iterdir() if p.suffix.lower() in VIDEO_EXT and p.is_file())
    if not clips:
        return None
    state = d / ".last_used.json"
    last = json.loads(state.read_text(encoding="utf-8")).get("name") if state.exists() else None
    choices = [c for c in clips if c.name != last] or clips
    chosen = (rng or random).choice(choices)
    state.write_text(json.dumps({"name": chosen.name}), encoding="utf-8")
    return chosen
