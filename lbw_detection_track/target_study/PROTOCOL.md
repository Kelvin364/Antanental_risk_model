# Target study protocol: can routine antenatal records reach ROC AUC 0.80, specificity 90 percent and 90 of 165 cases?

Written and committed before any model in this folder was fitted. When it was written, the only things looked at were the list of columns in the file, which libraries are installed, and outcome free consistency checks of the history fields (Section 9). Nothing here changes the served model, the web application or the main study.

## 1. Targets

These are research objectives, all to hold together, measured on the 3,126 development records of the main study (165 cases):

| Target | Value |
| --- | --- |
| ROC AUC | at least 0.80 |
| Specificity | at least 90 percent |
| Cases found | at least 90 of 165, so sensitivity at least 54.5 percent |

A target is **met** if its estimate reaches the value, and **firmly met** if the lower end of its 95 percent interval also does. The targets are met together only if every one is met by the same model at the same threshold, and that threshold must be chosen without the outer fold outcomes.

## 2. Records and the prediction moment

The records are the main study's 3,126 development records, identified by the record ids in `outputs/oof_predictions.parquet`. The held out list is never opened, and the 783 quarantined and 2,121 track test records are asserted absent.

The **prediction moment is the second visit**, which is at or before 28 weeks for every record, as in the served model. Only values recorded at visit one, visit two or registration may be used. Nothing from visit three onwards and nothing about later attendance is used.

## 3. Candidate predictors

**F0 (served set C, 25 inputs):** registration, visit two and visit one values, as served.

**F1 (clinical extended):** F0 plus:

* change from visit one to visit two, and change per week, for blood pressure, weight and pulse;
* body mass index, mean arterial pressure and pulse pressure;
* flags for anaemia (haemoglobin below 11), raised blood pressure (140 over 90 or more), short stature (below 150 cm), low body mass index (below 18.5) and first pregnancy;
* age squared;
* temperature, breathing rate, fetal heart heard and malaria test at visits one and two;
* bleeding in a previous pregnancy, second hand smoke, alcohol, vaginal bleeding and problems in the current pregnancy;
* social support, gender based violence, iron and folic acid, folic acid and bed net at visits one and two;
* prior stillbirth count.

**F2 (wide):** every column of the file recorded at registration, visit one or visit two, except the banned and unusable columns listed below. A column is read as numeric if at least 90 percent of its non missing values parse as numbers, and as a category otherwise. Numeric columns missing in more than 95 percent of development records are dropped; this is an availability rule, decided without the outcome. Categories are one hot encoded inside each training fold, keeping levels seen in at least 20 training records. Numeric values are limited to the training fold's 1st and 99th percentiles for linear models.

**Banned or unusable columns:**

* every outcome and delivery field banned by this track's protocol;
* every `_p`, `_1` to `_7` and visit three to eight column;
* `Risk`, `total_antenatal_visits` and `visit_number`;
* the date columns (`last_normal_menustration_date`, `expected_date_of_delivery`, and the fetal movement date columns), because there is no reference date to turn them into weeks;
* `duration_of_pregnancy_weeks_` and `duaration_of_pregnancy_days_`, because when they were recorded cannot be established (Section 9);
* free text columns (names starting `specify_`, `indicate_` or `other_`);
* the raw blood pressure text, replaced by the cleaned values of F0.

## 4. Models

These are all from scikit-learn 1.8.0. XGBoost, LightGBM, CatBoost, InterpretML (Explainable Boosting Machines) and pyGAM are not installed, and installing them would add unvetted dependencies to the project, so the nearest equivalents are used and named as such:

| Requested | Used here |
| --- | --- |
| Penalised logistic, L2 (reference) | `LogisticRegression`, penalty tuned |
| LASSO | `LogisticRegression` with an L1 penalty, tuned |
| Elastic net | `LogisticRegression` with a mixed penalty, penalty and mix tuned |
| Generalised additive model | cubic regression splines (`SplineTransformer`, 4 knots) on numeric inputs with an L2 logistic, penalty tuned |
| Explainable Boosting Machine, main effects | gradient boosting of depth 1 trees, which fits an additive model |
| Explainable Boosting Machine with pairwise terms | gradient boosting of depth 2 trees |
| LightGBM and XGBoost | `HistGradientBoostingClassifier`, the same histogram gradient boosting method, with depth, leaves, leaf size and learning rate tuned |
| CatBoost | not reproduced; its main difference is how it encodes categories, which here are one hot encoded |
| Random forest | `RandomForestClassifier`, leaf size tuned |
| Extra trees | `ExtraTreesClassifier`, leaf size tuned |
| Support vector machine | RBF kernel `SVC` with Platt probabilities, penalty tuned |
| Stacking | logistic regression over the elastic net, boosting and random forest, trained on inner fold predictions |
| Imbalance check | L2 logistic with balanced class weights |

Every model is run on F0, F1 and F2.

Missing data:

* linear models, splines and the support vector machine use median imputation with missingness indicators, learnt inside the training fold;
* boosting handles missing values natively;
* forests use median imputation with indicators;
* multiple imputation: the L2 logistic on F1 is repeated with chained equations (`IterativeImputer`, 5 posterior draws, predictions averaged), as a sensitivity analysis.

## 5. Validation

* **Outer folds:** 3 repeats of 5 folds, stratified by outcome and grouped by registration group, seed 20261109. Every outer fold refuses any group that crosses it.
* **Inside each outer training set:** imputation, encoding, selection by the L1 penalty, and tuning by 3 grouped inner folds scored by average precision. Then a further set of 3 grouped inner folds gives honest training scores, from which two thresholds are fixed:
  * **T90**, the score at which training specificity is 90 percent;
  * **T54**, the highest score at which training sensitivity is at least 54.5 percent.
* **Applied to the outer test fold:** the thresholds are used unchanged, so no outer outcome is used in choosing them.
* **No resampling:** resampling and synthetic records are not used. Class weights appear only in the imbalance check.

## 6. Measures

Each record's score is the mean of its 3 outer scores. Flags are shares of repeats flagged. For every model and feature set:

* ROC AUC, average precision against the base rate, and Brier score;
* calibration slope, and calibration intercept with the slope fixed at 1;
* at T90 and at T54: cases found, false alarms, sensitivity, specificity, positive and negative predictive values, and the confusion matrix;
* descriptive only, because it uses the outcomes to place the cut off: the sensitivity reached at exactly 90 percent specificity on the pooled scores, which is the best any threshold could do;
* a decision curve, giving net benefit at threshold probabilities from 2 to 20 percent, for the served model, the selected model, treat all and treat none.

Intervals come from 2,000 resamples of whole registration groups, seed 20261109, with comparisons against the rebuilt served model (L2 logistic on F0) paired on the same resamples.

## 7. Selection of the best model

This is decided before results:

1. take the highest average precision;
2. among models whose average precision is within one bootstrap standard error of it, choose the one whose calibration slope is closest to 1;
3. then the one with fewer inputs;
4. then linear before tree.

ROC AUC alone never selects. The selected model is then checked against the targets, and against the served model with paired intervals.

## 8. Whether the targets are possible with these records

1. **Geometry.** The smallest ROC AUC any proper curve through the point (90 percent specificity, 54.5 percent sensitivity) can have, and the ROC AUC implied by the usual binormal curve through it.
2. **Underfitting.** Training ROC AUC against validation ROC AUC for the most flexible models. Underfitting would show as both being low and close.
3. **Learning curve.** The selected and served models trained on 25, 50, 75 and 100 percent of each outer training set.
4. **Single predictor screen.** The ROC AUC of each F2 input on its own, descriptive only.
5. **Timing.**
   * The selected method using only registration and visit one, against visit two, on the same records.
   * The selected model's ROC AUC by week of visit two (up to 20, 21 to 24, 25 to 28).
   * Later landmarks are taken from this track's earlier results, which use a different and attendance conditioned population.
6. **What birth weight depends on.** Descriptive only: the share of development cases with a recorded preterm birth. The outcome fields are never used as predictors.

## 9. Data quality findings recorded before modelling (whole file, no outcome)

* **Prior births exceed prior deliveries:** prior live births plus prior stillbirths exceed prior deliveries in 64.2 percent of records.
* **Living children exceed prior deliveries:** this holds in 28.5 percent of records.
* **Prior stillbirths:** they are spread almost evenly over 0 to 4. The same pattern holds for prior infants of 4 kg or more over 1 to 4.
* **Dates:** expected delivery date minus last menstrual period has a median of 210 days instead of about 280.
* **Pregnancy duration field:** `duration_of_pregnancy_weeks_` agrees with visit one gestational age within one week in only 28.4 percent of records, and correlates with it at 0.21.

## 10. Reporting

Every result goes to `outputs/` and `REPORT.md` in this folder, whatever it shows. This is internal validation on development records. No independent external validation is possible with this file.
