"""Background music library for the Studio: generated ambiences, your own tracks, previews."""

import subprocess
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from mediafactory.api.deps import client_ip, get_db, require_user
from mediafactory.audit.service import record_audit
from mediafactory.core.config import get_settings
from mediafactory.db.models import User
from mediafactory.pipeline import music as lib

router = APIRouter(prefix="/api/music", tags=["music"])
PREVIEW_S = 15


def _data() -> Path:
    return Path(get_settings().data_dir)


@router.get("")
def list_music(user: User = Depends(require_user)) -> dict:
    return {
        "generated": [{"id": k, "label": {"en": en, "tr": tr}} for k, (en, tr, _) in lib.GENERATED.items()],
        "tracks": lib.tracks(_data()),
    }


@router.post("", status_code=201)
def upload_track(
    request: Request, file: UploadFile = File(...), licence: str = Form("", max_length=500),
    source: str = Form("", max_length=500), db: Session = Depends(get_db, scope="function"),
    user: User = Depends(require_user),
) -> dict:  # fmt: skip
    try:
        path = lib.add_track(_data(), file.filename or "track.mp3", file.file, licence=licence, source=source)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    record_audit(db, actor_id=user.id, action="music.add", target_type="music", target_id=path.name,
                 details={"licence": licence}, ip=client_ip(request))  # fmt: skip
    return next(t for t in lib.tracks(_data()) if t["name"] == path.name)


@router.get("/{name}/audio")
def track_audio(name: str, user: User = Depends(require_user)):
    """The track itself, or a short rendered sample of a generated ambience."""
    if name in lib.GENERATED:
        out = _data() / "music_previews" / f"{name.split(':')[1]}.mp3"
        if not out.exists():
            out.parent.mkdir(parents=True, exist_ok=True)
            src = lib.GENERATED[name][2].format(d=PREVIEW_S)
            proc = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", src,
                                   "-af", f"afade=t=in:d=1,afade=t=out:st={PREVIEW_S - 2}:d=2", "-b:a", "128k", str(out)],
                                  capture_output=True, timeout=60)  # fmt: skip
            if proc.returncode != 0:
                raise HTTPException(status_code=502, detail="could not render the ambience")
        return FileResponse(out, media_type="audio/mpeg")
    path = lib.resolve(_data(), name)
    if path is None:
        raise HTTPException(status_code=404, detail="track not found")
    return FileResponse(path)


@router.delete("/{name}")
def delete_track(
    name: str, request: Request, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)
) -> dict:
    if not lib.remove_track(_data(), name):
        raise HTTPException(status_code=404, detail="track not found")
    record_audit(db, actor_id=user.id, action="music.delete", target_type="music", target_id=name, ip=client_ip(request))
    return {"ok": True}
