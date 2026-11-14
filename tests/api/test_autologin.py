import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def autologin_env(monkeypatch):
    from mediafactory.core.config import get_settings

    monkeypatch.setenv("MF_AUTOLOGIN_NETWORKS", '["100.64.0.0/10"]')
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_autologin_from_trusted_network_gives_admin_session(app, make_user, autologin_env):
    make_user()
    c = TestClient(app, client=("100.100.1.2", 50000))
    r = c.post("/api/auth/auto")
    assert r.status_code == 200
    assert r.json()["user"]["email"] == "admin@example.com"
    assert c.get("/api/auth/me").status_code == 200


def test_autologin_refused_outside_trusted_network(app, make_user, autologin_env):
    make_user()
    c = TestClient(app, client=("192.168.1.50", 50000))
    assert c.post("/api/auth/auto").status_code == 403


def test_autologin_off_by_default(app, make_user):
    make_user()
    c = TestClient(app, client=("100.100.1.2", 50000))
    assert c.post("/api/auth/auto").status_code == 403
