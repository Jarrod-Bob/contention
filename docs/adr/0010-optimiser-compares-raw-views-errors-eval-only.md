# The Optimiser compares against raw views; predictor errors are eval-only

[ADR 0008](0008-derived-data-follow-the-clear-text.md) stopped showing "the Channel's typical Video" and "did better / worse than expected", but still let out-of-fold predictor errors choose the Optimiser's contrast set behind the scenes. We don't use that allowance: the contrast set is built only from the Developer Policies Guide's "acceptable metrics", and predictor errors are used only to evaluate the Predictor. A set chosen by hidden errors would have the suggestions imply "these beat expectations" and base their confidence on scores the user can't see, the same problem that kept errors out of the Strategist ([ADR 0009](0009-strategist-groups-by-unlabelled-theme-acceptable-metrics.md)).

- **Contrast set:** similar Videos from the Draft's Tier, within a comparable age band (e.g. 60–365 days old), sorted by raw YouTube views; the top and bottom of that list.
- **Suggestion confidence:** a computed count of how many top versus bottom Videos share the suggested trait (e.g. "7 of 10 top vs 2 of 10 bottom"). The LLM names which Videos show the trait; code checks every cited Video is in the set. The LLM never states the count.
- **The Draft's range:** shown next to the user's own Channel's recent Videos, listed one by one with their raw YouTube views and publish dates ("YouTube · as of …"). contention computes no Channel average or "typical" figure for display. With a Tier override, the range is shown alone.
- **Format:** an optional field the user picks on the Draft from the Niche's Format list, passed to the LLM as context. Never inferred, and no longer a Predictor feature.
- **Audience:** the local model still infers a Draft's Audience for the mismatch note, evaluated on ~30 sample Drafts the user writes. When held-out Corpus Videos are run as Drafts in evals, Audience inference is skipped.
- **Explanations:** the unlabelled Theme's SHAP term is shown with a neutral name ("what the Draft is about (similar-topic group)"), never a category name.

## Considered Options

- **Let errors pick the contrast set without showing them** (allowed by ADR 0008). Rejected: hidden reasons behind visible Evidence and confidence.
- **Compare the range with the median of the Channel's recent views.** Rejected: an average view count per Channel is one of the Guide's named examples of a channel score.

## Consequences

- Raw views are confounded by age and Channel; the Tier and age-band filters carry that, and every view count is shown with its age.
- The Predictor loses the Format feature; Theme enters as the nearest unlabelled cluster id (see [ADR 0007](0007-predictor-prior-uploads-lightgbm-cqr.md)).
- The Audience and Format eval on ~100 hand-labelled Corpus Videos is replaced by the Draft Audience eval.
