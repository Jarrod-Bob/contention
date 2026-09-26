# Postgres as the store, retrieval hand-built in Python

Postgres (installed through Homebrew, with pgvector) holds Channels, Videos, snapshots, Niche membership and embeddings, accessed with plain SQL through `psycopg` and numbered `.sql` migration files. Retrieval does not run in Postgres: embeddings are loaded from their pgvector column into numpy and searched by exact brute-force cosine similarity, and keyword search is a hand-written BM25 over weighted fields, cross-checked against `rank_bm25`. We chose this because the project is learning-first (the user wants to learn Postgres, and to build BM25 and vector search rather than call them), Postgres's `ts_rank` is not BM25, and at ~30k Videos the whole embedding matrix fits in memory and exact search takes milliseconds, so retrieval evals measure ranking choices rather than index approximation.

## Considered Options

- **SQLite.** Simpler for a single-user tool, but the user wants to learn Postgres.
- **Vector and keyword search in SQL (pgvector `<=>`, Postgres full-text).** Rejected for the MVP: hides the parts being learned, and Postgres full-text ranking is not BM25. Comparing numpy search with pgvector search is kept as an optional correctness check (both are exact without an index, so results should match).
- **An approximate nearest-neighbour index (FAISS, HNSW).** Rejected: solves a scale problem we don't have and would blur retrieval evals.
- **The SQLAlchemy ORM.** Rejected for now so the SQL stays visible; may be revisited later.

## Consequences

- Vectors are loaded at startup, and the in-memory copy must be reloaded after each 30-day refresh.
- Fusion (RRF by default, weighted sum compared in evals) and an optional cross-encoder reranker run in Python, exposed as a custom LangChain retriever (ADR 0002).
- A Docker setup is future work; the Homebrew install is the MVP.
