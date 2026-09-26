# contention

A single-user content intelligence tool over public YouTube content, built to learn LLM reasoning, hybrid RAG, and classic ML prediction.

## Language

**Corpus**:
The collection of public YouTube videos that contention indexes and learns from: every English long-form Video published in the last 3 years by the Channels of one Niche. Carries only publicly visible metadata and metrics.
_Avoid_: Dataset, knowledge base, historical content

**Niche**:
The subject area a Corpus covers, e.g. "tech careers". Defined by its curated list of Channels, not by classifying individual Videos.
_Avoid_: Topic, category, vertical

**Channel**:
A public YouTube channel curated into a Niche because most of its long-form output belongs there. All its long-form Videos enter the Corpus, including the occasional off-topic one.
_Avoid_: Creator, account, publisher

**Video**:
One item in the Corpus: a published YouTube video with its public metadata (title, description, Chapters, tags, topic categories) and public metrics. Never its transcript.
_Avoid_: Post, content item, clip

**Snapshot**:
The public metrics of a Video or Channel as read at one moment, with that moment recorded. Public data can't be kept for more than 30 days, so only recent Snapshots exist.
_Avoid_: Stats, reading, record

**Tier**:
A band of Channel subscriber counts: 1k–10k, 10k–100k, 100k–500k, 500k–1M, or 1M+. Channels are curated across Tiers, and a Draft can be predicted for a Tier instead of a real Channel.
_Avoid_: Size, bracket, level

**Chapter**:
A timestamped section title a creator lists in a Video's description, e.g. "2:14 How to negotiate". The only public outline of what happens inside a Video.
_Avoid_: Section, segment, timestamp

**Audience**:
A free-text description of the viewers a Video (or a Draft, or a strategy question) is aimed at, e.g. "early-career software engineers". Inferred from content, never measured.
_Avoid_: Demographic, segment, target market

**Theme**:
A group of similar Videos within a Niche, found by clustering and labelled in a few words, e.g. "salary negotiation" or "first-job mistakes". The Content Strategist reasons about Themes.
_Avoid_: Topic, cluster, category

**Format**:
The kind of Video, from a fixed list (e.g. personal story, tutorial, listicle, interview), inferred from content. Distinct from duration.
_Avoid_: Style, type, genre

**Draft**:
Content the user has not yet published, submitted to the Content Optimiser as text (not as media).
_Avoid_: Upload, submission, new video

**Content Strategist**:
The feature that answers "what should I create?" with recommendations grounded in evidence from the Corpus.
_Avoid_: Strategy engine, recommender

**Content Optimiser**:
The feature that answers "how should I improve this Draft?" by comparing it to similar Videos and a performance prediction.
_Avoid_: Draft analyser, optimizer

**Evidence**:
The specific Videos and analytics a recommendation cites so the user can inspect and challenge it.
_Avoid_: Sources, references, citations
