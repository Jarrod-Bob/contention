"""Deleting what the Corpus may no longer hold (refresh step 2, and the startup guard).

Everything derived from a Video or Channel references it with ON DELETE CASCADE,
so deleting the row deletes the derived data with it (ADR 0003, ADR 0008).
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import psycopg

from contention.artefacts import RETENTION, purge_runs
from contention.collect import WINDOW
from contention.niche import Niche


@dataclass(frozen=True)
class PurgeReport:
    """How many Channels, Videos and Snapshots a purge deleted."""

    channels: int = 0
    videos: int = 0
    snapshots: int = 0

    def __add__(self, other: "PurgeReport") -> "PurgeReport":
        return PurgeReport(self.channels + other.channels, self.videos + other.videos,
                           self.snapshots + other.snapshots)


def purge(conn: psycopg.Connection, niche: Niche, now: datetime) -> PurgeReport:
    """Apply every deletion rule after a refresh of `niche`.

    Deletes Channels no longer on the Niche's list (unless another Niche lists
    them), Videos missing from their Channel's latest refresh (deleted, private,
    became Shorts or stopped qualifying), then everything `purge_stale` deletes.
    """
    with conn.transaction():
        conn.execute(
            """
            DELETE FROM niche_channels nc USING channels c
            WHERE nc.channel_id = c.channel_id AND nc.niche = %s AND c.handle <> ALL(%s)
            """,
            (niche.name, [c.handle for c in niche.channels]),
        )
        unlisted = "NOT EXISTS (SELECT 1 FROM niche_channels nc WHERE nc.channel_id = {})"
        removed = conn.execute(f"DELETE FROM videos v WHERE {unlisted.format('v.channel_id')}").rowcount
        channels = conn.execute(f"DELETE FROM channels c WHERE {unlisted.format('c.channel_id')}").rowcount
        vanished = conn.execute(
            """
            DELETE FROM videos v USING channels c
            WHERE v.channel_id = c.channel_id AND v.last_refreshed_at < c.last_refreshed_at
            """
        ).rowcount
    return PurgeReport(channels=channels, videos=removed + vanished) + purge_stale(conn, now)


def purge_stale(conn: psycopg.Connection, now: datetime) -> PurgeReport:
    """Delete whatever has aged out, whether or not a refresh just ran.

    That is Videos past the 3-year window, Videos and Channels not refreshed
    within the retention period, and Snapshots older than it.
    """
    stale = now - RETENTION
    with conn.transaction():
        videos = conn.execute(
            "DELETE FROM videos WHERE published_at < %s OR last_refreshed_at < %s", (now - WINDOW, stale)
        ).rowcount
        channels = conn.execute("DELETE FROM channels WHERE last_refreshed_at < %s", (stale,)).rowcount
        snapshots = sum(
            conn.execute(f"DELETE FROM {table} WHERE taken_at < %s", (stale,)).rowcount
            for table in ("video_snapshots", "channel_snapshots")
        )
    return PurgeReport(channels=channels, videos=videos, snapshots=snapshots)


def startup_guard(conn: psycopg.Connection, artefacts_dir: Path, now: datetime) -> PurgeReport:
    """Run before serving answers: purge stale data and artefact runs past retention."""
    report = purge_stale(conn, now)
    purge_runs(artefacts_dir, now)
    return report
