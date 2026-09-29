"""Compare Okapi and Lucene idf on a synthetic Corpus, for docs/guides/keyword-search.md.

Run with `uv run python docs/guides/idf_comparison.py`. Everything here is made up:
a Zipf-distributed vocabulary stands in for Video text, so no YouTube data is used.
"""

import math
import random
from collections import Counter

from contention.search import UNWEIGHTED, Document, KeywordIndex, lucene_idf, okapi_idf

VIDEOS = 20_000  # about the size of a real Corpus
VOCABULARY = [f"w{rank}" for rank in range(1, 40_001)]
ZIPF = [1 / rank**1.07 for rank in range(1, 40_001)]  # word frequency falls with rank, as in real text


def synthetic_document_frequencies(rng: random.Random) -> Counter[str]:
    """How many of VIDEOS synthetic Videos (60-200 words each) contain each word."""
    frequencies: Counter[str] = Counter()
    for _ in range(VIDEOS):
        frequencies.update(set(rng.choices(VOCABULARY, weights=ZIPF, k=rng.randint(60, 200))))
    return frequencies


def idf_table(frequencies: Counter[str]) -> None:
    raw = [math.log(VIDEOS - n + 0.5) - math.log(n + 0.5) for n in frequencies.values()]
    print(f"{len(frequencies):,} distinct words; mean raw Okapi idf {sum(raw) / len(raw):.2f}, "
          f"so the floor is {0.25 * sum(raw) / len(raw):.2f}\n")
    print("share of Videos | Okapi idf | Lucene idf")
    for share in (0.001, 0.01, 0.10, 0.30, 0.45, 0.49, 0.50, 0.51, 0.80, 0.95):
        probe = Counter(frequencies)
        probe["probe"] = round(VIDEOS * share)
        print(f"{share:>15.1%} | {okapi_idf(probe, VIDEOS)['probe']:9.3f} | {lucene_idf(probe, VIDEOS)['probe']:10.3f}")


def ranking_inversion() -> None:
    """Two one-word matches: 'career' is in 51 of 100 Videos, 'interview' in 49."""
    documents = [
        Document(f"v{n}", " ".join(["career"] * (n < 51) + ["interview"] * (n >= 51) + [f"unique{n}"] * 3), (), (), "")
        for n in range(100)
    ]
    print("\nquery 'career interview': score of a Video matching only one word")
    for name, idf in (("Okapi", okapi_idf), ("Lucene", lucene_idf)):
        scores = KeywordIndex(documents, UNWEIGHTED, idf=idf).scores("career interview")
        print(f"{name:>6}: only 'career' (51%) {scores['v0']:.3f}, only 'interview' (49%) {scores['v99']:.3f}")


if __name__ == "__main__":
    idf_table(synthetic_document_frequencies(random.Random(7)))
    ranking_inversion()
