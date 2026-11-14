from fastapi.testclient import TestClient

from mediafactory import __version__
from mediafactory.api.app import create_app
from mediafactory.core.config import Settings
from tests.conftest import TEST_DATABASE_URL

KEY = "k" * 40


def settings(**kw):
    base = {"database_url": TEST_DATABASE_URL, "secret_key": KEY, "allowed_hosts": ["testserver"]}
    return Settings(_env_file=None, **{**base, **kw})


def test_health_ok(migrated):
    r = TestClient(create_app(settings())).get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "db": "up", "version": __version__}


def test_health_db_down_returns_503():
    bad = settings(database_url="postgresql+psycopg://mf:mf@127.0.0.1:1/nope")
    r = TestClient(create_app(bad)).get("/api/health")
    assert r.status_code == 503
    assert r.json()["db"] == "down" and r.json()["status"] == "degraded"


def test_unknown_host_rejected(migrated):
    client = TestClient(create_app(settings()), base_url="http://evil.example")
    assert client.get("/api/health").status_code == 400


def test_security_headers_present(migrated):
    r = TestClient(create_app(settings())).get("/api/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Referrer-Policy"] == "same-origin"
    assert "default-src 'self'" in r.headers["Content-Security-Policy"]


def test_api_docs_disabled(migrated):
    assert TestClient(create_app(settings())).get("/docs").status_code == 404
