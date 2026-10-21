# TRIPOD+AI checklist

Reporting checklist of Collins et al. (2024), TRIPOD+AI statement, BMJ 385,
e078378. Items follow the checklist version of 11 January 2024 published at
tripod-statement.org; the wording here is a short paraphrase. "D" marks items
for model development, "E" for evaluation. This study develops a model and
evaluates it internally, so both apply.

Status values: **Reported** (answered in the named place), **Partly** (answered
with a stated gap), **Not applicable** (with the reason), **Pending** (answered
in the technical report written in Stage 7, or after the single held out
evaluation of Stage 4).

| Item | Topic | What must be reported | Where it is answered | Status |
| --- | --- | --- | --- | --- |
| 1 | Title | Development or evaluation, target population, outcome | `docs/Technical-Report.md` title; proposal title | Reported |
| 2 | Abstract | TRIPOD+AI for Abstracts | `docs/Technical-Report.md` summary | Pending |
| 3a | Background | Healthcare context and rationale, existing models | Proposal Sections 1.1, 1.2, 2.6, 2.7 | Reported |
| 3b | Background | Target population, intended purpose and users | Proposal Section 1.5; README limitations; interface banner | Reported |
| 3c | Background | Known health inequalities between groups | Proposal Section 1.1 (regional burden) | Partly: no sociodemographic inequality data in the file beyond age and parity |
| 4 | Objectives | Objectives; development or validation | Proposal Sections 1.3, 1.4 (Table 1.1) | Reported |
| 5a | Data | Data sources, rationale, representativeness | `data/README.md`; `notebooks/01_data_audit.ipynb` section 1 | Reported |
| 5b | Data | Dates of participant data | `data/README.md` (collection May 2024 to March 2025, from the dataset record) | Reported |
| 6a | Participants | Setting, number and location of centres | `data/README.md`; proposal Section 3.3.1; no facility identifier in the file | Partly: centres cannot be identified |
| 6b | Participants | Eligibility criteria | `src/antenatal/cohort/builder.py`; `outputs/tables/cohort_flow.csv`; Figure 1 | Reported |
| 6c | Participants | Treatments received and how handled | Not recorded in a usable form; outcome is under care actually given (proposal Section 3.8) | Partly |
| 7 | Data preparation | Pre processing and quality checks | `src/antenatal/data/parsers.py`; `src/antenatal/audit/quality.py`; `notebooks/01_data_audit.ipynb` | Reported |
| 8a | Outcome | Outcome definition, time horizon, rationale | `StudySpec.lbw_threshold`; proposal Table 3.4 | Reported |
| 8b | Outcome | Qualifications of outcome assessors if subjective | Recorded weight; assessors not documented by the publisher | Not applicable |
| 8c | Outcome | Blinding of outcome assessment | Retrospective records; not documented by the publisher | Not applicable |
| 9a | Predictors | Choice and pre selection of predictors | Proposal Table 3.6; `src/antenatal/features/sets.py`; availability screen | Reported |
| 9b | Predictors | Definition and timing of every predictor | `src/antenatal/data/dictionary.py`; `webapp/model/model_params.json` | Reported |
| 9c | Predictors | Qualifications of predictor assessors | Routine clinic measurements; not documented by the publisher | Not applicable |
| 10 | Sample size | How the size was reached and why sufficient | `outputs/tables/detectable_difference.csv`; Figure 10; proposal Section 3.3.9 | Reported |
| 11 | Missing data | Handling of missing data | `src/antenatal/models/factory.py`; `outputs/tables/missingness*.csv`; `outputs/tables/multiple_imputation.csv` | Reported |
| 12a | Analytical methods | How data were used and partitioned | `src/antenatal/cohort/partition.py`; `src/antenatal/evaluation/nested_cv.py` | Reported |
| 12b | Analytical methods | Handling of predictors (scaling, form) | `src/antenatal/models/factory.py`; `src/antenatal/features/sets.py` | Reported |
| 12c | Analytical methods | Model type, building steps, tuning, internal validation | `src/antenatal/models/factory.py`; `src/antenatal/evaluation/nested_cv.py` | Reported |
| 12d | Analytical methods | Heterogeneity across clusters | No cluster identifier in the file | Not applicable |
| 12e | Analytical methods | Performance measures and plots, model comparison | `src/antenatal/evaluation/metrics.py`; `bootstrap.py`; Figures 6 to 11 | Reported |
| 12f | Analytical methods | Model updating | No recalibration applied (proposal Section 3.3.3) | Not applicable |
| 12g | Analytical methods | How predictions were calculated for evaluation | `src/antenatal/artefact/artefact.py`; `evaluation/holdout.py` | Reported |
| 13 | Class imbalance | Imbalance methods and recalibration | None used; `src/antenatal/models/factory.py` docstring | Reported |
| 14 | Fairness | Approaches to model fairness | `outputs/tables/subgroups.csv` (age and parity) | Partly: only age and parity are available |
| 15 | Model output | Output type and any thresholds | Probability with confidence interval and rank; no classification (R11) | Reported |
| 16 | Training versus evaluation | Differences between development and evaluation data | Same source and rules; random grouped split (`partitions/`) | Reported |
| 17 | Ethical approval | Ethics committee and consent | `docs/ethics_note.md` | Partly: the dataset release states no approval or consent; placeholder kept |
| 18a | Funding | Funding source and role | `docs/Technical-Report.md` | Pending |
| 18b | Conflicts of interest | Declarations | `docs/Technical-Report.md` | Pending |
| 18c | Protocol | Where the protocol can be accessed | The proposal, frozen before analysis | Pending: state its location |
| 18d | Registration | Registration information | Not registered | Pending: state in the report |
| 18e | Data sharing | Availability of data | `data/README.md` (CC BY 4.0, Zenodo DOI) | Reported |
| 18f | Code sharing | Availability of analytical code | This repository | Reported |
| 19 | Patient and public involvement | Involvement or none | None | Pending: state in the report |
| 20a | Participants | Flow, with and without the outcome | `outputs/tables/cohort_flow.csv`; Figure 1 | Reported |
| 20b | Participants | Characteristics, events, missing data | Figures 2 to 4; `outputs/tables/missingness.csv` | Reported |
| 20c | Participants | Evaluation versus development distributions | Single held out evaluation | Pending: Stage 4 |
| 21 | Model development | Participants and events in each analysis | Every table carries `n` and `events`; every figure title states both | Reported |
| 22 | Model specification | Full model to allow new predictions | `webapp/model/` artefact, `model_params.json`, `version.json` | Reported |
| 23a | Model performance | Estimates with intervals, including subgroups | `outputs/tables/model_performance.csv`; `subgroups.csv` | Reported |
| 23b | Model performance | Heterogeneity across clusters | No cluster identifier | Not applicable |
| 24 | Model updating | Results of updating | No updating | Not applicable |
| 25 | Interpretation | Overall interpretation including fairness | `notebooks/02_model_notebook.ipynb`; `docs/Technical-Report.md` section 5 | Reported |
| 26 | Limitations | Limitations and their effects | `notebooks/02_model_notebook.ipynb` section 12; proposal Section 3.8 | Reported |
| 27a | Usability | Handling poor or unavailable inputs | Entry rules in `webapp/app/services/validation.py`; imputation inside the artefact | Reported |
| 27b | Usability | User interaction and expertise required | Prototype is synthetic only and not for use (proposal Section 3.4.2) | Reported |
| 27c | Usability | Next steps for research | `docs/Technical-Report.md` | Pending |

Reference: Collins, G. S., Moons, K. G. M., Dhiman, P., et al. (2024). TRIPOD+AI
statement: updated guidance for reporting clinical prediction models that use
regression or machine learning methods. BMJ, 385, e078378.
https://doi.org/10.1136/bmj-2023-078378
