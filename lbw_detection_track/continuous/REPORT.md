# Predict the birth weight, then rank by it

Written for the author, the supervisor and the panel. Plan: [PROTOCOL.md](PROTOCOL.md), committed before any result (commit a264373). Every number comes from [outputs/](outputs/). Development pool only; no sealed set was opened.

## Answer

**No.** Learning from every birth weight instead of the yes or no label does not rank low birth weight better. The primary difference, gradient boosted regression against the boosting classifier for set D at 28 weeks, is −0.001 ROC AUC (−0.037 to +0.035, p 0.947).

## Results (`outputs/estimates.csv`, `outputs/comparisons.csv`)

| Week | Set | Logistic | Ridge on weight | Boosting | Boosting on weight | Boosting on lowest tenth |
| --- | --- | --- | --- | --- | --- | --- |
| 28 | B | 0.618 | 0.623 | 0.639 | 0.637 | 0.644 |
| 28 | D | 0.636 | 0.662 | 0.654 | 0.653 | 0.654 |
| 36 | B | 0.648 | 0.654 | 0.655 | 0.648 | 0.619 |
| 36 | D | 0.638 | 0.648 | 0.669 | 0.665 | 0.656 |

* None of the twelve paired comparisons has an interval that excludes zero.
* The largest gain is ridge over logistic for set D at 28 weeks: +0.026 (−0.006 to +0.058). It is a secondary result and is not claimed.
* Every configuration stays between 0.62 and 0.67, the same band as every earlier analysis.

The recorded birth weights include clear typing errors: the largest in the file is 500 kg. The training target was limited to 0.5 to 5.5 kg as planned.

Reproduce: `python lbw_detection_track/follow_up/run.py`, then `python lbw_detection_track/continuous/run.py` (about one minute).
