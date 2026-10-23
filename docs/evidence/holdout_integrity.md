# Held out partition integrity

Written by `python -m antenatal audit-holdout` on 2026-10-23T15:22:50+00:00.
The supervisor's one absolute rule is that the held out records never reach training
(decision D7). Each check below reads identifiers, predictor values or stored outputs
only; none reads a held out outcome, fits a model or scores the held out records.

| Check | Result | Value | Evidence |
| --- | --- | --- | --- |
| Held out file matches its recorded SHA 256 | pass | 249114c363dab8a8 | `partitions/holdout.sha256, verified on load` |
| Development records that are held out | pass | 0 | `Partition.development` |
| Registration groups shared by both partitions | pass | 0 | `group_key of both partitions` |
| Training guard refuses a held out record | pass | 782 records blocked | `TrainingGuard, required by every model fit` |
| Held out records in oof_predictions.parquet | pass | 0 | `outputs/oof_predictions.parquet` |
| Held out records in oof_extensions.parquet | pass | 0 | `outputs/oof_extensions.parquet` |
| Held out records in learning_curve_predictions.parquet | pass | 0 | `outputs/learning_curve_predictions.parquet` |
| Served reference caseload equals development out of fold predictions | pass | 3126 | `webapp/model/lbw_model.joblib` |
| Held out records with a predictor vector identical to a development record | pass | 0 | `25 predictors of the served model` |
| Held out evaluations recorded | pass | 0 | `partitions/holdout_access.log` |

10 of 10 checks passed.

What the checks mean. The first three show the split itself is clean: the file is the
sealed one, no record and no registration group is on both sides. The guard check shows
that a held out record offered to any model fit is refused. The stored prediction checks
show that no saved cross validation output ever scored a held out record. The reference
check shows that the served model's caseload was built from development predictions only.
The duplicate check looks for held out records that copy a development record value for
value, which would let a model recognise them. The last check counts evaluations of the
held out records: more than one would mean the held out records had been used to choose.
