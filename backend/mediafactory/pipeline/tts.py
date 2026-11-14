"""Local text-to-speech with Piper (ONNX, CPU-friendly), a catalog of English and Turkish voices,
speed (Piper length scale) and pitch (ffmpeg, duration kept)."""

import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
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
DEFAULT_VOICE = {"en": "en_US-ryan-high", "tr": "tr_TR-dfki-medium"}  # Piper voices: always available
PREFERRED_VOICE = {"tr": "tr-chatterbox"}  # used as the default when its engine is installed
VOICES = {lang: VOICE_CATALOG[vid]["path"] for lang, vid in DEFAULT_VOICE.items()}  # backwards compatibility


def default_voice(language: str) -> str:
    """Chatterbox for Turkish where it is installed, otherwise the language's Piper voice."""
    preferred = VOICE_CATALOG.get(PREFERRED_VOICE.get(language, ""))
    if preferred and available(preferred):
        return preferred["id"]
    return DEFAULT_VOICE.get(language, DEFAULT_VOICE["en"])


def lookup(voice_id: str | None) -> dict | None:
    """A catalog voice or one of your cloned voices (language "any")."""
    from mediafactory.pipeline import clones

    if voice_id in VOICE_CATALOG:
        return VOICE_CATALOG[voice_id]
    return clones.get_clone(clones.data_dir(), voice_id) if clones.CLONE_ID.match(voice_id or "") else None


def voice_for(language: str, voice_id: str | None) -> str:
    """The chosen voice if it speaks this language and its engine is installed, else the language's default."""
    v = lookup(voice_id)
    if v and v["language"] in (language, "any") and available(v):
        return v["id"]
    return default_voice(language)


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
    timeout: int = 1800, keep_s: float | None = None,
) -> float:  # fmt: skip
    """Speak `text` with the chosen catalog voice (any engine); returns the audio length in seconds."""
    vid = voice_for(language, voice_id)
    voice = lookup(vid) or VOICE_CATALOG[default_voice(language)]
    if voice["engine"] == "chatterbox":
        from mediafactory.pipeline import clones

        req = {"text": text, "language": language, "out": str(out_wav), "exaggeration": 0.55}
        ref = clones.clone_path(clones.data_dir(), vid)
        if ref is not None:
            req["reference"] = str(ref)
        chatterbox_request(req, timeout=timeout, keep_s=keep_s)
        change_speed(out_wav, speed)
        return wav_seconds(out_wav)
    return synthesize(text, ensure_voice(language, models_dir, vid), out_wav, length_scale=1.0 / speed)


class _ChatterboxServer:
    """One long-lived Chatterbox process per app process: the 3 GB model loads once, not once per video.
    It answers one JSON line per request, and is stopped after IDLE_S without work to give the memory back."""

    IDLE_S = 600
    REAP_S = 15.0

    def __init__(self) -> None:
        self.keep_s: float = self.IDLE_S
        self.lock = threading.Lock()
        self.proc: subprocess.Popen | None = None
        self.lines: queue.Queue = queue.Queue()
        self.stderr: list[str] = []
        self.last_used = 0.0

    def _start(self) -> None:
        self.lines, self.stderr = queue.Queue(), []
        self.proc = subprocess.Popen(
            [chatterbox_python() or sys.executable, str(WORKER), "--serve"], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", bufsize=1,
        )  # fmt: skip
        proc, lines, err = self.proc, self.lines, self.stderr

        def pump_out() -> None:
            for ln in proc.stdout:
                lines.put(ln)
            lines.put(None)  # process ended

        def pump_err() -> None:
            for ln in proc.stderr:
                err.append(ln)
                del err[:-40]

        for fn in (pump_out, pump_err):
            threading.Thread(target=fn, daemon=True).start()
        threading.Thread(target=self._reaper, args=(proc,), daemon=True).start()

    def _reaper(self, proc: subprocess.Popen) -> None:
        while proc.poll() is None:
            time.sleep(self.REAP_S)
            with self.lock:  # held during a request, so a busy server is never stopped
                if self.proc is proc and (time.monotonic() - self.last_used > self.keep_s or low_memory()):
                    self._stop()
                    return

    def _stop(self) -> None:
        proc, self.proc = self.proc, None
        if proc is None:
            return
        try:
            proc.stdin.close()  # the server exits at end of input
            proc.wait(timeout=10)
        except Exception:  # noqa: BLE001
            proc.kill()

    def request(self, req: dict, timeout: float, keep_s: float | None = None) -> dict:
        with self.lock:
            if self.proc is None or self.proc.poll() is not None:
                self._start()
            self.keep_s = self.IDLE_S if keep_s is None else keep_s
            self.last_used = time.monotonic()
            deadline = time.monotonic() + timeout
            try:
                self.proc.stdin.write(json.dumps({**req, "threads": os.cpu_count() or 4}) + "\n")
                self.proc.stdin.flush()
                while True:
                    ln = self.lines.get(timeout=max(0.1, deadline - time.monotonic()))
                    if ln is None:
                        raise RuntimeError(("".join(self.stderr) or "the Chatterbox process exited")[-400:])
                    if ln.startswith("{"):
                        result = json.loads(ln)
                        break
            except queue.Empty:
                self.proc.kill()
                self.proc = None
                raise RuntimeError(f"Chatterbox took longer than {timeout:.0f}s") from None
            except (OSError, RuntimeError) as exc:
                if self.proc is not None:
                    self.proc.wait(timeout=5)
                self.proc = None
                raise RuntimeError(f"Chatterbox failed: {exc}") from None
            finally:
                self.last_used = time.monotonic()
        if not result.get("ok"):
            raise RuntimeError(f"Chatterbox failed: {result.get('error')}")
        return result

    def shutdown(self) -> None:
        with self.lock:
            self._stop()


_SERVER = _ChatterboxServer()


LOW_MEMORY_MB = 1500


def low_memory() -> bool:
    """True when the machine has less than LOW_MEMORY_MB available (Linux; elsewhere never)."""
    try:
        with open("/proc/meminfo", encoding="ascii") as f:
            info = dict(ln.split(":", 1) for ln in f if ":" in ln)
        return int(info["MemAvailable"].split()[0]) // 1024 < LOW_MEMORY_MB
    except (OSError, KeyError, ValueError):
        return False


def chatterbox_request(req: dict, *, timeout: float = 1800, keep_s: float | None = None) -> dict:
    """Synthesise one request with the shared Chatterbox server (started on first use). It stays loaded for
    keep_s seconds afterwards (default IDLE_S), or until memory runs low."""
    return _SERVER.request(req, timeout, keep_s)


def chatterbox_shutdown() -> None:
    _SERVER.shutdown()
