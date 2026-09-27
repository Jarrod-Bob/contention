-- Text derived from each Video's description at collection time (ADR 0004).
-- Both are deleted with their Video (ADR 0003).

ALTER TABLE videos ADD COLUMN cleaned_description text NOT NULL DEFAULT '';

CREATE TABLE chapters (
    video_id      text NOT NULL REFERENCES videos ON DELETE CASCADE,
    position      integer NOT NULL,
    start_seconds integer NOT NULL,
    title         text NOT NULL,
    PRIMARY KEY (video_id, position)
);
