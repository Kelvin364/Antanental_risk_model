# Status report

A complete account of the repository at commit `28f9d75` (`git log -1`), updated on 22 October 2026 after CLAUDE.md Section 3 items 1 to 9, for a reviewer who has seen nothing else. Every number below is copied from a file in `outputs/`, a test run or git, and the source is named beside it. Where something does not exist, it says "Not built" with the reason.

The test run quoted in this report was made on 22 October 2026 at commit `28f9d75` with `.venv/bin/pytest tests -q --junitxml=... --cov --cov-report=json:...`: 235 tests (188 unit, 41 integration, 6 browser), 0 failures, 0 errors, 0 skipped, 196.4 seconds, line coverage 97.6 percent of 2,910 statements. The repository's own recorded run, `docs/evidence/test_summary.json`, made the same day (2026-10-22T10:27:25+00:00) by `scripts/record_test_results.py`, gives the same counts and coverage.

What changed since the previous version of this report (commit `5d5d5e2`): group bootstrap intervals beside every spread across repeats (R6), the limitation footer on every figure (R7), the research tables in SQLite through `load-db` (Section 3.4.4), performance and cross browser evidence, design images drawn from the running interface, the report PDF and submission scripts, and new deviation rows. The study results did not change: every number in `outputs/tables/sensitivity_analyses.csv` and `results_summary.csv` is identical to the earlier commit, and only the learning curve gained intervals.

## 1. Research question and the answer so far

### 1.1 The question as stated in the proposal

From Section 1.2 of the proposal: "In the eligible pregnancies of a publicly released Tanzanian antenatal dataset, does information from the first antenatal visit add predictive value for recorded low birth weight beyond the second visit alone, when prediction is made at the second visit occurring by 28 weeks?"

All results in this section are internal validation on the development partition (3,126 pregnancies, 165 events; `outputs/tables/results_summary.csv`, keys `development_records`, `development_events`). Intervals are 95 percent group bootstrap intervals over registration groups, 2,000 resamples, on out of fold predictions averaged per pregnancy over ten repeats. The detectable difference is the smallest difference the design could detect with 80 percent power at a two sided 5 percent level (`src/antenatal/evaluation/power.py`).

### 1.2 Primary result: set C over set B, area under the precision recall curve

Source: `outputs/tables/results_summary.csv`.

| Model family | Difference | 95 percent interval | Detectable difference | Key |
| --- | --- | --- | --- | --- |
| L2 logistic regression | -0.003960 | -0.013020 to 0.002469 | 0.010981 | `primary_c_over_b_logistic` |
| Gradient boosted trees, native missing value handling | -0.006633 | -0.017254 to 0.002370 | 0.014399 | `primary_c_over_b_gbt` |

Both intervals include zero.

### 1.3 Secondary result: set B over set A, area under the ROC curve

Source: `outputs/tables/results_summary.csv`.

| Model family | Difference | 95 percent interval | Detectable difference | Key |
| --- | --- | --- | --- | --- |
| L2 logistic regression | 0.020487 | -0.006609 to 0.047642 | 0.038467 | `secondary_b_over_a_logistic` |
| Gradient boosted trees | 0.034536 | 0.007008 to 0.062721 | 0.039695 | `secondary_b_over_a_gbt` |

The logistic interval includes zero; the tree interval excludes it.

### 1.4 Calibration slope and intercept

Source: `outputs/tables/calibration_by_set.csv` (n 3,126, events 165).

| Model | Set | Slope (95 percent interval) | Intercept (95 percent interval) |
| --- | --- | --- | --- |
| L2 logistic | A | 1.2090 (0.6443 to 1.8227) | -0.0002 (-0.1687 to 0.1536) |
| L2 logistic | B | 1.0114 (0.6386 to 1.4147) | -0.0005 (-0.1677 to 0.1516) |
| L2 logistic | C | 0.9788 (0.6266 to 1.3677) | -0.0018 (-0.1675 to 0.1504) |
| Gradient boosted trees | A | 0.9200 (0.6142 to 1.2522) | -0.0064 (-0.1731 to 0.1465) |
| Gradient boosted trees | B | 1.1438 (0.8029 to 1.4769) | 0.0013 (-0.1640 to 0.1545) |
| Gradient boosted trees | C | 1.1613 (0.7911 to 1.5293) | 0.0032 (-0.1616 to 0.1556) |

Every slope interval contains 1 and every intercept interval contains 0.

### 1.5 Sensitivity analyses

The primary comparison (set C over set B, PR AUC, L2 logistic regression) under each analysis. Full cohort counts are from `outputs/tables/sensitivity_cohorts.csv`; the development records actually analysed, which exclude every record of the primary sealed held out partition, and the differences are from `outputs/tables/sensitivity_analyses.csv`.

| Analysis | Specification | Full cohort, events | Development records analysed, events | Difference (95 percent interval) | Detectable difference |
| --- | --- | --- | --- | --- | --- |
| S1 | Visit two by 24 weeks | 2,449, 142 | 1,945, 113 | -0.0035 (-0.0116 to 0.0036) | 0.0109 |
| S2 | Visit two by 32 weeks | 5,083, 240 | 4,301, 199 | -0.0033 (-0.0130 to 0.0052) | 0.0127 |
| S3 | Excluding records marked both term and preterm | 3,848, 201 | 3,079, 162 | -0.0023 (-0.0114 to 0.0042) | 0.0109 |
| S4 | Every screened measurement recorded at both visits | Not tabulated: defined on development records only | 2,504, 144 | -0.0010 (-0.0067 to 0.0046) | 0.0078 |
| S5 | Rate of change per week added to set C (compared against B) | Same as primary: 3,908, 206 | 3,126, 165 | -0.0057 (-0.0162 to 0.0006) | 0.0115 |
| S6 | Lower birth weight bound relaxed to 0.5 kg | 3,908, 206 | 3,126, 165 | -0.0040 (-0.0130 to 0.0025) | 0.0110 |
| Extra | Gradient boosted trees with median imputation and indicators | Same as primary | 3,126, 165 | -0.0074 (-0.0216 to 0.0008) | 0.0162 |

No primary interval excludes zero (`results_summary.csv`, key `sensitivity_primary_excluding_zero`, value 0 of 7). For the secondary comparison, S2 gives 0.0266 (0.0031 to 0.0514), which excludes zero; the other cohort variants include zero (`sensitivity_analyses.csv`, rows with role `secondary`).

### 1.6 Further analyses (Stage 5)

All on development records, the same sealed folds, L2 logistic regression unless stated.

**Learning curve** (`outputs/tables/learning_curve.csv`, figure `outputs/figures/fig12_learning_curve.png`). Each outer training fold was cut to 20, 40, 60, 80 and 100 percent of its registration groups, ten repeats. The mean PR AUC gap of C minus B across repeats was -0.0014, -0.0011, -0.0039, -0.0020 and -0.0041 at the five fractions (standard deviations 0.0051, 0.0045, 0.0063, 0.0046, 0.0049), with mean training sizes of 500.2 to 2,500.8 records and 26.9 to 132.0 events. On predictions averaged per pregnancy across repeats, the gap with its 95 percent group bootstrap interval (columns `pr_auc_gap_pooled`, `pr_auc_gap_low`, `pr_auc_gap_high`) was -0.0026 (-0.0116 to 0.0068), -0.0001 (-0.0129 to 0.0147), -0.0061 (-0.0195 to 0.0023), -0.0022 (-0.0133 to 0.0074) and -0.0040 (-0.0130 to 0.0025). Every interval includes zero, and the gap does not grow with more data.

**Per measurement ablation** (`outputs/tables/ablation.csv`, `fig13_ablation.png`). Set C minus set C without one visit one measurement, PR AUC: systolic -0.0008 (-0.0053 to 0.0023), diastolic -0.0003 (-0.0020 to 0.0016), weight 0.0004 (-0.0045 to 0.0037), gestational week 0.0003 (-0.0026 to 0.0033), pulse -0.0016 (-0.0082 to 0.0032). No single first visit measurement carries a detectable contribution.

**Parameterisation comparison** (`outputs/tables/parameterisation.csv`, `fig14_parameterisation.png`). Against set B, PR AUC: values only -0.0040 (-0.0130 to 0.0025), values and change -0.0043 (-0.0142 to 0.0042), change only -0.0027 (-0.0105 to 0.0071), rate per week -0.0057 (-0.0162 to 0.0006). Against values only: values and change -0.0004 (-0.0045 to 0.0076), change only 0.0012 (-0.0037 to 0.0125), rate per week -0.0018 (-0.0070 to 0.0022). How the first visit is entered makes no detectable difference.

**Informative missingness** (`outputs/tables/missingness_outcome_rates.csv`, `outputs/tables/missingness_indicator_signal.csv`, `fig15_missingness_rates.png`). Low birth weight rate by whether the visit two value was recorded, Wilson intervals, difference with a Newcombe interval:

| Visit two measurement | Recorded: n, events, rate (interval) | Missing: n, events, rate (interval) | Missing minus recorded |
| --- | --- | --- | --- |
| Systolic pressure | 3,126, 165, 5.28 percent (4.55 to 6.12) | 0 records: required by the cohort rule | Not applicable |
| Diastolic pressure | 3,126, 165, 5.28 percent (4.55 to 6.12) | 0 records: required by the cohort rule | Not applicable |
| Gestational week | 3,126, 165, 5.28 percent (4.55 to 6.12) | 0 records: required by the cohort rule | Not applicable |
| Weight | 3,116, 165, 5.30 percent (4.56 to 6.14) | 10, 0, 0.00 percent (0.00 to 27.75) | -5.30 points (-6.14 to 22.47) |
| Pulse | 2,544, 146, 5.74 percent (4.90 to 6.71) | 582, 19, 3.26 percent (2.10 to 5.04) | -2.47 points (-3.99 to -0.51) |
| Haemoglobin | 1,213, 61, 5.03 percent (3.93 to 6.41) | 1,913, 104, 5.44 percent (4.51 to 6.54) | 0.41 points (-1.25 to 1.96) |

Adding missingness indicators changed PR AUC by 0.0029 (-0.0088 to 0.0147) in set B and 0.0022 (-0.0069 to 0.0114) in set C. Only pulse shows an association with the outcome. It is read as recording practice, not physiology, because the file has no facility identifier to separate the two, and the indicators carry no detectable predictive signal.

**Tree missing value handling** (`outputs/tables/gbt_missing_value_handling.csv`). Native handling minus median imputation, PR AUC: set A 0.0036 (-0.0042 to 0.0121), set B 0.0008 (-0.0074 to 0.0084), set C 0.0015 (-0.0034 to 0.0108). C over B, PR AUC: native -0.0066 (-0.0173 to 0.0024), uniform -0.0074 (-0.0216 to 0.0008). B over A, ROC AUC: native 0.0345 (0.0070 to 0.0627), uniform 0.0431 (0.0151 to 0.0727). Both conclusions are the same under either treatment.

**Multiple imputation** (`outputs/tables/multiple_imputation.csv`). C over B, PR AUC, with iterative imputation drawn five times and pooled by averaging the predictions: -0.0055 (-0.0151 to 0.0008). The five single draws gave -0.0060, -0.0071, -0.0035, -0.0051 and -0.0043, each with an interval including zero. Median imputation gave -0.0040 (-0.0130 to 0.0025).

**Subgroups** (`outputs/tables/subgroups.csv`). A stratum is reported only with at least 30 events. Reported: age under 20 (513, 46 events), set C PR AUC 0.1197 (0.0832 to 0.1823), C minus B -0.0068 (-0.0329 to 0.0079); age 20 to 34 (2,171, 94), 0.0805 (0.0569 to 0.1225), C minus B -0.0020 (-0.0161 to 0.0081); one or more prior deliveries (2,984, 154), 0.0906 (0.0698 to 0.1209), C minus B -0.0037 (-0.0129 to 0.0028). Not reported, fewer than 30 events: age 35 or over (388, 22), age missing (54, 3), no prior delivery (142, 11). The parity strata rest on prior delivery counts that the data audit found inconsistent with the number of pregnancies.

**Retrieval at budget** (`outputs/tables/retrieval_at_budget.csv`, `fig16_retrieval_at_budget.png`). Set C logistic ranking of the 3,126 development pregnancies. Top 10 percent (313 pregnancies): 36 of 165 events, 0.2182 (0.1585 to 0.2792), random expectation 0.10. Top 20 percent (626): 57, 0.3455 (0.2781 to 0.4204), random 0.20. Top 30 percent (938): 79, 0.4788 (0.4041 to 0.5537), random 0.30. This describes retrospective ranking only.

### 1.7 What the results allow us to claim

Within this dataset and design, adding the first visit to the second visit did not improve prediction of recorded low birth weight by any amount larger than about 0.011 in PR AUC, in either model family, any sensitivity analysis, under multiple imputation or at any training size tested. This is a null result bounded by the detectable difference, not proof that the first visit carries no information at all. There is weak evidence that the second visit improves discrimination over registration alone, seen in the tree model and in the 32 week cohort but not in the primary logistic comparison. The predicted probabilities are calibrated within wide intervals, and ranking by the model retrieves more low birth weight births than random ranking, which says nothing about whether acting on the ranking would change any outcome. None of these results has been confirmed on the held out partition, and none generalises beyond this single Tanzanian release without external validation.

### 1.8 What has not been evaluated

The held out partition (782 pregnancies, 41 events, derived as the analysis cohort minus development in `docs/meeting_evidence.md`) has not been opened. `partitions/holdout_access.log` does not exist: `test -e partitions/holdout_access.log` returns false, so its line count is zero. The log is created on the first access attempt by `src/antenatal/evaluation/holdout.py`, and none has been made in this repository.

## 2. Cohort

### 2.1 Flow

Source: `outputs/tables/cohort_flow.csv`; rules in `src/antenatal/cohort/builder.py`.

| Step | Rule applied | Excluded | Remaining | Events remaining |
| --- | --- | --- | --- | --- |
| 0 | Records in the released file | 0 | 8,817 | 443 |
| 1 | Keep a recorded live birth (`live_births` is yes) | 208 | 8,609 | 382 |
| 2 | Drop multiple deliveries (`twins_delivery` is yes) | 416 | 8,193 | 360 |
| 3 | Keep recorded birth weight within 1 to 6 kg; this is the eligible cohort | 32 | 8,161 | 360 |
| 4 | Visit one needs a parsed blood pressure in range and a gestational age in range | 167 | 7,994 | 349 |
| 5 | Visit two must exist with the same two conditions | 1,791 | 6,203 | 271 |
| 6 | Gestational age at visit two greater than at visit one | 138 | 6,065 | 268 |
| 7 | Visit two at or before 28 weeks; this is the analysis cohort | 2,157 | 3,908 | 206 |

### 2.2 Partitions

| Partition | Pregnancies | Events | Source |
| --- | --- | --- | --- |
| Analysis cohort | 3,908 | 206 | `outputs/tables/cohort_flow.csv` |
| Development | 3,126 | 165 | `outputs/tables/results_summary.csv` |
| Held out, sealed | 782 | 41 | Analysis minus development, `docs/meeting_evidence.md` |

Files: `partitions/holdout_ids.csv` with SHA 256 `249114c363dab8a86c5acbee9bb8cfd6fddbf97b3d74b62f907d1fda01a25ea0`, recorded in `partitions/holdout.sha256` and matching `shasum -a 256 partitions/holdout_ids.csv`. `partitions/folds.parquet` holds ten repeats of five grouped stratified folds, SHA 256 `5df188cc31765574674da6a745987f2490ecbcc2b4f337d62f5ed9529b2132d2`.

### 2.3 Raw file

`data/maternal_dataset_csv.csv`, SHA 256 `ab95366ef22dde5d13df93f10723942f5faffda8fbf0007e8efe85e4f25c1126` (`shasum -a 256`, and `StudySpec.data_sha256` in `src/antenatal/config.py`). Version 1 of the Dataset for Maternal Health Risks Stratification in Tanzania, Zenodo DOI 10.5281/zenodo.15309733, CC BY 4.0. The Zenodo record states that a newer version exists; this study stays on version 1 because the specification and every count were frozen against its checksum (`docs/ethics_note.md`, `docs/deviations.md`).

## 3. What was built, module by module

Line counts are from `wc -l`. Public names are those not starting with an underscore. "R" numbers are the requirements of proposal Table 3.11; the proposal lists R1 to R16.

### 3.1 Package `src/antenatal`

| File | Lines | Public classes and functions | Responsibility | Proposal link |
| --- | --- | --- | --- | --- |
| `config.py` | 148 | `Range.contains`; `PhysiologicalRanges.get`; `StudySpec.holdout_splits, variant, as_dict`; `sensitivity_specs` | Every constant, range and seed in one frozen specification | Table 3.4, Section 3.3.3, R4 |
| `paths.py` | 49 | `ProjectPaths` | Repository relative locations of inputs and outputs | R13 |
| `cli.py` | 173 | `derive_cohort`, `seal_partition`, `run_analysis`, `run_extensions`, `freeze_artefact`, `freeze_secondary_artefact`, `summarise_results`, `meeting_evidence`, `update_readme`, `technical_report`, `draw_figures`, `load_db`, `main` | Command line entry point | R13 |
| `analysis.py` | 154 | `summary_by_experiment`, `write_tables`, `curves`, `draw`, `uniform_imputation`, `run_analysis` | The `run-analysis` command | Sections 3.3.7 to 3.3.9 |
| `study.py` | 147 | `StudyContext`, `load_context`, `experiments`, `load_results`, `clinical_rule`, `ArtefactPlan`, `freeze_artefact` | Orchestration and the artefact freeze | Section 3.3.6, B3 |
| `extensions.py` | 220 | `extension_experiments`, `pool_imputations`, `ablation`, `parameterisation`, `gbt_native`, `multiple_imputation`, `calibration_by_set`, `run_primary_model_tables`, `run_learning_curve`, `run_extensions` | The Stage 5 analyses | Section 3.3.8.1, Table 3.7 |
| `storage.py` | 214 | `ResearchBase`, `PregnancyRecord`, `VisitMeasurement`, `ModelConfiguration`, `EvaluationResult`, `database_url`, `pregnancy_frame`, `visit_frame`, `configuration_frame`, `evaluation_frame`, `load_database` | The research tables of the data model in SQLite, written by `load-db` | Section 3.4.4, Figure 3.8 |
| `data/loader.py` | 73 | `ChecksumMismatch`, `sha256_of`, `DataLoader.verify_checksum, load, provenance` | Read the file only after its checksum matches | Table 3.9 loader, R13 |
| `data/parsers.py` | 129 | `BloodPressure.within`, `SentinelPolicy.is_missing`, `BloodPressureParser.parse, parse_in_range`, `NumericParser.parse`, `YesNoParser.parse` | Pure cell parsers | Section 3.3.3 |
| `data/dictionary.py` | 145 | `FieldKind`, `RegistrationField`, `VisitMeasurement.column_for`, `measurement`, `visit_column`, `source_columns` | Map study fields to raw columns | Table 3.6, Section 3.4.4 |
| `audit/quality.py` | 129 | `suspect_field_crosstabs`, `quality_findings`, `registration_ranges`, `consistency_checks`, `non_numeric_tokens` | Data quality audit | Table 3.3, Figure 3.1 |
| `audit/missingness.py` | 77 | `wilson_interval`, `missingness_table`, `missingness_mechanism` | Missingness summaries on development records | Section 3.3.3 |
| `cohort/cleaning.py` | 105 | `group_key_of`, `hash_key`, `RecordCleaner.clean` | One typed row per record with ranges applied | Section 3.3.3 |
| `cohort/builder.py` | 162 | `Cohort.analysis, events, flow_table, manifest`; `CohortBuilder.build` and one method per step | Eligibility with a reason per excluded record | Table 3.5, R1 |
| `cohort/exclusion_log.py` | 40 | `Step`, `ExclusionLog.append, counts, to_frame` | Ordered record of eligibility steps | R1 |
| `cohort/partition.py` | 154 | `PartitionAlreadySealed`, `PartitionTampered`, `Partition.holdout_size, development`, `FoldAssignment.splits, repeats`, `grouped_outer_folds`, `PartitionWriter.seal_holdout, load, outer_folds, write_folds, load_folds` | Seal the held out partition; build the outer folds | Section 3.3.7, R3 |
| `features/screen.py` | 63 | `ScreenResult.passed, to_frame`, `AvailabilityScreen.fit` | Outcome blind availability screen | Section 3.3.4, R2 |
| `features/sets.py` | 128 | `FeatureSet` and subclasses `SetA`, `SetB`, `SetC`, `SetCWithChange`, `SetCChangeOnly`, `SetCRate`, `SetCWithout` | Nested feature sets | Table 3.6, R2, S5 |
| `features/builder.py` | 59 | `input_columns`, `change_column`, `rate_column`, `FeatureBuilder.derive, matrix` | Derived change and rate columns shared with the prototype | Table 3.6 |
| `models/factory.py` | 191 | `ModelSpec.estimator_key`, `ModelFactory.spec, build` | Every pipeline and tuning grid | Sections 3.3.5, 3.3.6 |
| `evaluation/metrics.py` | 174 | `MetricStrategy` and subclasses `AveragePrecision`, `RocAuc`, `Brier`, `CalibrationSlope`, `CalibrationIntercept`; `logit`, `sigmoid`, `calibration_slope_intercept`, `net_benefit`, `net_benefit_treat_all`, `score_all` | Metrics of Table 3.7 | Table 3.7 |
| `evaluation/bootstrap.py` | 87 | `Interval.excludes_zero, as_dict`, `GroupBootstrap.indices, single, paired_difference` | Paired group bootstrap | Section 3.3.7 |
| `evaluation/power.py` | 20 | `detectable_difference` | Smallest detectable difference | Section 3.3.9 |
| `evaluation/nested_cv.py` | 170 | `Experiment`, `FittedModel`, `CVResults.averaged, merge`, `NestedCVRunner.fit, run` | Repeated nested grouped cross validation | Section 3.3.7, Figure 3.3 |
| `evaluation/comparisons.py` | 121 | `Comparison`, `primary_comparisons`, `ComparisonRunner.run, performance` | Table 1.1 comparisons with intervals | Table 1.1 |
| `evaluation/sensitivity.py` | 97 | `core_comparisons`, `SensitivityRunner.cohort_variant, complete_measurements, rate_per_week, run_all` | S1 to S6 | Table 3.8 |
| `evaluation/calibration.py` | 32 | `calibration_table` | Calibration curve data | Table 3.7 |
| `evaluation/decision_curve.py` | 28 | `decision_curve_table` | Net benefit data | Proposal Section 3.3.8 |
| `evaluation/learning_curve.py` | 205 | `subsample_groups`, `LearningCurveResult`, `LearningCurve.run`, `intervals`, `summarise` | Learning curve with group bootstrap intervals per fraction | Stage 5, R6 |
| `evaluation/missingness_signal.py` | 90 | `newcombe_difference`, `outcome_by_recording`, `indicator_comparisons` | Informative missingness | Research question 4 |
| `evaluation/subgroups.py` | 70 | `strata`, `subgroup_table` | Subgroups with the 30 event rule | Table 3.7 |
| `evaluation/retrieval.py` | 61 | `RetrievalAtBudget.compute`, `retrieval_table` | Retrieval within ranking budgets | Research question 3, Section 3.3.8.1 |
| `evaluation/holdout.py` | 115 | `HoldoutAccessRefused`, `HoldoutEvaluator.load_holdout, check_first_evaluation, record_evaluation, evaluate_once, evaluations_logged` | The only gate to the held out partition | R3, R5, Table 3.1 stage 4 |
| `artefact/artefact.py` | 177 | `build_timestamp`, `Assessment.caseload_size`, `FittedPipelineArtefact.score, rank_of, assess, params, version_record, save, load` | The frozen fitted pipeline | Section 3.3.6, R12, R16 |
| `artefact/interval.py` | 55 | `design_rows`, `coefficient_covariance`, `wald_interval` | Interval on one probability | Table 3.7 last row |
| `reporting/style.py` | 82 | `count_label`, `add_limitation`, `save` | Shared figure style; the limitation footer is added once in `save` | R6, R7 |
| `reporting/figures.py` | 149 | `cohort_flow`, `outcome_prevalence`, `measurement_distributions`, `missingness`, `availability_screen` | Descriptive figures | Figure 3.2 |
| `reporting/result_figures.py` | 186 | `model_comparison`, `feature_set_differences`, `calibration`, `decision_curve`, `detectable_difference`, `sensitivity` | Result figures | R6 |
| `reporting/extension_figures.py` | 134 | `learning_curve`, `forest`, `missingness_rates`, `retrieval` | Stage 5 figures | R6 |
| `reporting/redraw.py` | 79 | `redraw_all` | Redraw the sixteen figures from the tables (`draw-figures`) and refresh the manifest | R7, R13 |
| `reporting/manifest.py` | 59 | `library_versions`, `git_commit`, `write_manifest` | Run manifest with checksums | R4, R13 |
| `reporting/results_summary.py` | 221 | `SummaryBuilder.table, add, add_comparison`, `build_results_summary` | One table of headline numbers with sources | R6 |
| `reporting/meeting_evidence.py` | 155 | `write_meeting_evidence` | Generated meeting document | Reporting |
| `reporting/readme.py` | 118 | `results_block`, `tree_block`, `render_readme`, `update_readme` | Generated README blocks | Reporting |
| `reporting/technical_report.py` | 120 | `write_technical_report` | Generated technical report | Reporting |

### 3.2 Application `webapp/app`

| File | Lines | Public classes and functions | Responsibility | Proposal link |
| --- | --- | --- | --- | --- |
| `main.py` | 65 | `create_app` | Application factory; verifies the artefact at start up | R12 |
| `core/settings.py` | 36 | `Settings.from_env` | Paths and the fixed interface text; the limitation line is imported from `antenatal.config` so figures and screens share it | R7, R11 |
| `api/deps.py` | 24 | `model_service`, `case_service`, `ranking_service` | Service access for routers | Separation of concerns |
| `api/health.py` | 32 | `health`, `artefact`, `interface_text` | Health, artefact record, fixed text | R12, R16 |
| `api/predict.py` | 19 | `predict` | Stateless scoring | Section 3.4.2 |
| `api/cases.py` | 50 | `create_case`, `get_case`, `save_visit`, `assess`, `caseload` | Case, visit, assessment and caseload routes | Table 3.10 |
| `schemas/cases.py` | 130 | `CaseCreate`, `VisitCreate`, `PredictRequest`, `VisitOut`, `AssessmentOut`, `CaseOut`, `CaseloadRow`, `CaseloadOut`, `FieldError` | Request and response shapes | Table 3.10 |
| `services/validation.py` | 113 | `EntryRefused`, `EntryRules.check_case, check_visit` | Synthetic flag, ranges, timing | R9, R10 |
| `services/model_service.py` | 87 | `study_values`, `ModelService.predict, health, version` | Single scoring path through the artefact | R12 |
| `services/case_service.py` | 171 | `CaseNotFound`, `StepOutOfOrder`, `CaseService.create, save_visit, assess, assessment_out, describe, score` | Store cases and visits; record assessments | R10, R16 |
| `services/ranking_service.py` | 55 | `RankingService.caseload` | Caseload ordering | Table 3.10 screen 5, R11 |
| `db/models.py` | 106 | `Base`, `SyntheticCase`, `SyntheticVisit`, `Assessment` | SQLite tables | Figure 3.7 interface side |
| `db/database.py` | 28 | `create_session_factory` | Engine and tables on start up | Figure 3.7 |
| `../static/index.html` | 264 | Five screens in one page | Thin client over the API | Table 3.10 |

### 3.3 Notebooks, scripts, tests and documents

| Item | Size | Responsibility |
| --- | --- | --- |
| `notebooks/01_data_audit.ipynb` | 26 cells, 14 code, 0 error outputs | Audit narrative over the package |
| `notebooks/02_model_notebook.ipynb` | 48 cells, 23 code, 0 error outputs | Results narrative over the output tables |
| `scripts/input_variation.py` | 198 lines | Twelve inputs against a running API |
| `scripts/record_test_results.py` | 87 lines | Writes `docs/evidence/test_summary.json` |
| `scripts/benchmark_api.py` | 229 lines | Start up, latency and memory of the API; writes `docs/evidence/performance.md` |
| `scripts/render_designs.py` | 113 lines | Draws `designs/web/` from the running interface |
| `scripts/build_report_pdf.py` | 86 lines | Report PDF on A4, Times New Roman 11, fails above five pages |
| `scripts/package_attempt2.py` | 88 lines | Submission zip from `git archive HEAD`, the PDF, a video and `RUN.md` |
| `tests/unit/` | 12 files, 188 tests in the run | See Section 5.1 |
| `tests/integration/` | 3 files, 41 tests in the run | See Section 5.1 |
| `tests/e2e/` | 2 files plus `__init__.py`, 6 tests in the run | Five screen flow in three browsers at two sizes |
| `README.md` | 1,866 words (`wc -w`) | Overview, status, install, run, submission |
| `docs/ARCHITECTURE.md` | 947 words | Module diagram, request flow, data model |
| `docs/Technical-Report.md` | 2,240 words | Generated report |
| `docs/Technical-Report.pdf` | 5 pages | Built by `scripts/build_report_pdf.py` |
| `docs/VIDEO_SCRIPT.md` | 655 words | Timed outline for the walkthrough video |
| `docs/ethics_note.md` | 684 words | Dataset ethics status |
| `docs/deviations.md` | 633 words | Deviation log |
| `docs/tripod_ai_checklist.md` | 1,205 words | TRIPOD+AI mapping |
| `docs/tripod_ai_pending.md` | 262 words | Seven items for the author |
| `docs/meeting_evidence.md` | 1,252 words | Generated meeting document |
| `docs/evidence/input_tests.md` | 443 words | Input variation results |
| `docs/evidence/performance.md` | 240 words | API performance on one machine |
| `docs/evidence/compatibility.md` | 93 words, 30 screenshots in `compatibility/` | Browser compatibility matrix |
| `designs/README.md` | 151 words | The five design images |
| `CHANGELOG.md` | 451 words | Change history |
| `data/README.md` | 251 words | Data source and checksum |

## 4. Proposal feature table

Statuses: Completed, Partial, Not built. "Deviated" is noted inside the status where the built form differs from the proposal.

| Planned feature | Intended purpose | Current status | Evidence |
| --- | --- | --- | --- |
| Table 3.1 stage 1: loader, cleaning, eligibility | Reproduce Table 3.5 | Completed | `outputs/tables/cohort_flow.csv`; `tests/unit/test_cohort.py::test_flow_count` |
| Table 3.1 stage 2: partition writer | Seal held out partition first | Completed | `partitions/`; `tests/unit/test_partition.py` |
| Table 3.1 stage 3: nested cross validation module | Reproducible results from a seed | Completed | `outputs/tables/cv_fold_metrics.csv`; `tests/integration/test_pipeline_end_to_end.py` |
| Table 3.1 stage 4: held out evaluation module | Evaluate once with a timestamp | Partial: code written and tested on synthetic data; not run | `src/antenatal/evaluation/holdout.py`; `tests/unit/test_artefact_and_outputs.py::test_evaluate_once_on_a_synthetic_cohort` |
| Table 3.1 stage 5: recording screens | Save synthetic cases with ranges enforced | Completed | `docs/evidence/input_tests.md`; `tests/integration/test_api.py` |
| Table 3.1 stage 6: assessment and caseload screens | Load verified artefact; match the pipeline | Completed | `tests/integration/test_api.py::test_api_equals_service_equals_package_pipeline` |
| Feature set A | Registration only | Completed | `src/antenatal/features/sets.py::SetA` |
| Feature set B | A plus visit two | Completed | `SetB`; `tests/unit/test_features_and_models.py::test_set_b_keeps_haemoglobin_and_set_c_drops_its_first_visit` |
| Feature set C | B plus screened visit one values | Completed | `SetC`; `test_linear_set_c_has_no_change_or_rate_terms` |
| Model family: regularised logistic regression | Main model | Completed | `src/antenatal/models/factory.py` |
| Model family: gradient boosted trees, native missing handling | Second family | Completed | `factory.py`; `test_gradient_boosting_handles_missing_values_natively` |
| B0 constant prevalence | No skill floor | Completed | `outputs/tables/feature_set_comparisons.csv` rows over B0 |
| B1 registration only logistic | Reference for added measurements | Completed | `summary_by_experiment.csv`, logistic set A |
| B2 eight family screen on set C | Evidence for the main model | Completed | `outputs/tables/model_performance.csv`; `fig06_model_families.png` |
| B3 clinical rule, 140/90 at visit two | Descriptive context | Completed | `outputs/tables/clinical_rule_b3.csv` |
| Primary hypothesis, C over B on PR AUC | The research question | Completed on development records | Section 1.2 |
| Secondary hypothesis, B over A on ROC AUC | Pre specified secondary | Completed on development records | Section 1.3 |
| Baseline hypothesis, each set over B0 | Supporting | Completed | `feature_set_comparisons.csv`, role `supporting` |
| Metrics: PR AUC, ROC AUC, Brier, calibration, paired difference | Table 3.7 | Completed | `outputs/tables/summary_by_experiment.csv`, `calibration_by_set.csv` |
| Metric: subgroup performance with 30 event rule | Table 3.7 | Completed | `outputs/tables/subgroups.csv` |
| Metric: interval on one probability | Shown in the prototype | Completed | `src/antenatal/artefact/interval.py`; `test_wald_logit_matches_estimator` |
| Retrieval within ranking budgets (Section 3.3.8.1) | Research question 3 | Completed | `outputs/tables/retrieval_at_budget.csv` |
| Detectable difference (Section 3.3.9) | Read the null result | Completed | `outputs/tables/detectable_difference.csv` |
| S1 visit two by 24 weeks | Sensitivity | Completed | `sensitivity_analyses.csv` |
| S2 visit two by 32 weeks | Sensitivity | Completed | `sensitivity_analyses.csv` |
| S3 excluding term and preterm records | Sensitivity | Completed | `sensitivity_analyses.csv` |
| S4 complete screened measurements | Sensitivity | Completed | `sensitivity_analyses.csv` |
| S5 rate per week | Sensitivity | Completed | `sensitivity_analyses.csv` |
| S6 lower bound 0.5 kg | Sensitivity | Completed | `sensitivity_analyses.csv` |
| Screen 1 Register | Capture set A, synthetic flag | Completed; deviated: does not capture prior live births or stillbirths shown in the wireframe, because Table 3.6 does not use them | `webapp/static/index.html` |
| Screen 2 Visit one | Capture visit one | Completed | `index.html` |
| Screen 3 Visit two | Capture visit two; show haemoglobin screen result | Completed | `index.html`; `GET /api/artefact` |
| Screen 4 Assessment | Rank, probability, interval, prevalence, events, version, limitation | Completed | `index.html`; `tests/integration/test_api.py::test_add_visits_and_assess` |
| Screen 5 Caseload | Ordered synthetic cases with banner and limitation | Completed | `index.html`; `test_caseload_orders_by_probability` |
| R1 cohort counts and per record exclusion reasons | Requirement | Completed | `outputs/cohort_manifest.csv`; `test_manifest_has_one_row_per_record_with_reasons` |
| R2 sets from one specification, screen reported | Requirement | Completed | `outputs/tables/availability_screen.csv` |
| R3 seal before any model, never regenerate | Requirement | Completed | `test_sealing_twice_is_refused`; `test_load_verifies_checksum` |
| R4 record and report the seed | Requirement | Completed | `outputs/manifest.json` field `seed`; `StudySpec.seed` |
| R5 log every held out access with a timestamp | Requirement | Completed in code; no access has occurred, so no log exists | `test_holdout_refused_without_confirmation_and_logged` |
| R6 every performance figure with event count and interval | Requirement | Completed: every figure title states n and events; the learning curve and the fold level summary carry 95 percent group bootstrap intervals beside the spread across repeats | `learning_curve.csv`, `summary_by_experiment.csv`; `test_learning_curve_carries_bootstrap_intervals`, `test_fold_level_summary_carries_bootstrap_intervals` |
| R7 limitations beside every performance figure and on every screen | Requirement | Completed: all sixteen figures carry the limitation line as a footer, added once in `reporting/style.py`; the banner is on every screen and the limitation line on Assessment and Caseload | `test_every_figure_carries_the_limitation_footer`, `test_app_and_figures_share_one_limitation_line`, `test_draw_figures_redraws_all_sixteen` |
| R8 attributions labelled as model behaviour | Requirement | Completed | `notebooks/02_model_notebook.ipynb` section 11 |
| R9 ranges and timing at entry | Requirement | Completed | `docs/evidence/input_tests.md` rows 3 to 10 |
| R10 block saving without the synthetic flag | Requirement | Completed | `test_synthetic_flag_required`; input test row 2 |
| R11 rank and probability with interval, no category | Requirement | Completed | `test_interface_text_has_no_triage_language` |
| R12 load only the verified artefact | Requirement | Completed | `test_tampered_artefact_refuses_to_start` |
| R13 reproduce from the file and code alone | Requirement | Partial: commands reproduce outputs and model content; artefact bytes differ on refit; never run in a clean container or on CI | `tests/integration/test_artefact_reproducibility.py`; `docs/deviations.md` |
| R14 transmit no record outside the local environment | Requirement | Completed: no module in `src` or `webapp/app` imports an HTTP or socket client; for the same reason the application is not hosted (`docs/deviations.md`, row "Cloud hosting") | `grep -rn "import requests\|import httpx\|import urllib" src webapp/app` returns nothing |
| R15 recommend no referral or clinical action | Requirement | Completed | Limitation text in `webapp/app/core/settings.py` |
| R16 record artefact version, checksum, reference size per assessment | Requirement | Completed | `webapp/app/db/models.py::Assessment`; `test_stored_assessment_records_artefact_identity` |
| Data model: PREGNANCY_RECORD | Store cohort records | Completed: table `pregnancy_records`, 8,817 rows from `outputs/cohort_manifest.csv` | `storage.py`; `python -m antenatal load-db`; `test_pregnancy_records_hold_every_released_record` |
| Data model: VISIT_MEASUREMENT | Store visit values | Completed: table `visit_measurements`, 15,612 rows, unique per record and visit | `load-db` output; `test_visit_measurements_are_unique_per_record_and_visit` |
| Data model: EXCLUSION_LOG | Exclusion reasons | Completed as files | `cohort_flow.csv`, `cohort_manifest.csv` |
| Data model: PARTITION_ASSIGNMENT | Fold and held out assignment | Completed as files | `partitions/` |
| Data model: MODEL_CONFIGURATION | Frozen configuration | Completed: table `model_configurations`, 2 rows (sets B and C) from `version.json` and `model_params.json` | `test_model_configurations_match_the_frozen_artefacts` |
| Data model: PIPELINE_ARTEFACT | Artefact with checksum | Completed | `webapp/model/` |
| Data model: EVALUATION_RESULT | Results per fold and held out | Partial: table `evaluation_results`, 800 fold rows from `cv_fold_metrics.csv`; held out result not built (Stage 4) | `test_evaluation_results_match_the_fold_metrics` |
| Data model: SYNTHETIC_CASE | Interface case | Completed; deviated: fields follow Table 3.6, not every registration attribute of Figure 3.7 | `db/models.py` |
| Data model: SYNTHETIC_VISIT | Interface visit, unique per case and visit | Completed | `db/models.py`; `test_visit_is_replaced_not_duplicated` |
| Data model: ASSESSMENT | Interface result | Completed | `db/models.py` |
| Database technology | PostgreSQL (Table 3.12) | Deviated: SQLite file, local only, through SQLAlchemy; logged in `docs/deviations.md` | `webapp/app/db/database.py`, `src/antenatal/storage.py` |
| Frontend technology | React.js (Table 3.12) | Not built: the interface is plain HTML and JavaScript; a Next.js build, which is built on React, is Stage 6; logged in `docs/deviations.md` | `webapp/static/index.html` |
| Section 3.6: unit tests of parsing | Testing commitment | Completed | `tests/unit/test_parsers.py` |
| Section 3.6: range rules | Testing commitment | Completed | `test_numeric_parser_applies_bounds`; `test_visit_range_refused` |
| Section 3.6: eligibility evaluation | Testing commitment | Completed | `tests/unit/test_cohort.py` |
| Section 3.6: availability screen | Testing commitment | Completed | `test_screen_passes_and_fails_on_development`, `test_screen_never_reads_the_outcome` |
| Section 3.6: feature construction | Testing commitment | Completed | `test_sets_are_nested`, `test_builder_derives_changes_and_fills_missing_inputs` |
| Section 3.6: synthetic flag check | Testing commitment | Completed | `test_synthetic_flag_required` |
| Section 3.6: artefact checksum and refusal to start | Testing commitment | Completed | `test_tampered_artefact_is_refused`, `test_tampered_artefact_refuses_to_start` |
| Section 3.6: refusal of visit two not later or beyond 28 weeks | Testing commitment | Completed | `test_visit_two_not_later_than_visit_one_refused`, `test_visit_two_after_cutoff_refused` |
| Section 3.6: optional walkthrough | Task check with health workers | Not built: pending ALU determination | `docs/ethics_note.md` |
| Cloud hosting for the demonstration (budget line) | Availability during the defence | Not built by decision: hosting would send entered values to a remote server, against R14; the demonstration runs locally; awaits the supervisor's view | `docs/deviations.md` |
| Figma results view design | Design reference | Completed; deviated: replaced by five screenshots of the running interface, drawn by `scripts/render_designs.py`; the sign in screens were removed | `designs/web/`, `designs/README.md` |
| API performance evidence | Evidence that the prototype responds quickly | Completed on one machine | `docs/evidence/performance.md`; `test_performance_evidence_is_complete` |
| Browser compatibility evidence | Evidence that the five screens work across browsers and sizes | Completed: 6 of 6 runs pass | `docs/evidence/compatibility.md`; `tests/e2e/test_compatibility.py` |
| Technical report PDF | Submission | Completed: 5 pages, the limit | `docs/Technical-Report.pdf`; `test_report_pdf_is_a4_and_at_most_five_pages` |

## 5. Engineering quality evidence

### 5.1 Tests and coverage

Command: `.venv/bin/pytest tests --cov --cov-report=term` (or `make test`). Recorded run file: `docs/evidence/test_summary.json` (written by `scripts/record_test_results.py`).

| Test file | Tests in the run |
| --- | --- |
| `tests/unit/test_features_and_models.py` | 44 |
| `tests/unit/test_parsers.py` | 38 |
| `tests/unit/test_extensions.py` | 21 |
| `tests/unit/test_cohort.py` | 19 |
| `tests/unit/test_artefact_and_outputs.py` | 17 |
| `tests/unit/test_metrics.py` | 13 |
| `tests/unit/test_data_and_audit.py` | 10 |
| `tests/unit/test_partition.py` | 10 |
| `tests/unit/test_cli_and_missingness.py` | 7 |
| `tests/unit/test_storage.py` | 5 |
| `tests/unit/test_submission_files.py` | 3 |
| `tests/unit/test_performance_evidence.py` | 1 |
| `tests/integration/test_api.py` | 22 |
| `tests/integration/test_pipeline_end_to_end.py` | 16 |
| `tests/integration/test_artefact_reproducibility.py` | 3 |
| `tests/e2e/test_compatibility.py` | 6 |
| Total | 235: 188 unit, 41 integration, 6 browser, 0 failed, 0 skipped |

The browser tests (marked `e2e`) use Playwright and are skipped when Playwright or a browser is absent, so `make test` still runs on a machine without browsers; `make browsers` installs them.

Coverage by module, from the coverage JSON of the run: every module is at 100 percent except these.

| Module | Statements | Missed | Percent |
| --- | --- | --- | --- |
| `src/antenatal/__main__.py` | 2 | 2 | 0.0 |
| `src/antenatal/cli.py` | 85 | 32 | 62.4 |
| `src/antenatal/data/dictionary.py` | 39 | 7 | 82.1 |
| `src/antenatal/evaluation/learning_curve.py` | 88 | 7 | 92.0 |
| `src/antenatal/data/loader.py` | 34 | 2 | 94.1 |
| `src/antenatal/reporting/readme.py` | 57 | 3 | 94.7 |
| `src/antenatal/cohort/exclusion_log.py` | 22 | 1 | 95.5 |
| `src/antenatal/evaluation/bootstrap.py` | 48 | 2 | 95.8 |
| `src/antenatal/artefact/artefact.py` | 105 | 4 | 96.2 |
| `src/antenatal/reporting/manifest.py` | 28 | 1 | 96.4 |
| `src/antenatal/evaluation/nested_cv.py` | 85 | 3 | 96.5 |
| `src/antenatal/cohort/partition.py` | 88 | 2 | 97.7 |
| `webapp/app/services/validation.py` | 51 | 1 | 98.0 |
| `src/antenatal/evaluation/holdout.py` | 64 | 1 | 98.4 |
| `src/antenatal/config.py` | 68 | 1 | 98.5 |
| `src/antenatal/reporting/results_summary.py` | 78 | 1 | 98.7 |
| `webapp/app/services/case_service.py` | 84 | 1 | 98.8 |
| Total | 2,910 | 71 | 97.6 |

The largest gap is `cli.py`: every missed line lies inside the command wrappers from `run_analysis` to `load_db`, which the tests do not call; several of the functions they wrap are tested directly, for example `load_database`, `redraw_all` and `write_technical_report`.

### 5.2 Lint, format and size

`ruff check src tests webapp scripts`: "All checks passed!". `black --check src tests webapp scripts`: "101 files would be left unchanged." `make lint` runs the same two commands. Longest Python file: `tests/integration/test_api.py`, 234 lines; the longest outside tests is `src/antenatal/reporting/results_summary.py`, 221 lines. Longest function: `main` in `scripts/record_test_results.py`, 43 lines. Both measured with a script over `src/antenatal`, `webapp/app`, `scripts` and `tests` using Python's `ast` module; no file exceeds 300 lines and no function exceeds 50.

### 5.3 Object oriented design

Abstract base classes and subclasses:
* `MetricStrategy` (`evaluation/metrics.py`): `AveragePrecision`, `RocAuc`, `Brier`, `CalibrationSlope`, `CalibrationIntercept`, and `RetrievalAtBudget` (`evaluation/retrieval.py`).
* `FeatureSet` (`features/sets.py`): `SetA`, then `SetB(SetA)`, `SetC(SetB)`, `SetCWithChange(SetB)`, `SetCChangeOnly(SetB)`, `SetCRate(SetC)`, `SetCWithout(SetC)`.

Factories: `ModelFactory.build` (`models/factory.py`) builds every pipeline and grid from a `ModelSpec`; `create_app` (`webapp/app/main.py`) builds the application; `create_session_factory` (`db/database.py`); `StudySpec.variant` builds sensitivity specifications; `grouped_outer_folds` builds fold assignments.

Dataclasses used as contracts: `Range`, `PhysiologicalRanges`, `StudySpec`, `ProjectPaths`, `RegistrationField`, `VisitMeasurement`, `BloodPressure`, `Step`, `ExclusionLog`, `Cohort`, `Partition`, `FoldAssignment`, `ScreenResult`, `ModelSpec`, `Experiment`, `FittedModel`, `CVResults`, `LearningCurveResult`, `Comparison`, `Interval`, `Assessment`, `FittedPipelineArtefact`, `StudyContext`, `ArtefactPlan`, `Settings`, and `Variation` in `scripts/input_variation.py`. Pydantic models play the same role at the API boundary (`webapp/app/schemas/cases.py`). SQLAlchemy declarative classes describe the stored tables on both sides: `SyntheticCase`, `SyntheticVisit` and `Assessment` for the interface (`webapp/app/db/models.py`), and `PregnancyRecord`, `VisitMeasurement`, `ModelConfiguration` and `EvaluationResult` for the research data (`src/antenatal/storage.py`).

Polymorphism in place of branching: `NestedCVRunner.fit` calls `experiment.feature_set.columns(screen, family)` and never tests a set's name; `score_all`, `ComparisonRunner.run` and `GroupBootstrap.single` loop over `MetricStrategy` objects and never test a metric's name; `ModelFactory.build` reads the imputer, scaling and grid from `ModelSpec` instead of branching per family.

### 5.4 Algorithms and custom logic

| Algorithm | File | Description | Cost |
| --- | --- | --- | --- |
| Blood pressure parsing with a sentinel policy | `data/parsers.py` | A regular expression takes the first pair of two or three digit numbers around a slash; sentinel tokens such as "not_checked" return no reading. Range checking is a separate step, so "121/20" is parsed then rejected. | Linear in the cell length, per cell |
| Cohort derivation with exclusion log | `cohort/builder.py` | One named method per eligibility step returns a boolean mask; each step records how many records it removed and the reason on each record. | Linear in records per step, eight steps |
| Grouped stratified partitioning | `cohort/partition.py` | Records sharing a registration profile form a group; scikit-learn `StratifiedGroupKFold` assigns whole groups to folds while balancing events, and the first fold is sealed. | About linear in records plus groups per split, ten repeats of five folds |
| Availability screen | `features/screen.py` | For each measurement, the share of records with values at both visits; passes at the threshold. Reads no outcome. | Linear in records times measurements, refitted per training fold |
| Repeated nested grouped cross validation | `evaluation/nested_cv.py` | For each repeat and outer fold, tune on grouped inner folds by average precision, refit and predict the outer fold. | For L2 logistic, ten repeats times five folds times (four grid values times three inner folds plus one refit), 650 fits per experiment |
| Paired group bootstrap | `evaluation/bootstrap.py` | Predictions are averaged per record across repeats; registration groups are resampled and the paired metric difference recomputed. | 2,000 resamples times two metric evaluations of order n log n |
| Detectable difference | `evaluation/power.py` | (z for a two sided 5 percent test plus z for 80 percent power) times the bootstrap standard error. | Constant |
| Calibration slope and intercept | `evaluation/metrics.py` | Unpenalised logistic regression of the outcome on the logit of the prediction by Newton steps; the intercept fit uses the logit as an offset. | Linear in records per Newton step, at most 50 steps |
| Wald interval on one probability | `artefact/interval.py` | The coefficient covariance is the inverse penalised Hessian of the fitted design; the logit standard error of a new case gives the interval. | One p by p inversion at freeze time; order p squared per case |
| Net benefit | `evaluation/metrics.py` | True positives minus false positives weighted by threshold odds, per pregnancy. | Records times thresholds |
| Learning curve | `evaluation/learning_curve.py` | Training folds cut to a fraction of their groups, refitted, and the full test fold predicted; predictions are averaged per pregnancy across repeats and a paired group bootstrap gives an interval for each set and for the gap at each fraction. | Five fractions times two sets times 50 fold fits, then 2,000 resamples per fraction |
| Retrieval at budget | `evaluation/retrieval.py` | Share of events among the top k percent by predicted probability. | Sort of order n log n per evaluation |
| Newcombe difference | `evaluation/missingness_signal.py` | Interval for a difference of two proportions combining two Wilson intervals. | Constant |
| Multiple imputation pooling | `extensions.py` | Five iterative imputations with posterior draws; probabilities averaged per record before the bootstrap. | Five times the nested cross validation cost, each fit running up to ten imputation rounds |
| Rank against the reference caseload | `artefact/artefact.py` | One plus the number of reference probabilities above the case's probability. | Linear scan over 3,126 values per case |

### 5.5 Commit history

`git rev-list --count HEAD`: 65 commits before this report's own commit. First: 2026-10-01 22:58:29 +0200, `22b8192` "commit". Last: 2026-10-22 12:31:45 +0200, `28f9d75`. Of these, 58 (`git rev-list --count 1362f7e..HEAD`) were made during finalisation with descriptive messages; the seven earlier commits are named "commit" or "Add files via upload". Ten representative messages:

1. `d3c363b` Seal holdout partition before any screen or model step (C07)
2. `daf1797` Derive the cohort with one method per Table 3.5 step (R1)
3. `c25bec5` Freeze the artefact as the development fit, not a full cohort refit
4. `d40ef51` Build feature sets A, B and C from Table 3.6 with a fold level screen
5. `62293ff` Make the interface a thin client of the API with no triage wording (R11)
6. `48961b8` Use native missing value handling for gradient boosted trees (Section 3.3.6)
7. `d52d5b9` Add Question 3 retrieval within 10, 20 and 30 percent ranking budgets
8. `63607f6` Rewrite the README to describe the repository as it is
9. `b2621a7` Test artefact reproducibility on model content, not file bytes
10. `73082ea` State the missing ethics statement, the request to the producers and the version choice
11. `4e3eefe` Report group bootstrap intervals beside every spread across repeats (R6)
12. `968e06a` Store the research data model in SQLite with a load-db command (Section 3.4.4)
13. `8032597` Draw the design images from the running interface and remove sign in screens (R11)

### 5.6 Continuous integration

`.github/workflows/ci.yml` runs on push and pull request: checkout, Python 3.12 setup, install from `requirements-dev.txt`, a SHA 256 check of the data file, `ruff check`, `black --check`, and `pytest --cov` with a coverage XML uploaded as an artefact. It has not yet run on GitHub, because nothing from finalisation has been pushed. Two gaps against CLAUDE.md Section 5: its lint step checks `src tests webapp` but not `scripts`, and it does not install browsers, so the six browser tests would be skipped on the runner.

## 6. Interface and API

### 6.1 Routes

Request and response schemas are from the application's OpenAPI document (`create_app().openapi()`); messages are from `webapp/app/services/validation.py` and `case_service.py`.

| Method and path | Request | Success | Refusals |
| --- | --- | --- | --- |
| `GET /health` | None | 200 with status, artefact version and SHA 256, data and partition SHA 256, prevalence, events, feature count, reference caseload size | None |
| `GET /api/artefact` | None | 200 with `webapp/model/version.json` | None |
| `GET /api/interface-text` | None | 200 with banner, limitation and interval label | None |
| `POST /api/cases` | `CaseCreate` | 201 `CaseOut` | 422 "Saving is blocked: tick the synthetic flag. No real pregnancy may be entered."; 422 "<field> is required"; 422 "<field> must be between <low> and <high> <unit>; <value> is outside the cleaning range"; 422 type errors from Pydantic |
| `GET /api/cases/{case_id}` | None | 200 `CaseOut` | 404 "No synthetic case with id <id>" |
| `PUT /api/cases/{case_id}/visits/{visit_number}` | `VisitCreate`; visit number 1 or 2 | 200 `CaseOut` | 422 range and required messages as above; 422 "Visit <n> must be at or before 28 weeks; <value> is later"; 422 "Visit two must be later than visit one (<week> weeks); <value> is not"; 409 "Record visit one before visit two"; 404 unknown case; 422 visit number outside 1 to 2 |
| `POST /api/cases/{case_id}/assessment` | None | 201 `AssessmentOut` | 409 "Both visits must be recorded before an assessment"; 404 unknown case |
| `GET /api/caseload` | None | 200 `CaseloadOut` | None |
| `POST /api/predict` | `PredictRequest` | 200 `AssessmentOut`, not stored | 422 with every case and visit refusal listed together |

Range labels: maternal age, number of pregnancies, prior deliveries, height, registration weight; gestational week, systolic and diastolic blood pressure, weight, pulse rate, haemoglobin. Ranges come from `StudySpec.ranges`. Pulse and haemoglobin may be left empty; every other value is required.

The server refuses to start when the artefact checksum does not match (`ChecksumMismatch` from `create_app`; `test_tampered_artefact_refuses_to_start`).

### 6.2 Screens

Source: `webapp/static/index.html`, 264 lines. Every screen carries the banner "Synthetic cases only. Do not enter any real pregnancy." fetched from `/api/interface-text`. No logo and no circled numbers.

| Screen | Shows | Refuses (messages from the API) |
| --- | --- | --- |
| Register | Five numeric fields, nine yes or no boxes, a locked and ticked synthetic box | Missing or out of range values |
| Visit one | Six measurement fields | Out of range values; visit after 28 weeks |
| Visit two | Six fields; the haemoglobin availability screen result from `/api/artefact` | As visit one, plus not later than visit one; entering before visit one |
| Assessment | Rank as "position of reference size plus one", probability, labelled interval, development prevalence and events, artefact version and short SHA 256, limitation line | Assessment before both visits |
| Caseload | Assessed cases by probability with position, probability, interval and reference rank; interval label, prevalence, events, version, limitation line | None |

Computation in the browser: no model computation. The page formats percentages and adds one to the reference caseload size for display (`index.html`, two occurrences of `reference_caseload_size+1`). Probability, interval and rank come from the API. The five screens are walked through automatically by `tests/e2e/test_compatibility.py` (Section 6.4), which saves one screenshot per screen. The same flow at 1366 by 768 in Chromium draws the design images in `designs/web/`.

### 6.3 Input variation tests

From `docs/evidence/input_tests.md`, run against a live server on 2026-10-21T17:00:49+00:00. 12 of 12 behaved as expected.

| No. | Input | Expected | Observed status | Observed | Result |
| --- | --- | --- | --- | --- | --- |
| 1 | Typical complete case | 201, assessment returned | 201 | probability 0.0597, rank 983 of 3127 | pass |
| 2 | Synthetic flag not set | 422, message contains "synthetic flag" | 422 | Saving is blocked: tick the synthetic flag. No real pregnancy may be entered. | pass |
| 3 | Age 121 | 422, message contains "Maternal age must be between 12 and 55" | 422 | Maternal age must be between 12 and 55 years; 121 is outside the cleaning range | pass |
| 4 | Age 55, upper boundary | 201, assessment returned | 201 | probability 0.0399, rank 2148 of 3127 | pass |
| 5 | Height missing | 422, message contains "Height is required" | 422 | Height is required | pass |
| 6 | Visit one systolic 300 | 422, message contains "Systolic blood pressure must be between 60 and 250" | 422 | Systolic blood pressure must be between 60 and 250 mmHg; 300 is outside the cleaning range | pass |
| 7 | Visit one diastolic 20 | 422, message contains "Diastolic blood pressure must be between 30 and 160" | 422 | Diastolic blood pressure must be between 30 and 160 mmHg; 20 is outside the cleaning range | pass |
| 8 | Visit one at 30 weeks | 422, message contains "at or before 28 weeks" | 422 | Visit 1 must be at or before 28 weeks; 30 is later | pass |
| 9 | Visit two at the same week as visit one | 422, message contains "later than visit one" | 422 | Visit two must be later than visit one (16 weeks); 16 is not | pass |
| 10 | Visit two at 28 weeks, upper boundary | 201, assessment returned | 201 | probability 0.0564, rank 1157 of 3127 | pass |
| 11 | Visit two pulse and haemoglobin missing | 201, assessment returned | 201 | probability 0.0466, rank 1715 of 3127 | pass |
| 12 | Visit two entered before visit one | 409, message contains "Record visit one before visit two" | 409 | Record visit one before visit two | pass |

### 6.4 Performance and compatibility

**Performance.** From `docs/evidence/performance.md` and `performance.json`, recorded 2026-10-22T09:59:33+00:00 by `scripts/benchmark_api.py` on an Apple M3 with 8 logical cores and 8.0 GB of memory, macOS 15.5, Python 3.12.13. One uvicorn worker, client and server on the same machine.

| Measure | Value |
| --- | --- |
| Start up, launch to first `/health` answer | 1.75 seconds |
| Peak resident memory of the server | 209.5 MB |
| 500 sequential `POST /api/predict`: p50, p95, slowest | 2.6, 2.9, 6.9 ms |
| 50 concurrent requests: p50, p95, slowest | 102.0, 138.3, 139.0 ms |
| 50 concurrent requests: wall time | 0.14 seconds |

The single worker answers concurrent requests one after another, so concurrent latency includes queueing. These numbers describe one laptop, not a phone or a network.

**Compatibility.** From `docs/evidence/compatibility.md`, recorded 2026-10-22T10:27:24+00:00 by `pytest tests/e2e` on macOS 15.5 with Playwright. Each cell is the whole five screen flow, including the banner, the locked synthetic box, the interval sentence, the limitation line and the absence of triage wording.

| Browser | Version | 1366 by 768 | 390 by 844 |
| --- | --- | --- | --- |
| Chromium | 156.0.8078.4 | pass | pass |
| Firefox | 157.0 | pass | pass |
| WebKit | 27.2 | pass | pass |

6 of 6 runs passed; 30 screenshots are in `docs/evidence/compatibility/`. At 390 by 844 the step navigation scrolls sideways, so the last step labels sit off screen until scrolled; the flow still completes.

**Not built:** accessibility scores and a container run (Stage 6 and CLAUDE.md item 12).

## 7. Documentation inventory

| Document | State |
| --- | --- |
| `README.md` | Rewritten. Results table and repository tree are generated by `python -m antenatal update-readme`; `tests/unit/test_extensions.py::test_readme_generated_blocks_are_current` fails if they drift. A "Submission" section links the report PDF and holds a placeholder for the video, with the outline in `docs/VIDEO_SCRIPT.md`. |
| `docs/ARCHITECTURE.md` | Three Mermaid diagrams: modules, the request flow for one assessment, the analysis flow; a data model section for the research tables written by `load-db`. |
| `docs/ethics_note.md` | The gap: the release has no ethics approval or consent statement; a request was sent to the producers on 21 October 2026. A marked placeholder stands where the statement would be quoted. The walkthrough is recorded as a proposed activity pending ALU determination. |
| `docs/deviations.md` | Thirteen rows, including Table 3.8 counts, S4 defined on development records only (2,504 with 144 events), the pulse range confirmed against `StudySpec`, the tree missing value handling, the iterative imputer option, artefact reproducibility, the newer dataset version, the missing ethics statement, cloud hosting against R14, and React.js and PostgreSQL in Table 3.12 against the Next.js plan and SQLite. |
| `CHANGELOG.md` | Version 1.0.0 dated 2026-10-21 and an Unreleased section listing Stage 4, Stage 6 and the container image as not done. Not yet updated for CLAUDE.md items 1 to 9: its Unreleased section still lists cross browser tests, the latency benchmark and regenerated designs as not done. |
| `docs/tripod_ai_checklist.md` | Every item of the TRIPOD+AI checklist version of 11 January 2024 mapped to a file. Pending: 2, 18a, 18b, 18c, 18d, 19, 27c (need statements from the author, listed with prompts in `docs/tripod_ai_pending.md`), and 20c (needs Stage 4). Item 17 is partly answered. |
| `docs/Technical-Report.md` | 2,240 words (`wc -w`), generated by `python -m antenatal technical-report` from `src/antenatal/reporting/templates/technical_report.md`. Generated numbers: cohort and partition counts, every result and interval, test counts, coverage, lint status, input test table, commit count, and design constants from `StudySpec`. No unfilled fields remain (`test_technical_report_fills_every_field_from_files`). It does not yet contain the seven author statements or an abstract. `scripts/build_report_pdf.py` (`make report-pdf`) prints it to `docs/Technical-Report.pdf`: 5 pages, exactly the limit, so any added text needs a cut elsewhere. The commit count it states is the count at generation time. |
| `docs/VIDEO_SCRIPT.md` | A ten minute outline in seven timed parts with commands, addresses and files. Its parts A to E follow the report's five sections, because the assignment brief's own Section 2 headings are not in the repository; each is marked "To confirm". |
| `designs/README.md` | Lists the five design images and how to redraw them. |
| `docs/meeting_evidence.md` | Generated by `python -m antenatal meeting-evidence`. Cohort flow, partitions, both families' results, learning curve, S1 to S6, missingness, and a "Not yet complete" section. |

## 8. Not built, deviated or placeholder

Hours are estimates by the author of this report, not measurements.

| Item | Status | Reason | What it would take | Estimated hours |
| --- | --- | --- | --- | --- |
| Stage 4 single held out evaluation | Not built | Waits for the supervisor to review the analysis plan | Confirm review, run `HoldoutEvaluator.evaluate_once`, add the result to the report and TRIPOD item 20c (CLAUDE.md item 10) | 3 |
| Stage 6 Next.js interface | Not built | Runs only on instruction (CLAUDE.md item 11) | Build five pages over the existing API, serve the static build from FastAPI, rerun the browser tests, benchmark and designs | 20 |
| Container image | Not built | Docker is not installed on the development machine (CLAUDE.md item 12) | Build and run the image, fix any path issues, record the run | 3 |
| Accessibility scores | Not built | Part of Stage 6 | Lighthouse on each page | 2 |
| Phone width navigation | Cosmetic defect | At 390 by 844 the step navigation scrolls sideways, so the last step labels sit off screen | Wrap or shorten the step labels; part of Stage 6 | 0.5 |
| Demonstration video | Placeholder | Not recorded; the outline's A to E headings await the brief's wording | Confirm headings in `docs/VIDEO_SCRIPT.md`, record, add the link to the README | 3 |
| Report author statements and abstract | Placeholder | Only the author can write them; the PDF is already at five pages | Write them, cut elsewhere, rebuild with `make report-pdf` | 3 |
| TRIPOD+AI items 2, 18a to 18d, 19, 27c | Placeholder | Need statements only the author can give | Fill `docs/tripod_ai_pending.md`, move into the report | 2 |
| TRIPOD+AI item 20c | Not built | Needs Stage 4 | Compare held out and development distributions after Stage 4 | 1 |
| Ethics statement of the data producers | Placeholder | Not published with the release; request sent 21 October 2026 | Quote the reply in `docs/ethics_note.md` | 1 after a reply |
| University ethics determination | Placeholder | Not yet recorded | Record the decision in `docs/ethics_note.md` | 1 |
| Walkthrough with health workers | Not built | Optional; pending ALU determination | Obtain determination, run with synthetic cases | 6 |
| Continuous integration run | Not built | Not pushed; the workflow also omits `scripts` from lint and installs no browsers | Add `scripts` to the lint step, push, fix any environment differences on the runner | 1 |
| Clean clone and submission zip checks | Not run | CLAUDE.md Section 5 items 12 and 13 need a fresh machine or directory | Unzip the package, `make install`, `make test`, `make serve` | 1 |
| Roadmap and guideline documents | Placeholder | CLAUDE.md names `docs/Capstone-Finalisation-Roadmap.md` and `docs/Implementation-Guideline-for-Claude.md`; neither is in the repository | Add both files | 0.5 |
| CHANGELOG | Out of date | Not updated for CLAUDE.md items 1 to 9 | Move the finished items out of "Not yet done" | 0.5 |
| Cloud hosting | Not built by decision | R14 keeps every record local; logged in `docs/deviations.md` | Supervisor's view; if hosting is wanted, deploy with synthetic entry only | 4 if wanted |
| Database technology | Deviated | SQLite chosen for a local, single user prototype; Table 3.12 names PostgreSQL | Change `ANTENATAL_DATABASE_URL` and add the driver if a server is needed | 2 |
| Frontend technology | Deviated | Table 3.12 names React.js; the interface is plain HTML until Stage 6 builds the Next.js version | Stage 6 | Included above |
| Proposal Table 3.8 counts | Deviated | S1 is 2,449 not 2,444; S4 is 2,504 with 144 on development records; S5 and S6 keep 206 events | Correct the proposal | 0.5 |
| Pulse range | Deviated | Not in Section 3.3.3; confirmed as 30 to 200 in `StudySpec` | Add 30 to 200 to Section 3.3.3 | 0.5 |
| Artefact byte reproducibility | Deviated | The class gained a field after the freeze, so a refit differs in bytes but not in content | Accept, or refreeze and update the recorded checksum | 1 |

## 9. Risks for a project defence

1. **"Your main result is null. How do you know the study was not simply too small?"** The design could detect a PR AUC difference of about 0.011 for the logistic model and 0.014 for the trees; the observed differences were negative, and the learning curve gap stayed between -0.0041 and -0.0011 across repeats with no upward trend, every fraction's bootstrap interval including zero. A smaller true effect cannot be ruled out. Files: `outputs/tables/detectable_difference.csv`, `outputs/tables/learning_curve.csv`.
2. **"Was the held out partition used anywhere?"** No. It was sealed before any screen or model step, no access has been attempted, so `partitions/holdout_access.log` does not exist, and a test confirms no out of fold prediction belongs to a held out record. Files: `src/antenatal/cohort/partition.py`, `tests/unit/test_artefact_and_outputs.py::test_out_of_fold_predictions_never_include_held_out_records`.
3. **"Why should I trust a PR AUC near 0.09?"** It is above the no skill value of about 0.054 with an interval excluding zero for each set over the constant baseline, but discrimination is modest (ROC AUC 0.61 to 0.63 for logistic). File: `outputs/tables/feature_set_comparisons.csv`, `summary_by_experiment.csv`.
4. **"Is the secondary gain real?"** It excludes zero for the trees (0.0345, 0.0070 to 0.0627) and for logistic in S2, but not for logistic in the primary cohort. It is weak evidence, not a finding. File: `outputs/tables/feature_set_comparisons.csv`, `sensitivity_analyses.csv`.
5. **"Did you handle class imbalance?"** Through the metrics only; no weighting or resampling, so probabilities stay calibrated. File: `src/antenatal/models/factory.py`, `tests/unit/test_features_and_models.py::test_factory_builds_unweighted_pipelines`.
6. **"How were missing values handled, and does it matter?"** Median imputation with indicators for most models, native handling for trees, and a five draw iterative imputation sensitivity; the conclusion is unchanged under each. Files: `outputs/tables/multiple_imputation.csv`, `gbt_missing_value_handling.csv`.
7. **"Does the prototype compute the same probability as the study?"** Yes, to 1e-9: API, service and package pipeline are compared in a test, and the server refuses to start on a changed artefact. File: `tests/integration/test_api.py`.
8. **"Is the data ethically usable?"** It is released under CC BY 4.0 without identifiers, but the release has no ethics approval or consent statement; a request was sent on 21 October 2026 and the university determination is not yet recorded. File: `docs/ethics_note.md`.
9. **"Can someone reproduce your work?"** The commands reproduce every output and the model content to 1e-9 from the released file, but not the artefact bytes, CI has not run, the container has never been built, and the submission zip has not yet been installed on a clean machine. Files: `tests/integration/test_artefact_reproducibility.py`, `docs/deviations.md`.
10. **"What of the proposed system is actually built?"** The research pipeline, the artefacts, the research tables in SQLite, the API and a five screen interface are built and tested, with performance evidence on one machine, a pass in three browsers at two sizes, and a five page report PDF; the held out evaluation, the Next.js interface, accessibility scores, the container and the video are not. File: Section 8 of this document, `README.md` feature status table.

## 10. Verification commands

Run from a fresh clone with Python 3.12 available as `python3.12`. Expected outputs are those of the state described here.

```bash
git clone https://github.com/Kelvin364/Antanental_risk_model.git && cd Antanental_risk_model
make install
```

Section 2, raw file and partition checksums:

```bash
shasum -a 256 data/maternal_dataset_csv.csv partitions/holdout_ids.csv partitions/folds.parquet
# ab95366ef22dde5d13df93f10723942f5faffda8fbf0007e8efe85e4f25c1126  data/maternal_dataset_csv.csv
# 249114c363dab8a86c5acbee9bb8cfd6fddbf97b3d74b62f907d1fda01a25ea0  partitions/holdout_ids.csv
# 5df188cc31765574674da6a745987f2490ecbcc2b4f337d62f5ed9529b2132d2  partitions/folds.parquet
test -e partitions/holdout_access.log && wc -l partitions/holdout_access.log || echo "absent"
# absent
```

Section 2, cohort flow:

```bash
.venv/bin/python -m antenatal derive-cohort | tail -1
# last row: 7  Visit two later than 28 weeks  2157  3908  206
```

Section 1, results:

```bash
.venv/bin/python -c "import pandas as pd; s=pd.read_csv('outputs/tables/results_summary.csv').set_index('key'); print(s.loc[['primary_c_over_b_logistic','primary_c_over_b_gbt','secondary_b_over_a_logistic','secondary_b_over_a_gbt'],['value','ci_low','ci_high']].round(4))"
# primary_c_over_b_logistic    -0.0040 -0.0130  0.0025
# primary_c_over_b_gbt         -0.0066 -0.0173  0.0024
# secondary_b_over_a_logistic   0.0205 -0.0066  0.0476
# secondary_b_over_a_gbt        0.0345  0.0070  0.0627
```

To regenerate the results instead of reading them (several minutes each):

```bash
.venv/bin/python -m antenatal run-analysis
.venv/bin/python -m antenatal run-extensions
.venv/bin/python -m antenatal summarise-results
```

Section 5, tests, coverage and lint:

```bash
.venv/bin/pytest tests --cov --cov-report=term -q | tail -3
# TOTAL  2910  71  98%
# 235 passed  (without browsers installed, 229 pass and the browser tests are skipped)
.venv/bin/ruff check src tests webapp scripts
# All checks passed!
.venv/bin/black --check src tests webapp scripts
# All done!
# 101 files would be left unchanged.
git rev-list --count HEAD
# 65 at commit 28f9d75, before this report's own commit
```

Section 6, the API and the input tests:

```bash
.venv/bin/python -m uvicorn webapp.app.main:app --port 8000 &
curl -s http://127.0.0.1:8000/health
# {"status":"ok","artefact_version":"1.0.0","artefact_sha256":"7358b0b26f83aa6072f55986652d8691f111dbc6646a31a50ba46f94ff2d0c35", ...}
.venv/bin/python scripts/input_variation.py --base-url http://127.0.0.1:8000 && echo all-pass
# all-pass  (rewrites docs/evidence/input_tests.md with a new timestamp)
kill %1
```

Section 6.4 and the submission files:

```bash
.venv/bin/python scripts/benchmark_api.py          # rewrites docs/evidence/performance.md
make browsers && make e2e                          # rewrites docs/evidence/compatibility.md
# 6 passed
make report-pdf
# docs/Technical-Report.pdf: 5 pages (limit 5)
ANTENATAL_DATABASE_URL=sqlite:////tmp/check.sqlite3 .venv/bin/python -m antenatal load-db
# {'pregnancy_records': 8817, 'visit_measurements': 15612, 'model_configurations': 2, 'evaluation_results': 800}
```
