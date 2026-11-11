"""Protocol Sections 2 and 3: follow up window, landmarks 28 and 36, term and preterm cases.

Run from the repository root: ``python lbw_detection_track/follow_up/run.py``.
Writes outputs/by_quarter.csv, outputs/predictions.parquet and outputs/results.csv.
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
from run_experiments import check_records, ids, out_of_fold  # noqa: E402
from scoring import interval, resamples  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402

OUT = HERE / "outputs"
WINDOW = ("2024-01-01", "2024-09-30")
LANDMARKS, NAMES, METHODS = (28, 36), ("B", "D"), ("logistic", "boosting")
SEED, RESAMPLES = 20261111, 2000


def calendar(index: pd.Index) -> pd.DataFrame:
    """Start date and recorded preterm birth; preterm is for description only."""
    cols = ["SN", "last_normal_menustration_date", "preterm_labour"]
    raw = pd.read_csv(ROOT / "data/maternal_dataset_csv.csv", dtype=str, usecols=cols)
    raw = raw.assign(SN=raw["SN"].astype(int)).set_index("SN").loc[index]
    start = pd.to_datetime(raw["last_normal_menustration_date"], format="%m/%d/%Y", errors="coerce")
    preterm = raw["preterm_labour"].str.lower().eq("yes").astype(int)
    return pd.DataFrame({"start": start, "preterm": preterm}, index=index)


def by_quarter(raw: pd.DataFrame, cal: pd.DataFrame) -> pd.DataFrame:
    frame = cal.assign(lbw=raw["lbw"].astype(int), quarter=cal["start"].dt.to_period("Q"))
    table = frame.groupby("quarter").agg(
        records=("lbw", "size"), lbw=("lbw", "sum"), preterm=("preterm", "sum")
    )
    table["lbw_share"] = table["lbw"] / table["records"]
    table["preterm_share"] = table["preterm"] / table["records"]
    return table[table["records"] >= 20].reset_index().astype({"quarter": str})


def _auc(y, p, keep):
    return roc_auc_score(y[keep], p[keep]) if 0 < y[keep].sum() < keep.sum() else np.nan


def measures(y, p, preterm) -> dict[str, float]:
    control = y == 0
    return {
        "roc_auc": roc_auc_score(y, p),
        "term_cases_auc": _auc(y, p, control | ((y == 1) & (preterm == 0))),
        "preterm_cases_auc": _auc(y, p, control | ((y == 1) & (preterm == 1))),
    }


def job(frame, week, population, name, method):
    p = out_of_fold(frame, SETS[name], method)
    return pd.DataFrame({"record_id": frame.index, "week": week, "population": population,
                         "set": name, "method": method, "p": p})  # fmt: skip


def summarise(predictions: pd.DataFrame, raw: pd.DataFrame, cal: pd.DataFrame) -> pd.DataFrame:
    rows = []
    keys = ["week", "population", "set", "method"]
    for key, part in predictions.groupby(keys):
        ids_ = part["record_id"].to_numpy()
        y = raw.loc[ids_, "lbw"].astype(int).to_numpy()
        pre, p = cal.loc[ids_, "preterm"].to_numpy(), part["p"].to_numpy()
        groups = raw.loc[ids_, "group_key_hash"].to_numpy()
        point = measures(y, p, pre)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            draws = pd.DataFrame([measures(y[i], p[i], pre[i])
                                  for i in resamples(groups, RESAMPLES, SEED)])  # fmt: skip
        row = dict(zip(keys, key, strict=True)) | {"records": len(y), "cases": int(y.sum()),
                                      "preterm_cases": int((y * pre).sum())}  # fmt: skip
        for measure, value in point.items():
            low, high, _ = interval(draws[measure].dropna().tolist())
            row |= {measure: value, f"{measure}_low": low, f"{measure}_high": high}
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    raw = load_raw(ids("development_ids"))
    check_records(raw.index)
    cal = calendar(raw.index)
    by_quarter(raw, cal).to_csv(OUT / "by_quarter.csv", index=False)
    in_window = cal["start"].between(*WINDOW)
    jobs = []
    for week in LANDMARKS:
        full = at_landmark(raw, week)
        window = full[in_window.loc[full.index]]
        for population, frame in (("full", full), ("window", window)):
            jobs += [(frame, week, population, s, m) for s in NAMES for m in METHODS]
    done = Parallel(n_jobs=-1, verbose=1)(delayed(job)(*j) for j in jobs)
    predictions = pd.concat(done, ignore_index=True)
    predictions.to_parquet(OUT / "predictions.parquet")
    result = summarise(predictions, raw, cal)
    result.to_csv(OUT / "results.csv", index=False)
    print(result.round(3).to_string())


if __name__ == "__main__":
    main()
