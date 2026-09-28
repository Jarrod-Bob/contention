# contention MVP spec

A single-user, local tool over a public YouTube **Corpus** (one **Niche**, long-form only) with two features: a **Content Strategist** ("what should I create?") and a **Content Optimiser** ("how should I improve this **Draft**, and how might it do?"). Both are text-only, cite **Evidence**, and the Optimiser predicts one public metric.

This spec is the destination of the map [Map: contention MVP spec](https://github.com/Jarrod-Bob/contention/issues/6), revised by [Map: YouTube API compliance approach](https://github.com/Jarrod-Bob/contention/issues/43). It states *what* is built. The *why* lives in the linked tickets and ADRs; don't re-argue decisions here, change them there. Terms in **bold** are defined in [`CONTEXT.md`](../../CONTEXT.md).

## 1. Goals and constraints

- **Learning-first.** Each technique (LLM reasoning, hybrid RAG, classic ML, clustering) is built honestly, not delegated to a framework that hides it.
- **Single user, local.** No auth, no deployment, no multi-user concerns.
- **Python.**
- **Within YouTube's terms.** Public data only, via the YouTube Data API. No transcripts, no scraping. Public data and everything derived from it is refreshed or deleted within 30 days. Corpus Videos never get inferred categories, audiences or performance scores, even internally; only ambiguous derivations (embeddings, unlabelled clusters, Draft predictions) are used. See [ADR 0004](../adr/0004-corpus-has-no-transcripts.md), [ADR 0008](../adr/0008-derived-data-follow-the-clear-text.md) and §11.
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
| Clustering | HDBSCAN (or similar) for unlabelled Themes |
| UI | Streamlit (local) |
| Operations | Typer CLI, weekly `launchd` job |

Decisions: [ADR 0002](../adr/0002-langchain-orchestration-hand-built-retrieval.md), [ADR 0005](../adr/0005-postgres-store-retrieval-in-python.md), [Interface for the Strategist and Optimiser](https://github.com/Jarrod-Bob/contention/issues/23).

### Model roles

| Job | Model | Why this one |
| --- | --- | --- |
| Strategist and Optimiser answers (real use) | Claude Opus 5.5 (`claude-opus-5-5`) via LangChain | Quality; real Drafts only go to Claude |
| Strategist and Optimiser answers (while building) | a free OpenRouter model on a zero-retention endpoint, else the local Ollama model; sample Drafts only | Free |
| Strategist and Optimiser answers (evals) | Claude Opus 5.5 via the Message Batches API, same prompt, model and effort as the LangChain path; each batch deleted once its results are stored | 50% cheaper |
| Draft Audience | one local model through Ollama | Free, private |
| Eval judge (grounding) | a free OpenRouter zero-retention model if it passes calibration, else Claude Haiku 4.5 | Cheap |
| Retrieval relevance pre-grading | a free OpenRouter zero-retention model, else the local Ollama model; confirmed by the user | Free |

**Which providers may receive YouTube data:** only those that don't train on inputs and keep them ≤30 days. Anthropic's API qualifies (don't use its Files API for YouTube data). OpenRouter qualifies only with account prompt logging off, the training opt-out on for free and paid models, and every request sending `provider: {zdr: true, data_collection: "deny"}`. Ollama runs with `OLLAMA_NO_CLOUD=1`. No hosted tracing (e.g. LangSmith). See [Which LLM providers may receive API Data](https://github.com/Jarrod-Bob/contention/issues/47).

Opus 5.5 notes for builders: thinking can't be disabled, so set `effort` explicitly (default `medium`); forced tool choice returns a 400, so structured output must not rely on LangChain forcing a tool call. See [LLM provider and embedding approach](https://github.com/Jarrod-Bob/contention/issues/9).

## 3. Data

### The niche folder

Everything niche-specific is data in one folder; nothing niche-specific lives in code or prompts. The folder holds **only what the user wrote**: the Niche description, the **Format** list (offered on the Draft form), the Channel list (handles the user typed, each with **Tier** and a one-line reason), and test query texts. The first Niche is **tech careers**. See [ADR 0001](../adr/0001-niche-is-a-curated-channel-list.md).

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
3. For new or changed Videos: clean the description (strip URLs, hashtags, sponsor and "follow me" lines), parse Chapters, embed.
4. Re-cluster Themes (unlabelled).
5. Retrain the predictor and recompute its out-of-fold errors (used only by the predictor eval).
6. Reload the in-memory vectors.

On startup, the app purges anything not refreshed within 28 days before serving answers.

**Files:** every derived file (trained models, batch input and output files, detailed eval outputs, logs) lives in one git-ignored `artefacts/` directory, tagged with the refresh run that made it; the purge and the startup guard delete runs older than 28 days. The BM25 index, the embedding matrix and Streamlit caches live in memory only (never `persist="disk"`). Never `pg_dump` the Corpus tables; back up only user-written data. Any machine backup excludes the Postgres data directory and `artefacts/`. See [Persisted artefacts outside Postgres](https://github.com/Jarrod-Bob/contention/issues/46).

**Derived data follows its source:** cleaned text, Chapters, embeddings, Themes, predictor errors, grades, ratings and stored answers are refreshed with their Video and deleted with it. **Kept permanently:** only what the user wrote (the niche folder, Drafts, sample Drafts and their Audience labels, the privacy agreement date) and aggregate eval scores per milestone run. Optimiser and Strategist answers are regenerated, not archived.

## 4. Enrichment

- **Embeddings:** one sentence-transformer over title + Chapters + the first ~500 characters of the cleaned description. The model is picked by the retrieval eval from `all-MiniLM-L6-v2`, `bge-small-en-v1.5`, `bge-base-en-v1.5` (ties go to the smaller). Stored in a pgvector column.
- **Themes:** Video embeddings are clustered over the whole Corpus. Themes are never labelled, named or shown as categories.
- **No inferred labels on Corpus Videos:** no Audience, Format or Theme labels are created for Corpus Videos ([ADR 0008](../adr/0008-derived-data-follow-the-clear-text.md)).
- **Duration bands:** fixed, objective bands (e.g. < 8, 8–15, 15–30, 30+ minutes).

Decisions: [Derived data: audit, redesign, or accept the risk](https://github.com/Jarrod-Bob/contention/issues/45), [Shape of a Content Strategist answer](https://github.com/Jarrod-Bob/contention/issues/13).

## 5. Retrieval

Scoped to one Niche. Exposed to LangChain as a custom retriever.

1. **Hard filters:** Niche, long-form, not a held-out test Video, and an age band where a comparison needs one.
2. **Keyword search:** hand-written BM25 over weighted fields (title highest, then Chapters and tags, then cleaned description), cross-checked against `rank_bm25`.
3. **Vector search:** exact cosine similarity over the in-memory matrix.
4. **Fusion:** RRF by default; a weighted sum of normalised scores is compared in the retrieval eval.
5. **Reranking (optional):** a local cross-encoder over the top ~50, kept only if the retrieval eval shows it helps.
6. **Boosts:** the user's own Channel, recency. An intended Audience is appended to the query text, so embedding similarity does the rest.

Decision: [Retrieval store and hybrid retrieval design](https://github.com/Jarrod-Bob/contention/issues/11), [ADR 0005](../adr/0005-postgres-store-retrieval-in-python.md).

## 6. Predictor

- **Target:** log(`viewCount`) at the latest Snapshot. Trained on Videos ≥30 days old, excluding held-out test Videos. Drafts are always predicted at an age of **90 days**.
- **Model:** LightGBM; Ridge regression as a second baseline.
- **80% range:** conformalised quantile regression (CQR) on LightGBM quantile models.
- **Features:**
  - *Channel strength (no subscriber count):* median log views of the Channel's ~10 Videos published before this one, their median age, and the Channel's upload count by then.
  - *Title:* embedding reduced to ~32 dimensions; length, contains a number, question, first person, all-caps words.
  - *Structure:* log duration, Chapter count, description length, tag count.
  - *Theme:* the unlabelled cluster id (nearest cluster for a Draft).
  - *Age:* log age at the Snapshot (90 days for a Draft).
  - *Drift:* the share of the Video's life since 2026-08-24, when YouTube changed what counts as a view (1 for every Draft).
- **Channel context for a Draft:** the user's own Channel by default (its latest uploads fetched on demand if it isn't in the Corpus, never stored past 28 days), or a Tier override that sets the Channel features to that Tier's typical values.
- **Errors:** actual minus predicted log views for every Corpus Video ≥30 days old, from **out-of-fold** predictions. Used only by the predictor eval: never shown, and never used by the Optimiser or Strategist ([ADR 0010](../adr/0010-optimiser-compares-raw-views-errors-eval-only.md)).
- **Explanations:** TreeSHAP contributions, grouped into readable terms (e.g. "title wording"). The Theme term is shown as "what the Draft is about (similar-topic group)", never a category name.

Decisions: [Predictor target metric](https://github.com/Jarrod-Bob/contention/issues/10), [Predictor model family and features](https://github.com/Jarrod-Bob/contention/issues/18), [ADR 0003](../adr/0003-predict-raw-log-views.md), [ADR 0007](../adr/0007-predictor-prior-uploads-lightgbm-cqr.md), [ADR 0010](../adr/0010-optimiser-compares-raw-views-errors-eval-only.md).

## 7. Content Optimiser

One-shot: submit a Draft, get a report.

**Input (a Draft):** required title, planned duration, and a Channel (the user's own by default) or a Tier. Optional description, tags, script or outline, Chapters, intended Audience, and a Format picked from the Niche's list.

**Processing:**
1. If a script is given, the LLM summarises it into Chapters.
2. The local model infers the Draft's Audience (skipped when held-out Corpus Videos are run as Drafts in evals).
3. The predictor gives an 80% range of views at 90 days and SHAP signals.
4. Retrieval finds similar Videos from the Draft's Tier within a comparable age band (e.g. 60–365 days old), sorted by raw YouTube views; the **contrast set** is the top and bottom of that list.
5. Claude writes suggestions over the Evidence (structured output); a chosen Format is passed as context.
6. Title what-ifs: the predictor re-scores alternative titles; a what-if is shown only if its change exceeds the prediction's uncertainty.

**Output:**
- The 80% range, shown next to the user's own Channel's recent Videos listed one by one with their raw YouTube views and publish dates. No Channel average or "typical" figure. With a Tier override, the range alone.
- Positive and risk signals from SHAP.
- An Audience mismatch note if the inferred and intended Audiences differ.
- Up to 5 suggestions, ranked by impact, each with *what to change*, *why*, *cited Evidence Videos* (title and link) and *confidence*: a computed count of top vs bottom contrast-set Videos sharing the trait (e.g. "7 of 10 top vs 2 of 10 bottom"). The LLM names the Videos; code checks they're in the set and counts. No suggestions about a script's wording.
- Title what-ifs that passed the threshold.

Decisions: [Content Optimiser input and output](https://github.com/Jarrod-Bob/contention/issues/12), [Optimiser output without expectation scores](https://github.com/Jarrod-Bob/contention/issues/52), [ADR 0010](../adr/0010-optimiser-compares-raw-views-errors-eval-only.md).

## 8. Content Strategist

RAG over computed analytics, run as a fixed pipeline (not an agent).

**Input:** a free-form question, with optional scope: a Channel (the user's own) or a Tier, and an intended Audience (appended to the retrieval query). The Niche description is passed in as data.

**Pipeline:**
1. Retrieve related Videos.
2. Group them by unlabelled Theme and duration band, within one Tier: the question's scope; else the user's own Channel's Tier; else stats per Tier (Tiers with too few Videos left out).
3. Compute each group's stats, using only simple sums, counts, averages and medians of raw YouTube data: Video count, Channel count, median views, median age, median duration, Tier mix. No predictor errors.
4. Claude reasons over the Videos and the computed numbers (structured output). It never counts or estimates. It may describe cited Videos in prose; that description is never stored as a label.
5. **Check:** every claim must cite retrieved Evidence ids and quote computed stats by reference. Code verifies both. On failure, retry once with the errors; if it still fails, remove the failing claims and say so visibly.

**Output:**
- Up to 3 directions, each with the direction, an example concept (a title), a format (duration band + suggested Chapter structure), a target Audience for the concept, Evidence (cited Videos + group stats; views always shown with median age), and confidence.
- **Confidence** is computed from Video count, Channel count and the spread of log views within the Tier (Low / Moderate / High), with the reason shown.
- With a Channel or Tier, each concept gets the predictor's 90-day range; small differences between directions aren't presented as meaningful.
- A note on what the Evidence doesn't cover.

Decisions: [Shape of a Content Strategist answer](https://github.com/Jarrod-Bob/contention/issues/13), [ADR 0006](../adr/0006-strategist-rag-over-computed-analytics.md), [Strategist grouping without stored categories](https://github.com/Jarrod-Bob/contention/issues/51), [ADR 0009](../adr/0009-strategist-groups-by-unlabelled-theme-acceptable-metrics.md).

## 9. Interface

- **Streamlit app (local):** a Strategist page, an Optimiser page (Draft form), an **About & privacy** page, and keyboard-driven labelling pages with a queue per job: sample-Draft Audience labels, retrieval grade confirmation, usefulness ratings, judge calibration.
- **Typer CLI:** `refresh`, Channel curation (e.g. `channels add`), migrations, eval runs (e.g. `eval retrieval`), and `demo` (loads a synthetic demo Corpus). The weekly `launchd` job calls `refresh`. `--help` points to the About & privacy text in the README.

**YouTube's terms in the UI:**
- **About & privacy page** (mirrored in the README): contention uses YouTube API Services; a link to YouTube's Terms of Service (https://www.youtube.com/t/terms) and that using contention means agreeing to them; a link to the Google Privacy Policy (http://www.google.com/policies/privacy); what is fetched and stored and that it's deleted after 28 days; which LLM providers receive YouTube data; contact via GitHub Issues. On first launch the app shows it with an **I agree** button and stores the date.
- **Attribution:** the official "developed with YouTube" logo, linked to youtube.com, next to the Evidence on the Strategist and Optimiser pages, per the Branding Guidelines. Every Evidence Video links to its YouTube page. No YouTube logo as the app icon; no "YouTube" or "YT" in the app's name.
- **Source labels:** YouTube numbers and text read "YouTube · as of <last refresh date>"; predictions, confidence, suggestions, directions and group stats read "Computed by contention, not from YouTube".
- **Descriptions:** wherever one is shown, the original; never the cleaned text.

Decisions: [Interface for the Strategist and Optimiser](https://github.com/Jarrod-Bob/contention/issues/23), [User-facing compliance: privacy, ToS link, attribution and labels](https://github.com/Jarrod-Bob/contention/issues/49).

## 10. Evaluation

| What | How | Good enough |
| --- | --- | --- |
| Predictor | Time-based split (headline) + held-out-Channel split. MAE on log views (reported as "off by ×N") and 80% range coverage. Baselines: Channel median at similar age, Niche median, Ridge. | ≥10% lower MAE than the Channel-median baseline, beats Ridge, 75–85% coverage |
| Retrieval | ~40 queries (Strategist-style and Drafts-as-queries), pooled across variants, pre-graded 0/1/2 by an LLM and confirmed by the user. nDCG@10 and Recall@50. Decides fusion, reranker, embedding model, BM25 field weights. | Chosen hybrid beats keyword-only and embedding-only |
| Grounding | An LLM judge marks each Strategist claim and Optimiser suggestion supported / partly / unsupported against its cited Evidence. The judge is first calibrated on ~30 claims the user grades. Also report retries and removed claims. | Judge ≥85% agreement with the user; ≥90% of claims supported |
| Usefulness | The user rates answers 1–5 (actionable, not obvious, fits the Niche): ~15 Strategist questions and ~10 test Drafts per milestone run. | Tracked per run |
| Optimiser end to end | Held-out test Videos submitted as Drafts (title, duration, description, Chapters only); predictions scored against actual views. | As predictor |
| Draft Audience | ~30 sample Drafts written and labelled by the user. | Audience judged plausible |
| Themes | Checklist inspection of sampled member titles per cluster (no labels). | No cluster mixes unrelated Videos |

**Cost:** LLM evals run only at milestones, capped at **$5 per run** (expected ~$2–3): batched Opus 5.5 answers (batches deleted once stored), a free zero-retention or Haiku judge, and stored answers so re-judging is free (while their Videos remain in the Corpus). Retrieval and predictor evals are local and run anytime.

Decision: [Evaluation plan](https://github.com/Jarrod-Bob/contention/issues/14).

**Publishing:** eval reports and write-ups describe the system and how well it performs, never the YouTube data. Allowed: aggregate or binned measures of contention's own performance (Predictor MAE, range coverage overall and per Tier, nDCG@10 / Recall@50, judge agreement, share of claims supported, usefulness, cost per run), Corpus size and the Niche's name, and a link to the committed niche folder. Not allowed: per-Video plots, charts of Corpus metrics, findings about what content works, stats on named Channels, Theme descriptions. Screenshots and worked examples come only from the synthetic demo Corpus, labelled illustrative. Committed eval result files hold aggregates only. See [What published write-ups and eval reports may contain](https://github.com/Jarrod-Bob/contention/issues/54).

## 11. Reconciliations

Where later decisions refined earlier ones, this spec follows the later one:

1. **Where eval data lives.** The Evaluation plan put eval sets in the niche folder; the interface decision moved labels, grades, ratings and stored answers into Postgres, following their Videos (30-day rule on API ids). The niche folder keeps only the query texts and lists the user wrote. ([ADR 0001](../adr/0001-niche-is-a-curated-channel-list.md) consequences.)
2. **Opening suggestions.** The Optimiser originally allowed opening-level suggestions if transcripts were available; with no transcripts, a script is compared through its Chapters instead.
3. **Labels on Corpus Videos.** Audience, Format and Theme labels, Audience groups, and "did better / worse than expected" were removed from the Corpus by [ADR 0008](../adr/0008-derived-data-follow-the-clear-text.md); the Strategist and Optimiser were redesigned around acceptable metrics ([ADR 0009](../adr/0009-strategist-groups-by-unlabelled-theme-acceptable-metrics.md), [ADR 0010](../adr/0010-optimiser-compares-raw-views-errors-eval-only.md)).
4. **Predictor errors.** Out-of-fold, ≥30 days old only, and now eval-only.

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
| Audience and Format | [Inferring Audience and Format for Corpus Videos](https://github.com/Jarrod-Bob/contention/issues/19) | superseded by [0008](../adr/0008-derived-data-follow-the-clear-text.md) |
| Interface and persistence | [Interface for the Strategist and Optimiser](https://github.com/Jarrod-Bob/contention/issues/23) | [0001](../adr/0001-niche-is-a-curated-channel-list.md) (refined) |
| Derived-data line | [Derived data: audit, redesign, or accept the risk](https://github.com/Jarrod-Bob/contention/issues/45) | [0008](../adr/0008-derived-data-follow-the-clear-text.md) |
| Files outside Postgres | [Persisted artefacts outside Postgres](https://github.com/Jarrod-Bob/contention/issues/46) | |
| LLM providers and YouTube data | [Which LLM providers may receive API Data](https://github.com/Jarrod-Bob/contention/issues/47) | |
| Google account and project | [Google account and Cloud project ownership](https://github.com/Jarrod-Bob/contention/issues/48) | |
| Privacy, attribution, labels | [User-facing compliance: privacy, ToS link, attribution and labels](https://github.com/Jarrod-Bob/contention/issues/49) | |
| Strategist grouping | [Strategist grouping without stored categories](https://github.com/Jarrod-Bob/contention/issues/51) | [0009](../adr/0009-strategist-groups-by-unlabelled-theme-acceptable-metrics.md) |
| Optimiser comparisons | [Optimiser output without expectation scores](https://github.com/Jarrod-Bob/contention/issues/52) | [0010](../adr/0010-optimiser-compares-raw-views-errors-eval-only.md) |
| Publishing | [What published write-ups and eval reports may contain](https://github.com/Jarrod-Bob/contention/issues/54) | |
