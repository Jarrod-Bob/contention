"""The `contention` command line: operations such as migrations and refreshes."""

import os
from datetime import UTC, datetime
from pathlib import Path

import typer
from dotenv import load_dotenv

from contention import db
from contention.artefacts import run_dir
from contention.channels import add_channel
from contention.collect import refresh as refresh_corpus
from contention.niche import TIERS, load_niche
from contention.purge import purge
from contention.search import search
from contention.youtube import HttpYouTube

NICHES_DIR = Path(__file__).resolve().parents[2] / "niches"
ARTEFACTS_DIR = Path(__file__).resolve().parents[2] / "artefacts"

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
    """Collect the Niche's Channels and their long-form English Videos, then delete what the Corpus may no longer hold."""
    youtube = _youtube()
    curated = load_niche(NICHES_DIR / niche)
    now = datetime.now(UTC)
    run = run_dir(ARTEFACTS_DIR, now)
    with db.connect() as conn:
        report = refresh_corpus(conn, youtube, curated, now=now)
        purged = purge(conn, curated, ARTEFACTS_DIR, now)
    lines = [
        f"refreshed {report.channels} Channels and {report.videos} Videos ({report.quota_used} quota units)",
        f"deleted {purged.channels} Channels, {purged.videos} Videos, {purged.snapshots} Snapshots"
        f" and {purged.runs} artefact runs",
    ]
    (run / "refresh.log").write_text("\n".join(lines) + "\n")
    for line in lines:
        typer.echo(line)
    for handle in report.unknown_handles:
        typer.echo(f"warning: YouTube has no Channel with the handle {handle}", err=True)


@app.command("search")
def search_command(
    query: str = typer.Argument(help="Words to look for in Video titles, Chapters, tags and descriptions."),
    limit: int = typer.Option(10, help="How many Videos to show."),
    niche: str = NICHE_OPTION,
) -> None:
    """Keyword-search the Niche's Videos (BM25) and print them best first."""
    with db.connect() as conn:
        results = search(conn, niche, query, limit=limit)
    if not results:
        typer.echo(f"no Videos match {query!r}")
    for rank, result in enumerate(results, start=1):
        typer.echo(f"{rank:>2}. {result.score:6.2f}  {result.title}  [{result.channel_title}]  {result.video_id}")
