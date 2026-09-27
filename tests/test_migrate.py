import psycopg
import pytest


from contention.db import migrate


def write(folder, name, sql):
    (folder / name).write_text(sql)


def test_applies_pending_migrations_in_number_order(conn, tmp_path):
    write(tmp_path, "0002_add_row.sql", "INSERT INTO t VALUES (2);")
    write(tmp_path, "0001_create.sql", "CREATE TABLE t (n int); INSERT INTO t VALUES (1);")

    applied = migrate(conn, tmp_path)

    assert applied == ["0001_create.sql", "0002_add_row.sql"]
    assert conn.execute("SELECT n FROM t ORDER BY n").fetchall() == [(1,), (2,)]


def test_skips_migrations_already_applied(conn, tmp_path):
    write(tmp_path, "0001_create.sql", "CREATE TABLE t (n int);")
    migrate(conn, tmp_path)
    write(tmp_path, "0002_add_row.sql", "INSERT INTO t VALUES (2);")

    applied = migrate(conn, tmp_path)

    assert applied == ["0002_add_row.sql"]
    assert migrate(conn, tmp_path) == []


def test_failing_migration_is_rolled_back_and_earlier_ones_are_kept(conn, tmp_path):
    write(tmp_path, "0001_create.sql", "CREATE TABLE t (n int);")
    write(tmp_path, "0002_broken.sql", "INSERT INTO t VALUES (2); SELECT no_such_column FROM t;")

    with pytest.raises(psycopg.Error):
        migrate(conn, tmp_path)

    write(tmp_path, "0002_broken.sql", "INSERT INTO t VALUES (2);")
    assert migrate(conn, tmp_path) == ["0002_broken.sql"]
    assert conn.execute("SELECT n FROM t").fetchall() == [(2,)]
