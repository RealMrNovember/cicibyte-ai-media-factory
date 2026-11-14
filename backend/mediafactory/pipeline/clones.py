"""Cloned voices: a short sample of a real voice (DATA_DIR/media/voices) that Chatterbox imitates.

A sample is stored as a 24 kHz mono WAV, trimmed to MAX_S seconds, and works for every language.
Uploading requires an explicit confirmation that the speaker agreed to having their voice cloned.
"""

import json
import re
import secrets
import shutil
import subprocess
import tempfile
import wave
from datetime import UTC, datetime
from pathlib import Path

AUDIO_EXT = (".wav", ".mp3", ".m4a", ".ogg", ".flac", ".aac", ".opus", ".webm")
CLONE_ID = re.compile(r"^clone-[0-9a-f]{8}$")
RATE = 24000
MIN_S, MAX_S = 5.0, 30.0


def data_dir() -> Path:
    from mediafactory.core.config import get_settings

    return Path(get_settings().data_dir)


def clones_dir(base: Path) -> Path:
    d = base / "media" / "voices"
    d.mkdir(parents=True, exist_ok=True)
    return d


def clone_path(base: Path, vid: str) -> Path | None:
    if not CLONE_ID.match(vid or ""):
        return None
    p = clones_dir(base) / f"{vid}.wav"
    return p if p.is_file() else None


def _voice(vid: str, meta: dict) -> dict:
    return {"id": vid, "path": "", "language": "any", "label": meta.get("label") or vid, "gender": "custom",
            "accent": "Clone", "quality": "high", "engine": "chatterbox", "created": meta.get("created", "")}  # fmt: skip


def get_clone(base: Path, vid: str) -> dict | None:
    p = clone_path(base, vid)
    if p is None:
        return None
    side = p.with_suffix(".json")
    return _voice(vid, json.loads(side.read_text(encoding="utf-8")) if side.exists() else {})


def list_clones(base: Path) -> list[dict]:
    return [v for p in sorted(clones_dir(base).glob("clone-*.wav")) if (v := get_clone(base, p.stem))]


def add_clone(base: Path, filename: str, stream, *, label: str, consent: bool) -> dict:
    if not consent:
        raise ValueError("confirm you have the speaker's permission to clone this voice")
    ext = Path(filename or "").suffix.lower()
    if ext not in AUDIO_EXT:
        raise ValueError(f"unsupported audio type {ext or '(none)'}; use {', '.join(AUDIO_EXT)}")
    vid = f"clone-{secrets.token_hex(4)}"
    dest = clones_dir(base) / f"{vid}.wav"
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / f"upload{ext}"
        with raw.open("wb") as f:
            shutil.copyfileobj(stream, f, length=1024 * 1024)
        proc = subprocess.run(
            [shutil.which("ffmpeg") or "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(raw), "-t", f"{MAX_S:g}",
             "-ac", "1", "-ar", str(RATE), "-c:a", "pcm_s16le", str(dest)],
            capture_output=True, timeout=120,
        )  # fmt: skip
    if proc.returncode != 0 or not dest.exists():
        dest.unlink(missing_ok=True)
        raise ValueError("could not read this audio file")
    with wave.open(str(dest)) as w:
        seconds = w.getnframes() / w.getframerate()
    if seconds < MIN_S:
        dest.unlink(missing_ok=True)
        raise ValueError(f"the sample must be at least {MIN_S:g} seconds long (got {seconds:.1f}s)")
    meta = {"label": (label or "").strip()[:60] or "My voice", "created": datetime.now(UTC).isoformat(timespec="seconds"),
            "seconds": round(seconds, 1), "consent": True}  # fmt: skip
    dest.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return _voice(vid, meta)


def remove_clone(base: Path, vid: str) -> bool:
    p = clone_path(base, vid)
    if p is None:
        return False
    p.unlink(missing_ok=True)
    p.with_suffix(".json").unlink(missing_ok=True)
    return True
