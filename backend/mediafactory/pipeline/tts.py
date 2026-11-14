"""Local text-to-speech with Piper (ONNX, CPU-friendly), a catalog of English and Turkish voices,
speed (Piper length scale) and pitch (ffmpeg, duration kept)."""

import json
import os
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import httpx

BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/"


def _v(vid: str, label: str, gender: str, accent: str) -> tuple[str, dict]:
    lang_code, name, quality = vid.split("-", 2)
    family = lang_code.split("_")[0]
    return vid, {"id": vid, "path": f"{family}/{lang_code}/{name}/{quality}/{vid}", "language": family,
                 "label": label, "gender": gender, "accent": accent, "quality": quality, "engine": "piper"}  # fmt: skip


def _cbx(vid: str, language: str, gender: str) -> tuple[str, dict]:
    return vid, {"id": vid, "path": "", "language": language, "label": "Chatterbox (natural)", "gender": gender,
                 "accent": "Chatterbox", "quality": "high", "engine": "chatterbox"}  # fmt: skip


# Single-speaker voices only (multi-speaker models need a speaker id and vary a lot in quality).
VOICE_CATALOG: dict[str, dict] = dict([
    _v("en_US-ryan-high", "Ryan", "male", "US"),
    _v("en_US-joe-medium", "Joe", "male", "US"),
    _v("en_US-john-medium", "John", "male", "US"),
    _v("en_US-norman-medium", "Norman", "male", "US"),
    _v("en_US-bryce-medium", "Bryce", "male", "US"),
    _v("en_US-kusal-medium", "Kusal", "male", "US"),
    _v("en_US-hfc_male-medium", "HFC male", "male", "US"),
    _v("en_US-lessac-high", "Lessac", "female", "US"),
    _v("en_US-ljspeech-high", "LJ", "female", "US"),
    _v("en_US-amy-medium", "Amy", "female", "US"),
    _v("en_US-kristin-medium", "Kristin", "female", "US"),
    _v("en_US-kathleen-medium", "Kathleen", "female", "US"),
    _v("en_US-hfc_female-medium", "HFC female", "female", "US"),
    _v("en_GB-alan-medium", "Alan", "male", "UK"),
    _v("en_GB-northern_english_male-medium", "Northern English", "male", "UK"),
    _v("en_GB-cori-high", "Cori", "female", "UK"),
    _v("en_GB-jenny_dioco-medium", "Jenny", "female", "UK"),
    _v("en_GB-alba-medium", "Alba", "female", "Scottish"),
    _v("tr_TR-dfki-medium", "DFKI", "male", "TR"),
    # Chatterbox Multilingual (Resemble AI, MIT): far more natural, slower on CPU; needs its own virtualenv.
    _cbx("tr-chatterbox", "tr", "neutral"),
    _cbx("en-chatterbox", "en", "neutral"),
])  # fmt: skip
WORKER = Path(__file__).with_name("chatterbox_worker.py")


def chatterbox_python() -> str | None:
    """Python of the separate Chatterbox virtualenv (MF_CHATTERBOX_PYTHON), if installed."""
    path = os.environ.get("MF_CHATTERBOX_PYTHON", "")
    return path if path and Path(path).exists() else None


def available(voice: dict) -> bool:
    return voice["engine"] != "chatterbox" or chatterbox_python() is not None
DEFAULT_VOICE = {"en": "en_US-ryan-high", "tr": "tr_TR-dfki-medium"}
VOICES = {lang: VOICE_CATALOG[vid]["path"] for lang, vid in DEFAULT_VOICE.items()}  # backwards compatibility


def voice_for(language: str, voice_id: str | None) -> str:
    """The chosen voice if it speaks this language, else the language's default."""
    v = VOICE_CATALOG.get(voice_id or "")
    if v and v["language"] == language and available(v):
        return v["id"]
    return DEFAULT_VOICE.get(language, DEFAULT_VOICE["en"])


def ensure_voice(language: str, models_dir: Path, voice_id: str | None = None) -> Path:
    """Download a Piper voice once; return the .onnx path."""
    vid = voice_for(language, voice_id)
    if VOICE_CATALOG[vid]["engine"] != "piper":
        vid = DEFAULT_VOICE.get(language, DEFAULT_VOICE["en"])
    rel = VOICE_CATALOG[vid]["path"]
    target = models_dir / "piper" / (Path(rel).name + ".onnx")
    target.parent.mkdir(parents=True, exist_ok=True)
    for suffix in (".onnx", ".onnx.json"):
        path = target.parent / (Path(rel).name + suffix)
        if path.exists() and path.stat().st_size > 0:
            continue
        tmp = path.with_suffix(path.suffix + ".part")
        with httpx.stream("GET", BASE + rel + suffix, follow_redirects=True, timeout=300) as r:
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
    return wav_seconds(out_wav)


def wav_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as wf:
        return wf.getnframes() / float(wf.getframerate())


def shift_pitch(wav: Path, semitones: int) -> None:
    """Raise/lower the voice by semitones in place, keeping the duration (resample + tempo correction)."""
    if not semitones:
        return
    with wave.open(str(wav), "rb") as wf:
        rate = wf.getframerate()
    factor = 2 ** (semitones / 12)
    tmp = wav.with_name(wav.stem + ".pitch.wav")
    subprocess.run(
        [shutil.which("ffmpeg") or "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(wav), "-af",
         f"asetrate={rate * factor:.0f},aresample={rate},atempo={1 / factor:.6f}", str(tmp)],
        check=True, capture_output=True, timeout=120,
    )  # fmt: skip
    tmp.replace(wav)


def change_speed(wav: Path, speed: float) -> None:
    """Speed up/slow down in place without changing the pitch."""
    if abs(speed - 1.0) < 0.01:
        return
    tmp = wav.with_name(wav.stem + ".speed.wav")
    subprocess.run([shutil.which("ffmpeg") or "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(wav),
                    "-af", f"atempo={speed:.3f}", str(tmp)], check=True, capture_output=True, timeout=120)  # fmt: skip
    tmp.replace(wav)


def synthesize_voice(
    voice_id: str, language: str, text: str, out_wav: Path, *, models_dir: Path, speed: float = 1.0,
    timeout: int = 1800,
) -> float:  # fmt: skip
    """Speak `text` with the chosen catalog voice (any engine); returns the audio length in seconds."""
    vid = voice_for(language, voice_id)
    voice = VOICE_CATALOG[vid]
    if voice["engine"] == "chatterbox":
        req = {"text": text, "language": language, "out": str(out_wav), "exaggeration": 0.55,
               "threads": os.cpu_count() or 4}  # fmt: skip
        proc = subprocess.run([chatterbox_python() or sys.executable, str(WORKER)], input=json.dumps(req),
                              capture_output=True, text=True, timeout=timeout)  # fmt: skip
        lines = [ln for ln in proc.stdout.strip().splitlines() if ln.startswith("{")]
        result = json.loads(lines[-1]) if lines else {"ok": False, "error": proc.stderr[-400:]}
        if not result.get("ok"):
            raise RuntimeError(f"Chatterbox failed: {result.get('error')}")
        change_speed(out_wav, speed)
        return wav_seconds(out_wav)
    return synthesize(text, ensure_voice(language, models_dir, vid), out_wav, length_scale=1.0 / speed)
