"""Protocol Section 4: grouped repeated cross validation with thresholds learnt in training.

Run from the repository root: ``python lbw_detection_track/whole_pregnancy/run.py``.
Writes outputs/predictions.parquet, outputs/checks.json and outputs/p2_check.json.
"""

from __future__ import annotations

import json
import warnings

import history
import numpy as np
import pandas as pd
from features import load_raw
from joblib import Parallel, delayed
from methods import SEED, build
from run_experiments import check_records, ids, out_of_fold
from scoring import threshold_for
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold

OUT = history.HERE / "outputs"
REPEATS, FOLDS, INNER = 5, 5, 5
METHODS = ("logistic", "boosting")
EXPECTED = {"records": 2612, "events": 82}


def splits(y: np.ndarray, groups: np.ndarray, folds: int, seed: int):
    for train, test in StratifiedGroupKFold(folds, shuffle=True, random_state=seed).split(
        y, y, groups
    ):
        if set(groups[train]) & set(groups[test]):
            raise RuntimeError("A registration group crosses a fold.")
        yield train, test


def _fit(x, y, groups, method):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return build(method).fit(x, y, groups)


def at_specificity(y: np.ndarray, p: np.ndarray, target: float = 0.90) -> float:
    controls = np.sort(p[y == 0])[::-1]
    return float(controls[int(np.ceil((1 - target) * len(controls))) - 1])


def rules(x, y, groups, method, seed) -> dict[str, float]:
    """Both thresholds from inner out of fold scores of the training records only."""
    inner = np.full(len(y), np.nan)
    for train, test in splits(y, groups, INNER, seed):
        inner[test] = _fit(x[train], y[train], groups[train], method).predict_proba(x[test])[:, 1]
    return {"t75": threshold_for(y, inner), "t90": at_specificity(y, inner)}


def config(frame: pd.DataFrame, name: str, method: str) -> pd.DataFrame:
    x = frame[history.SET_NAMES[name]].to_numpy(float)
    y, groups = frame["lbw"].to_numpy(), frame["group"].to_numpy()
    parts = []
    for repeat in range(REPEATS):
        for fold, (train, test) in enumerate(splits(y, groups, FOLDS, SEED + repeat)):
            t = rules(x[train], y[train], groups[train], method, SEED + repeat)
            p = _fit(x[train], y[train], groups[train], method).predict_proba(x[test])[:, 1]
            parts.append(pd.DataFrame({
                "record_id": frame.index[test], "repeat": repeat, "fold": fold, "p": p,
                "flag_75": p >= t["t75"], "flag_90": p >= t["t90"], **t,
            }))  # fmt: skip
    return pd.concat(parts).assign(set=name, method=method)


def p2_check(raw: pd.DataFrame) -> dict:
    """Leakage demonstration: what the timing of the last visit alone reveals."""
    frame = history.any_visit_frame(raw)
    y = frame["lbw"].to_numpy()
    single = {}
    for column in ("ga", "visits_by_36"):
        known = frame[column].notna()
        auc = roc_auc_score(y[known], frame.loc[known, column])
        single[column] = max(auc, 1 - auc)
    p = out_of_fold(frame, history.SET_NAMES["B"], "logistic")
    return {"records": len(frame), "events": int(y.sum()), "single_predictor_auc": single,
            "logistic_set_b_latest_any_visit_roc_auc": roc_auc_score(y, p)}  # fmt: skip


def main() -> None:
    OUT.mkdir(exist_ok=True)
    raw = load_raw(ids("development_ids"))
    check_records(raw.index)
    frame = history.primary_frame(raw)
    counts = {"records": len(frame), "events": int(frame["lbw"].sum())}
    if counts != EXPECTED:
        raise RuntimeError(f"Population differs from the protocol: {counts}")
    jobs = [(s, m) for s in history.SET_NAMES for m in METHODS]
    done = Parallel(n_jobs=-1, verbose=2)(delayed(config)(frame, s, m) for s, m in jobs)
    pd.concat(done, ignore_index=True).to_parquet(OUT / "predictions.parquet")
    (OUT / "checks.json").write_text(json.dumps(counts, indent=1) + "\n")
    check = p2_check(raw)
    (OUT / "p2_check.json").write_text(json.dumps(check, indent=1) + "\n")
    print(json.dumps(counts | {"p2": check}, indent=1))


if __name__ == "__main__":
    main()
