from datetime import UTC, datetime, timedelta

import psycopg
import pytest

from contention import db
from contention.collect import refresh
from contention.niche import CuratedChannel, Niche
from contention.purge import purge, startup_guard

from fake_youtube import FakeYouTube, channel_details, video_details

NOW = datetime(2026, 9, 27, tzinfo=UTC)
CHAPTERED = "My first year.\n0:00 Intro\n1:15 The mistake"
EXAMPLE = CuratedChannel("@example", "10k-100k", "Solid career advice")
OTHER = CuratedChannel("@other", "1k-10k", "Small but sharp")


def niche(*channels, name="tech-careers"):
    return Niche(name=name, description="A Niche.", formats=("other",), channels=channels)


def video_ids(conn):
    return [video_id for (video_id,) in conn.execute("SELECT video_id FROM videos ORDER BY video_id")]


def derived_rows(conn, video_id):
    """How many rows derived from the Video remain, per table."""
    return {
        table: conn.execute(f"SELECT count(*) FROM {table} WHERE video_id = %s", (video_id,)).fetchone()[0]
        for table in ("video_snapshots", "chapters")
    }


@pytest.fixture
def corpus(conn):
    db.migrate(conn, db.MIGRATIONS_DIR)
    return conn


@pytest.mark.parametrize("second_look", [
    pytest.param([], id="deleted or private"),
    pytest.param([video_details("gone", duration_seconds=60)], id="became a Short"),
])
def test_deletes_videos_that_disappeared_from_their_channel(corpus, tmp_path, second_look):
    curated = niche(EXAMPLE)
    refresh(corpus, FakeYouTube({"@example": channel_details("UC1")},
                                [video_details("kept"), video_details("gone", description=CHAPTERED)]), curated, NOW)
    later = NOW + timedelta(days=7)
    refresh(corpus, FakeYouTube({"@example": channel_details("UC1")}, [video_details("kept"), *second_look]),
            curated, later)

    report = purge(corpus, curated, later)

    assert video_ids(corpus) == ["kept"]
    assert derived_rows(corpus, "gone") == {"video_snapshots": 0, "chapters": 0}
    assert report.videos == 1


def test_deletes_videos_past_the_three_year_window(corpus):
    curated = niche(EXAMPLE)
    refresh(corpus, FakeYouTube({"@example": channel_details("UC1")}, [
        video_details("recent"),
        video_details("ageing", published_at=datetime(2023, 10, 1, tzinfo=UTC), description=CHAPTERED),
    ]), curated, NOW)

    purge(corpus, curated, NOW + timedelta(days=14))

    assert video_ids(corpus) == ["recent"]
    assert derived_rows(corpus, "ageing") == {"video_snapshots": 0, "chapters": 0}


def test_deletes_channels_removed_from_the_list_unless_in_another_niche(corpus):
    youtube = FakeYouTube(
        {"@example": channel_details("UC1"), "@other": channel_details("UC2")},
        [video_details("v1", channel_id="UC1", description=CHAPTERED), video_details("v2", channel_id="UC2")],
    )
    refresh(corpus, youtube, niche(EXAMPLE, OTHER), NOW)
    refresh(corpus, youtube, niche(OTHER, name="interviews"), NOW)

    report = purge(corpus, niche(), NOW)

    assert corpus.execute("SELECT channel_id FROM channels").fetchall() == [("UC2",)]
    assert corpus.execute("SELECT niche, channel_id FROM niche_channels").fetchall() == [("interviews", "UC2")]
    assert video_ids(corpus) == ["v2"]
    assert derived_rows(corpus, "v1") == {"video_snapshots": 0, "chapters": 0}
    assert corpus.execute("SELECT count(*) FROM channel_snapshots WHERE channel_id = 'UC1'").fetchone() == (0,)
    assert (report.channels, report.videos) == (1, 1)


def test_deletes_anything_not_refreshed_within_28_days(corpus):
    curated = niche(EXAMPLE)
    refresh(corpus, FakeYouTube({"@example": channel_details("UC1")},
                                [video_details("v1", description=CHAPTERED)]), curated, NOW)

    purge(corpus, curated, NOW + timedelta(days=28))
    assert video_ids(corpus) == ["v1"]

    purge(corpus, curated, NOW + timedelta(days=28, seconds=1))
    assert video_ids(corpus) == []
    assert corpus.execute("SELECT count(*) FROM channels").fetchone() == (0,)
    assert derived_rows(corpus, "v1") == {"video_snapshots": 0, "chapters": 0}


def test_purges_snapshots_older_than_28_days_but_keeps_their_video(corpus):
    curated = niche(EXAMPLE)
    youtube = FakeYouTube({"@example": channel_details("UC1")}, [video_details("v1")])
    for week in range(5):
        refresh(corpus, youtube, curated, NOW + timedelta(weeks=week))
    now = NOW + timedelta(weeks=4, days=1)

    report = purge(corpus, curated, now)

    assert video_ids(corpus) == ["v1"]
    for table in ("video_snapshots", "channel_snapshots"):
        assert corpus.execute(f"SELECT min(taken_at), count(*) FROM {table}").fetchone() == (
            NOW + timedelta(weeks=1), 4,
        )
    assert report.snapshots == 2


def test_purge_is_committed(corpus, database_url):
    curated = niche(EXAMPLE)
    refresh(corpus, FakeYouTube({"@example": channel_details("UC1")}, [video_details("v1")]), curated, NOW)

    purge(corpus, niche(), NOW)

    with psycopg.connect(database_url) as other:
        assert other.execute("SELECT count(*) FROM videos").fetchone() == (0,)


def test_startup_guard_purges_stale_data_and_old_artefact_runs(corpus, tmp_path):
    refresh(corpus, FakeYouTube({"@example": channel_details("UC1")}, [
        video_details("v1", description=CHAPTERED),
    ]), niche(EXAMPLE), NOW)
    old_run = tmp_path / "run-20260801T030000Z"
    old_run.mkdir()
    (old_run / "model.txt").write_text("trained")

    startup_guard(corpus, tmp_path, NOW + timedelta(days=29))

    assert video_ids(corpus) == []
    assert corpus.execute("SELECT count(*) FROM channels").fetchone() == (0,)
    assert not old_run.exists()


def test_startup_guard_keeps_fresh_data(corpus, tmp_path):
    refresh(corpus, FakeYouTube({"@example": channel_details("UC1")}, [video_details("v1")]), niche(EXAMPLE), NOW)

    startup_guard(corpus, tmp_path, NOW + timedelta(days=3))

    assert video_ids(corpus) == ["v1"]
