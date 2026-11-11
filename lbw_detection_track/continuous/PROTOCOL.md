# Protocol: predict the birth weight, then rank by it

Status: **fixed on 11 November 2026, before any result of this analysis was computed.** Later changes are added at the end as dated amendments.

## 1. Why

Every model so far learns from a yes or no label: below 2.5 kg or not. Only the 82 to 165 low birth weight births carry the signal, so the model sees few examples. Cutting a measured quantity into two groups is known to throw information away. A model of the birth weight itself learns from every birth, including the difference between a 2.6 kg and a 3.6 kg baby. Women are then ranked by predicted birth weight, lowest first, and judged on the same outcome, recorded low birth weight.

The birth weight is an outcome. It is used only as the training target, never as a predictor. Only the track's development pool is read. The track test set and the quarantine list are not opened, and no served or locked model changes.

## 2. Design

* **Populations:** the track's landmarks 28 and 36 weeks over the development pool (2,989 records with 141 cases, and 2,612 with 82), as in `follow_up`.
* **Inputs:** the track's sets B and D.
* **Training target:** recorded birth weight in kilograms, limited to the range 0.5 to 5.5 kg so that a few typing errors cannot dominate the squared error.
* **Regression methods:**
  * `ridge`: median imputation with missing indicators, scaling, and ridge regression with the penalty chosen by internal cross validation within the training fold;
  * `boosting_reg`: gradient boosted trees with the track's fixed classifier settings, squared error loss;
  * `quantile_reg`: the same trees fitted to the 10th percentile of birth weight, so the model aims at the lower tail.
* **Score:** minus the predicted birth weight, so a higher score means a smaller expected baby.
* **Validation:** exactly the splits of `run_experiments.out_of_fold`: 5 repeats of 5 folds grouped by registration group, stratified by low birth weight, seed 20261107. Scores are averaged over repeats.
* **Comparators:** the classifiers on the same splits, read from `follow_up/outputs/predictions.parquet` (population "full").

## 3. Measures and comparisons

* ROC AUC and average precision for each configuration, each with a 95 percent interval from 2,000 resamples of registration groups (seed 20261111).
* **Primary comparison:** `boosting_reg` against the `boosting` classifier, set D, landmark 28, the difference in ROC AUC paired over the same resamples.
* **Secondary comparisons:**
  * `ridge` against the `logistic` classifier;
  * `quantile_reg` against `boosting`.
  * Each is made for both sets at both landmarks, and the primary pair also at the other three combinations.
* The weight model is said to improve ranking only if the primary interval lies above zero. Secondary results are reported as estimates, not claims.

## Amendments

None yet.
