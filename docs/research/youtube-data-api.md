# YouTube Data API: quotas, public fields, and transcript access

Research for [#7](https://github.com/Jarrod-Bob/contention/issues/7), part of map [#6](https://github.com/Jarrod-Bob/contention/issues/6).
Sources were read on 2026-09-26. Quotas and policies change often; the API revision history below shows three relevant changes in 2026 alone.

## TL;DR

- **Quota is not the bottleneck for metadata.** The default allocation is 10,000 units/day for general methods. On top of that, `search.list` now has its **own bucket of 100 calls/day** (changed June 2026), and `videos.batchGetStats` has its own 10,000/day bucket. Listing a channel's uploads and fetching their metadata costs about **2 units per 50 Videos**, so a single day of quota covers a whole niche Corpus of tens of thousands of Videos.
- **Discovery is the scarce resource.** `search.list` is capped at 100 calls/day, which is at most about 5,000 results. Use it only to find *channels*, then walk each channel's uploads playlist.
- **You only get current snapshots.** The Data API has no historical or time-series metrics. The Analytics/Reporting APIs have history, but only for channels whose owner grants OAuth consent. A target like "views at a fixed age" means polling Videos yourself.
- **Public fields:** Videos have views, likes and comments. Dislikes have been private since Dec 2021, and `favoriteCount` is always 0. Channels have views, subscribers (rounded down to 3 significant figures, and can be hidden) and a public video count.
- **Transcripts have no ToS-compliant route for other people's Videos.** `captions.download` needs edit permission on the Video. `youtube-transcript-api` calls undocumented web-client endpoints, and YouTube's ToS forbids automated access without written permission.
- **Two policy constraints matter for the design:**
  1. Public ("Non-Authorized") API data must not be stored for **more than 30 days** without being refreshed or deleted.
  2. API clients must not "use API Data to create new or derived data or metrics".

  Both bear directly on the Corpus and on the choice of predictor target (see [Constraints on the predictor target](#constraints-on-the-predictor-target)).

## 1. Quota

**Default allocation.** "Projects that enable the YouTube Data API have a default quota allocation of 100 search.list calls, 100 videos.insert calls, and 10,000 units per day combined for all other endpoints." Quotas reset at midnight Pacific Time. Every request costs at least 1 unit, including invalid ones, and every extra page of results is charged again. ([Quota Calculator](https://developers.google.com/youtube/v3/determine_quota_cost), last updated 2026-09-15)

**Separate quota buckets (new).** On 2026-06-01 the API moved to "a granular quota system", and "API calls to the videos.insert and search.list methods will be charged to their own respective quota buckets". On 2026-06-03 it added `videos.batchGetStats` at "1 unit in its own granular quota bucket", with a default of 10,000 units/day. ([Revision history](https://developers.google.com/youtube/v3/revision_history))

> Older blog posts that say "search costs 100 units" are out of date. Search no longer draws from the 10,000-unit pool, but it is limited to 100 calls/day.

**Unit costs of the calls we need** ([Quota Calculator](https://developers.google.com/youtube/v3/determine_quota_cost) and the method reference pages):

| Call | Cost | Items per call | Auth | Use |
|---|---|---|---|---|
| `search.list` | 1 call from a 100/day bucket | up to 50 (`maxResults` 0–50) | API key | Discover channels or Videos by keyword. `type=video&videoDuration=long` filters to Videos over 20 min, `medium` to 4–20 min. ([docs](https://developers.google.com/youtube/v3/docs/search/list)) |
| `channels.list` | 1 | up to 50 ids | API key | Channel snippet and stats, plus `contentDetails.relatedPlaylists.uploads` (the uploads playlist id). Also supports `forHandle`. ([docs](https://developers.google.com/youtube/v3/docs/channels)) |
| `playlistItems.list` | 1 | up to 50 (`maxResults` 0–50) | API key | Page through a channel's uploads playlist. Returns the videoId and `contentDetails.videoPublishedAt`. ([docs](https://developers.google.com/youtube/v3/docs/playlistItems/list)) |
| `videos.list` | 1 | up to 50 ids per call (widely used limit; see note) | API key | Full metadata and statistics. ([docs](https://developers.google.com/youtube/v3/docs/videos/list)) |
| `videos.batchGetStats` | 1 from its own 10,000/day bucket | comma-separated ids (maximum not documented) | none needed for public Videos | Cheap stats refresh: views, likes, comments, publishTime, duration. ([docs](https://developers.google.com/youtube/v3/docs/videos/batchGetStats)) |
| `videoCategories.list` | 1 | – | API key | Maps category ids to names. |
| `commentThreads.list` | 1 | up to 100 | API key | Comment text, if we ever want it (not in scope). |
| `captions.list` | 50 | – | **OAuth** | Lists caption tracks only, without their text. ([docs](https://developers.google.com/youtube/v3/docs/captions/list)) |
| `captions.download` | 200 | – | **OAuth, and the user must be able to edit the Video** | ([docs](https://developers.google.com/youtube/v3/docs/captions/download)) |

Note on `videos.list`: its reference page documents `maxResults` 1–50 and says it is "not supported for use in conjunction with the id parameter". It does not state a maximum number of ids. **50 ids per call is the widely used practical limit (unverified in the docs); plan for it.**

## 2. Public fields

### Per Video (`videos.list`, parts `snippet,contentDetails,statistics,topicDetails,status`)

Source: [videos resource](https://developers.google.com/youtube/v3/docs/videos).

- **snippet:**
  - `publishedAt`, `channelId`, `title` (max 100 chars), `description` (max 5000 bytes), `tags[]` (max 500 chars total)
  - `categoryId`, `defaultLanguage`, `defaultAudioLanguage`, `thumbnails` (higher resolutions fhd/qhd/uhd added in Sept 2026)
  - Tags are visible through the API even though the YouTube UI hides them.
- **contentDetails:**
  - `duration` (ISO 8601, e.g. `PT15M33S`)
  - `definition` (hd/sd)
  - `caption`: a boolean that says whether captions exist. It does not give their text.
  - `licensedContent`
- **statistics:**
  - `viewCount`, `likeCount`, `commentCount`. These are returned as strings; the type annotation was corrected in Aug 2022.
  - `dislikeCount`: "made private as of December 13, 2021 … included in an API response only if the API request was authenticated by the video owner."
  - `favoriteCount`: deprecated since 2015, always 0.
  - `viewCount` semantics changed on **2026-08-24**. For all formats it now counts "views the moment a video begins to play (includes autoplay, hold the pointer over, and click/tap to play)". ([revision history, 2026-08-27](https://developers.google.com/youtube/v3/revision_history)) **View counts before and after that date are not strictly comparable.** This matters for any target built on views.
- **topicDetails:** topic ids and Wikipedia category URLs. They are a free coarse topic signal.
- **status:**
  - privacy status, license, `embeddable`, `madeForKids`
  - `containsSyntheticMedia` (added Oct 2024)
- **paidProductPlacementDetails.hasPaidProductPlacement**
- **liveStreamingDetails:** present for livestreams. We can use it to exclude them.

Hidden or missing values:

- Creators can hide like counts, and can disable comments. **In those cases `likeCount` or `commentCount` is typically absent from the response.** The docs don't say this explicitly (unverified), so the collector must treat these fields as optional.
- **The API has no "is Short" flag.** A long-form filter has to rely on `duration`, for example ≥ 4 min, which also matches `search.list`'s `videoDuration=medium|long` buckets.

### Per channel (`channels.list`)

Source: [channels resource](https://developers.google.com/youtube/v3/docs/channels).

- **statistics:**
  - `viewCount`: all-time total, using the same new counting rule since 2026-08-24.
  - `subscriberCount`: "rounded down to three significant figures".
  - `hiddenSubscriberCount`: a boolean. When it is true, no subscriber count is shown.
  - `videoCount`: public videos only.
- **snippet:** title, description, customUrl (handle), `publishedAt`, country, thumbnails
- **contentDetails.relatedPlaylists.uploads:** the key to cheap enumeration of a channel's Videos
- **brandingSettings:** keywords etc.
- **topicDetails**

## 3. Historical and time-series metrics

**The Data API returns only the current value of every statistic.** No endpoint returns past views, likes or subscribers for a Video or channel. This follows from the resource definitions above: every statistic is a single scalar, with no date parameter.

**Historical daily metrics exist only in the YouTube Analytics and Reporting APIs.** Those APIs "utilize OAuth 2.0 for authorizing access to private user data" and don't support service accounts ([authorization guide](https://developers.google.com/youtube/reporting/guides/authorization)). In other words, only the channel owner, or a CMS content owner, can get them. They are not usable for a multi-channel public Corpus.

**What follows:** any time-dependent target must be built by polling Videos ourselves. Examples are views at day N, growth rate, or the ratio of early to late views. The one exception is the Video's current age, which we can compute from `publishedAt`.

## 4. Transcripts

- **Official API: not available for other people's Videos.**
  - `captions.list` (50 units) needs OAuth and returns only track metadata.
  - `captions.download` (200 units) "requires the user to have permission to edit the video" ([docs](https://developers.google.com/youtube/v3/docs/captions/download)).
- **`youtube-transcript-api` (PyPI, v1.2.4):**
  - Its README says: "This code uses an undocumented part of the YouTube API, which is called by the YouTube web-client."
  - It needs no API key and it handles auto-generated captions.
  - It warns there is "no guarantee that it won't stop working tomorrow".
  - It documents YouTube blocking cloud-provider IPs (`RequestBlocked`/`IpBlocked`) and recommends rotating residential proxies. ([README](https://github.com/jdepoix/youtube-transcript-api))
- **YouTube Terms of Service:**
  - You may not "access the Service using any automated means (such as robots, botnets or scrapers) except (a) in the case of public search engines, in accordance with YouTube's robots.txt file; or (b) with YouTube's prior written permission".
  - You may not "access, reproduce, download … any part of the Service or any Content except (a) as expressly authorized by the Service; or (b) with prior written permission". ([YouTube ToS](https://www.youtube.com/static?template=terms))
- **YouTube API Services Developer Policies:** you must not "scrape YouTube Applications or Google Applications, or obtain scraped YouTube data or content" ([Developer Policies](https://developers.google.com/youtube/terms/developer-policies)).
- **Self-transcribing** (downloading audio and running Whisper) is also "download[ing] … Content" without authorization, so it is equally outside the terms.
- **YouTube Researcher Program:** the sanctioned route to expanded data access. It is limited to "a student, research-focused staff, or faculty member affiliated with an accredited, higher-education institution" ([policies](https://research.youtube/policies/)), so it probably doesn't apply here.

**Conclusion:** strictly within YouTube's terms, **transcripts of third-party Videos cannot be obtained.** The options for the map are:

- (a) run hybrid RAG over title, description, tags and topic data only
- (b) knowingly accept the ToS risk of `youtube-transcript-api` for a personal learning tool, at low volume from a residential IP
- (c) use transcripts only for Videos the user owns, via OAuth + `captions.download`

This is a decision for the user, not something research can settle.

## 5. Storage and derived-metric policies

These come from the [Developer Policies](https://developers.google.com/youtube/terms/developer-policies), section III.E "Handling YouTube Data". They apply to any API client, including a local personal tool.

- **The 30-day rule for public data.**
  - "API Clients may temporarily store limited amounts of Non-Authorized Data for as long as is necessary for the purposes of the API Client but not longer than 30 calendar days … after 30 calendar days, the API Client must either delete or refresh the stored data."
  - Specifically: "an API Client must not store statistics retrieved as Non-Authorized Data for more than 30 days."
  - Clients "may display historical API Data provided that it is presented accurately in context of time."
- **No derived metrics.**
  - "Your API Clients must not (i) replace API Data with similar, independently calculated data, or (ii) access or use API Data to create new or derived data or metrics."
  - The worked example forbids "a score that factors in likes, total views, or any other API Data".
- **No business insights.** Do not "aggregate API Data or otherwise use API Data … to gain insights into YouTube's usage, revenue, or any other aspects of YouTube's business."

Practical implication: a compliant Corpus needs a **refresh-or-purge job** that re-fetches every stored Video and channel within 30 days of its last fetch, or drops it. Refreshing is cheap: about 1 unit per 50 Videos, or `batchGetStats` from its own bucket. A 60k-Video Corpus is about 1,200 units per full refresh.

## 6. How many Videos does a few days of quota yield?

Cheapest discovery strategy:

1. `search.list` with `type=channel` (or `type=video&videoDuration=long|medium`, keeping only the channelIds) over niche keywords. Each call is 1 of the 100 daily calls and returns up to 50 results. Paging through results spends calls. In practice this gives a few hundred to a couple of thousand distinct candidate channels per day.
2. `channels.list` on 50 channel ids at a time costs 1 unit and returns stats plus the uploads playlist id.
3. `playlistItems.list` on each uploads playlist costs 1 unit per 50 Videos.
4. `videos.list` on 50 Video ids at a time costs 1 unit and returns full metadata plus stats. Filter to long-form by `duration` here.

Cost is about **2 units per 50 Videos (~0.04 units/Video)** plus about 0.02 units per channel.

| Scenario | Units | Days of 10k quota |
|---|---|---|
| 200 channels × 300 Videos = 60,000 Videos | ~2,400 + 4 | 0.25 |
| 1,000 channels × 300 Videos = 300,000 Videos | ~12,000 | ~1.2 |
| Theoretical ceiling per day | 10,000 | ~250,000 Videos/day |

The real limits are **discovery** (100 search calls/day finds channels, not Videos) and the **30-day refresh obligation**. The size of the stored Corpus sets a recurring refresh cost of about 0.02 units per Video every 30 days, which is trivial. **So quota is effectively not a constraint for a single-niche Corpus. A few days of default quota could collect hundreds of thousands of Videos' metadata. Channel discovery (about 100 searches/day) and, above all, transcripts are the binding limits.**

Caveats:

- The uploads playlist includes Shorts and livestreams, which we filter out after `videos.list`.
- Deleted or private Videos drop out silently.
- Some Videos have `likeCount` or `commentCount` missing.

## Constraints on the predictor target

1. **Snapshot-only data.**
   - "Views relative to channel median" and "engagement/like rate" can be computed from one crawl, but they mix Videos of different ages. They need age as a feature, or a minimum-age filter such as ≥ 30 days old.
   - "Views at a fixed age N" needs repeated polling of newly published Videos. We can't backfill it.
   - Combined with the 30-day storage rule, N ≤ 30 days is the practical ceiling: day-7 or day-28 views are possible, day-90 views are not. That also means collection has to run for weeks before a training set exists.
2. **The 30-day storage rule** also means a long-lived training table of raw stats is non-compliant unless it is refreshed. Refreshing overwrites the snapshot, so a fixed-age label can't be kept across refreshes.
3. **The derived-metrics prohibition**, read literally, covers all four candidate targets. Each one is a new metric computed from API Data: a ratio to the channel median, (likes+comments)/views, likes/views, and interpolated views at age N. Raw `viewCount` together with age as a feature is the least "derived" option. How strictly this clause applies to a private, non-displayed learning model is a risk judgement for the user. The policy text does not carve out personal or offline use.
4. **The view-count definition changed on 2026-08-24.** Any target based on views will see a level shift for Videos accumulating views across that date. Collect after the change, or restrict training to Videos published after 2026-08-24.
5. **Subscriber counts** are rounded to 3 significant figures and sometimes hidden. They are usable as a coarse feature but not as a target.
6. **Likes** are sometimes hidden, so a like-rate target has missing labels. Dislikes are unavailable.
