"""Pure text handling for Video metadata: durations, Chapters and description cleaning."""

import re
from dataclasses import dataclass

_DURATION = re.compile(r"^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?$")


def parse_duration(iso: str) -> int:
    """Seconds in a YouTube ISO 8601 duration such as `PT1H2M3S`."""
    match = _DURATION.match(iso)
    if not match:
        raise ValueError(f"not a YouTube duration: {iso!r}")
    days, hours, minutes, seconds = (int(part or 0) for part in match.groups())
    return ((days * 24 + hours) * 60 + minutes) * 60 + seconds


@dataclass(frozen=True)
class Chapter:
    start_seconds: int
    title: str


_TIMESTAMP = r"(?:(\d{1,2}):)?(\d{1,2}):(\d{2})"
_LEADING = re.compile(rf"^\s*{_TIMESTAMP}\s*[-–—:|]?\s*(.+?)\s*$")
_TRAILING = re.compile(rf"^\s*(.+?)\s*[-–—:|]?\s*{_TIMESTAMP}\s*$")


def _seconds(hours: str | None, minutes: str, seconds: str) -> int:
    return (int(hours or 0) * 60 + int(minutes)) * 60 + int(seconds)


def parse_chapters(description: str) -> list[Chapter]:
    """Chapters listed in a description, one timestamped line each.

    Follows YouTube's rules: the first Chapter starts at 0:00, there are at least
    three, and they're in ascending order. Otherwise there are no Chapters.
    """
    chapters = []
    for line in description.splitlines():
        if match := _LEADING.match(line):
            hours, minutes, seconds, title = match.groups()
        elif match := _TRAILING.match(line):
            title, hours, minutes, seconds = match.groups()
        else:
            continue
        chapters.append(Chapter(_seconds(hours, minutes, seconds), title))

    starts = [chapter.start_seconds for chapter in chapters]
    valid = len(chapters) >= 3 and starts[0] == 0 and starts == sorted(set(starts))
    return chapters if valid else []


_URL = re.compile(r"\S*https?://\S+|\bwww\.\S+")
_HASHTAG = re.compile(r"#\w+")
_PROMOTIONAL = re.compile(
    r"sponsor|use code|promo code|discount|% off|affiliate|patreon|merch"
    r"|follow me|subscribe|instagram|twitter|tiktok|linkedin|discord|newsletter"
    r"|join (?:our|my)|(?:your|our|my) community|private group|check out|my course",
    re.IGNORECASE,
)
_LINK_LABEL_MAX_WORDS = 6  # a line that only labels a link, like "My gear:"


def clean_description(description: str) -> str:
    """The description without links, hashtags, or sponsor and "follow me" lines.

    What's left is the creator's own words about the Video, for search and embeddings.
    """
    kept = []
    for line in description.splitlines():
        if _PROMOTIONAL.search(line):
            continue
        without_links = _URL.sub("", line)
        had_link = without_links != line
        line = " ".join(_HASHTAG.sub("", without_links).split())
        if had_link and (line.endswith((":", "-", "–")) or len(line.split()) <= _LINK_LABEL_MAX_WORDS):
            continue
        if line:
            kept.append(line)
    return "\n".join(kept)
