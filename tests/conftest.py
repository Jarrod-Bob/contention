import os

import psycopg
import pytest

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "postgresql:///contention_test")


@pytest.fixture
def database_url():
    """A test database with an empty public schema."""
    with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
        conn.execute("DROP EXTENSION IF EXISTS vector")
    return TEST_DATABASE_URL


@pytest.fixture
def conn(database_url):
    with psycopg.connect(database_url) as conn:
        yield conn
