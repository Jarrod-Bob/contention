"""The synthetic demo Corpus: made-up Channels and Videos in a database of their own.

Every screenshot, README example and demo uses it, so nothing real from YouTube
appears in published material. `load` fills a demo database by refreshing it
from an in-memory YouTube that serves the synthetic Corpus, so the same
collection code runs as on real data and no API key is needed. The database is
marked as the demo (the `demo_corpus` table): the app shows BANNER on it, and
`refresh` on it reads the synthetic Corpus instead of YouTube.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from contention import db
from contention.collect import RefreshReport, refresh as refresh_corpus
from contention.fake_youtube import FakeYouTube
from contention.niche import Niche
from contention.youtube import ChannelDetails, VideoDetails

NICHE = "demo"  # the niche folder listing the made-up Channels
DATABASE_URL = "postgresql:///contention_demo"  # used unless DEMO_DATABASE_URL says otherwise
BANNER = "Demo data: a synthetic Corpus of made-up Channels and Videos, not from YouTube. Its numbers are illustrative."

# Snapshots `load` writes, as days before loading: a short history, well inside the 28-day limit.
SNAPSHOT_DAYS_AGO = (14, 7, 0)
# Days after publishing at which a Video has half its eventual views.
HALF_VIEWS_DAYS = 10


@dataclass(frozen=True)
class _Channel:
    handle: str
    channel_id: str
    title: str
    subscribers: int
    view_count: int
    video_count: int


@dataclass(frozen=True)
class _Video:
    video_id: str
    handle: str
    days_old: int  # when the demo was loaded
    duration: str  # m:ss or h:mm:ss
    eventual_views: int
    title: str
    summary: str
    chapters: tuple[str, ...] = ()  # "m:ss Title" lines, as a creator writes them


_CHANNELS = (
    _Channel("@demo.firstcommit", "UCdemo-firstcommit", "First Commit Diaries", 4_200, 61_000, 38),
    _Channel("@demo.queuetheinterview", "UCdemo-queuetheinterview", "Queue the Interview", 8_900, 240_000, 55),
    _Channel("@demo.standupnotes", "UCdemo-standupnotes", "Standup Notes", 46_000, 2_900_000, 120),
    _Channel("@demo.offerladder", "UCdemo-offerladder", "Offer Ladder", 230_000, 18_000_000, 160),
    _Channel("@demo.systemsketch", "UCdemo-systemsketch", "System Sketch", 680_000, 51_000_000, 140),
    _Channel("@demo.careerstackweekly", "UCdemo-careerstackweekly", "Career Stack Weekly", 1_700_000,
             310_000_000, 420),
)

_VIDEOS = (
    # First Commit Diaries (1k-10k)
    _Video("demo-fc01", "@demo.firstcommit", 5, "11:40", 900, "My first code review got 47 comments",
           "I opened my first real pull request at work and it came back covered in comments. Here's how I "
           "worked through them without panicking.",
           ("0:00 The pull request", "1:50 Reading every comment", "5:12 What my lead actually meant",
            "9:30 What I'd do differently")),
    _Video("demo-fc02", "@demo.firstcommit", 40, "14:05", 2_300, "Bootcamp to junior developer: my honest first 6 months",
           "Six months after a coding bootcamp: what the job is really like, what I was ready for and what I wasn't.",
           ("0:00 Where I started", "2:30 The first week", "6:45 Imposter syndrome", "11:10 What helped most")),
    _Video("demo-fc03", "@demo.firstcommit", 120, "9:20", 1_100, "Things nobody told me about on-call as a junior",
           "My first on-call rotation, the 3am page, and the runbook habits I picked up afterwards.",
           ("0:00 Intro", "1:05 The first page", "4:40 Runbooks", "7:30 Asking for help")),
    _Video("demo-fc04", "@demo.firstcommit", 300, "16:45", 5_400, "How I got my first developer job with no degree",
           "Portfolio projects, 140 applications and the referral that finally worked.\n\n"
           "Sponsored by a made-up course platform. Follow me for more: https://example.com/demo",
           ("0:00 My background", "3:15 Portfolio projects", "8:00 Applications that went nowhere",
            "12:20 The referral")),
    _Video("demo-fc05", "@demo.firstcommit", 520, "8:10", 700, "My desk setup as a junior developer (on a budget)",
           "A tour of the cheap desk setup I code on every day."),
    _Video("demo-fc06", "@demo.firstcommit", 30, "0:58", 3_000, "One tip for your first standup",
           "Keep it short. (A Short: refresh leaves it out of the Corpus.)"),
    # Queue the Interview (1k-10k)
    _Video("demo-qi01", "@demo.queuetheinterview", 9, "42:10", 1_800,
           "Mock interview: two sum to sliding window (junior candidate)",
           "A viewer joins for a live coding interview on arrays and hashing, with feedback at the end.",
           ("0:00 Meet the candidate", "3:20 Two sum", "15:40 Sliding window", "34:00 Feedback")),
    _Video("demo-qi02", "@demo.queuetheinterview", 60, "38:30", 3_900,
           "Mock interview: design a URL shortener with a viewer",
           "A first system design interview for a new-grad candidate, start to finish.",
           ("0:00 Requirements", "6:10 API design", "14:25 Storage", "27:50 Scaling reads", "34:10 Feedback")),
    _Video("demo-qi03", "@demo.queuetheinterview", 200, "47:00", 6_100,
           "Mock interview: graph problems when you freeze up",
           "The candidate blanks on a graph question. We practise getting unstuck out loud.",
           ("0:00 Intro", "4:00 The problem", "12:30 Freezing up", "20:15 Talking it through", "40:00 Debrief")),
    _Video("demo-qi04", "@demo.queuetheinterview", 410, "25:15", 2_200, "Reviewing a viewer's resume live",
           "Line-by-line resume feedback for a career switcher applying to backend roles."),
    _Video("demo-qi05", "@demo.queuetheinterview", 700, "33:40", 1_500,
           "Mock behavioural interview: tell me about a conflict",
           "Practising the behavioural questions that trip people up, with a stronger answer at the end.",
           ("0:00 Intro", "2:45 The first answer", "13:30 Structuring the story", "26:00 A stronger answer")),
    # Standup Notes (10k-100k)
    _Video("demo-sn01", "@demo.standupnotes", 3, "12:30", 14_000, "A day in my life as a mid-level engineer (remote)",
           "Deep work, one meeting too many, and shipping a small feature from my kitchen table.",
           ("0:00 Morning routine", "2:40 Deep work block", "6:15 Standup and meetings", "10:05 Shipping")),
    _Video("demo-sn02", "@demo.standupnotes", 25, "18:20", 22_000, "How I write design docs that actually get read",
           "A template and the habits that get reviewers to finish reading.",
           ("0:00 Why docs get ignored", "3:30 My template", "9:45 Getting reviews", "15:10 Examples")),
    _Video("demo-sn03", "@demo.standupnotes", 90, "10:05", 9_500, "Why I stopped taking meetings before noon",
           "An experiment with protecting my mornings, and what it did to my output.",
           ("0:00 The experiment", "2:20 Pushback from my team", "6:30 The results")),
    _Video("demo-sn04", "@demo.standupnotes", 250, "21:40", 31_000,
           "What my engineering manager looks for in a promotion packet",
           "I sat down with my manager to go through how promotion cases are really judged.",
           ("0:00 Intro", "2:10 Scope and impact", "9:30 Writing it down", "15:45 Common mistakes",
            "19:20 Timing")),
    _Video("demo-sn05", "@demo.standupnotes", 480, "13:15", 12_000, "Office day vs remote day: a side by side",
           "The same week, split between the office and home. Which one got more done?"),
    _Video("demo-sn06", "@demo.standupnotes", 900, "15:50", 8_000, "My note-taking system for a big codebase",
           "How I keep track of a large codebase I didn't write.",
           ("0:00 The problem", "2:50 Daily notes", "8:10 Maps of the code", "12:30 Reviewing notes")),
    # Offer Ladder (100k-500k)
    _Video("demo-ol01", "@demo.offerladder", 12, "19:30", 85_000,
           "How to negotiate your first tech offer (word-for-word script)",
           "Exactly what to say on the offer call, even if you have no competing offer.",
           ("0:00 Why negotiate", "2:45 Before the call", "7:30 The script", "14:10 Handling pushback")),
    _Video("demo-ol02", "@demo.offerladder", 70, "24:10", 140_000, "How hiring managers set salary bands",
           "Levels, bands and where the flexibility really is, explained by a former hiring manager.",
           ("0:00 Intro", "3:00 Levels", "9:40 Bands", "16:20 Where there's room", "21:00 Recap")),
    _Video("demo-ol03", "@demo.offerladder", 160, "16:00", 60_000, "Senior to staff: what changes and what doesn't",
           "The jump from senior to staff engineer: scope, influence and the work you stop doing.",
           ("0:00 Intro", "2:30 Scope", "7:15 Influence without authority", "12:40 What you stop doing")),
    _Video("demo-ol04", "@demo.offerladder", 330, "22:45", 210_000, "Counter-offers: when to take them and when to walk",
           "Your company matched the offer. Should you stay?",
           ("0:00 The situation", "4:10 Why companies counter", "10:30 Questions to ask", "18:00 My advice")),
    _Video("demo-ol05", "@demo.offerladder", 620, "14:30", 45_000, "Equity explained for engineers: RSUs, options and refreshers",
           "What your equity is worth, how vesting works, and what to ask before you sign.",
           ("0:00 Intro", "1:40 RSUs", "5:20 Options", "9:50 Refreshers", "12:30 Questions to ask")),
    _Video("demo-ol06", "@demo.offerladder", 1000, "17:20", 95_000, "Should you switch companies to get promoted?",
           "Internal promotion versus leaving for a level up: the trade-offs."),
    # System Sketch (500k-1M)
    _Video("demo-ss01", "@demo.systemsketch", 7, "28:40", 120_000,
           "Design a chat app: system design interview walkthrough",
           "A full walkthrough of a messaging system: delivery, presence and storage.",
           ("0:00 Requirements", "4:30 High-level design", "11:15 Message delivery", "19:40 Presence",
            "24:50 Storage")),
    _Video("demo-ss02", "@demo.systemsketch", 45, "31:15", 260_000, "Design a rate limiter in 30 minutes",
           "Token buckets, sliding windows and where the limiter lives.",
           ("0:00 Requirements", "3:50 Algorithms", "14:20 Distributed limits", "25:30 Trade-offs")),
    _Video("demo-ss03", "@demo.systemsketch", 150, "35:00", 180_000,
           "Caching strategies every system design interview asks about",
           "Cache-aside, write-through, eviction and invalidation, with diagrams.",
           ("0:00 Intro", "3:10 Cache-aside", "10:45 Write-through", "18:30 Eviction", "27:00 Invalidation")),
    _Video("demo-ss04", "@demo.systemsketch", 380, "26:20", 410_000, "Design a news feed: the version interviewers want",
           "Fan-out on write versus read, ranking, and the follow-up questions to expect.",
           ("0:00 Requirements", "5:00 Fan-out", "13:40 Ranking", "21:10 Follow-ups")),
    _Video("demo-ss05", "@demo.systemsketch", 760, "40:05", 150_000, "Consistent hashing, drawn out step by step",
           "Why consistent hashing exists and how virtual nodes fix the hot spots."),
    _Video("demo-ss06", "@demo.systemsketch", 1050, "22:30", 90_000, "How I'd study system design in 4 weeks",
           "A week-by-week plan for system design interview preparation.",
           ("0:00 Week 1: fundamentals", "6:00 Week 2: classic designs", "12:30 Week 3: mock interviews",
            "18:00 Week 4: review")),
    # Career Stack Weekly (1M+)
    _Video("demo-cs01", "@demo.careerstackweekly", 2, "16:10", 380_000,
           "The tech job market this month: hiring, layoffs and what's next",
           "A monthly roundup of made-up hiring news for the demo.",
           ("0:00 Headlines", "3:20 Hiring", "8:40 Layoffs", "12:50 What's next")),
    _Video("demo-cs02", "@demo.careerstackweekly", 35, "20:45", 720_000, "Is it still worth learning to code?",
           "A long look at whether learning to code still pays off for career switchers.",
           ("0:00 The question", "4:15 Entry-level roles", "11:30 Other paths", "17:40 My answer")),
    _Video("demo-cs03", "@demo.careerstackweekly", 100, "13:30", 510_000,
           "AI coding tools at work: what engineers actually say",
           "Engineers on how AI coding tools changed their day-to-day work.",
           ("0:00 Intro", "2:00 Speed", "6:30 Code review", "10:15 Juniors")),
    _Video("demo-cs04", "@demo.careerstackweekly", 280, "24:00", 1_100_000,
           "Why junior roles disappeared (and where they went)",
           "Where entry-level engineering jobs went, and how new grads are getting in now.",
           ("0:00 Intro", "3:40 What changed", "10:20 Where the roles went", "18:30 How people get in now")),
    _Video("demo-cs05", "@demo.careerstackweekly", 560, "18:40", 640_000, "Big tech vs startups: an honest comparison",
           "Pay, pace, learning and stability, compared.",
           ("0:00 Intro", "2:30 Pay", "7:10 Pace", "11:45 Learning", "15:30 Stability")),
    _Video("demo-cs06", "@demo.careerstackweekly", 840, "11:55", 300_000, "Reacting to the worst tech resume advice",
           "Going through bad resume tips and what to do instead."),
)


def synthetic_youtube(loaded_at: datetime, now: datetime) -> FakeYouTube:
    """An in-memory YouTube serving the synthetic Corpus as it would look at `now`.

    Publish dates count back from `loaded_at`, so they stay put across refreshes.
    Only Videos published by `now` exist, and their views grow with age.
    """
    channels = {
        c.handle: ChannelDetails(
            channel_id=c.channel_id, title=c.title, uploads_playlist_id="UU" + c.channel_id[2:],
            view_count=c.view_count, subscriber_count=c.subscribers, video_count=c.video_count,
        )
        for c in _CHANNELS
    }
    videos = []
    for v in _VIDEOS:
        published_at = loaded_at - timedelta(days=v.days_old)
        if published_at > now:
            continue
        age_days = (now - published_at) / timedelta(days=1)
        views = round(v.eventual_views * age_days / (age_days + HALF_VIEWS_DAYS))
        videos.append(VideoDetails(
            video_id=v.video_id, channel_id=channels[v.handle].channel_id, published_at=published_at,
            title=v.title, description=_description(v), tags=("tech careers", "demo"), topic_categories=(),
            duration_seconds=_seconds(v.duration), audio_language="en", default_language="en",
            view_count=views, like_count=views // 25, comment_count=views // 250,
        ))
    return FakeYouTube(channels, videos)


def _description(video: _Video) -> str:
    parts = [video.summary]
    if video.chapters:
        parts.append("\n".join(video.chapters))
    parts.append("#techcareers #demo")
    return "\n\n".join(parts)


def _seconds(duration: str) -> int:
    seconds = 0
    for part in duration.split(":"):
        seconds = seconds * 60 + int(part)
    return seconds


def is_demo(conn: psycopg.Connection) -> bool:
    """Whether this database holds the synthetic demo Corpus (the app shows BANNER when it does)."""
    if conn.execute("SELECT to_regclass('demo_corpus')").fetchone()[0] is None:
        return False
    return conn.execute("SELECT exists(SELECT 1 FROM demo_corpus)").fetchone()[0]


def create_database(url: str) -> None:
    """Create the database `url` names, unless it already exists."""
    name = conninfo_to_dict(url)["dbname"]
    with psycopg.connect(make_conninfo(url, dbname="postgres"), autocommit=True) as admin:
        if not admin.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone():
            admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))


def load(conn: psycopg.Connection, niche: Niche, now: datetime) -> RefreshReport:
    """Replace everything in the database with the synthetic Corpus, marked as the demo.

    Migrates the emptied schema, then refreshes once per SNAPSHOT_DAYS_AGO so
    every Video has a short Snapshot history. Returns the last refresh's report.

    Raises ValueError, changing nothing, if the database has tables but isn't a
    demo database: it may hold real data.
    """
    has_tables = conn.execute("SELECT exists(SELECT 1 FROM pg_tables WHERE schemaname = 'public')").fetchone()[0]
    overwritable = not has_tables or is_demo(conn)
    conn.rollback()  # end the checks' implicit transaction, so each step below commits on its own
    if not overwritable:
        raise ValueError(f"{conn.info.dbname} isn't a demo database, so the demo won't overwrite it")
    with conn.transaction():
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
        conn.execute("DROP EXTENSION IF EXISTS vector")
    db.migrate(conn, db.MIGRATIONS_DIR)
    with conn.transaction():
        conn.execute("INSERT INTO demo_corpus (loaded_at) VALUES (%s)", (now,))
    for days_ago in SNAPSHOT_DAYS_AGO:
        taken_at = now - timedelta(days=days_ago)
        report = refresh_corpus(conn, synthetic_youtube(now, taken_at), niche, now=taken_at)
    return report


def refresh(conn: psycopg.Connection, niche: Niche, now: datetime) -> RefreshReport:
    """Refresh a demo database from the synthetic Corpus, as `collect.refresh` does from YouTube."""
    (loaded_at,) = conn.execute("SELECT loaded_at FROM demo_corpus").fetchone()
    return refresh_corpus(conn, synthetic_youtube(loaded_at, now), niche, now=now)
