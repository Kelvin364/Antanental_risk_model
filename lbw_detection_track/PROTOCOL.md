# Protocol for the low birth weight detection track

Written on 7 November 2026, before any model in this folder was fitted and before any outcome of the new test set was read. It is committed to git together with the sealed test list, so the history proves the order. It is not edited after that commit. A change is added at the end as a dated amendment with its reason, and any result it affects is labelled exploratory.

This is an independent track. It does not change the study, its cohort, its partitions, the served model 1.0.0 or any reported result. The author asked for it, and asked that the proposal not bind it, so class weighting and resampling are allowed here and nowhere else.

## 1. Objectives

1. Class separation: ROC AUC of at least 0.70 on the new test set. This is the conventional lower bound of acceptable discrimination.
2. Detection: sensitivity of at least 0.70 on the new test set at a threshold locked beforehand.
3. Integrity: no test record influences any choice.

Both targets are reported as met or not met, whatever the result.

## 2. The three groups of records

| Group | Records | Use |
| --- | --- | --- |
| Old held out partition | 782 pregnancies, plus any record sharing a registration group with them | Quarantined. Not used for training, tuning or testing here. Its identifiers are found by subtraction (analysis cohort minus development records), so `partitions/holdout_ids.csv` is not opened, and its outcomes are dropped before anything is computed |
| Development pool | The 3,126 study development records, plus half of the remaining eligible records | All training, feature choice, tuning and threshold choice |
| New test set | The other half of the remaining eligible records | Sealed now, evaluated once at the end |

Eligible means the study's rules 1 to 3: a recorded live birth, a singleton, and a birth weight from 1 to 6 kg (8,161 records).

The split is a seeded random draw over whole registration groups. A group with a member in the development records or the quarantine cannot enter the test set. No outcome is read to make the split, so the number of events in the test set is not known until the final evaluation.

**Why the 782 are not the test.** They were evaluated on 24 October 2026, their results are known to the author and to this investigation, and the study's protocol allows one evaluation only. They are not untouched.

**Known weakness of the new test set.** Every eligible pregnancy with a second visit by 28 weeks is already in the development records or the quarantine. The test set therefore contains later bookers and pregnancies with fewer early visits. It is a real and unseen test, but its population differs from the development records, which may make it harder.

## 3. The prediction moment

A landmark is a fixed week of pregnancy at which a prediction is made. Three are examined: 28, 32 and 36 weeks.

A pregnancy enters a landmark only if it has a usable visit in the four weeks up to and including that week. This matters. A woman who delivers early stops attending, and early delivery causes low birth weight, so using "latest visit", "number of visits" or "time since last visit" without a landmark would let the model read the birth from the attendance pattern. Pregnancies that have already ended are not predicted at that landmark, and the report states how many of all low birth weight births each landmark can reach at all.

## 4. Predictors

Only values recorded at or before the landmark may be used.

| Set | Contents |
| --- | --- |
| A | Registration: age, gravidity, prior deliveries, height, registration weight and the medical history fields of study set A |
| B | A plus the latest visit in the landmark window: blood pressure, weight, gestational age, pulse, haemoglobin |
| C | B plus the earliest visit and the change between them: earlier blood pressure, weight, gestational age, pulse, and weight gain per week |
| D | C plus the wider record: further obstetric and medical history, body mass index, anaemia, symptoms, supplements and malaria prevention, social factors, foetal heart and presentation |

**Banned from every set, because they are known only at or after the birth or are built from it:** `Risk`, `total_antenatal_visits`, `mode_of_delivery`, `live_births`, `still_births`, `labour_at_term`, `post_term`, `preterm_labour`, `twins_delivery`, `number_of_twins`, `newborn_birth_weight_kg_`, `newborn_with_weight_4kg_and_above`, `gender_of_new_born_child`, `new_born_with_complication`, `immunization_status`, `miscarriages_or_abortions_1`, `bleeding_during_pregnancy`, `bleeding_during_delivery`, `bleeding_after_delivery`, `other_problems_during_pregnancy`, every column ending in `_p`, and any count of visits or time since the last visit. Also banned, from the study's audit (`src/antenatal/audit/extended.py`): `preterm_labour_1` and `labour_at_term_1`, which look like history but copy the current delivery outcome, and `miscarriages_or_abortions` and `number_of_miscarriages_or_abortions`, which agree with the outcome field. `twin_pregnancy`, `congenital_malformations` and its type field are not used either, because they may describe this baby.

## 5. Methods compared

Chosen from the review in `LITERATURE.md`. Each is run on every landmark and set: logistic regression with an L2 penalty (the reference), the same with class weighting, the same with SMOTE inside the training fold, gradient boosted trees, the same with class weighting, a random forest, and an average of logistic regression and gradient boosting. Nothing else is added after results are seen.

## 6. Validation

Five repeats of five fold cross validation grouped by registration group and stratified by outcome, on development pool records only. Imputation, scaling, resampling and tuning all happen inside each training fold. Each record's out of fold probabilities are averaged over repeats. Intervals are group bootstrap intervals with 2,000 resamples. Seed 20261107.

Automatic leakage checks stop the run if: a test or quarantined record is present; a banned column is used; a value from after the landmark is used; or any single predictor alone reaches ROC AUC 0.80 on development records, which would need explaining before continuing.

## 7. Selection, fixed in advance

1. **Landmark.** The earliest landmark at which the best model's out of fold ROC AUC reaches 0.70. If none does, the landmark with the highest out of fold ROC AUC.
2. **Model.** At that landmark, the highest specificity at 75 percent out of fold sensitivity. Any model within one bootstrap standard error of the best counts as tied, and ties go to fewer inputs, then linear over tree, then no resampling or weighting.
3. **Threshold.** The highest probability at which out of fold sensitivity is at least 0.75. The margin over 0.70 is deliberate: a threshold set at exactly 0.70 would be expected to fall below the target on new records about half the time.
4. **Final fit.** The chosen configuration is refitted on all development pool records at that landmark, saved with its checksum and committed before the test set is opened.

## 8. The single test

For the locked model and the same configuration on sets A, B and C at the locked landmark: ROC AUC, PR AUC, sensitivity, specificity, predictive values, confusion matrix, calibration slope, Brier score, each with a group bootstrap interval, and paired differences between the sets. The script writes a log and refuses a second run. The detection target is met if the sensitivity estimate is 0.70 or more, and firmly met only if the lower end of its interval is also 0.70 or more.

Nothing is changed after the test. A shortfall is reported as a shortfall.
