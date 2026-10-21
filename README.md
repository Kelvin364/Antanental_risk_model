# Antenatal caseload prediction

### Incremental predictive value of two antenatal visits for recorded low birth weight

[![CI](https://github.com/Kelvin364/Antanental_risk_model/actions/workflows/ci.yml/badge.svg)](https://github.com/Kelvin364/Antanental_risk_model/actions/workflows/ci.yml)
[![Licence: MIT](https://img.shields.io/badge/licence-MIT-blue.svg)](LICENSE)

Kelvin Rwihimba, BSc Software Engineering, African Leadership University. Supervisor: Emmanuel Adjei.

> **Research code. The prototype accepts synthetic cases only. It is not a medical device and must not be used for any real pregnancy.**

## Overview

When a pregnancy is seen for the second time, at or before 28 weeks, does information from the first antenatal visit help predict a recorded birth weight below 2.5 kg beyond what the second visit already shows? This repository answers that question on the publicly released Maternal Health Risks Stratification dataset from Tanzania (Mwifunyi et al., 2025; 8,817 records; CC BY 4.0), following the frozen plan in the project proposal.

It contains four things that fit together:

1. **The `antenatal` package** (`src/antenatal`). It loads the file after checking its SHA 256, derives the cohort exactly as Table 3.5 of the proposal states, seals a held out partition before any modelling step, runs repeated nested grouped cross validation on development records only, and writes every table and figure.
2. **Two notebooks** (`notebooks/`) that explain the audit and the results in plain English. They compute nothing of their own; they read the package outputs.
3. **A frozen model artefact** (`webapp/model/`): L2 logistic regression on set C, fitted once on the 3,126 development records, saved with a checksum and a version record. A set B artefact sits beside it and is not served.
4. **A prototype interface** (`webapp/`): a FastAPI service and a single page that score synthetic cases with that artefact and show a rank, a probability and its confidence interval, never a clinical risk category.

## Results

Every number below is generated from `outputs/tables/results_summary.csv` by `python -m antenatal update-readme`. None is typed by hand. Intervals are 95 percent group bootstrap intervals on development out of fold predictions.

<!-- results:start -->
| Result | Value (95 percent interval) |
| --- | --- |
| Analysis cohort | 3,908 pregnancies, 206 events |
| Development partition | 3,126 pregnancies, 165 events |
| Primary: first visit added (C over B), PR AUC, logistic | -0.0040 (-0.0130 to +0.0025) |
| Primary: first visit added (C over B), PR AUC, trees | -0.0066 (-0.0173 to +0.0024) |
| Secondary: second visit added (B over A), ROC AUC, logistic | +0.0205 (-0.0066 to +0.0476) |
| Secondary: second visit added (B over A), ROC AUC, trees | +0.0345 (+0.0070 to +0.0627) |
| Smallest detectable C over B, PR AUC, logistic | 0.0110 |
| C minus B with all training data (learning curve) | -0.0041 |
| C over B under pooled multiple imputation | -0.0055 (-0.0151 to +0.0008) |
| Share of events in the top 10 percent of the ranking | 21.8 percent (15.9 to 27.9) |
| Calibration slope, logistic, set C | 0.98 (0.63 to 1.37) |
<!-- results:end -->

In plain words: adding the first visit to the second did not improve prediction by any amount this design could detect, and the learning curve gives no sign that more data of this kind would change that. The held out partition has not been opened yet (see the feature status table).

## Feature status

| Feature | Status | Evidence |
| --- | --- | --- |
| Data loader with checksum verification | Completed | [`data/loader.py`](src/antenatal/data/loader.py), [`tests/unit/test_data_and_audit.py`](tests/unit/test_data_and_audit.py) |
| Data quality audit (Table 3.3) | Completed | [`audit/quality.py`](src/antenatal/audit/quality.py), [`01_data_audit.ipynb`](notebooks/01_data_audit.ipynb) |
| Cohort derivation reproducing Table 3.5 with a per record exclusion reason (R1) | Completed | [`cohort_flow.csv`](outputs/tables/cohort_flow.csv), [`cohort_manifest.csv`](outputs/cohort_manifest.csv) |
| Held out partition sealed before any model step (R3) | Completed | [`partitions/`](partitions), [`cohort/partition.py`](src/antenatal/cohort/partition.py) |
| Feature sets A, B and C with the availability screen (R2) | Completed | [`features/sets.py`](src/antenatal/features/sets.py), [`availability_screen.csv`](outputs/tables/availability_screen.csv) |
| Eight model families and the constant prevalence baseline | Completed | [`models/factory.py`](src/antenatal/models/factory.py), [`model_performance.csv`](outputs/tables/model_performance.csv) |
| Repeated nested grouped cross validation and paired group bootstrap | Completed | [`evaluation/nested_cv.py`](src/antenatal/evaluation/nested_cv.py), [`feature_set_comparisons.csv`](outputs/tables/feature_set_comparisons.csv) |
| Calibration, decision curve and detectable difference | Completed | [`calibration_by_set.csv`](outputs/tables/calibration_by_set.csv), [`decision_curve.csv`](outputs/tables/decision_curve.csv), [`detectable_difference.csv`](outputs/tables/detectable_difference.csv) |
| Sensitivity analyses S1 to S6 | Completed | [`sensitivity_analyses.csv`](outputs/tables/sensitivity_analyses.csv) |
| Further analyses: learning curve, ablation, parameterisation, missingness, multiple imputation, subgroups, retrieval | Completed | [`extensions.py`](src/antenatal/extensions.py), [`02_model_notebook.ipynb`](notebooks/02_model_notebook.ipynb) |
| Frozen primary artefact and secondary set B artefact (R12) | Completed | [`webapp/model/version.json`](webapp/model/version.json), [`secondary_set_b/version.json`](webapp/model/secondary_set_b/version.json) |
| Backend API with synthetic flag, range and timing rules (R9, R10, R16) | Completed | [`webapp/app/`](webapp/app), [`tests/integration/test_api.py`](tests/integration/test_api.py) |
| Prototype interface, single page over the API, no risk categories (R11) | Completed | [`webapp/static/index.html`](webapp/static/index.html) |
| Automated tests and continuous integration workflow | Partial: the workflow file is written but has not run on GitHub yet | [`tests/`](tests), [`.github/workflows/ci.yml`](.github/workflows/ci.yml) |
| TRIPOD+AI checklist | Partial: some items pending | [`docs/tripod_ai_checklist.md`](docs/tripod_ai_checklist.md) |
| Single evaluation on the held out partition (Stage 4) | Not implemented: written and tested on synthetic data, not yet run | [`evaluation/holdout.py`](src/antenatal/evaluation/holdout.py) |
| Next.js interface, cross browser tests, accessibility and latency benchmarks (Stage 6) | Not implemented | None yet |
| Docker image | Not implemented: Dockerfile and compose file are written but have never been built or run | [`Dockerfile`](Dockerfile), [`docker-compose.yml`](docker-compose.yml) |
| Technical report, architecture and ethics notes (Stage 7) | Not implemented | None yet |

## Quick start

These three commands install everything and start the prototype at http://127.0.0.1:8000/. They need Python 3.12 on the path as `python3.12`.

```bash
git clone https://github.com/Kelvin364/Antanental_risk_model.git && cd Antanental_risk_model
make install
make serve
```

## Full installation

| Component | Version |
| --- | --- |
| Python | 3.12 (the committed results used 3.12.13) |
| scikit-learn | 1.8.0 |
| pandas | 3.0.2 |
| NumPy | 2.4.4 |
| FastAPI | 0.142.2 |
| uvicorn | 0.46.0 |
| Node.js | not used yet; needed only for the Stage 6 interface |

Every runtime version is pinned in [`requirements.txt`](requirements.txt) and every development tool in [`requirements-dev.txt`](requirements-dev.txt). The artefact is serialised with scikit-learn 1.8.0 and joblib 1.5.3, and other versions may not load it.

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pip install -e .
```

The data file is included under its CC BY 4.0 licence. See [`data/README.md`](data/README.md) for its source and checksum.

## Repository structure

<!-- tree:start -->
```
.
├── .dockerignore
├── .github
│   └── workflows
├── .gitignore
├── Dockerfile
├── LICENSE
├── Makefile
├── README.md
├── data
│   ├── README.md
│   └── maternal_dataset_csv.csv
├── designs
│   └── web
├── docker-compose.yml
├── docs
│   ├── ARCHITECTURE.md
│   ├── deviations.md
│   ├── meeting_evidence.md
│   └── tripod_ai_checklist.md
├── notebooks
│   ├── 01_data_audit.ipynb
│   └── 02_model_notebook.ipynb
├── outputs
│   ├── cohort_manifest.csv
│   ├── figures
│   ├── manifest.json
│   ├── oof_extensions.parquet
│   ├── oof_predictions.parquet
│   └── tables
├── partitions
│   ├── folds.parquet
│   ├── holdout.sha256
│   └── holdout_ids.csv
├── pyproject.toml
├── requirements-dev.txt
├── requirements.txt
├── src
│   └── antenatal
├── tests
│   ├── __init__.py
│   ├── conftest.py
│   ├── integration
│   └── unit
└── webapp
    ├── __init__.py
    ├── app
    ├── data
    ├── model
    └── static
```
<!-- tree:end -->

## How to run

**The analysis.** Each command reads and writes paths relative to the repository root.

```bash
.venv/bin/python -m antenatal derive-cohort      # cohort, per record manifest, flow table
.venv/bin/python -m antenatal seal-partition     # reads the sealed partition; never regenerates it
.venv/bin/python -m antenatal run-analysis       # nested cross validation, tables and figures (about 5 minutes)
.venv/bin/python -m antenatal run-extensions     # further analyses (several minutes)
.venv/bin/python -m antenatal summarise-results  # outputs/tables/results_summary.csv
.venv/bin/python -m antenatal update-readme      # refreshes the results and structure blocks above
```

`python -m antenatal run-all` runs the full sequence, including `freeze-artefact` and `freeze-secondary-artefact`. Refitting the artefacts reproduces the same coefficients and reference probabilities, but the files get new checksums, so the committed artefacts remain the ones of record. The single held out evaluation is never part of `run-all`.

**The notebooks.** `make notebook` executes both notebooks in place. They read the outputs above.

**The application.** `make serve` starts the API and the interface at http://127.0.0.1:8000/, with interactive API documentation at http://127.0.0.1:8000/docs. The server verifies the artefact checksum when it starts and refuses to start if the file has changed.

**The tests.** `make test` runs the unit and integration suites with coverage, and `make lint` runs ruff and black.

**The benchmarks.** No benchmark exists yet. The latency benchmark is part of Stage 6.

## Designs

`designs/web/` holds seven screens from the earlier Figma design. They include sign up and sign in screens and triage wording, both of which are now out of scope, so they do not match the current interface. They are to be regenerated from the real screens in Stage 6.

## Links

| Item | Link |
| --- | --- |
| Demonstration video | To be added |
| Technical report | To be added |

## Limitations

* One public Tanzanian dataset with no facility or geographic identifier, so neither external nor geographic validation is possible.
* The development partition holds 165 events, so only differences of roughly the detectable size shown above could be seen.
* Haemoglobin at visit two is recorded for a minority of pregnancies, so the test of the earlier visit rests mainly on blood pressure, weight, gestational week and pulse.
* The outcome is the birth weight recorded under the care actually given. Nothing here shows that acting on a prediction would change it.
* The held out partition has not yet been evaluated.
* The prototype is a demonstration on synthetic cases. It has not been validated for any pregnancy.

## Licence

The code is released under the MIT licence (see [`LICENSE`](LICENSE)). The data file is by Mwifunyi et al. (2025), released under CC BY 4.0, https://doi.org/10.5281/zenodo.15309733.
