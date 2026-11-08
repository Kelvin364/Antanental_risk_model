"""Checks added after the results were seen; descriptive only and labelled post hoc in REPORT.md.

1. Whether having a week 36 visit is itself linked to the outcome (it is known only at
   36 weeks and an early birth removes the chance of that visit).
2. Specificity at 75 percent sensitivity for option 1 and option 4 with the same in sample
   cut off rule, so the stacker gets no credit that belongs to the cut off.
"""

from __future__ import annotations

import json
from pathlib import Path

import measures
import nested
import pandas as pd
from frames import load
from scoring import at_threshold, threshold_for

OUT = Path(__file__).resolve().parent / "outputs"


def main() -> None:
    frames = load()
    predictions = pd.read_parquet(OUT / "nested_predictions.parquet")
    pooled = measures.pooled(predictions, frames.served["lbw"])
    seen, y = pooled["has_two"], pooled["lbw"]
    weights = pd.read_csv(OUT / "stacker_weights.csv", index_col=0)["mean"]
    typical = nested.logit(pooled.loc[seen, "p2"].median())
    record = {
        "base_rate_with_week36_visit": float(y[seen].mean()),
        "base_rate_without_week36_visit": float(y[~seen].mean()),
        "events_without_week36_visit": int(y[~seen].sum()),
        "records_without_week36_visit": int((~seen).sum()),
        "stacker_shift_for_typical_week36_score_log_odds": float(
            weights["stack_has2"] + weights["stack_w2"] * typical
        ),
    }
    for option, column in (("1 served", "p1"), ("4 stacked", "p4"), ("4b average", "p_avg")):
        p = pooled[column].to_numpy()
        record[f"{option}, in sample cut off at 75 percent sensitivity"] = at_threshold(
            y.to_numpy(), p, threshold_for(y.to_numpy(), p)
        )
    (OUT / "post_hoc.json").write_text(json.dumps(record, indent=1))
    print(json.dumps(record, indent=1))


if __name__ == "__main__":
    main()
