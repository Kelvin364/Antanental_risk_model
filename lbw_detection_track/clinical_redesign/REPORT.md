# Clinical redesign: what has to change for a stronger low birth weight prediction system

Written on 11 November 2026 for the author, the supervisor and the panel. It follows the target study ([../target_study/REPORT.md](../target_study/REPORT.md)), which found that none of 37 model configurations reached the targets and that the best ROC AUC was 0.669.

This investigation fits **no new model**. It audits the source file, reanalyses the target study's stored out of fold scores, and plans the next study. Every number below comes from a file in [outputs/](outputs/), from the main study's outputs, or from the earlier reports, and the file is named beside it. The served model, the web application, the main study and both sealed partitions are untouched. Outcome values were read only for the 3,126 development records.

The plan for future work is [PROTOCOL.md](PROTOCOL.md).

## 1. The answer in brief

1. **The limit is information, not algorithms or sample size.**
   * The file lacks almost every strong predictor of small babies.
   * The few history fields that look relevant are corrupted. The registration field that appears to record a previous preterm birth is in fact an exact copy of the current birth's outcome.
   * Pregnancy dating is unreliable, so preterm birth and poor growth cannot be told apart.
2. **Splitting LBW into its pathways would not, by itself, help with these predictors.** The stored scores rank LBW with recorded preterm birth and LBW without it about equally. With the right data, separate models for preterm birth and for SGA are the right design, because the two pathways have different predictors.
3. **The early visit finding is consistent but not established.** It appears in 33 of 37 configurations. Its interval barely excludes zero, it was found after looking, and it does not follow booking week the way a real timing effect would. It is a hypothesis for a prospective landmark study.
4. **Sample size is not the binding constraint once predictors are strong.**
   * At an anticipated ROC AUC of 0.80 with 20 parameters, development needs about 2,695 records with 143 LBW events, about the size of today's development set.
   * External validation needs about 7,589 records with 401 events.
   * More records of the same fields will not raise the ceiling. New fields and new sites will.
5. **ROC AUC 0.80 is not promised.** Published results near that level for small babies use third trimester ultrasound. Published models using routine maternal factors alone for preterm birth reach about 0.54 to 0.67 when validated externally.

## 2. Deliverable 1: why the current dataset has limited predictive power

### 2.1 The strongest predictors are absent

A name search over all 683 columns (`outputs/field_audit.json`, key `searched_names`) found no field for:

* previous birth weight;
* mid upper arm circumference;
* estimated fetal weight;
* abdominal circumference;
* any Doppler measure;
* a dating scan;
* the date of delivery;
* gestational age at birth;
* a visit date;
* a facility identifier.

### 2.2 The history fields that exist are not history

Source: `outputs/field_audit.json` (whole file, no outcome read) and `outputs/outcome_quality.json` (development records).

* **`preterm_labour_1`** sits in the registration section and looks like "previous preterm labour". It is "yes" in 105 of 2,392 first pregnancies, which cannot have a previous birth. Its "yes" rate is 4.4 percent in first pregnancies and 3.8 percent in later ones, when a true history field would be zero in first pregnancies. On the 3,126 development records it agrees with the current birth's preterm outcome in every record: 119 yes with yes, 3,007 no with no, and no disagreements. **It is a copy of the outcome.** The track was right to ban it, and any model that used it would be reading the birth.
* **`labour_at_term_1`** is "yes" in 2,187 first pregnancies.
* **Parity is inconsistent.** 2,001 first pregnancies report at least one prior delivery.
* **Previous babies of 4 kg or more** are reported by 1,586 first pregnancies. The count is 4 for 1,199 women in the whole file.
* **Stillbirths and births** were already shown to be implausible (`../target_study/outputs/ceiling.json`): prior live births plus stillbirths exceed prior deliveries in 64.2 percent of records.

### 2.3 Dating is unreliable, so gestational age is unknown

Source: `outputs/field_audit.json`, key `dating`.

* **Last period and expected delivery date disagree.** The expected delivery date should be about 280 days after the last menstrual period. It is within 7 days of that in only 23.8 percent of records, and the median gap is 210 days.
* **Booking weeks disagree with visit one.** The recorded weeks of pregnancy at booking are within 2 weeks of the visit one gestational week in only 33.0 percent of records.
* **Visit order is mostly sound.** Recorded visit weeks rise from visit to visit in 95.2 percent of women with two or more visits, so the order of visits is usable even though the calendar is not.
* **There is no delivery date.** Gestational age at birth therefore cannot be computed, and SGA cannot be derived.

### 2.4 Measurements are coarse

Source: `outputs/field_audit.json`, key `measures`.

* **Fundal height** is recorded only as normal or abnormal, never in centimetres. There are 0 numeric values at visit one.
* **Ultrasound** was done at visit one in 11.9 percent of records. Its result is a category such as "normal" (739 records) or "single_live" (61), with no measurements.
* **Raised blood pressure** (140/90 or more) appears at 1.0 percent of first visits. Previous hypertension is recorded for 19 women and chronic hypertension for 7, too few to model.
* **Haemoglobin** is numeric at 91.9 percent of first visits, but at only 34.4 percent of second visits.
* **Height** is complete (share 1.000). This is one of the few strong maternal fields, and 29.0 percent of women are below 150 cm.

### 2.5 The outcome fields themselves are noisy

Source: `outputs/outcome_quality.json`, development records.

* **Contradictory delivery flags.** 47 records are flagged as both preterm and term labour, and 57 as neither.
* **Preterm births with late visits.** 15 of the 119 records with a recorded preterm birth have an antenatal visit at 37 weeks or later.
* **Rounded birth weights.** Every birth weight is recorded to a tenth of a kilogram, and 29.8 percent are exact whole or half kilograms. At a 2,500 gram cut off, rounding moves babies across the line.

### 2.6 Consequence

* **The targets are out of reach on geometry alone.** They need an ROC AUC of about 0.84 under the usual curve shape (`../target_study/outputs/ceiling.json`).
* **Flexible models are memorising noise.** They reached training ROC AUC of 0.92 to 0.98 but honest scores of 0.61 to 0.63 (target study, Section 6).

These two facts together say the signal in these fields is exhausted. The bottleneck is what is recorded and how, not the method.

## 3. Deliverable 2: the most important missing predictors

**Available** means a usable field exists in the current file (`outputs/predictor_inventory.csv`). **Early value** is the judgement of whether the predictor could help a prediction before 28 weeks.

| Predictor | Why it matters clinically | When it is known | In current file | Could improve early prediction | Needs new collection |
| --- | --- | --- | --- | --- | --- |
| Previous LBW baby | Small babies recur. Shared maternal, placental and social causes | Booking | No | Yes, strongly, in women who have given birth before | Yes |
| Previous preterm birth | Strongest single routine predictor of preterm birth. Absolute recurrence about 20 percent for a singleton after a preterm singleton (Kazemier and colleagues, 2014) | Booking | No. The field present is a copy of the outcome | Yes | Yes |
| Previous stillbirth | Marks placental disease and recurrence of poor growth | Booking | Present, implausible counts | Yes, if reliable | Yes, with checks |
| Reliable parity and gravidity | First births carry more SGA and some preterm risk; history predictors only apply after a first birth | Booking | Present, inconsistent (2,001 first pregnancies with prior deliveries) | Yes, as a modifier | Yes, with automatic consistency checks |
| Maternal nutritional status (mid upper arm circumference) | Undernutrition limits fetal growth. The measure changes little with pregnancy | Booking, any time | No | Yes, for SGA | Yes, cheap |
| Maternal height | Short stature constrains fetal growth | Booking | Yes, complete | Already used | No |
| Pre pregnancy body mass index | Low body mass index predicts SGA and modifies the effect of weight gain | Booking (recalled, or first trimester weight) | Booking weight only, at unknown gestation | Yes, for SGA | Yes: record weight with dated gestation |
| Haemoglobin and anaemia | Anaemia is linked to preterm birth and LBW | Booking, repeated | Yes at visit one (91.9 percent numeric), sparse later | Partly used already | Repeat in third trimester |
| Hypertension and pre eclampsia | Pre eclampsia drives provider initiated preterm birth and placental growth restriction | Chronic: booking. Pre eclampsia: after 20 weeks | Rare and coarse (1.0 percent raised blood pressure at visit one) | Moderately, mostly after 20 weeks | Dated blood pressure at every visit and quantified urine protein |
| Gestational age at delivery | Defines preterm birth and SGA. **It is part of the outcome, never a predictor** | At birth | No | Not a predictor; it makes the right outcomes possible | Yes, essential |
| Early ultrasound dating | Accurate gestational age for every visit, for SGA centiles and for preterm definition | 10 to 14 weeks by crown rump length; before 24 weeks by WHO advice | Scan category only, 11.9 percent at visit one | Indirectly: it makes every other gestational measure correct | Yes |
| Estimated fetal weight | Direct measure of fetal size. The strongest single predictor of SGA in published screening | About 28 to 36 weeks | No | Not before 28 weeks; strong at 32 to 36 weeks | Yes, ultrasound and training |
| Fetal abdominal circumference | Most sensitive single biometric measure of growth restriction | About 28 to 36 weeks | No | As above | As above |
| Uterine artery Doppler | Reflects placental development. Predicts early onset growth restriction and pre eclampsia | 11 to 14 or 19 to 24 weeks | No | Yes, for early onset disease | Yes, specialist skill |
| Umbilical artery Doppler | Assesses placental function once growth restriction is suspected | Third trimester, usually after a concern | No | Little for screening; it is a management test | Record when done, not as a screening predictor |
| Numeric fundal height | Cheap measure of fetal size. Its trajectory, compared with a standard, is more informative than a single value | From about 20 to 24 weeks, every visit | No. Normal or abnormal only | Moderately, from the late second trimester | Yes: tape measure in centimetres, dated |
| Maternal weight gain trajectory | Poor gain is linked to SGA, modified by early body mass index | Serial, from the second trimester | Weights present (5,103 records with 3 or more), but gestation per visit uncertain | Moderately | Dated weights; reliable dating |

Clinical timing statements in this table are standard obstetric practice. The WHO dating advice and the third trimester ultrasound figures were checked by web search (Section 13). The others are general knowledge, not checked against a source in this investigation.

## 4. Deliverable 3: LBW, preterm birth and SGA as prediction outcomes

### 4.1 How they differ

| | Preterm birth | SGA | LBW |
| --- | --- | --- | --- |
| What it measures | **Timing:** born before 37 weeks | **Growth:** smaller than expected for sex and gestational age | **Size alone:** below 2,500 grams |
| Needs gestational age at birth | Yes | Yes | No |
| Main causes | Spontaneous labour (infection, cervical factors, previous preterm birth) or delivery for maternal or fetal illness (pre eclampsia, growth restriction) | Placental insufficiency, maternal undernutrition and short stature, hypertension, smoking, infection | A mixture of the two, in proportions that vary by setting |
| Best known predictors | Previous preterm birth, cervical length, multiple pregnancy | Fetal biometry, uterine artery Doppler, maternal size and nutrition, previous SGA | Those of both |
| What a flag leads to | Closer monitoring and preparation for an early birth | Growth scans and timing of delivery | Unclear: the right action depends on which pathway is responsible |

In 138 low and middle income countries in 2010, about 59 percent of LBW babies were born at term and SGA (Lee and colleagues, 2013). LBW and SGA overlap but are not interchangeable. LBW is not redefined here.

### 4.2 What the current records show

Development records (`outputs/outcome_decomposition.csv`):

| Group | Records | Median birth weight (kg) |
| --- | --- | --- |
| LBW with recorded preterm birth | 66 | 2.0 |
| LBW without recorded preterm birth | 99 | 2.3 |
| Not LBW, recorded preterm birth | 53 | 3.1 |
| Neither | 2,908 | 3.1 |

* **Recorded term labour.** 96 of the 99 LBW babies without recorded preterm birth also have recorded term labour. They are the closest available proxy for SGA at term, but only a proxy: without gestational age at birth, SGA cannot be confirmed.
* **Preterm babies of normal weight.** 44 of the 53 not LBW, recorded preterm births also have recorded term labour. This is a further sign that the preterm flag is unreliable outside LBW.

**Do the current scores rank the two pathways differently?** Each row of the table below takes stored out of fold scores from the target study and compares one kind of case against all non LBW records (`outputs/discrimination_by_case_type.csv`; group bootstrap, 2,000 resamples).

| Model | LBW with preterm birth | LBW without preterm birth | Difference (without minus with) | Any recorded preterm birth versus none |
| --- | --- | --- | --- | --- |
| Served method, F0 | 0.614 (0.544 to 0.683) | 0.635 (0.578 to 0.692) | +0.021 (−0.067 to +0.108) | 0.552 (0.499 to 0.604) |
| L2 logistic, F2 | 0.662 (0.595 to 0.727) | 0.655 (0.594 to 0.714) | −0.007 (−0.098 to +0.082) | 0.593 (0.543 to 0.644) |
| Stacking, F2 (selected) | 0.692 (0.629 to 0.752) | 0.650 (0.589 to 0.709) | −0.042 (−0.127 to +0.042) | 0.607 (0.554 to 0.660) |
| Random forest, F2 | 0.699 (0.637 to 0.757) | 0.650 (0.590 to 0.707) | −0.049 (−0.134 to +0.034) | 0.606 (0.554 to 0.658) |

At the selected model's 90 percent specificity threshold, the share of each group flagged was:

* LBW with preterm birth: 27.8 percent;
* LBW without preterm birth: 28.6 percent;
* non LBW: 11.7 percent.

**Reading.**

* **No difference between pathways.** Every difference interval includes zero. The current scores pick up both pathways weakly and about equally, so there is no hidden subgroup that a separate model would suddenly rank well.
* **The scores do not predict preterm birth as such.** Recorded preterm birth regardless of weight is ranked worse still: 0.552 to 0.607.

The combined outcome is therefore not what is holding the models back today. The predictors are.

### 4.3 Recommended framework

**A hierarchical, two pathway framework, built only once gestational age at birth is recorded:**

1. **Model P:** preterm birth before 37 weeks, with spontaneous and provider initiated births reported separately.
2. **Model G:** SGA, below the INTERGROWTH 21st 10th centile.
3. **LBW** predicted two ways:
   * directly by its own model;
   * by combining P and G. LBW is mostly preterm birth or term SGA, so its probability can be built from the pathway probabilities with a small correction model fitted on the same development data.

   Research question RQ2 in the protocol decides which of the two predictions to use, on external data.

Why not the alternatives:

* **Separate models alone** lose the LBW prediction that the study and its interface are built around.
* **A multitask neural model** shares information between outcomes, but needs far more events than the 100 to 400 per outcome this study can expect. Its benefit over two penalised logistic models with a shared predictor set is unproven at this size, and it is harder to explain.
* **A single LBW model** hides which action a flag should lead to.

## 5. Deliverable 4: proposed clinical prediction architecture

Model complexity is set by the number of events. At 140 to 220 events per outcome and landmark (Section 8), about 10 to 20 parameters per model is the ceiling.

1. **Inputs by landmark** (20, 28 and 36 weeks). Each landmark uses only information dated on or before it (PROTOCOL.md Section 4).
2. **Clinically informed features** with fixed, prespecified forms:
   * **Fundal height deviation:** measured centimetres minus the standard expected for the gestational week.
   * **Weight gain:** per week since booking, interpreted against booking body mass index.
   * **Blood pressure:** the highest mean arterial pressure to date.
   * **Haemoglobin:** the lowest value to date.
   * **History:** a summary of previous preterm birth, LBW and stillbirth, coded as "not applicable" for first pregnancies rather than "no".
3. **Longitudinal handling in two stages.** A mixed effects model of fundal height and weight against gestational age, fitted on development data only, gives each woman's deviation from the expected trajectory at the landmark. That deviation enters the outcome model as one predictor. This uses all dated visits without a complex joint model.
4. **Outcome models:** penalised logistic regression for P, G and LBW, with restricted cubic splines for continuous inputs.
5. **Facility variation:**
   * a facility random intercept in a mixed effects logistic model as a sensitivity analysis;
   * internal external cross validation by facility for the main estimate of transportability.
6. **Explanation:**
   * coefficients and odds ratios are the explanation;
   * for each prediction, the contribution of each input to the log odds is shown;
   * no separate post hoc explainer is needed for a linear model.
7. **Ensembles and trees** are prespecified comparisons only. They are chosen only if they improve external net benefit. The target study showed no gain from them at this size.
8. **Deep learning is not proposed.** There are too few events, and the inputs are tabular.

## 6. The early antenatal visit finding and a proper landmark design

### 6.1 What the stored scores show

Sources: `outputs/early_visit_case_mix.csv` and `outputs/early_visit_summary.json`.

| Visit two week | Records | Cases | Of which preterm | Median visit one week | Haemoglobin at visit two missing | ROC AUC, selected model |
| --- | --- | --- | --- | --- | --- | --- |
| Up to 20 | 987 | 53 | 25 | 12 | 71.7 percent | 0.730 (target study) |
| 21 to 24 | 958 | 60 | 25 | 18 | 61.1 percent | 0.628 |
| 25 to 28 | 1,181 | 52 | 16 | 21 | 52.5 percent | 0.636 |

* **Consistent across models.** The early band has the highest ROC AUC in 33 of the 37 configurations. The median across configurations is 0.705 for the early band, against 0.621 and 0.603 for the later bands.
* **The difference only just excludes zero.** For the selected model, the early band minus the later bands is +0.095, interval +0.007 to +0.181, with 1.5 percent of resamples at or below zero.
* **It does not follow booking week.** Split by visit one week, which is known earlier, ROC AUC is:
  * 0.651 for visit one by 12 weeks (35 cases);
  * 0.766 for 13 to 16 weeks (31 cases);
  * 0.643 for 17 to 20 weeks (66 cases);
  * 0.623 for 21 to 27 weeks (33 cases).

  A real benefit of earlier assessment would be expected to rise steadily towards the earliest bookings. Instead the highest band sits in the middle and rests on 31 cases.
* **Both pathways rise in the early band.** Preterm LBW reaches 0.735 and LBW without preterm birth reaches 0.725 there.

**Why this is not yet evidence.**

1. It was found after the main results.
2. Agreement across 37 configurations is not independent confirmation, because all of them score the same records and the same cases.
3. Women whose second visit falls by 20 weeks are a selected group: earlier bookers who return quickly. Who they are, not when they were seen, may explain the difference.
4. The band is defined by when the second visit happened. That is known at the second visit, but a model applied at a fixed week to all women cannot use it the same way.

Early assessment may still be a useful prediction moment, but this data cannot show it.

### 6.2 How many pregnancies each landmark can reach today

Source: `outputs/landmark_reach.csv`. The track development pool holds 5,257 eligible pregnancies with 241 LBW births.

| Landmark week | One visit by then: records (cases, share of all cases) | Two visits by then: records (cases, share) |
| --- | --- | --- |
| 16 | 1,626 (84, 34.9 percent) | 375 (17, 7.1 percent) |
| 20 | 2,843 (163, 67.6 percent) | 1,052 (55, 22.8 percent) |
| 24 | 3,920 (212, 88.0 percent) | 2,062 (118, 49.0 percent) |
| 28 | 4,576 (231, 95.9 percent) | 3,277 (174, 72.2 percent) |
| 32 | 4,959 (237, 98.3 percent) | 3,925 (192, 79.7 percent) |

**What this means for each landmark.**

* **20 weeks.** A landmark that needs two visits reaches only 22.8 percent of LBW births. With one visit it reaches 67.6 percent, but then no change between visits is available.
* **28 weeks.** This is the earliest landmark that reaches most cases with two visits.

### 6.3 Proper landmark design

The full design is PROTOCOL.md Sections 4 and 5. In short:

* **Who is predicted:** women still pregnant at the landmark. Women who give birth earlier are counted and reported, not predicted.
* **What is used:** only predictors dated on or before the landmark.
* **What is never used:** attendance after the landmark.
* **Requirements:** a delivery date and visit dates. Neither exists in the current file (Section 2.3), so this design cannot be built now without leaning on attendance. The target study reached the same conclusion.

The early visit question becomes protocol question RQ4: does a 20 week landmark perform as well as a 28 week one, in new data?

## 7. Deliverable 5: data strategy and multicentre research

### 7.1 Available now versus proposed

| Source | Status | What it can give |
| --- | --- | --- |
| The current file, unused columns | **Checked, exhausted.** All 683 columns searched (Section 2.1); the target study already used every usable field recorded by visit two | Nothing new for prediction. Date of first fetal movement exists but is "no" for 4,518 records and gives only rough dating |
| Other data in this project | **Checked.** The repository holds only the source file plus derived partitions and outputs; `backups/online.sqlite3` is an application database | Nothing new |
| The dataset producers (University of Dodoma, MHRS) | **Proposed: ask.** The Zenodo record describes a cleaned file named `maternal_data_FINAL_CLEANED_v5.csv` with 7,982 participants after cleaning, which differs from the 8,817 record version 1 file used here | Ask for the data dictionary (`metadata.pdf`), delivery dates, visit dates, facility codes, and whether the history fields were entered as history or copied from the delivery register |
| KCMC Medical Birth Registry, Moshi, Tanzania | **Proposed external source**, access to be negotiated | Gestational age from the last menstrual period in completed weeks, birth weight, and maternally linked births. Linkage allows a real "previous LBW baby" and "previous preterm birth" history. A published recurrence study used 26,191 linked births. Hospital based, so not representative of primary care |
| PRECISE Network cohort (The Gambia, Kenya, Mozambique) | **Proposed external source**, access through the consortium's data and sample access committee | A prospective pregnancy cohort of up to 10,000 women focused on placental disorders, with detailed antenatal data. Suitable for developing and testing the growth pathway model |
| INTERGROWTH 21st standards | **Available reference, not a dataset** | Centiles needed to define SGA and expected fundal height and fetal size |
| Demographic and Health Surveys | **Not suitable** for antenatal prediction | Birth weight by recall, history only after the birth |
| Prospective collection | **Necessary** | The only route to dated visits, reliable dating, numeric fundal height, mid upper arm circumference and verified history in the target population |

External sources differ from the study population (referral hospital, other countries). They are proposed for developing and testing the pathway models and for external validation of the approach. They are not to be pooled with the Tanzanian primary care data without modelling site differences.

### 7.2 Prospective multicentre collection

* **Design:** the current antenatal card fields plus the additions in PROTOCOL.md Section 6, entered digitally at each visit with a date and a facility code.
* **Delivery record:** a separate form, linked by a study identifier.
* **Sites:**
  * at least 10 facilities across at least 2 regions, so that internal external cross validation has enough facilities to estimate variation;
  * including at least one facility with ultrasound, so the ultrasound predictor group can be tested where it is available;
  * one region held back entirely for geographic validation.
* **Quality checks at entry:**
  * a history that is impossible for the stated parity is refused;
  * gestational age is computed from the dating date;
  * birth weight is entered in grams.

## 8. Deliverable 6: sample size and feasibility

Sources: `outputs/sample_size_development.csv`, `outputs/sample_size_validation.csv` and `outputs/feasibility.json`. The development criteria are those of Riley and colleagues (BMJ 2020): shrinkage of at least 0.9, optimism in R squared of at most 0.05, and overall risk within 0.05.

The prevalence values come from the development records:

* LBW: 0.053;
* recorded preterm birth: 0.038;
* LBW without recorded preterm birth: 0.032.

### 8.1 Development: records (events) needed

LBW:

| Anticipated ROC AUC | 10 parameters | 20 parameters | 30 parameters |
| --- | --- | --- | --- |
| 0.70 | 3,420 (181) | 6,839 (361) | 10,259 (542) |
| 0.75 | 2,073 (110) | 4,145 (219) | 6,218 (329) |
| 0.80 | 1,348 (72) | 2,695 (143) | 4,042 (214) |

At 20 parameters and an anticipated ROC AUC of 0.75:

* preterm birth needs 5,644 records (215 events);
* LBW without recorded preterm birth needs 6,643 (211).

The shrinkage criterion drives every row.

### 8.2 External validation: records (events) needed

* **Target precision:**
  * calibration slope interval width 0.2;
  * observed to expected ratio within 10 percent;
  * ROC AUC interval width 0.1;
  * sensitivity at 54.5 percent within 5 points;
  * specificity at 90 percent within 2 points.
* **LBW at an anticipated ROC AUC of 0.80:** 7,589 records with 401 events, driven by the observed to expected criterion.
* **LBW at 0.70:** 15,076 with 796 events, driven by the calibration slope.
* **The sensitivity target alone** needs 7,219 records, about 381 cases.

For comparison, Riley and colleagues' worked example of external validation needed 177 events for calibration and discrimination, and 116 for net benefit at one threshold.

### 8.3 Is several thousand more records from the same facilities enough?

The five districts produced 8,161 singleton live births with a recorded weight, including 360 LBW births, over 10.3 months of collection. That is about 791 births and 34.9 LBW births a month (`outputs/feasibility.json`; main study `outputs/tables/cohort_flow.csv`).

* **For development, numerically yes.** 2,695 records would take about 3.4 months at that yield, and 6,839 (the 0.70 scenario) about 8.6 months.
* **But only if the new fields are recorded.** The same facilities, with the same forms, would add records but no new information. The learning curve in the target study shows records of the current kind add little.
* **For validation, the same facilities are not enough.** 7,589 records is about 9.6 months, but a sample from the same facilities gives only temporal validation. It cannot show whether the model transports to other places.
* **The file has no facility code,** so even variation between the current facilities cannot be measured.
* **Multiple sites are therefore necessary:** at least 10 facilities, with one region held out, as in Section 7.2.

**Conclusion.** About 12 to 18 months of prospective collection across 10 or more facilities would support development and temporal validation for LBW, with geographic validation in a held out region. Preterm birth and SGA need about the same number of records each but are rarer, so they would need the longer end of that range. This estimate is a planning figure from the yields above, not a guarantee.

## 9. Deliverable 7: future validation protocol

The complete protocol is [PROTOCOL.md](PROTOCOL.md). It specifies:

| Element | Section |
| --- | --- |
| Research questions RQ1 to RQ5 | 2 |
| Outcome definitions | 3 |
| Prediction time points and landmark rule | 4 |
| Dating rule | 5 |
| Required predictors | 6 |
| Inclusion and exclusion | 7 |
| Sample size | 8 |
| Missing data | 9 |
| Group aware, internal external, temporal and geographic validation | 10 |
| Threshold selection | 11 |
| Calibration | 12 |
| Clinical utility | 13 |
| Model families allowed | 14 |

The existing sealed sets stay closed. Both have already had their single evaluation (main study holdout on 24 October 2026; track test set on 7 November 2026), so new validation must come from new data.

## 10. Deliverable 8: step by step roadmap

1. **Now, at no cost.**
   * Record the findings of this report in the main study's limitations: the history field that copies the outcome, unreliable dating, and coarse fundal height.
   * Ask the MHRS producers for the data dictionary, delivery and visit dates, facility codes and the later file version.
2. **Month 0 to 2.**
   * Supervisor review of PROTOCOL.md and its amendment.
   * Apply for ethics approval.
   * Approach the KCMC registry and the PRECISE Network about data access.
3. **Month 1 to 3.** Design the digital antenatal and delivery forms with entry checks (Section 7.2). Train staff on dated visits, fundal height in centimetres, mid upper arm circumference, and birth weight in grams.
4. **Month 3 to 4: pilot at 2 facilities.**
   * Measure completeness and the agreement of dating methods.
   * Recompute the sample size from the pilot prevalence with pmsampsize.
   * Seal the temporal and geographic validation ids before any outcome is entered.
5. **Month 4 to 16.** Recruit across 10 or more facilities.
6. **In parallel, if external data access is granted.** Develop and internally validate the history based preterm model (Model P) on linked registry data, as a first test of whether verified history lifts discrimination.
7. **Month 16 to 19.**
   * Develop Models P, G and LBW at each landmark, with internal external cross validation by facility.
   * Lock the models and thresholds.
8. **Month 19 to 20.**
   * Run the single logged evaluation on the temporal and geographic validation sets.
   * Report with TRIPOD+AI.
9. **Only after external validation:**
   * consider whether any model replaces or sits beside the served model;
   * change the interface to show the pathway outputs with no risk category wording.

## 11. Recommendations ranked

Each recommendation is scored on four dimensions:

* **Clinical impact:** expected effect on prediction and care.
* **Feasibility:** in Tanzanian primary care.
* **Cost:** money and staff time.
* **Research value:** the questions it answers.

Rank combines all four, with impact weighted most.

| Rank | Recommendation | Clinical impact | Feasibility | Cost | Research value |
| --- | --- | --- | --- | --- | --- |
| 1 | Record visit dates, delivery date and gestational age at birth with a dating rule | Large: makes preterm birth, SGA and landmarks possible | Easy | Small | Large |
| 2 | Record verified obstetric history (previous preterm birth, LBW, stillbirth) with parity checks | Large for women who have given birth before | Easy | Small | Large |
| 3 | Birth weight in grams on a calibrated scale; separate delivery form | Moderate: removes outcome noise at the cut off | Easy | Small | Moderate |
| 4 | Multicentre collection with facility codes and a held out region | Large for credibility and transportability | Moderate | Moderate | Large |
| 5 | Numeric fundal height and mid upper arm circumference at every visit | Moderate, mainly for SGA from 24 weeks | Easy | Small | Moderate |
| 6 | Ask the MHRS producers for dates, facility codes and the dictionary | Moderate if the fields exist | Easy | None | Moderate |
| 7 | Develop a history based preterm model on linked registry data | Moderate: tests the history hypothesis early | Moderate (access) | Small | Large |
| 8 | Early dating ultrasound before 24 weeks where available | Moderate: corrects every gestational measure | Moderate | Moderate to large | Moderate |
| 9 | Third trimester estimated fetal weight and abdominal circumference | Large for SGA, but only after 28 weeks | Hard in primary care | Large | Large |
| 10 | Uterine artery Doppler | Moderate, for early onset disease | Hard | Large | Moderate |
| 11 | Further algorithm search on the current fields | Small: already shown in the target study | Easy | Small | Small |

## 12. Limitations of this investigation

* **Reuse of stored scores.** The case type and early visit analyses reuse the target study's stored scores. Those models were trained for LBW, not for preterm birth or SGA, so they show what current predictors carry, not what a dedicated pathway model could reach.
* **An imperfect SGA proxy.** "LBW without recorded preterm birth" stands in for SGA, and the preterm flag itself is unreliable (Section 2.5).
* **Planning figures.** The sample sizes assume a binormal score and a calibrated model, and use closed forms written for this report. They are planning figures to be confirmed with pmsampsize and pmvalsampsize.
* **Feasibility from one period.** Yields come from one 10.3 month collection period and assume the same attendance and prevalence.
* **Literature from summaries.** Literature figures were read as search summaries and abstracts, not full texts (Section 13).

## 13. Sources

Searched on 11 November 2026. Figures were read from abstracts and search summaries. Check each in full before quoting it to the panel.

* Lee A C C and colleagues (2013). National and regional estimates of term and preterm babies born small for gestational age in 138 low income and middle income countries in 2010. Lancet Global Health 1: e26 to e36. doi 10.1016/S2214-109X(13)70006-8. Gives the 59 percent figure in Section 4.1.
* Riley R D and colleagues (2020). Calculating the sample size required for developing a clinical prediction model. BMJ 368: m441. Gives the development criteria. The shrinkage target of 0.9 was confirmed; the exact form of the other two criteria was taken from the published method and implemented in `sample_size.py`, and should be checked against the paper.
* Riley R D and colleagues (2021). Minimum sample size for external validation of a clinical prediction model with a binary outcome. Statistics in Medicine 40: 4230 to 4251. Gives the worked example of 177 events, and 116 for net benefit.
* Meertens L J E and colleagues (2018). Prediction models for the risk of spontaneous preterm birth based on maternal characteristics: external validation. Gives ROC AUC 0.54 to 0.67 before 37 weeks.
* Kazemier B M and colleagues (2014). Systematic review of the recurrence of preterm birth. Gives about 20 percent absolute recurrence for a singleton after a preterm singleton.
* Third trimester screening for SGA: abdominal circumference ROC AUC 0.85 and estimated fetal weight 0.87 (Souka and colleagues). At 27 to 30 weeks, maternal factors with estimated fetal weight and uterine artery Doppler gave ROC AUC 0.77 (PMC7523308).
* WHO (2016). Recommendations on antenatal care for a positive pregnancy experience: one ultrasound scan before 24 weeks. Crown rump length is best measured from 10 to 14 weeks.
* INTERGROWTH 21st newborn size standards: SGA defined as below the 10th centile for sex and gestational age.
* KCMC Medical Birth Registry: PLOS ONE 2019 recurrence study, doi 10.1371/journal.pone.0215768.
* PRECISE Network: Reproductive Health 2020 protocol, and BMJ Open 2025 cohort profile.
* Zenodo record 15309733, Dataset for Maternal Health Risks Stratification in Tanzania.
* Not confirmed: the claim that tree ensembles and multitask models give no benefit at this event count is a judgement from the target study's results and general sample size theory, not from a cited trial.
