import pytest
from pydantic import ValidationError

from mediafactory.core.config import Settings

DB = "postgresql+psycopg://u:p@localhost/db"


def test_missing_secret_key_raises(monkeypatch):
    monkeypatch.delenv("MF_SECRET_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url=DB)


def test_secret_key_too_short_rejected():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url=DB, secret_key="short")


def test_defaults():
    s = Settings(_env_file=None, database_url=DB, secret_key="x" * 32)
    assert s.bind_host == "127.0.0.1"
    assert s.bind_port == 8080
    assert s.session_ttl_hours == 72
