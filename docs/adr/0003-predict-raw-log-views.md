# Predict raw log views; outperformance is explained, never the target

The predictor's target is log(`viewCount`) at the latest snapshot, not a ratio such as views relative to the channel median, engagement rate or like rate. The YouTube Developer Policies ban using API data "to create new or derived data or metrics", and we read that strictly: the target stays a raw public metric, and channel size and Video age go in as features so the model learns each Channel's baseline itself. Outperformance can still be shown to the user as an explanation, but it is never trained on.

## Considered Options

- **Views relative to the channel median (outperformance).** Rejected: a derived metric under the strict reading, and the model learns the same baseline from channel features.
- **Views at a fixed age (e.g. day 7).** Rejected for the MVP: the Data API has no history, so it needs daily polling of new uploads, yields only a few hundred Videos a month, and the 30-day retention rule caps the age at 30 days. A good follow-up once collection has run for a while.

## Consequences

- Only Videos at least 30 days old are trained on, and every Draft is predicted at an age of 90 days.
- A Draft is predicted for a Channel: the user's own by default, or a chosen subscriber tier.
- A feature records how much of a Video's life came after YouTube's 2026-08-24 view-count definition change.
- **Derived data follows its source** (added when resolving "Corpus collection and refresh policy", #16): cleaned text, Chapters, embeddings, Audience and Format labels, Themes and predictor errors count as API data. They are refreshed with their source Video, deleted with it, and never kept past 30 days. No derived metric is ever created or shown as a YouTube statistic. The fully literal reading of "new or derived data" would forbid the whole project, so this is where we draw the line.
