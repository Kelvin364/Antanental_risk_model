# Whole pregnancy week 36 model: does using every visit up to 36 weeks help?

Written for the author, the supervisor and the panel. Plan: [PROTOCOL.md](PROTOCOL.md), committed before any result (commit e561457). Every number comes from a file in [outputs/](outputs/). Development records only. The track's test set, already evaluated once on 7 November 2026, was not opened.

## 1. What the locked week 36 model reads

The locked model (set B) reads the registration form plus **one visit: the latest one in weeks 33 to 36**. It does not read any visit before week 33, apart from what the registration form records at booking. Set C adds the first visit and weight gain per week between the two. Neither set reads the visits in between.

## 2. The answer

**No. Summarising every visit up to 36 weeks does not improve the week 36 model.**

* On the same 2,612 development records (82 low birth weight births), the whole pregnancy set H with logistic regression reaches ROC AUC 0.659 (0.599 to 0.721). The locked set B reaches 0.648 (0.588 to 0.709).
* The paired difference is +0.011 (−0.024 to +0.047, p 0.525). The interval includes zero, so under the protocol H does not improve on B.

Set B's figure here matches the track's recorded development value of 0.648, so the rebuild is faithful.

## 3. Results

Thresholds were chosen inside each training fold. The first rule catches 75 percent of cases (the track's rule); the second keeps 90 percent specificity. Intervals come from 2,000 resamples of whole registration groups. Source: `outputs/estimates.csv`.

| Set and model | ROC AUC | Sensitivity, 75% rule | Specificity, 75% rule | PPV, 75% rule | NPV, 75% rule | Sensitivity, 90% specificity rule | Specificity, 90% specificity rule | PPV, 90% specificity rule | NPV, 90% specificity rule |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **B logistic (locked set)** | 0.648 (0.588 to 0.709) | 77.3% | 43.5% | 4.2% | 98.3% | 17.6% | 91.0% | 5.9% | 97.1% |
| C logistic | 0.654 (0.590 to 0.719) | 78.3% | 40.5% | 4.1% | 98.3% | 22.0% | 90.3% | 6.9% | 97.3% |
| **H logistic (every visit)** | 0.659 (0.599 to 0.721) | 74.4% | 47.1% | 4.4% | 98.3% | 19.8% | 89.7% | 5.9% | 97.2% |
| B boosting | 0.655 (0.595 to 0.714) | 83.2% | 35.2% | 4.0% | 98.5% | 24.6% | 90.0% | 7.4% | 97.4% |
| C boosting | 0.637 (0.574 to 0.703) | 80.0% | 32.3% | 3.7% | 98.0% | 26.1% | 90.4% | 8.1% | 97.4% |
| H boosting | 0.644 (0.585 to 0.708) | 79.5% | 35.0% | 3.8% | 98.1% | 24.1% | 90.1% | 7.3% | 97.3% |

Paired comparisons (`outputs/comparisons.csv`):

| Role | Comparison | Difference (95 percent interval) | p |
| --- | --- | --- | --- |
| Primary | H logistic over B logistic, ROC AUC | +0.011 (−0.024 to +0.047) | 0.525 |
| Secondary | H logistic over C logistic, ROC AUC | +0.005 (−0.020 to +0.031) | 0.708 |
| Secondary | C logistic over B logistic, ROC AUC | +0.006 (−0.034 to +0.042) | 0.708 |
| Secondary | H boosting over B logistic, ROC AUC | −0.004 (−0.062 to +0.055) | 0.883 |
| Secondary | H logistic over B logistic, sensitivity at 90% specificity | +2.2 points (−4.6 to +9.0) | 0.559 |
| Secondary | H boosting over B logistic, sensitivity at 90% specificity | +6.6 points (−1.8 to +15.3) | 0.121 |
| Secondary | C logistic over B logistic, sensitivity at 90% specificity | +4.4 points (−0.5 to +9.6) | 0.093 |

None of the differences has an interval that excludes zero.

## 4. Why women without a late visit cannot be added

The second part of the question was whether the model could cover everyone up to 36 weeks, including women whose last visit came before week 33. The descriptive check on all 5,195 development pool records with any visit by 36 weeks (240 cases) is in `outputs/p2_check.json`:

* **The week of the latest visit alone ranks cases at ROC AUC 0.612.** It is not a clinical measurement. It shows that a woman whose last visit came early is more often a case, largely because a baby born early ends the visits.
* Set B logistic built from the latest visit at any time reaches 0.665, higher than the honest 0.648. Part of that gain is this attendance signal, not information about the pregnancy.
* The number of visits by 36 weeks alone gives 0.502, so the leak is in the timing of the last visit, not the count.

A model for "everyone at 36 weeks" is honest only for women known to be still pregnant at 36 weeks, which needs a delivery date this file does not have. Such a model could not be used in practice anyway. A woman who has already given birth cannot be flagged before birth.

## 5. Limits

* Internal validation only. No untouched test set remains.
* Set H has 49 inputs for 82 cases. The penalised logistic model limits overfitting, but some of any gain is lost to it, which the cross validation measures.
* Haemoglobin and pulse are often missing at later visits, so their summaries rest on few readings.

Reproduce: `python lbw_detection_track/whole_pregnancy/run.py`, then `python lbw_detection_track/whole_pregnancy/evaluate.py`. The run takes about 40 seconds and the evaluation about 25.
