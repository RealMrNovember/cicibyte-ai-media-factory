"""End-to-end: source item -> original script -> voice -> captions -> 9:16 video."""

import json
import time
from pathlib import Path

from sqlalchemy.orm import Session

from mediafactory.db.models import SourceItem
from mediafactory.pipeline.backgrounds import pick_background
from mediafactory.pipeline.captions import cues_for, to_ass, to_srt, to_vtt
from mediafactory.pipeline.render import render_short
from mediafactory.pipeline.script import generate_script
from mediafactory.pipeline.tts import ensure_voice, synthesize


def make_short(
    session: Session, item_id: int, *, language: str, data_dir: Path, seconds: int = 50,
    background: Path | None = None, log=print,
) -> dict:  # fmt: skip
    item = session.get(SourceItem, item_id)
    if item is None:
        raise ValueError(f"source item {item_id} not found")
    out = data_dir / "videos" / f"item{item_id}-{language}-{int(time.time())}"
    out.mkdir(parents=True, exist_ok=True)

    started = time.monotonic()
    log(f"[1/4] script ({language}) from item {item_id}: {item.title[:70]}")
    script = generate_script(session, item, language=language, seconds=seconds)
    (out / "script.json").write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"      -> '{script['title']}' via {script['model']} ({len(script['narration'].split())} words)")

    log("[2/4] voice (Piper)")
    voice = ensure_voice(language, data_dir / "models")
    duration = synthesize(script["narration"], voice, out / "voice.wav")
    log(f"      -> {duration:.1f}s of narration")

    log("[3/4] captions")
    cues = cues_for(script["narration"], duration)
    (out / "captions.ass").write_text(to_ass(cues, language), encoding="utf-8")
    (out / "captions.srt").write_text(to_srt(cues), encoding="utf-8")
    (out / "captions.vtt").write_text(to_vtt(cues), encoding="utf-8")

    background = background or pick_background(data_dir)
    log(f"[4/4] render 1080x1920 over {background.name if background else 'generated gradient'}")
    video = render_short(out, audio="voice.wav", captions_ass="captions.ass", duration=duration, background=background)
    result = {
        "item_id": item_id, "language": language, "title": script["title"], "video": str(video),
        "duration_s": round(duration, 1), "elapsed_s": round(time.monotonic() - started, 1), "folder": str(out),
    }  # fmt: skip
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"done in {result['elapsed_s']}s -> {video}")
    return result
