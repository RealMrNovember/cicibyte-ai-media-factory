import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def factory(engine):
    """Real committing sessions (queue tests need several connections); tables are wiped after."""

    def _wipe():
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE job_stage_runs, production_jobs RESTART IDENTITY CASCADE"))
            conn.execute(text("DELETE FROM system_settings WHERE key = 'worker.heartbeat'"))  # left by run_worker

    _wipe()
    yield sessionmaker(bind=engine, expire_on_commit=False)
    _wipe()


@pytest.fixture
def registry():
    from mediafactory.queue import registry as reg

    saved = dict(reg.HANDLERS)
    reg.HANDLERS.clear()
    yield reg
    reg.HANDLERS.clear()
    reg.HANDLERS.update(saved)
