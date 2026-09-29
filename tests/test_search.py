import random

import pytest
from rank_bm25 import BM25Okapi

from contention import db
from contention.search import UNWEIGHTED, Document, FieldWeights, KeywordIndex, search, tokenize

from corpus_rows import insert_channel, insert_video


def document(video_id, title="", chapters=(), tags=(), description=""):
    return Document(video_id=video_id, title=title, chapters=tuple(chapters), tags=tuple(tags),
                    description=description)


SAMPLE = [
    document("a", "How I got a software engineering job", ["Intro", "The resume", "The interview"],
             ["software engineer", "career"], "My story of landing a job after a bootcamp."),
    document("b", "Negotiate your salary", ["Intro", "Anchoring", "Counter offers"],
             ["salary", "negotiation", "career"], "How to negotiate salary at a tech company."),
    document("c", "Day in the life of a software engineer", [], ["day in the life", "software"],
             "A day at work: meetings, code review and lunch."),
    document("d", "Quitting my job", ["Intro", "Why I quit", "What next"], ["career"],
             "I quit my job at a big tech company. Here is why."),
    document("e", "Resume tips that got me interviews", [], ["resume", "career", "job"],
             "Resume resume resume: the one page resume that works."),
    document("f", "Is a bootcamp worth it?", ["Intro", "Cost", "Outcomes"], ["bootcamp"], ""),
]


def reference_scores(documents, query):
    """rank_bm25's Okapi scores over each Document's fields run together."""
    reference = BM25Okapi([tokenize(" ".join([d.title, *d.chapters, *d.tags, d.description])) for d in documents])
    return dict(zip([d.video_id for d in documents], reference.get_scores(tokenize(query))))


@pytest.mark.parametrize("query", [
    "software engineer job", "resume", "career", "intro", "salary negotiation tech", "job job", "unknown words",
])
def test_unweighted_scores_match_rank_bm25(query):
    index = KeywordIndex(SAMPLE, UNWEIGHTED)

    scores = index.scores(query)

    assert scores == pytest.approx(reference_scores(SAMPLE, query))


def test_unweighted_scores_match_rank_bm25_on_a_random_sample():
    rng = random.Random(30)
    vocabulary = [f"w{n}" for n in range(60)]

    def words(most):
        return " ".join(rng.choices(vocabulary, weights=range(60, 0, -1), k=rng.randint(0, most)))

    documents = [document(str(n), words(8), [words(4) for _ in range(rng.randint(0, 3))],
                          [words(2) for _ in range(rng.randint(0, 4))], words(40)) for n in range(200)]
    index = KeywordIndex(documents, UNWEIGHTED)

    for _ in range(20):
        query = words(5)
        assert index.scores(query) == pytest.approx(reference_scores(documents, query))


def test_tokenize_lowercases_and_splits_on_non_word_characters():
    assert tokenize("Day-in-the-Life: SWE @ Google, 2026!") == ["day", "in", "the", "life", "swe", "google", "2026"]


# Okapi idf is 0 for a term in exactly half the Videos, so ranking tests pad the query term's rarity.
FILLER = [document(f"filler-{n}", "Unrelated video", description="Nothing to see") for n in range(6)]


def test_a_match_in_the_title_outranks_the_same_match_in_the_description():
    documents = [
        document("in-description", "My week", description="Thoughts on salary"),
        document("in-title", "Thoughts on salary", description="My week"),
        *FILLER,
    ]

    ranked = KeywordIndex(documents).search("salary")

    assert [result.video_id for result in ranked] == ["in-title", "in-description"]


def test_field_weights_change_the_ranking():
    documents = [
        document("in-title", "Salary talk", description="A chat"),
        document("in-description", "A chat", description="Salary talk"),
        *FILLER,
    ]
    description_first = FieldWeights(title=1, chapters=1, tags=1, description=5)

    ranked = KeywordIndex(documents, description_first).search("salary")

    assert [result.video_id for result in ranked] == ["in-description", "in-title"]


def test_a_term_in_most_videos_still_counts_a_little():
    documents = [document(f"career-{n}", f"Career story number{n}") for n in range(5)] + FILLER[:2]
    index = KeywordIndex(documents)

    common, rare = index.scores("career")["career-0"], index.scores("number0")["career-0"]

    assert 0 < common < rare


def test_search_returns_at_most_limit_results_best_first():
    ranked = KeywordIndex(SAMPLE).search("resume job career", limit=3)

    assert len(ranked) == 3
    assert [result.score for result in ranked] == sorted((result.score for result in ranked), reverse=True)
    assert ranked[0].video_id == "e"


def test_an_empty_index_finds_nothing():
    assert KeywordIndex([]).search("anything") == []


def insert_filler(conn, count=6):
    for n in range(count):
        insert_video(conn, f"filler-{n}", title="Unrelated video")


def test_search_applies_the_hard_filters(conn):
    db.migrate(conn, db.MIGRATIONS_DIR)
    insert_channel(conn, "UC1", "tech-careers")
    insert_channel(conn, "UC2", "cooking")
    insert_video(conn, "kept")
    insert_video(conn, "other-niche", channel_id="UC2")
    insert_video(conn, "short", duration_seconds=60)
    insert_video(conn, "held-out", is_held_out=True)
    insert_filler(conn)

    results = search(conn, "tech-careers", "salary")

    assert [result.video_id for result in results] == ["kept"]
    assert results[0].title == "Salary advice"
    assert results[0].channel_title == "Channel UC1"


def test_search_reads_chapters_tags_and_the_cleaned_description(conn):
    db.migrate(conn, db.MIGRATIONS_DIR)
    insert_channel(conn, "UC1", "tech-careers")
    insert_video(conn, "by-chapter", title="Video one", chapters=["Intro", "Negotiation", "Outro"])
    insert_video(conn, "by-tag", title="Video two", tags=["negotiation"])
    insert_video(conn, "by-description", title="Video three", cleaned_description="All about negotiation")
    insert_filler(conn, count=10)

    results = search(conn, "tech-careers", "negotiation")

    assert {result.video_id for result in results} == {"by-chapter", "by-tag", "by-description"}

