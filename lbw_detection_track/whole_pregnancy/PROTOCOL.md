# Protocol: does the week 36 model gain from every visit up to 36 weeks?

Status: **fixed on 11 November 2026, before any result of this analysis was computed.** Later changes are added at the end as dated amendments with their reason.

## 1. Why

The locked week 36 model (set B) uses the registration form and **only the latest visit in weeks 33 to 36**. Set C adds the first visit and weight gain per week between the two. Visits in between are never used. This analysis asks whether a summary of every visit recorded up to 36 weeks ranks and flags low birth weight better.

Nothing here changes the served model, the locked week 36 model, the web application or the main study. Only this track's development pool is read. The test list and the quarantine list are read only to check that none of their records is present. The test set has already had its single evaluation and is not opened.

## 2. Population

**Primary (P1):** the 2,612 development pool records (82 low birth weight births) with a usable visit in weeks 33 to 36. This is the same population the week 36 model was built on, so all sets are compared on the same women. These women are known to be pregnant at 33 weeks or later.

**Descriptive check only (P2):** every development pool record with any visit at or before 36 weeks, using the latest visit whenever it happened. This shows why women without a late visit cannot simply be added. A woman who gave birth early stops attending, so the week of her last visit carries the outcome. P2 is reported as a leakage demonstration, never as a performance result.

## 3. Predictor sets

* **B:** the locked set. Registration fields plus the latest visit in weeks 33 to 36: systolic and diastolic blood pressure, weight, gestational age, pulse and haemoglobin.
* **C:** B plus the first visit's values and weight gain per week.
* **H (whole pregnancy):** C plus, for each of the five measurements, the mean, lowest, highest and slope per week over every visit at or before 36 weeks. Also the number of visits at or before 36 weeks, any haemoglobin below 11 g/dL, and any positive malaria test, all at or before 36 weeks.

Only visits whose recorded week is at or before 36 are used. No delivery field, banned field, total visit count or later visit is read. The track's banned list check in `features.load_raw` applies.

## 4. Models and validation

* L2 penalised logistic regression (the track's `Logistic`, penalty tuned on grouped inner folds) and gradient boosted trees (the track's fixed `Trees` settings).
* 5 repeats of 5 outer folds, grouped by registration group and stratified by outcome, with the track's seed (20261107).
* **Thresholds are chosen inside each outer training fold** from inner out of fold scores (5 grouped inner folds). Two rules are used:
  * the track's rule of 75 percent sensitivity;
  * 90 percent specificity.
* Scores and flags are averaged over repeats per record.
* No class weighting, oversampling, undersampling or synthetic records.

## 5. Measures and comparisons

* For each set and model: ROC AUC, average precision and calibration slope, plus sensitivity, specificity, PPV and NPV at both thresholds. Each comes with a 95 percent interval from 2,000 resamples of whole registration groups (seed 20261111).
* **Primary comparison:** logistic H against logistic B, difference in ROC AUC, paired over the same resamples.
* **Secondary comparisons:** H against C and C against B for logistic; boosting H against logistic B; and differences in sensitivity at 90 percent specificity.
* H is said to improve on B only if the primary interval lies above zero.
* **P2 check:** ROC AUC of the week of the latest visit alone and of the number of visits alone, and out of fold ROC AUC of logistic set B built from the latest visit at any time.

## 6. Limits fixed in advance

Internal validation only, because no untouched test set remains. H has many more inputs than B for 82 events, so overfitting is expected to cancel some gain. The penalty and the cross validation measure this rather than hide it.

## Amendments

None yet.
