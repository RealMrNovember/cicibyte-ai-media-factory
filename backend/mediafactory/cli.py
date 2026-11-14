"""`mf` command line entry point."""

import typer

app = typer.Typer(help="CiciByte AI Media Factory", no_args_is_help=True)


@app.callback()
def main() -> None:
    """CiciByte AI Media Factory command line."""
