"""Word-timed captions (estimated from the narration audio length) as ASS (burned in) and SRT/VTT."""

import re
from dataclasses import dataclass

WORDS_PER_CAPTION = 3


@dataclass
class Cue:
    start: float
    end: float
    text: str


def upper(text: str, language: str) -> str:
    """Language-aware upper case (Turkish dotted/dotless i)."""
    if language == "tr":
        text = text.replace("i", "İ").replace("ı", "I")
    return text.upper()


def cues_for(narration: str, duration: float, *, lead_in: float = 0.15) -> list[Cue]:
    words = re.findall(r"\S+", narration)
    if not words:
        return []
    weights = [len(w) + 2 + (6 if w[-1] in ".!?" else 3 if w[-1] in ",;:" else 0) for w in words]
    usable = max(0.5, duration - lead_in)
    per = usable / sum(weights)
    cues, t = [], lead_in
    for i in range(0, len(words), WORDS_PER_CAPTION):
        group = words[i : i + WORDS_PER_CAPTION]
        span = sum(weights[i : i + WORDS_PER_CAPTION]) * per
        cues.append(Cue(t, t + span, " ".join(group)))
        t += span
    return cues


def _ass_time(s: float) -> str:
    h, rem = divmod(max(0.0, s), 3600)
    m, sec = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{sec:05.2f}"


def _srt_time(s: float, sep: str = ",") -> str:
    ms = int(round(max(0.0, s) * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    sec, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{sec:02d}{sep}{ms:03d}"


def to_ass(cues: list[Cue], language: str, *, font: str = "Arial", width: int = 1080, height: int = 1920) -> str:
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{font},96,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,7,3,5,80,80,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for c in cues:
        text = upper(c.text, language).replace("{", "(").replace("}", ")")
        lines.append(f"Dialogue: 0,{_ass_time(c.start)},{_ass_time(c.end)},Cap,,0,0,0,,{{\\fad(60,60)}}{text}")
    return header + "\n".join(lines) + "\n"


def to_srt(cues: list[Cue]) -> str:
    return "\n".join(f"{i}\n{_srt_time(c.start)} --> {_srt_time(c.end)}\n{c.text}\n" for i, c in enumerate(cues, 1))


def to_vtt(cues: list[Cue]) -> str:
    body = "\n".join(f"{_srt_time(c.start, '.')} --> {_srt_time(c.end, '.')}\n{c.text}\n" for c in cues)
    return "WEBVTT\n\n" + body
