"""Schedules (Takvim): recurring production and recurring YouTube publishing."""

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from mediafactory.api.deps import client_ip, get_db, require_user
from mediafactory.audit.service import record_audit
from mediafactory.db.models import Schedule, User
from mediafactory.pipeline.style import CaptionStyle
from mediafactory.pipeline.voice import VoiceSettings
from mediafactory.schedule.runner import ACTIONS, plan_next
from mediafactory.schedule.timing import parse_times, zone

router = APIRouter(prefix="/api/schedules", tags=["schedules"])


class ProduceParams(BaseModel):
    count: int = Field(default=1, ge=1, le=20)
    languages: list[Literal["en", "tr"]] = Field(default_factory=lambda: ["en"], min_length=1, max_length=2)
    seconds: int = Field(default=50, ge=15, le=170)
    background: str = Field(default="random", max_length=120)
    style: CaptionStyle = Field(default_factory=CaptionStyle)
    voice: VoiceSettings = Field(default_factory=VoiceSettings)
    auto_approve: bool = False
    source_id: int | None = None
    min_chars: int | None = Field(default=None, ge=0, le=100_000)


class PublishParams(BaseModel):
    count: int = Field(default=1, ge=1, le=10)
    privacy: Literal["public", "unlisted", "private"] = "public"
    language: Literal["en", "tr"] | None = None


class ScheduleIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: Literal["produce", "publish"]
    enabled: bool = True
    times: list[str] = Field(min_length=1, max_length=24)
    weekdays: list[int] = Field(default_factory=lambda: list(range(7)), max_length=7)
    timezone: str = Field(default="UTC", max_length=64)
    params: dict = Field(default_factory=dict)

    @field_validator("times")
    @classmethod
    def _times(cls, v: list[str]) -> list[str]:
        return [f"{h:02d}:{m:02d}" for h, m in parse_times(v)]

    @field_validator("weekdays")
    @classmethod
    def _days(cls, v: list[int]) -> list[int]:
        if not v or not set(v) <= set(range(7)):
            raise ValueError("pick at least one weekday (0 = Monday … 6 = Sunday)")
        return sorted(set(v))

    @field_validator("timezone")
    @classmethod
    def _tz(cls, v: str) -> str:
        zone(v)
        return v

    def clean_params(self) -> dict:
        model = ProduceParams if self.kind == "produce" else PublishParams
        return model(**self.params).model_dump()


def out(s: Schedule) -> dict:
    return {
        "id": s.id, "name": s.name, "kind": s.kind, "enabled": s.enabled, "times": s.times, "weekdays": s.weekdays,
        "timezone": s.timezone, "params": s.params,
        "next_run_at": s.next_run_at.isoformat() if s.next_run_at else None,
        "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None, "last_result": s.last_result,
    }  # fmt: skip


def _get(db: Session, sid: int) -> Schedule:
    s = db.get(Schedule, sid)
    if s is None:
        raise HTTPException(status_code=404, detail="schedule not found")
    return s


def _apply(s: Schedule, body: ScheduleIn) -> None:
    try:
        params = body.clean_params()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    s.name, s.kind, s.enabled, s.times, s.weekdays, s.timezone, s.params = (
        body.name, body.kind, body.enabled, body.times, body.weekdays, body.timezone, params)  # fmt: skip
    plan_next(s, datetime.now(timezone.utc))


@router.get("")
def list_schedules(db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)) -> dict:
    return {"items": [out(s) for s in db.scalars(select(Schedule).order_by(Schedule.id))]}


@router.post("", status_code=201)
def create_schedule(
    body: ScheduleIn, request: Request, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)
) -> dict:
    s = Schedule()
    _apply(s, body)
    db.add(s)
    db.flush()
    record_audit(db, actor_id=user.id, action="schedule.create", target_type="schedule", target_id=str(s.id),
                 details={"name": s.name, "kind": s.kind}, ip=client_ip(request))  # fmt: skip
    return out(s)


@router.put("/{sid}")
def update_schedule(
    sid: int, body: ScheduleIn, request: Request, db: Session = Depends(get_db, scope="function"),
    user: User = Depends(require_user),
) -> dict:  # fmt: skip
    s = _get(db, sid)
    _apply(s, body)
    record_audit(db, actor_id=user.id, action="schedule.update", target_type="schedule", target_id=str(sid),
                 ip=client_ip(request))  # fmt: skip
    return out(s)


@router.delete("/{sid}")
def delete_schedule(
    sid: int, request: Request, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)
) -> dict:
    db.delete(_get(db, sid))
    record_audit(db, actor_id=user.id, action="schedule.delete", target_type="schedule", target_id=str(sid),
                 ip=client_ip(request))  # fmt: skip
    return {"ok": True}


@router.post("/{sid}/run")
def run_now(sid: int, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)) -> dict:
    s = _get(db, sid)
    try:
        with db.begin_nested():
            s.last_result = ACTIONS[s.kind](db, s)
    except Exception as exc:
        s.last_result = f"error: {exc}"[:1000]
    s.last_run_at = datetime.now(timezone.utc)
    return out(s)
