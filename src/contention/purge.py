"""Deleting what the Corpus may no longer hold (refresh step 2, and the startup guard).

Everything derived from a Video or Channel references it with ON DELETE CASCADE,
so deleting the row deletes the derived data with it (ADR 0003, ADR 0008).
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import psycopg

from contention.artefacts import purge_runs
from contention.collect import RETENTION, WINDOW
from contention.niche import Niche


@dataclass(frozen=True)
class PurgeReport:
    """How many Channels, Videos, Snapshots and artefact runs a purge deleted."""

    channels: int = 0
    videos: int = 0
    snapshots: int = 0
    runs: int = 0


def purge(conn: psycopg.Connection, niche: Niche, artefacts_dir: Path, now: datetime) -> PurgeReport:
    """Apply every deletion rule after a refresh of `niche`.

    Deletes Channels no longer on the Niche's list (unless another Niche lists
    them) with their Videos, Videos missing from their Channel's latest refresh
    (deleted, private, became Shorts or stopped qualifying), then everything
    `startup_guard` deletes. An empty Channel list is taken as a mistake, not as
    "remove every Channel": those Channels age out after the retention period instead.
    """
    unlisted_videos = channels = 0
    with conn.transaction():
        if niche.channels:
            conn.execute(
                """
                DELETE FROM niche_channels nc USING channels c
                WHERE nc.channel_id = c.channel_id AND nc.niche = %s AND c.handle <> ALL(%s)
                """,
                (niche.name, [c.handle for c in niche.channels]),
            )
            unlisted_videos = conn.execute(
                """
                DELETE FROM videos v
                WHERE NOT EXISTS (SELECT 1 FROM niche_channels nc WHERE nc.channel_id = v.channel_id)
                """
            ).rowcount
            channels = conn.execute(
                """
                DELETE FROM channels c
                WHERE NOT EXISTS (SELECT 1 FROM niche_channels nc WHERE nc.channel_id = c.channel_id)
                """
            ).rowcount
        vanished_videos = conn.execute(
            """
            DELETE FROM videos v USING channels c
            WHERE v.channel_id = c.channel_id AND v.last_refreshed_at < c.last_refreshed_at
            """
        ).rowcount
    stale = startup_guard(conn, artefacts_dir, now)
    return PurgeReport(stale.channels + channels, stale.videos + unlisted_videos + vanished_videos,
                       stale.snapshots, stale.runs)


def startup_guard(conn: psycopg.Connection, artefacts_dir: Path, now: datetime) -> PurgeReport:
    """Delete whatever has aged out; run before serving answers, and by every refresh.

    That is Videos past the 3-year window, Videos and Channels not refreshed within
    the retention period, Snapshots older than it, and artefact runs older than it.
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
    runs = len(purge_runs(artefacts_dir, now))
    return PurgeReport(channels, videos, snapshots, runs)
