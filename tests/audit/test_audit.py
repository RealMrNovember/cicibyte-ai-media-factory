from sqlalchemy import select

from mediafactory.audit.service import record_audit
from mediafactory.db.models import AuditLog
from tests.helpers import login




def test_details_are_redacted(db):
    record_audit(db, actor_id=None, action="provider.create", details={"api_key": "sk-secret123456", "name": "x"})
    db.flush()
    row = db.scalar(select(AuditLog).where(AuditLog.action == "provider.create"))
    assert "sk-secret123456" not in str(row.details)
    assert row.details["name"] == "x"



def test_audit_list_newest_first(client, make_user, db):
    record_audit(db, actor_id=None, action="test.earlier")
    db.flush()
    record_audit(db, actor_id=None, action="test.later")
    db.flush()
    items = client.get("/api/audit?limit=2").json()["items"]
    assert items[0]["action"] == "test.later"
    assert items[1]["action"] == "test.earlier"


def test_compound_secret_keys_masked(db):
    record_audit(
        db, actor_id=None, action="x.compound",
        details={"client_secret": "cs-123", "refresh_token": "rt-456", "db_password": "pw-789", "name": "keep"},
    )  # fmt: skip
    db.flush()
    row = db.scalar(select(AuditLog).where(AuditLog.action == "x.compound"))
    assert not {"cs-123", "rt-456", "pw-789"} & set(str(row.details).replace("'", " ").split())
    assert row.details["name"] == "keep"
