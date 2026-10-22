# Deviations from the proposal and the implementation guideline

Every place where the data or an implementation decision departs from the
proposal or the guideline is listed here, with its treatment, so it can be
taken to the supervisor. Each count is produced by code in this repository.

| Item | Proposal or guideline | What the data or the code gives | Treatment |
| --- | --- | --- | --- |
| S1 cohort, visit two by 24 weeks | Table 3.8: 2,444 records, 142 events | 2,449 records, 142 events (`outputs/tables/sensitivity_cohorts.csv`) | Report the computed count; correct Table 3.8 |
| S5 and S6 events | Table 3.8: 178 events, 5.68 percent | Both keep the primary cohort, 3,908 records and 206 events | Correct Table 3.8 |
| S4 size | Table 3.8: 3,135 records, 178 events | S4 is defined on development records only: 2,504 records with 144 events (`outputs/tables/sensitivity_analyses.csv`, columns `n` and `events`). | Report the computed count; correct Table 3.8 to state that S4 uses development records only |
| Pulse range | Not stated in Section 3.3.3 | Needed to clean pulse | Confirmed: 30 to 200 beats per minute, `StudySpec.pulse = Range(30, 200)` in `src/antenatal/config.py`, applied with the other range rules; being added to Section 3.3.3 |
| Missing values in the tree model | Section 3.3.6: native handling | Implemented as stated | Median imputation with indicators kept as the sensitivity row "GBT, uniform imputation" |
| Repository layout | Flatten `antenatal-caseload-prediction/` into the root | The folder was already flat | No change needed |
| Iterative imputer option | Implementation plan: `IterativeImputer(keep_empty_features=True)` for the multiple imputation sensitivity | With that option, scikit-learn 1.8.0 writes into the input array during the initial imputation and fails with "assignment destination is read-only" when cross validation runs in parallel workers, which pass read only arrays | The option was removed. It only matters when a column is entirely missing in a training fold, and no development column is, so the imputed values are unaffected. Recorded in `src/antenatal/models/factory.py` |
| Artefact reproducibility | Guideline: one artefact with a checksum | Refitting with `SOURCE_DATE_EPOCH` set to the recorded time gives the same coefficients and reference probabilities but different bytes, because the artefact class gained a `role` field after the primary artefact was frozen | The committed artefact remains the one of record; the README says so |
| Dataset version | Proposal: version 1 of the released file | The Zenodo record states that a newer version exists | This study uses version 1 only, fixed by its SHA 256 (`docs/ethics_note.md`) |
| Ethics statement of the data producers | Guideline: quote it with page or section | The Zenodo record and its `metadata.pdf` contain no ethics or consent statement, and no data paper is linked | `docs/ethics_note.md` holds a marked placeholder; nothing is paraphrased |
| Cloud hosting | Budget line for cloud hosting of the demonstration | R14 requires that no record leaves the local environment, and a hosted demonstration would send every entered value to a remote server | Not deployed. The demonstration runs locally with `make serve` and the budget line is unused unless the supervisor decides otherwise |
| Interface technology | Table 3.12: React.js | The implementation plan names Next.js, a framework built on React. The current interface is plain HTML and JavaScript in `webapp/static/index.html` over the same API | Next.js remains the Stage 6 plan and is consistent with React.js; the plain interface stands until Stage 6 is run |
| Database technology | Table 3.12: PostgreSQL | SQLite file in `webapp/data/`, written through SQLAlchemy (`src/antenatal/storage.py`) | Kept for a local, single user prototype that satisfies R14. A server database needs only a different `ANTENATAL_DATABASE_URL` and its driver |
