from sqlalchemy import select

from mediafactory.db.models import AIProvider, AuditLog
from tests.helpers import csrf_headers, login


def setup(client, make_user, db):
    make_user()
    login(client)
    p = AIProvider(name="router", base_url="http://r/v1", locality="remote", timeout_s=120)
    db.add(p)
    db.flush()
    return csrf_headers(client), p


def test_put_and_get_route(client, make_user, db):
    h, p = setup(client, make_user, db)
    body = {"steps": [{"provider_id": p.id, "model": "mf-senaryo"}], "rounds": 3, "retry_delay_s": 3}
    r = client.put("/api/task-routes/script", json=body, headers=h)
    assert r.status_code == 200
    items = client.get("/api/task-routes").json()["items"]
    assert items == [{"task": "script", "steps": body["steps"], "rounds": 3, "retry_delay_s": 3.0}]
    assert db.scalar(select(AuditLog).where(AuditLog.action == "task_route.update")) is not None


def test_defaults_are_3_rounds_3_seconds(client, make_user, db):
    h, p = setup(client, make_user, db)
    r = client.put("/api/task-routes/classify", json={"steps": [{"provider_id": p.id, "model": "m"}]}, headers=h)
    assert r.json()["rounds"] == 3 and r.json()["retry_delay_s"] == 3.0


def test_unknown_task_404(client, make_user, db):
    h, p = setup(client, make_user, db)
    r = client.put("/api/task-routes/dance", json={"steps": []}, headers=h)
    assert r.status_code == 404


def test_unknown_provider_rejected(client, make_user, db):
    h, _ = setup(client, make_user, db)
    r = client.put("/api/task-routes/script", json={"steps": [{"provider_id": 999999, "model": "m"}]}, headers=h)
    assert r.status_code == 422
