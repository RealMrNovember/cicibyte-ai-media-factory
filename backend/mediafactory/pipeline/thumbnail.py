"""Cover image for a Short: the liveliest clean frame of the background (no captions) with a big title."""

import json
import shutil
import subprocess
import textwrap
from pathlib import Path

from mediafactory.pipeline.captions import upper
from mediafactory.pipeline.style import FONTS, CaptionStyle, ass_colour

SAMPLES = 8


def _bin(name: str) -> str:
    return shutil.which(name) or name


def frame_score(rgb) -> float:
    """Higher for frames with contrast and mid brightness (good thumbnails), lower for flat/dark ones."""
    import numpy as np

    gray = rgb.astype(np.float32).mean(axis=2)
    brightness = gray.mean() / 255.0
    return float(gray.std() / 64.0 + 1.0 - abs(brightness - 0.5) * 2.0)


def _clip_seconds(clip: Path) -> float:
    out = subprocess.run([_bin("ffprobe"), "-v", "error", "-show_entries", "format=duration", "-of", "json", str(clip)],
                         capture_output=True, text=True, timeout=30)  # fmt: skip
    try:
        return float(json.loads(out.stdout)["format"]["duration"])
    except (ValueError, KeyError):
        return 0.0


def best_time(clip: Path, duration: float) -> float:
    import numpy as np

    length = min(_clip_seconds(clip) or duration, max(duration, 1.0))
    best, best_t = -1.0, 0.0
    for i in range(SAMPLES):
        t = length * (i + 0.5) / SAMPLES
        raw = subprocess.run([_bin("ffmpeg"), "-hide_banner", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(clip),
                              "-frames:v", "1", "-vf", "scale=108:192", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                             capture_output=True, timeout=30).stdout  # fmt: skip
        if len(raw) != 108 * 192 * 3:
            continue
        score = frame_score(np.frombuffer(raw, dtype=np.uint8).reshape(192, 108, 3))
        if score > best:
            best, best_t = score, t
    return best_t


def title_ass(title: str, *, font: str, color: str, upper_case: bool = True, upper_lang: str = "en",
              size_px: tuple[int, int] = (1080, 1920), **kw) -> str:  # fmt: skip
    upper_case = kw.pop("upper", upper_case)
    WIDTH, HEIGHT = size_px  # noqa: N806
    landscape = WIDTH > HEIGHT
    text = (upper(title, upper_lang) if upper_case else title).replace("{", "(").replace("}", ")").replace("\\", "/")
    # Shrink the type for longer titles so the whole title fits (5 lines tall, 3 lines wide).
    steps = ((20, 130), (24, 112), (30, 92), (36, 78)) if landscape else ((14, 150), (16, 132), (19, 112), (22, 96), (26, 82))
    max_lines = 3 if landscape else 5
    for width, size in steps:
        lines = textwrap.wrap(text, width=width)
        if len(lines) <= max_lines:
            break
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(".,;:!? ") + "…"
    return (
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {WIDTH}\nPlayResY: {HEIGHT}\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, "
        "Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
        "MarginR, MarginV, Encoding\n"
        f"Style: T,{font},{size},{ass_colour(color)},&H000000FF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,10,6,5,60,60,0,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        f"Dialogue: 0,0:00:00.00,0:00:10.00,T,,0,0,0,,{{\\pos({WIDTH // 2},{int(HEIGHT * (0.5 if landscape else 0.36))})}}"
        + "\\N".join(lines) + "\n"
    )


def make_thumbnail(
    out_dir: Path, *, background: Path | None, title: str, style: CaptionStyle, duration: float, language: str = "en",
    output: str = "thumbnail.jpg",
) -> Path:  # fmt: skip
    WIDTH, HEIGHT = (1280, 720) if style.aspect == "16:9" else (1080, 1920)  # noqa: N806 - YouTube's landscape cover size
    (out_dir / "title.ass").write_text(
        title_ass(title, font=FONTS[style.font], color=style.highlight_color, upper_case=style.uppercase, upper_lang=language,
                  size_px=(WIDTH, HEIGHT)),
        encoding="utf-8",
    )
    fit = f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,crop={WIDTH}:{HEIGHT}"
    if background is not None:
        src = ["-ss", f"{best_time(background, duration):.2f}", "-i", str(background)]
        vf = f"{fit},eq=brightness=-0.06:saturation=1.05,vignette=PI/5,ass=title.ass"
    else:
        src = ["-f", "lavfi", "-i", f"gradients=s={WIDTH}x{HEIGHT}:c0=0x07070c:c1=0x2b0a10:c2=0x0c1420:c3=0x140a1c:duration=1"]
        vf = "vignette=PI/4,ass=title.ass"
    proc = subprocess.run([_bin("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", *src, "-frames:v", "1", "-vf", vf,
                           "-q:v", "3", output], cwd=out_dir, capture_output=True, text=True, timeout=120)  # fmt: skip
    if proc.returncode != 0 or not (out_dir / output).exists():
        raise RuntimeError(f"thumbnail failed: {proc.stderr[-400:]}")
    return out_dir / output
