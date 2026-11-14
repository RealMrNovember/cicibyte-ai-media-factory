"""Background music: your own tracks (DATA_DIR/media/music) or royalty-free ambiences synthesised by ffmpeg,
mixed under the narration with ducking (music dips while the narrator speaks) and fades."""

import json
import random
import re
import shutil
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

AUDIO_EXT = (".mp3", ".wav", ".ogg", ".m4a", ".flac", ".aac", ".opus")
SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")

# Pure synthesis (sine drones, pulses and pads), so there is no copyright in them.
GENERATED = {
    "gen:dark": ("Dark drone", "Karanlık uğultu",
                 "aevalsrc='0.22*sin(2*PI*55*t)*(0.6+0.4*sin(2*PI*0.07*t))+0.14*sin(2*PI*82.4*t)*(0.5+0.5*sin(2*PI*0.05*t+1))"
                 "+0.07*sin(2*PI*110.3*t)':s=48000:d={d},lowpass=f=700,aecho=0.8:0.6:180|360:0.35|0.2"),
    "gen:tension": ("Tension pulse", "Gerilim nabzı",
                    "aevalsrc='0.35*sin(2*PI*62*t)*pow(0.5+0.5*sin(2*PI*1.15*t)\\,6)+0.08*sin(2*PI*124*t)"
                    "*(0.5+0.5*sin(2*PI*0.09*t))':s=48000:d={d},lowpass=f=900,aecho=0.8:0.5:90:0.3"),
    "gen:mystery": ("Mystery pad", "Gizem",
                    "aevalsrc='(0.12*sin(2*PI*110*t)+0.1*sin(2*PI*130.81*t)+0.08*sin(2*PI*164.81*t)+0.04*sin(2*PI*220.4*t))"
                    "*(0.6+0.4*sin(2*PI*0.08*t))':s=48000:d={d},lowpass=f=1200,aecho=0.8:0.7:250|500:0.4|0.25"),
}  # fmt: skip


class MusicSettings(BaseModel):
    track: str = Field(default="none", max_length=120, description='"none", "random", "gen:…" or a library file')
    volume_db: int = Field(default=-18, ge=-35, le=-6)
    ducking: bool = True

    @field_validator("track")
    @classmethod
    def _track(cls, v: str) -> str:
        if v in ("none", "random") or v in GENERATED:
            return v
        if v != Path(v).name or Path(v).suffix.lower() not in AUDIO_EXT:
            raise ValueError("unknown music track")
        return v


def library_dir(data_dir: Path) -> Path:
    d = data_dir / "media" / "music"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _files(data_dir: Path) -> list[Path]:
    return sorted(p for p in library_dir(data_dir).iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXT)


def tracks(data_dir: Path) -> list[dict]:
    out = []
    for p in _files(data_dir):
        side = p.with_suffix(p.suffix + ".json")
        meta = json.loads(side.read_text(encoding="utf-8")) if side.exists() else {}
        out.append({"name": p.name, "size": p.stat().st_size, "licence": meta.get("licence", ""), "source": meta.get("source", "")})
    return out


def resolve(data_dir: Path, name: str) -> Path | None:
    if not name or name != Path(name).name:
        return None
    p = library_dir(data_dir) / name
    return p if p.is_file() and p.suffix.lower() in AUDIO_EXT else None


def add_track(data_dir: Path, filename: str, stream, *, licence: str = "", source: str = "") -> Path:
    stem, ext = Path(filename).stem, Path(filename).suffix.lower()
    if ext not in AUDIO_EXT:
        raise ValueError(f"unsupported audio type {ext or '(none)'}; use {', '.join(AUDIO_EXT)}")
    name = (SAFE_NAME.sub("-", stem).strip("-.") or "track")[:80] + ext
    dest, n = library_dir(data_dir) / name, 2
    while dest.exists():
        dest, n = dest.with_name(f"{Path(name).stem}-{n}{ext}"), n + 1
    with dest.open("wb") as f:
        shutil.copyfileobj(stream, f, length=1024 * 1024)
    dest.with_suffix(dest.suffix + ".json").write_text(json.dumps({"licence": licence, "source": source}), encoding="utf-8")
    return dest


def remove_track(data_dir: Path, name: str) -> bool:
    p = resolve(data_dir, name)
    if p is None:
        return False
    p.unlink(missing_ok=True)
    p.with_suffix(p.suffix + ".json").unlink(missing_ok=True)
    return True


def source_for(data_dir: Path, settings: MusicSettings, *, seconds: float) -> list[str] | None:
    """ffmpeg input arguments for the chosen music, or None for no music."""
    track = settings.track
    if track == "none":
        return None
    if track in GENERATED:
        return ["-f", "lavfi", "-i", GENERATED[track][2].format(d=round(seconds, 2))]
    path = random.choice(_files(data_dir)) if track == "random" and _files(data_dir) else resolve(data_dir, track)
    return ["-stream_loop", "-1", "-i", str(path)] if path else None


MASTER = "loudnorm=I=-14:TP=-2:LRA=11,alimiter=limit=0.75:level=false"


def audio_graph(settings: MusicSettings, *, total: float, music_input: int | None) -> str:
    """filter_complex chain producing [a]: narration (input 1), optionally mixed with music, then mastered."""
    if music_input is None:
        return f"[1:a]{MASTER}[a]"
    fade_out = max(0.0, total - 2.0)
    m = (f"[{music_input}:a]aformat=channel_layouts=mono,volume={settings.volume_db}dB,"
         f"afade=t=in:d=1.5,afade=t=out:st={fade_out:.2f}:d=2[m]")  # fmt: skip
    if settings.ducking:
        return (f"{m};[1:a]asplit=2[nv][nsc];[m][nsc]sidechaincompress=threshold=0.02:ratio=8:attack=30:release=500[md];"
                f"[nv][md]amix=inputs=2:duration=first:normalize=0,{MASTER}[a]")  # fmt: skip
    return f"{m};[1:a][m]amix=inputs=2:duration=first:normalize=0,{MASTER}[a]"
