"""`mf` command line entry point."""

from pathlib import Path

import typer

app = typer.Typer(help="CiciByte AI Media Factory", no_args_is_help=True)


@app.callback()
def main() -> None:
    """CiciByte AI Media Factory command line."""


def _load_settings():
    """Settings, or a short readable message (not a traceback) when required ones are missing or invalid."""
    from pydantic import ValidationError

    from mediafactory.core.config import get_settings

    try:
        return get_settings()
    except ValidationError as exc:
        lines = []
        for err in exc.errors():
            name = "MF_" + str(err["loc"][0]).upper() if err.get("loc") else "settings"
            lines.append(f"  {name}: {err['msg']}")
        typer.echo("Settings problem (set these in .env or /etc/mediafactory/env):\n" + "\n".join(lines), err=True)
        raise typer.Exit(2) from None


def wait_for_database(check, *, timeout_s: float = 60, sleep=None) -> bool:
    """Call check() until it stops raising (the database accepts connections) or timeout_s passes."""
    import time

    sleep = sleep or time.sleep
    waited = 0.0
    while True:
        try:
            check()
            return True
        except Exception:  # noqa: BLE001 - any connection problem means "not yet"
            if waited + 2 > timeout_s:
                return False
            sleep(2)
            waited += 2


def stop_requested(data_dir: Path) -> bool:
    """True when the desktop app asked the engine to stop (a file, since Windows has no gentle SIGTERM)."""
    return (Path(data_dir) / "engine.stop").exists()


def _setup_logging(settings) -> None:
    import logging
    import logging.handlers

    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    if settings.log_file:
        handler = logging.handlers.RotatingFileHandler(settings.log_file, maxBytes=5 * 2**20, backupCount=5, encoding="utf-8")
        handler.setFormatter(logging.Formatter(fmt))
        logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    else:
        logging.basicConfig(level=logging.INFO, format=fmt)


def health_host(allowed: list[str]) -> str:
    """A host name the API accepts, for the container health check (wildcards are not names)."""
    return next((h for h in allowed if h and "*" not in h), "localhost")


@app.command("healthcheck")
def healthcheck() -> None:
    """Exit 0 when the API answers /api/health (used by Docker; sends an allowed Host name)."""
    import urllib.request

    settings = _load_settings()
    req = urllib.request.Request(f"http://127.0.0.1:{settings.bind_port}/api/health",
                                 headers={"Host": health_host(settings.allowed_hosts)})  # fmt: skip
    try:
        with urllib.request.urlopen(req, timeout=4) as r:  # noqa: S310 - our own API on loopback
            ok = r.status == 200
    except Exception:  # noqa: BLE001
        ok = False
    raise typer.Exit(0 if ok else 1)


@app.command("migrate")
def migrate(revision: str = typer.Argument("head", help="Target revision")) -> None:
    """Apply database migrations (works from an installed package, no repo checkout needed)."""
    from pathlib import Path

    from alembic import command
    from alembic.config import Config

    import mediafactory.db as db_pkg

    settings = _load_settings()

    def _ping():
        from sqlalchemy import create_engine, text

        engine = create_engine(settings.database_url, connect_args={"connect_timeout": 3})
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        finally:
            engine.dispose()

    if not wait_for_database(_ping, timeout_s=60):
        typer.echo("the database did not accept connections within 60 seconds", err=True)
        raise typer.Exit(1)
    cfg = Config()
    cfg.set_main_option("script_location", str(Path(db_pkg.__file__).parent / "migrations"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, revision)
    typer.echo(f"database migrated to {revision}")


@app.command("make")
def make(
    item: int = typer.Option(..., help="Source item id"),
    lang: str = typer.Option("en", help="Narration language (en, tr)"),
    seconds: int = typer.Option(50, help="Target length in seconds"),
    background: str = typer.Option(None, help="Optional background video clip"),
) -> None:
    """Produce a 9:16 Short from one source item (script -> voice -> captions -> video)."""
    from pathlib import Path

    from mediafactory.core.config import get_settings
    from mediafactory.db.session import session_scope
    from mediafactory.pipeline.make import make_short

    with session_scope() as session:
        result = make_short(
            session, item, language=lang, seconds=seconds, data_dir=Path(get_settings().data_dir),
            background=Path(background) if background else None, log=typer.echo,
        )  # fmt: skip
    typer.echo(result["video"])


@app.command("api")
def api(
    host: str = typer.Option(None, help="Bind address (default: MF_BIND_HOST)"),
    port: int = typer.Option(None, help="Bind port (default: MF_BIND_PORT)"),
) -> None:
    """Serve the REST API and panel."""
    import uvicorn

    from mediafactory.api.app import create_app

    settings = _load_settings()
    _setup_logging(settings)
    uvicorn.run(
        create_app(settings),
        host=host or settings.bind_host,
        port=port or settings.bind_port,
        proxy_headers=False,  # handled in create_app() with MF_TRUSTED_PROXIES
        log_config=None if settings.log_file else uvicorn.config.LOGGING_CONFIG,
    )


@app.command("worker")
def worker() -> None:
    """Run the background worker that processes queued production stages."""
    import signal

    import mediafactory.pipeline.handlers  # noqa: F401  (register stage handlers)
    from mediafactory.core.config import get_settings as _gs
    from mediafactory.db.session import SessionLocal
    from mediafactory.queue.worker import run_worker

    _setup_logging(_gs())
    stopping = {"flag": False}

    def _stop(*_):
        stopping["flag"] = True

    import threading

    from mediafactory.core.config import get_settings
    from mediafactory.core.net import SafeFetcher
    from mediafactory.sources.poller import SourcePoller

    poller_stop = threading.Event()

    def _stop_all(*_):
        _stop()
        poller_stop.set()

    signal.signal(signal.SIGTERM, _stop_all)
    signal.signal(signal.SIGINT, _stop_all)
    from mediafactory.core.throttle import DbHostThrottle

    fetcher = SafeFetcher(allowlist=get_settings().fetch_allowlist, throttle=DbHostThrottle(SessionLocal))
    SourcePoller(SessionLocal, fetcher=fetcher, stop_event=poller_stop).start()
    from mediafactory.schedule.runner import Scheduler

    Scheduler(SessionLocal, stop_event=poller_stop).start()
    data_dir = Path(get_settings().data_dir)

    def should_stop() -> bool:
        if not stopping["flag"] and stop_requested(data_dir):
            _stop_all()
        return stopping["flag"]

    run_worker(SessionLocal, should_stop=should_stop)


@app.command("create-admin")
def create_admin(
    email: str = typer.Option(..., help="Admin e-mail address"),
    reset: bool = typer.Option(False, "--reset", help="Reset the password if the user already exists"),
) -> None:
    """Create the admin account (or reset its password with --reset). Prints a generated password once."""
    from sqlalchemy import func, select

    from mediafactory.auth.passwords import generate_password, hash_password
    from mediafactory.db.models import User
    from mediafactory.db.session import session_scope

    password = generate_password()
    with session_scope() as session:
        user = session.scalar(select(User).where(func.lower(User.email) == email.lower()))
        if user is not None and not reset:
            typer.echo(f"user {email} already exists; use --reset to set a new password", err=True)
            raise typer.Exit(code=1)
        if user is None:
            user = User(email=email, role="admin", password_hash=hash_password(password))
            session.add(user)
            action = "created"
        else:
            from mediafactory.auth.service import end_all_sessions

            user.password_hash = hash_password(password)
            user.role = "admin"
            user.is_active = True
            end_all_sessions(user)
            action = "password reset"
    typer.echo(f"admin {action}: {email}")
    typer.echo(f"password: {password}")
    typer.echo("Store it safely; it will not be shown again.")


def _session_factory():
    from mediafactory.db.session import SessionLocal

    return SessionLocal


@app.command("busy")
def busy() -> None:
    """Exit 0 when no production stage is running, 3 when one is (the updater waits for it)."""
    from sqlalchemy import func, select

    from mediafactory.db.models import JobStageRun

    with _session_factory()() as s:
        running = s.scalar(select(func.count()).select_from(JobStageRun).where(JobStageRun.state == "running")) or 0
    typer.echo(f"{running} running")
    raise typer.Exit(3 if running else 0)
