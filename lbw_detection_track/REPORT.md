# Low birth weight detection track: report

Written on 7 November 2026 for the author, the supervisor and the panel. Every number comes from `outputs/` or `locked/` in this folder. The plan fixed before any model was fitted is `PROTOCOL.md`, and the evidence behind it is `LITERATURE.md`.

## 1. The result in brief

| Target | Result on the new test set | Verdict |
| --- | --- | --- |
| Sensitivity of at least 0.70 | 0.862 (95 percent interval 0.719 to 0.968): 25 of 29 low birth weight births | Met, and firmly, among pregnancies seen at 33 to 36 weeks |
| ROC AUC of at least 0.70 | 0.706 (0.624 to 0.781) | Met on the estimate, not firmly: the interval reaches below 0.70 |
| Of all low birth weight births in the test set | 25 of 78 found, 0.321 | **Not met.** 49 of the 78 had no usable visit in the 33 to 36 week window |

**Read the first row together with the third.** The model reached its target only among pregnancies it could see at the prediction moment, and it flagged half of them to do so. Counted over the whole test set, it found 32.1 percent of low birth weight births with a specificity of 77.2 percent. That is about what the served study model achieved on its own held out records (34.1 percent and 79.5 percent), although the two sets of records differ. The new approach moved the cut off and the moment of prediction. It did not produce a stronger separation of the two classes.

## 2. The locked model

Logistic regression with an L2 penalty on set B at the 36 week landmark, threshold 0.0294. Set B is registration data plus the latest visit in weeks 33 to 36. It was chosen by the rule in protocol Section 7, not by preference, and locked at commit `6dda03c` before the test set was opened.

| Test set, 975 pregnancies with 29 events | Actually low birth weight | Actually not |
| --- | --- | --- |
| Flagged | 25 | 465 |
| Not flagged | 4 | 481 |

| Measure | Value (95 percent interval) |
| --- | --- |
| Sensitivity | 0.862 (0.719 to 0.968) |
| Specificity | 0.509 (0.476 to 0.541) |
| ROC AUC | 0.706 (0.624 to 0.781) |
| PR AUC | 0.064 (0.037 to 0.130), against a base rate of 0.030 |
| Positive predictive value | 0.051 (0.033 to 0.073) |
| Negative predictive value | 0.992 (0.983 to 0.998) |
| Calibration slope | 2.03 |
| Brier score | 0.0285 |

About 1 in 20 flagged pregnancies was truly low birth weight. Half of all pregnancies were flagged (490 of 975). The calibration slope of 2.03 means the probabilities themselves are not reliable on these records, so only the ranking and the flag should be read.

The test sensitivity (0.862) is above the development value (0.756). With 29 events that gap is well inside chance, and 0.756 is the safer expectation.

## 3. The three feature sets on the test set

Same method, same landmark, each with its own threshold locked at 75 percent development sensitivity.

| Set | ROC AUC (95% interval) | PR AUC | Sensitivity | Specificity | Found of 29 | False alarms |
| --- | --- | --- | --- | --- | --- | --- |
| A, registration | 0.686 (0.592 to 0.779) | 0.068 | 0.897 | 0.275 | 26 | 686 |
| B, plus latest visit | 0.706 (0.624 to 0.781) | 0.064 | 0.862 | 0.509 | 25 | 465 |
| C, plus earliest visit and weight gain | 0.692 (0.602 to 0.779) | 0.057 | 0.828 | 0.482 | 24 | 490 |

| Paired difference | Value (95% interval) | p |
| --- | --- | --- |
| B over A, ROC AUC | +0.021 (-0.070 to +0.105) | 0.636 |
| C over B, ROC AUC | -0.015 (-0.056 to +0.028) | 0.450 |
| C over A, ROC AUC | +0.006 (-0.097 to +0.107) | 0.917 |

No difference between the sets can be detected here. Adding the earlier visit did not help, which agrees with the study. The clearest practical gain is that set B reached a similar sensitivity to set A with 221 fewer false alarms, but this comparison was not tested formally and each set has its own threshold.

## 4. What was compared on development records

Seven methods, four predictor sets and three landmarks: 84 configurations, all cross validated with registration groups kept together.

| Landmark | Pregnancies, events (of 241 in the pool) | Best ROC AUC | Configuration |
| --- | --- | --- | --- |
| 28 weeks | 2,989, 141 | 0.656 | Average of logistic and boosting, set D |
| 32 weeks | 2,811, 108 | 0.667 | Average of logistic and boosting, set D |
| 36 weeks | 2,612, 82 | 0.685 | Random forest, set C |

No configuration reached ROC AUC 0.70 on development records. Separation improved only slightly as pregnancy advanced, while the share of cases that could be reached fell from 141 to 82.

**Imbalance methods, 36 week landmark, set B:**

| Method | ROC AUC | Specificity at 75% sensitivity | Calibration slope | Brier score |
| --- | --- | --- | --- | --- |
| Logistic, no correction | 0.648 | 0.508 | 0.92 | 0.030 |
| Class weighted | 0.636 | 0.418 | 0.60 | 0.220 |
| SMOTE inside the fold | 0.637 | 0.489 | 0.45 | 0.213 |

Weighting and SMOTE did not improve separation and badly damaged the probabilities, as van den Goorbergh et al. (2022) predict. High sensitivity came from the threshold.

## 5. Integrity

| Check | Result |
| --- | --- |
| Test list sealed before any model, outcome blind | Commit `0366c53`, SHA 256 `e60150f9…6145` |
| Models and thresholds locked before the test was opened | Commit `6dda03c` |
| Test, development and quarantine lists | No overlap, and no registration group crosses them |
| Single predictor check for leakage | Largest 0.651 (first pulse at 36 weeks), under the 0.80 stop; the leading cases are young, light women, which is clinically sensible |
| Banned columns | Refused in code; includes two columns that look like history but copy the delivery outcome |
| Later values | Only visits at or before the landmark are used; visit counts and time since the last visit are never used |
| Resampling, imputation, scaling, tuning | Inside each training fold |
| One test only | `sealed/test_access.log`; a second run was tried and refused |
| Old 782 held out records | Not opened, not used for training or testing; `partitions/holdout_access.log` still has 3 lines |
| Study and served model | Data and artefact checksums unchanged |

## 6. Limitations

1. **Few test events.** 29 events, against the 116 in one published worked example of validation sample size. Intervals are wide.
2. **Reach.** Pregnancies with no visit in weeks 33 to 36 are not predicted. Some had already delivered, and those early births are often the most serious low birth weight cases. Others simply did not attend. The file cannot separate these reliably.
3. **Timing.** A prediction at 36 weeks leaves little time to act.
4. **Population shift.** The test set holds later bookers, because every pregnancy with a second visit by 28 weeks was already used. Base rates and calibration differ from development.
5. **Selection by rule.** The rule chose the landmark with the highest development ROC AUC among three, and the test uses that one landmark only.
6. **Data quality.** Prior stillbirth counts are spread almost evenly from 0 to 4, which is implausible, and fundal height is nearly always "normal". The file has little of the ultrasound information behind the best published results.
7. **One dataset.** There is no external validation.

## 7. What can honestly be claimed

* A 70 percent detection target can be reached on unseen records, among pregnancies seen late in the third trimester, at the cost of flagging about half of them.
* Separation is modest: ROC AUC about 0.65 to 0.70. It is clearly better than chance on these records, and in line with the median of 0.68 reported for small for gestational age prediction.
* It is not a strong model. Over all low birth weight births the detection rate stayed near one third.
* Routine visit data appears to be the limit. Seven methods and 84 configurations, added to the 36 earlier candidates (28 in Stage 2 and 8 in the 26 October sprint), did not change that.

This track does not replace the served model 1.0.0 or change any result of the study.

## 8. How to reproduce

From the repository root, with `.venv` active. The last step is refused by design.

```
cd lbw_detection_track
PYTHONPATH=../src:. python run_experiments.py
PYTHONPATH=../src:. python lock_model.py
PYTHONPATH=../src:. python evaluate_test.py
```
