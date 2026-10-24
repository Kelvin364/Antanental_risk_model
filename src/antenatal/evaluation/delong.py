"""DeLong's test for two correlated ROC AUCs on the same records (DeLong et al., 1988).

Reported as descriptive only. The test treats every record as independent, but
records that share a registration group are not, so its standard error is too
small when groups hold more than one record. The paired group bootstrap is the
test of record; this one is shown beside it because readers expect it.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import NormalDist

import numpy as np
from scipy.stats import rankdata


@dataclass(frozen=True)
class DeLongResult:
    """Difference of two ROC AUCs with its DeLong standard error and two sided p value."""

    auc_new: float
    auc_old: float
    difference: float
    se: float
    p_value: float


def _components(y: np.ndarray, p: np.ndarray) -> tuple[float, np.ndarray, np.ndarray]:
    """The AUC and the structural components of events and non events (midranks)."""
    events, others = p[y == 1], p[y == 0]
    m, n = len(events), len(others)
    pooled = rankdata(np.concatenate([events, others]))
    v10 = (pooled[:m] - rankdata(events)) / n
    v01 = 1 - (pooled[m:] - rankdata(others)) / m
    return float(v10.mean()), v10, v01


def delong_paired(y, p_new, p_old) -> DeLongResult:
    """DeLong's test of ``AUC(p_new) - AUC(p_old)`` on the same records."""
    y = np.asarray(y).astype(int)
    auc_new, v10_new, v01_new = _components(y, np.asarray(p_new, dtype=float))
    auc_old, v10_old, v01_old = _components(y, np.asarray(p_old, dtype=float))
    s10 = np.cov(np.vstack([v10_new, v10_old]))
    s01 = np.cov(np.vstack([v01_new, v01_old]))
    m, n = len(v10_new), len(v01_new)
    variance = (s10[0, 0] + s10[1, 1] - 2 * s10[0, 1]) / m + (
        s01[0, 0] + s01[1, 1] - 2 * s01[0, 1]
    ) / n
    difference = auc_new - auc_old
    se = float(np.sqrt(max(variance, 0.0)))
    p_value = 1.0 if se == 0 else 2 * (1 - NormalDist().cdf(abs(difference) / se))
    return DeLongResult(auc_new, auc_old, difference, se, float(p_value))
