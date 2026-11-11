"""Protocol Section 3: rebuild both models in the fusion analysis's folds and apply the rules.

Run from the repository root: ``python lbw_detection_track/sequential/run_nested.py``.
Writes outputs/nested_predictions.parquet, outputs/fold_rules.csv and outputs/checks.json.
"""

from __future__ import annotations

import json

import _paths  # noqa: F401  (import path to the fusion and track code)
import frames as frames_module
import nested
import numpy as np
import pandas as pd
import rules
from _paths import FUSION, OUT
from joblib import Parallel, delayed

TOLERANCE = 1e-9


def outer_fold(frames, repeat: int, fold: int, train, test) -> pd.DataFrame:
    seed = nested.SEED + repeat
    outer_groups = set(frames.served.loc[test, "group_key_hash"])
    if set(frames.served.loc[train, "group_key_hash"]) & outer_groups:
        raise RuntimeError("A registration group crosses an outer fold.")
    y_train = frames.served.loc[train, "lbw"].to_numpy()
    model, t = rules.learn(y_train, *nested.inner_scores(frames, train, outer_groups, seed))
    bases = nested.Bases(frames, train, outer_groups, seed)
    p1, p2 = bases.score(frames, test)
    pu = rules.updated(model, p1, p2)
    columns = {"record_id": test, "repeat": repeat, "fold": fold, "p1": p1, "p2": p2, "pu": pu}
    columns |= rules.flags(p1, p2, pu, t)
    columns |= {f"rule_{k}": v for k, v in t.items()}
    columns |= {"upd_w1": model.coef_[0, 0], "upd_w2": model.coef_[0, 1]}
    return pd.DataFrame(columns)


def run(frames) -> pd.DataFrame:
    jobs = Parallel(n_jobs=-1, verbose=2)(
        delayed(outer_fold)(frames, r, f, train, test) for r, f, train, test in nested.tasks(frames)
    )
    predictions = pd.concat(jobs, ignore_index=True)
    counts = predictions.groupby("repeat")["record_id"].nunique()
    if (counts != len(frames.served)).any():
        raise RuntimeError("A repeat did not score every record exactly once.")
    return predictions


def reproduces_fusion(predictions: pd.DataFrame) -> dict[str, float]:
    """Protocol Section 3 check: the same folds, models and scores as the fusion analysis."""
    stored = pd.read_parquet(FUSION / "outputs" / "nested_predictions.parquet")
    keys = ["repeat", "fold", "record_id"]
    both = predictions.merge(stored[[*keys, "p1", "p2", "flag1"]], on=keys, suffixes=("", "_f"))
    if len(both) != len(predictions) or len(both) != len(stored):
        raise RuntimeError("Records or folds differ from the fusion analysis.")
    gap1 = float(np.abs(both["p1"] - both["p1_f"]).max())
    gap2 = float(np.nanmax(np.abs(both["p2"] - both["p2_f"])))
    same_flags = bool((both["flag_base"] == both["flag1"]).all())
    if gap1 > TOLERANCE or gap2 > TOLERANCE or not same_flags:
        raise RuntimeError(f"Rebuild differs from the fusion analysis: {gap1}, {gap2}.")
    return {"max_baseline_score_gap": gap1, "max_late_score_gap": gap2, "same_flags": same_flags}


def main() -> None:
    OUT.mkdir(exist_ok=True)
    frames = frames_module.load()
    record = {"counts": frames_module.check(frames)}
    predictions = run(frames)
    record["reproduces_fusion"] = reproduces_fusion(predictions)
    predictions.to_parquet(OUT / "nested_predictions.parquet")
    folds = predictions.drop_duplicates(["repeat", "fold"])
    columns = [c for c in predictions if c.startswith(("rule_", "upd_w"))]
    folds[["repeat", "fold", *columns]].to_csv(OUT / "fold_rules.csv", index=False)
    (OUT / "checks.json").write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps(record, indent=1))


if __name__ == "__main__":
    main()
