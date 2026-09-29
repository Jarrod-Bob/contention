-- Marks a database that holds the synthetic demo Corpus loaded by `contention
-- demo` instead of data from YouTube: the app shows a "demo data" banner when
-- this table has a row, and `refresh` reads the synthetic Corpus, not YouTube.
-- At most one row, recording when the demo was loaded; that moment anchors the
-- synthetic Videos' publish dates, so later refreshes stay consistent with it.

CREATE TABLE demo_corpus (
    only_row  boolean PRIMARY KEY DEFAULT true CHECK (only_row),
    loaded_at timestamptz NOT NULL
);
