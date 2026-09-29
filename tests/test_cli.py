import psycopg
from typer.testing import CliRunner

from contention import cli, db
from contention.cli import app

from corpus_rows import insert_channel, insert_video
from fake_youtube import FakeYouTube, channel_details, video_details

runner = CliRunner()


def test_migrate_creates_the_schema_on_an_empty_database(database_url):
    result = runner.invoke(app, ["migrate"], env={"DATABASE_URL": database_url})

    assert result.exit_code == 0, result.output
    with psycopg.connect(database_url) as conn:
        tables = {name for (name,) in conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )}
        extensions = {name for (name,) in conn.execute("SELECT extname FROM pg_extension")}
    assert {"channels", "niche_channels", "videos", "video_snapshots", "channel_snapshots"} <= tables
    assert "vector" in extensions


def test_refresh_purges_channels_dropped_from_the_list_and_logs_the_run(database_url, tmp_path, monkeypatch):
    folder = tmp_path / "niches" / "tech-careers"
    folder.mkdir(parents=True)
    (folder / "niche.toml").write_text('description = "Tech careers."\nformats = ["other"]\n')
    (folder / "channels.toml").write_text('[[channels]]\nhandle = "@example"\ntier = "10k-100k"\nreason = "Good"\n')
    with psycopg.connect(database_url) as conn:
        db.migrate(conn, db.MIGRATIONS_DIR)
        conn.execute("INSERT INTO channels VALUES ('UC9', '@dropped', 'Dropped', '1k-10k', 'UU9', now())")
        conn.execute("INSERT INTO niche_channels VALUES ('tech-careers', 'UC9')")
    youtube = FakeYouTube({"@example": channel_details("UC1")}, [video_details("v1")])
    monkeypatch.setattr(cli, "NICHES_DIR", tmp_path / "niches")
    monkeypatch.setattr(cli, "ARTEFACTS_DIR", tmp_path / "artefacts")
    monkeypatch.setattr(cli, "_youtube", lambda: youtube)

    result = runner.invoke(app, ["refresh"], env={"DATABASE_URL": database_url})

    assert result.exit_code == 0, result.output
    assert "deleted 1 Channels" in result.output
    with psycopg.connect(database_url) as conn:
        assert conn.execute("SELECT channel_id FROM channels").fetchall() == [("UC1",)]
    [log] = (tmp_path / "artefacts").glob("run-*/refresh.log")
    assert "refreshed 1 Channels" in log.read_text()


def test_search_prints_ranked_videos(database_url, tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "ARTEFACTS_DIR", tmp_path)
    with psycopg.connect(database_url) as conn:
        db.migrate(conn, db.MIGRATIONS_DIR)
        insert_channel(conn, "UC1", "tech-careers")
        insert_video(conn, "v-title", title="Salary negotiation tips")
        insert_video(conn, "v-desc", title="My week", cleaned_description="A word on salary")
        for n in range(4):
            insert_video(conn, f"v-none-{n}", title="Unrelated")

    result = runner.invoke(app, ["search", "salary"], env={"DATABASE_URL": database_url})

    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert len(lines) == 2
    assert lines[0].startswith(" 1.") and "Salary negotiation tips" in lines[0] and "v-title" in lines[0]
    assert lines[1].startswith(" 2.") and "My week" in lines[1] and "Channel UC1" in lines[1]


def test_search_purges_stale_data_before_answering(database_url, tmp_path, monkeypatch):
    with psycopg.connect(database_url) as conn:
        db.migrate(conn, db.MIGRATIONS_DIR)
        insert_channel(conn, "UC1", "tech-careers")
        insert_video(conn, "fresh", title="Salary talk")
        insert_video(conn, "stale", title="Salary talk")
        conn.execute("UPDATE videos SET last_refreshed_at = now() - interval '29 days' WHERE video_id = 'stale'")
    monkeypatch.setattr(cli, "ARTEFACTS_DIR", tmp_path)

    result = runner.invoke(app, ["search", "salary"], env={"DATABASE_URL": database_url})

    assert result.exit_code == 0, result.output
    assert "fresh" in result.output and "stale" not in result.output
    with psycopg.connect(database_url) as conn:
        assert conn.execute("SELECT video_id FROM videos").fetchall() == [("fresh",)]


def test_search_says_when_nothing_matches(database_url, tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "ARTEFACTS_DIR", tmp_path)
    with psycopg.connect(database_url) as conn:
        db.migrate(conn, db.MIGRATIONS_DIR)

    result = runner.invoke(app, ["search", "salary"], env={"DATABASE_URL": database_url})

    assert result.exit_code == 0, result.output
    assert "no Videos match" in result.output
