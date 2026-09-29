"""An in-memory stand-in for the YouTube Data API: serves the demo Corpus and the tests."""

from contention.youtube import ChannelDetails, VideoDetails


class FakeYouTube:
    """Answers YouTube calls from fixed Channels and Videos, counting quota like the real API."""

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
