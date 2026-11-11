# Week 36 model

A second, separate model built after the main study's single held out evaluation. It predicts recorded low birth weight for pregnancies with a visit between 33 and 36 weeks. It has its own plan, its own sealed test set and its own single evaluation. It does not replace the served 28 week model and is not used by the web application.

Its plan was committed before any model was fitted and still carries its working title, "detection track" ([PROTOCOL.md](PROTOCOL.md), commit 0366c53). The evidence behind the plan is [LITERATURE.md](LITERATURE.md). The full results are in [REPORT.md](REPORT.md).

## The locked model

Logistic regression with an L2 penalty (a penalty that shrinks the coefficients to limit overfitting). It uses set B: registration data plus the latest visit in weeks 33 to 36. It was chosen by the rule in the protocol and locked at commit 6dda03c before the test set was opened.

## The single test evaluation

The test set was opened once, on 7 November 2026 (`sealed/test_access.log`). It holds 975 pregnancies, 29 of them with low birth weight. Source: `outputs/test_results.csv` and `outputs/test_comparisons.csv`.

| Measure | Set B, locked | 95 percent interval |
| --- | --- | --- |
| ROC AUC (how often a case is ranked above a non case; 0.5 is chance) | 0.706 | 0.624 to 0.781 |
| Sensitivity at the locked threshold | 0.862 (25 of 29) | 0.719 to 0.968 |
| Specificity at the locked threshold | 0.508 | 0.476 to 0.541 |

Three points must be read with these numbers:

* **It sees only pregnancies still attending at 33 to 36 weeks.** Of all 78 low birth weight births among the test set's records, it found 25. The other cases had no visit in that window, often because the baby came early.
* **Most of its separation comes from that population, not from the late visit.** Registration data alone (set A) reached ROC AUC 0.685 on the same records. Adding the late visit (B over A) changed it by +0.021 (−0.070 to +0.105).
* **It repeats the main study's finding.** Adding the first visit (C over B) changed ROC AUC by −0.015 (−0.056 to +0.028). The first visit added nothing at 28 weeks in the main study, and adds nothing at 36 weeks here.

## Files

| Path | What it holds |
| --- | --- |
| `features.py` | Builds the inputs at a landmark week from the raw file, using the main package's parsers and ranges |
| `methods.py` | The model families compared in development |
| `scoring.py` | Thresholds, measures and group bootstrap intervals |
| `run_experiments.py` | Grouped repeated cross validation on development records only |
| `lock_model.py` | Fits and locks the chosen model with checksums |
| `evaluate_test.py` | The single test evaluation; refuses a second run |
| `seal_test_set.py` | Wrote the sealed test list; kept for the record, never rerun |
| `sealed/` | Development, test and quarantine record lists, the test checksum and the access log |
| `locked/` | The locked models and `locked.json` with thresholds and checksums |
| `outputs/` | Development and test results |

The quarantine list is the main study's held out partition. It is excluded here so that this model never sees those records.

## Reproduce

From the repository root with `.venv` active:

```
python week36_model/run_experiments.py
```

This reruns development and rewrites `outputs/development_results.csv` with identical values. `lock_model.py` would overwrite the locked models, and `evaluate_test.py` refuses to run a second time, so neither should be rerun. `tests/integration/test_week36_model.py` checks the sealed list, the access log and the locked model checksums without opening the test records.
