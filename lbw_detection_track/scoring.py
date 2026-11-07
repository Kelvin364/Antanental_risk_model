"""Measures and group bootstrap intervals used on development and test predictions."""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

TARGET_SENSITIVITY = 0.75


def threshold_for(y: np.ndarray, p: np.ndarray, sensitivity: float = TARGET_SENSITIVITY) -> float:
    """The highest probability at which at least ``sensitivity`` of events are flagged."""
    events = np.sort(p[y == 1])[::-1]
    return float(events[int(np.ceil(sensitivity * len(events))) - 1])


def counts(y: np.ndarray, p: np.ndarray, threshold: float) -> dict[str, int]:
    flagged = p >= threshold
    return {
        "tp": int((flagged & (y == 1)).sum()),
        "fp": int((flagged & (y == 0)).sum()),
        "fn": int((~flagged & (y == 1)).sum()),
        "tn": int((~flagged & (y == 0)).sum()),
    }


def at_threshold(y: np.ndarray, p: np.ndarray, threshold: float) -> dict[str, float]:
    c = counts(y, p, threshold)
    return {
        "sensitivity": c["tp"] / max(c["tp"] + c["fn"], 1),
        "specificity": c["tn"] / max(c["tn"] + c["fp"], 1),
        "ppv": c["tp"] / max(c["tp"] + c["fp"], 1),
        "npv": c["tn"] / max(c["tn"] + c["fn"], 1),
    }


def specificity_at_target(y: np.ndarray, p: np.ndarray) -> float:
    return at_threshold(y, p, threshold_for(y, p))["specificity"]


def calibration_slope(y: np.ndarray, p: np.ndarray) -> float:
    clipped = np.clip(p, 1e-6, 1 - 1e-6)
    logit = np.log(clipped / (1 - clipped))
    if np.ptp(logit) == 0:
        return float("nan")
    fit = LogisticRegression(C=1e9, max_iter=1000).fit(logit.reshape(-1, 1), y)
    return float(fit.coef_[0, 0])


def summary(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    return {
        "roc_auc": roc_auc_score(y, p),
        "pr_auc": average_precision_score(y, p),
        "brier": brier_score_loss(y, p),
        "calibration_slope": calibration_slope(y, p),
        "specificity_at_75": specificity_at_target(y, p),
    }


def resamples(groups: np.ndarray, n: int, seed: int):
    """Yield record positions for each resample of whole registration groups."""
    codes, inverse = np.unique(groups, return_inverse=True)
    order = np.argsort(inverse, kind="stable")
    bounds = np.searchsorted(inverse[order], np.arange(len(codes) + 1))
    members = [order[bounds[i] : bounds[i + 1]] for i in range(len(codes))]
    rng = np.random.default_rng(seed)
    for _ in range(n):
        yield np.concatenate([members[g] for g in rng.integers(0, len(codes), len(codes))])


def interval(values: list[float]) -> tuple[float, float, float]:
    """Percentile 95 percent interval and bootstrap standard error."""
    data = np.asarray(values, dtype=float)
    data = data[~np.isnan(data)]
    low, high = np.percentile(data, [2.5, 97.5])
    return float(low), float(high), float(data.std(ddof=1))
