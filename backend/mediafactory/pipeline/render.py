"""Render a 9:16 Short with ffmpeg: background (clip or generated), narration audio, burned-in captions."""

import shutil
import subprocess
from pathlib import Path

WIDTH, HEIGHT, FPS = 1080, 1920, 30


def ffmpeg_bin() -> str:
    found = shutil.which("ffmpeg")
    if not found:
        raise RuntimeError("ffmpeg is not installed")
    return found


def render_short(
    out_dir: Path, *, audio: str, captions_ass: str, duration: float, background: Path | None = None,
    output: str = "short.mp4",
) -> Path:  # fmt: skip
    """All file names are relative to out_dir (ffmpeg runs there, so paths need no filter escaping)."""
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
    graph = f"{bg},ass={captions_ass}[v]"
    cmd = [
        ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-y",
        *bg_in, "-i", audio,
        "-filter_complex", graph, "-map", "[v]", "-map", "1:a",
        "-t", str(total), "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", output,
    ]  # fmt: skip
    proc = subprocess.run(cmd, cwd=out_dir, capture_output=True, text=True, timeout=900)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {proc.stderr[-800:]}")
    return out_dir / output
