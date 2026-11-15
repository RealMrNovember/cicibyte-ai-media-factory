"""Render the video with ffmpeg (9:16 Short/Reel or 16:9): background, narration, music, effects, captions."""

import shutil
import subprocess
from pathlib import Path

from mediafactory.pipeline.music import MusicSettings, audio_graph, source_for

WIDTH, HEIGHT, FPS = 1080, 1920, 30


def ffmpeg_bin() -> str:
    found = shutil.which("ffmpeg")
    if not found:
        raise RuntimeError("ffmpeg is not installed")
    return found


def render_short(
    out_dir: Path, *, audio: str, captions_ass: str, duration: float, background: Path | None = None,
    output: str = "short.mp4", music: "MusicSettings | None" = None, data_dir: Path | None = None,
    size: tuple[int, int] = (WIDTH, HEIGHT), sfx: str | None = None,
) -> Path:  # fmt: skip
    """All file names are relative to out_dir (ffmpeg runs there, so paths need no filter escaping)."""
    WIDTH, HEIGHT = size  # noqa: N806 - same names as the module defaults
    total = round(duration + 0.6, 2)
    if background is not None:
        bg_in = ["-stream_loop", "-1", "-i", str(background)]
        bg = (
            f"[0:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,crop={WIDTH}:{HEIGHT},"
            f"fps={FPS},eq=brightness=-0.12:saturation=0.8"
        )
    else:  # moody animated gradient when no licensed clip is available yet
        bg_in = ["-f", "lavfi", "-i",
                 f"gradients=s={WIDTH}x{HEIGHT}:c0=0x07070c:c1=0x2b0a10:c2=0x0c1420:c3=0x140a1c:"
                 f"speed=0.012:duration={total}:rate={FPS}"]  # fmt: skip
        bg = "[0:v]noise=alls=6:allf=t,vignette=PI/4"
    music = music or MusicSettings()
    music_in = source_for(data_dir or out_dir, music, seconds=total) if music.track != "none" else None
    # Audio: narration (+ music ducked under it), mastered to -14 LUFS with a limiter (no clipping after AAC).
    sfx_in = ["-i", sfx] if sfx else []
    agraph = audio_graph(music, total=total, music_input=2 if music_in else None,
                         sfx_input=(3 if music_in else 2) if sfx else None)  # fmt: skip
    graph = f"{bg},ass={captions_ass}[v];{agraph}"
    cmd = [
        ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-y",
        *bg_in, "-i", audio, *(music_in or []), *sfx_in,
        "-filter_complex", graph, "-map", "[v]", "-map", "[a]", "-ar", "48000",
        "-t", str(total), "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", output,
    ]  # fmt: skip
    proc = subprocess.run(cmd, cwd=out_dir, capture_output=True, text=True, timeout=900)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {proc.stderr[-800:]}")
    return out_dir / output
