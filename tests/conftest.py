import os

import pytest
from fastapi.testclient import TestClient

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg://mf:mf@127.0.0.1:55432/mf_test")
os.environ["MF_DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("MF_SECRET_KEY", "test-secret-key-0123456789abcdef0123456789")
os.environ.setdefault("MF_ALLOWED_HOSTS", '["testserver","localhost","127.0.0.1"]')


def _alembic_config():
    from alembic.config import Config

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = Config(os.path.join(root, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(root, "backend", "mediafactory", "db", "migrations"))
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    return cfg


@pytest.fixture(scope="session")
def alembic_cfg():
    return _alembic_config()


@pytest.fixture(scope="session")
def migrated(alembic_cfg):
    from alembic import command

    command.downgrade(alembic_cfg, "base")
    command.upgrade(alembic_cfg, "head")
    yield
    # leave schema in place for inspection; next session resets it


@pytest.fixture
def engine(migrated):
    from mediafactory.db.session import get_engine

    return get_engine()


@pytest.fixture
def db(engine):
    """A session bound to a transaction that is rolled back after the test."""
    from sqlalchemy.orm import Session

    conn = engine.connect()
    trans = conn.begin()
    session = Session(bind=conn, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        conn.close()


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
    from mediafactory.auth.passwords import hash_password
    from mediafactory.db.models import User

    def _make(email="admin@example.com", password="correct horse battery", role="admin"):
        user = User(email=email, password_hash=hash_password(password), role=role)
        db.add(user)
        db.flush()
        return user

    return _make
