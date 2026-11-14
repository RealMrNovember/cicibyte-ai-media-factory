"""Version and automatic updates (Settings → Updates).

The app never updates itself directly: it only leaves files that the root-run updater
(deploy/update/mf-update.sh, systemd timer + path unit) reads, and shows the status it writes.
"""

import json
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from mediafactory import __version__
from mediafactory.api.deps import client_ip, get_db, require_user
from mediafactory.audit.service import record_audit
from mediafactory.core.config import get_settings
from mediafactory.db.models import User

router = APIRouter(prefix="/api/system", tags=["system"])
REPO = "https://github.com/RealMrNovember/cicibyte-ai-media-factory"


def _dir() -> Path:
    return Path(get_settings().data_dir) / "update"


def _read(name: str) -> dict | None:
    try:
        return json.loads((_dir() / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


@router.get("")
def system_info(user: User = Depends(require_user)) -> dict:
    status = _read("update-status.json")
    tail = ""
    try:
        tail = "\n".join((_dir() / "update.log").read_text(encoding="utf-8").splitlines()[-15:])
    except OSError:
        pass
    return {
        "version": __version__,
        "repository": REPO,
        "update": status,
        "auto": (_read("update-config.json") or {}).get("auto", True),
        "pending": (_dir() / "update-request").exists(),
        "log": tail,
    }


class ConfigIn(BaseModel):
    auto: bool


@router.put("/update-config")
def update_config(
    body: ConfigIn, request: Request, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)
) -> dict:
    _dir().mkdir(parents=True, exist_ok=True)
    (_dir() / "update-config.json").write_text(json.dumps({"auto": body.auto}), encoding="utf-8")
    record_audit(db, actor_id=user.id, action="system.autoupdate", details={"auto": body.auto}, ip=client_ip(request))
    return {"auto": body.auto}


class UpdateIn(BaseModel):
    force: bool = False


@router.post("/update", status_code=202)
def update_now(
    body: UpdateIn, request: Request, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)
):
    """Ask the updater to check now (and install if there is something new)."""
    _dir().mkdir(parents=True, exist_ok=True)
    (_dir() / "update-request").write_text("force" if body.force else "now", encoding="utf-8")
    record_audit(db, actor_id=user.id, action="system.update", details={"force": body.force}, ip=client_ip(request))
    return JSONResponse({"ok": True}, status_code=202)
