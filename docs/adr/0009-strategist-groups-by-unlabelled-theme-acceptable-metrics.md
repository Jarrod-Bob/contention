# The Strategist groups by unlabelled Theme and shows only acceptable metrics

[ADR 0008](0008-derived-data-follow-the-clear-text.md) removed what ADR 0006's pipeline grouped and scored by: Theme labels, Audience groups, Format, and "how many did better or worse than expected". The Strategist now groups retrieved Videos by **stored, unlabelled Theme ids crossed with duration band**, compares them **within one Tier**, and computes only the Developer Policies Guide's "acceptable metrics": simple sums, counts, averages and medians of raw YouTube data. We kept stored Themes rather than clustering each question's results because stable groups make stats repeatable and evaluable, and we dropped predictor errors from the Strategist entirely, even behind the scenes, because a ranking whose reason can't be quoted breaks ADR 0006's rule that every claim cites a computed stat.

- **Stats per group:** Video count, Channel count, median views, median age, median duration, Tier mix. Views are always shown with their median age.
- **Tier:** the question's Channel or Tier; with no scope, the user's own Channel's Tier, or stats per Tier (Tiers with too few Videos left out) until that Channel is set up.
- **Confidence:** Low / Moderate / High from Video count, Channel count (breadth) and the spread of log views within the Tier, with the reason shown. Cut-offs are tuned on the eval runs.
- **Describing groups:** the LLM may describe cited Videos in prose inside an answer; that description is never stored as a label on a Video or Theme.
- **Intended Audience:** appended to the retrieval query as text; there is no Audience grouping. A direction's target Audience is written about the user's concept, not about Corpus Videos.
- **"How might it do":** comes from the predictor's range for each concept, which ADR 0008 allows.

## Considered Options

- **Cluster only the retrieved Videos, per question.** Rejected: groups would change with every phrasing, so stats couldn't be compared or evaluated.
- **Rank groups by predictor errors without showing them.** Rejected: the reason behind a ranking would be hidden from the claim check.
- **Group only by duration band and Tier.** Rejected: loses any grouping by what Videos are about, which the Strategist exists for.

## Consequences

- Raw median views are confounded by age, so comparisons lean on Tier scoping and on showing median age beside every view count.
- The Themes eval stays: inspect sampled member titles per cluster; no labels.
