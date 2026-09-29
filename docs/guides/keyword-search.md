# Keyword search: how the BM25 works and why it's built this way

A guide to `src/contention/search.py`: what the index computes, why its idf is Lucene's rather than Okapi's, how the retrieval eval will test that choice, and what to watch for when you write a scorer like this yourself. Decisions it rests on: [ADR 0005](../adr/0005-postgres-store-retrieval-in-python.md) and spec §5.

All numbers here come from [`idf_comparison.py`](idf_comparison.py), which runs the real `search.py` functions on a synthetic Corpus. Re-run it with `uv run python docs/guides/idf_comparison.py`. Nothing here is measured on YouTube data, and nothing should be: published material may only describe the system (#54).

## 1. Keyword search is a sparse vectorization

It helps to see BM25 as the same kind of thing as the embedding search coming later: both turn a Video into a vector and score a query by a dot product.

- **Dense (embeddings):** a Video becomes ~384–768 numbers, none of which means anything alone. Similar meaning gives nearby vectors, even with no words in common ("pay rise" ≈ "salary negotiation").
- **Sparse (BM25):** a Video becomes one number per word in the vocabulary (~40,000 of them), almost all zero. The number for word *t* in Video *d* is its BM25 weight:

  ```
  w(t, d) = idf(t) · tf(t, d) · (k1 + 1) / (tf(t, d) + k1 · (1 − b + b · len(d) / avglen))
  ```

  A query is a vector of 1s (one per query word, counted again if repeated), and the score is the dot product: the sum of `w(t, d)` over the query's words.

The two fail in opposite ways, which is why spec §5 fuses them. Sparse vectors can't match synonyms. Dense vectors blur exact terms: a query for "LeetCode 75" or "L5 promotion" needs the literal tokens. Keyword search is the half of hybrid retrieval that's good at exact terms, and that should guide every choice below.

The formula has three parts, and each is a decision:

| Part | What it does | Our setting |
|---|---|---|
| `idf(t)` | Rare words count more than common ones | Lucene's formula (section 2) |
| `tf · (k1+1) / (tf + k1·…)` | Repeats help, with diminishing returns (saturation) | `k1 = 1.5` |
| `1 − b + b · len/avglen` | Long Videos don't win just by having more words | `b = 0.75` |

### Saturation, and what field weights really do

With `k1 = 1.5`, at average length, the term-frequency part gives:

| Occurrences | 1 | 2 | 3 | 6 | ∞ |
|---|---|---|---|---|---|
| Weight | 1.00 | 1.43 | 1.67 | 2.00 | 2.50 |

**Field weights are applied before saturation.** A title word with weight 3 counts as 3 occurrences, so it scores 1.67× a description word, not 3×. This is the BM25F idea: combine the fields first, then saturate once, so a word repeated in the title, the tags and the description can't add up to three full scores. The weights also add to the Video's length (a 10-word title counts as 30 words), so long titles are penalised like long descriptions.

Our version is a simplified BM25F with one `b` for all fields. Full BM25F normalises each field against its own average length, since titles and descriptions have very different typical lengths. That's a sensible experiment once the eval exists.

## 2. The idf decision: Okapi or Lucene

### The two formulas

With `N` Videos, of which `n` contain the word:

```
Okapi  (rank_bm25):  idf = log((N − n + 0.5) / (n + 0.5))
Lucene (default):    idf = log(1 + (N − n + 0.5) / (n + 0.5))
```

Okapi's formula comes from the Robertson–Spärck Jones probabilistic model. It is **negative when a word is in more than half the Videos**: in that model, a match on such a word is weak evidence *against* relevance. A negative weight means that matching a query word lowers the score, which no user expects. So `rank_bm25` replaces every negative idf with a floor of `0.25 × the mean idf of the whole vocabulary`.

Lucene (and so Elasticsearch and OpenSearch) adds 1 inside the log. The result is always positive, and always falls as `n` grows.

### What the floor does on a Corpus our size

From `idf_comparison.py`: 20,000 synthetic Videos with a Zipf-distributed vocabulary (the usual shape of real text).

| Share of Videos containing the word | Okapi idf | Lucene idf |
|---|---|---|
| 0.1% | 6.88 | 6.88 |
| 1% | 4.59 | 4.60 |
| 10% | 2.20 | 2.30 |
| 30% | 0.85 | 1.20 |
| 49% | 0.04 | 0.71 |
| 50% | **0.00** | 0.69 |
| 51% | **1.87** | 0.67 |
| 95% | **1.87** | 0.05 |

For rare words the two agree, and most query words are rare. They differ sharply for common words:

1. **Okapi jumps at 50%.** A word in 49% of Videos is worth 0.04, and a word in 51% is worth 1.87, about 47× more. The floor is big because the vocabulary's mean idf (7.47) is dominated by the long tail of rare words.
2. **Near-universal words beat moderately common ones.** Under Okapi, a word in 95% of Videos (in practice "the", "and", "to", since we don't remove stopwords) outweighs a word in 30%. Every query containing "the" gives most of the Corpus a spurious bonus.
3. **Exactly-half words disappear.** At `n = N/2` the Okapi idf is 0, so matching the word adds nothing.

The same flip changes rankings. In a 100-Video example where "career" is in 51 Videos and "interview" in 49, the query "career interview" scores:

| | Video matching only "career" (51%) | Video matching only "interview" (49%) |
|---|---|---|
| Okapi | 1.028 | 0.040 |
| Lucene | 0.674 | 0.713 |

Okapi ranks the more common word 25× higher. Lucene ranks the rarer word slightly higher, as idf intends.

### Why this matters more for our Corpus than for a general one

- **A Niche Corpus concentrates its vocabulary.** Every Video in "tech careers" is about careers, jobs and software, so those content words sit at 30–70% of Videos. That band is where the two formulas disagree, and these are words users type.
- **The floor moves when unrelated text changes.** It depends on the mean idf over the whole vocabulary. A weekly refresh that brings in Videos with lots of rare tokens (names, typos, version numbers) raises the mean, and so shifts the weight of "career" without any change in how many Videos contain it. Rankings shouldn't depend on that. Lucene's idf depends only on `n` and `N`.
- **Short queries magnify idf.** Strategist-style queries are a few words long, so one miscounted common word swings the whole ranking.
- **Keyword search is there for exact, rare terms** (section 1). Both formulas agree on rare terms. Where they differ, Lucene's behaviour (common words count a little, never more than rarer ones) is the safe choice.

What Lucene gives up: a word in almost every Video still counts a tiny bit (0.05 at 95%), where the probabilistic model says it should count against a Video. In practice the effect is negligible, and it treats every Video equally.

### Why `rank_bm25` stays in the tests

ADR 0005 asks for a cross-check against `rank_bm25`, to prove the hand-written formula is right. That's why `okapi_idf` still exists. The parity tests build the index with `idf=okapi_idf` and every weight at 1, and must equal `rank_bm25.BM25Okapi` to floating-point tolerance. The cross-check validates the machinery (term frequencies, length normalisation, saturation) and swaps out only the idf. Copying a reference implementation to check your code doesn't commit you to its design choices.

## 3. How the retrieval eval should decide it

The choice above rests on the properties of the formulas, not on a measurement. The retrieval eval (#32) is where to confirm it. Spec §10 defines the eval: about 40 queries, results graded 0/1/2 (not relevant / relevant / highly relevant), scored with nDCG@10 and Recall@50.

### The metrics

- **nDCG@10** (normalised discounted cumulative gain). It asks: are the best Videos at the top of the first 10?

  ```
  DCG@10  = Σ_{i=1..10} (2^grade_i − 1) / log2(i + 1)
  nDCG@10 = DCG@10 / DCG@10 of the ideal ordering
  ```

  A grade-2 Video at rank 1 is worth 3; the same Video at rank 10 is worth 3 / log2(11) ≈ 0.87. It rewards putting the strongest Evidence first, which is what the Strategist and Optimiser show.
- **Recall@50.** Of all Videos graded relevant for the query, what share appear in the top 50? In a hybrid system, keyword search is a *candidate generator*: fusion and the optional reranker only reorder what's in the top ~50. A relevant Video that keyword search ranks 200th is lost for good. For choosing the idf, Recall@50 matters at least as much as nDCG@10.
- **MRR** (mean reciprocal rank of the first relevant Video) isn't in the spec. It's a useful extra check when a query has one obvious right answer.

### Running the comparison fairly

1. **Pool both variants.** Judgments are pooled: only Videos that some variant retrieved get graded. If Okapi's results aren't in the pool, the Videos only Okapi finds count as non-relevant, and Lucene wins by construction. Put both runs in the pool.
2. **Compare per query, not just the averages.** With 40 queries, a 0.01 difference in mean nDCG@10 is likely noise. Count the queries each variant wins, and bootstrap a confidence interval: resample the 40 queries with replacement 10,000 times and look at the spread of the difference.
3. **Look at the queries where they disagree.** The formulas differ by more than a few percent only for words in more than ~10% of Videos. Split the queries into "has a common word" and "only rare words". Expect near-identical scores on the second group; any real difference should show up in the first.
4. **Check whether the rankings differ at all.** Rank correlation (Kendall's τ) or top-50 overlap between the two variants per query shows whether the choice matters for this Corpus. If the top 50 barely changes, the decision is low-stakes and the simpler, more stable formula wins.
5. **Tune one thing at a time.** Field weights, `k1`, `b` and idf interact (a bigger title weight saturates sooner). Fix idf first, then tune weights on nDCG@10. Keep a few queries aside so you aren't tuning to the same 40 you report.

**The prediction to test:** Lucene should beat or tie Okapi on Recall@50 and nDCG@10, with the gain concentrated in queries containing common Niche words ("career", "job", "engineer") or stopwords.

## 4. When you write your own scorer: what to watch for

These are the places this implementation had to make a call, in the order you'll hit them.

**Tokenization decides what can match.** `tokenize` lowercases and keeps runs of letters, digits and underscores.
- "C++" becomes `c` and "C#" becomes `c`, so they can't be told apart. "Node.js" becomes `node`, `js`.
- There's no stemming: "negotiate" doesn't match "negotiation". Adding a stemmer raises recall and blurs exact terms.
- There's no stopword list. Lucene idf makes stopwords nearly harmless (0.05 at 95%), so you don't need one to fix scoring, but one would shrink the index.
- Whatever you choose, the query and the Videos must go through the **same** tokenizer.

**Define document frequency precisely.** `n` counts the Videos that contain the word *in any field with a non-zero weight*.
- A field weighted 0 must drop out completely: that was a real bug caught in review, and the test `test_a_field_weighted_zero_is_left_out_entirely` now covers it.
- Compute `n` **after** the hard filters. Held-out test Videos and other Niches aren't in the index, so they don't change idf. Otherwise the eval would leak information from the held-out set.

**Guard the edge cases.**
- An empty Corpus (average length 0): the code checks for it before dividing.
- A word no Video contains: it has no idf entry and contributes nothing.
- Repeated query words: they count again, as in `rank_bm25`.
- Ties: broken by `video_id`, so results are deterministic.
- Negative scores: impossible with Lucene idf. With Okapi on a tiny Corpus the floor itself can go negative, which is one more reason Okapi isn't the default.

**Test the properties, not just examples.** Beyond "these five Videos rank in this order", test things that must always hold:
- idf is positive and strictly falls as `n` grows (`test_idf_is_positive_and_falls_as_more_videos_contain_the_term`);
- a title match outranks the same match in the description;
- scores match a reference implementation within `pytest.approx`.

To check a test has teeth, break the code on purpose and watch it fail. Changing `k1` from 1.5 to 1.2 failed six parity tests, and the first zero-weight test passed even without the fix, so it was rewritten.

**Know your reference's quirks.** `rank_bm25`'s Okapi floor, its `epsilon = 0.25` and its tokenization-free input are its choices, not BM25's. Match them when checking parity, and choose deliberately when setting defaults.

**Scale is a design input.** `KeywordIndex.scores` loops over every Video for every query: O(Videos × query words). At ~20–30k Videos that takes milliseconds, and it keeps the code readable. An inverted index (word → list of Videos containing it) is the standard fix if the Corpus grows, and it only visits Videos that share a query word. Per the spec, the index lives in memory and is rebuilt on refresh, never saved to disk.

**Keep it explainable.** BM25's advantage over embeddings is that you can say exactly why a Video scored what it did: which words matched, in which fields, with what idf. When a ranking looks wrong, print the per-word contributions before changing parameters.

## Further reading

- Robertson & Zaragoza, *The Probabilistic Relevance Framework: BM25 and Beyond* (2009): where BM25, the Okapi idf and BM25F come from.
- The Lucene `BM25Similarity` documentation: the `log(1 + …)` idf.
- Järvelin & Kekäläinen, *Cumulated gain-based evaluation of IR techniques* (2002): nDCG.
