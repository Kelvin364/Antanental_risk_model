# Changelog

All notable changes to this project. Dates are in UTC.

## Unreleased

### Not yet done

* Stage 4: the single evaluation of the held out partition. The code is written and tested on synthetic data and runs only after the supervisor has reviewed the analysis plan.
* Stage 6: the Next.js interface, cross browser tests, accessibility scores, latency benchmark and regenerated design screens.
* The container image: the Dockerfile and compose file have never been built or run.

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
