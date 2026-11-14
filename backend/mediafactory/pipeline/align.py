"""Real word timings for captions: faster-whisper listens to the narration, then the heard words are
matched to the known script so captions keep the exact script text but follow the actual voice."""

import difflib
import logging
import os
import re
import threading
from pathlib import Path

log = logging.getLogger(__name__)

MIN_MATCH_RATIO = 0.5  # below this the transcript is too different; fall back to estimated timing
_models: dict[str, object] = {}
_lock = threading.Lock()


def norm(word: str) -> str:
    # Treat I/İ/ı/i as one letter so English "I" and Turkish dotted/dotless forms all match.
    w = word.replace("İ", "i").replace("I", "i").replace("ı", "i").lower()
    return re.sub(r"[^\w]", "", w)


def align_words(
    narration: list[str], heard: list[tuple[str, float, float]], *, duration: float
) -> list[tuple[float, float]] | None:
    """Timings for every narration word, or None when too few words could be matched."""
    if not narration:
        return []
    a, b = [norm(w) for w in narration], [norm(w) for w, _, _ in heard]
    times: list[tuple[float, float] | None] = [None] * len(narration)
    matched = 0
    for block in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_matching_blocks():
        for k in range(block.size):
            _, s, e = heard[block.b + k]
            times[block.a + k] = (float(s), float(e))
            matched += 1
    if matched < max(1, MIN_MATCH_RATIO * len(narration)):
        return None
    # Fill gaps (misheard or missing words) evenly between the known neighbours.
    i, n = 0, len(times)
    while i < n:
        if times[i] is not None:
            i += 1
            continue
        j = i
        while j < n and times[j] is None:
            j += 1
        left = times[i - 1][1] if i > 0 else 0.0
        right = times[j][0] if j < n else duration
        if right <= left:
            right = left + 0.08 * (j - i)
        step = (right - left) / (j - i)
        for k in range(i, j):
            times[k] = (left + step * (k - i), left + step * (k - i + 1))
        i = j
    # Keep order and stay inside the audio.
    out, last = [], 0.0
    for s, e in times:  # type: ignore[misc]
        s = min(max(s, last), duration)
        e = min(max(e, s + 0.04), duration)
        out.append((round(s, 3), round(e, 3)))
        last = s
    return out


def _model(models_dir: Path):
    name = os.environ.get("MF_WHISPER_MODEL", "small")
    with _lock:
        if name not in _models:
            from faster_whisper import WhisperModel

            _models[name] = WhisperModel(name, device="cpu", compute_type="int8",
                                         download_root=str(models_dir / "whisper"))  # fmt: skip
        return _models[name]


def _pcm16k(wav: Path):
    """Mono 16 kHz float32 samples via ffmpeg (avoids PyAV, whose versions often clash)."""
    import subprocess

    import numpy as np

    raw = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(wav), "-ac", "1", "-ar", "16000",
                          "-f", "s16le", "-"], capture_output=True, check=True, timeout=120).stdout  # fmt: skip
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def transcribe_words(wav: Path, language: str, models_dir: Path) -> list[tuple[str, float, float]]:
    segments, _ = _model(models_dir).transcribe(_pcm16k(wav), language=language, word_timestamps=True, beam_size=1,
                                                condition_on_previous_text=False)  # fmt: skip
    return [(w.word.strip(), w.start, w.end) for seg in segments for w in (seg.words or []) if w.word.strip()]


def word_times(
    wav: Path, narration: str, *, language: str, duration: float, models_dir: Path
) -> tuple[list[tuple[float, float]] | None, str]:
    """(timings, note). Never raises: any problem means estimated timing is used instead."""
    words = re.findall(r"\S+", narration)
    try:
        heard = transcribe_words(wav, language, models_dir)
    except Exception as exc:  # missing package, model download failure, decoding error…
        log.warning("whisper alignment unavailable: %s", exc)
        return None, f"estimated timing (whisper unavailable: {type(exc).__name__})"
    times = align_words(words, heard, duration=duration)
    if times is None:
        return None, f"estimated timing (whisper heard {len(heard)} words, too different from the script)"
    exact = sum(1 for w in words if norm(w) in {norm(h) for h, _, _ in heard})
    return times, f"whisper-aligned ({exact}/{len(words)} words heard)"
