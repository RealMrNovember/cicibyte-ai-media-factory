"""Settings export / import (Settings → Backup & move)."""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from mediafactory.api.deps import client_ip, get_db, require_user
from mediafactory.audit.service import record_audit
from mediafactory.db.models import User
from mediafactory.portability import PortabilityError, export_settings, import_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])
MAX_FILE = 5 * 1024 * 1024


class ExportIn(BaseModel):
    password: str | None = Field(default=None, max_length=200)


@router.post("/export")
def export_file(
    body: ExportIn, request: Request, db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user)
) -> Response:
    if body.password is not None and 0 < len(body.password) < 6:
        raise HTTPException(status_code=422, detail="use a password of at least 6 characters")
    data = export_settings(db, password=body.password or None)
    record_audit(db, actor_id=user.id, action="settings.export", details={"with_secrets": bool(body.password)},
                 ip=client_ip(request))  # fmt: skip
    name = f"mediafactory-settings-{datetime.now():%Y%m%d-%H%M}.json"
    return Response(json.dumps(data, ensure_ascii=False, indent=2), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})  # fmt: skip


@router.post("/import")
def import_file(
    request: Request, file: UploadFile = File(...), password: str = Form("", max_length=200),
    db: Session = Depends(get_db, scope="function"), user: User = Depends(require_user),
) -> dict:  # fmt: skip
    raw = file.file.read(MAX_FILE + 1)
    if len(raw) > MAX_FILE:
        raise HTTPException(status_code=422, detail="file is too large")
    try:
        payload = json.loads(raw.decode("utf-8"))
        summary = import_settings(db, payload, password=password or None)
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="this is not a valid settings file") from None
    except PortabilityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    record_audit(db, actor_id=user.id, action="settings.import", details=summary, ip=client_ip(request))
    return summary
