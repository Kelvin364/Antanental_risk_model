# Protocol draft: pathway specific prediction of preterm birth, small for gestational age and low birth weight

Status: **draft for supervisor review, written on 11 November 2026, before any new data exists and before any further model is fitted.** No model in this folder has been fitted. When approved, this file is committed unchanged and later changes are added at the end as dated amendments with their reason, as the earlier protocols in this track did.

Evidence behind each choice is in [REPORT.md](REPORT.md) and in [outputs/](outputs/). The served model, the web application, the main study and every sealed partition are left exactly as they are.

## 1. Terms used

* **Low birth weight (LBW):** a live born baby weighing less than 2,500 grams. This definition does not change.
* **Preterm birth:** birth before 37 completed weeks of gestation. **Spontaneous** preterm birth starts with labour or ruptured membranes. **Provider initiated** preterm birth follows induction or caesarean section for a maternal or fetal reason.
* **Small for gestational age (SGA):** birth weight below the 10th centile for sex and gestational age on the INTERGROWTH 21st newborn size standard. SGA is a measure of fetal growth. It is not the same as LBW. A baby can be LBW without being SGA (born early but grown normally) and SGA without being LBW (grown poorly but born late enough to weigh 2,500 grams or more).
* **Landmark:** a fixed week of pregnancy at which a prediction is made, using only information recorded up to that week, for women still pregnant at that week.
* **Group aware validation:** resampling or splitting by whole registration groups or facilities, so records that belong together never sit on both sides of a split.
* **Calibration:** agreement between predicted probabilities and observed rates. **Calibration slope** below 1 means predictions are too extreme.
* **Net benefit:** true positives minus false positives weighted by the odds of the chosen threshold, per pregnancy.

## 2. Research questions

1. **RQ1.** At landmarks of 20, 28 and 36 weeks, how well do separate models predict (A) preterm birth, (B) SGA and (C) LBW, in discrimination, calibration and net benefit?
2. **RQ2.** Does predicting LBW through its two pathways (A and B) rank and calibrate LBW better than one direct LBW model fitted on the same records and predictors?
3. **RQ3.** Which newly collected predictor groups (reliable obstetric history, accurate dating, numeric fundal height and growth measures, ultrasound biometry) add discrimination beyond routine fields, measured as the change in ROC AUC and net benefit with intervals?
4. **RQ4.** Does a 20 week landmark perform as well as a 28 week landmark? This tests prospectively the post hoc observation that second visits by 20 weeks were ranked better (target study, ROC AUC 0.730).
5. **RQ5.** How much do performance and calibration vary between facilities, and does a model developed in some facilities transport to others?

The aspirational targets of the earlier study (ROC AUC at least 0.80, specificity at least 90 percent, sensitivity at least 54.5 percent) are reported against, never tuned towards. No claim that they are met is made without the external validation in Section 10.

## 3. Outcomes

| Code | Outcome | Definition | Needs |
| --- | --- | --- | --- |
| A | Preterm birth | Birth before 37 completed weeks; spontaneous and provider initiated reported separately | Gestational age at birth from the dating rule in Section 5 |
| A1 | Early preterm birth | Birth before 34 weeks | As A |
| B | SGA | Birth weight below the INTERGROWTH 21st 10th centile for sex and gestational age | Gestational age at birth, sex, birth weight to 10 grams |
| B1 | Severe SGA | Below the 3rd centile | As B |
| C | LBW | Live birth weighing below 2,500 grams | Birth weight to 10 grams |

Rules:

* Birth weight is measured on a calibrated digital scale within one hour of birth and recorded in grams, not rounded to tenths or halves of a kilogram.
* Multiple pregnancies are excluded from the primary analysis and reported separately.
* Stillbirths are recorded with weight and gestational age and analysed as a secondary outcome. They are not silently dropped.
* Outcome fields are entered on a delivery form that cannot be seen from the antenatal record, and antenatal fields are locked once a visit is saved.

## 4. Prediction time points and the landmark rule

* Landmarks: 20, 28 and 36 completed weeks.
* At each landmark a pregnancy is included only if it is ongoing at that week (gestational age at birth or pregnancy loss later than the landmark) and has at least one antenatal visit dated on or before the landmark.
* Predictors are the last value recorded on or before the landmark. Change terms use only visits on or before the landmark.
* **Forbidden:** number of visits after the landmark, date of the next visit, whether a later visit happened, total antenatal visits, and any field entered after the landmark. Future attendance is a consequence of the pregnancy continuing, so it would leak the outcome.
* Births that occur before a landmark are counted and reported: the share of all preterm, SGA and LBW births that each landmark can reach is a primary result, not a footnote.

## 5. Dating rule

Gestational age at each visit and at birth is computed from one dating date per pregnancy:

1. an ultrasound crown rump length at 10 to 14 weeks, otherwise
2. an ultrasound head circumference or biometry before 24 weeks, otherwise
3. a sure last menstrual period confirmed within 7 days by an early examination, otherwise
4. marked as **uncertain dating** and analysed in a sensitivity analysis only.

Every visit carries a calendar date. Gestational age is derived from dates, never typed.

## 6. Predictors

Prespecified, grouped by when they are known. Section 3 of REPORT.md gives the clinical reason for each.

| Group | Predictors | Known by |
| --- | --- | --- |
| H: history | previous preterm birth, previous LBW baby, previous SGA baby if known, previous stillbirth, previous pre eclampsia, parity and gravidity with automatic consistency checks, interpregnancy interval | booking |
| M: maternal | age, height, booking weight and body mass index, mid upper arm circumference, chronic hypertension, diabetes, HIV status, smoking, multiple pregnancy | booking |
| L: laboratory | haemoglobin in grams per decilitre at booking and in the third trimester, urine protein, malaria test | booking, repeated |
| V: visit series | blood pressure, weight, numeric symphysis fundal height in centimetres, all dated | every visit |
| U: ultrasound, where available | dating crown rump length; estimated fetal weight and abdominal circumference at about 28 to 36 weeks; uterine artery pulsatility index at 19 to 24 weeks | by landmark |

Umbilical artery Doppler is recorded but not used as a screening predictor, because it is done mainly after growth restriction is already suspected and would mix management with prediction.

Predictor budget: no more than 10 candidate parameters per model at the 20 week landmark and 20 at the 28 and 36 week landmarks, unless the realised events support more under Section 8.

## 7. Inclusion and exclusion

* **Include:** pregnant women booking at a participating facility, with consent, any gestational age at booking.
* **Exclude from the primary analysis:** multiple pregnancy, known major congenital anomaly at booking, delivery outside the network without a traced outcome (reported as loss to follow up).
* **Per landmark:** the landmark rule of Section 4.
* **No exclusion based on later attendance.** The earlier study's rule "visit two by 28 weeks" removed 2,157 records (outputs/tables/cohort_flow.csv in the main study) and conditioned the cohort on attendance. It is not repeated.

## 8. Sample size

Computed by `sample_size.py` (outputs/sample_size_development.csv and sample_size_validation.csv) with the criteria of Riley and colleagues. Before registration the numbers are recomputed with the pmsampsize and pmvalsampsize software using the realised prevalence of the pilot.

* **Development, per outcome and landmark:** the larger of the three criteria at an anticipated ROC AUC of 0.75 and the predictor budget of Section 6. For LBW with 20 parameters this is 4,145 records with 219 events; for preterm birth 5,644 with 215; for the LBW without recorded preterm birth group (the closest SGA proxy available now) 6,643 with 211.
* **External validation, per outcome:** at least 400 events, the largest of the precision criteria at an anticipated ROC AUC of 0.80. For LBW this is 7,589 records with 401 events.
* The anticipated ROC AUC of 0.75 is a planning value, not a promise. If the pilot shows lower discrimination, the predictor budget is cut before any model is fitted.

## 9. Missing data

* Missingness is reported by facility, landmark, outcome group and predictor before any model is fitted.
* **Primary:** multiple imputation by chained equations within each training fold, with the outcome, the facility and auxiliary variables in the imputation model, 20 imputations, estimates pooled by Rubin's rules.
* A missingness indicator is used only where missingness is plausibly part of care (for example, a laboratory test not offered) and is stable across facilities. It is never used for a field whose missingness depends on later attendance.
* **Sensitivity:** complete case analysis, and imputation without the outcome.
* Fields missing in more than 50 percent of records at a landmark are reported but not used as predictors at that landmark.

## 10. Validation

* **Development:** internal validation by bootstrap with all steps (imputation, selection, penalty choice, threshold) repeated in every resample, resampling whole facilities or registration groups.
* **Internal external cross validation:** each facility (or district, if facilities are small) is left out in turn; the model is fitted on the rest and tested on the one left out. Performance and calibration are pooled by random effects meta analysis, giving an estimate of between facility variation and a prediction interval.
* **Temporal validation:** the last 6 months of recruitment at the development facilities are sealed when recruitment starts, with ids and a checksum committed before any outcome is entered.
* **Geographic external validation:** at least one region whose facilities never contribute to development. Its ids are sealed the same way, and it is opened once, through a logged single evaluation, after the model is locked.
* **Existing sealed sets:** `partitions/holdout_ids.csv` and `lbw_detection_track/sealed/test_ids.csv` stay closed and are not reused. Both have already had their single evaluation, so neither can serve as an independent test of anything new.

## 11. Threshold selection

* Thresholds are chosen in development only, by one rule fixed now: the threshold whose flagged share matches the review capacity a facility can actually serve, plus the two reference thresholds of the earlier study (90 percent specificity and 54.5 percent sensitivity), each estimated on honest out of sample scores inside the training data.
* Thresholds are locked with the model and applied unchanged to temporal and geographic validation.
* Reported at each threshold: sensitivity, specificity, positive and negative predictive value, cases found and false alarms per 1,000 pregnancies, all with group bootstrap intervals.

## 12. Calibration assessment

Calibration in the large, calibration slope, observed to expected ratio and a flexible calibration curve, per landmark, outcome and facility. A model whose external calibration slope interval excludes 1 is recalibrated (intercept first, then slope) on a prespecified local sample before any use, and the recalibration is reported as a separate model version.

## 13. Clinical utility assessment

* Decision curves for each outcome and landmark across threshold probabilities from 1 to 30 percent, against treating everyone and treating no one.
* Net benefit is interpreted against a named action decided with clinicians before analysis (for example, referral for a growth scan, or an extra visit), because utility depends on what the flag leads to.
* No risk category, priority label or triage wording is used anywhere, consistent with the study's rules. Outputs are a probability and whether it passes a locked threshold.

## 14. Model families allowed

Penalised logistic regression (ridge or LASSO) for each outcome, with restricted cubic splines for continuous predictors; a mixed effects logistic model with a facility random intercept as a sensitivity analysis; a two pathway combination for RQ2 (Section 5 of REPORT.md). Tree ensembles are fitted only as a prespecified comparison and selected only if they beat the logistic model on external net benefit. No class weighting, oversampling, undersampling or synthetic minority generation.

## 15. Reporting

TRIPOD+AI for development and validation, and STROBE for the cohort. The analysis code and this protocol are committed before data collection ends.

## 16. Items only the author or the institution can complete

* [Author to complete: ethics approval route and committee for prospective collection]
* [Author to complete: data sharing agreements with participating facilities and any external registry]
* [Author to complete: funding and registration of the protocol]
