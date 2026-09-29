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

4. Get a YouTube Data API key. The wizard walks you through Google Cloud Console, saves the key to `.env` (git-ignored) and checks that it works:

   ```sh
   scripts/setup-youtube-api-key.sh
   ```

5. Run the tests:

   ```sh
   uv run pytest
   ```

The app connects to `DATABASE_URL` (default `postgresql:///contention`). Tests use `TEST_DATABASE_URL` (default `postgresql:///contention_test`) and wipe it on every run.

## LLM providers

YouTube data (Corpus titles, descriptions and anything derived from them) only goes to providers that don't train on it and don't keep it past 30 days ([spec §2](docs/spec/mvp.md), [#47](https://github.com/Jarrod-Bob/contention/issues/47)). Every LLM client is built by `contention.llm`, which enforces the parts code can: OpenRouter requests always send `provider: {zdr: true, data_collection: "deny"}`, Ollama must be local with cloud models off, LangSmith tracing is off, real Drafts only go to Claude or the local Ollama model, and each Message Batch is deleted once its results are stored. Put `ANTHROPIC_API_KEY` and `OPENROUTER_API_KEY` in `.env`.

The rest are one-time account settings that code can't check. Set them before sending anything:

- **OpenRouter** ([privacy settings](https://openrouter.ai/settings/privacy)):
  - prompt and output logging: **off** (OpenRouter's terms let it use, distribute and sell logged inputs);
  - the product-improvement opt-in (discount for sharing your data): **off**;
  - model training: **opted out**, for free models **and** paid models.
- **Ollama:** run the server with cloud models off, e.g. `OLLAMA_NO_CLOUD=1 ollama serve`, or for the macOS app `launchctl setenv OLLAMA_NO_CLOUD 1` and restart it. contention also refuses `*-cloud` models and non-local `OLLAMA_HOST`s.
- **Anthropic:** nothing to change; the API doesn't train on inputs and deletes them within 30 days. Don't use its Files API for YouTube data.

Niche-specific data lives in [`niches/`](niches/), one folder per Niche, holding only what you wrote yourself (see [ADR 0001](docs/adr/0001-niche-is-a-curated-channel-list.md)).

## Weekly refresh

`uv run contention refresh` re-reads every curated Channel, then deletes what the Corpus may no longer hold: Videos that disappeared or passed the 3-year window, Channels dropped from the Niche's list (unless another Niche lists them), anything not refreshed within 28 days, Snapshots older than 28 days, and `artefacts/` runs older than 28 days. Everything derived from a deleted Video goes with it.

To run it weekly (Sundays at 03:00) with `launchd`:

```sh
scripts/install-refresh-job.sh              # install, or reinstall after moving the checkout
launchctl kickstart gui/$(id -u)/local.contention.refresh   # run it now
scripts/install-refresh-job.sh --uninstall  # remove it
```

The job's output goes to `artefacts/launchd.log`. Each refresh also writes a log to its own run directory, `artefacts/run-<UTC timestamp>/`, where trained models, batch files and eval outputs will go too. `artefacts/` is git-ignored; keep it, and the Postgres data directory, out of any machine backup.
