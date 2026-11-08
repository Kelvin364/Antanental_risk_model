# Target study: can routine antenatal records reach ROC AUC 0.80, specificity 90 percent and 90 of 165 cases?

Written for the author, the supervisor and the panel. Plan: [PROTOCOL.md](PROTOCOL.md), committed before any model was fitted (commit d04e37f). Every number below comes from a file in [outputs/](outputs/). Nothing here changes the served model, the web application or the main study.

## 1. The answer

**No. The targets cannot be reached together with these records, and the gap is large, not marginal.**

| Target | Needed | Best reached by any of 37 models (internal validation) |
| --- | --- | --- |
| ROC AUC | 0.80 | 0.669 (random forest, wide set; interval 0.624 to 0.713) |
| Cases found at 90 percent specificity | 90 of 165 | 46.7 (selected model, threshold fixed in training folds) |
| Best case, cut off placed on these same outcomes | 90 of 165 | 0.285 sensitivity, about 47 cases (pairwise boosting, wide set) |

No model met all targets at either prespecified threshold (`outputs/selection.json`, `any_model_meets_all_targets: false`).

Even with the cut off placed using the outcomes themselves, which is an optimistic best case, no model found more than about half the required cases at 90 percent specificity.

What did improve is real but small. Using every usable column recorded by visit two raised ROC AUC from 0.627 to about 0.67, and average precision from 0.087 to about 0.11 to 0.12, with intervals that exclude zero. This is the kind of improvement the request called cosmetic, and it is honest to call it that.

## 2. Deliverable 1: research strategy

Three ways a new approach could beat the served model were tested, each against the served model under the same validation:

1. **More information.**
   * **F1:** 66 inputs. Change and rate terms, body mass index, blood pressure summaries, clinical flags, and the track's extra visit fields.
   * **F2:** 234 inputs. Every column recorded at registration, visit one or visit two that the protocol allows, including urine, syphilis, blood group, blood sugar, ultrasound, fundal height and full obstetric and medical history.
2. **More flexible models:**
   * splines (an additive model);
   * boosting with depth 1 and depth 2 trees (an Explainable Boosting Machine equivalent);
   * tuned gradient boosting (the LightGBM and XGBoost method);
   * random forest and extra trees;
   * a support vector machine;
   * LASSO and elastic net;
   * stacking.
3. **Better handling of missing values:** multiple imputation by chained equations, with missingness indicators throughout.

XGBoost, LightGBM, CatBoost, InterpretML and pyGAM are not installed, so the scikit-learn equivalents named in the protocol were used (`HistGradientBoostingClassifier` implements the same histogram gradient boosting as LightGBM). CatBoost's category encoding was not reproduced.

## 3. Deliverable 2: implementation

The scripts sit in this folder:

* `predictors.py` builds the three predictor sets;
* `zoo.py` holds the models, each a full pipeline so imputation, encoding, scaling and selection happen inside the training fold;
* `run_targets.py` runs the nested validation;
* `evaluate.py` computes the measures, intervals, selection and decision curves;
* `ceiling.py` and `week_intervals.py` run the feasibility, timing and learning curve checks.

Validation:

* **Records:** the 3,126 development records (165 cases). The held out list was never opened.
* **Outer folds:** 3 repeats of 5 grouped outer folds, seed 20261109.
* **Inside each training set:** 3 grouped inner folds for tuning by average precision, then 3 more for honest training scores.
* **Thresholds:** fixed from those honest training scores (T90 for 90 percent specificity, T54 for 54.5 percent sensitivity) and applied unchanged to the outer fold.

That is 555 model fits in all.

Rerun from the repository root, in this order:

1. `python lbw_detection_track/target_study/run_targets.py` (about 40 minutes on 8 cores);
2. `evaluate.py`;
3. `ceiling.py`;
4. `week_intervals.py`.

## 4. Deliverables 3 and 4: comparison and performance

Source: `outputs/results.csv` and `outputs/comparisons.csv`. Base rate 0.053.

The **served model rebuilt** here is L2 logistic on F0. It reproduces the main study: ROC AUC 0.627 and average precision 0.087.

### Ranking and calibration (all 37 configurations are in `results.csv`; the most relevant shown)

| Model | Set | ROC AUC (95% interval) | Average precision (95% interval) | Calibration slope (interval) |
| --- | --- | --- | --- | --- |
| L2 logistic (served method) | F0 | 0.627 (0.582 to 0.671) | 0.087 (0.068 to 0.116) | 0.99 (0.61 to 1.40) |
| L2 logistic | F2 | 0.658 (0.612 to 0.703) | 0.121 (0.088 to 0.164) | 0.79 (0.54 to 1.04) |
| **Stacking (selected)** | **F2** | **0.667 (0.622 to 0.710)** | **0.110 (0.085 to 0.151)** | **1.20 (0.85 to 1.56)** |
| Random forest | F2 | 0.669 (0.624 to 0.713) | 0.104 | 1.34 |
| Multiple imputation, L2 logistic | F1 | 0.660 (0.618 to 0.702) | 0.102 | 0.71 |
| LASSO | F2 | 0.656 (0.613 to 0.699) | 0.104 | 0.74 |
| Spline additive model | F2 | 0.643 | 0.095 | 1.05 |
| Gradient boosting (LightGBM method) | F2 | 0.647 | 0.099 | 0.59 |
| Additive boosting (EBM main effects) | F2 | 0.645 | 0.090 | 0.81 |
| Extra trees | F2 | 0.647 | 0.094 | 0.98 |
| Support vector machine | F2 | 0.562 | 0.063 | 0.90 |

### At the two thresholds fixed in training folds

Counts are averages over 3 repeats.

| Model | Threshold | Cases found of 165 | False alarms of 2,961 | Sensitivity (interval) | Specificity (interval) | PPV | NPV |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Served method, F0 | T90 | 38.0 | 329.3 | 23.0% (17.5 to 28.9) | 88.9% (87.8 to 89.9) | 10.3% | 95.4% |
| Selected, stacking F2 | T90 | 46.7 | 347.7 | 28.3% (22.7 to 34.0) | 88.3% (87.3 to 89.3) | 11.8% | 95.7% |
| Served method, F0 | T54 | 91.7 | 1,130.3 | 55.6% (48.5 to 62.6) | 61.8% (60.2 to 63.4) | 7.5% | 96.1% |
| Selected, stacking F2 | T54 | 97.0 | 997.3 | 58.8% (52.1 to 65.8) | 66.3% (64.8 to 67.9) | 8.9% | 96.7% |

**Confusion matrices for the selected model** (cases found, cases missed, false alarms, correct clears):

| Threshold | Found | Missed | False alarms | Correct clears |
| --- | --- | --- | --- | --- |
| T90 | 46.7 | 118.3 | 347.7 | 2,613.3 |
| T54 | 97.0 | 68.0 | 997.3 | 1,963.7 |

How to read this:

* **Same thresholds, one target at a time.** At the threshold that keeps specificity near 90 percent, the selected model finds 47 cases, about half of the 90 needed. At the threshold that reaches 90 or more cases, specificity falls to 66 percent and about 1,000 pregnancies are flagged by mistake.
* **Specificity at T90 is just under 90 percent.** It is 88.3 percent, because thresholds learnt on training scores shift slightly on new records.

### Paired comparison of the selected model with the served method (same resamples)

| Measure | Difference (95% interval) | p |
| --- | --- | --- |
| ROC AUC | +0.040 (+0.010 to +0.071) | 0.010 |
| Average precision | +0.023 (+0.003 to +0.050) | 0.024 |
| Sensitivity at T90 | +5.3 points (+0.4 to +10.1) | 0.039 |
| Specificity at T54 | +4.5 points (+3.1 to +5.9) | below 0.001 |

These p values are not adjusted for comparing 36 configurations with the served method, and choosing the best of 37 makes its estimate optimistic. With a Holm adjustment over 36 tests, none of these would pass. The gain is best described as small and probably real for the wide set, not established.

### Decision curve

Source: `outputs/decision_curve.csv`. **Net benefit** is the share of true cases flagged, minus false alarms weighted by how much a missed case is judged to outweigh a false alarm.

* **Against treating everyone:** between threshold probabilities of 4 and 15 percent, the selected and served models both do better than treating everyone and better than treating no one.
* **Against the served model:** the selected model's advantage is at most 0.0039, at a threshold of 5 percent (0.0150 against 0.0116). That is about 3 to 4 extra true cases per 1,000 pregnancies with no extra false alarms.
* **Above 15 percent:** no model offers anything.

## 5. Deliverable 5: the best model on the evidence

The selection rule written in advance:

1. take the highest average precision;
2. among models within one standard error of it, choose the calibration slope closest to 1;
3. then fewer inputs;
4. then linear before tree.

It chose **stacking on F2**: ROC AUC 0.667, average precision 0.110, calibration slope 1.20.

**Honest alternative.** L2 logistic on F2 has the highest average precision, 0.121, and is far simpler. It was passed over only because its calibration slope of 0.79 was further from 1. It is the more defensible choice in practice.

**The model with the highest ROC AUC,** random forest on F2 at 0.669, was not chosen, because its slope of 1.34 means its probabilities are compressed and its average precision is lower.

**Neither replaces the served model.** The gain is small, would not survive adjustment for 36 comparisons, comes from 234 inputs that a clinic would have to record, and has no independent test.

## 6. Section 8 of the protocol: why the targets are out of reach

1. **The targets demand far more separation than the records show.**
   * Any ROC curve passing through 90 percent specificity and 54.5 percent sensitivity must have ROC AUC at least 0.723.
   * A curve of the usual shape (binormal) through that point has ROC AUC 0.838.
   * The same shape at the served model's 0.627 gives only 20.5 percent sensitivity at 90 percent specificity.
   * Even at the target, only 23.3 percent of flags would be real cases, with 296 false alarms. Source: `outputs/ceiling.json`.
2. **The models are not underfitting.** The flexible models reach training ROC AUC of 0.92 to 0.98, but 0.61 to 0.63 on honest training scores. The support vector machine reached 1.00 on its training records and 0.55 on honest scores. More flexibility only memorises noise.
3. **More records of the same kind would help only a little.** On the learning curve, the stacking model rose from 0.559 to 0.655 as training data grew from 25 to 100 percent, and the served method from 0.603 to 0.625 (`outputs/learning_curve.csv`; one repeat of 5 folds). The curve is still rising for the wide model. Even its steepest recent step (+0.019 per extra quarter of the data) would need several times the current number of cases to approach 0.80.
4. **No single input is strong.**
   * The highest single input ROC AUC of any of the 234 wide inputs is 0.692, for visit one pulse read as text categories (`outputs/single_predictor_screen.csv`). That figure is computed in sample with one rate per category, so it is optimistic.
   * The best plain numeric inputs, age and weight, reach about 0.59.
5. **Much of low birth weight here is early birth, which these records barely predict.** 66 of the 165 cases (40.0 percent) have a recorded preterm birth, against 1.8 percent of other births. Preterm birth is known to be hard to predict from routine antenatal measurements. The outcome fields were used only for this count, never as predictors.
6. **Key history fields are unreliable** (whole file, no outcome):
   * prior live births plus stillbirths exceed prior deliveries in 64.2 percent of records;
   * living children exceed prior deliveries in 28.5 percent;
   * prior stillbirths are spread almost evenly over 0 to 4 (2,259; 1,552; 1,477; 1,679; 1,845).

   A previous low birth weight baby, the strongest predictor in the literature, is not recorded at all.
7. **Missing data is not the bottleneck.** Multiple imputation (ROC AUC 0.660) did no better than median imputation with indicators on the same set (0.660).

## 7. Prediction timing

Source: `outputs/ceiling.json` and `outputs/roc_by_visit_two_week.csv`.

* **Visit one alone versus visit two:** the selected method using only registration and visit one (145 inputs) reached ROC AUC 0.659, against 0.667 with visit two. The second visit adds almost nothing in the wide model, consistent with the main study.
* **By week of visit two:**

  | Visit two week | Records | Cases | ROC AUC (interval) |
  | --- | --- | --- | --- |
  | Up to 20 | 987 | 53 | 0.730 (0.669 to 0.790) |
  | 21 to 24 | 958 | 60 | 0.628 (0.547 to 0.704) |
  | 25 to 28 | 1,181 | 52 | 0.636 (0.554 to 0.718) |

  Pregnancies whose second visit came by 20 weeks were ranked better. This is a subgroup finding examined after the overall results, with wide and overlapping intervals, so it is a hypothesis to test, not a result. Its upper interval still stops below 0.80.
* **Later landmarks:** this track's earlier work at weeks 32 and 36 did not reach 0.70 on development records, and its populations are conditioned on attendance.
* **No better prediction time:** none was found within what these records allow. The file has no gestational age at birth, so a proper landmark analysis (only women still pregnant at the landmark) cannot be built without leaning on attendance, which leaks the outcome.

## 8. Deliverable 6: limitations

* **Internal validation only.** All results come from cross validation within the 3,126 development records. They are not independent external validation; no sealed or held out record was opened, and the held out access log still has 3 lines. A held out or external test of a 234 input model would likely show a lower ROC AUC than 0.667, as happened with the served model (0.628 in development, 0.573 held out).
* **Optimism from choosing the best of 37.** The comparison p values are unadjusted.
* **Library substitutes.** The models are scikit-learn equivalents, not XGBoost, LightGBM, CatBoost or InterpretML themselves.
* **The support vector machine failed.** On F0 its ROC AUC was 0.455 with a negative calibration slope. Its built in probability step uses folds that ignore registration groups and copes badly with rare cases. It is reported, not fixed after the fact.
* **The wide set reads columns whose recording practice is unknown.** For example, whether a test result was entered on the day of the visit. The protocol rules exclude every column known to be later or derived from the outcome, but cannot rule out every timing issue in a file without visit dates.

## 9. Deliverable 7: what would make the targets achievable

These are ordered by expected effect, from the literature reviewed in `../LITERATURE.md`:

1. **Ultrasound measurements**:
   * accurate dating by early ultrasound;
   * estimated fetal weight and abdominal circumference in the third trimester;
   * uterine and umbilical artery Doppler.

   Published models that reach ROC AUC near or above 0.80 for small babies use these.
2. **Gestational age at birth and the date of every visit.** Without them, low birth weight cannot be separated into preterm birth and poor growth, which have different predictors, and proper landmark analysis is impossible.
3. **Reliable obstetric history**, above all a previous preterm or low birth weight baby, recorded consistently and checked against the counts.
4. **Numeric fundal height** in centimetres at every visit, instead of normal or abnormal (abnormal at visit two was recorded in 29 of 6,844 records in the whole file).
5. **More cases from more sites**, with facility codes, so that a richer model can be trained on several thousand cases and tested on a site it never saw.
6. **A prediction aim that fits routine data.** A ranking tool for a fixed review list, as the served model already is, or separate models for preterm birth and for small for gestational age at term, judged against their own published benchmarks.

## 10. What this means for the study

**The served model stays as it is.** This study answers the panel question "did you try harder models and more variables?" with evidence: 12 model types, 3 predictor sets up to 234 inputs, multiple imputation and stacking, all under the same nested validation. The best reached ROC AUC 0.67, and the targets would need about 0.84.

The limit is shown four ways:

* the geometry of the targets;
* the gap between training and honest scores;
* the learning curve;
* the unreliable and missing fields.

It is not assumed.
