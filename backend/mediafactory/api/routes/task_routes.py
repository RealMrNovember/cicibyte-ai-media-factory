from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from mediafactory.api.deps import client_ip, get_db, require_admin
from mediafactory.audit.service import record_audit
from mediafactory.db.models import AIProvider, AITaskRoute, User
from mediafactory.db.models.ai import TASKS

router = APIRouter(prefix="/api/task-routes", tags=["ai"])


class Step(BaseModel):
    provider_id: int
    model: str = Field(min_length=1, max_length=200)


class RouteIn(BaseModel):
    steps: list[Step] = Field(max_length=50)
    rounds: int = Field(default=3, ge=1, le=20)
    retry_delay_s: float = Field(default=3.0, ge=0, le=600)


def out(r: AITaskRoute) -> dict:
    return {"task": r.task, "steps": r.steps, "rounds": r.rounds, "retry_delay_s": float(r.retry_delay_s)}


@router.get("")
def list_routes(db: Session = Depends(get_db, scope="function"), user: User = Depends(require_admin)) -> dict:
    return {"items": [out(r) for r in db.scalars(select(AITaskRoute).order_by(AITaskRoute.task)).all()]}


@router.put("/{task}")
def put_route(
    task: str, body: RouteIn, request: Request, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_admin)
) -> dict:
    if task not in TASKS:
        raise HTTPException(status_code=404, detail=f"unknown task; expected one of {', '.join(TASKS)}")
    for step in body.steps:
        if db.get(AIProvider, step.provider_id) is None:
            raise HTTPException(status_code=422, detail=f"provider {step.provider_id} does not exist")
    route = db.scalar(select(AITaskRoute).where(AITaskRoute.task == task)) or AITaskRoute(task=task)
    route.steps = [s.model_dump() for s in body.steps]
    route.rounds = body.rounds
    route.retry_delay_s = body.retry_delay_s
    db.add(route)
    db.flush()
    record_audit(
        db, actor_id=user.id, action="task_route.update", target_type="ai_task_route", target_id=task,
        details=body.model_dump(), ip=client_ip(request),
    )  # fmt: skip
    return out(route)
