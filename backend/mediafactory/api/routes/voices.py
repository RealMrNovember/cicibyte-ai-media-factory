"""Voice catalog, your cloned voices and short previews for the Studio voice picker."""

import hashlib
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from mediafactory.api.deps import client_ip, get_db, require_user
from mediafactory.audit.service import record_audit
from mediafactory.core.config import get_settings
from mediafactory.db.models import User
from mediafactory.pipeline import clones, pronounce
from mediafactory.pipeline.tts import (
    VOICE_CATALOG,
    available,
    chatterbox_ready,
    default_voice,
    lookup,
    shift_pitch,
    synthesize_voice,
)  # fmt: skip

router = APIRouter(prefix="/api/voices", tags=["voices"])
dictionary = APIRouter(prefix="/api/pronunciations", tags=["voices"])
PREVIEW_KEEP_S = 90  # the API keeps Chatterbox only briefly: the worker needs the memory for videos

SAMPLE = {
    "en": "It was three in the morning when I heard the attic door open. Slowly. By itself.",
    "tr": "Gece saat üçte tavan arasının kapısının açıldığını duydum. Yavaşça. Kendi kendine.",
}


@router.get("")
def list_voices(user: User = Depends(require_user)) -> dict:
    data = Path(get_settings().data_dir) / "models" / "piper"
    voices = [{k: v for k, v in voice.items() if k != "path"} | {"downloaded": (data / f"{voice['id']}.onnx").exists()}
              for voice in VOICE_CATALOG.values() if available(voice)]  # fmt: skip
    cloning = chatterbox_ready()
    if cloning:
        voices += [{k: v for k, v in c.items() if k != "path"} | {"downloaded": True} for c in clones.list_clones(clones.data_dir())]
    return {"voices": voices, "defaults": {lang: default_voice(lang) for lang in ("en", "tr")}, "cloning": cloning,
            "clone_limits": {"min_s": clones.MIN_S, "max_s": clones.MAX_S}}  # fmt: skip


@router.post("/clones", status_code=201)
def add_clone(
    request: Request, file: UploadFile = File(...), label: str = Form("", max_length=60), consent: bool = Form(False),
    db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user),
) -> dict:  # fmt: skip
    if not chatterbox_ready():
        raise HTTPException(status_code=409, detail="voice cloning needs Chatterbox installed on the server")
    try:
        voice = clones.add_clone(clones.data_dir(), file.filename or "", file.file, label=label, consent=consent)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    record_audit(db, actor_id=user.id, action="voice.clone.add", target_type="voice", target_id=voice["id"],
                 details={"label": voice["label"], "consent": True}, ip=client_ip(request))  # fmt: skip
    return voice


@router.get("/clones/{vid}/audio")
def clone_audio(vid: str, user: User = Depends(require_user)):
    path = clones.clone_path(clones.data_dir(), vid)
    if path is None:
        raise HTTPException(status_code=404, detail="voice not found")
    return FileResponse(path, media_type="audio/wav")


@router.delete("/clones/{vid}")
def delete_clone(
    vid: str, request: Request, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)
) -> dict:
    if not clones.remove_clone(clones.data_dir(), vid):
        raise HTTPException(status_code=404, detail="voice not found")
    record_audit(db, actor_id=user.id, action="voice.clone.delete", target_type="voice", target_id=vid, ip=client_ip(request))
    return {"ok": True}


class PreviewIn(BaseModel):
    voice: str = Field(max_length=80)
    speed: float = Field(default=1.0, ge=0.8, le=1.3)
    pitch: int = Field(default=0, ge=-4, le=4)
    language: str = Field(default="", pattern=r"^(en|tr)?$", description="for cloned voices, which sample to speak")
    text: str = Field(default="", max_length=240, description="say this instead of the sample (pronunciation check)")


@router.post("/preview")
def preview(body: PreviewIn, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)):
    """A short sample in this voice (downloads the voice the first time; cached afterwards)."""
    voice = lookup(body.voice)
    if voice is None or not available(voice):
        raise HTTPException(status_code=404, detail="unknown voice")
    language = voice["language"] if voice["language"] != "any" else (body.language or "en")
    data = Path(get_settings().data_dir)
    text = pronounce.spoken(db, body.text.strip() or SAMPLE[language], language)
    key = hashlib.sha256(f"{body.voice}|{language}|{body.speed:.2f}|{body.pitch}|{text}".encode()).hexdigest()[:20]
    out = data / "voice_previews" / f"{key}.wav"
    if not out.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            tmp = out.with_suffix(".tmp.wav")
            synthesize_voice(body.voice, language, text, tmp, models_dir=data / "models", speed=body.speed,
                             keep_s=PREVIEW_KEEP_S)  # fmt: skip
            shift_pitch(tmp, body.pitch)
            tmp.replace(out)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"could not make a preview: {exc}") from None
    return FileResponse(out, media_type="audio/wav")


class Rule(BaseModel):
    word: str = Field(max_length=80)
    say: str = Field(max_length=120)
    language: str = Field(default="any", pattern=r"^(any|en|tr)$")


class RulesIn(BaseModel):
    items: list[Rule] = Field(max_length=pronounce.MAX_RULES)


@dictionary.get("")
def list_rules(db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)) -> dict:
    return {"items": pronounce.rules(db)}


@dictionary.put("")
def save_rules(
    body: RulesIn, request: Request, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)
) -> dict:
    items = pronounce.save(db, [r.model_dump() for r in body.items])
    record_audit(db, actor_id=user.id, action="pronunciations.save", details={"count": len(items)}, ip=client_ip(request))
    return {"items": items}
