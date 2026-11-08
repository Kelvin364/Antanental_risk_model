"""Protocol Section 5: nested validation of every model on every predictor set.

Run from the repository root: ``python lbw_detection_track/target_study/run_targets.py``.
Thresholds are fixed from honest training scores; outer outcomes are never used to choose them.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import predictors
import zoo
from joblib import Parallel, delayed
from sklearn.base import clone
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold, cross_val_predict

OUT = Path(__file__).resolve().parent / "outputs"
REPEATS, FOLDS, INNER = 3, 5, 3
SPECIFICITY, SENSITIVITY = 0.90, 90 / 165


def grouped(y, groups, folds, seed):
    splits = list(StratifiedGroupKFold(folds, shuffle=True, random_state=seed).split(y, y, groups))
    for train, test in splits:
        if set(groups[train]) & set(groups[test]):
            raise RuntimeError("A registration group crosses a fold.")
    return splits


def thresholds(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    """T90: training specificity 90 percent. T54: training sensitivity at least 54.5 percent."""
    t90 = float(np.quantile(p[y == 0], SPECIFICITY))
    cases = np.sort(p[y == 1])[::-1]
    t54 = float(cases[int(np.ceil(SENSITIVITY * len(cases))) - 1])
    return {"t90": t90, "t54": t54}


def fit_one(data, name, set_name, repeat, fold, train, test):
    x, y, groups = data[set_name], data["y"], data["groups"]
    zoo.GROUPS.update(dict(zip(data["ids"], groups, strict=True)))  # each worker needs it
    data["guard"].check(pd.DataFrame({"record_id": data["ids"][train]}))
    seed = zoo.SEED + repeat
    pipeline, grid = zoo.model(name, list(x.columns), data["categorical"])
    xt, yt, gt = x.iloc[train], y[train], groups[train]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if grid:
            search = GridSearchCV(
                pipeline, grid, scoring="average_precision", cv=grouped(yt, gt, INNER, seed)
            )
            best, params = search.fit(xt, yt).best_estimator_, search.best_params_
        else:
            best, params = pipeline.fit(xt, yt), {}
        honest = cross_val_predict(
            clone(best), xt, yt, cv=grouped(yt, gt, INNER, seed + 100), method="predict_proba"
        )[:, 1]
        p_test = best.predict_proba(x.iloc[test])[:, 1]
        p_train = best.predict_proba(xt)[:, 1]
    t = thresholds(yt, honest)
    return pd.DataFrame(
        {
            "record_id": data["ids"][test], "model": name, "set": set_name, "repeat": repeat,
            "fold": fold, "p": p_test, "flag_t90": p_test >= t["t90"],
            "flag_t54": p_test >= t["t54"], "t90": t["t90"], "t54": t["t54"],
            "train_auc": roc_auc_score(yt, p_train), "honest_train_auc": roc_auc_score(yt, honest),
            "params": str(params),
        }
    )  # fmt: skip


def configurations():
    for set_name in ("F0", "F1", "F2"):
        for name in zoo.NAMES:
            yield name, set_name
    yield "multiple_imputation", "F1"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    data = predictors.build()
    zoo.GROUPS.update(dict(zip(data["ids"], data["groups"], strict=True)))
    splits = [
        (r, f, tr, te)
        for r in range(REPEATS)
        for f, (tr, te) in enumerate(grouped(data["y"], data["groups"], FOLDS, zoo.SEED + r))
    ]
    jobs = [(n, s, r, f, tr, te) for n, s in configurations() for r, f, tr, te in splits]
    done = Parallel(n_jobs=-1, verbose=5)(delayed(fit_one)(data, *job) for job in jobs)
    predictions = pd.concat(done, ignore_index=True)
    counts = predictions.groupby(["model", "set", "repeat"])["record_id"].nunique()
    if (counts != len(data["ids"])).any():
        raise RuntimeError("A repeat did not score every record exactly once.")
    predictions.to_parquet(OUT / "nested_predictions.parquet")


if __name__ == "__main__":
    main()
