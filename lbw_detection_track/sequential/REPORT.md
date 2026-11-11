# Sequential strategy: does a second look at 36 weeks add to the served model?

Written for the author, the supervisor and the panel. Plan: [PROTOCOL.md](PROTOCOL.md), committed before any result (commit d670883). Every number below comes from a file in [outputs/](outputs/). Nothing here changes the served model, its threshold, the web application, the main study or any sealed list.

## 1. The answer

**No. The week 36 model does not add useful information to the served model, under the rule fixed in advance.**

* The sequential strategy at the primary target finds 5.4 more of the 165 cases than the served model alone (2.2 to 9.2). It pays 129.8 extra false alarms, about 24 for each extra case.
* Lowering the served model's own threshold, so that it flags the same number of women at 28 weeks, finds 9.4 extra cases for 125.8 extra false alarms, about 13 for each extra case.
* The difference in sensitivity between the sequential strategy and that workload matched baseline is −2.4 points (−5.1 to +0.3). At every target the sequential strategy found fewer cases than the matched baseline, and at the 80 percent target the interval excludes zero.
* Among women the served model did not flag and who were seen at 33 to 36 weeks, the week 36 model ranks cases barely above chance. Its ROC AUC there is 0.586 (0.473 to 0.688), against 0.575 for the served score.

So a second look finds extra cases only because it flags more women, not because the week 36 visit carries new information. If more cases must be found, lowering the served model's threshold at 28 weeks does it better, and earlier.

## 2. A note on the figure of 0.703

The brief describes the baseline as having ROC AUC of about 0.703. **No baseline model in this repository has that value on development records.**

* The served model's development ROC AUC is 0.628 (0.584 to 0.675), from `outputs/tables/model_performance.csv`. Its single held out evaluation gave 0.572 (0.475 to 0.672) on 782 records.
* The nearest figure is 0.706 (0.624 to 0.781). That is the **week 36 model's** single evaluation on this track's test set, which holds 29 cases (`lbw_detection_track/outputs/test_results.csv`).
* In development, the week 36 model ranked worse than the served model on the women who had both scores.

This analysis therefore uses the served model as the baseline. It is the model in service, it has an original threshold to preserve, and its development figures are reproduced exactly below. The source of 0.703 should be checked before it is quoted.

## 3. What was done

* **Records:** the 3,126 development records of the main study (165 low birth weight births). Every strategy is judged on all of them, whether or not the woman was seen late in pregnancy.
* **Baseline:** the served model, rebuilt inside the fusion analysis's folds with its original rule: flag the top 20 percent of training scores.
* **Late model:** this track's week 36 model, an L2 penalised logistic regression (shrunk coefficients) on set B. It uses only registration fields and the latest visit in weeks 33 to 36.
  * It never sees a delivery field, total visits or any later visit.
  * Its banned field list is in `lbw_detection_track/features.py`.
* **Reassessed:** a woman with a usable visit in weeks 33 to 36. That is 1,620 records with 56 cases. A woman who gave birth before then, or did not attend, keeps her 28 week result.
* **Sequential strategy:** flag at 28 weeks with the served rule. Then flag again any woman not yet flagged, if she is reassessed and her week 36 score passes a late threshold. Nobody is unflagged.
* **Late thresholds:** set for a target specificity among reassessed training women the served model had not flagged. The targets are 95, 90 (primary), 85 and 80 percent.
* **Updated late score:** a logistic regression on the log odds of both scores, fitted on reassessed training records, with no term for attendance.
* **Workload matched baseline:** the served model alone with its threshold lowered, inside training, to flag the same share of women as the sequential strategy.
* **Validation:**
  * 5 repeats of 5 outer folds, grouped by registration group and stratified by outcome, with 5 inner folds.
  * **Every threshold and the updated score were learnt from inner out of fold scores of outer training records only.**
  * Intervals are 95 percent percentile intervals from 2,000 paired resamples of whole registration groups.
  * Counts are averages over the 5 repeats, so they can carry a decimal.

Terms used:

* **Sensitivity:** the share of low birth weight births flagged.
* **Specificity:** the share of other births not flagged.
* **PPV (positive predictive value):** the share of flags that were low birth weight.
* **NPV (negative predictive value):** the share of unflagged women whose baby was not low birth weight.
* **ROC AUC:** how often a case is ranked above a non case, where 0.5 is chance.
* **Average precision:** how pure the top of the ranking is.
* **Calibration slope:** 1 means predictions are neither too extreme nor too timid.
* **Calibration intercept:** 0 means predictions are right on average.
* **Observed to expected ratio:** observed cases divided by the sum of predicted probabilities.

## 4. Baseline reproduction

Source: `outputs/baseline_reproduction.json`, `outputs/checks.json`.

| Version of the served model | ROC AUC | Cases found | False alarms | Sensitivity | Specificity |
| --- | --- | --- | --- | --- | --- |
| Main study record | 0.628 (0.584 to 0.675) | | | | |
| Stored out of fold scores at the frozen threshold 0.0688 | | 57 | 569 | 34.5% | 80.8% |
| This rebuild, threshold learnt per fold | 0.627 (0.583 to 0.672) | 56.2 | 564.4 | 34.1% (27.5 to 40.8) | 80.9% (79.7 to 82.1) |

Every rebuilt score equals the score stored by the fusion analysis. The largest gap is 0.0 for both models, and every baseline flag is the same. Thresholds learnt per fold averaged 0.0690 (0.0655 to 0.0731 across the 25 folds), against the frozen 0.0688. The baseline is preserved as the reference.

Baseline calibration on all records is good: slope 0.97 (0.60 to 1.35), intercept 0.00 (−0.16 to 0.16), and observed to expected 1.00 (0.86 to 1.16).

## 5. Deliverable 1: comparison of strategies

All 3,126 records, 165 cases. Source: `outputs/estimates.csv`.

| Strategy | Cases found | False alarms | Sensitivity | Specificity | PPV | NPV | Flags per 1,000 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Baseline, original rule | 56.2 | 564.4 | 34.1% (27.5 to 40.8) | 80.9% (79.7 to 82.1) | 9.1% (7.1 to 11.2) | 95.7% (94.8 to 96.4) | 198.5 |
| Late model alone, 90 percent target | 13.4 | 234.2 | 8.1% (4.6 to 12.1) | 92.1% (91.3 to 92.9) | 5.4% (3.0 to 8.0) | 94.7% (93.9 to 95.5) | 79.2 |
| Late model alone, track rule | 44.2 | 998.2 | 26.8% (20.3 to 33.6) | 66.3% (64.8 to 67.9) | 4.2% (3.1 to 5.5) | 94.2% (93.2 to 95.2) | 333.5 |
| **Sequential, 90 percent target** | 61.6 | 694.2 | 37.3% (30.8 to 43.9) | 76.6% (75.2 to 77.8) | 8.2% (6.4 to 10.0) | 95.6% (94.8 to 96.4) | 241.8 |
| Sequential with updated late score, 90 percent | 59.6 | 694.2 | 36.1% (29.8 to 42.9) | 76.6% (75.2 to 77.8) | 7.9% (6.2 to 9.8) | 95.6% (94.7 to 96.3) | 241.1 |
| **Workload matched baseline, 90 percent** | 65.6 | 690.2 | 39.8% (33.2 to 46.6) | 76.7% (75.3 to 78.0) | 8.7% (6.9 to 10.6) | 95.8% (95.0 to 96.6) | 241.8 |
| Sequential, track rule (the fusion analysis's two checks) | 78.8 | 1,332.2 | 47.8% (40.9 to 54.9) | 55.0% (53.5 to 56.6) | 5.6% (4.5 to 6.7) | 95.0% (94.0 to 96.0) | 451.4 |

A sequential strategy has no single score, so it has no ROC AUC. Its two scores are compared in Section 9.

### Every target

| Late target | Sequential cases found | Sequential false alarms | Matched baseline cases found | Matched baseline false alarms | Sensitivity, sequential minus matched |
| --- | --- | --- | --- | --- | --- |
| 95 percent | 59.0 | 631.0 | 61.2 | 627.0 | −1.3 points (−2.9 to +0.3) |
| 90 percent | 61.6 | 694.2 | 65.6 | 690.2 | −2.4 points (−5.1 to +0.3) |
| 85 percent | 63.8 | 753.4 | 69.2 | 755.8 | −3.3 points (−7.0 to +0.4) |
| 80 percent | 66.4 | 825.8 | 73.8 | 815.2 | −4.5 points (−8.6 to −0.3) |

Source: `outputs/comparisons.csv`. At the same workload, the late step never found as many cases as the served model with a lower threshold.

Using the updated late score instead of the week 36 score alone did not help at any target. At 90 percent the difference was −1.2 points (−3.1 to +0.5). In the updated score, the weight on the week 36 score averaged 0.08 (−0.34 to 0.71 across folds), against 0.96 on the served score (`outputs/fold_rules.csv`).

## 6. Deliverable 2: case overlap

Of the 165 cases, which ones each model flags. The late model applies each threshold to every reassessed woman. "Late only" cases are exactly the extra cases the sequential strategy adds. Source: `outputs/estimates.csv`, strategies `overlap_*`.

| Late rule | Both models | Baseline only | Late model only (unique extra cases) | Neither |
| --- | --- | --- | --- | --- |
| 95 percent target | 4.6 | 51.6 | 2.8 (1.0 to 5.0) | 106.0 |
| **90 percent target** | 8.0 | 48.2 | **5.4 (2.2 to 9.2)** | 103.4 |
| 85 percent target | 10.0 | 46.2 | 7.6 (3.4 to 12.4) | 101.2 |
| 80 percent target | 11.6 | 44.6 | 10.2 (5.0 to 16.0) | 98.6 |
| Track rule, 75 percent sensitivity | 21.6 | 34.6 | 22.6 (14.4 to 31.4) | 86.2 |

### Why the late model can add so few cases

Source: `outputs/attendance.csv`.

| Seen at 33 to 36 weeks | Recorded preterm birth | Records | Cases | Cases the baseline missed |
| --- | --- | --- | --- | --- |
| Yes | Yes | 47 | 13 | 7 |
| Yes | No | 1,573 | 43 | 28 |
| No | Yes | 72 | 53 | 38 |
| No | No | 1,434 | 56 | 38 |

* The baseline missed 111 cases in most repeats.
* Only 35 of them were seen at 33 to 36 weeks, so **35 is the most any week 36 step could ever add.**
* The other 76 were never seen late in pregnancy. Half of them were recorded preterm births, who cannot attend a visit after they are born.
* The cases most in need of a second chance are the ones a later visit cannot reach.

## 7. Deliverable 3: additional false alarms and workload

All 3,126 records. Source: `outputs/estimates.csv`.

| Strategy | Extra cases | Extra false alarms | Extra flags per 1,000 pregnancies | Extra cases per 1,000 | Extra false alarms per 1,000 | False alarms per extra case |
| --- | --- | --- | --- | --- | --- | --- |
| Sequential, 95 percent | 2.8 | 66.6 | 22.2 | 0.9 | 21.3 | 23.8 (12.8 to 68.0) |
| **Sequential, 90 percent** | 5.4 | 129.8 | 43.3 | 1.7 | 41.5 | **24.0 (14.1 to 59.4)** |
| Sequential, 85 percent | 7.6 | 189.0 | 62.9 | 2.4 | 60.5 | 24.9 (15.1 to 56.2) |
| Sequential, 80 percent | 10.2 | 261.4 | 86.9 | 3.3 | 83.6 | 25.6 (16.0 to 52.0) |
| Sequential, track rule | 22.6 | 767.8 | 252.8 | 7.2 | 245.6 | 34.0 (24.1 to 54.0) |
| **Workload matched baseline, 90 percent** | 9.4 | 125.8 | 43.3 | 3.0 | 40.2 | **13.4 (9.3 to 21.3)** |
| Workload matched baseline, 80 percent | 17.6 | 250.8 | 85.9 | 5.6 | 80.2 | 14.3 (10.6 to 20.4) |

For comparison, the served model's own flags carry 10.0 false alarms per case found (8.0 to 13.1).

In practice, at the primary target:

* The second look adds about 43 flags per 1,000 pregnancies. About 42 of them are false alarms, and about 2 are real cases.
* Every reassessed woman's score is computed at 36 weeks, but only the flagged women create review work.
* Lowering the 28 week threshold creates the same review work, finds about 3 cases per 1,000, and finds them eight weeks earlier.

## 8. Deliverable 4: recommendation

Decision rule of protocol Section 7, at the 90 percent target (`outputs/decision.json`):

| Condition | Result | Met |
| --- | --- | --- |
| 1. Gain over the baseline, interval above zero | +3.3 points (+1.4 to +5.3) | Yes |
| 2. Gain over the workload matched baseline, interval above zero | −2.4 points (−5.1 to +0.3) | **No** |
| 3. False alarms per extra case no more than the baseline's 10.0 | 24.0 | **No** |
| 4. Specificity falls by no more than 5 points | falls 4.4 points | Yes |

**The week 36 model does not add useful information to the served model.**

* **Keep the served model and its frozen threshold unchanged.** Every strategy here preserved it as the first step, and none improved on it except by flagging more women.
* **Do not add the week 36 model as a supplementary step.** It finds extra cases only by adding flags, and fewer cases per flag than the served model.
* **If clinicians want more cases found and can accept more reviews,** lower the served model's threshold. At 43 extra flags per 1,000 pregnancies, that finds about 9.4 extra cases instead of 5.4, at 28 weeks instead of 36. This changes the served rule, so it would be a new model version with its own validation, and the frozen artefact stays as it is.
* **A later assessment is worth building only around information that is new at 36 weeks** and absent from this file: numeric fundal height, an ultrasound estimate of fetal weight, and accurate gestational age. The [clinical redesign](../clinical_redesign/REPORT.md) sets out how to collect them.

## 9. How well each score separates cases

Source: `outputs/estimates.csv` and `outputs/comparisons.csv`.

| Score | Records (cases) | ROC AUC | Average precision | Calibration slope | Calibration intercept | Observed to expected |
| --- | --- | --- | --- | --- | --- | --- |
| Baseline, all records | 3,126 (165) | 0.627 (0.583 to 0.672) | 0.088 | 0.97 (0.60 to 1.35) | 0.00 (−0.16 to 0.16) | 1.00 (0.86 to 1.16) |
| Baseline, reassessed | 1,620 (56) | 0.658 (0.578 to 0.737) | 0.080 | 1.17 (0.51 to 1.88) | −0.40 (−0.68 to −0.16) | 0.68 (0.52 to 0.86) |
| Late model, reassessed | 1,620 (56) | 0.616 (0.537 to 0.685) | 0.054 | 0.79 (0.19 to 1.38) | 0.10 (−0.19 to 0.34) | 1.10 (0.83 to 1.38) |
| Updated late score, reassessed | 1,620 (56) | 0.641 (0.562 to 0.721) | 0.076 | 0.98 (0.32 to 1.67) | −0.01 (−0.29 to 0.22) | 0.99 (0.76 to 1.24) |
| Baseline, reassessed and not flagged | 1,357 (35) | 0.575 (0.475 to 0.678) | 0.041 | 0.46 | −0.53 | 0.60 (0.42 to 0.80) |
| Late model, reassessed and not flagged | 1,357 (35) | 0.586 (0.473 to 0.688) | 0.043 | 0.61 | −0.12 | 0.89 (0.63 to 1.19) |
| Updated late score, reassessed and not flagged | 1,357 (35) | 0.550 (0.447 to 0.654) | 0.036 | 0.20 | −0.14 | 0.87 (0.62 to 1.16) |

Paired differences in ROC AUC against the baseline score:

| Population | Late model minus baseline | Updated score minus baseline |
| --- | --- | --- |
| Reassessed, not flagged by the baseline | +0.011 (−0.077 to +0.101) | −0.025 (−0.049 to −0.004) |
| All reassessed | −0.043 (−0.112 to +0.025) | −0.017 (−0.029 to −0.005) |

The late model's best chance to add information is among women the baseline cleared, and there its ROC AUC interval includes 0.5. "Reassessed and not flagged" means not flagged in a majority of the 5 repeats.

The baseline over predicts among reassessed women (observed to expected 0.68), because women seen late in pregnancy have a lower recorded rate: 3.5 percent against 7.2 percent for those not seen. Its slope interval among those not flagged is very wide. Calibration slopes on that group are reported without intervals in the table because the intervals run across zero; they are in `outputs/estimates.csv`.

### The late model on its own

Among the 1,620 reassessed women:

* At the track's own rule it found 78.9 percent of cases (68.4 to 88.0) with specificity 36.2 percent (34.2 to 38.2).
* At the 90 percent target it found 23.9 percent (14.5 to 33.3) with specificity 85.0 percent (83.6 to 86.4).
* On this track's test set its ROC AUC was 0.706 (0.624 to 0.781), on 29 cases. That set holds later bookers whom the served model cannot score, so it says nothing about the sequential question.

## 10. Deliverable 5: proposed sequential architecture

The structure below is what a supplementary late step must look like. It is offered for future data, not for the late model tested here, which failed condition 2.

```
28 weeks   Served model, frozen threshold  ──>  flagged: stays flagged
                     │
                  not flagged
                     │
33 to 36 weeks   seen?  ── no ──>  keeps the 28 week result (counted, never dropped)
                     │
                    yes
                     │
             Late score, using only data recorded by that visit,
             threshold locked in training at a capacity based specificity
                     │
             passes ──>  flagged at 36 weeks          fails ──>  not flagged
```

Rules the architecture must keep:

1. **The first step never changes.** The served model and threshold 0.0688 stay as they are. The late step can only add flags and never removes one.
2. **The late step acts only on women not flagged at 28 weeks who are still pregnant and seen.** Its threshold is set for those women, not for everyone.
3. **No future information at either step.** Whether a later visit happens is never a predictor. It only decides whether the second look takes place. The fusion analysis showed how a term for attendance leaks the outcome.
4. **Judged on everyone eligible at 28 weeks,** including women who give birth or stop attending before the second look.
5. **Compared against a workload matched baseline,** so a second step earns its place only by finding more cases at the same review cost.
6. **The late score should be fitted for the women it will see:** conditional on the baseline score, among those the baseline cleared, using predictors new at 36 weeks.
7. **Thresholds, the late model and the decision rule are locked before a new test set is opened.** No flag is labelled with a category, priority or triage band. The output is a probability and whether it passed a locked threshold.

## 11. Deliverable 6: limitations

* **Missing data.**
  * The late model uses whatever the latest visit in weeks 33 to 36 recorded.
  * In the whole file, haemoglobin is numeric at visit two in only 34.4 percent of records (`clinical_redesign/outputs/field_audit.json`), and later visits are sparser still.
  * Fundal height is never numeric.
  * Missing values are handled as in the track's model and were not imputed again here.
* **Late visit attendance bias.**
  * The 1,620 reassessed women are a selected group. Their recorded rate of low birth weight is half that of women not seen (3.5 against 7.2 percent, `fusion/outputs/post_hoc.json`).
  * A baby born early cannot have a late visit.
  * All comparisons were made on all 3,126 records, so this selection cannot flatter the sequential strategy. It does, however, cap what any late step can do.
* **Births before the second look.** The file has no reliable delivery date. Recorded preterm birth is the only marker, and it is noisy: 47 records are flagged both preterm and term (`clinical_redesign/outputs/outcome_quality.json`). The attendance table is therefore approximate.
* **Validation.**
  * Internal validation only.
  * Both sealed sets have already had their single evaluation (24 October and 7 November 2026), so no untouched set remains for this question.
  * The late model trains on this track's development pool, which includes 992 extra later bookers. Their records never sit in an outer test group, as checked by the fusion code.
* **Few cases.** Only 35 cases could ever be reached by the late step. Every difference in this report is built on that small number, so the intervals are wide.
* **Thresholds averaged over repeats.** Counts are averages over 5 repeats of the folds. A single deployed threshold would give whole numbers that vary around them.
* **No new negative control.** The fitting code is identical to the fusion analysis, whose shuffled outcome control gave ROC AUC 0.480 and 0.475. The new parts are thresholds learnt from inner training scores. The scores themselves were checked to match the fusion analysis exactly.

## 12. Reproduce

From the repository root with the virtual environment active:

```
python lbw_detection_track/sequential/run_nested.py
python lbw_detection_track/sequential/evaluate.py
```

The run takes about 15 seconds and the evaluation about 40 seconds on the author's machine.
