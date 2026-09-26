import psycopg
from typer.testing import CliRunner

from contention.cli import app

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
