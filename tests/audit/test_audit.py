from sqlalchemy import select

from mediafactory.audit.service import record_audit
from mediafactory.db.models import AuditLog
from tests.helpers import login


def test_login_is_audited(client, make_user, db):
    user = make_user()
    login(client)
    rows = db.scalars(select(AuditLog).where(AuditLog.action == "auth.login")).all()
    assert len(rows) == 1 and rows[0].actor_id == user.id


def test_failed_login_is_audited(client, make_user, db):
    make_user()
    login(client, password="wrong")
    row = db.scalar(select(AuditLog).where(AuditLog.action == "auth.login_failed"))
    assert row is not None and row.details["email"] == "admin@example.com"


def test_details_are_redacted(db):
    record_audit(db, actor_id=None, action="provider.create", details={"api_key": "sk-secret123456", "name": "x"})
    db.flush()
    row = db.scalar(select(AuditLog).where(AuditLog.action == "provider.create"))
    assert "sk-secret123456" not in str(row.details)
    assert row.details["name"] == "x"


def test_audit_list_admin_only(client, make_user):
    make_user(email="ed@example.com", role="editor")
    login(client, email="ed@example.com")
    assert client.get("/api/audit").status_code == 403


def test_audit_list_newest_first(client, make_user, db):
    make_user()
    login(client)
    record_audit(db, actor_id=None, action="test.later")
    db.flush()
    items = client.get("/api/audit?limit=2").json()["items"]
    assert items[0]["action"] == "test.later"
    assert items[1]["action"] == "auth.login"
