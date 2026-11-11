# Follow up window: does incomplete follow up blur the signal?

Written for the author, the supervisor and the panel. Plan: [PROTOCOL.md](PROTOCOL.md), committed before any model result (commit 6561210). Every number comes from [outputs/](outputs/). Development pool only; the track test set and the main held out set were not opened.

## Answer

**No.** Restricting to pregnancies with complete follow up lowers ROC AUC rather than raising it, and the models detect preterm and term low birth weight about equally poorly.

## F1: the calendar pattern (`outputs/by_quarter.csv`)

| Start quarter (last period) | Records | Low birth weight | Share | Recorded preterm share |
| --- | --- | --- | --- | --- |
| 2023 Q3 | 162 | 3 | 1.9% | 1.9% |
| 2023 Q4 | 340 | 5 | 1.5% | 2.4% |
| 2024 Q1 | 671 | 22 | 3.3% | 3.1% |
| 2024 Q2 | 2,043 | 94 | 4.6% | 3.6% |
| 2024 Q3 | 1,677 | 95 | 5.7% | 3.7% |
| 2024 Q4 | 344 | 22 | 6.4% | 6.7% |

The share rises with calendar time. That fits early births missing from pregnancies that started before the register and late births missing from those that started near the end of the extract. It is a property of the file to report as a limitation. Calendar date must never be a predictor, because it would pick up this artefact.

## F2 and F3: full pool against the complete follow up window (`outputs/results.csv`)

| Week | Set | Method | Full pool ROC AUC | Window ROC AUC | Term cases ROC AUC (full) | Preterm cases ROC AUC (full) |
| --- | --- | --- | --- | --- | --- | --- |
| 28 | B | logistic | 0.618 | 0.600 | 0.649 | 0.563 |
| 28 | B | boosting | 0.639 | 0.601 | 0.654 | 0.613 |
| 28 | D | logistic | 0.636 | 0.617 | 0.648 | 0.615 |
| 28 | D | boosting | 0.654 | 0.626 | 0.650 | 0.660 |
| 36 | B | logistic | 0.648 | 0.595 | 0.650 | 0.640 |
| 36 | B | boosting | 0.655 | 0.644 | 0.642 | 0.705 |
| 36 | D | logistic | 0.638 | 0.581 | 0.621 | 0.703 |
| 36 | D | boosting | 0.669 | 0.617 | 0.646 | 0.759 |

* The window is lower in all eight configurations, so the protocol's condition for "follow up blurs the signal" is not met. The window holds fewer cases (120 and 69), which also widens the intervals.
* No term interval lies wholly above its preterm point estimate, so the F3 condition is not met either. At week 36 only 14 to 17 cases are preterm, so those figures are very uncertain.

Reproduce: `python lbw_detection_track/follow_up/run.py` (about two minutes).
