"""Group bootstrap intervals for the selected model's ROC AUC by week of visit two (Section 8.5).

Added after ``ceiling.py`` showed a higher estimate for early second visits; descriptive only.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import predictors
from ceiling import OUT
from evaluate import RESAMPLES, SEED, interval, resamples
from sklearn.metrics import roc_auc_score

BANDS = (("up to 20", 0, 20), ("21 to 24", 20, 24), ("25 to 28", 24, 28))


def main() -> None:
    data = predictors.build()
    name, set_name = json.loads((OUT / "selection.json").read_text())["selected"]
    predictions = pd.read_parquet(OUT / "nested_predictions.parquet")
    part = predictions[(predictions["model"] == name) & (predictions["set"] == set_name)]
    p = part.groupby("record_id")["p"].mean().loc[data["ids"]].to_numpy()
    rows = []
    for label, low, high in BANDS:
        keep = (data["ga_v2"] > low) & (data["ga_v2"] <= high)
        y, q, g = data["y"][keep], p[keep], data["groups"][keep]
        draws = [roc_auc_score(y[i], q[i]) for i in resamples(g, RESAMPLES, SEED)
                 if 0 < y[i].sum() < len(i)]  # fmt: skip
        lo, hi, _ = interval(draws)
        rows.append({"visit_two_week": label, "records": int(keep.sum()), "cases": int(y.sum()),
                     "roc_auc": roc_auc_score(y, q), "low": lo, "high": hi})  # fmt: skip
    table = pd.DataFrame(rows)
    table.to_csv(OUT / "roc_by_visit_two_week.csv", index=False)
    print(table.round(3).to_string(index=False), np.round(p.mean(), 4))


if __name__ == "__main__":
    main()
