"""Reading public data from the YouTube Data API v3."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import httpx

from contention.text import parse_duration

API = "https://www.googleapis.com/youtube/v3/"
BATCH = 50  # most ids one list call accepts


@dataclass(frozen=True)
class VideoDetails:
    """A Video as the API returns it: metadata, plus the metrics a Snapshot records."""

    video_id: str
    channel_id: str
    published_at: datetime
    title: str
    description: str
    tags: tuple[str, ...]
    topic_categories: tuple[str, ...]
    duration_seconds: int
    audio_language: str | None
    default_language: str | None
    view_count: int
    like_count: int | None  # None when hidden
    comment_count: int | None  # None when hidden or disabled


@dataclass(frozen=True)
class ChannelDetails:
    """A Channel as the API returns it: metadata, plus the metrics a Snapshot records."""

    channel_id: str
    title: str
    uploads_playlist_id: str
    view_count: int
    subscriber_count: int | None  # None when hidden
    video_count: int


def _parse_channel(resource: dict) -> ChannelDetails:
    statistics = resource.get("statistics", {})
    hidden = statistics.get("hiddenSubscriberCount", False)
    return ChannelDetails(
        channel_id=resource["id"],
        title=resource["snippet"]["title"],
        uploads_playlist_id=resource["contentDetails"]["relatedPlaylists"]["uploads"],
        view_count=int(statistics.get("viewCount", 0)),
        subscriber_count=None if hidden else _count(statistics, "subscriberCount"),
        video_count=int(statistics.get("videoCount", 0)),
    )


def _count(statistics: dict, field: str) -> int | None:
    return int(statistics[field]) if field in statistics else None


def _parse_video(resource: dict) -> VideoDetails:
    snippet, statistics = resource["snippet"], resource.get("statistics", {})
    return VideoDetails(
        video_id=resource["id"],
        channel_id=snippet["channelId"],
        published_at=_timestamp(snippet["publishedAt"]),
        title=snippet["title"],
        description=snippet.get("description", ""),
        tags=tuple(snippet.get("tags", ())),
        topic_categories=tuple(resource.get("topicDetails", {}).get("topicCategories", ())),
        duration_seconds=parse_duration(resource["contentDetails"]["duration"]),
        audio_language=snippet.get("defaultAudioLanguage"),
        default_language=snippet.get("defaultLanguage"),
        view_count=int(statistics.get("viewCount", 0)),
        like_count=_count(statistics, "likeCount"),
        comment_count=_count(statistics, "commentCount"),
    )


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _batches(ids: list[str]) -> Iterator[list[str]]:
    for start in range(0, len(ids), BATCH):
        yield ids[start:start + BATCH]


class YouTube(Protocol):
    """What the rest of contention needs from YouTube. HttpYouTube is the real one."""

    quota_used: int

    def channel_by_handle(self, handle: str) -> ChannelDetails | None: ...
    def channels(self, ids: list[str]) -> list[ChannelDetails]: ...
    def upload_ids(self, playlist_id: str, published_after: datetime) -> list[str]: ...
    def videos(self, ids: list[str]) -> list[VideoDetails]: ...


class HttpYouTube:
    """The YouTube Data API over HTTP, counting the quota units it spends."""

    def __init__(self, api_key: str, transport: httpx.BaseTransport | None = None):
        self._client = httpx.Client(base_url=API, params={"key": api_key}, transport=transport, timeout=30)
        self.quota_used = 0

    def _get(self, endpoint: str, **params) -> dict:
        response = self._client.get(endpoint, params=params)
        self.quota_used += 1  # every list call used here costs 1 unit
        response.raise_for_status()
        return response.json()

    def upload_ids(self, playlist_id: str, published_after: datetime) -> list[str]:
        """Ids of a Channel's uploads published after a moment, newest first.

        Uploads playlists are ordered newest first, so paging stops at the first
        older Video. Private or deleted Videos, which have no publish date, are skipped.
        """
        ids = []
        page_token = None
        while True:
            params = {"part": "contentDetails", "playlistId": playlist_id, "maxResults": 50}
            if page_token:
                params["pageToken"] = page_token
            page = self._get("playlistItems", **params)
            for entry in page.get("items", []):
                content = entry["contentDetails"]
                if "videoPublishedAt" not in content:
                    continue
                if _timestamp(content["videoPublishedAt"]) < published_after:
                    return ids
                ids.append(content["videoId"])
            page_token = page.get("nextPageToken")
            if not page_token:
                return ids

    def videos(self, ids: list[str]) -> list[VideoDetails]:
        """Details of Videos by id, fetched 50 at a time. Missing Videos are skipped."""
        found = []
        for batch in _batches(ids):
            page = self._get("videos", part="snippet,contentDetails,statistics,topicDetails", id=",".join(batch))
            found.extend(_parse_video(resource) for resource in page.get("items", []))
        return found

    def channel_by_handle(self, handle: str) -> ChannelDetails | None:
        """The Channel with this handle (e.g. `@example`), or None if there isn't one."""
        page = self._get("channels", part="snippet,contentDetails,statistics", forHandle=handle)
        items = page.get("items", [])
        return _parse_channel(items[0]) if items else None

    def channels(self, ids: list[str]) -> list[ChannelDetails]:
        """Details of Channels by id, fetched 50 at a time. Missing Channels are skipped."""
        found = []
        for batch in _batches(ids):
            page = self._get("channels", part="snippet,contentDetails,statistics", id=",".join(batch))
            found.extend(_parse_channel(resource) for resource in page.get("items", []))
        return found
