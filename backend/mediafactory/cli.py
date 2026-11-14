"""`mf` command line entry point."""

import typer

app = typer.Typer(help="CiciByte AI Media Factory", no_args_is_help=True)


@app.callback()
def main() -> None:
    """CiciByte AI Media Factory command line."""


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
            user.password_hash = hash_password(password)
            user.role = "admin"
            user.is_active = True
            action = "password reset"
    typer.echo(f"admin {action}: {email}")
    typer.echo(f"password: {password}")
    typer.echo("Store it safely; it will not be shown again.")
