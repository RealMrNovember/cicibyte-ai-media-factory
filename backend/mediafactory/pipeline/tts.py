"""Local text-to-speech with Piper (ONNX, CPU-friendly, English and Turkish voices)."""

import wave
from pathlib import Path

import httpx

VOICES = {
    "en": "en/en_US/ryan/high/en_US-ryan-high",
    "tr": "tr/tr_TR/dfki/medium/tr_TR-dfki-medium",
}
BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/"


def ensure_voice(language: str, models_dir: Path) -> Path:
    """Download the Piper voice for a language once; return the .onnx path."""
    rel = VOICES.get(language) or VOICES["en"]
    target = models_dir / "piper" / (Path(rel).name + ".onnx")
    target.parent.mkdir(parents=True, exist_ok=True)
    for suffix in (".onnx", ".onnx.json"):
        path = target.parent / (Path(rel).name + suffix)
        if path.exists() and path.stat().st_size > 0:
            continue
        tmp = path.with_suffix(path.suffix + ".part")
        with httpx.stream("GET", BASE + rel + suffix, follow_redirects=True, timeout=120) as r:
            r.raise_for_status()
            with open(tmp, "wb") as fh:
                for chunk in r.iter_bytes():
                    fh.write(chunk)
        tmp.replace(path)
    return target


def synthesize(text: str, voice_path: Path, out_wav: Path, *, length_scale: float = 1.0) -> float:
    """Write narration to a WAV file and return its duration in seconds."""
    from piper import PiperVoice, SynthesisConfig

    voice = PiperVoice.load(str(voice_path))
    with wave.open(str(out_wav), "wb") as wf:
        voice.synthesize_wav(text, wf, syn_config=SynthesisConfig(length_scale=length_scale))
    with wave.open(str(out_wav), "rb") as wf:
        return wf.getnframes() / float(wf.getframerate())
