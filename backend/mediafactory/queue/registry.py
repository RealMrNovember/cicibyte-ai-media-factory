"""Stage handler registry. Later plans register handlers for normalize, classify, script, voice, ..."""

from collections.abc import Callable
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from mediafactory.db.models import JobStageRun, ProductionJob


@dataclass
class StageOutcome:
    next_status: str
    outputs: dict = field(default_factory=dict)
    next_stage: tuple[str, str] | None = None  # (stage, job_class)


@dataclass
class StageContext:
    session: Session
    job: ProductionJob
    run: JobStageRun
    log: Callable[[str], None]
    is_cancelled: Callable[[], bool]


Handler = Callable[[StageContext], StageOutcome]


@dataclass
class _Entry:
    job_class: str
    fn: Handler


HANDLERS: dict[str, _Entry] = {}


def stage_handler(stage: str, job_class: str) -> Callable[[Handler], Handler]:
    def decorate(fn: Handler) -> Handler:
        HANDLERS[stage] = _Entry(job_class=job_class, fn=fn)
        return fn

    return decorate


def get_handler(stage: str) -> Handler | None:
    entry = HANDLERS.get(stage)
    return entry.fn if entry else None
