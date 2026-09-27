# Follow the derived-data text where it's clear; accept risk only where it's ambiguous

The YouTube Developer Policies ban using API Data "to create new or derived data or metrics", and since June 2026 YouTube's Guide and derived-metrics amendment name what that covers: inferring a video's content category or type, estimating its audience, and scoring channels or videos from their views. We follow those named examples strictly, for internal use too, because the ban is on *creating* the data, not only showing it, and the repo is public. Where the text is silent or ambiguous (embeddings, unlabelled clusters, predictions for Drafts), we accept the risk. This replaces ADR 0003's line ("derived data follows its source, never shown as a YouTube statistic"), which handled storage and display but not creation. Sources: the [policies research note](https://github.com/Jarrod-Bob/contention/blob/research/youtube-developer-policies/docs/research/youtube-developer-policies.md) and the [enforcement research note](https://github.com/Jarrod-Bob/contention/blob/research/youtube-api-enforcement/docs/research/youtube-api-enforcement.md).

| Feature | Ruling |
|---|---|
| Embeddings, BM25, hybrid retrieval | Keep |
| Cleaned description text and Chapters | Keep, internal only; wherever a description is shown, show the original |
| Predicted range for a Draft | Keep, labelled as contention's prediction, not YouTube data |
| Prior-uploads baseline and unlabelled cluster ids as Predictor features | Keep, internal only |
| Out-of-fold predictor errors | Internal only (evals, choosing the contrast set); never shown per Video |
| "Did better / worse than expected", "the Channel's typical Video" | Not shown |
| Format labels on Corpus Videos | Dropped, not created at all |
| Audience labels and Audience groups on Corpus Videos | Dropped, not created at all |
| Theme labels | Dropped; unlabelled clusters internal only |
| Audience and Format of a Draft | Keep where useful: a Draft is user data, not API Data |
| Strategist group stats | Only the Guide's "acceptable metrics" (counts, sums, averages or medians of raw YouTube views and durations) over groups of retrieved Videos |

## Considered Options

- **Apply for the API Compliance Audit (Analytics & Reporting use case) to accept the derived-metrics amendment.** Rejected for now: the only documented storage and derived-data findings came from audits the developer started, a refusal would turn carrying on into a knowing violation, and approval isn't certain. Revisit if contention is ever hosted or needs more than the default quota.
- **Build as designed and accept the risk.** Rejected: the design would visibly match the Guide's named examples in a public repo and write-ups.
- **Follow the Guide's examples and the ambiguous cases too.** Rejected: it would give up embeddings-based retrieval and the Predictor, the project's core learning goals, over text that doesn't mention them.

## Consequences

- **Conditional on a dedicated Google account.** Accepting the ambiguous cases rests on the Cloud project and API key living under a Google account that holds none of the owner's personal data, so the realistic worst case is losing API access, not the account. Without that, fall back to following the ambiguous cases too.
- The Strategist no longer groups by stored Theme, Audience group or Format labels (revises ADR 0006), and the Predictor loses the Format feature (revises ADR 0007).
- ADR 0003's choice of target (raw log views) stands, as does "derived data follows its source" for storage.
