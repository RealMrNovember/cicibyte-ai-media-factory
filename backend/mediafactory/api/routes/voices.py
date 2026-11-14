"""Voice catalog and short previews for the Studio voice picker."""

import hashlib
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from mediafactory.api.deps import require_user
from mediafactory.core.config import get_settings
from mediafactory.db.models import User
from mediafactory.pipeline.tts import DEFAULT_VOICE, VOICE_CATALOG, ensure_voice, shift_pitch, synthesize

router = APIRouter(prefix="/api/voices", tags=["voices"])

SAMPLE = {
    "en": "It was three in the morning when I heard the attic door open. Slowly. By itself.",
    "tr": "Gece saat üçte tavan arasının kapısının açıldığını duydum. Yavaşça. Kendi kendine.",
}


@router.get("")
def list_voices(user: User = Depends(require_user)) -> dict:
    data = Path(get_settings().data_dir) / "models" / "piper"
    voices = [{k: v for k, v in voice.items() if k != "path"} | {"downloaded": (data / f"{voice['id']}.onnx").exists()}
              for voice in VOICE_CATALOG.values()]  # fmt: skip
    return {"voices": voices, "defaults": DEFAULT_VOICE}


class PreviewIn(BaseModel):
    voice: str = Field(max_length=80)
    speed: float = Field(default=1.0, ge=0.8, le=1.3)
    pitch: int = Field(default=0, ge=-4, le=4)


@router.post("/preview")
def preview(body: PreviewIn, user: User = Depends(require_user)):
    """A short sample in this voice (downloads the voice the first time; cached afterwards)."""
    voice = VOICE_CATALOG.get(body.voice)
    if voice is None:
        raise HTTPException(status_code=404, detail="unknown voice")
    data = Path(get_settings().data_dir)
    key = hashlib.sha256(f"{body.voice}|{body.speed:.2f}|{body.pitch}".encode()).hexdigest()[:20]
    out = data / "voice_previews" / f"{key}.wav"
    if not out.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            path = ensure_voice(voice["language"], data / "models", body.voice)
            tmp = out.with_suffix(".tmp.wav")
            synthesize(SAMPLE[voice["language"]], path, tmp, length_scale=1.0 / body.speed)
            shift_pitch(tmp, body.pitch)
            tmp.replace(out)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"could not make a preview: {exc}") from None
    return FileResponse(out, media_type="audio/wav")
