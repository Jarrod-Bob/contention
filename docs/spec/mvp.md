# contention MVP spec

A single-user, local tool over a public YouTube **Corpus** (one **Niche**, long-form only) with two features: a **Content Strategist** ("what should I create?") and a **Content Optimiser** ("how should I improve this **Draft**, and how might it do?"). Both are text-only, cite **Evidence**, and the Optimiser predicts one public metric.

This spec is the destination of the map [Map: contention MVP spec](https://github.com/Jarrod-Bob/contention/issues/6). It states *what* is built. The *why* lives in the linked tickets and ADRs; don't re-argue decisions here, change them there. Terms in **bold** are defined in [`CONTEXT.md`](../../CONTEXT.md).

## 1. Goals and constraints

- **Learning-first.** Each technique (LLM reasoning, hybrid RAG, classic ML, clustering) is built honestly, not delegated to a framework that hides it.
- **Single user, local.** No auth, no deployment, no multi-user concerns.
- **Python.**
- **Within YouTube's terms.** Public data only, via the YouTube Data API. No transcripts, no scraping. Public data and everything derived from it is refreshed or deleted within 30 days. No derived metric is ever presented as a YouTube statistic. See [ADR 0003](../adr/0003-predict-raw-log-views.md) and [ADR 0004](../adr/0004-corpus-has-no-transcripts.md).
- **Low running cost.** Free and local models wherever privacy and consistency allow; Claude where quality or privacy require it.

### Out of scope

Multimodal understanding, the publish-measure-retrain feedback loop, Shorts, private creator analytics, other platforms, several Niches side by side, iterating over Draft versions, transcripts of the user's own Videos, a Docker setup, and slicing this spec into build issues (the next effort). Each is recorded on the map.

## 2. Architecture

A **core Python package** holds all logic. Two thin interfaces call it; the eval harness calls the same functions.

| Part | Technology |
| --- | --- |
| Store | Postgres + pgvector, installed with Homebrew; plain SQL through `psycopg`; numbered `.sql` migrations |
| Collection | YouTube Data API (API key) |
| Embeddings | local sentence-transformers (one model for all Niches) |
| Keyword search | hand-written BM25 |
| Vector search | exact cosine similarity in numpy |
| Orchestration | LangChain (models and chaining only, no framework retrievers) |
| Predictor | LightGBM + CQR, Ridge baseline, TreeSHAP |
| Clustering | HDBSCAN (or similar) for Themes and Audience groups |
| UI | Streamlit (local) |
| Operations | Typer CLI, weekly `launchd` job |

Decisions: [ADR 0002](../adr/0002-langchain-orchestration-hand-built-retrieval.md), [ADR 0005](../adr/0005-postgres-store-retrieval-in-python.md), [Interface for the Strategist and Optimiser](https://github.com/Jarrod-Bob/contention/issues/23).

### Model roles

| Job | Model | Why this one |
| --- | --- | --- |
| Strategist and Optimiser answers (real use) | Claude Opus 5.5 (`claude-opus-5-5`) via LangChain | Quality; real Drafts only go to Claude |
| Strategist and Optimiser answers (while building) | free OpenRouter models, with sample Drafts only | Free |
| Strategist and Optimiser answers (evals) | Claude Opus 5.5 via the Message Batches API, same prompt, model and effort as the LangChain path | 50% cheaper |
| Audience and Format labels (Corpus and Drafts) | one local model through Ollama, same prompt for both; Claude Haiku 4.5 fallback if Format accuracy < 80% | Free, private, consistent |
| Theme and Audience group labels | the same local model | Free, consistent |
| Eval judge (grounding) | a free OpenRouter model if it passes calibration, else Claude Haiku 4.5 | All eval content is public |
| Retrieval relevance pre-grading | a free OpenRouter model, confirmed by the user | Public data |

Opus 5.5 notes for builders: thinking can't be disabled, so set `effort` explicitly (default `medium`); forced tool choice returns a 400, so structured output must not rely on LangChain forcing a tool call. See [LLM provider and embedding approach](https://github.com/Jarrod-Bob/contention/issues/9).

## 3. Data

### The niche folder

Everything niche-specific is data in one folder; nothing niche-specific lives in code or prompts. The folder holds **only what the user wrote**: the Niche description, the **Format** list, the Channel list (handles the user typed, each with **Tier** and a one-line reason), and test query texts. The first Niche is **tech careers**. See [ADR 0001](../adr/0001-niche-is-a-curated-channel-list.md).

### The Corpus

- **Channels:** ~100–200, hand-curated, spread across 5 Tiers (1k–10k, 10k–100k, 100k–500k, 500k–1M, 1M+), ~30 each. Candidates come from channels the user knows, then each Channel's featured channels, then ~20 seed searches (mainly for small Tiers).
- **Videos:** every English, long-form Video a curated Channel published in the last 3 years (~15–30k). Long-form is decided by `duration`.
- **A Video's text:** title, description, **Chapters** (parsed from the description), tags, topic categories. Never a transcript.
- **Snapshots:** each weekly refresh records timestamped metrics per Video and Channel, kept as a rolling history of up to 28 days.
- **Store:** one Postgres database keyed by YouTube id, with Niche membership as a label. A Channel in two Niches is stored once.
- **Held-out test Videos:** a fixed random sample of ~40 Videos, ≥30 days old, across the 5 Tiers. Flagged in the database, excluded from the index and from training, kept with metrics for scoring; a deleted one is replaced from the same Tier.

Decisions: [Choose the Corpus niche](https://github.com/Jarrod-Bob/contention/issues/8), [Corpus collection and refresh policy](https://github.com/Jarrod-Bob/contention/issues/16), [Transcript policy for the Corpus](https://github.com/Jarrod-Bob/contention/issues/15).

### Refresh and data lifecycle

`contention refresh` runs weekly (via `launchd`) and on demand (~1,300 of 10,000 daily quota units). In order:

1. Re-read every curated Channel's uploads; fetch Video details and Channel stats; write Snapshots.
2. **Delete**, with everything derived from them: Videos that disappeared (deleted, private, became Shorts), Videos past the 3-year window, Videos of Channels removed from the list (unless in another Niche), and anything not refreshed within 28 days. Purge Snapshots older than 28 days.
3. For new or changed Videos: clean the description (strip URLs, hashtags, sponsor and "follow me" lines), parse Chapters, embed, infer Audience and Format.
4. Re-cluster Themes and Audience groups; relabel them.
5. Retrain the predictor and recompute its errors for every Corpus Video.
6. Reload the in-memory vectors.

On startup, the app purges anything not refreshed within 28 days before serving answers.

**Derived data follows its source:** cleaned text, Chapters, embeddings, labels, Themes, Audience groups, predictor errors, eval labels, grades, ratings and stored answers are refreshed with their Video and deleted with it. **Kept permanently:** only what the user wrote (the niche folder, Drafts) and aggregate eval scores per milestone run. Optimiser and Strategist answers are regenerated, not archived.

## 4. Enrichment

- **Embeddings:** one sentence-transformer over title + Chapters + the first ~500 characters of the cleaned description. The model is picked by the retrieval eval from `all-MiniLM-L6-v2`, `bge-small-en-v1.5`, `bge-base-en-v1.5` (ties go to the smaller). Stored in a pgvector column.
- **Audience and Format:** the local labelling model reads title, Chapters, tags and the first ~1,000 characters of the cleaned description, and returns (structured) an Audience of one sentence ≤ 15 words and one Format from the Niche's list. Recomputed only when that text changes, or fully when the list, prompt or model changes. Starting Format list for tech careers: personal story · tutorial / how-to · advice / tips list · commentary / opinion · interview / podcast · day-in-the-life · mock interview / walkthrough · review / reaction · news / update · Q&A · other.
- **Audience groups:** Audience descriptions are embedded and clustered, then labelled.
- **Themes:** Video embeddings are clustered over the whole Corpus, then labelled.
- **Duration bands:** fixed, objective bands (e.g. < 8, 8–15, 15–30, 30+ minutes).

Decisions: [Inferring Audience and Format for Corpus Videos](https://github.com/Jarrod-Bob/contention/issues/19), [Shape of a Content Strategist answer](https://github.com/Jarrod-Bob/contention/issues/13).

## 5. Retrieval

Scoped to one Niche. Exposed to LangChain as a custom retriever.

1. **Hard filters:** Niche, long-form, not a held-out test Video, and ≥30 days old where predictor errors are needed.
2. **Keyword search:** hand-written BM25 over weighted fields (title highest, then Chapters and tags, then cleaned description), cross-checked against `rank_bm25`.
3. **Vector search:** exact cosine similarity over the in-memory matrix.
4. **Fusion:** RRF by default; a weighted sum of normalised scores is compared in the retrieval eval.
5. **Reranking (optional):** a local cross-encoder over the top ~50, kept only if the retrieval eval shows it helps.
6. **Boosts:** Audience similarity, the user's own Channel, recency.

Decision: [Retrieval store and hybrid retrieval design](https://github.com/Jarrod-Bob/contention/issues/11), [ADR 0005](../adr/0005-postgres-store-retrieval-in-python.md).

## 6. Predictor

- **Target:** log(`viewCount`) at the latest Snapshot. Trained on Videos ≥30 days old, excluding held-out test Videos. Drafts are always predicted at an age of **90 days**.
- **Model:** LightGBM; Ridge regression as a second baseline.
- **80% range:** conformalised quantile regression (CQR) on LightGBM quantile models.
- **Features:**
  - *Channel strength (no subscriber count):* median log views of the Channel's ~10 Videos published before this one, their median age, and the Channel's upload count by then.
  - *Title:* embedding reduced to ~32 dimensions; length, contains a number, question, first person, all-caps words.
  - *Structure:* log duration, Chapter count, description length, tag count.
  - *Labels:* Theme (nearest cluster for a Draft) and Format.
  - *Age:* log age at the Snapshot (90 days for a Draft).
  - *Drift:* the share of the Video's life since 2026-08-24, when YouTube changed what counts as a view (1 for every Draft).
- **Channel context for a Draft:** the user's own Channel by default (its latest uploads fetched on demand if it isn't in the Corpus, never stored past 28 days), or a Tier override that sets the Channel features to that Tier's typical values.
- **Errors:** actual minus predicted log views for every Corpus Video ≥30 days old, from **out-of-fold** predictions. They pick the Optimiser's contrast set and drive the Strategist's group stats. Shown to the user only as "did better / worse than expected", never as a YouTube statistic.
- **Explanations:** TreeSHAP contributions, grouped into readable terms (e.g. "title wording").

Decisions: [Predictor target metric](https://github.com/Jarrod-Bob/contention/issues/10), [Predictor model family and features](https://github.com/Jarrod-Bob/contention/issues/18), [ADR 0003](../adr/0003-predict-raw-log-views.md), [ADR 0007](../adr/0007-predictor-prior-uploads-lightgbm-cqr.md).

## 7. Content Optimiser

One-shot: submit a Draft, get a report.

**Input (a Draft):** required title, planned duration, and a Channel (the user's own by default) or a Tier. Optional description, tags, script or outline, Chapters, and intended Audience.

**Processing:**
1. If a script is given, the LLM summarises it into Chapters.
2. The local labelling model infers the Draft's Audience and Format (same prompt as the Corpus).
3. The predictor gives an 80% range of views at 90 days and SHAP signals.
4. Retrieval finds similar Videos; the contrast set is those that did better and worse than the predictor expected, with the user's own Channel's Videos also shown separately when it's in the Corpus.
5. Claude writes suggestions over the Evidence (structured output).
6. Title what-ifs: the predictor re-scores alternative titles; a what-if is shown only if its change exceeds the prediction's uncertainty.

**Output:**
- The 80% range, plus how it compares with the Channel's typical Video at 90 days.
- Positive and risk signals from SHAP.
- An Audience mismatch note if the inferred and intended Audiences differ.
- Up to 5 suggestions, ranked by impact, each with *what to change*, *why*, *cited Evidence Videos* (title and link) and *confidence* (how much of the contrast set supports it). No suggestions about a script's wording.
- Title what-ifs that passed the threshold.

Decision: [Content Optimiser input and output](https://github.com/Jarrod-Bob/contention/issues/12).

## 8. Content Strategist

RAG over computed analytics, run as a fixed pipeline (not an agent).

**Input:** a free-form question, with optional scope: a Channel (the user's own) or a Tier, and an intended Audience. The Niche description is passed in as data.

**Pipeline:**
1. Retrieve related Videos.
2. Group them by Theme, Audience group, Format and duration band.
3. Compute each group's stats: Video count, how many did better or worse than the predictor expected, and the typical size of the gap.
4. Claude reasons over the Videos and the computed numbers (structured output). It never counts or estimates.
5. **Check:** every claim must cite retrieved Evidence ids and quote computed stats by reference. Code verifies both. On failure, retry once with the errors; if it still fails, remove the failing claims and say so visibly.

**Output:**
- Up to 3 directions, each with the direction, an example concept (a title), a format (duration band + suggested Chapter structure), a target Audience, Evidence (cited Videos + group stats), and confidence.
- **Confidence** is computed from sample size and consistency (Low / Moderate / High), with the reason shown.
- With a Channel or Tier, each concept gets the predictor's 90-day range; small differences between directions aren't presented as meaningful.
- A note on what the Evidence doesn't cover.

Decisions: [Shape of a Content Strategist answer](https://github.com/Jarrod-Bob/contention/issues/13), [ADR 0006](../adr/0006-strategist-rag-over-computed-analytics.md).

## 9. Interface

- **Streamlit app (local):** a Strategist page, an Optimiser page (Draft form), and keyboard-driven labelling pages with a queue per job: Audience/Format labels, retrieval grade confirmation, usefulness ratings, judge calibration.
- **Typer CLI:** `refresh`, Channel curation (e.g. `channels add`), migrations, eval runs (e.g. `eval retrieval`). The weekly `launchd` job calls `refresh`.

Decision: [Interface for the Strategist and Optimiser](https://github.com/Jarrod-Bob/contention/issues/23).

## 10. Evaluation

| What | How | Good enough |
| --- | --- | --- |
| Predictor | Time-based split (headline) + held-out-Channel split. MAE on log views (reported as "off by ×N") and 80% range coverage. Baselines: Channel median at similar age, Niche median, Ridge. | ≥10% lower MAE than the Channel-median baseline, beats Ridge, 75–85% coverage |
| Retrieval | ~40 queries (Strategist-style and Drafts-as-queries), pooled across variants, pre-graded 0/1/2 by an LLM and confirmed by the user. nDCG@10 and Recall@50. Decides fusion, reranker, embedding model, BM25 field weights. | Chosen hybrid beats keyword-only and embedding-only |
| Grounding | An LLM judge marks each Strategist claim and Optimiser suggestion supported / partly / unsupported against its cited Evidence. The judge is first calibrated on ~30 claims the user grades. Also report retries and removed claims. | Judge ≥85% agreement with the user; ≥90% of claims supported |
| Usefulness | The user rates answers 1–5 (actionable, not obvious, fits the Niche): ~15 Strategist questions and ~10 test Drafts per milestone run. | Tracked per run |
| Optimiser end to end | Held-out test Videos submitted as Drafts (title, duration, description, Chapters only); predictions scored against actual views. | As predictor |
| Audience and Format | ~100 Videos hand-labelled by the user. | Format ≥80% correct; Audience judged plausible; "other" ≤ ~10% |
| Themes | Checklist inspection of sampled members per cluster. | No cluster mixes unrelated Videos |

**Cost:** LLM evals run only at milestones, capped at **$5 per run** (expected ~$2–3): batched Opus 5.5 answers, a free or Haiku judge, and stored answers so re-judging is free (while their Videos remain in the Corpus). Retrieval and predictor evals are local and run anytime.

Decision: [Evaluation plan](https://github.com/Jarrod-Bob/contention/issues/14).

## 11. Reconciliations

Where later decisions refined earlier ones, this spec follows the later one:

1. **Where eval data lives.** The Evaluation plan put eval sets in the niche folder; the interface decision moved labels, grades, ratings and stored answers into Postgres, following their Videos (30-day rule on API ids). The niche folder keeps only the query texts and lists the user wrote. ([ADR 0001](../adr/0001-niche-is-a-curated-channel-list.md) consequences.)
2. **Opening suggestions.** The Optimiser originally allowed opening-level suggestions if transcripts were available; with no transcripts, a script is compared through its Chapters instead.
3. **Theme labels.** The Strategist decision allowed free models for Theme labels; this spec uses the same local labelling model as Audience and Format, for consistency and zero cost.
4. **Predictor errors.** Errors that pick contrast sets and drive group stats come from out-of-fold predictions and cover Videos ≥30 days old only; in-sample errors would understate how surprising a Video was.

## 12. Decision index

| Decision | Ticket | ADR |
| --- | --- | --- |
| YouTube Data API facts | [YouTube Data API: quotas, public fields, and transcript access](https://github.com/Jarrod-Bob/contention/issues/7) | |
| Niche and Corpus membership | [Choose the Corpus niche](https://github.com/Jarrod-Bob/contention/issues/8) | [0001](../adr/0001-niche-is-a-curated-channel-list.md) |
| Models, embeddings, framework | [LLM provider and embedding approach](https://github.com/Jarrod-Bob/contention/issues/9) | [0002](../adr/0002-langchain-orchestration-hand-built-retrieval.md) |
| Predictor target | [Predictor target metric](https://github.com/Jarrod-Bob/contention/issues/10) | [0003](../adr/0003-predict-raw-log-views.md) |
| Store and retrieval | [Retrieval store and hybrid retrieval design](https://github.com/Jarrod-Bob/contention/issues/11) | [0005](../adr/0005-postgres-store-retrieval-in-python.md) |
| Optimiser | [Content Optimiser input and output](https://github.com/Jarrod-Bob/contention/issues/12) | |
| Strategist | [Shape of a Content Strategist answer](https://github.com/Jarrod-Bob/contention/issues/13) | [0006](../adr/0006-strategist-rag-over-computed-analytics.md) |
| Evaluation | [Evaluation plan](https://github.com/Jarrod-Bob/contention/issues/14) | |
| Transcripts | [Transcript policy for the Corpus](https://github.com/Jarrod-Bob/contention/issues/15) | [0004](../adr/0004-corpus-has-no-transcripts.md) |
| Collection and refresh | [Corpus collection and refresh policy](https://github.com/Jarrod-Bob/contention/issues/16) | [0003](../adr/0003-predict-raw-log-views.md) (derived data) |
| Predictor model and features | [Predictor model family and features](https://github.com/Jarrod-Bob/contention/issues/18) | [0007](../adr/0007-predictor-prior-uploads-lightgbm-cqr.md) |
| Audience and Format | [Inferring Audience and Format for Corpus Videos](https://github.com/Jarrod-Bob/contention/issues/19) | |
| Interface and persistence | [Interface for the Strategist and Optimiser](https://github.com/Jarrod-Bob/contention/issues/23) | [0001](../adr/0001-niche-is-a-curated-channel-list.md) (refined) |
