import pytest

from contention.text import Chapter, clean_description, parse_chapters, parse_duration


@pytest.mark.parametrize("iso, seconds", [
    ("PT45S", 45),
    ("PT12M3S", 723),
    ("PT1H2M3S", 3723),
    ("PT2H", 7200),
    ("P1DT1S", 86401),
])
def test_parses_youtube_durations(iso, seconds):
    assert parse_duration(iso) == seconds


DESCRIPTION = """In this video I talk about my first year as a software engineer.

0:00 Intro
1:15 - My biggest mistake
04:30 How I recovered
1:02:03 Q&A
Promotion story 1:10:00

Follow me on Twitter: https://twitter.com/example
"""


def test_parses_chapters_from_a_description():
    assert parse_chapters(DESCRIPTION) == [
        Chapter(0, "Intro"),
        Chapter(75, "My biggest mistake"),
        Chapter(270, "How I recovered"),
        Chapter(3723, "Q&A"),
        Chapter(4200, "Promotion story"),
    ]


@pytest.mark.parametrize("description", [
    "0:00 Intro\n1:00 Middle\n",                 # fewer than 3 timestamps
    "0:30 Intro\n1:00 Middle\n2:00 End\n",       # doesn't start at 0:00
    "0:00 Intro\n2:00 Middle\n1:00 End\n",       # not ascending
    "No timestamps here at all.",
])
def test_ignores_timestamps_that_are_not_valid_chapters(description):
    assert parse_chapters(description) == []


def test_cleans_links_hashtags_and_promotional_lines_from_a_description():
    description = """How I negotiated a 30% raise as a junior developer.
Read the full guide at https://example.com/guide before your review.

This video is sponsored by Acme. Use code JARROD for 20% off!
Follow me on Instagram: @example
Subscribe for more career videos
My affiliate links: https://amzn.to/xyz

#softwareengineer #careeradvice #tech
"""

    assert clean_description(description) == (
        "How I negotiated a 30% raise as a junior developer.\n"
        "Read the full guide at before your review."
    )


def test_drops_link_labels_and_community_promotion():
    description = """First impressions on the new phone.
Apple Photos to Lightroom converter: https://example.com/converter
Read my notes on the launch at https://example.com/notes before watching.
🌊 Join our private group
Your Community for Crypto, Stocks, DeFi & Tech. Get the inside track on trading.
Check out my course on system design
"""

    assert clean_description(description) == (
        "First impressions on the new phone.\n"
        "Read my notes on the launch at before watching."
    )
