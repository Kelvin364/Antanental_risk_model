"""Protocol Section 6: measures of every strategy and score on one (possibly resampled) frame."""

from __future__ import annotations

import _paths  # noqa: F401  (import path to the fusion and track code)
import numpy as np
import pandas as pd
from measures import flagging
from rules import TARGETS
from scipy.optimize import brentq
from scoring import calibration_slope
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

LATE_RULES = ("75", *TARGETS)
STRATEGIES = ["flag_base", "alone_75", "seq_75"] + [
    f"{kind}_{k}" for k in TARGETS for kind in ("alone", "seq", "upd", "match")
]
ADDED = ["seq_75"] + [f"{kind}_{k}" for k in TARGETS for kind in ("seq", "upd", "match")]
SCORES = {"all": ("p1",), "reassessed": ("p1", "p2", "pu"), "cleared": ("p1", "p2", "pu")}


def pooled(predictions: pd.DataFrame, served: pd.DataFrame) -> pd.DataFrame:
    """One row per record: mean score and share of repeats flagged."""
    flags = [c for c in predictions if predictions[c].dtype == bool]
    frame = predictions.groupby("record_id")[["p1", "p2", "pu", *flags]].mean()
    frame["lbw"] = served.loc[frame.index, "lbw"].to_numpy()
    frame["preterm"] = served.loc[frame.index, "preterm_labour"].to_numpy().astype(bool)
    frame["reassessed"] = frame["p2"].notna()
    frame["cleared"] = frame["reassessed"] & (frame["flag_base"] < 0.5)
    return frame


def calibration_intercept(y: np.ndarray, p: np.ndarray) -> float:
    """Shift in log odds that makes the mean prediction equal the observed rate."""
    lp = np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))
    return float(brentq(lambda a: (y - 1 / (1 + np.exp(-(a + lp)))).sum(), -10, 10))


def ranking(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    return {
        "records": len(y),
        "cases": float(y.sum()),
        "roc_auc": roc_auc_score(y, p),
        "pr_auc": average_precision_score(y, p),
        "base_rate": float(y.mean()),
        "brier": brier_score_loss(y, p),
        "calibration_slope": calibration_slope(y, p),
        "calibration_intercept": calibration_intercept(y, p),
        "observed_to_expected": float(y.sum() / p.sum()),
    }


def _flag_measures(y: np.ndarray, f: np.ndarray) -> dict[str, float]:
    values = flagging(y, f)
    return values | {"records": len(y), "flagged_per_1000": 1000 * values["flagged"] / len(y)}


def _added(point: dict, population: str, strategy: str, n: int) -> dict[tuple, float]:
    """Extra flags, cases and false alarms over the baseline, and their ratio."""
    new, base = (population, strategy), (population, "flag_base")
    cases = point[(*new, "cases_found")] - point[(*base, "cases_found")]
    alarms = point[(*new, "false_alarms")] - point[(*base, "false_alarms")]
    ratio = alarms / cases if cases > 0 else float("nan")
    return {
        (*new, "extra_cases"): cases,
        (*new, "extra_false_alarms"): alarms,
        (*new, "extra_flags_per_1000"): 1000 * (cases + alarms) / n,
        (*new, "extra_cases_per_1000"): 1000 * cases / n,
        (*new, "extra_false_alarms_per_1000"): 1000 * alarms / n,
        (*new, "false_alarms_per_extra_case"): ratio,
    }


def _overlap(part: pd.DataFrame, k: str) -> dict[tuple, float]:
    """Cases and false alarms flagged by both models, by one only, or by neither."""
    out = {}
    for label, mask in (("cases", part["lbw"] == 1), ("false_alarms", part["lbw"] == 0)):
        rows = part[mask]
        both, base = rows[f"both_{k}"].sum(), rows["flag_base"].sum()
        late = rows[f"alone_{k}"].sum() - both
        out |= {
            ("all", f"overlap_{k}", f"{label}_both"): both,
            ("all", f"overlap_{k}", f"{label}_baseline_only"): base - both,
            ("all", f"overlap_{k}", f"{label}_late_only"): late,
            ("all", f"overlap_{k}", f"{label}_neither"): len(rows) - base - late,
        }
    return out


def _population(frame: pd.DataFrame, name: str) -> pd.DataFrame:
    return frame if name == "all" else frame[frame[name]]


def measure_all(frame: pd.DataFrame) -> dict[tuple, float]:
    out = {}
    for population, scores in SCORES.items():
        part = _population(frame, population)
        y = part["lbw"].to_numpy()
        for score in scores:
            values = ranking(y, part[score].to_numpy())
            out |= {(population, score, k): v for k, v in values.items()}
        if population == "cleared":
            continue
        for strategy in STRATEGIES:
            values = _flag_measures(y, part[strategy].to_numpy())
            out |= {(population, strategy, k): v for k, v in values.items()}
        for strategy in ADDED:
            out |= _added(out, population, strategy, len(part))
    for k in LATE_RULES:
        out |= _overlap(frame, k)
    base = ("all", "flag_base")
    out[(*base, "false_alarms_per_case_found")] = (
        out[(*base, "false_alarms")] / out[(*base, "cases_found")]
    )
    return out
