"""Protocol Sections 5 to 7 on development pool records only. The test list is read only to
assert that none of its records is present."""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from features import LANDMARKS, SETS, TRACK, at_landmark, load_raw
from joblib import Parallel, delayed
from methods import ENSEMBLE, METHODS, SEED, build
from scoring import interval, resamples, specificity_at_target, summary
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold

REPEATS, FOLDS, RESAMPLES = 5, 5, 2000
SEALED, OUT = TRACK / "sealed", TRACK / "outputs"


def ids(name: str) -> pd.Series:
    return pd.read_csv(SEALED / f"{name}.csv")["record_id"]


def check_records(index: pd.Index) -> None:
    forbidden = set(ids("test_ids")) | set(ids("quarantine_ids"))
    if forbidden & set(index):
        raise RuntimeError("A sealed or quarantined record reached the development frame.")


def single_predictor_check(frame: pd.DataFrame, week: int) -> pd.DataFrame:
    """Stops the run if any one predictor alone looks too good to be honest."""
    rows = []
    for column in SETS["D"]:
        known = frame[column].notna()
        if known.sum() > 50 and frame.loc[known, column].nunique() > 1:
            auc = roc_auc_score(frame.loc[known, "lbw"], frame.loc[known, column])
            rows.append({"landmark": week, "column": column, "auc": max(auc, 1 - auc)})
    table = pd.DataFrame(rows).sort_values("auc", ascending=False)
    if table["auc"].max() >= 0.80:
        raise RuntimeError(f"Possible leakage: {table.head(3).to_dict('records')}")
    return table


def fit_fold(frame, columns, method, train, test):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = build(method).fit(
            frame.iloc[train][columns].to_numpy(float),
            frame.iloc[train]["lbw"].to_numpy(),
            frame.iloc[train]["group"].to_numpy(),
        )
        return test, model.predict_proba(frame.iloc[test][columns].to_numpy(float))[:, 1]


def out_of_fold(frame: pd.DataFrame, columns: list[str], method: str) -> np.ndarray:
    y, groups = frame["lbw"].to_numpy(), frame["group"].to_numpy()
    total = np.zeros(len(frame))
    for repeat in range(REPEATS):
        splitter = StratifiedGroupKFold(FOLDS, shuffle=True, random_state=SEED + repeat)
        for train, test in splitter.split(frame, y, groups):
            if set(groups[train]) & set(groups[test]):
                raise RuntimeError("A registration group crosses a fold.")
            positions, probabilities = fit_fold(frame, columns, method, train, test)
            total[positions] += probabilities
    return total / REPEATS


def score(week, name, method, y, groups, p):
    row = {"landmark": week, "set": name, "method": method, "n": len(y), "events": int(y.sum())}
    row |= summary(y, p)
    aucs, specs = [], []
    for picks in resamples(groups, RESAMPLES, SEED):
        if 0 < y[picks].sum() < len(picks):
            aucs.append(roc_auc_score(y[picks], p[picks]))
            specs.append(specificity_at_target(y[picks], p[picks]))
    row["roc_low"], row["roc_high"], row["roc_se"] = interval(aucs)
    row["spec_low"], row["spec_high"], row["spec_se"] = interval(specs)
    return row


def job(frame, week, name, method):
    return week, name, method, out_of_fold(frame, SETS[name], method)


def main() -> None:
    raw = load_raw(ids("development_ids"))
    check_records(raw.index)
    frames = {week: at_landmark(raw, week) for week in LANDMARKS}
    checks = pd.concat([single_predictor_check(f, w) for w, f in frames.items()])
    checks.to_csv(OUT / "single_predictor_check.csv", index=False)
    print("Largest single predictor AUC", round(checks["auc"].max(), 3), flush=True)
    tasks = [(w, s, m) for w in LANDMARKS for s in SETS for m in METHODS]
    done = Parallel(n_jobs=-1, verbose=5)(
        delayed(job)(frames[w], w, s, m) for w, s, m in tasks
    )
    predictions = {(w, s, m): p for w, s, m, p in done}
    for w in LANDMARKS:
        for s in SETS:
            pair = predictions[w, s, "logistic"], predictions[w, s, "boosting"]
            predictions[w, s, ENSEMBLE] = (pair[0] + pair[1]) / 2
    rows = Parallel(n_jobs=-1)(
        delayed(score)(
            w, s, m, frames[w]["lbw"].to_numpy(), frames[w]["group"].to_numpy(), p
        )
        for (w, s, m), p in predictions.items()
    )
    table = pd.DataFrame(rows).sort_values(["landmark", "set", "method"])
    table.to_csv(OUT / "development_results.csv", index=False)
    long = [
        pd.DataFrame({"record_id": frames[w].index, "landmark": w, "set": s, "method": m, "p": p})
        for (w, s, m), p in predictions.items()
    ]
    pd.concat(long).to_parquet(OUT / "development_oof.parquet")


if __name__ == "__main__":
    main()
