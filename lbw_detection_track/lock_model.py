"""Protocol Section 7: apply the selection rule, fix thresholds, refit and save. No test record."""

from __future__ import annotations

import hashlib
import json
import warnings

import joblib
import numpy as np
import pandas as pd
from features import SETS, TRACK, at_landmark, load_raw
from methods import ENSEMBLE, build
from run_experiments import OUT, check_records, ids
from scoring import at_threshold, threshold_for

LOCKED = TRACK / "locked"


def tie_break(row: pd.Series) -> tuple[int, int, int]:
    """Fewer inputs, then linear over tree, then no resampling or weighting."""
    tree = 0 if row["method"].startswith("logistic") and row["method"] != ENSEMBLE else 1
    adjusted = 1 if row["method"].endswith(("weighted", "smote")) else 0
    return len(SETS[row["set"]]), tree, adjusted


def select(table: pd.DataFrame) -> tuple[int, pd.Series, pd.DataFrame]:
    best_by_landmark = table.groupby("landmark")["roc_auc"].max()
    passing = best_by_landmark[best_by_landmark >= 0.70]
    week = int(passing.index.min() if len(passing) else best_by_landmark.idxmax())
    at_week = table[table["landmark"] == week]
    leader = at_week.loc[at_week["specificity_at_75"].idxmax()]
    tied = at_week[at_week["specificity_at_75"] >= leader["specificity_at_75"] - leader["spec_se"]]
    ranked = tied.assign(rank=tied.apply(tie_break, axis=1)).sort_values("rank")
    return week, ranked.iloc[0], ranked


def fit_final(frame: pd.DataFrame, set_name: str, method: str):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return build(method).fit(
            frame[SETS[set_name]].to_numpy(float),
            frame["lbw"].to_numpy(),
            frame["group"].to_numpy(),
        )


def main() -> None:
    LOCKED.mkdir(exist_ok=True)
    table = pd.read_csv(OUT / "development_results.csv")
    week, chosen, tied = select(table)
    tied.drop(columns="rank").to_csv(OUT / "selection_ties.csv", index=False)
    raw = load_raw(ids("development_ids"))
    check_records(raw.index)
    frame = at_landmark(raw, week)
    oof = pd.read_parquet(OUT / "development_oof.parquet")
    record = {
        "landmark": week,
        "primary_set": chosen["set"],
        "method": chosen["method"],
        "best_roc_auc_any_landmark": float(table["roc_auc"].max()),
        "models": {},
    }
    for set_name in sorted({"A", "B", "C", chosen["set"]}):
        rows = oof[
            (oof["landmark"] == week)
            & (oof["set"] == set_name)
            & (oof["method"] == chosen["method"])
        ].set_index("record_id")
        p, y = rows.loc[frame.index, "p"].to_numpy(), frame["lbw"].to_numpy()
        threshold = threshold_for(y, p)
        path = LOCKED / f"model_set_{set_name}.joblib"
        joblib.dump(fit_final(frame, set_name, chosen["method"]), path)
        record["models"][set_name] = {
            "threshold": threshold,
            "development_at_threshold": at_threshold(y, p, threshold),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    (LOCKED / "locked.json").write_text(json.dumps(record, indent=1))
    print(json.dumps(record, indent=1))
    print(tied[["set", "method", "specificity_at_75", "roc_auc", "rank"]].to_string())
    assert np.isfinite(record["models"][chosen["set"]]["threshold"])


if __name__ == "__main__":
    main()
