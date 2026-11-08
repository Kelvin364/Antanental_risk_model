"""Run the fusion protocol end to end on development records and write every result.

Run from the repository root: ``python lbw_detection_track/fusion/run_fusion.py``.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import frames as frames_module
import measures
import nested
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
STOP_AUC = 0.60
FROZEN = {"served": 0.0688, "week36": 0.029404318481584212}


def run(frames, repeats: int = nested.REPEATS) -> pd.DataFrame:
    jobs = Parallel(n_jobs=-1, verbose=2)(
        delayed(nested.outer_fold)(frames, r, f, train, test)
        for r, f, train, test in nested.tasks(frames, repeats)
    )
    predictions = pd.concat(jobs, ignore_index=True)
    counts = predictions.groupby("repeat")["record_id"].nunique()
    if (counts != len(frames.served)).any():
        raise RuntimeError("A repeat did not score every record exactly once.")
    return predictions


def shuffled(frames):
    """Negative control: outcomes permuted across records, the same value in both frames."""
    ids = frames.served.index.union(frames.week36.index)
    truth = pd.concat([frames.served["lbw"], frames.week36["lbw"]])
    truth = truth[~truth.index.duplicated()].loc[ids]
    permuted = pd.Series(
        np.random.default_rng(nested.SEED).permutation(truth.to_numpy()), index=ids
    )
    served = frames.served.assign(lbw=permuted.loc[frames.served.index].to_numpy())
    week36 = frames.week36.assign(lbw=permuted.loc[frames.week36.index].to_numpy())
    return replace(frames, served=served, week36=week36)


def negative_control(frames) -> dict[str, float]:
    control = shuffled(frames)
    predictions = run(control, repeats=1)
    y = control.served.loc[predictions["record_id"], "lbw"].to_numpy()
    result = {
        "roc_auc_option_1": roc_auc_score(y, predictions["p1"]),
        "roc_auc_option_4": roc_auc_score(y, predictions["p4"]),
    }
    if max(result.values()) > STOP_AUC:
        raise RuntimeError(f"Negative control failed, possible leakage: {result}")
    return result


def reference_check(frames) -> pd.DataFrame:
    """Option 3 from the stored predictions and frozen thresholds (protocol Section 6.6)."""
    root = frames_module.ROOT
    served = pd.read_parquet(root / "outputs/oof_predictions.parquet")
    served = served[(served["model"] == "logistic_l2") & (served["feature_set"] == "C")]
    p1 = served.groupby("record_id")["probability"].mean().loc[frames.served.index]
    track = pd.read_parquet(root / "lbw_detection_track/outputs/development_oof.parquet")
    chosen = (track["landmark"] == 36) & (track["set"] == "B") & (track["method"] == "logistic")
    track = track[chosen]
    p2 = track.set_index("record_id")["p"].reindex(frames.served.index)
    y = frames.served["lbw"].to_numpy()
    one = (p1 >= FROZEN["served"]).to_numpy()
    two = (p2.fillna(-1) >= FROZEN["week36"]).to_numpy()
    rows = [
        {"option": name} | measures.flagging(y, flags.astype(float))
        for name, flags in (("1 served", one), ("3 two checks", one | two))
    ]
    return pd.DataFrame(rows)


def stacker_weights(predictions: pd.DataFrame) -> pd.DataFrame:
    folds = predictions.drop_duplicates(["repeat", "fold"])
    columns = ["stack_w1", "stack_has2", "stack_w2", "two_trained_on"]
    columns += [c for c in predictions if c.startswith("threshold_")]
    return folds[columns].describe().T[["mean", "min", "max"]]


def main() -> None:
    OUT.mkdir(exist_ok=True)
    frames = frames_module.load()
    record = {"counts": frames_module.check(frames)}
    predictions = run(frames)
    predictions.to_parquet(OUT / "nested_predictions.parquet")
    stacker_weights(predictions).to_csv(OUT / "stacker_weights.csv")
    record["negative_control"] = negative_control(frames)
    reference_check(frames).to_csv(OUT / "reference_check.csv", index=False)
    pooled = measures.pooled(predictions, frames.served["lbw"])
    groups = frames.served.loc[pooled.index, "group_key_hash"].to_numpy()
    draws = measures.bootstrap(pooled, groups, nested.SEED)
    record["bootstrap_resamples_used"] = len(draws)
    measures.estimates(pooled, draws).to_csv(OUT / "estimates.csv", index=False)
    measures.comparisons(pooled, draws).to_csv(OUT / "comparisons.csv", index=False)
    (OUT / "checks.json").write_text(json.dumps(record, indent=1))
    print(json.dumps(record, indent=1))


if __name__ == "__main__":
    main()
