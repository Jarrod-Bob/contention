-- The first schema: Channels, their Niche membership, Videos, and Snapshots.
-- Everything is keyed by YouTube id. Rows derived from a Video or Channel are
-- deleted with it (ON DELETE CASCADE), per ADR 0003.

CREATE EXTENSION IF NOT EXISTS vector;

-- A band of Channel subscriber counts, recorded when the Channel is curated.
CREATE TYPE tier AS ENUM ('1k-10k', '10k-100k', '100k-500k', '500k-1M', '1M+');

CREATE TABLE channels (
    channel_id          text PRIMARY KEY,
    handle              text NOT NULL UNIQUE,  -- as typed in the niche folder's Channel list
    title               text NOT NULL,
    tier                tier NOT NULL,
    uploads_playlist_id text NOT NULL,
    last_refreshed_at   timestamptz NOT NULL
);

-- Niche membership is a label on the Channel (ADR 0001): one Channel can be in
-- several Niches but is stored once.
CREATE TABLE niche_channels (
    niche      text NOT NULL,
    channel_id text NOT NULL REFERENCES channels ON DELETE CASCADE,
    PRIMARY KEY (niche, channel_id)
);

CREATE TABLE videos (
    video_id          text PRIMARY KEY,
    channel_id        text NOT NULL REFERENCES channels ON DELETE CASCADE,
    published_at      timestamptz NOT NULL,
    title             text NOT NULL,
    description       text NOT NULL,
    tags              text[] NOT NULL DEFAULT '{}',
    topic_categories  text[] NOT NULL DEFAULT '{}',
    duration_seconds  integer NOT NULL,
    is_held_out       boolean NOT NULL DEFAULT false,
    last_refreshed_at timestamptz NOT NULL
);

-- Snapshots: public metrics as read at one moment. Kept for at most 28 days.
CREATE TABLE video_snapshots (
    video_id      text NOT NULL REFERENCES videos ON DELETE CASCADE,
    taken_at      timestamptz NOT NULL,
    view_count    bigint NOT NULL,
    like_count    bigint,
    comment_count bigint,
    PRIMARY KEY (video_id, taken_at)
);

CREATE TABLE channel_snapshots (
    channel_id       text NOT NULL REFERENCES channels ON DELETE CASCADE,
    taken_at         timestamptz NOT NULL,
    view_count       bigint NOT NULL,
    subscriber_count bigint,
    video_count      integer NOT NULL,
    PRIMARY KEY (channel_id, taken_at)
);
