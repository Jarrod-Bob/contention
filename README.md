# contention

A content intelligence tool, built as a hands-on way to learn LLMs, hybrid RAG, and classic ML prediction systems.

## Features

1. **Content Strategist**: ask an LLM what content strategy suits a given demographic. Its answers draw on a hybrid-RAG index over existing online content and deterministic analytics.
2. **Content Optimiser**: submit your own content and get suggestions for improving it. These are based on a prediction engine's performance estimate and a comparison with similar existing content.

## Status

Being built from the [MVP spec](docs/spec/mvp.md). Decisions are recorded in [`docs/adr/`](docs/adr/) and the vocabulary in [`CONTEXT.md`](CONTEXT.md).

## Development setup

Requires macOS with [Homebrew](https://brew.sh) and [uv](https://docs.astral.sh/uv/).

1. Install Postgres and pgvector, and start Postgres as a background service:

   ```sh
   brew install postgresql@18 pgvector
   brew services start postgresql@18
   ```

2. Create the development and test databases:

   ```sh
   /opt/homebrew/opt/postgresql@18/bin/createdb contention
   /opt/homebrew/opt/postgresql@18/bin/createdb contention_test
   ```

3. Install dependencies (uv provides Python 3.14) and apply the schema:

   ```sh
   uv sync
   uv run contention migrate
   ```

4. Run the tests:

   ```sh
   uv run pytest
   ```

The app connects to `DATABASE_URL` (default `postgresql:///contention`). Tests use `TEST_DATABASE_URL` (default `postgresql:///contention_test`) and wipe it on every run.

Niche-specific data lives in [`niches/`](niches/), one folder per Niche, holding only what you wrote yourself (see [ADR 0001](docs/adr/0001-niche-is-a-curated-channel-list.md)).
