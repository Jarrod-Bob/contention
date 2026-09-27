from datetime import UTC, datetime

import httpx

from contention.youtube import HttpYouTube


def fake_api(pages):
    """An httpx transport serving canned YouTube responses, keyed by (endpoint, pageToken or id)."""
    requests = []

    def handler(request):
        requests.append(request)
        endpoint = request.url.path.rsplit("/", 1)[-1]
        key = request.url.params.get("pageToken") or request.url.params.get("id") or request.url.params.get("forHandle")
        return httpx.Response(200, json=pages[(endpoint, key)])

    return httpx.MockTransport(handler), requests


def item(video_id, published):
    return {"contentDetails": {"videoId": video_id, "videoPublishedAt": published}}


def test_upload_ids_follows_pages_and_stops_at_the_window():
    transport, requests = fake_api({
        ("playlistItems", None): {
            "items": [item("v1", "2026-09-01T00:00:00Z"), item("v2", "2025-01-01T00:00:00Z")],
            "nextPageToken": "p2",
        },
        ("playlistItems", "p2"): {
            "items": [item("v3", "2024-01-01T00:00:00Z"), item("v4", "2022-01-01T00:00:00Z")],
            "nextPageToken": "p3",
        },
    })
    youtube = HttpYouTube("key", transport=transport)

    ids = youtube.upload_ids("UU123", published_after=datetime(2023, 9, 27, tzinfo=UTC))

    assert ids == ["v1", "v2", "v3"]
    assert len(requests) == 2  # never asked for page p3
    assert youtube.quota_used == 2


def video(video_id, **overrides):
    resource = {
        "id": video_id,
        "snippet": {
            "channelId": "UC1",
            "publishedAt": "2026-01-02T03:04:05Z",
            "title": f"Title {video_id}",
            "description": "About this video",
            "tags": ["career"],
            "defaultAudioLanguage": "en-US",
        },
        "contentDetails": {"duration": "PT12M3S"},
        "statistics": {"viewCount": "1500", "likeCount": "40", "commentCount": "5"},
        "topicDetails": {"topicCategories": ["https://en.wikipedia.org/wiki/Knowledge"]},
    }
    for section, fields in overrides.items():
        resource[section] = fields
    return resource


def test_videos_are_fetched_in_batches_of_50_and_parsed():
    ids = [f"v{n}" for n in range(51)]
    hidden = video("v50", statistics={"viewCount": "7"})  # likes and comments hidden
    transport, requests = fake_api({
        ("videos", ",".join(ids[:50])): {"items": [video(i) for i in ids[:50]]},
        ("videos", "v50"): {"items": [hidden]},
    })
    youtube = HttpYouTube("key", transport=transport)

    videos = youtube.videos(ids)

    assert len(requests) == 2 and youtube.quota_used == 2
    first = videos[0]
    assert first.video_id == "v0"
    assert first.channel_id == "UC1"
    assert first.published_at == datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    assert first.duration_seconds == 723
    assert first.audio_language == "en-US"
    assert first.tags == ("career",)
    assert (first.view_count, first.like_count, first.comment_count) == (1500, 40, 5)
    assert first.topic_categories == ("https://en.wikipedia.org/wiki/Knowledge",)
    assert (videos[-1].like_count, videos[-1].comment_count) == (None, None)


def channel(channel_id, hidden_subscribers=False):
    return {
        "id": channel_id,
        "snippet": {"title": f"Channel {channel_id}", "customUrl": "@example"},
        "contentDetails": {"relatedPlaylists": {"uploads": "UU" + channel_id[2:]}},
        "statistics": {
            "viewCount": "900000",
            "subscriberCount": "12300",
            "hiddenSubscriberCount": hidden_subscribers,
            "videoCount": "210",
        },
    }


def test_looks_up_channels_by_handle_and_by_id():
    transport, _ = fake_api({
        ("channels", "@example"): {"items": [channel("UCabc")]},
        ("channels", "@nobody"): {"pageInfo": {"totalResults": 0}},
        ("channels", "UCabc,UCdef"): {"items": [channel("UCabc"), channel("UCdef", hidden_subscribers=True)]},
    })
    youtube = HttpYouTube("key", transport=transport)

    found = youtube.channel_by_handle("@example")
    assert (found.channel_id, found.title, found.uploads_playlist_id) == ("UCabc", "Channel UCabc", "UUabc")
    assert (found.view_count, found.subscriber_count, found.video_count) == (900000, 12300, 210)

    assert youtube.channel_by_handle("@nobody") is None

    both = youtube.channels(["UCabc", "UCdef"])
    assert [c.subscriber_count for c in both] == [12300, None]
    assert youtube.quota_used == 3
