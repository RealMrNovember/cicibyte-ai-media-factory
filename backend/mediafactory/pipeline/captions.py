"""Word-timed captions (estimated from the narration audio length) as ASS (burned in) and SRT/VTT."""

import re
from dataclasses import dataclass, field

from mediafactory.pipeline.style import FONTS, CaptionStyle, ass_colour

WORDS_PER_CAPTION = 3


@dataclass
class Cue:
    start: float
    end: float
    text: str
    words: list[tuple[float, float, str]] = field(default_factory=list)


def upper(text: str, language: str) -> str:
    """Language-aware upper case (Turkish dotted/dotless i)."""
    if language == "tr":
        text = text.replace("i", "İ").replace("ı", "I")
    return text.upper()


def cues_for(
    narration: str, duration: float, *, words_per_cue: int = WORDS_PER_CAPTION, lead_in: float = 0.15,
    times: list[tuple[float, float]] | None = None,
) -> list[Cue]:
    """Caption cues; `times` are real per-word timings (from whisper), otherwise timing is estimated."""
    words = re.findall(r"\S+", narration)
    if not words:
        return []
    if times is not None:
        if len(times) != len(words):
            raise ValueError("one timing per narration word is required")
        timed = [(s, e, w) for (s, e), w in zip(times, words, strict=True)]
    else:
        weights = [len(w) + 2 + (6 if w[-1] in ".!?" else 3 if w[-1] in ",;:" else 0) for w in words]
        per = max(0.5, duration - lead_in) / sum(weights)
        timed, t = [], lead_in
        for w, wt in zip(words, weights, strict=True):
            timed.append((t, t + wt * per, w))
            t += wt * per
    cues = []
    for i in range(0, len(timed), words_per_cue):
        group = timed[i : i + words_per_cue]
        cues.append(Cue(group[0][0], group[-1][1], " ".join(w for _, _, w in group), group))
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


def _clean(text: str) -> str:
    return text.replace("{", "(").replace("}", ")").replace("\\", "/")


INTRO = {
    "none": "",
    "fade": r"\fad(90,60)",
    "pop": r"\fscx70\fscy70\t(0,110,\fscx100\fscy100)",
    "slide_up": r"\fad(60,0)",
    "karaoke": "",
}


def to_ass(
    cues: list[Cue], language: str, *, style: CaptionStyle | None = None, width: int = 1080, height: int = 1920
) -> str:
    st = style or CaptionStyle()
    x, y = width // 2, round(height * st.position / 100)
    primary, hi = ass_colour(st.color), ass_colour(st.highlight_color)
    header = (
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {width}\nPlayResY: {height}\nWrapStyle: 0\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
        "MarginR, MarginV, Encoding\n"
        f"Style: Cap,{FONTS[st.font]},{st.size},{primary},&H000000FF,{ass_colour(st.outline_color)},&H80000000,"
        f"-1,0,0,0,100,100,0,0,1,{st.outline},{st.shadow},5,70,70,0,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    case = (lambda s: upper(s, language)) if st.uppercase else (lambda s: s)
    pos = rf"\move({x},{y + 60},{x},{y},0,140)" if st.animation == "slide_up" else rf"\pos({x},{y})"
    lines = []
    for c in cues:
        if st.animation == "karaoke" and c.words:
            words = [_clean(case(w)) for _, _, w in c.words]
            for i, (ws, we, _) in enumerate(c.words):
                end = c.words[i + 1][0] if i + 1 < len(c.words) else we
                text = " ".join(
                    "{\\c" + hi + "&}" + w + "{\\c" + primary + "&}" if j == i else w for j, w in enumerate(words)
                )
                lines.append(f"Dialogue: 0,{_ass_time(ws)},{_ass_time(end)},Cap,,0,0,0,,{{\\pos({x},{y})}}{text}")
            continue
        tags = "{" + pos + INTRO[st.animation] + "}"
        lines.append(f"Dialogue: 0,{_ass_time(c.start)},{_ass_time(c.end)},Cap,,0,0,0,,{tags}{_clean(case(c.text))}")
    return header + "\n".join(lines) + "\n"


def to_srt(cues: list[Cue]) -> str:
    return "\n".join(f"{i}\n{_srt_time(c.start)} --> {_srt_time(c.end)}\n{c.text}\n" for i, c in enumerate(cues, 1))


def to_vtt(cues: list[Cue]) -> str:
    body = "\n".join(f"{_srt_time(c.start, '.')} --> {_srt_time(c.end, '.')}\n{c.text}\n" for c in cues)
    return "WEBVTT\n\n" + body
