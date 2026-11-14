import re

import pytest
from typer.testing import CliRunner

from mediafactory.auth.passwords import verify_password
from mediafactory.cli import app
from mediafactory.db.models import User

runner = CliRunner()


@pytest.fixture
def clean_users(engine):
    from sqlalchemy import delete
    from sqlalchemy.orm import Session

    def _wipe():
        with Session(engine) as s:
            s.execute(delete(User).where(User.email == "boss@example.com"))
            s.commit()

    _wipe()
    yield
    _wipe()


def _password(output: str) -> str:
    m = re.search(r"password:\s*(\S+)", output)
    assert m, output
    return m.group(1)


def _stored_hash(engine) -> str:
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    with Session(engine) as s:
        return s.scalar(select(User.password_hash).where(User.email == "boss@example.com"))


def test_create_admin_prints_password(engine, clean_users):
    r = runner.invoke(app, ["create-admin", "--email", "boss@example.com"])
    assert r.exit_code == 0, r.output
    pw = _password(r.output)
    assert len(pw) >= 20
    assert verify_password(pw, _stored_hash(engine))


def test_create_admin_twice_without_reset_fails(engine, clean_users):
    first = runner.invoke(app, ["create-admin", "--email", "boss@example.com"])
    before = _stored_hash(engine)
    second = runner.invoke(app, ["create-admin", "--email", "boss@example.com"])
    assert second.exit_code == 1
    assert _stored_hash(engine) == before
    assert verify_password(_password(first.output), before)


def test_create_admin_reset_changes_password(engine, clean_users):
    runner.invoke(app, ["create-admin", "--email", "boss@example.com"])
    before = _stored_hash(engine)
    r = runner.invoke(app, ["create-admin", "--email", "boss@example.com", "--reset"])
    assert r.exit_code == 0, r.output
    assert _stored_hash(engine) != before
    assert verify_password(_password(r.output), _stored_hash(engine))
