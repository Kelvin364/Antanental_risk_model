"""Protocol Sections 2 and 3: rank by predicted birth weight, compared with the classifiers.

Run after follow_up/run.py: ``python lbw_detection_track/continuous/run.py``.
Writes outputs/predictions.parquet, outputs/estimates.csv and outputs/comparisons.csv.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
TRACK = HERE.parent
if str(TRACK) not in sys.path:
    sys.path.insert(0, str(TRACK))

from features import ROOT, SETS, at_landmark, load_raw  # noqa: E402
from joblib import Parallel, delayed  # noqa: E402
from methods import SEED, _prepare  # noqa: E402
from run_experiments import FOLDS, REPEATS, check_records, ids  # noqa: E402
from scoring import interval, resamples  # noqa: E402
from sklearn.ensemble import HistGradientBoostingRegressor  # noqa: E402
from sklearn.linear_model import RidgeCV  # noqa: E402
from sklearn.metrics import average_precision_score, roc_auc_score  # noqa: E402
from sklearn.model_selection import StratifiedGroupKFold  # noqa: E402
from sklearn.pipeline import make_pipeline  # noqa: E402

OUT = HERE / "outputs"
CLASSIFIERS = TRACK / "follow_up/outputs/predictions.parquet"
LANDMARKS, NAMES = (28, 36), ("B", "D")
REGRESSORS = ("ridge", "boosting_reg", "quantile_reg")
BOUNDS, BOOT_SEED, RESAMPLES = (0.5, 5.5), 20261111, 2000
PAIRS = (("boosting_reg", "boosting"), ("ridge", "logistic"), ("quantile_reg", "boosting"))


def regressor(method: str):
    trees = dict(learning_rate=0.05, max_iter=150, max_depth=3, min_samples_leaf=30,
                 l2_regularization=1.0, random_state=SEED)  # fmt: skip
    if method == "ridge":
        return make_pipeline(_prepare(), RidgeCV(alphas=np.logspace(-2, 4, 25)))
    if method == "quantile_reg":
        return HistGradientBoostingRegressor(loss="quantile", quantile=0.1, **trees)
    return HistGradientBoostingRegressor(**trees)


def out_of_fold(frame: pd.DataFrame, columns: list[str], method: str) -> np.ndarray:
    """Same splits as run_experiments.out_of_fold; the target is the birth weight."""
    x, y = frame[columns].to_numpy(float), frame["lbw"].to_numpy()
    weight, groups = frame["weight_kg"].clip(*BOUNDS).to_numpy(), frame["group"].to_numpy()
    total = np.zeros(len(frame))
    for repeat in range(REPEATS):
        splitter = StratifiedGroupKFold(FOLDS, shuffle=True, random_state=SEED + repeat)
        for train, test in splitter.split(frame, y, groups):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                total[test] -= regressor(method).fit(x[train], weight[train]).predict(x[test])
    return total / REPEATS


def job(frame, week, name, method):
    p = out_of_fold(frame, SETS[name], method)
    return pd.DataFrame({"record_id": frame.index, "week": week, "set": name,
                         "method": method, "p": p})  # fmt: skip


def measures(table: pd.DataFrame) -> dict[str, float]:
    y = table["lbw"].to_numpy()
    out = {}
    for column in table.columns.drop("lbw"):
        out[(column, "roc_auc")] = roc_auc_score(y, table[column])
        out[(column, "pr_auc")] = average_precision_score(y, table[column])
    return out


def evaluate(predictions: pd.DataFrame, labels: pd.Series, groups: pd.Series):
    estimates, comparisons = [], []
    for (week, name), part in predictions.groupby(["week", "set"]):
        table = part.pivot(index="record_id", columns="method", values="p")
        table["lbw"] = labels.loc[table.index]
        point = measures(table)
        draws = pd.DataFrame(
            [
                measures(table.iloc[i])
                for i in resamples(groups.loc[table.index].to_numpy(), RESAMPLES, BOOT_SEED)
            ]
        )
        for key, value in point.items():
            low, high, _ = interval(draws[key].tolist())
            estimates.append({"week": week, "set": name, "method": key[0], "measure": key[1],
                              "estimate": value, "low": low, "high": high})  # fmt: skip
        for new, old in PAIRS:
            diff = (draws[(new, "roc_auc")] - draws[(old, "roc_auc")]).to_numpy()
            low, high, _ = interval(diff.tolist())
            primary = (week, name, new) == (28, "D", "boosting_reg")
            comparisons.append({
                "role": "primary" if primary else "secondary", "week": week, "set": name,
                "method": new, "against": old,
                "difference": point[(new, "roc_auc")] - point[(old, "roc_auc")],
                "low": low, "high": high,
                "p_value": min(1.0, 2 * min((diff <= 0).mean(), (diff >= 0).mean())),
            })  # fmt: skip
    return pd.DataFrame(estimates), pd.DataFrame(comparisons)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    raw = load_raw(ids("development_ids"))
    check_records(raw.index)
    manifest = pd.read_csv(ROOT / "outputs/cohort_manifest.csv", index_col="record_id")
    jobs = []
    for week in LANDMARKS:
        frame = at_landmark(raw, week)
        frame["weight_kg"] = manifest.loc[frame.index, "birth_weight_kg"]
        jobs += [(frame, week, s, m) for s in NAMES for m in REGRESSORS]
    done = Parallel(n_jobs=-1, verbose=1)(delayed(job)(*j) for j in jobs)
    mine = pd.concat(done, ignore_index=True)
    mine.to_parquet(OUT / "predictions.parquet")
    theirs = pd.read_parquet(CLASSIFIERS).query("population == 'full'").drop(columns="population")
    both = pd.concat([mine, theirs], ignore_index=True)
    estimates, comparisons = evaluate(both, raw["lbw"].astype(int), raw["group_key_hash"])
    estimates.to_csv(OUT / "estimates.csv", index=False)
    comparisons.to_csv(OUT / "comparisons.csv", index=False)
    wide = estimates.pivot_table(index=["week", "set", "method"], columns="measure",
                                 values="estimate")  # fmt: skip
    print(wide.round(3).to_string())
    print(comparisons.round(3).to_string())


if __name__ == "__main__":
    main()
