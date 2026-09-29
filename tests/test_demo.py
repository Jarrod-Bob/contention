from datetime import UTC, datetime, timedelta

import psycopg
import pytest
from typer.testing import CliRunner

from contention import cli, db, demo
from contention.cli import NICHES_DIR, app
from contention.niche import TIERS, load_niche

runner = CliRunner()
NOW = datetime(2026, 9, 27, tzinfo=UTC)
TIER_BOUNDS = {"1k-10k": (1_000, 10_000), "10k-100k": (10_000, 100_000), "100k-500k": (100_000, 500_000),
               "500k-1M": (500_000, 1_000_000), "1M+": (1_000_000, 10**12)}


@pytest.fixture(autouse=True)
def artefacts_dir(tmp_path, monkeypatch):
    """Keep refresh runs out of the repo's artefacts/ directory."""
    monkeypatch.setattr(cli, "ARTEFACTS_DIR", tmp_path / "artefacts")
    return tmp_path / "artefacts"


def demo_niche():
    return load_niche(NICHES_DIR / demo.NICHE)


def invoke(*args, **env):
    return runner.invoke(app, list(args), env={"YOUTUBE_API_KEY": "", **env})


def test_the_demo_niche_lists_made_up_channels_in_every_tier():
    niche = demo_niche()
    youtube = demo.synthetic_youtube(loaded_at=NOW, now=NOW)

    assert {c.tier for c in niche.channels} == set(TIERS)
    for curated in niche.channels:
        assert curated.handle.startswith("@demo.")
        channel = youtube.channel_by_handle(curated.handle)
        assert channel is not None, curated.handle
        assert channel.channel_id.startswith("UCdemo")
        low, high = TIER_BOUNDS[curated.tier]
        assert low <= channel.subscriber_count < high, curated.handle


def test_every_synthetic_video_is_made_up_and_most_have_chapters():
    videos = demo.synthetic_youtube(loaded_at=NOW, now=NOW).all_videos

    assert len(videos) >= 30
    assert all(v.video_id.startswith("demo") for v in videos)
    assert all("youtube.com" not in v.description and "youtu.be" not in v.description for v in videos)
    assert sum("0:00" in v.description for v in videos) > len(videos) / 2


def test_views_grow_and_videos_appear_only_once_published():
    earlier = demo.synthetic_youtube(loaded_at=NOW, now=NOW - timedelta(days=14))
    later = demo.synthetic_youtube(loaded_at=NOW, now=NOW)

    earlier_views = {v.video_id: v.view_count for v in earlier.all_videos}
    assert all(v.published_at <= NOW - timedelta(days=14) for v in earlier.all_videos)
    assert len(later.all_videos) > len(earlier.all_videos)
    for video in later.all_videos:
        assert video.view_count >= earlier_views.get(video.video_id, 0)


def test_demo_loads_the_synthetic_corpus_into_its_own_database(database_url):
    result = invoke("demo", DEMO_DATABASE_URL=database_url, DATABASE_URL="postgresql:///not_the_demo")

    assert result.exit_code == 0, result.output
    with psycopg.connect(database_url) as conn:
        assert demo.is_demo(conn)
        channels = conn.execute("SELECT count(*) FROM channels").fetchone()[0]
        videos = conn.execute("SELECT count(*) FROM videos").fetchone()[0]
        assert channels == len(demo_niche().channels)
        assert videos >= 30
        assert conn.execute("SELECT DISTINCT niche FROM niche_channels").fetchall() == [(demo.NICHE,)]
        assert conn.execute("SELECT count(DISTINCT video_id) FROM chapters").fetchone()[0] > videos / 2
        assert conn.execute("SELECT count(DISTINCT taken_at) FROM video_snapshots").fetchone() == (3,)
        oldest = conn.execute("SELECT min(taken_at), max(taken_at) FROM video_snapshots").fetchone()
        assert oldest[1] - oldest[0] < timedelta(days=28)
    assert f"{channels} Channels and {videos} Videos" in result.output


def test_demo_reloads_over_an_earlier_demo(database_url):
    invoke("demo", DEMO_DATABASE_URL=database_url)

    result = invoke("demo", DEMO_DATABASE_URL=database_url)

    assert result.exit_code == 0, result.output
    with psycopg.connect(database_url) as conn:
        assert conn.execute("SELECT count(DISTINCT taken_at) FROM video_snapshots").fetchone() == (3,)


def test_demo_refuses_to_overwrite_a_database_that_is_not_the_demo(conn, database_url):
    db.migrate(conn, db.MIGRATIONS_DIR)
    conn.execute("INSERT INTO channels VALUES ('UCreal', '@real', 'Real', '1M+', 'UUreal', now())")
    conn.commit()

    result = invoke("demo", DEMO_DATABASE_URL=database_url)

    assert result.exit_code == 1
    assert "isn't a demo database" in result.output
    assert conn.execute("SELECT channel_id FROM channels").fetchall() == [("UCreal",)]


def test_demo_creates_its_database_if_it_is_missing(database_url):
    new_url = database_url + "_demo_created"
    new_name = new_url.rsplit("/", 1)[1]
    with psycopg.connect(database_url, autocommit=True) as admin:
        admin.execute(f'DROP DATABASE IF EXISTS "{new_name}"')
    try:
        result = invoke("demo", DEMO_DATABASE_URL=new_url)

        assert result.exit_code == 0, result.output
        with psycopg.connect(new_url) as conn:
            assert demo.is_demo(conn)
    finally:
        with psycopg.connect(database_url, autocommit=True) as admin:
            admin.execute(f'DROP DATABASE IF EXISTS "{new_name}"')


def test_refresh_runs_on_the_demo_database_without_an_api_key(database_url):
    invoke("demo", DEMO_DATABASE_URL=database_url)

    result = invoke("refresh", DATABASE_URL=database_url)

    assert result.exit_code == 0, result.output
    assert demo.BANNER in result.output
    assert "deleted 0 Channels, 0 Videos, 0 Snapshots" in result.output  # the purge runs, and a fresh demo is clean
    with psycopg.connect(database_url) as conn:
        assert conn.execute("SELECT count(DISTINCT taken_at) FROM video_snapshots").fetchone() == (4,)


def test_search_runs_on_the_demo_database(database_url):
    invoke("demo", DEMO_DATABASE_URL=database_url)

    result = invoke("search", "code review", DATABASE_URL=database_url)

    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert lines[0] == demo.BANNER
    assert lines[1].startswith(" 1.") and "My first code review got 47 comments" in lines[1]


def test_refresh_on_the_demo_database_only_takes_the_demo_niche(database_url):
    invoke("demo", DEMO_DATABASE_URL=database_url)

    result = invoke("refresh", "--niche", "tech-careers", DATABASE_URL=database_url)

    assert result.exit_code == 1
    assert "demo database" in result.output


def test_refresh_keeps_the_demo_niche_out_of_a_regular_database(conn, database_url):
    db.migrate(conn, db.MIGRATIONS_DIR)
    conn.commit()

    result = invoke("refresh", "--niche", demo.NICHE, DATABASE_URL=database_url)

    assert result.exit_code == 1
    assert "contention demo" in result.output
    assert conn.execute("SELECT count(*) FROM channels").fetchone() == (0,)


def test_a_regular_database_is_not_the_demo(conn):
    assert not demo.is_demo(conn)  # not even migrated
    db.migrate(conn, db.MIGRATIONS_DIR)
    assert not demo.is_demo(conn)



def test_channels_add_refuses_the_demo_niche():
    before = (NICHES_DIR / demo.NICHE / "channels.toml").read_text()

    result = runner.invoke(app, ["channels", "add", "@real", "--tier", "1k-10k", "--reason", "Real", "--niche", "demo"],
                           env={"YOUTUBE_API_KEY": ""})

    assert result.exit_code == 1
    assert "made-up Channels" in result.output
    assert (NICHES_DIR / demo.NICHE / "channels.toml").read_text() == before
