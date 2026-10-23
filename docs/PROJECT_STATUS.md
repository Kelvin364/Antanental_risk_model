# Project status

Status on 2026-10-23, at commit `bbededf` on `main`. This page gives an overview of where the project stands, whether the model behaves as it should, and what a live deployment would need. Every number comes from a file in `outputs/` or `docs/evidence/`, and the source is named beside it.

## In short

* The research analysis, the prediction service and the five screen interface are finished and tested.
* The model behaves as designed. It gives the same answer every time for the same input, matches the research pipeline exactly, refuses invalid input with clear messages, and refuses to start if its file has been altered or was saved under a different library version.
* The model is weak, and that matches the study's finding. Visit one measurements add nothing measurable on top of visit two. The model ranks pregnancies better than chance, but only modestly.
* The held out partition has not been opened. Until it is, every performance figure is an estimate from cross validation on development records.
* The application is not deployed on the internet. This is deliberate: requirement R14 says no record leaves the local environment. A live deployment needs the supervisor's decision first, then the work listed under "What a live deployment needs".

## Where the project stands

| Part | State | Evidence |
| --- | --- | --- |
| Cohort derivation | Done. 8,817 records in the file, 3,908 in the analysis cohort with 206 low birth weight events | `outputs/tables/cohort_flow.csv` |
| Development and held out split | Done and sealed. 3,126 development records with 165 events | `outputs/tables/results_summary.csv`, `partitions/` |
| Model comparison, eight families plus a prevalence baseline | Done | `outputs/tables/model_performance.csv` |
| Calibration, decision curve, sensitivity and subgroup analyses | Done | `outputs/tables/` |
| Frozen model file (logistic regression, feature set C, 25 features) | Done, checksum recorded | `webapp/model/version.json`, `webapp/model/lbw_model.sha256` |
| FastAPI service with nine endpoints | Done | `webapp/app/` |
| Next.js interface, five screens | Done, served by FastAPI from `frontend/out` | `frontend/` |
| Container image | Done. Builds, starts healthy and keeps cases across restarts | `Dockerfile`, `docker-compose.yml` |
| Automated tests | 235 tests, 0 failures, 0 skipped, 97.6 percent line coverage | `docs/evidence/test_summary.json` |
| Browser compatibility | Chromium, Firefox and WebKit at desktop and phone sizes, no failures | `docs/evidence/compatibility.md` |
| Accessibility (automated audit) | Every screen scores 100 at both sizes | `docs/evidence/accessibility.md` |
| Performance on one laptop | Start up 2.11 seconds, peak memory 267.7 MB, single request p50 11.9 ms and p95 24.1 ms | `docs/evidence/performance.md` |
| Technical report | Five pages, built to PDF | `docs/Technical-Report.pdf` |
| Single evaluation on the held out partition (Stage 4) | Not run. Code written and tested on synthetic data; waits for the supervisor | `src/antenatal/evaluation/holdout.py` |
| Author statements (abstract, funding, conflicts, protocol, registration, public involvement, next steps) | Not written. Prompts are in place | `docs/tripod_ai_pending.md` |
| Data producers' ethics statement | Placeholder. The dataset release contains none | `docs/ethics_note.md` |
| Demonstration video | Not recorded. Outline ready | `docs/VIDEO_SCRIPT.md` |
| Manual screen reader and keyboard check | Not done. The automated audit cannot show this | `docs/evidence/accessibility.md` |
| Editing a registration after saving | Not supported. There is no update endpoint for a case | `webapp/app/api/` |

## Is the model behaving and responding as it should?

Yes, in every way that can be tested without the held out records. "Behaving" covers two different questions, so each is answered separately.

### 1. Does the software do exactly what it was built to do?

Yes. These checks were run again on 2026-10-23.

| Check | Result |
| --- | --- |
| The checksums of the dataset, the held out ids, the folds and the model file match their recorded values | Match (`src/antenatal/config.py`, `partitions/holdout.sha256`, `outputs/manifest.json`, `webapp/model/lbw_model.sha256`) |
| The held out partition has never been opened | `partitions/holdout_access.log` does not exist |
| Refitting on development records gives the committed model's coefficients, intercept, feature names and reference probabilities to within 1e-9 | Pass (`tests/integration/test_artefact_reproducibility.py`) |
| The API, the service layer and the research pipeline give the same probability to within 1e-9 | Pass (`tests/integration/test_api.py::test_api_equals_service_equals_package_pipeline`) |
| No held out record appears in any out of fold prediction | Pass (`tests/unit/test_artefact_and_outputs.py`) |
| The service refuses to load the model under a different scikit-learn release | Pass (`test_other_scikit_learn_release_is_refused`) |
| Twelve live inputs through the running API: typical cases, boundaries, out of range values, wrong visit order, missing values | 12 of 12 behaved as expected (`docs/evidence/input_tests.md`) |
| The same input sent twice | Same probability both times |

When single inputs were changed one at a time from a typical case, the predicted probability moved in the directions the literature on low birth weight would lead you to expect. It went up with lower weight at visit two, shorter height, higher blood pressure, younger age and a first pregnancy, and down with the opposite changes. No input produced an implausible jump.

### 2. Does the model predict well?

Only modestly. This is the study's honest result, not a fault in the software. All figures are cross validated on the 3,126 development records, with 95 percent group bootstrap intervals.

| Measure | Value | Source |
| --- | --- | --- |
| ROC AUC, logistic regression, set C (the deployed model). 0.5 is chance, 1.0 is perfect | 0.628 (0.584 to 0.675) | `outputs/tables/model_performance.csv` |
| PR AUC, same model. The prevalence baseline scores 0.054 | 0.089 (0.070 to 0.118) | `outputs/tables/model_performance.csv` |
| Calibration slope, same model. 1.0 means predicted probabilities are neither too spread nor too squeezed | 0.98 (0.63 to 1.37) | `outputs/tables/calibration_by_set.csv` |
| Share of all events found in the top 10 percent of the ranking | 21.8 percent (15.9 to 27.9) | `outputs/tables/retrieval_at_budget.csv` |
| Change in PR AUC from adding visit one (C over B), logistic | -0.0040 (-0.0130 to +0.0025) | `outputs/tables/results_summary.csv` |
| Change in ROC AUC from adding visit two (B over A), gradient boosting | +0.0345 (+0.0070 to +0.0627) | `outputs/tables/results_summary.csv` |

What this means in plain terms:

* The model orders pregnancies better than chance. The top tenth of its ranking holds about twice the share of events that a random tenth would.
* Its probabilities are well calibrated on average. They are also all small, because only about 5 percent of pregnancies in the data had a low birth weight (prevalence 0.0528, `webapp/model/version.json`).
* Adding visit one does not improve it. This is the primary research question, and the answer is no measurable gain.
* The figures could be lower on unseen records. Only the Stage 4 held out evaluation will show that.

The interface shows a rank position and a probability with its interval, and deliberately no category. That is the right way to present a model this weak.

## What a live deployment needs

### Decisions to make first

1. **The supervisor's decision on R14.** R14 says no entered record may leave the local environment. A hosted site sends every value a user types to a remote server. The deviation log (`docs/deviations.md`, row "Cloud hosting") records this and waits for that decision.
2. **Stage 4 before any public claim.** Run the single held out evaluation, then publish its result next to the cross validated figures. A public demonstration should not show performance figures that have never been checked on unseen records.
3. **A clear purpose statement.** The site must say it is a research demonstration for synthetic cases only, not a medical device and not for care decisions. The synthetic banner and the limitation line already appear on every screen; a short "about" page would complete this.

### Already in place

* A container image that builds the interface and serves it with the API from one process on port 8000, runs as a non root user, and has a health check (`Dockerfile`).
* A named volume that keeps the SQLite database across restarts (`docker-compose.yml`).
* A `/health` endpoint that reports the model version and checksums, for uptime monitoring.
* A start up refusal if the model file is altered or the library version differs, so a broken deployment fails loudly instead of answering wrongly.
* No secrets, keys or accounts to manage.
* Continuous integration that lints, tests, type checks and builds the interface on every push.

### Work still needed

| Need | Why | Suggested approach |
| --- | --- | --- |
| A host | Somewhere to run the container | A small container service such as Render, Fly.io, Railway, Google Cloud Run or a single virtual machine. The image needs about 300 MB of memory (`docs/evidence/performance.md`) |
| HTTPS and a domain | Browsers and users expect an encrypted connection | Most container hosts provide this. On a virtual machine, put Caddy or nginx in front of port 8000 |
| Protection against misuse | There are no accounts by design, so anyone with the link can create cases | Rate limit by IP address at the proxy or with a FastAPI middleware, cap request size, and add a privacy notice telling people not to enter real data |
| A rule for clearing old cases | Synthetic cases pile up without limit, and anyone can see the caseload | A scheduled job that deletes cases older than, for example, seven days, or a reset on each deploy. There is no delete endpoint yet |
| Persistent storage, or deliberately none | Some hosts erase local files on restart | Mount a volume at `/app/state`, or accept that the demonstration database resets |
| More than one worker, if many people will use it at once | One worker answers requests one after another; 50 at once gave a p95 of 1,056.7 ms | Start uvicorn with `--workers 2` or more, or let the host run several copies. SQLite suits light use; for real concurrency, set `ANTENATAL_DATABASE_URL` to a PostgreSQL database |
| Logs and monitoring | To notice when the site is down or failing | Point the host's uptime check at `/health` and keep the uvicorn access logs |
| Deployment from CI | So that every release is the tested commit | Add a job that builds the image, pushes it to a registry and deploys after the existing checks pass |
| Pinned library versions in the image | The model loads only under the scikit-learn release it was saved with | Already pinned in `requirements.txt`; keep that pin when updating dependencies |

### Smallest route to a working public demonstration

Once the supervisor agrees:

1. Run Stage 4 and add the held out result to the report and README.
2. Deploy the existing image to a container host with HTTPS, a volume at `/app/state` and its uptime check on `/health`.
3. Add rate limiting and a scheduled cleanup of old synthetic cases.
4. Add an "about" page stating the purpose and the limits.
5. Run `scripts/input_variation.py --base-url <public address>` against the live site and record the result.

## How to run it locally today

```
make serve         # API and the built interface on http://127.0.0.1:8000
```

or, while editing the interface, in two terminals:

```
make serve         # API on port 8000
make frontend-dev  # interface with live reload on http://127.0.0.1:3000
```

The interface on port 3000 needs the API on port 8000. Without it nothing can be saved, so the Visit one and Visit two steps stay locked.
