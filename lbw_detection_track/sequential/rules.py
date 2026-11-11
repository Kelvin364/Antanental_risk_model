"""Protocol Section 4: every threshold and the updated late score, learnt in training only.

``learn`` sees inner out of fold scores of outer training records and nothing else.
``flags`` applies the learnt rules to outer test records.
"""

from __future__ import annotations

import _paths  # noqa: F401  (import path to the fusion and track code)
import numpy as np
from nested import logit, top_share
from scoring import threshold_for
from sklearn.linear_model import LogisticRegression

TARGETS = {"95": 0.95, "90": 0.90, "85": 0.85, "80": 0.80}
PRIMARY = "90"


def _inputs(p1: np.ndarray, p2: np.ndarray) -> np.ndarray:
    return np.column_stack([logit(p1), logit(p2)])


def fit_updated(y: np.ndarray, p1: np.ndarray, p2: np.ndarray) -> LogisticRegression:
    """Log odds of both scores, reassessed records only, no term for attendance."""
    seen = ~np.isnan(p2)
    return LogisticRegression(C=1e9, max_iter=5000).fit(_inputs(p1[seen], p2[seen]), y[seen])


def updated(model: LogisticRegression, p1: np.ndarray, p2: np.ndarray) -> np.ndarray:
    out, seen = np.full(len(p1), np.nan), ~np.isnan(p2)
    if seen.any():
        out[seen] = model.predict_proba(_inputs(p1[seen], p2[seen]))[:, 1]
    return out


def _at_specificity(score: np.ndarray, controls: np.ndarray, target: float) -> float:
    """The score that flags ``1 - target`` of the given non cases."""
    return top_share(score[controls], 1 - target)


def learn(y: np.ndarray, p1: np.ndarray, p2: np.ndarray):
    """Thresholds of protocol Section 4 from inner scores of training records."""
    t1 = top_share(p1)
    seen = ~np.isnan(p2)
    cleared = seen & (p1 < t1)
    controls = cleared & (y == 0)
    model = fit_updated(y, p1, p2)
    pu = updated(model, p1, p2)
    t = {"t1": t1, "t75": threshold_for(y[seen], p2[seen])}
    for k, target in TARGETS.items():
        t[f"late_{k}"] = _at_specificity(p2, controls, target)
        t[f"upd_{k}"] = _at_specificity(pu, controls, target)
        share = float(((p1 >= t1) | (cleared & (p2 >= t[f"late_{k}"]))).mean())
        t[f"match_{k}"] = top_share(p1, share)
        t[f"share_{k}"] = share
    return model, t


def flags(p1: np.ndarray, p2: np.ndarray, pu: np.ndarray, t: dict) -> dict[str, np.ndarray]:
    """Every strategy's flags. A missing late score never flags."""
    seen = ~np.isnan(p2)
    base = p1 >= t["t1"]
    late = seen & (np.nan_to_num(p2, nan=-1.0) >= t["t75"])
    out = {"flag_base": base, "alone_75": late, "seq_75": base | late}
    for k in TARGETS:
        alone = seen & (np.nan_to_num(p2, nan=-1.0) >= t[f"late_{k}"])
        upd = seen & (np.nan_to_num(pu, nan=-1.0) >= t[f"upd_{k}"])
        out |= {
            f"alone_{k}": alone,
            f"seq_{k}": base | alone,
            f"upd_{k}": base | upd,
            f"match_{k}": p1 >= t[f"match_{k}"],
        }
    for k in ("75", *TARGETS):
        out[f"both_{k}"] = base & out[f"alone_{k}"]
    return out
