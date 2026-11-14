"""`mf` command line entry point."""

import typer

app = typer.Typer(help="CiciByte AI Media Factory", no_args_is_help=True)


@app.callback()
def main() -> None:
    """CiciByte AI Media Factory command line."""


@app.command("migrate")
def migrate(revision: str = typer.Argument("head", help="Target revision")) -> None:
    """Apply database migrations (works from an installed package, no repo checkout needed)."""
    from pathlib import Path

    from alembic import command
    from alembic.config import Config

    import mediafactory.db as db_pkg
    from mediafactory.core.config import get_settings

    cfg = Config()
    cfg.set_main_option("script_location", str(Path(db_pkg.__file__).parent / "migrations"))
    cfg.set_main_option("sqlalchemy.url", get_settings().database_url)
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
    from mediafactory.core.config import get_settings

    settings = get_settings()
    uvicorn.run(
        create_app(settings),
        host=host or settings.bind_host,
        port=port or settings.bind_port,
        proxy_headers=False,  # handled in create_app() with MF_TRUSTED_PROXIES
    )


@app.command("worker")
def worker() -> None:
    """Run the background worker that processes queued production stages."""
    import logging
    import signal

    import mediafactory.pipeline.handlers  # noqa: F401  (register stage handlers)
    from mediafactory.db.session import SessionLocal
    from mediafactory.queue.worker import run_worker

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
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
    run_worker(SessionLocal, should_stop=lambda: stopping["flag"])


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
