# contention

A single-user content intelligence tool over public YouTube content, built to learn LLM reasoning, hybrid RAG, and classic ML prediction.

## Language

**Corpus**:
The collection of public YouTube videos, from many channels, that contention indexes and learns from. Carries only publicly visible metadata and metrics.
_Avoid_: Dataset, knowledge base, historical content

**Video**:
One item in the Corpus: a published YouTube video with its metadata, public metrics, and transcript.
_Avoid_: Post, content item, clip

**Audience**:
A free-text description of the viewers a Video (or a Draft, or a strategy question) is aimed at, e.g. "early-career software engineers". Inferred from content, never measured.
_Avoid_: Demographic, segment, target market

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
