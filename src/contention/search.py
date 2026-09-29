"""Keyword search: a hand-written BM25 over a Video's weighted text fields (ADR 0005)."""

import math
import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass

import psycopg

from contention.collect import SHORTS_MAX_SECONDS

_WORD = re.compile(r"\w+")


def tokenize(text: str) -> list[str]:
    """Lowercased runs of letters, digits and underscores."""
    return _WORD.findall(text.lower())


@dataclass(frozen=True)
class FieldWeights:
    """How much one occurrence of a term counts in each field. Tuned by the retrieval eval."""

    title: float = 3.0
    chapters: float = 2.0
    tags: float = 2.0
    description: float = 1.0


UNWEIGHTED = FieldWeights(title=1, chapters=1, tags=1, description=1)


@dataclass(frozen=True)
class Document:
    """The searchable text of one Video: its title, Chapter titles, tags and cleaned description."""

    video_id: str
    title: str
    chapters: tuple[str, ...]
    tags: tuple[str, ...]
    description: str

    def field_tokens(self) -> dict[str, list[str]]:
        return {
            "title": tokenize(self.title),
            "chapters": tokenize(" ".join(self.chapters)),
            "tags": tokenize(" ".join(self.tags)),
            "description": tokenize(self.description),
        }


@dataclass(frozen=True)
class Match:
    """A Video the index ranked for a query, with its BM25 score."""

    video_id: str
    score: float


class KeywordIndex:
    """Okapi BM25 over weighted fields, held in memory.

    Each field's term counts and length are multiplied by its weight and summed,
    so a title word counts like several description words (a simple BM25F with
    one length normalisation). With every weight at 1 this is plain BM25 over the
    fields run together. `idf` defaults to `lucene_idf`; with `okapi_idf` and every
    weight at 1, scores equal `rank_bm25.BM25Okapi`'s (the ADR 0005 cross-check).
    """

    def __init__(
        self,
        documents: list[Document],
        weights: FieldWeights = FieldWeights(),
        k1: float = 1.5,
        b: float = 0.75,
        idf: Callable[[Counter[str], int], dict[str, float]] | None = None,
    ):
        self.k1 = k1
        self.b = b
        self.video_ids = [document.video_id for document in documents]
        self.term_counts: list[Counter[str]] = []
        self.lengths: list[float] = []
        document_frequencies: Counter[str] = Counter()
        for document in documents:
            counts: Counter[str] = Counter()
            length = 0.0
            for name, tokens in document.field_tokens().items():
                weight = getattr(weights, name)
                if not weight:  # a field switched off shouldn't count towards document frequency either
                    continue
                for term, count in Counter(tokens).items():
                    counts[term] += weight * count
                length += weight * len(tokens)
            self.term_counts.append(counts)
            self.lengths.append(length)
            document_frequencies.update(counts.keys())
        self.average_length = sum(self.lengths) / len(documents) if documents else 0.0
        self.idf = (idf or lucene_idf)(document_frequencies, len(documents))

    def scores(self, query: str) -> dict[str, float]:
        """Every indexed Video's score for the query; 0 for Videos sharing no term with it."""
        terms = tokenize(query)
        scores = {}
        for video_id, counts, length in zip(self.video_ids, self.term_counts, self.lengths):
            score = 0.0
            if self.average_length:
                norm = self.k1 * (1 - self.b + self.b * length / self.average_length)
                for term in terms:  # a repeated query term counts again, as in rank_bm25
                    if count := counts.get(term):
                        score += self.idf[term] * count * (self.k1 + 1) / (count + norm)
            scores[video_id] = score
        return scores

    def search(self, query: str, limit: int = 10) -> list[Match]:
        """The best `limit` Videos with a positive score, best first (ties by id)."""
        ranked = sorted(self.scores(query).items(), key=lambda item: (-item[1], item[0]))
        return [Match(video_id, score) for video_id, score in ranked[:limit] if score > 0]


def lucene_idf(document_frequencies: Counter[str], size: int) -> dict[str, float]:
    """Each term's idf, always positive and falling as more Videos contain the term."""
    return {
        term: math.log(1 + (size - frequency + 0.5) / (frequency + 0.5))
        for term, frequency in document_frequencies.items()
    }


def okapi_idf(document_frequencies: Counter[str], size: int, epsilon: float = 0.25) -> dict[str, float]:
    """Each term's idf as `rank_bm25.BM25Okapi` computes it, for the cross-check.

    A term in more than half the Videos would get a negative idf, so it gets
    `epsilon` times the average idf instead. That floor isn't monotonic (a term in
    51% of Videos can outscore one in 49%), which is why it isn't the default.
    """
    idf = {
        term: math.log(size - frequency + 0.5) - math.log(frequency + 0.5)
        for term, frequency in document_frequencies.items()
    }
    if idf:
        floor = epsilon * sum(idf.values()) / len(idf)
        idf = {term: value if value >= 0 else floor for term, value in idf.items()}
    return idf


@dataclass(frozen=True)
class SearchResult:
    """A ranked Video as `search` shows it: a Match plus its title and Channel title."""

    video_id: str
    title: str
    channel_title: str
    score: float


def load_documents(conn: psycopg.Connection, niche: str) -> tuple[list[Document], dict[str, tuple[str, str]]]:
    """The searchable Videos of a Niche, and each one's title and Channel title by id.

    Applies retrieval's hard filters: the Niche's Channels, long-form only, and
    never a held-out test Video.
    """
    rows = conn.execute(
        """
        SELECT v.video_id, v.title, c.title, v.tags, v.cleaned_description,
               coalesce(array_agg(ch.title ORDER BY ch.position) FILTER (WHERE ch.title IS NOT NULL), '{}')
        FROM videos v
        JOIN niche_channels n ON n.channel_id = v.channel_id AND n.niche = %s
        JOIN channels c ON c.channel_id = v.channel_id
        LEFT JOIN chapters ch ON ch.video_id = v.video_id
        WHERE v.duration_seconds > %s AND NOT v.is_held_out
        GROUP BY v.video_id, c.title
        ORDER BY v.video_id
        """,
        (niche, SHORTS_MAX_SECONDS),
    ).fetchall()
    documents = [Document(video_id, title, tuple(chapters), tuple(tags), description)
                 for video_id, title, _, tags, description, chapters in rows]
    titles = {video_id: (title, channel_title) for video_id, title, channel_title, *_ in rows}
    return documents, titles


def search(
    conn: psycopg.Connection, niche: str, query: str, weights: FieldWeights = FieldWeights(), limit: int = 10
) -> list[SearchResult]:
    """Keyword search over a Niche's searchable Videos, best first."""
    documents, titles = load_documents(conn, niche)
    return [SearchResult(match.video_id, *titles[match.video_id], match.score)
            for match in KeywordIndex(documents, weights).search(query, limit)]
