# Fusion analysis protocol: four options compared on the same records

Written and committed before any fusion result was computed. The only facts known when it was written are counts of records and events, given in Section 2. Nothing here changes the served model, the web application or the main study.

## 1. Question

Can the served model, which checks a pregnancy at its second visit by 28 weeks, and the week 36 model of this track be combined so that more recorded low birth weight cases are found, and does a learned combination separate cases from non cases better than the served model alone?

Four options are compared:

| Option | What it is |
| --- | --- |
| 1 | The served model alone: logistic regression with an L2 penalty on set C of the main study (registration, second visit and first visit values), checked at the second visit |
| 2 | The week 36 model alone: logistic regression with an L2 penalty on set B of this track (registration and the latest visit in weeks 33 to 36). It can score only pregnancies with a usable visit in that window |
| 3 | A two check rule: flag if option 1 flags, or if option 2 flags. No new fitting |
| 4 | A learned combination (stacking): a small logistic regression that takes the two scores as its inputs and learns how much weight each deserves |

A secondary, exploratory version of option 4 with no learning is also reported: the average of the two scores on the log odds scale where both exist, and the option 1 score where only it exists. It answers whether learning the weights was needed.

## 2. Records

The 3,126 development records of the main study, 165 with recorded low birth weight. They are identified by the record ids in `outputs/oof_predictions.parquet`; the held out list `partitions/holdout_ids.csv` is never opened. Of these, 1,620 records (56 events) have a usable visit in weeks 33 to 36 and so have an option 2 score. The other 1,506 records (109 events) can be checked by option 1 only.

Option 2 is also trained on the 992 further records of this track's development pool that have a usable visit in weeks 33 to 36 but are outside the main study cohort (26 events), so that it is not weaker than in the track. These records are used for training only and are never scored.

Never used anywhere: the 783 quarantined records and the 2,121 records of this track's test set. Both lists are read only to assert that none of their records is present.

## 3. Procedure: nested cross validation for all four options

All four options are rebuilt inside the same folds, so they are compared on the same records with the same information. The stored predictions are not reused for the main comparison.

1. **Outer folds.** 5 repeats of 5 folds over the 3,126 records, stratified by outcome and grouped by registration group, seed 20261108.
2. **For each outer fold**, using the outer training records only:
   1. Option 1 is fitted with the main study's own code (`NestedCVRunner.fit`, logistic L2, set C, penalty tuned on inner grouped folds by average precision).
   2. Option 2 is fitted with this track's code (`methods.Logistic`, set B at week 36) on the outer training records that have a week 36 visit plus the extra training records of Section 2, after removing any record whose registration group appears in the outer test fold.
   3. Inner folds: 5 grouped folds over the outer training records. In each, both base models are refitted without the inner test records, and the inner test records are scored. This gives every outer training record an honest score from each base model.
   4. Option 4 is fitted on those inner scores only. Its inputs are the log odds of the option 1 score, an indicator that an option 2 score exists, and the log odds of the option 2 score where it exists (zero otherwise). It is an unpenalised logistic regression with these three inputs and an intercept.
   5. Thresholds are fixed from the inner scores of the outer training records only:
      * option 1 and option 4: the score that marks the highest 20 percent, the rule of the served model;
      * option 4 also at a second point: the highest score at which at least 75 percent of events are flagged;
      * option 2: the highest score at which at least 75 percent of events with a week 36 visit are flagged, the rule of this track.
3. **The outer test fold** is then scored by all options with the base models refitted on the whole outer training set, and flagged with the thresholds of step 2.5.

## 4. Measures

On all 3,126 records:

* **Ranking** (options 1 and 4, and the exploratory average): ROC AUC, average precision (PR AUC) against the base rate, Brier score, calibration slope. Each record's score is the mean over the 5 repeats.
* **Flags** (all options): cases found, false alarms, sensitivity, specificity, positive predictive value, negative predictive value. Each record's flag is the share of the 5 repeats in which it was flagged, so counts are averages over repeats.
* **Option 3 against option 1**: extra cases found, extra false alarms, and extra false alarms per extra case.

On the 1,620 records with a week 36 visit, the same measures are reported for options 1, 2 and 4, because only there can option 2 be judged.

Intervals: 2,000 resamples of whole registration groups, seed 20261108, paired so that options are compared on the same resampled records. Percentile 95 percent intervals; two sided p value as twice the share of resampled differences on the other side of zero.

## 5. Prespecified comparisons and decision

* **Primary.** Option 4 over option 1, average precision, on all 3,126 records.
* **Secondary.** Option 4 over option 1, ROC AUC; option 4 over option 1, sensitivity at the 20 percent flag rate; option 3 over option 1, sensitivity and specificity.

A combination is said to **add detectable value** only if the interval of its gain in average precision excludes zero and its calibration slope interval contains 1. Option 3 has no score, so it is judged only on the trade between extra cases and extra false alarms, and no claim of better separation can be made for it.

Whatever the result, it is reported in `REPORT.md` in this folder. This is internal validation on development records: no untouched test set remains for a new combined rule, because the 782 held out records were opened once on 24 October 2026 and the track's test set holds later bookers whom option 1 cannot score.

## 6. Leakage checks at every stage

1. Every training frame is checked against the quarantine and test lists.
2. Every outer and inner split is checked so that no registration group sits on both sides.
3. Option 2's extra training records are checked against the outer and inner test groups.
4. Option 4 and every threshold learn from inner scores of outer training records only.
5. A negative control: the whole procedure is run once more, one repeat, with the outcome randomly shuffled within the training records. Its ROC AUC should be near 0.5; a value above 0.60 stops the analysis as a sign of leakage.
6. A reference check: option 3 is also computed from the stored predictions with the frozen thresholds 0.0688 and 0.0294, as a secondary comparison with the rebuilt version.
