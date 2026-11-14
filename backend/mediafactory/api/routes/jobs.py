from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from mediafactory.api.deps import client_ip, get_db, require_user
from mediafactory.audit.service import record_audit
from mediafactory.core.config import get_settings
from mediafactory.db.models import JobStageRun, ProductionJob, SourceItem, User
from mediafactory.pipeline.handlers import MAKE_SHORT
from mediafactory.pipeline.style import CaptionStyle
from mediafactory.queue.jobs import JobBusy, cancel_job, create_job, enqueue_stage, retry_failed

router = APIRouter(prefix="/api", tags=["jobs"])


class MakeIn(BaseModel):
    languages: list[Literal["en", "tr"]] = Field(default_factory=lambda: ["en"], min_length=1, max_length=2)
    seconds: int = Field(default=50, ge=15, le=170)
    background: str = Field(default="random", max_length=120, description='"random", "none" or a library clip name')
    style: CaptionStyle = Field(default_factory=CaptionStyle)


def job_out(job: ProductionJob, runs: list[JobStageRun] | None = None) -> dict:
    result = (job.payload or {}).get("result") or {}
    out = {
        "id": job.id,
        "status": job.status,
        "language": job.language,
        "source_item_id": job.source_item_id,
        "content_group": job.content_group,
        "title": result.get("title") or (job.payload or {}).get("title"),
        "duration_s": result.get("duration_s"),
        "has_video": bool(result.get("video")),
        "youtube": (job.payload or {}).get("youtube"),
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }
    if runs is not None:
        out["stages"] = [
            {"stage": r.stage, "state": r.state, "attempts": r.attempts, "error": r.error, "log": r.log,
             "started_at": r.started_at.isoformat() if r.started_at else None,
             "finished_at": r.finished_at.isoformat() if r.finished_at else None}  # fmt: skip
            for r in runs
        ]
    return out


def _job(db: Session, jid: int) -> ProductionJob:
    job = db.get(ProductionJob, jid)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@router.post("/items/{iid}/make", status_code=201)
def make_from_item(
    iid: int, body: MakeIn, request: Request, db: Session = Depends(get_db, scope="function"),
    user: User = Depends(require_user),
) -> dict:  # fmt: skip
    item = db.get(SourceItem, iid)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    if body.background not in ("random", "none"):
        from mediafactory.pipeline.backgrounds import resolve

        if resolve(Path(get_settings().data_dir), body.background) is None:
            raise HTTPException(status_code=422, detail="background clip not found")
    from mediafactory.pipeline.production import start_production

    jobs = start_production(db, item, languages=body.languages, seconds=body.seconds, background=body.background,
                            style=body.style)  # fmt: skip
    record_audit(db, actor_id=user.id, action="job.make", target_type="source_item", target_id=str(iid),
                 details={"languages": body.languages, "jobs": [j.id for j in jobs]}, ip=client_ip(request))  # fmt: skip
    return {"jobs": [job_out(j) for j in jobs]}


@router.get("/jobs")
def list_jobs(
    status: str | None = None, limit: int = 50, db: Session = Depends(get_db, scope="function"),
    user: User = Depends(require_user),
) -> dict:  # fmt: skip
    q = select(ProductionJob).order_by(ProductionJob.id.desc()).limit(min(max(limit, 1), 200))
    if status:
        q = q.where(ProductionJob.status == status)
    return {"items": [job_out(j) for j in db.scalars(q).all()]}


@router.get("/jobs/{jid}")
def get_job(jid: int, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)) -> dict:
    job = _job(db, jid)
    runs = db.scalars(select(JobStageRun).where(JobStageRun.job_id == jid).order_by(JobStageRun.id)).all()
    out = job_out(job, list(runs))
    out["script"] = None
    video = ((job.payload or {}).get("result") or {}).get("video")
    if video:
        script = Path(video).parent / "script.json"
        if script.exists():
            import json

            out["script"] = json.loads(script.read_text(encoding="utf-8"))
    return out


@router.post("/jobs/{jid}/cancel")
def cancel(jid: int, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)) -> dict:
    _job(db, jid)
    cancel_job(db, jid)
    return job_out(_job(db, jid))


@router.post("/jobs/{jid}/retry")
def retry(jid: int, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)) -> dict:
    _job(db, jid)
    try:
        if retry_failed(db, jid) is None:
            raise HTTPException(status_code=409, detail="nothing to retry")
    except JobBusy:
        raise HTTPException(status_code=409, detail="job is still running") from None
    return job_out(_job(db, jid))


class DecisionIn(BaseModel):
    decision: Literal["approve", "reject"]


@router.post("/jobs/{jid}/decision")
def decide(
    jid: int, body: DecisionIn, request: Request, db: Session = Depends(get_db, scope="function"),
    user: User = Depends(require_user),
) -> dict:  # fmt: skip
    job = _job(db, jid)
    if job.status not in ("needs_review", "approved", "rejected"):
        raise HTTPException(status_code=409, detail="video is not ready yet")
    job.status = "approved" if body.decision == "approve" else "rejected"
    record_audit(db, actor_id=user.id, action=f"job.{body.decision}", target_type="production_job",
                 target_id=str(jid), ip=client_ip(request))  # fmt: skip
    return job_out(job)


@router.get("/jobs/{jid}/video")
def video_file(jid: int, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)):
    job = _job(db, jid)
    video = ((job.payload or {}).get("result") or {}).get("video")
    if not video:
        raise HTTPException(status_code=404, detail="no video for this job")
    path = Path(video).resolve()
    root = (Path(get_settings().data_dir) / "videos").resolve()
    if root not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="video file missing")
    return FileResponse(path, media_type="video/mp4", filename=f"short-{jid}.mp4")
