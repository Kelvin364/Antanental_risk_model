# Deviations from the proposal and the implementation guideline

Every place where the data or an implementation decision departs from the
proposal or the guideline is listed here, with its treatment, so it can be
taken to the supervisor. Each count is produced by code in this repository.

| Item | Proposal or guideline | What the data or the code gives | Treatment |
| --- | --- | --- | --- |
| S1 cohort, visit two by 24 weeks | Table 3.8: 2,444 records, 142 events | 2,449 records, 142 events (`outputs/tables/sensitivity_cohorts.csv`) | Report the computed count; correct Table 3.8 |
| S5 and S6 events | Table 3.8: 178 events, 5.68 percent | Both keep the primary cohort, 3,908 records and 206 events | Correct Table 3.8 |
| S4 size | Table 3.8: 3,135 records, 178 events | Depends on the development screen; computed in `outputs/tables/sensitivity_analyses.csv` | Report the computed count |
| Pulse range | Not stated in Section 3.3.3 | Needed to clean pulse | 30 to 200 beats per minute, recorded in `StudySpec`; being added to Section 3.3.3 |
| Missing values in the tree model | Section 3.3.6: native handling | Implemented as stated | Median imputation with indicators kept as the sensitivity row "GBT, uniform imputation" |
| Repository layout | Flatten `antenatal-caseload-prediction/` into the root | The folder was already flat | No change needed |
