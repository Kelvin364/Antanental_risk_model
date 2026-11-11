"""Protocol Section 5: estimates and paired comparisons over resamples of registration groups.

Run after run.py: ``python lbw_detection_track/whole_pregnancy/evaluate.py``.
Writes outputs/estimates.csv and outputs/comparisons.csv.
"""

from __future__ import annotations

import warnings

import history
import numpy as np
import pandas as pd
from features import load_raw
from run_experiments import ids
from scoring import calibration_slope, interval, resamples
from sklearn.metrics import average_precision_score, roc_auc_score

OUT = history.HERE / "outputs"
SEED, RESAMPLES = 20261111, 2000
COMPARISONS = (
    ("primary", "H logistic", "B logistic", "roc_auc"),
    ("secondary", "H logistic", "C logistic", "roc_auc"),
    ("secondary", "C logistic", "B logistic", "roc_auc"),
    ("secondary", "H boosting", "B logistic", "roc_auc"),
    ("secondary", "H logistic", "B logistic", "sensitivity_90"),
    ("secondary", "H boosting", "B logistic", "sensitivity_90"),
    ("secondary", "C logistic", "B logistic", "sensitivity_90"),
)


def pooled(predictions: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
    """One row per record; columns ``<set> <method> <p|flag_75|flag_90>``."""
    wide = predictions.pivot_table(
        index="record_id", columns=["set", "method"], values=["p", "flag_75", "flag_90"],
        aggfunc="mean",
    )  # fmt: skip
    wide.columns = [f"{s} {m} {v}" for v, s, m in wide.columns]
    return wide.assign(lbw=y.loc[wide.index].to_numpy())


def _flags(y: np.ndarray, f: np.ndarray, rule: str) -> dict[str, float]:
    tp, fp = (f * y).sum(), (f * (1 - y)).sum()
    fn, tn = y.sum() - tp, (1 - y).sum() - fp
    return {
        f"sensitivity_{rule}": tp / (tp + fn), f"specificity_{rule}": tn / (tn + fp),
        f"ppv_{rule}": tp / max(tp + fp, 1e-9), f"npv_{rule}": tn / max(tn + fn, 1e-9),
    }  # fmt: skip


def measure_all(frame: pd.DataFrame) -> dict[tuple[str, str], float]:
    y = frame["lbw"].to_numpy()
    configs = sorted({c.rsplit(" ", 1)[0] for c in frame.columns if c.endswith(" p")})
    out = {}
    for c in configs:
        p = frame[f"{c} p"].to_numpy()
        values = {
            "roc_auc": roc_auc_score(y, p),
            "pr_auc": average_precision_score(y, p),
            "calibration_slope": calibration_slope(y, p),
        }
        for rule in ("75", "90"):
            values |= _flags(y, frame[f"{c} flag_{rule}"].to_numpy(), rule)
        out |= {(c, k): v for k, v in values.items()}
    return out


def main() -> None:
    predictions = pd.read_parquet(OUT / "predictions.parquet")
    frame = history.primary_frame(load_raw(ids("development_ids")))
    table = pooled(predictions, frame["lbw"])
    groups = frame.loc[table.index, "group"].to_numpy()
    point = measure_all(table)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        draws = pd.DataFrame(
            [measure_all(table.iloc[i]) for i in resamples(groups, RESAMPLES, SEED)]
        )
    rows = []
    for key, value in point.items():
        low, high, _ = interval(draws[key].tolist())
        rows.append({"config": key[0], "measure": key[1], "estimate": value, "low": low,
                     "high": high})  # fmt: skip
    pd.DataFrame(rows).to_csv(OUT / "estimates.csv", index=False)
    rows = []
    for role, new, old, measure in COMPARISONS:
        diff = (draws[(new, measure)] - draws[(old, measure)]).to_numpy()
        low, high, _ = interval(diff.tolist())
        share = min((diff <= 0).mean(), (diff >= 0).mean())
        rows.append({"role": role, "config": new, "against": old, "measure": measure,
                     "difference": point[(new, measure)] - point[(old, measure)],
                     "low": low, "high": high, "p_value": min(1.0, 2 * share)})  # fmt: skip
    result = pd.DataFrame(rows)
    result.to_csv(OUT / "comparisons.csv", index=False)
    print(pd.DataFrame(point, index=[0]).T.unstack().round(3).to_string())
    print(result.round(4).to_string())


if __name__ == "__main__":
    main()
