from sqlalchemy import select

from mediafactory.db.models import AuditLog, SystemSetting
from mediafactory.sources.credentials import get_reddit_credentials
from tests.helpers import csrf_headers, login

BODY = {"client_id": "my-client", "client_secret": "super-secret-value"}


def admin(client, make_user):
    make_user()
    login(client)
    return csrf_headers(client)


def test_not_configured_initially(client, make_user):
    admin(client, make_user)
    assert client.get("/api/source-credentials").json() == {"reddit": {"configured": False, "client_id": None}}


def test_credentials_put_get_never_returns_secret(client, make_user, db):
    h = admin(client, make_user)
    assert client.put("/api/source-credentials/reddit", json=BODY, headers=h).status_code == 200
    body = client.get("/api/source-credentials").json()
    assert body == {"reddit": {"configured": True, "client_id": "my-client"}}
    stored = db.get(SystemSetting, "credentials.reddit").value
    assert "super-secret-value" not in str(stored)
    assert get_reddit_credentials(db) == BODY


def test_delete_credentials(client, make_user, db):
    h = admin(client, make_user)
    client.put("/api/source-credentials/reddit", json=BODY, headers=h)
    assert client.delete("/api/source-credentials/reddit", headers=h).status_code == 204
    assert get_reddit_credentials(db) is None



def test_credentials_audited_masked(client, make_user, db):
    h = admin(client, make_user)
    client.put("/api/source-credentials/reddit", json=BODY, headers=h)
    row = db.scalar(select(AuditLog).where(AuditLog.action == "source_credentials.update"))
    assert row is not None and "super-secret-value" not in str(row.details)
