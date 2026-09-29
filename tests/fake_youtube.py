"""Test helpers around the in-memory YouTube: Channels and Videos with sensible defaults."""

from datetime import UTC, datetime

from contention.fake_youtube import FakeYouTube
from contention.youtube import ChannelDetails, VideoDetails

__all__ = ["FakeYouTube", "channel_details", "video_details"]


def channel_details(channel_id="UC1", subscribers=12_300, **fields):
    return ChannelDetails(**{
        "channel_id": channel_id, "title": f"Channel {channel_id}", "uploads_playlist_id": "UU" + channel_id[2:],
        "view_count": 900_000, "subscriber_count": subscribers, "video_count": 210, **fields,
    })


def video_details(video_id, channel_id="UC1", **fields):
    return VideoDetails(**{
        "video_id": video_id, "channel_id": channel_id,
        "published_at": datetime(2026, 1, 2, tzinfo=UTC),
        "title": f"Title {video_id}", "description": "About this video", "tags": ("career",),
        "topic_categories": (), "duration_seconds": 720, "audio_language": "en", "default_language": None,
        "view_count": 1500, "like_count": 40, "comment_count": 5, **fields,
    })
