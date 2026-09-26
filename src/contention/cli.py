"""The `contention` command line: operations such as migrations and refreshes."""

import typer

from contention import db

app = typer.Typer()


@app.callback()
def main() -> None:
    """Content intelligence over a public YouTube Corpus."""


@app.command()
def migrate() -> None:
    """Apply pending database migrations."""
    with db.connect() as conn:
        applied = db.migrate(conn, db.MIGRATIONS_DIR)
    if applied:
        for name in applied:
            typer.echo(f"applied {name}")
    else:
        typer.echo("already up to date")
