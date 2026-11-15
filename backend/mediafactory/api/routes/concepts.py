"""Channel concepts (Takvim → Kanallar ve konseptler)."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from mediafactory import concepts
from mediafactory.api.deps import client_ip, get_db, require_user
from mediafactory.audit.service import record_audit
from mediafactory.db.models import Concept, User, YouTubeChannel
from mediafactory.pipeline.music import MusicSettings
from mediafactory.pipeline.style import CaptionStyle
from mediafactory.pipeline.voice import VoiceSettings

router = APIRouter(prefix="/api/concepts", tags=["concepts"])


class ConceptIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    enabled: bool = True
    language: Literal["en", "tr"] = "en"
    topic: str = Field(default="random", max_length=20)
    seconds: int = Field(default=50, ge=15, le=170)
    style: CaptionStyle = Field(default_factory=CaptionStyle)
    voice: VoiceSettings = Field(default_factory=VoiceSettings)
    music: MusicSettings = Field(default_factory=MusicSettings)
    background: str = Field(default="random", max_length=120)
    youtube_channel_id: int | None = None
    platforms: list[Literal["youtube", "instagram"]] = Field(default_factory=lambda: ["youtube"], min_length=1, max_length=2)
    privacy: Literal["public", "unlisted", "private"] = "public"
    ready_buffer: int = Field(default=0, ge=0, le=20)
    auto_approve: bool = False


def _get(db: Session, cid: int) -> Concept:
    c = db.get(Concept, cid)
    if c is None:
        raise HTTPException(status_code=404, detail="concept not found")
    return c


def _apply(db: Session, c: Concept, body: ConceptIn) -> None:
    if body.youtube_channel_id is not None and db.get(YouTubeChannel, body.youtube_channel_id) is None:
        raise HTTPException(status_code=422, detail="unknown YouTube channel")
    data = body.model_dump()
    for key in ("style", "voice", "music"):
        data[key] = getattr(body, key).model_dump()
    data["platforms"] = list(dict.fromkeys(body.platforms))
    for k, v in data.items():
        setattr(c, k, v)


def _save(db: Session, c: Concept) -> None:
    try:
        with db.begin_nested():
            db.add(c)
            db.flush()
    except IntegrityError:
        raise HTTPException(status_code=409, detail="a concept with this name already exists") from None


@router.get("")
def list_concepts(db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)) -> dict:
    return {"items": [concepts.out(c, stock=concepts.stock(db, c)) for c in db.scalars(select(Concept).order_by(Concept.id))]}


@router.post("", status_code=201)
def create_concept(
    body: ConceptIn, request: Request, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)
) -> dict:
    c = Concept()
    _apply(db, c, body)
    _save(db, c)
    record_audit(db, actor_id=user.id, action="concept.create", target_type="concept", target_id=str(c.id),
                 details={"name": c.name}, ip=client_ip(request))  # fmt: skip
    return concepts.out(c, stock=0)


@router.put("/{cid}")
def update_concept(
    cid: int, body: ConceptIn, request: Request, db: Session = Depends(get_db, scope="function"),
    user: User = Depends(require_user),
) -> dict:  # fmt: skip
    c = _get(db, cid)
    _apply(db, c, body)
    _save(db, c)
    record_audit(db, actor_id=user.id, action="concept.update", target_type="concept", target_id=str(cid), ip=client_ip(request))
    return concepts.out(c, stock=concepts.stock(db, c))


@router.delete("/{cid}")
def delete_concept(
    cid: int, request: Request, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)
) -> dict:
    db.delete(_get(db, cid))
    record_audit(db, actor_id=user.id, action="concept.delete", target_type="concept", target_id=str(cid), ip=client_ip(request))
    return {"ok": True}


@router.post("/{cid}/produce")
def produce_now(
    cid: int, request: Request, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)
) -> dict:
    """Make one video of this concept now (it waits in Ready unless the concept approves automatically)."""
    c = _get(db, cid)
    job = concepts.produce(db, c, origin=f"concept:{c.id}")
    if job is None:
        raise HTTPException(status_code=409, detail="no unused story for this concept's language and topic")
    record_audit(db, actor_id=user.id, action="concept.produce", target_type="concept", target_id=str(cid), ip=client_ip(request))
    return {"job_id": job.id, "title": (job.payload or {}).get("title", "")}
