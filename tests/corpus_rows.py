"""Inserting Channels and Videos straight into the store, for tests that read the Corpus."""

from datetime import UTC, datetime

NOW = datetime(2026, 9, 27, tzinfo=UTC)


def insert_channel(conn, channel_id, niche):
    conn.execute(
        "INSERT INTO channels (channel_id, handle, title, tier, uploads_playlist_id, last_refreshed_at)"
        " VALUES (%s, %s, %s, '10k-100k', %s, %s)",
        (channel_id, "@" + channel_id, f"Channel {channel_id}", "UU" + channel_id, NOW),
    )
    conn.execute("INSERT INTO niche_channels (niche, channel_id) VALUES (%s, %s)", (niche, channel_id))


def insert_video(conn, video_id, channel_id="UC1", title="Salary advice", duration_seconds=720, is_held_out=False,
                 tags=(), cleaned_description="", chapters=()):
    conn.execute(
        """
        INSERT INTO videos (video_id, channel_id, published_at, title, description, cleaned_description, tags,
                            duration_seconds, is_held_out, last_refreshed_at)
        VALUES (%s, %s, %s, %s, '', %s, %s, %s, %s, %s)
        """,
        (video_id, channel_id, NOW, title, cleaned_description, list(tags), duration_seconds, is_held_out, NOW),
    )
    for position, chapter in enumerate(chapters):
        conn.execute("INSERT INTO chapters (video_id, position, start_seconds, title) VALUES (%s, %s, %s, %s)",
                     (video_id, position, position * 60, chapter))
