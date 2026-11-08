# Fusion analysis: can the served model and the week 36 model be combined?

Written for the author, the supervisor and the panel. Plan: [PROTOCOL.md](PROTOCOL.md), committed before any result (commit b3a5a3b). Every number below comes from a file in [outputs/](outputs/). Nothing here changes the served model, the web application or the main study.

## 1. The answer

No combination separates low birth weight from other births better than the served model alone. The prespecified primary comparison, the stacked combination against the served model on average precision, gives a difference of +0.0003 (95 percent interval −0.0158 to +0.0146, p 0.946).

A combination can find more cases only by flagging many more pregnancies. The two check rule (option 3) found 22.6 more of the 165 cases than the served model, with 767.8 more false alarms: about 34 false alarms for each extra case.

The learned combination (option 4) looked better on ROC AUC and at a 75 percent target. That gain comes from a signal that is not available when the prediction is needed (Section 5), so option 4 must not be used as it stands.

## 2. What was compared

All four options were rebuilt inside the same nested cross validation: 5 repeats of 5 outer folds over the 3,126 development records of the main study (165 cases), with 5 inner folds inside each outer training set.

* **Option 1** is the served model: logistic regression with an L2 penalty on set C, fitted with the main study's own code.
* **Option 2** is the week 36 model: logistic regression with an L2 penalty on set B at week 36, fitted with this track's code.
* **Option 3** flags if option 1 or option 2 flags.
* **Option 4** is a small logistic regression that learns how to weight the two scores (stacking). It learns only from inner scores of outer training records, and its thresholds are fixed the same way.
* **Option 4b** is an exploratory average of the two scores with no learning.

The held out list was never opened, and no quarantined or test record was used.

Terms used below:

* **Cases found** (sensitivity): the share of low birth weight births flagged.
* **Specificity**: the share of other births not flagged.
* **Flag right rate** (positive predictive value): the share of flags that were real cases.
* **ROC AUC**: how often a case is ranked above a non case (0.5 is chance).
* **Average precision** (PR AUC): how pure the top of the list is, judged against the base rate.
* **Calibration slope**: 1 means the probabilities mean what they say.

Flag counts are averages over the 5 repeats, so they can carry a decimal. Intervals come from 2,000 paired resamples of whole registration groups.

## 3. Results on all 3,126 records (165 cases)

Source: `outputs/estimates.csv`

| Option | ROC AUC | Average precision (base 0.053) | Calibration slope | Cases found | False alarms | Sensitivity | Specificity | Flag right rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 served | 0.627 (0.582 to 0.671) | 0.088 (0.070 to 0.119) | 0.97 (0.60 to 1.34) | 56.2 | 564.4 | 34.1% (27.7 to 40.7) | 80.9% (79.6 to 82.2) | 9.1% |
| 2 week 36 | can score 1,620 only | | | 44.2 | 998.2 | 26.8% (19.9 to 33.6) | 66.3% (64.8 to 67.8) | 4.2% |
| 3 two checks | no score | | | 78.8 | 1,332.2 | 47.8% (40.6 to 54.6) | 55.0% (53.4 to 56.6) | 5.6% |
| 4 stacked, 20 percent flagged | 0.657 (0.614 to 0.697) | 0.088 (0.071 to 0.117) | 1.04 (0.72 to 1.39) | 60.4 | 574.2 | 36.6% (29.9 to 43.4) | 80.6% (79.4 to 81.9) | 9.5% |
| 4 stacked, 75 percent target | as above | | | 121.0 | 1,488.0 | 73.3% (67.0 to 79.2) | 49.8% (48.1 to 51.4) | 7.5% |
| 4b average | 0.648 (0.604 to 0.690) | 0.090 (0.072 to 0.120) | 1.08 (0.73 to 1.46) | 58.2 | 568.2 | 35.3% (29.0 to 41.9) | 80.8% (79.6 to 82.1) | 9.3% |

The rebuilt option 1 matches the main study's recorded values: average precision 0.089, ROC AUC 0.628, sensitivity 34.5 percent and specificity 80.8 percent. So the rebuild is faithful.

## 4. Prespecified comparisons

Source: `outputs/comparisons.csv`

| Role | Comparison | Difference (95 percent interval) | p |
| --- | --- | --- | --- |
| Primary | 4 over 1, average precision | +0.0003 (−0.0158 to +0.0146) | 0.946 |
| Secondary | 4 over 1, ROC AUC | +0.029 (−0.005 to +0.063) | 0.095 |
| Secondary | 4 over 1, sensitivity with 20 percent flagged | +2.6 points (−3.9 to +9.0) | 0.456 |
| Secondary | 3 over 1, sensitivity | +13.7 points (+8.8 to +18.7) | below 0.001 |
| Secondary | 3 over 1, specificity | −25.9 points (−27.4 to −24.5) | below 0.001 |
| Descriptive | 3 over 1, cases found | +22.6 (+14.2 to +31.8) | |
| Descriptive | 3 over 1, false alarms | +767.8 (+726.8 to +810.2) | |
| Exploratory | 4b over 1, average precision | +0.0017 (−0.0116 to +0.0128) | 0.702 |
| Exploratory | 4 over 1, calibration slope | +0.07 (−0.20 to +0.34) | 0.561 |

**Decision under the protocol.** A combination adds detectable value only if its gain in average precision has an interval that excludes zero. Option 4's interval runs from −0.0158 to +0.0146, so it does not add detectable value. Neither does option 4b. Option 3 finds more cases, but only by flagging 1,411 of 3,126 pregnancies instead of 621.

## 5. Why option 4 looks better than it is (post hoc, descriptive)

These checks were added after the results were seen. Source: `outputs/post_hoc.json` and `outputs/estimates.csv`.

1. Pregnancies **without** a usable visit in weeks 33 to 36 had a recorded low birth weight rate of 7.2 percent (109 of 1,506). Pregnancies with that visit had 3.5 percent. Part of the reason is that a baby born early cannot have a late visit.
2. The stacker learned this. For a typical week 36 score, having that visit lowers the log odds by 0.73.
3. With the 75 percent target, option 4 finds 121 cases, but only 19.6 of the 56 cases with a week 36 visit (35.0 percent). The rest come from flagging nearly everyone without such a visit.
4. Whether a woman will be seen at 33 to 36 weeks is not known at 28 weeks. Missing that visit partly reflects an early birth. This is the attendance leakage that this track's protocol bans, entering through the indicator of a week 36 score.
5. On the 1,620 records where both scores exist, so the attendance signal plays no part, option 4 does not beat option 1. The ROC AUC difference is −0.009 (−0.028 to +0.008).
6. With the same in sample cut off rule at 75 percent sensitivity, specificity is 38.1 percent for option 1, 49.3 percent for option 4 and 47.8 percent for option 4b. The gap for option 4 is explained by point 2, not by better use of the visit values.

So the protocol's option 4 had a design flaw that was not seen in advance. The primary result is unaffected, because it showed no gain anyway.

## 6. Results on the 1,620 records with a week 36 visit (56 cases)

| Option | ROC AUC | Average precision (base 0.035) | Sensitivity | Specificity |
| --- | --- | --- | --- | --- |
| 1 served, scored at 28 weeks | 0.658 (0.579 to 0.740) | 0.080 (0.051 to 0.140) | 38.9% | 83.9% |
| 2 week 36 | 0.616 (0.536 to 0.690) | 0.054 (0.037 to 0.087) | 78.9% | 36.2% |
| 3 two checks | | | 79.3% | 34.8% |
| 4 stacked | 0.649 (0.567 to 0.729) | 0.073 (0.047 to 0.126) | | |

Among women seen in both periods, the week 36 model did not rank better than the served model scored eight weeks earlier. The ROC AUC difference is −0.043 (−0.113 to +0.024), and the average precision difference is −0.027 (−0.075 to +0.001).

The week 36 model's higher sensitivity comes from its lower cut off, not from better separation.

## 7. Integrity checks

Source: `outputs/checks.json`, `outputs/stacker_weights.csv`, `outputs/reference_check.csv`

* **Counts:** they match the protocol: 3,126 records with 165 cases; 1,620 with 56 at week 36; 992 extra training records with 26 cases.
* **Excluded records:** no quarantined or test record was in either frame, and the training guard checked every option 1 fit.
* **Fold checks:** no registration group crossed any outer or inner split. Option 2's training records were checked against the outer and inner test groups each time.
* **Negative control:** with the outcome shuffled, ROC AUC was 0.480 for option 1 and 0.475 for option 4, near chance as expected.
* **Stacker weights:** across the 25 outer folds, the weight on the served score averaged 0.70 (0.21 to 1.08) and the weight on the week 36 score 0.21 (−0.24 to 0.84). The week 36 score gets little weight, and its weight is unstable.
* **Frozen threshold check:** option 3 built from the stored predictions with the frozen thresholds 0.0688 and 0.0294 found 76 cases against 57 for option 1, with 1,147 false alarms against 569. That is the same direction and size as the rebuilt version.

## 8. Limits

* **Internal validation only.** No untouched test set remains for a new combined rule, because the 782 held out records were opened once on 24 October 2026. The track's test set holds later bookers whom option 1 cannot score.
* **Option 2's threshold** is fixed on development scores, as in the track.
* **Few cases with both scores.** Only 56 cases have both scores, so intervals on the 1,620 records are wide.

## 9. What this means for the study

The served model stays as it is.

A second check at 36 weeks can raise the share of cases found from about a third to about a half. It costs about 34 false alarms per extra case, and almost half of all pregnancies get flagged. A learned combination adds no separation once the attendance signal is removed.

This agrees with the main study and the track: the limit is the information in routine visit records, shown here by testing every way of combining what the records hold.

Rerun: `python lbw_detection_track/fusion/run_fusion.py`, then `python lbw_detection_track/fusion/post_hoc.py`.
