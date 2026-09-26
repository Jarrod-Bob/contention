"""The Postgres store: connections and schema migrations."""

import os
from pathlib import Path

import psycopg

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def connect() -> psycopg.Connection:
    """Connect to the database named by `DATABASE_URL` (default: local `contention`)."""
    return psycopg.connect(os.environ.get("DATABASE_URL", "postgresql:///contention"))


def migrate(conn: psycopg.Connection, migrations_dir: Path) -> list[str]:
    """Apply pending `.sql` migrations in number order and return their file names.

    Applied migrations are recorded in `schema_migrations`, so running this again
    only applies files added since. Each file runs in its own transaction: a
    failing file is rolled back completely and raises, and files before it stay
    applied.
    """
    with conn.transaction():
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name text PRIMARY KEY)")
        already_applied = {name for (name,) in conn.execute("SELECT name FROM schema_migrations")}
    applied = []
    for path in sorted(Path(migrations_dir).glob("*.sql")):
        if path.name in already_applied:
            continue
        with conn.transaction():
            conn.execute(path.read_text())
            conn.execute("INSERT INTO schema_migrations (name) VALUES (%s)", (path.name,))
        applied.append(path.name)
    return applied
