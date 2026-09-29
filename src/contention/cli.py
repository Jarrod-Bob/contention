"""The `contention` command line: operations such as migrations and refreshes."""

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import NoReturn

import psycopg
import typer
from dotenv import load_dotenv

from contention import db, demo
from contention.artefacts import run_dir
from contention.channels import add_channel
from contention.collect import refresh as refresh_corpus
from contention.niche import TIERS, load_niche
from contention.purge import purge, startup_guard
from contention.search import search as search_corpus
from contention.youtube import HttpYouTube

NICHES_DIR = Path(__file__).resolve().parents[2] / "niches"
ARTEFACTS_DIR = Path(__file__).resolve().parents[2] / "artefacts"

app = typer.Typer()
channels_app = typer.Typer(help="Curate the Channels of a Niche.")
app.add_typer(channels_app, name="channels")

DEFAULT_NICHE = "tech-careers"
NICHE_OPTION = typer.Option(DEFAULT_NICHE, help="The Niche folder under niches/.")
DATABASE_NICHE_OPTION = typer.Option(
    None, help=f"The Niche folder under niches/ (default: {DEFAULT_NICHE}, or {demo.NICHE} on the demo database).",
)


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
def refresh(niche: str | None = DATABASE_NICHE_OPTION) -> None:
    """Collect the Niche's Channels and their long-form English Videos, then delete what the Corpus may no longer hold.

    On the demo database this reads the synthetic Corpus instead of YouTube.
    """
    now = datetime.now(UTC)
    run = run_dir(ARTEFACTS_DIR, now)
    with db.connect() as conn:
        curated = load_niche(NICHES_DIR / _niche_on(conn, niche))
        if curated.name == demo.NICHE:
            report = demo.refresh(conn, curated, now=now)
        else:
            report = refresh_corpus(conn, _youtube(), curated, now=now)
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


@app.command()
def search(
    query: str = typer.Argument(help="Words to look for in Video titles, Chapters, tags and descriptions."),
    limit: int = typer.Option(10, help="How many Videos to show."),
    niche: str | None = DATABASE_NICHE_OPTION,
) -> None:
    """Keyword-search the Niche's Videos (BM25) and print them best first."""
    with db.connect() as conn:
        niche = _niche_on(conn, niche)
        startup_guard(conn, ARTEFACTS_DIR, datetime.now(UTC))
        results = search_corpus(conn, niche, query, limit=limit)
    if not results:
        typer.echo(f"no Videos match {query!r}")
    for rank, result in enumerate(results, start=1):
        typer.echo(f"{rank:>2}. {result.score:6.2f}  {result.title}  [{result.channel_title}]  {result.video_id}")


@app.command("demo")
def load_demo() -> None:
    """Load the synthetic demo Corpus (made-up Channels and Videos) into its own database.

    The database is DEMO_DATABASE_URL (default postgresql:///contention_demo),
    created if missing and replaced on every run. It never touches YouTube.
    """
    url = os.environ.get("DEMO_DATABASE_URL", demo.DATABASE_URL)
    demo.create_database(url)
    with psycopg.connect(url) as conn:
        try:
            report = demo.load(conn, load_niche(NICHES_DIR / demo.NICHE), now=datetime.now(UTC))
        except ValueError as error:
            _fail(str(error))
    typer.echo(demo.BANNER)
    typer.echo(f"loaded {report.channels} Channels and {report.videos} Videos into {url}")
    typer.echo(f"Run commands on it with DATABASE_URL={url}, e.g. DATABASE_URL={url} contention refresh")


def _niche_on(conn: psycopg.Connection, niche: str | None) -> str:
    """The Niche a command works on in this database, printing the demo banner on the demo database.

    The demo database holds only the demo Niche, and no other database may hold it.
    """
    if demo.is_demo(conn):
        if niche not in (None, demo.NICHE):
            _fail(f"This is the demo database: it only holds the {demo.NICHE} Niche.")
        typer.echo(demo.BANNER)
        return demo.NICHE
    if niche == demo.NICHE:
        _fail("The demo Niche is made up: load it into its own database with `contention demo`.")
    return niche or DEFAULT_NICHE


def _fail(message: str) -> NoReturn:
    typer.echo(message, err=True)
    raise typer.Exit(1)
