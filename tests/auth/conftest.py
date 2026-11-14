import pytest
from fastapi.testclient import TestClient

from mediafactory.auth.passwords import hash_password
from mediafactory.db.models import User


@pytest.fixture
def app(db):
    from mediafactory.api.app import create_app
    from mediafactory.api.deps import get_db
    from mediafactory.auth import service

    service.reset_rate_limits()
    application = create_app()
    application.dependency_overrides[get_db] = lambda: db
    return application


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def make_user(db):
    def _make(email="admin@example.com", password="correct horse battery", role="admin"):
        user = User(email=email, password_hash=hash_password(password), role=role)
        db.add(user)
        db.flush()
        return user

    return _make


def login(client, email="admin@example.com", password="correct horse battery"):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def csrf_headers(client):
    return {"X-CSRF-Token": client.cookies.get("mf_csrf", "")}
