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
_HANDLE = re.compile(r"(?<!\w)@\w+")
# Promotional phrasing, not topic words: "sponsorship" or "LinkedIn" can be what a Video is about.
_PROMOTIONAL = re.compile(
    r"sponsored by|this video'?s sponsor|for sponsoring|business inquiries|use code|promo code|% off"
    r"|affiliate|patreon|my merch|follow (?:me|us)|connect with (?:me|us)|subscribe (?:for|to)|and subscribe"
    r"|join (?:our|my)|(?:your|our|my) community|private group|check out my|my course|my newsletter",
    re.IGNORECASE,
)
_PLATFORM = re.compile(r"instagram|twitter|tiktok|linkedin|discord|threads|facebook", re.IGNORECASE)
_EMAIL = re.compile(r"\S+@\S+\.\w+")
_LINK_LABEL_MAX_WORDS = 6  # a line that only labels a link, like "My gear:"


def _is_chapter_line(line: str) -> bool:
    return bool(_LEADING.match(line) or _TRAILING.match(line))


def _is_promotional(line: str) -> bool:
    if _PROMOTIONAL.search(line) or _EMAIL.search(line):
        return True
    # A platform name is promotion only when it points somewhere: "Twitter: @me", not "my LinkedIn headline".
    return bool(_PLATFORM.search(line) and (_HANDLE.search(line) or _URL.search(line)))


def clean_description(description: str) -> str:
    """The description without links, hashtags, promotion or Chapter lines.

    What's left is the Channel's own words about the Video, for search and
    embeddings. Chapters are kept separately, so their lines are dropped here.
    """
    has_chapters = bool(parse_chapters(description))
    kept = []
    for line in description.splitlines():
        if _is_promotional(line) or (has_chapters and _is_chapter_line(line)):
            continue
        without_links = _URL.sub("", line)
        had_link = without_links != line
        line = " ".join(_HASHTAG.sub("", without_links).split())
        # A line ending in ":" heads a list of links; a short line that had a link just labels it.
        if line.endswith(":") or (had_link and (line.endswith(("-", "–")) or len(line.split()) <= _LINK_LABEL_MAX_WORDS)):
            continue
        if any(char.isalnum() for char in line):  # skip decorative lines like "━━━━"
            kept.append(line)
    return "\n".join(kept)
