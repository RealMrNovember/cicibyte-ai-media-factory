"""Easy Setup: find or choose an AI, check it, save it as a provider + task routes, and try it.

There is no sign-in, so anyone who reaches the API counts as admin. Checking an arbitrary address is therefore
allowed only in local mode (the engine listens on 127.0.0.1 only); a server on a network accepts only the
ready-made services and its own 127.0.0.1 scan, so it never becomes an open proxy.
"""

import time
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from mediafactory.ai import client as ai_client
from mediafactory.ai import discovery, presets
from mediafactory.api.db_utils import save_unique
from mediafactory.api.deps import client_ip, get_db, require_admin
from mediafactory.audit.service import record_audit
from mediafactory.core.config import get_settings
from mediafactory.core.crypto import encrypt
from mediafactory.db.models import AIProvider, AITaskRoute, SystemSetting, User

router = APIRouter(prefix="/api/ai-setup", tags=["ai-setup"])
SETUP_KEY = "setup"
TRY_PROMPTS = {
    "tr": "Bir korku hikâyesinin ilk cümlesini yaz. Yalnızca o cümleyi yaz.",
    "en": "Write the first sentence of a horror story. Reply with that sentence only.",
}


class Target(BaseModel):
    preset: str | None = Field(default=None, max_length=40)
    base_url: str | None = Field(default=None, max_length=500)
    api_key: str | None = Field(default=None, max_length=500)
    model: str | None = Field(default=None, max_length=200)


class ApplyIn(Target):
    name: str | None = Field(default=None, max_length=100)
    script_model: str = Field(min_length=1, max_length=200)
    classify_model: str = Field(min_length=1, max_length=200)
    mode: Literal["primary", "only"] = "primary"


def _resolve(body: Target) -> tuple[str, str, dict, str]:
    """(display name, base_url, options, locality) for a preset or a custom address."""
    if body.preset:
        p = presets.get(body.preset)
        if p is None:
            raise HTTPException(status_code=404, detail="unknown service")
        return p["name"], p["base_url"], dict(p["options"]), "remote"
    if not body.base_url:
        raise HTTPException(status_code=422, detail="choose a service or enter an address")
    if not get_settings().local_mode:
        raise HTTPException(status_code=403, detail="custom AI addresses can be set up only in the app on this computer")
    base = discovery.normalize_base(body.base_url)
    local = "127.0.0.1" in base or "localhost" in base
    return "AI server", base, {}, "local" if local else "remote"


def _probe_provider(name: str, base: str, options: dict, locality: str, api_key: str | None) -> AIProvider:
    # Not added to the session: a throwaway object the client can use for one check.
    return AIProvider(name=name, kind="openai_compatible", base_url=base, locality=locality, timeout_s=30,
                      api_key_enc=encrypt(api_key) if api_key else None, options=options)  # fmt: skip


def _reason(exc: ai_client.ProviderError) -> tuple[str, str]:
    text = str(exc).lower()
    if exc.status in (401, 403) or "api key" in text or "unauthorized" in text:
        return "bad_key", "the API key was not accepted"
    if exc.status == 404 or "model" in text and "not" in text:
        return "no_model", "that model was not found for this key"
    if "timeout" in text:
        return "slow", "the AI took too long — try a smaller or faster model"
    if "connect" in text or "connection" in text:
        return "unreachable", "nothing answered at this address"
    return "error", str(exc)[:200]


@router.get("")
def status(db: Session = Depends(get_db, scope="function"), user: User = Depends(require_admin)) -> dict:
    routes = {r.task: r.steps for r in db.scalars(select(AITaskRoute))}
    row = db.get(SystemSetting, SETUP_KEY)
    return {"local_mode": get_settings().local_mode, "configured": bool(routes.get("script")),
            "setup_done": bool(row and isinstance(row.value, dict) and row.value.get("done")),
            "presets": [{k: p[k] for k in ("id", "name", "key_url", "models")} for p in presets.PRESETS],
            "downloads": discovery.DOWNLOADS}  # fmt: skip


@router.get("/scan")
def scan(user: User = Depends(require_admin)) -> dict:
    return {"found": discovery.scan()}


@router.post("/check")
def check(body: Target, user: User = Depends(require_admin)) -> dict:
    name, base, options, locality = _resolve(body)
    probe = _probe_provider(name, base, options, locality, body.api_key)
    try:
        models = ai_client.check_key(probe, body.model or (presets.get(body.preset)["models"][0] if body.preset else None))
    except ai_client.ProviderError as exc:
        reason, message = _reason(exc)
        return {"ok": False, "reason": reason, "error": message}
    return {"ok": True, "models": discovery.rank(models) if locality == "local" else models, "base_url": base}


def _route_steps(db: Session, task: str, provider_id: int, model: str, mode: str) -> None:
    route = db.scalar(select(AITaskRoute).where(AITaskRoute.task == task)) or AITaskRoute(task=task, rounds=3, retry_delay_s=3)
    new = {"provider_id": provider_id, "model": model}
    old = [s for s in (route.steps or []) if s.get("provider_id") != provider_id] if mode == "primary" else []
    route.steps = [new, *old]
    db.add(route)


@router.post("/apply")
def apply(
    body: ApplyIn, request: Request, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_admin)
) -> dict:  # fmt: skip
    name, base, options, locality = _resolve(body)
    name = (body.name or name).strip()[:100]
    prov = db.scalar(select(AIProvider).where(AIProvider.name == name))

    def save() -> None:
        nonlocal prov
        if prov is None:
            prov = AIProvider(name=name, kind="openai_compatible")
            db.add(prov)
        prov.base_url, prov.locality, prov.options, prov.enabled = base, locality, options, True
        prov.timeout_s = 600 if locality == "local" else 120
        if body.api_key:
            prov.api_key_enc = encrypt(body.api_key.strip())

    save_unique(db, save, "a provider with this name already exists")
    db.flush()
    _route_steps(db, "script", prov.id, body.script_model, body.mode)
    _route_steps(db, "classify", prov.id, body.classify_model, body.mode)
    db.flush()
    record_audit(db, actor_id=user.id, action="ai_setup.apply", target_type="ai_provider", target_id=str(prov.id),
                 details={"name": name, "base_url": base, "script": body.script_model, "classify": body.classify_model,
                          "mode": body.mode}, ip=client_ip(request))  # fmt: skip
    return {"provider": {"id": prov.id, "name": prov.name, "base_url": prov.base_url}}


@router.post("/try")
def try_it(db: Session = Depends(get_db, scope="function"), user: User = Depends(require_admin)) -> dict:
    from mediafactory.ai import router as ai_router

    t0 = time.monotonic()
    sample = {}
    try:
        for lang, prompt in TRY_PROMPTS.items():
            res = ai_router.run_task(db, "script", [{"role": "user", "content": prompt}], max_tokens=200)
            sample[lang] = res.text.strip()[:200]
    except Exception as exc:  # noqa: BLE001 - shown to the user in plain words
        errors = getattr(exc, "errors", None)
        return {"ok": False, "error": (errors[-1] if errors else str(exc))[:300]}
    return {"ok": True, "seconds": round(time.monotonic() - t0, 1), "sample": sample}


@router.post("/done")
def done(request: Request, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_admin)) -> dict:
    value = {"done": True, "at": datetime.now(UTC).isoformat()}
    row = db.get(SystemSetting, SETUP_KEY)
    if row is None:
        db.add(SystemSetting(key=SETUP_KEY, value=value))
    else:
        row.value = value
    record_audit(db, actor_id=user.id, action="ai_setup.done", ip=client_ip(request))
    return value
