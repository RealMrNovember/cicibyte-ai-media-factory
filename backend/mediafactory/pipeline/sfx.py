"""Sound effects: short cues (door knocks, heartbeat, thunder…) placed where the narration mentions them.

Effects are synthesised by ffmpeg (no copyright), or taken from your own files in DATA_DIR/media/sfx whose
file name contains the effect's name (e.g. "door-knock.wav" for "knock"). The cues are mixed into one
sfx.wav track, which the renderer lays over the narration and music.
"""

import random
import re
import subprocess
from pathlib import Path

from mediafactory.pipeline.music import AUDIO_EXT

# name -> (English, Turkish, ffmpeg lavfi source)
EFFECTS: dict[str, tuple[str, str, str]] = {
    "whoosh": ("Whoosh", "Vuuş", "anoisesrc=d=1.2:c=pink:a=0.7,highpass=f=300,lowpass=f=3500,afade=t=in:d=0.7,afade=t=out:st=0.7:d=0.5"),
    "knock": ("Knocks", "Kapı vuruşu",
              "aevalsrc='0.9*sin(2*PI*170*t)*exp(-55*mod(t\\,0.32))*lt(t\\,0.95)':s=48000:d=1.1,lowpass=f=900"),
    "creak": ("Creak", "Gıcırtı",
              "aevalsrc='0.45*sin(2*PI*(210+90*sin(2*PI*2.5*t))*t)*(0.55+0.45*sin(2*PI*13*t))':s=48000:d=1.6,"
              "bandpass=f=650:w=500,afade=t=in:d=0.2,afade=t=out:st=1.1:d=0.5"),
    "heartbeat": ("Heartbeat", "Kalp atışı",
                  "aevalsrc='0.95*sin(2*PI*48*t)*(exp(-16*mod(t\\,0.85))+0.8*gte(mod(t\\,0.85)\\,0.27)"
                  "*exp(-16*(mod(t\\,0.85)-0.27)))':s=48000:d=2.55,lowpass=f=140"),
    "tick": ("Clock ticks", "Saat tik takı", "aevalsrc='0.7*sin(2*PI*2300*t)*exp(-180*mod(t\\,0.5))':s=48000:d=2.5,highpass=f=900"),
    "whisper": ("Whisper", "Fısıltı",
                "anoisesrc=d=1.6:c=white:a=0.3,bandpass=f=2600:w=1800,tremolo=f=8:d=0.7,afade=t=in:d=0.3,afade=t=out:st=1.0:d=0.6"),
    "thunder": ("Thunder", "Gök gürültüsü", "anoisesrc=d=3.2:c=brown:a=0.95,lowpass=f=280,afade=t=in:d=0.04,afade=t=out:st=0.4:d=2.8"),
    "hit": ("Impact", "Darbe",
            "aevalsrc='0.95*sin(2*PI*(70-35*t)*t)*exp(-2.8*t)':s=48000:d=2.2,lowpass=f=220"),
}  # fmt: skip

# Words (English and Turkish stems) that call for an effect. Checked on lower-cased words without punctuation.
KEYWORDS: dict[str, tuple[str, ...]] = {
    "knock": ("knock", "knocked", "knocking", "vurdu", "vuruyor", "vuruş", "tıkırtı", "tık"),
    "creak": ("creak", "creaked", "creaking", "squeak", "gıcır", "gıcırdı", "gıcırtı", "gıcırdadı"),
    "heartbeat": ("heart", "heartbeat", "pulse", "kalbim", "kalp", "kalbimin", "nabzım", "nabız"),
    "tick": ("clock", "ticking", "tick", "tik", "tiktak"),
    "whisper": ("whisper", "whispered", "whispering", "fısıltı", "fısıldadı", "fısıldıyor", "fısıltıyla"),
    "thunder": ("thunder", "lightning", "storm", "gökgürültüsü", "şimşek", "şimşekler", "fırtına", "fırtınada"),
    "hit": ("scream", "screamed", "slam", "slammed", "bang", "crash", "çığlık", "çarptı", "çarpıldı", "patladı"),
}
MIN_GAP_S = 3.0  # never two cues closer than this
_WORD = re.compile(r"[^\W_]+", re.UNICODE)


def library_dir(data_dir: Path) -> Path:
    d = data_dir / "media" / "sfx"
    d.mkdir(parents=True, exist_ok=True)
    return d


def library_file(data_dir: Path, effect: str) -> Path | None:
    files = [p for p in library_dir(data_dir).iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXT and effect in p.stem.lower()]
    return random.choice(files) if files else None


def effect_for(word: str) -> str | None:
    w = " ".join(_WORD.findall(word.casefold()))
    for effect, words in KEYWORDS.items():
        if w in words:
            return effect
    return None


def plan_cues(words: list[str], starts: list[float], *, max_cues: int = 6, hook: bool = True) -> list[tuple[float, str]]:
    """(time, effect) pairs: a whoosh under the hook, then effects where the words mention them, spaced out."""
    cues: list[tuple[float, str]] = [(0.0, "whoosh")] if hook else []
    used: set[str] = set()
    for word, t in zip(words, starts, strict=False):
        effect = effect_for(word)
        if effect is None or effect in used or any(abs(t - c) < MIN_GAP_S for c, _ in cues):
            continue
        cues.append((max(0.0, t - 0.15), effect))  # slightly before the word, like a real foley cue
        used.add(effect)
        if len(cues) >= max_cues:
            break
    return cues


def build_track(out_dir: Path, cues: list[tuple[float, str]], *, total: float, data_dir: Path, output: str = "sfx.wav") -> Path | None:
    """Mix the cues into one track of `total` seconds; None when there is nothing to add."""
    if not cues:
        return None
    inputs, chains = [], []
    for i, (t, effect) in enumerate(cues):
        own = library_file(data_dir, effect)
        inputs += ["-i", str(own)] if own else ["-f", "lavfi", "-i", EFFECTS[effect][2]]
        ms = int(t * 1000)
        chains.append(f"[{i}:a]aformat=sample_rates=48000:channel_layouts=mono,atrim=0:4,adelay={ms}:all=1[c{i}]")
    mix = "".join(f"[c{i}]" for i in range(len(cues)))
    graph = ";".join(chains) + f";{mix}amix=inputs={len(cues)}:duration=longest:normalize=0,apad=whole_dur={total:.2f}[s]"
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs, "-filter_complex", graph, "-map", "[s]",
           "-t", f"{total:.2f}", "-ar", "48000", "-ac", "1", output]  # fmt: skip
    proc = subprocess.run(cmd, cwd=out_dir, capture_output=True, text=True, timeout=180)
    if proc.returncode != 0:
        raise RuntimeError(f"sound effects failed: {proc.stderr[-400:]}")
    return out_dir / output
