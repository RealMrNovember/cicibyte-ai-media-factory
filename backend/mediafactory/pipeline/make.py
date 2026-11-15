"""End-to-end: source item -> original script -> voice -> captions -> 9:16 video."""

import json
import time
from pathlib import Path

from sqlalchemy.orm import Session

from mediafactory.db.models import SourceItem
from mediafactory.pipeline.align import word_times
from mediafactory.pipeline.backgrounds import pick_background, resolve, story_category
from mediafactory.pipeline.captions import cues_for, to_ass, to_srt, to_vtt
from mediafactory.pipeline.classify import classify_script, content_check, with_checks
from mediafactory.pipeline.doctor import summary as doctor_summary
from mediafactory.pipeline.music import MusicSettings
from mediafactory.pipeline.originality import with_originality
from mediafactory.pipeline.qc import check_video
from mediafactory.pipeline.render import render_short
from mediafactory.pipeline.script import generate_script
from mediafactory.pipeline.style import CaptionStyle
from mediafactory.pipeline.thumbnail import make_thumbnail
from mediafactory.pipeline.tts import shift_pitch, synthesize_voice, voice_for, wav_seconds
from mediafactory.pipeline.voice import VoiceSettings


def make_short(
    session: Session, item_id: int, *, language: str, data_dir: Path, seconds: int = 50,
    background: Path | None = None, background_choice: str = "random", style: dict | None = None,
    script: dict | None = None, voice: dict | None = None, music: dict | None = None, category: str | None = None,
    log=print,
) -> dict:  # fmt: skip
    caption_style = CaptionStyle(**(style or {}))
    item = session.get(SourceItem, item_id)
    if item is None:
        raise ValueError(f"source item {item_id} not found")
    out = data_dir / "videos" / f"item{item_id}-{language}-{int(time.time())}"
    out.mkdir(parents=True, exist_ok=True)

    started = time.monotonic()
    if script and str(script.get("narration", "")).strip():
        log(f"[1/4] script ({language}): using the reviewed script '{script.get('title', '')[:70]}'")
        script = {**script, "model": script.get("model") or "edited"}
    else:
        log(f"[1/4] script ({language}) from item {item_id}: {item.title[:70]}")
        script = generate_script(session, item, language=language, seconds=seconds)
    (out / "script.json").write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"      -> '{script['title']}' via {script['model']} ({len(script['narration'].split())} words)")
    if script.get("doctor"):
        log(f"      Script Doctor: {doctor_summary(script['doctor'])}")
    content = classify_script(session, script["narration"], language=language)
    log(f"      content check: {content_check(content)['value']}")

    vs = VoiceSettings(**(voice or {}))
    voice_id = voice_for(language, getattr(vs, language, None))
    log(f"[2/4] voice ({voice_id}, speed {vs.speed:g}x, pitch {vs.pitch:+d})")
    duration = synthesize_voice(voice_id, language, script["narration"], out / "voice.wav", models_dir=data_dir / "models",
                                speed=vs.speed)  # fmt: skip
    if vs.pitch:
        shift_pitch(out / "voice.wav", vs.pitch)
        duration = wav_seconds(out / "voice.wav")
    log(f"      -> {duration:.1f}s of narration")

    log("[3/4] captions")
    times, note = word_times(out / "voice.wav", script["narration"], language=language, duration=duration,
                             models_dir=data_dir / "models")  # fmt: skip
    log(f"      -> {note}")
    cues = cues_for(script["narration"], duration, words_per_cue=caption_style.words_per_cue, times=times)
    (out / "captions.ass").write_text(to_ass(cues, language, style=caption_style), encoding="utf-8")
    (out / "captions.srt").write_text(to_srt(cues), encoding="utf-8")
    (out / "captions.vtt").write_text(to_vtt(cues), encoding="utf-8")

    if background is None and background_choice not in ("random", "none"):
        background = resolve(data_dir, background_choice)
    if background is None and background_choice != "none":
        background = pick_background(data_dir, category=category or story_category(session, item))
    log(f"[4/4] render 1080x1920 over {background.name if background else 'generated gradient'}")
    ms = MusicSettings(**(music or {}))
    if ms.track != "none":
        log(f"      music: {ms.track} at {ms.volume_db} dB{', ducked under the voice' if ms.ducking else ''}")
    video = render_short(out, audio="voice.wav", captions_ass="captions.ass", duration=duration, background=background,
                         music=ms, data_dir=data_dir)  # fmt: skip

    log("[+] cover image and quality check")
    thumb = None
    try:
        thumb = make_thumbnail(out, background=background, title=script["title"], style=caption_style,
                               duration=duration, language=language)  # fmt: skip
    except Exception as exc:  # a missing cover must not lose the video
        log(f"      cover image failed: {exc}")
    qc = check_video(video, captions=len(cues))
    if item.rights_status != "user_owned":  # your own story may be read as it is
        qc = with_originality(qc, script["narration"], item.normalized_text or "")
    qc = with_checks(qc, content, item.rights_status)
    failed = [f"{c['name']} ({c['value']})" for c in qc["checks"] if not c["ok"]]
    log("      QC passed" if qc["passed"] else f"      QC issues: {', '.join(failed)}")
    result = {
        "item_id": item_id, "language": language, "title": script["title"], "video": str(video),
        "thumbnail": str(thumb) if thumb else None, "qc": qc, "content": content,
        "duration_s": round(duration, 1), "elapsed_s": round(time.monotonic() - started, 1), "folder": str(out),
    }  # fmt: skip
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"done in {result['elapsed_s']}s -> {video}")
    return result
