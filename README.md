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
4. **A prototype interface** (`webapp/`, `frontend/`): a FastAPI service and a Next.js interface that score synthetic cases with that artefact and show a rank, a probability and its confidence interval, never a clinical risk category.

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
| Research data model in SQLite: pregnancy records, visit measurements, model configurations, evaluation results (Section 3.4.4) | Completed | [`storage.py`](src/antenatal/storage.py), `python -m antenatal load-db`, [`tests/unit/test_storage.py`](tests/unit/test_storage.py) |
| Backend API with synthetic flag, range and timing rules (R9, R10, R16) | Completed | [`webapp/app/`](webapp/app), [`tests/integration/test_api.py`](tests/integration/test_api.py) |
| Prototype interface over the API, five screens, no risk categories (R11) | Completed: Next.js in `frontend/` | [`frontend/src/`](frontend/src) |
| Automated tests and continuous integration workflow | Partial: the workflow file is written but has not run on GitHub yet | [`tests/`](tests), [`.github/workflows/ci.yml`](.github/workflows/ci.yml) |
| TRIPOD+AI checklist | Partial: some items pending | [`docs/tripod_ai_checklist.md`](docs/tripod_ai_checklist.md) |
| Single evaluation on the held out partition (Stage 4) | Not implemented: written and tested on synthetic data, not yet run | [`evaluation/holdout.py`](src/antenatal/evaluation/holdout.py) |
| API performance: start up, latency and memory on one machine | Completed | [`scripts/benchmark_api.py`](scripts/benchmark_api.py), [`docs/evidence/performance.md`](docs/evidence/performance.md) |
| Compatibility of the current interface: five screen flow in Chromium, Firefox and WebKit at 1366 by 768 and 390 by 844 | Completed | [`tests/e2e/`](tests/e2e), [`docs/evidence/compatibility.md`](docs/evidence/compatibility.md) |
| Design images drawn from the running interface, five screens, no sign in screens | Completed | [`scripts/render_designs.py`](scripts/render_designs.py), [`designs/README.md`](designs/README.md) |
| Next.js interface (Stage 6): App Router, TypeScript, Tailwind, typed client generated from the OpenAPI schema, static export served by FastAPI | Completed | [`frontend/`](frontend), [`scripts/export_openapi.py`](scripts/export_openapi.py), [`tests/e2e/`](tests/e2e) |
| Accessibility of the five screens: Lighthouse accessibility scores at phone and desktop sizes | Completed | [`scripts/accessibility_audit.py`](scripts/accessibility_audit.py), [`docs/evidence/accessibility.md`](docs/evidence/accessibility.md) |
| Docker image: interface built in a Node stage, API and interface served by one container, cases kept on a named volume | Completed: built and run with `docker compose up --build`, health check passing | [`Dockerfile`](Dockerfile), [`docker-compose.yml`](docker-compose.yml) |
| Technical report, Markdown and a PDF of at most five pages | Completed | [`docs/Technical-Report.md`](docs/Technical-Report.md), [`docs/Technical-Report.pdf`](docs/Technical-Report.pdf), [`scripts/build_report_pdf.py`](scripts/build_report_pdf.py) |
| Submission bundle and video outline | Completed as scripts; the video is not recorded yet | [`scripts/package_attempt2.py`](scripts/package_attempt2.py), [`docs/VIDEO_SCRIPT.md`](docs/VIDEO_SCRIPT.md) |
| Architecture, ethics note, changelog and deviation log | Completed; the ethics note holds a placeholder because the dataset release has no ethics statement | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`docs/ethics_note.md`](docs/ethics_note.md), [`CHANGELOG.md`](CHANGELOG.md), [`docs/deviations.md`](docs/deviations.md) |
| Input variation evidence | Completed | [`docs/evidence/input_tests.md`](docs/evidence/input_tests.md) |

## Quick start

These commands install everything, build the interface and start the prototype at http://127.0.0.1:8000/. They need Python 3.12 on the path as `python3.12` and Node.js 20.9 or newer.

```bash
git clone https://github.com/Kelvin364/Antanental_risk_model.git && cd Antanental_risk_model
make install
make frontend
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
| Node.js | 20.9 or newer, to build the interface (Next.js 16.4.2) |

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
├── CHANGELOG.md
├── Dockerfile
├── LICENSE
├── Makefile
├── README.md
├── configs
│   └── experiment_plan.yaml
├── data
│   ├── README.md
│   └── maternal_dataset_csv.csv
├── designs
│   ├── README.md
│   └── web
├── docker-compose.yml
├── docs
│   ├── ARCHITECTURE.md
│   ├── Technical-Report.md
│   ├── Technical-Report.pdf
│   ├── VIDEO_SCRIPT.md
│   ├── decisions_log.md
│   ├── deviations.md
│   ├── ethics_note.md
│   ├── evidence
│   ├── tripod_ai_checklist.md
│   └── tripod_ai_pending.md
├── frontend
│   ├── next-env.d.ts
│   ├── next.config.ts
│   ├── openapi.json
│   ├── package-lock.json
│   ├── package.json
│   ├── postcss.config.mjs
│   ├── src
│   └── tsconfig.json
├── notebooks
│   ├── 01_data_audit.ipynb
│   └── 02_model_notebook.ipynb
├── outputs
│   ├── cohort_manifest.csv
│   ├── figures
│   ├── learning_curve_predictions.parquet
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
├── scripts
│   ├── accessibility_audit.py
│   ├── benchmark_api.py
│   ├── build_report_pdf.py
│   ├── export_openapi.py
│   ├── input_variation.py
│   ├── package_attempt2.py
│   ├── record_test_results.py
│   └── render_designs.py
├── src
│   └── antenatal
├── tests
│   ├── __init__.py
│   ├── conftest.py
│   ├── e2e
│   ├── integration
│   └── unit
└── webapp
    ├── __init__.py
    ├── app
    ├── data
    └── model
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

**The application.** `make frontend` builds the Next.js interface into `frontend/out`, and `make serve` starts the API and serves that interface at http://127.0.0.1:8000/, with interactive API documentation at http://127.0.0.1:8000/docs. Without a build, `make serve` runs the API only. While changing the interface, `make frontend-dev` serves it with hot reloading at http://127.0.0.1:3000/ and forwards API calls to `make serve`. After a change to an API request or response, `make api-types` regenerates `frontend/openapi.json` and the typed client; continuous integration fails if either is stale. The server verifies the artefact checksum when it starts and refuses to start if the file has changed.

**The tests.** `make test` runs the unit, integration and browser suites with coverage, and `make lint` runs ruff and black. The browser tests need `make browsers` once, which downloads Chromium, Firefox and WebKit for Playwright; without them those tests are skipped. `make e2e` runs only the browser tests and rewrites `docs/evidence/compatibility.md`.

**The benchmarks.** `make benchmark` starts its own server, sends 500 sequential and 50 concurrent predictions and writes `docs/evidence/performance.md`. `make accessibility` starts its own server, records one synthetic case and runs the Lighthouse accessibility audit on each screen at phone and desktop sizes, writing `docs/evidence/accessibility.md`; it needs `make frontend` and `make browsers` first, and fetches the pinned Lighthouse through `npx` so it never enters the interface's dependencies.

**The container.** `make docker` (that is, `docker compose up --build`) builds the interface and the API into one image and serves both at http://127.0.0.1:8000/. Cases are kept on the `app-state` volume; `docker compose down -v` removes them. On WSL without systemd, start the engine first with `sudo dockerd &`, or enable systemd by putting `systemd=true` under `[boot]` in `/etc/wsl.conf`.

## Designs

`designs/web/` holds five screenshots of the running interface, one per screen, drawn by `scripts/render_designs.py` from a synthetic case. The earlier Figma screens with sign up, sign in and triage wording were removed. [`designs/README.md`](designs/README.md) lists the files.

## Submission

| Item | Link |
| --- | --- |
| Demonstration video | To be added after recording; outline in [`docs/VIDEO_SCRIPT.md`](docs/VIDEO_SCRIPT.md) |
| Technical report | [`docs/Technical-Report.pdf`](docs/Technical-Report.pdf), built from [`docs/Technical-Report.md`](docs/Technical-Report.md) by `make report-pdf`; final submitted link to be added |
| Submission bundle | `.venv/bin/python scripts/package_attempt2.py VIDEO` writes `dist/attempt2.zip` |

## Limitations

* One public Tanzanian dataset with no facility or geographic identifier, so neither external nor geographic validation is possible.
* The development partition holds 165 events, so only differences of roughly the detectable size shown above could be seen.
* Haemoglobin at visit two is recorded for a minority of pregnancies, so the test of the earlier visit rests mainly on blood pressure, weight, gestational week and pulse.
* The outcome is the birth weight recorded under the care actually given. Nothing here shows that acting on a prediction would change it.
* The held out partition has not yet been evaluated.
* The prototype is a demonstration on synthetic cases. It has not been validated for any pregnancy.

## Licence

The code is released under the MIT licence (see [`LICENSE`](LICENSE)). The data file is by Mwifunyi et al. (2025), released under CC BY 4.0, https://doi.org/10.5281/zenodo.15309733.
