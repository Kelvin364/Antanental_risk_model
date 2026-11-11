# Protocol: a sequential antenatal low birth weight prediction strategy

Status: **fixed on 11 November 2026, before any result of this analysis was computed.** Later changes are added at the end as dated amendments with their reason.

This analysis asks whether the week 36 model can be used as a supplementary second look at women whom the served model did not flag at 28 weeks, while the served model and its rule stay exactly as they are. It builds on the [fusion analysis](../fusion/REPORT.md), which tested four ways of combining the two models but never tested a second look restricted to women the first model cleared, with its own threshold chosen inside training.

Nothing here changes the served model, the web application, the main study or any sealed list. Neither `partitions/holdout_ids.csv` nor `lbw_detection_track/sealed/test_ids.csv` is opened.

## 1. Terms used

* **Baseline model:** the served model. It is an L2 penalised logistic regression (logistic regression whose coefficients are shrunk towards zero) on set C, using visits up to 28 weeks. Its original rule flags the highest 20 percent of training scores. The frozen artefact's threshold is 0.0688.
* **Late model:** the week 36 model of this track. It is an L2 penalised logistic regression on set B, using the latest visit in weeks 33 to 36 and registration fields. It can score only women with such a visit.
* **Reassessed:** a woman who has a usable visit in weeks 33 to 36. A woman who gave birth before then, or did not attend, cannot be reassessed and keeps her 28 week result.
* **Sequential strategy:** flag at 28 weeks with the baseline rule. Then, among women not flagged and reassessed, flag again if the late score passes a late threshold. Nobody is ever unflagged.
* **Updated late score:** a small logistic regression on the log odds of both scores, fitted only on reassessed training records. It has no term for whether a visit happened.
* **Workload matched baseline:** the baseline model alone, with its threshold lowered inside training so that it flags the same share of training records as the sequential strategy. It answers whether the late step does anything that simply flagging more women at 28 weeks would not.
* **Sensitivity:** the share of low birth weight births flagged. **Specificity:** the share of other births not flagged. **PPV (positive predictive value):** the share of flags that are low birth weight births. **NPV (negative predictive value):** the share of unflagged women whose baby was not low birth weight.

## 2. Records

* All 3,126 development records of the main study (165 low birth weight births), the same frame as the fusion analysis. Every strategy is judged on these same records, whether or not the woman was reassessed.
* The late model trains on this track's development pool, as in the fusion analysis, with every record of an outer test registration group removed.
* Quarantined and test records are refused by the training guard.

## 3. Validation

* The outer and inner folds, the seed (20261108), and the fitting of both models are exactly those of the fusion analysis (`fusion/nested.py`): 5 repeats of 5 outer folds, grouped by registration group and stratified by outcome, with 5 inner folds.
* **Every threshold and the updated late score are learnt from inner out of fold scores of outer training records only.** Outer test records never contribute.
* **Check:** for every repeat, fold and record, the rebuilt baseline score must equal the score stored by the fusion analysis to within 1e-9. If not, the analysis stops.

## 4. Thresholds learnt in training

From the inner scores of the outer training records:

1. Baseline threshold: the served rule, flagging the top 20 percent.
2. Late threshold at each **reassessment specificity** target of 95, 90, 85 and 80 percent. The threshold flags that share of non cases among reassessed training records that the baseline did not flag.
3. The same four targets for the updated late score.
4. The late model's own rule from the track (75 percent sensitivity among reassessed training records), as the fusion analysis's "two checks" reference.
5. For each target, the workload matched baseline threshold: the top share of baseline scores equal to the training share flagged by the sequential strategy.

## 5. Strategies compared, on the same 3,126 records

* Baseline alone, original rule.
* Late model alone: its own rule, and each specificity target applied to every reassessed woman.
* Sequential strategy with the late model at each target, and with the track's own late rule (the fusion analysis's two checks).
* Sequential strategy with the updated late score at each target.
* Workload matched baseline at each target.

Scores and flags are averaged over the 5 repeats per record. Intervals come from 2,000 paired resamples of whole registration groups (seed 20261111), so every strategy is compared on the same resampled records.

## 6. Measures

* **For every strategy, on all 3,126 records and on the 1,620 reassessed:** cases found, false alarms, sensitivity, specificity, PPV, NPV, and flags per 1,000 pregnancies.
* **For each score:** ROC AUC, average precision, Brier score, calibration slope, calibration intercept and the ratio of observed to expected events.
  * The baseline is scored on all records and on reassessed records.
  * Both late scores are scored on reassessed records.
  * The late model is also scored against the baseline on reassessed records the baseline did not flag in a majority of repeats. This is the group where the late step acts.
* **Case overlap** for each late rule: cases flagged by both models, by the baseline only, by the late model only, and by neither. The same is reported for false alarms.
* **Workload:** extra flags at 36 weeks per 1,000 pregnancies, and extra false alarms per extra case found.
* **Attendance accounting:**
  * cases and records by whether they were reassessed and by recorded preterm birth;
  * the number of baseline missed cases that could be reassessed at all. This is the most the late step could ever add.

A sequential strategy has no single score, so it gets no ROC AUC. Its components do.

## 7. Prespecified comparisons and decision rule

**Primary:** the sequential strategy at the 90 percent target, against

* (a) the baseline alone: difference in sensitivity;
* (b) the workload matched baseline at 90 percent: difference in sensitivity.

**Secondary:**

* the same two comparisons at the 95, 85 and 80 percent targets;
* the updated late score against the late model in the sequential strategy, at each target;
* the difference in specificity of each sequential strategy against the baseline;
* on reassessed records the baseline did not flag, the difference in ROC AUC of the late model and of the updated late score against the baseline score.

**The late model is said to add useful information only if, at the 90 percent target, all four hold:**

1. the interval for (a) lies above zero;
2. the interval for (b) lies above zero;
3. extra false alarms per extra case found is no more than the baseline's own false alarms per case found;
4. specificity falls by no more than 5 percentage points.

If 1 holds but 2 does not, the late step finds more cases only by flagging more women, and lowering the baseline threshold would find at least as many cases, earlier. No result at the other targets can overturn the primary decision. Those results are reported to show the trade off.

## 8. What can and cannot be concluded

* Internal validation only, as in the fusion analysis. Both sealed sets have already had their single evaluation. A strategy that passes Section 7 still needs a new prospective or external test before any use.
* The strategy outputs a flag and the probabilities behind it. No risk category, priority label or triage wording is used.
* No class weighting, oversampling, undersampling or synthetic records.

## Amendments

None yet.
