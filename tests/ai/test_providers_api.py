import httpx
import respx
from sqlalchemy import select

from mediafactory.core.crypto import decrypt
from mediafactory.db.models import AIProvider, AuditLog
from tests.helpers import csrf_headers, login

NEW = {"name": "router", "base_url": "http://ai-router:20128/v1", "api_key": "sk-supersecret-123", "locality": "remote"}


def admin(client, make_user):
    make_user()
    login(client)
    return csrf_headers(client)


def test_create_and_list_never_returns_key(client, make_user):
    h = admin(client, make_user)
    r = client.post("/api/providers", json=NEW, headers=h)
    assert r.status_code == 201
    body = r.json()
    assert body["has_api_key"] is True and "api_key" not in body and "api_key_enc" not in body
    listed = client.get("/api/providers").json()["items"]
    assert "sk-supersecret-123" not in str(listed)


def test_api_key_stored_encrypted(client, make_user, db):
    h = admin(client, make_user)
    client.post("/api/providers", json=NEW, headers=h)
    row = db.scalar(select(AIProvider).where(AIProvider.name == "router"))
    assert row.api_key_enc != "sk-supersecret-123"
    assert decrypt(row.api_key_enc) == "sk-supersecret-123"


def test_default_timeout_by_locality(client, make_user):
    h = admin(client, make_user)
    local = client.post("/api/providers", json={**NEW, "name": "l", "locality": "local"}, headers=h).json()
    remote = client.post("/api/providers", json=NEW, headers=h).json()
    assert local["timeout_s"] == 600 and remote["timeout_s"] == 120


def test_duplicate_name_409(client, make_user):
    h = admin(client, make_user)
    client.post("/api/providers", json=NEW, headers=h)
    assert client.post("/api/providers", json=NEW, headers=h).status_code == 409


def test_provider_create_is_audited(client, make_user, db):
    h = admin(client, make_user)
    client.post("/api/providers", json=NEW, headers=h)
    row = db.scalar(select(AuditLog).where(AuditLog.action == "provider.create"))
    assert row is not None and "sk-supersecret-123" not in str(row.details)


def test_patch_and_clear_key(client, make_user):
    h = admin(client, make_user)
    pid = client.post("/api/providers", json=NEW, headers=h).json()["id"]
    r = client.patch(f"/api/providers/{pid}", json={"enabled": False, "api_key": ""}, headers=h)
    assert r.status_code == 200 and r.json()["enabled"] is False and r.json()["has_api_key"] is False


def test_delete(client, make_user):
    h = admin(client, make_user)
    pid = client.post("/api/providers", json=NEW, headers=h).json()["id"]
    assert client.delete(f"/api/providers/{pid}", headers=h).status_code == 204
    assert client.get("/api/providers").json()["items"] == []


def test_test_endpoint_lists_models(client, make_user):
    h = admin(client, make_user)
    pid = client.post("/api/providers", json=NEW, headers=h).json()["id"]
    with respx.mock(assert_all_called=False) as mock:
        mock.route(host="testserver").pass_through()
        mock.get("http://ai-router:20128/v1/models").mock(
            return_value=httpx.Response(200, json={"data": [{"id": "mf-senaryo"}, {"id": "local/qwen"}]})
        )
        r = client.post(f"/api/providers/{pid}/test", headers=h).json()
    assert r == {"ok": True, "models": ["mf-senaryo", "local/qwen"]}


def test_test_endpoint_reports_failure(client, make_user):
    h = admin(client, make_user)
    pid = client.post("/api/providers", json=NEW, headers=h).json()["id"]
    with respx.mock(assert_all_called=False) as mock:
        mock.route(host="testserver").pass_through()
        mock.get("http://ai-router:20128/v1/models").mock(side_effect=httpx.ConnectError("refused"))
        r = client.post(f"/api/providers/{pid}/test", headers=h).json()
    assert r["ok"] is False and r["error"]



def test_duplicate_name_keeps_session_usable(client, make_user):
    h = admin(client, make_user)
    client.post("/api/providers", json=NEW, headers=h)
    assert client.post("/api/providers", json=NEW, headers=h).status_code == 409
    assert client.get("/api/auth/me").status_code == 200


def test_rename_conflict_409_keeps_original(client, make_user):
    h = admin(client, make_user)
    client.post("/api/providers", json=NEW, headers=h)
    other = client.post("/api/providers", json={**NEW, "name": "other"}, headers=h).json()["id"]
    assert client.patch(f"/api/providers/{other}", json={"name": "router"}, headers=h).status_code == 409
    names = sorted(p["name"] for p in client.get("/api/providers").json()["items"])
    assert names == ["other", "router"]
