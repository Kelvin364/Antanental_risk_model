"""Protocol Sections 4 and 5: measures, paired group bootstrap intervals and comparisons."""

from __future__ import annotations

import frames  # noqa: F401  (puts the track folder on the import path)
import numpy as np
import pandas as pd
from scoring import calibration_slope, interval, resamples
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

RESAMPLES = 2000
SCORES = {"1 served": "p1", "2 week 36": "p2", "4 stacked": "p4", "4b average": "p_avg"}
FLAGS = {
    "1 served": "flag1", "2 week 36": "flag2", "3 two checks": "flag3",
    "4 stacked, 20 percent flagged": "flag4_20", "4 stacked, 75 percent target": "flag4_75",
    "4b average": "flag_avg",
}  # fmt: skip
POPULATIONS = ("all 3,126", "week 36 visit")
COMPARISONS = (
    ("primary", "all 3,126", "4 stacked", "1 served", "pr_auc"),
    ("secondary", "all 3,126", "4 stacked", "1 served", "roc_auc"),
    ("secondary", "all 3,126", "4 stacked, 20 percent flagged", "1 served", "sensitivity"),
    ("secondary", "all 3,126", "3 two checks", "1 served", "sensitivity"),
    ("secondary", "all 3,126", "3 two checks", "1 served", "specificity"),
    ("descriptive", "all 3,126", "3 two checks", "1 served", "false_alarms"),
    ("descriptive", "all 3,126", "3 two checks", "1 served", "cases_found"),
    ("exploratory", "all 3,126", "4b average", "1 served", "pr_auc"),
    ("exploratory", "all 3,126", "4 stacked", "1 served", "calibration_slope"),
    ("exploratory", "week 36 visit", "2 week 36", "1 served", "roc_auc"),
    ("exploratory", "week 36 visit", "4 stacked", "1 served", "roc_auc"),
    ("exploratory", "week 36 visit", "2 week 36", "1 served", "pr_auc"),
)


def pooled(predictions: pd.DataFrame, outcome: pd.Series) -> pd.DataFrame:
    """One row per record: mean score and share of repeats flagged."""
    columns = list(SCORES.values()) + list(FLAGS.values())
    frame = predictions.groupby("record_id")[columns].mean()
    frame["lbw"] = outcome.loc[frame.index].to_numpy()
    frame["has_two"] = frame["p2"].notna()
    return frame


def ranking(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    return {
        "roc_auc": roc_auc_score(y, p),
        "pr_auc": average_precision_score(y, p),
        "base_rate": float(y.mean()),
        "brier": brier_score_loss(y, p),
        "calibration_slope": calibration_slope(y, p),
    }


def flagging(y: np.ndarray, f: np.ndarray) -> dict[str, float]:
    tp, fp = float((f * y).sum()), float((f * (1 - y)).sum())
    fn, tn = float(y.sum()) - tp, float((1 - y).sum()) - fp
    return {
        "cases_found": tp, "false_alarms": fp, "cases_missed": fn, "correct_clear": tn,
        "flagged": tp + fp, "sensitivity": tp / (tp + fn), "specificity": tn / (tn + fp),
        "ppv": tp / max(tp + fp, 1e-9), "npv": tn / max(tn + fn, 1e-9),
    }  # fmt: skip


def measure_all(frame: pd.DataFrame, slopes: bool = True) -> dict[tuple, float]:
    """Every option, population and measure, for one (possibly resampled) frame."""
    out = {}
    for population in POPULATIONS:
        part = frame if population == POPULATIONS[0] else frame[frame["has_two"]]
        y = part["lbw"].to_numpy()
        for option, column in SCORES.items():
            if column == "p2" and population == POPULATIONS[0]:
                continue
            values = ranking(y, part[column].to_numpy())
            if not slopes:
                values.pop("calibration_slope")
            out |= {(population, option, k): v for k, v in values.items()}
        for option, column in FLAGS.items():
            values = flagging(y, part[column].to_numpy())
            out |= {(population, option, k): v for k, v in values.items()}
    return out


def bootstrap(frame: pd.DataFrame, groups: np.ndarray, seed: int) -> pd.DataFrame:
    """Paired resamples of whole registration groups; every option sees the same records."""
    rows = []
    for picks in resamples(groups, RESAMPLES, seed):
        sample = frame.iloc[picks]
        if 0 < sample.loc[sample["has_two"], "lbw"].sum() < sample["has_two"].sum():
            rows.append(measure_all(sample))
    return pd.DataFrame(rows)


def estimates(frame: pd.DataFrame, draws: pd.DataFrame) -> pd.DataFrame:
    point = measure_all(frame)
    rows = []
    for key, value in point.items():
        low, high, se = interval(draws[key].tolist())
        rows.append(dict(zip(("population", "option", "measure"), key, strict=True)))
        rows[-1] |= {"estimate": value, "low": low, "high": high, "se": se}
    return pd.DataFrame(rows)


def comparisons(frame: pd.DataFrame, draws: pd.DataFrame) -> pd.DataFrame:
    point, rows = measure_all(frame), []
    for role, population, new, old, measure in COMPARISONS:
        a, b = (population, new, measure), (population, old, measure)
        diff = (draws[a] - draws[b]).dropna().to_numpy()
        low, high, se = interval(diff.tolist())
        share = min((diff <= 0).mean(), (diff >= 0).mean())
        rows.append(
            {
                "role": role, "population": population, "option": new, "against": old,
                "measure": measure, "difference": point[a] - point[b], "low": low,
                "high": high, "se": se, "p_value": min(1.0, 2 * share), "resamples": len(diff),
            }
        )  # fmt: skip
    return pd.DataFrame(rows)
