from alembic import command
from sqlalchemy import create_engine, inspect

from tests.conftest import TEST_DATABASE_URL

TABLES = {
    "users",
    "audit_logs",
    "system_settings",
    "ai_providers",
    "ai_task_routes",
    "production_jobs",
    "job_stage_runs",
    "source_connectors",
    "source_items",
    "source_rights_records",
}


def _tables():
    eng = create_engine(TEST_DATABASE_URL)
    try:
        return set(inspect(eng).get_table_names())
    finally:
        eng.dispose()


def test_upgrade_creates_tables(migrated):
    assert TABLES <= _tables()


def test_downgrade_base_is_clean(migrated, alembic_cfg):
    command.downgrade(alembic_cfg, "base")
    assert not (TABLES & _tables())
    command.upgrade(alembic_cfg, "head")
    assert TABLES <= _tables()
