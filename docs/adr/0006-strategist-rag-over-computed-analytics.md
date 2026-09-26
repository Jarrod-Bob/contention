# The Content Strategist is RAG over computed analytics, in a fixed pipeline rather than an agent

The Content Strategist always runs the same steps in code: retrieve related Videos, group them by Theme, Audience, Format and duration band, compute each group's stats (Video count, how many over- or under-performed the predictor, typical size of the gap), then have the LLM reason over the Videos and the computed numbers. The LLM never counts or estimates statistics, and confidence is computed from sample size and consistency, not stated by the LLM. Every claim in the structured answer cites Evidence ids and quotes computed stats by reference; code checks both, retries once on failure, then removes failing claims with a visible note. We chose this because computing the numbers removes the main place LLMs fabricate, a fixed pipeline is far easier to evaluate, and it is the scoping document's core hypothesis: retrieval plus analytics plus LLM reasoning beats an LLM alone.

## Considered Options

- **Plain RAG (retrieve, then let the LLM spot patterns).** Rejected: the LLM would have to count and compare, where it is least reliable.
- **Agentic RAG (the LLM calls search and stats tools and decides what to look at).** Deferred: a good later learning step, evaluated against this pipeline as its baseline.

## Consequences

- Themes are found once by clustering embeddings over the whole Corpus and recomputed on each refresh, so group stats are stable across questions.
- Format is inferred per Video from a fixed list, in the same pass as Audience.
