# Video script

A timed outline for a walkthrough of 10 minutes, inside the 8 to 12 minute limit. Each part shows the exact command, address or file. Read every result from the screen or the named file while recording; this outline types no results.

**To confirm before recording.** The assignment brief's Section 2 headings A to E are not stored in this repository. The five parts below follow the five numbered sections of `docs/Technical-Report.md`, which are written to that brief. Replace each "Brief heading" line with the brief's own wording, and move material between parts if the brief orders them differently.

## Before recording

Run these once so nothing waits on screen:

```
make install
make browsers
python -m antenatal derive-cohort
make frontend
python -m webapp.app.admin create-admin admin   # note the printed password; change it at first sign in
make serve            # leave running in a second terminal
```

Open in the browser: http://127.0.0.1:8000/ (or the live site https://antenatal-caseload.fly.dev/) and http://127.0.0.1:8000/docs. Open in the editor: `README.md`, `docs/Technical-Report.pdf`, `docs/holdout_results.md`, `docs/research_results.md`. Use only synthetic cases on camera, and never show a password.

## Timed outline

| Time | Part | Brief heading |
| --- | --- | --- |
| 0:00 to 0:45 | Opening | None |
| 0:45 to 2:30 | A | To confirm: scope alignment |
| 2:30 to 5:30 | B | To confirm: technical functionality and algorithms |
| 5:30 to 7:15 | C | To confirm: testing approaches and results |
| 7:15 to 8:30 | D | To confirm: code quality practices |
| 8:30 to 9:45 | E | To confirm: results and limitations |
| 9:45 to 10:00 | Close | None |

### Opening (0:00 to 0:45)

State the question: does adding two antenatal visits to registration data improve the ranking of pregnancies by recorded low birth weight in one Tanzanian dataset. State that the prototype orders a caseload and does not decide care, and that only synthetic cases are entered.

Show: the top of `README.md`.

### Part A, scope alignment (0:45 to 2:30)

Show the scope table in section 1 of `docs/Technical-Report.pdf` and the feature table in `README.md`. Name what is completed, what is partial and what is not built, reading the status column.

Show `docs/deviations.md` and name two deviations from the proposal and the reason given for each.

### Part B, technical functionality and algorithms (2:30 to 5:30)

Run in a terminal:

```
python -m antenatal derive-cohort
```

Point at the eight flow counts as they print, then open `outputs/figures/fig01_cohort_flow.png`.

Explain the sealed partition: open `src/antenatal/evaluation/holdout.py` and show that `evaluate_once` needs `confirm_supervisor_reviewed=True`, and that every model fit carries a `TrainingGuard`. Run `cat partitions/holdout_access.log` to show the partition was opened once, evaluated once, and a second attempt refused. Run `python -m antenatal audit-holdout` and read the eleven checks.

Explain feature sets A, B and C and the repeated nested grouped cross validation, using `outputs/figures/fig06_model_families.png` and `outputs/figures/fig07_feature_set_differences.png`.

Sign in, then walk the five screens at http://127.0.0.1:8000/: register, visit one, visit two, assessment, caseload. On the assessment screen read the rank position, the probability, its interval, the label "Likely" or "Not likely low birth weight" with how often it is right, and the limitation line. Show that the caseload refuses access after signing out. Then open http://127.0.0.1:8000/docs and run `POST /api/predict` once.

Show `configs/experiment_plan.yaml` and `outputs/tables/selection_v2.json`: the Stage 2 experiments were written down before they ran, and none passed the rule, so artefact 1.0.0 stays.

### Part C, testing approaches and results (5:30 to 7:15)

Run:

```
.venv/bin/python -m pytest tests/unit tests/integration -q -o addopts="" --cov=src --cov=webapp/app
```

While it runs, open `docs/evidence/input_tests.md` (12 entered inputs) and `docs/evidence/compatibility.md` with one screenshot from `docs/evidence/compatibility/`. Open `docs/evidence/performance.md` and read the p50, p95, memory and start up rows. When the test run ends, read the summary line and the coverage total.

### Part D, code quality practices (7:15 to 8:30)

Run:

```
make lint
```

Show `src/antenatal/config.py` (`StudySpec`, one place for every constant), `src/antenatal/features/` (one class per feature set) and `.github/workflows/ci.yml`, including the `security` job. Show `git log --oneline | head -15` and point out that each message cites a proposal section, requirement or supervisor comment.

### Part E, results and limitations (8:30 to 9:45)

Open `notebooks/03_statistical_analysis.ipynb` or `docs/research_results.md` and read the answer to each of the four research questions. Show `outputs/figures/fig08_calibration.png` and `outputs/figures/fig10_detectable_difference.png`.

Open `docs/holdout_results.md`: section 1 shows why the model never learned from the held out records; then read the held out table beside the development values. Read the limitations from section 5 of `docs/Technical-Report.pdf`: one dataset with weak predictors, a small held out partition whose ROC AUC interval includes random ranking, a recorded outcome, and the need for a larger independent cohort.

### Close (9:45 to 10:00)

Show the "Submission" section of `README.md` with the report link and the repository link.
