from datetime import UTC, datetime

import psycopg

from contention import db
from contention.collect import refresh
from contention.niche import CuratedChannel, Niche

from fake_youtube import FakeYouTube, channel_details, video_details

NOW = datetime(2026, 9, 27, tzinfo=UTC)
CHAPTERED = "My first year.\n0:00 Intro\n1:15 The mistake\n4:30 Recovery\nhttps://example.com\n#career"


def niche(*channels):
    return Niche(name="tech-careers", description="Tech careers.", formats=("other",), channels=channels)


def test_refresh_collects_long_form_english_videos_of_curated_channels(conn):
    db.migrate(conn, db.MIGRATIONS_DIR)
    youtube = FakeYouTube(
        {"@example": channel_details("UC1")},
        [
            video_details("long", description=CHAPTERED),
            video_details("no-language", audio_language=None),
            video_details("short", duration_seconds=60),
            video_details("spanish", audio_language="es"),
            video_details("old", published_at=datetime(2023, 1, 1, tzinfo=UTC)),
        ],
    )

    report = refresh(conn, youtube, niche(CuratedChannel("@example", "10k-100k", "Solid career advice")), now=NOW)

    assert report.videos == 2
    assert conn.execute("SELECT channel_id, handle, tier FROM channels").fetchall() == [("UC1", "@example", "10k-100k")]
    assert conn.execute("SELECT niche, channel_id FROM niche_channels").fetchall() == [("tech-careers", "UC1")]
    assert conn.execute("SELECT subscriber_count FROM channel_snapshots").fetchall() == [(12_300,)]
    assert conn.execute("SELECT video_id FROM videos ORDER BY video_id").fetchall() == [("long",), ("no-language",)]
    assert conn.execute("SELECT count(*) FROM video_snapshots").fetchone() == (2,)
    assert conn.execute("SELECT cleaned_description FROM videos WHERE video_id = 'long'").fetchone() == (
        "My first year.\n0:00 Intro\n1:15 The mistake\n4:30 Recovery",
    )
    assert conn.execute(
        "SELECT start_seconds, title FROM chapters WHERE video_id = 'long' ORDER BY position"
    ).fetchall() == [(0, "Intro"), (75, "The mistake"), (270, "Recovery")]


def test_a_later_refresh_updates_in_place_and_adds_snapshots(conn):
    db.migrate(conn, db.MIGRATIONS_DIR)
    curated = niche(CuratedChannel("@example", "10k-100k", "Solid career advice"))
    refresh(conn, FakeYouTube({"@example": channel_details("UC1")}, [video_details("v1", view_count=100)]),
            curated, now=NOW)

    youtube = FakeYouTube({"@example": channel_details("UC1")}, [video_details("v1", title="Renamed", view_count=900)])
    report = refresh(conn, youtube, curated, now=datetime(2026, 10, 4, tzinfo=UTC))

    assert youtube.quota_used == 3  # the handle is already known, so it isn't looked up again
    assert report.unknown_handles == ()
    assert conn.execute("SELECT title FROM videos").fetchall() == [("Renamed",)]
    assert conn.execute("SELECT view_count FROM video_snapshots ORDER BY taken_at").fetchall() == [(100,), (900,)]
    assert conn.execute("SELECT count(*) FROM channel_snapshots").fetchone() == (2,)


def test_reports_handles_that_youtube_does_not_know(conn):
    db.migrate(conn, db.MIGRATIONS_DIR)

    report = refresh(conn, FakeYouTube({}, []), niche(CuratedChannel("@typo", "1k-10k", "Misspelt")), now=NOW)

    assert report.unknown_handles == ("@typo",)
    assert report.channels == 0


def test_refreshed_channels_are_committed(conn, database_url):
    db.migrate(conn, db.MIGRATIONS_DIR)
    youtube = FakeYouTube({"@example": channel_details("UC1")}, [video_details("v1")])

    refresh(conn, youtube, niche(CuratedChannel("@example", "10k-100k", "Solid career advice")), now=NOW)

    with psycopg.connect(database_url) as other:
        assert other.execute("SELECT count(*) FROM videos").fetchone() == (1,)
