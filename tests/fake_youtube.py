"""An in-memory stand-in for the YouTube Data API, for tests."""

from datetime import UTC, datetime

from contention.youtube import ChannelDetails, VideoDetails


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


class FakeYouTube:
    def __init__(self, channels_by_handle: dict[str, ChannelDetails], videos: list[VideoDetails]):
        self.channels_by_handle = channels_by_handle
        self.all_videos = videos
        self.quota_used = 0

    def channel_by_handle(self, handle):
        self.quota_used += 1
        return self.channels_by_handle.get(handle)

    def channels(self, ids):
        self.quota_used += 1
        return [c for c in self.channels_by_handle.values() if c.channel_id in ids]

    def upload_ids(self, playlist_id, published_after):
        self.quota_used += 1
        channel_id = "UC" + playlist_id[2:]
        return [v.video_id for v in self.all_videos
                if v.channel_id == channel_id and v.published_at >= published_after]

    def videos(self, ids):
        self.quota_used += 1
        return [v for v in self.all_videos if v.video_id in ids]
