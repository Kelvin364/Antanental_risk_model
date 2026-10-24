# Changelog

All notable changes to this project. Dates are in UTC.

## Unreleased

### Added

* The single held out evaluation, run once on 24 October 2026 after the supervisor's approval, and `python -m antenatal holdout-report`, which writes `docs/holdout_results.md`: the proof that the model never learned from the held out records (git timeline, the integrity audit before and after, the training guard, the exact rebuild from development records, the one logged read) and every held out result beside its development value. The audits and the run output are kept in `docs/evidence/holdout_run/`.
* `docs/ethics_and_ai.md` replaces `docs/ethics_note.md` and `docs/tripod_ai_pending.md`: one document for the ethical basis of the data, the safeguards built into the model and the application, and the statements only the author writes, each marked AUTHOR TO WRITE.
* The research results now answer the four research questions quoted from the proposal: question 2 adds the comparison with the prevalence only model and the calibration of set C against set B, and question 4 gathers the sensitivity analyses on missing measurements and questionable outcome records.
* The held out evaluation also writes `holdout_net_benefit.csv`, the net benefit of each locked model at every prespecified threshold, with intervals.
* Stage 3 of guideline version 2: `python -m antenatal research-results` answers research questions 1 to 4 from the saved out of fold predictions without fitting any model, and writes `outputs/research/results_table.csv`, a figure and `docs/research_results.md`; `notebooks/03_statistical_analysis.ipynb` reads them, checks record alignment before each paired test and recomputes DeLong's test as descriptive; the notebook is executed by the tests.
* The single held out evaluation is prepared but not run: `docs/holdout_protocol.md` fixes the locked candidate, the comparisons and what cannot change afterwards; a frozen set A comparator in `webapp/model/comparator_set_a/` (`python -m antenatal freeze-comparator-artefact`); `HoldoutEvaluator.evaluate_once` now evaluates the candidate and both comparators together and writes `holdout_result.csv`, `holdout_comparisons.csv` and `holdout_classification.csv`; `scripts/run_holdout.py` runs it only on the exact approval sentence.
* The Next.js interface in `frontend/` (App Router, TypeScript, Tailwind): the five screens as separate routes over the existing API, a typed client generated from the API's OpenAPI schema, validation messages taken from the API only, and a footer reporting the artefact version from `/health`. FastAPI serves its static export.
* `scripts/export_openapi.py`, with a `--check` mode in continuous integration, and an interface build job.
* The cross browser tests and the design screens were rerun against the new interface.
* `scripts/accessibility_audit.py` and `docs/evidence/accessibility.md`: Lighthouse accessibility scores for the five screens at phone and desktop sizes.
* `make benchmark`, `make accessibility` and `make docker`. The container image was built and run for the first time; its health check passes and cases persist across a restart.
* A label on every assessment, "Likely" or "Not likely low birth weight", at a threshold fixed from out of fold predictions by `python -m antenatal freeze-classification` (decision D6). The assessment shows the threshold's sensitivity, specificity and predictive values with intervals and whether the case's interval crosses the threshold; the caseload shows each label. The threshold is saved with the artefact's checksum and the server refuses one fixed for another artefact.

* Sign in with administrator and researcher roles (decision D1): scrypt password hashes, server side sessions in HttpOnly SameSite cookies, a CSRF token on every change, lockout after five failures, a per address sign in limit, an audit trail without clinical values, and researchers limited to their own cases. Sign in, account, administration and about pages; the first administrator comes from `python -m webapp.app.admin create-admin`.
* `TrainingGuard`, required by every model fit, and `make audit` with ten recorded checks that the held out records never reached training (decision D7).
* Stage 2 of guideline version 2: `python -m antenatal run-experiments-v2` runs the 28 prespecified experiments and writes `experiments_v2.csv`, `candidates_v2.csv`, `operating_points_v2.csv`, `net_benefit_v2.csv`, `missing_data_v2.csv`, `coefficients_v2.csv`, `permutation_importance_v2.csv` and `selection_v2.json`. No candidate passed the selection rule; artefact 1.0.0 stays.
* The online system at https://antenatal-caseload.fly.dev/; Fly.io deployment files, `scripts/smoke_test.py`, `docs/OPERATIONS.md`, `make deploy`, `make backup-online` and an optional CI deploy job.

### Changed

* Security headers, including a content security policy, a 64 KB request cap, and a container start script that hands the state volume to the app user.
* The latency benchmark was rerun against the current server and now names the CPU on Linux.
* The step navigation wraps at phone width instead of scrolling sideways and hiding the current step.
* The limitation line reads "Not a diagnosis and not a recommendation for care"; every figure footer was redrawn.

### Removed

* The plain HTML page in `webapp/static/`; the Next.js interface is the only interface.
* The `meeting-evidence` command and its generator. The supervisor meeting notes and the project status page are kept outside the repository.

### Fixed

* Loading the artefact under a scikit-learn release other than the one that saved it now stops the server at start up instead of failing at the first prediction.

### Not yet done

* Stage 4: the single evaluation of the held out partition. The code is written and tested on synthetic data and runs only after the supervisor has reviewed the analysis plan.

## 1.0.0 (2026-10-21)

### Added

* The `antenatal` package: frozen `StudySpec`, checksum verified loader, pure value parsers, the data quality audit, and `CohortBuilder` reproducing Table 3.5 with an exclusion reason per record.
* The held out partition, sealed to file with a checksum before any model step, and a gate that logs every access and refuses without supervisor confirmation.
* Feature sets A, B and C with an outcome blind availability screen refitted per training fold.
* Eight model families and the constant prevalence baseline; repeated nested grouped cross validation; metric strategies; the paired group bootstrap; the detectable difference.
* Sensitivity analyses S1 to S6 and a uniform imputation sensitivity row for the tree model.
* Further analyses: learning curve, per measurement ablation, parameterisation comparison, informative missingness, multiple imputation, subgroups, retrieval within ranking budgets and calibration by set.
* The primary artefact (L2 logistic regression on set C) and a secondary set B artefact that is not served.
* A FastAPI backend with routers, services, schemas and a SQLite store; the synthetic flag, range and timing rules with specific messages; checksum verification at start up.
* A single page interface over the API with no clinical risk category.
* Unit, integration and end to end tests; ruff and black; a continuous integration workflow.
* Generated documents: the README results and tree, the technical report, the meeting evidence and the results summary. Also the architecture, ethics and TRIPOD+AI notes, and the input variation evidence.

### Changed

* One cohort rule replaces the two notebooks' different cohort rules.
* The served model is the development fit instead of a refit on every record including the held out partition.
* Set C for the linear model holds visit one values only; change and rate terms are no longer entered beside the values they are computed from.
* The gradient boosted trees handle missing values natively, as Section 3.3.6 states.
* The interface no longer computes probabilities in the browser and no longer shows triage wording.
* Both notebooks are narratives over the package outputs instead of standalone computations.

### Removed

* The old cohort manifesto notebook and its separate outputs, the hard coded output paths, and the embedded model coefficients in the interface.
