# Sequential strategy

Tests whether the week 36 model can serve as a second look for women the served model did not flag at 28 weeks. The served model and its threshold stay unchanged as the first step.

* [PROTOCOL.md](PROTOCOL.md): the plan, committed before any result.
* [REPORT.md](REPORT.md): results, the recommendation, the proposed architecture and limitations.

It reuses the folds, seed and model fitting of the [fusion analysis](../fusion/REPORT.md) and checks that every score matches it exactly. No sealed list is opened, and nothing in the main study or the web application changes.

| Script | Does | Writes to outputs/ |
| --- | --- | --- |
| `run_nested.py` | Rebuilds both models in each outer fold. Learns every threshold from inner training scores, then applies the strategies to outer test records | `nested_predictions.parquet`, `fold_rules.csv`, `checks.json` |
| `evaluate.py` | Group bootstrap estimates, paired comparisons, the decision rule, attendance accounting and baseline reproduction | `estimates.csv`, `comparisons.csv`, `decision.json`, `attendance.csv`, `baseline_reproduction.json` |
| `rules.py` | Thresholds and the updated late score (protocol Section 4) | |
| `strategy_measures.py` | Measures for each strategy and score (protocol Section 6) | |

```
python lbw_detection_track/sequential/run_nested.py
python lbw_detection_track/sequential/evaluate.py
```
