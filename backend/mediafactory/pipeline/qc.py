"""Quality check of a finished Short: format, length, loudness, long silences, black screens, captions."""

import json
import re
import shutil
import subprocess
from pathlib import Path

LIMITS = {
    "min_s": 10.0, "max_s": 180.0,          # YouTube Shorts length
    "lufs_min": -20.0, "lufs_max": -10.0,   # we normalise to -14 LUFS
    "peak_max": -0.5,                       # dBTP, above means clipping risk
    "silence_s": 2.5, "black_s": 2.0,
}  # fmt: skip


def _bin(name: str) -> str:
    return shutil.which(name) or name


def parse_ffmpeg_report(stderr: str) -> dict:
    """Pull loudness (loudnorm JSON), silences and black segments out of an ffmpeg analysis run."""
    lufs = peak = None
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", stderr, re.S)
    if m:
        data = json.loads(m.group(0))
        lufs, peak = float(data["input_i"]), float(data["input_tp"])
    silences = [float(x) for x in re.findall(r"silence_duration:\s*([\d.]+)", stderr)]
    blacks = [float(x) for x in re.findall(r"black_duration:\s*([\d.]+)", stderr)]
    return {"lufs": lufs if lufs is None or lufs > -70 else None, "true_peak": peak, "silences": silences, "blacks": blacks}


def measure(video: Path) -> dict:
    probe = json.loads(subprocess.run(
        [_bin("ffprobe"), "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)],
        capture_output=True, text=True, check=True, timeout=60,
    ).stdout)  # fmt: skip
    v = next((s for s in probe["streams"] if s["codec_type"] == "video"), {})
    has_audio = any(s["codec_type"] == "audio" for s in probe["streams"])
    cmd = [_bin("ffmpeg"), "-hide_banner", "-nostats", "-i", str(video), "-vf", "blackdetect=d=1.5:pix_th=0.03"]
    if has_audio:
        cmd += ["-af", "loudnorm=print_format=json,silencedetect=noise=-45dB:d=2"]
    report = subprocess.run(cmd + ["-f", "null", "-"], capture_output=True, text=True, timeout=600).stderr
    return {"width": int(v.get("width", 0)), "height": int(v.get("height", 0)),
            "duration": float(probe["format"].get("duration", 0)), "has_audio": has_audio,
            **parse_ffmpeg_report(report)}  # fmt: skip


def judge(m: dict) -> dict:
    L = LIMITS
    checks = [
        ("resolution", (m["width"], m["height"]) == tuple(m.get("expected_size") or (1080, 1920)), f"{m['width']}×{m['height']}"),
        ("duration", L["min_s"] <= m["duration"] <= L["max_s"], f"{m['duration']:.1f} s"),
        ("audio", bool(m["has_audio"]), "present" if m["has_audio"] else "missing"),
        ("loudness", m.get("lufs") is not None and L["lufs_min"] <= m["lufs"] <= L["lufs_max"],
         f"{m['lufs']:.1f} LUFS" if m.get("lufs") is not None else "silent"),
        ("peak", m.get("true_peak") is not None and m["true_peak"] <= L["peak_max"],
         f"{m['true_peak']:.1f} dBTP" if m.get("true_peak") is not None else "—"),
        ("silence", not any(s > L["silence_s"] for s in m.get("silences", [])),
         f"longest {max(m.get('silences') or [0]):.1f} s"),
        ("black", not any(b > L["black_s"] for b in m.get("blacks", [])), f"longest {max(m.get('blacks') or [0]):.1f} s"),
        ("captions", m.get("captions", 1) > 0, f"{m.get('captions', '?')} lines"),
    ]  # fmt: skip
    if not m["has_audio"]:  # loudness/peak/silence are meaningless without audio; report audio once
        checks = [c if c[0] not in ("loudness", "peak", "silence") else (c[0], True, "—") for c in checks]
    return {"passed": all(ok for _, ok, _ in checks), "checks": [{"name": n, "ok": ok, "value": val} for n, ok, val in checks]}


def check_video(video: Path, *, captions: int, size: tuple[int, int] = (1080, 1920)) -> dict:
    """Never raises: a failed measurement is itself a QC failure."""
    try:
        return judge({**measure(video), "captions": captions, "expected_size": size})
    except Exception as exc:
        return {"passed": False, "checks": [{"name": "measure", "ok": False, "value": f"{type(exc).__name__}: {exc}"[:200]}]}
