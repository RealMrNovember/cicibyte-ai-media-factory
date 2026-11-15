"""One real frame of the video: the chosen background with the captions burned in by the same renderer (libass)
the final video uses. The Studio's live preview is CSS and can differ slightly in outline and line breaks; this
frame is exact."""

import subprocess
from pathlib import Path

from mediafactory.pipeline.captions import cues_for, to_ass
from mediafactory.pipeline.render import ffmpeg_bin
from mediafactory.pipeline.style import CaptionStyle, frame_size

DURATION = 2.0  # the sample caption is on screen from 0 to 2 s; the frame is taken at 0.6 s (after any intro animation)
AT = 0.6


def sample_ass(text: str, style: CaptionStyle, language: str) -> str:
    """Captions for the first `words_per_cue` words only, shown for the whole sample."""
    words = text.split()[: style.words_per_cue] or ["…"]
    cues = cues_for(" ".join(words), DURATION, words_per_cue=style.words_per_cue, lead_in=0.0)
    cues = [cues[0]] if cues else []
    if cues:
        cues[0].start, cues[0].end = 0.0, DURATION
    w, h = frame_size(style.aspect)
    ass = to_ass(cues, language, style=style, width=w, height=h)
    # Karaoke writes one line per word: keep the first (first word highlighted) and show it for the whole sample.
    head, _, events = ass.partition("\nDialogue:")
    if not events:
        return ass
    first = "Dialogue:" + events.split("\nDialogue:")[0].rstrip("\n")
    parts = first.split(",", 3)
    parts[1], parts[2] = "0:00:00.00", f"0:00:0{DURATION:.2f}"
    return head + "\n" + ",".join(parts) + "\n"


def render_frame(out_dir: Path, *, style: CaptionStyle, text: str, language: str, background: Path | None) -> Path:
    w, h = frame_size(style.aspect)
    (out_dir / "frame.ass").write_text(sample_ass(text, style, language), encoding="utf-8")
    if background is not None:
        src = ["-ss", "1", "-i", str(background)]
        vf = (f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},eq=brightness=-0.12:saturation=0.8,"
              f"ass=frame.ass")  # fmt: skip - same look as render_short
    else:
        src = ["-f", "lavfi", "-i", f"gradients=s={w}x{h}:c0=0x07070c:c1=0x2b0a10:c2=0x0c1420:c3=0x140a1c:duration={DURATION}"]
        vf = "vignette=PI/4,ass=frame.ass"
    # The ass filter needs the timeline to reach AT: decode from the start of the (seeked) input and pick that frame.
    cmd = [ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-y", *src, "-vf", f"{vf},trim=start={AT},setpts=PTS-STARTPTS",
           "-frames:v", "1", "-q:v", "3", "frame.jpg"]  # fmt: skip
    proc = subprocess.run(cmd, cwd=out_dir, capture_output=True, text=True, timeout=60)
    if proc.returncode != 0 or not (out_dir / "frame.jpg").exists():
        raise RuntimeError(f"preview frame failed: {proc.stderr[-300:]}")
    return out_dir / "frame.jpg"
