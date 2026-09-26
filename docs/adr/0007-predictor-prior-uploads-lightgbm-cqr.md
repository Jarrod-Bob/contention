# Predictor: prior-uploads Channel features, LightGBM with conformalised ranges

The predictor never uses a Channel's subscriber count. Channel strength comes from a prior-uploads baseline: the median log views of the Channel's ~10 Videos published before the one being predicted, their median age, and how many Videos the Channel had uploaded by then. Current subscriber counts leak the answer (a small Channel's hit multiplies its subscribers), and the 30-day storage limit means subscriber counts at publish time can never be kept. The prior-uploads baseline only looks backwards, exactly like a Draft, which knows its Channel's past Videos but not the future. The model is LightGBM, with a Ridge regression as a second baseline, and the 80% range comes from conformalised quantile regression (CQR) so its coverage is calibrated.

## Considered Options

- **Current subscriber count as a feature.** Rejected: leaks the target.
- **Quantile LightGBM without calibration.** Rejected: coverage is often off; the Evaluation plan requires 75–85%.
- **A fine-tuned text model.** Rejected: heavy, and the text is mostly a title.

## Consequences

- A small leak remains: a hit also lifts views on a Channel's older Videos. Accepted.
- For the user's own Channel, the baseline comes from its latest uploads, fetched on demand if it isn't in the Corpus and never stored past 28 days. For a Tier override, it is set to that Tier's typical values.
- Theme is a feature, and Themes are re-clustered on every weekly refresh, so the predictor is retrained after each refresh.
- TreeSHAP contributions, grouped into readable terms, explain each prediction in the Content Optimiser.
