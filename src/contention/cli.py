"""The `contention` command line: operations such as migrations and refreshes."""

import os
from datetime import UTC, datetime
from pathlib import Path

import typer
from dotenv import load_dotenv

from contention import db
from contention.channels import add_channel
from contention.collect import refresh as refresh_corpus
from contention.niche import TIERS, load_niche
from contention.youtube import HttpYouTube

NICHES_DIR = Path(__file__).resolve().parents[2] / "niches"

app = typer.Typer()
channels_app = typer.Typer(help="Curate the Channels of a Niche.")
app.add_typer(channels_app, name="channels")

NICHE_OPTION = typer.Option("tech-careers", help="The Niche folder under niches/.")


@app.callback()
def main() -> None:
    """Content intelligence over a public YouTube Corpus."""
    load_dotenv()


def _youtube() -> HttpYouTube:
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        typer.echo("No YOUTUBE_API_KEY in .env. Run scripts/setup-youtube-api-key.sh first.", err=True)
        raise typer.Exit(1)
    return HttpYouTube(key)


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


@channels_app.command("add")
def channels_add(
    handle: str = typer.Argument(help="The Channel's handle, e.g. @example."),
    tier: str = typer.Option(help=f"One of: {', '.join(TIERS)}."),
    reason: str = typer.Option(help="One line on why this Channel belongs in the Niche."),
    niche: str = NICHE_OPTION,
) -> None:
    """Add a Channel to the Niche's Channel list (checks the handle with YouTube: 1 quota unit)."""
    try:
        add_channel(NICHES_DIR / niche, _youtube(), handle, tier, reason)
    except ValueError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1)
    typer.echo(f"added {handle} ({tier}) to {niche}")


@app.command()
def refresh(niche: str = NICHE_OPTION) -> None:
    """Collect the Niche's Channels and their long-form English Videos from YouTube."""
    youtube = _youtube()
    with db.connect() as conn:
        report = refresh_corpus(conn, youtube, load_niche(NICHES_DIR / niche), now=datetime.now(UTC))
    typer.echo(f"refreshed {report.channels} Channels and {report.videos} Videos ({report.quota_used} quota units)")
    for handle in report.unknown_handles:
        typer.echo(f"warning: YouTube has no Channel with the handle {handle}", err=True)
