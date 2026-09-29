"""Collecting the Corpus: syncing curated Channels and their Videos from YouTube."""

from dataclasses import dataclass
from datetime import datetime, timedelta
import psycopg

from contention.niche import CuratedChannel, Niche
from contention.text import clean_description, parse_chapters
from contention.youtube import ChannelDetails, VideoDetails, YouTube

WINDOW = timedelta(days=3 * 365)  # the Corpus holds Videos from the last 3 years
RETENTION = timedelta(days=28)  # API Data, and anything derived from it, is kept at most this long
SHORTS_MAX_SECONDS = 180  # Shorts run up to 3 minutes; long-form is anything longer


@dataclass(frozen=True)
class RefreshReport:
    """What a refresh did: counts, quota spent, and handles YouTube didn't recognise."""

    channels: int
    videos: int
    quota_used: int
    unknown_handles: tuple[str, ...]


def is_long_form(video: VideoDetails) -> bool:
    """Longer than a Short can be."""
    return video.duration_seconds > SHORTS_MAX_SECONDS


def is_english(video: VideoDetails) -> bool:
    """English unless the Video says otherwise: curated Channels are English-language."""
    language = video.audio_language or video.default_language
    return language is None or language.lower().startswith("en")


def refresh(conn: psycopg.Connection, youtube: YouTube, niche: Niche, now: datetime) -> RefreshReport:
    """Bring the Niche's Channels and their long-form English Videos up to date.

    Writes a timestamped Snapshot for every Channel and Video, and each Video's
    cleaned description and Chapters.
    """
    curated_by_handle = {c.handle: c for c in niche.channels}
    channel_ids_by_handle = dict(conn.execute(
        "SELECT handle, channel_id FROM channels WHERE handle = ANY(%s)", (list(curated_by_handle),)
    ))
    unknown_handles = []
    for handle in curated_by_handle.keys() - channel_ids_by_handle.keys():
        found = youtube.channel_by_handle(handle)
        if found:
            channel_ids_by_handle[handle] = found.channel_id
        else:
            unknown_handles.append(handle)
    curated_by_channel_id = {cid: curated_by_handle[handle] for handle, cid in channel_ids_by_handle.items()}
    conn.commit()  # end the lookup's implicit transaction, so each Channel below commits on its own

    video_count = 0
    channels = youtube.channels(list(curated_by_channel_id))
    for channel in channels:
        with conn.transaction():
            _store_channel(conn, niche, channel, curated_by_channel_id[channel.channel_id], now)
            ids = youtube.upload_ids(channel.uploads_playlist_id, published_after=now - WINDOW)
            for video in youtube.videos(ids):
                if is_long_form(video) and is_english(video):
                    _store_video(conn, video, now)
                    video_count += 1

    return RefreshReport(len(channels), video_count, youtube.quota_used, tuple(sorted(unknown_handles)))


def _store_channel(
    conn: psycopg.Connection, niche: Niche, channel: ChannelDetails, curated: CuratedChannel, now: datetime
) -> None:
    conn.execute(
        """
        INSERT INTO channels (channel_id, handle, title, tier, uploads_playlist_id, last_refreshed_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (channel_id) DO UPDATE SET handle = EXCLUDED.handle, title = EXCLUDED.title,
            tier = EXCLUDED.tier, uploads_playlist_id = EXCLUDED.uploads_playlist_id,
            last_refreshed_at = EXCLUDED.last_refreshed_at
        """,
        (channel.channel_id, curated.handle, channel.title, curated.tier, channel.uploads_playlist_id, now),
    )
    conn.execute(
        "INSERT INTO niche_channels (niche, channel_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
        (niche.name, channel.channel_id),
    )
    conn.execute(
        """
        INSERT INTO channel_snapshots (channel_id, taken_at, view_count, subscriber_count, video_count)
        VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING
        """,
        (channel.channel_id, now, channel.view_count, channel.subscriber_count, channel.video_count),
    )


def _store_video(conn: psycopg.Connection, video: VideoDetails, now: datetime) -> None:
    conn.execute(
        """
        INSERT INTO videos (video_id, channel_id, published_at, title, description, cleaned_description,
                            tags, topic_categories, duration_seconds, last_refreshed_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (video_id) DO UPDATE SET title = EXCLUDED.title, description = EXCLUDED.description,
            cleaned_description = EXCLUDED.cleaned_description, tags = EXCLUDED.tags,
            topic_categories = EXCLUDED.topic_categories, duration_seconds = EXCLUDED.duration_seconds,
            last_refreshed_at = EXCLUDED.last_refreshed_at
        """,
        (video.video_id, video.channel_id, video.published_at, video.title, video.description,
         clean_description(video.description), list(video.tags), list(video.topic_categories),
         video.duration_seconds, now),
    )
    conn.execute(
        """
        INSERT INTO video_snapshots (video_id, taken_at, view_count, like_count, comment_count)
        VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING
        """,
        (video.video_id, now, video.view_count, video.like_count, video.comment_count),
    )
    conn.execute("DELETE FROM chapters WHERE video_id = %s", (video.video_id,))
    for position, chapter in enumerate(parse_chapters(video.description)):
        conn.execute(
            "INSERT INTO chapters (video_id, position, start_seconds, title) VALUES (%s, %s, %s, %s)",
            (video.video_id, position, chapter.start_seconds, chapter.title),
        )
