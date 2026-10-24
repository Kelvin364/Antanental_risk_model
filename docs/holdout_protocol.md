# Protocol for the single held out evaluation

This page fixes, before any held out outcome is read, what will be evaluated on the held out records, how, and what may and may not change afterwards. It serves guideline version 2 Stage 4 and decision D7 in `docs/decisions_log.md`.

The held out records are 782 pregnancies with 41 recorded low birth weight outcomes, set aside by `partitions/holdout_ids.csv` before any model was fitted. Until the run below, `partitions/holdout_access.log` does not exist and `python -m antenatal audit-holdout` reports every check as pass.

## 1. What is locked

| Role | Predictors | Directory | SHA 256 of `lbw_model.joblib` |
| --- | --- | --- | --- |
| Candidate, served (artefact 1.0.0) | Set C: registration, visit two and visit one values | `webapp/model/` | `7358b0b26f83aa6072f55986652d8691f111dbc6646a31a50ba46f94ff2d0c35` |
| Comparator for the primary comparison | Set B: registration and visit two values | `webapp/model/secondary_set_b/` | `f3a94ce3b2d86f59e2a8bf16e7ccaa5a99c92d51996dd08facb79d400ce9c9e0` |
| Comparator for the secondary comparison | Set A: registration values only | `webapp/model/comparator_set_a/` | `4189d65e5ee036157e39aa485f0ad196326337497e8ecfe9f482ef58bfabd47a` |

All three are the same configuration (logistic regression with an L2 penalty, the served model of Stage 2 outcome (c)) refitted on all 3,126 development records. None was fitted, tuned or chosen with any held out record. The classification threshold is the one in `webapp/model/classification.json` (0.0688, the top 20 percent of out of fold predictions on development records), saved with the candidate's checksum.

## 2. What is measured

Every interval is a 95 percent group bootstrap interval with 2,000 resamples that keeps registration groups together, using the study seed.

1. **Each model** (`outputs/tables/holdout_result.csv`): average precision, ROC AUC (the area under the receiver operating characteristic curve), Brier score and calibration measures.
2. **Primary comparison** (`outputs/tables/holdout_comparisons.csv`): average precision of C minus B, with its paired interval, bootstrap standard error, detectable difference and bootstrap p value. ROC AUC of C minus B is reported as descriptive.
3. **Secondary comparison**: ROC AUC of B minus A, with the same quantities. Average precision of B minus A is descriptive.
4. **The label** (`outputs/tables/holdout_classification.csv`): how many records the candidate labels "Likely low birth weight" at the fixed threshold, with sensitivity, specificity and the two predictive values, and the share of events retrieved in the top 10, 20 and 30 percent of the ranking.
5. **Net benefit** (`outputs/tables/holdout_net_benefit.csv`): the net benefit of acting on each locked model at every prespecified threshold from 0.03 to 0.12 and at the label's threshold, with its interval, beside acting for everyone. Net benefit counts true positives minus false positives weighted by the threshold's odds, per pregnancy.

A comparison counts as a finding only when its interval excludes zero. The two comparisons are prespecified, so no adjustment for multiple comparisons is applied to them; the descriptive rows are not tested.

## 3. What the held out records can detect

The detectable difference is the smallest true difference a two sided test at the 5 percent level finds with 80 percent power, 2.8 bootstrap standard errors (`src/antenatal/evaluation/power.py`). A bootstrap standard error shrinks roughly with the square root of the number of events, so with 41 events instead of 165 it is about the square root of 165 over 41, 2.006, times larger than on development records.

| Comparison | Detectable on development records (`outputs/tables/detectable_difference.csv`) | Expected on held out records |
| --- | --- | --- |
| C over B, average precision | 0.011 | about 0.022 |
| B over A, ROC AUC | 0.038 | about 0.077 |

The held out check is therefore less able to find a small difference than the development analysis. Its role is to confirm that the locked models behave on unseen records as the development analysis said, not to overturn the development estimate. The exact detectable difference is recomputed from the held out bootstrap and written in the comparisons table.

## 4. How it is run

Only after the supervisor's approval, by the author:

```
python scripts/run_holdout.py --approval "supervisor approved on 23 October, run the holdout on artefact 1.0.0" --operator NAME
```

The script refuses any other sentence. It verifies every checksum, loads the three locked models and the threshold, and calls `HoldoutEvaluator.evaluate_once` once. The access log records the operator, purpose, commit, model and data checksums and the results path. A second call is refused. `python -m antenatal audit-holdout` is run before and after, and both reports are committed with the log.

## 5. What does not change afterwards

* No model, predictor set, threshold, setting or artefact is changed because of the held out results. Artefact 1.0.0 stays served whatever they show.
* The results are reported as they are, including a comparison whose interval contains zero, and a result worse than on development records.
* Any later analysis that reads the held out records is labelled exploratory and cannot change a reported conclusion.
