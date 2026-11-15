"""Task routing: try each configured (provider, model) step in order; after a full failed round,
wait `retry_delay_s` and start over, for at most `rounds` rounds."""

import logging
import time
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from mediafactory.ai.client import ChatResult, ProviderError, chat
from mediafactory.db.models import AIProvider, AITaskRoute

log = logging.getLogger(__name__)


class TaskNotConfigured(Exception):
    retryable = False  # a missing route will not appear by retrying: the worker fails the stage at once

    def __init__(self, task: str):
        super().__init__(f"no AI route configured for task '{task}'")
        self.task = task


class TaskFailed(Exception):
    def __init__(self, task: str, errors: list[str]):
        super().__init__(f"all AI providers failed for task '{task}' ({len(errors)} attempts)")
        self.task = task
        self.errors = errors


def run_task(
    session: Session,
    task: str,
    messages: list[dict],
    *,
    json_schema: dict | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> ChatResult:
    route = session.scalar(select(AITaskRoute).where(AITaskRoute.task == task))
    if route is None or not route.steps:
        raise TaskNotConfigured(task)
    errors: list[str] = []
    rounds = max(1, route.rounds)
    for round_no in range(1, rounds + 1):
        for step in route.steps:
            provider = session.get(AIProvider, step.get("provider_id"))
            if provider is None or not provider.enabled:
                continue
            model = step.get("model", "")
            try:
                return chat(
                    provider, model, messages, json_schema=json_schema, max_tokens=max_tokens, temperature=temperature
                )
            except ProviderError as exc:
                msg = f"round {round_no} {provider.name}/{model}: {exc}"
                log.warning("AI step failed: %s", msg)
                errors.append(msg)
        if round_no < rounds:
            sleep(route.retry_delay_s)
    raise TaskFailed(task, errors)
