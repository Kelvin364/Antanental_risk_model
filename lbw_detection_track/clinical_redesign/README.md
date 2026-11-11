# Clinical redesign

The next research phase after the [target study](../target_study/REPORT.md). It asks what must change in outcomes, predictors, measurement and timing for a stronger low birth weight prediction system, rather than trying more algorithms.

* [REPORT.md](REPORT.md): findings and the eight deliverables, with ranked recommendations.
* [PROTOCOL.md](PROTOCOL.md): draft protocol for the future study, for supervisor review.

No model is fitted in this folder. The served model, the web application, the main study and both sealed partitions are untouched. Outcome values are read only for the 3,126 development records, through the served frame. The audit of the whole file reads predictor fields only.

## Scripts and outputs

Run from the repository root with the virtual environment active, in this order (about 40 seconds in all):

| Script | Reads | Writes to outputs/ |
| --- | --- | --- |
| `field_audit.py` | Predictor fields of the whole file | `field_audit.json`, `predictor_inventory.csv` |
| `outcome_study.py` | Development records; target study stored scores | `outcome_decomposition.csv`, `outcome_quality.json`, `discrimination_by_case_type.csv` |
| `early_visit.py` | Development records; stored scores; track development pool visit weeks | `early_visit_by_config.csv`, `early_visit_case_mix.csv`, `early_visit_summary.json`, `landmark_reach.csv` |
| `sample_size.py` | `outcome_decomposition.csv`; main study `outputs/tables/cohort_flow.csv` | `sample_size_development.csv`, `sample_size_validation.csv`, `feasibility.json` |

```
python lbw_detection_track/clinical_redesign/field_audit.py
python lbw_detection_track/clinical_redesign/outcome_study.py
python lbw_detection_track/clinical_redesign/early_visit.py
python lbw_detection_track/clinical_redesign/sample_size.py
```

`early_visit.py` and `outcome_study.py` need `lbw_detection_track/target_study/outputs/nested_predictions.parquet` from the target study run. Group bootstrap intervals use 2,000 resamples with seed 20261111.
