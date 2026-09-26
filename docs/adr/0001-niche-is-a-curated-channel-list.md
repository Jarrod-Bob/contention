# A Niche is a curated Channel list, stored as a label

A Niche is defined by a hand-curated list of Channels, not by classifying individual Videos: every English long-form Video a curated Channel published in the last 3 years enters the Corpus, off-topic ones included. We chose this because it avoids the 100-calls/day search quota, keeps each Channel's full upload history for the predictor to learn channel-level effects, and makes membership easy to explain when a recommendation looks wrong.

The MVP builds and queries one Niche at a time, and everything niche-specific (description, Channel list, eval set) is data kept in one niche folder, never in code or prompts. Channels and Videos live in one store keyed by YouTube id with Niche membership as a label, all Niches share one embedding model, and the predictor trains on whatever set of Videos is in scope.

## Considered Options

- **Classify each Video into or out of the Niche.** Rejected: needs search or a classifier to find candidates, and fragments Channel histories.
- **Fully separate data, index and model per Niche.** Rejected: a future cross-niche question would then need a data migration, and fusing separately trained predictors is unsound (each extrapolates outside its training data). With one labelled store, cross-niche retrieval is a query over the union, and cross-niche prediction is retraining on pooled Videos with Niche as a feature.

## Consequences

- A Channel in two Niches' lists is stored once.
- Switching Niches does not delete the old one: its data must still be refreshed or purged within 30 days under the YouTube Developer Policies.
- **What the niche folder holds** (refined when resolving "Interface for the Strategist and Optimiser", #23): only what the user wrote, meaning the Niche description, the Format list, the Channel list as handles the user typed, and test query texts. Eval labels, retrieval grades, usefulness ratings and stored answers reference Videos by id, and no exception lets API ids outlive the 30-day limit, so they live in Postgres and follow their Video (ADR 0003). Aggregate eval scores per milestone run are kept permanently.
