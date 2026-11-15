"""Background clip library for the Studio: list, upload (with licence note), preview, delete."""

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from mediafactory.api.deps import client_ip, get_db, require_user
from mediafactory.audit.service import record_audit
from mediafactory.core.config import get_settings
from mediafactory.db.models import User
from mediafactory.pipeline import backgrounds as lib

router = APIRouter(prefix="/api/backgrounds", tags=["backgrounds"])


def _data() -> Path:
    return Path(get_settings().data_dir)


def _clip(name: str) -> Path:
    clip = lib.resolve(_data(), name)
    if clip is None:
        raise HTTPException(status_code=404, detail="clip not found")
    return clip


@router.get("")
def list_clips(user: User = Depends(require_user)) -> dict:
    return {"items": [lib.info(c) for c in lib.clips(_data())]}


@router.post("", status_code=201)
def upload_clip(
    request: Request, file: UploadFile = File(...), licence: str = Form("", max_length=500),
    source: str = Form("", max_length=500), tags: str = Form("", max_length=300),
    db: Session = Depends(get_db, scope="function"),
    user: User = Depends(require_user),
) -> dict:  # fmt: skip
    try:
        clip = lib.add_clip(_data(), file.filename or "clip.mp4", file.file, licence=licence, source=source,
                            tags=[t for t in tags.split(",") if t])  # fmt: skip
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    try:
        lib.thumbnail(clip)
    except RuntimeError:
        lib.remove_clip(_data(), clip.name)
        raise HTTPException(status_code=422, detail="this file is not a readable video") from None
    record_audit(db, actor_id=user.id, action="background.add", target_type="background", target_id=clip.name,
                 details={"licence": licence, "source": source}, ip=client_ip(request))  # fmt: skip
    return lib.info(clip)


@router.get("/{name}/thumb")
def clip_thumb(name: str, user: User = Depends(require_user)):
    try:
        return FileResponse(lib.thumbnail(_clip(name)), media_type="image/jpeg")
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@router.get("/{name}/video")
def clip_video(name: str, user: User = Depends(require_user)):
    return FileResponse(_clip(name))


@router.delete("/{name}")
def delete_clip(
    name: str, request: Request, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)
) -> dict:
    if not lib.remove_clip(_data(), name):
        raise HTTPException(status_code=404, detail="clip not found")
    record_audit(db, actor_id=user.id, action="background.delete", target_type="background", target_id=name,
                 ip=client_ip(request))  # fmt: skip
    return {"ok": True}


class TagsIn(BaseModel):
    tags: list[str] = Field(default_factory=list, max_length=20)


@router.put("/{name}/tags")
def update_tags(name: str, body: TagsIn, user: User = Depends(require_user)) -> dict:
    tags = lib.set_tags(_data(), name, body.tags)
    if tags is None:
        raise HTTPException(status_code=404, detail="clip not found")
    return {"name": name, "tags": tags}


studio = APIRouter(prefix="/api/studio", tags=["studio"])


class FrameIn(BaseModel):
    style: dict = Field(default_factory=dict)
    text: str = Field(default="It was three in the morning when I heard the attic door open", max_length=300)
    language: str = Field(default="en", pattern=r"^(en|tr)$")
    background: str = Field(default="random", max_length=200)


@studio.post("/frame")
def preview_frame(body: FrameIn, user: User = Depends(require_user)):
    """One exact frame of the video (same caption renderer as the final video)."""
    import tempfile

    from fastapi.responses import Response

    from mediafactory.pipeline.framepreview import render_frame
    from mediafactory.pipeline.style import CaptionStyle

    try:
        style = CaptionStyle(**body.style)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    if body.background == "none":
        bg = None
    elif body.background == "random":
        clips = lib.clips(_data())
        bg = clips[0] if clips else None
    else:
        bg = _clip(body.background)
    with tempfile.TemporaryDirectory() as td:
        try:
            frame = render_frame(Path(td), style=style, text=body.text, language=body.language, background=bg)
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from None
        data = frame.read_bytes()
    return Response(content=data, media_type="image/jpeg", headers={"Cache-Control": "no-store"})
