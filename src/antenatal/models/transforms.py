"""Prespecified nonlinear terms for experiment 2.4 (``configs/experiment_plan.yaml``).

Algorithm. A restricted cubic spline with three knots adds one nonlinear term per
variable, linear beyond the outer knots (Harrell's form). The knots sit at the
10th, 50th and 90th percentiles of the variable in the training fold, learned in
``fit`` so no test fold value shapes them. Two products add the prespecified
interactions. Missing inputs stay missing, for the imputer that follows.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

SPLINE_TERMS = ("age", "registration_weight", "weight_v2", "sbp_v2")
INTERACTIONS = (("age", "gravidity"), ("sbp_v2", "ga_v2"))
KNOT_PERCENTILES = (10, 50, 90)


def _cube(values: np.ndarray) -> np.ndarray:
    return np.where(values > 0, values, 0.0) ** 3


def spline_term(x: np.ndarray, knots: tuple[float, float, float]) -> np.ndarray:
    """The single nonlinear basis term of a three knot restricted cubic spline."""
    k1, k2, k3 = knots
    term = (
        _cube(x - k1)
        - _cube(x - k2) * (k3 - k1) / (k3 - k2)
        + _cube(x - k3) * (k2 - k1) / (k3 - k2)
    )
    return term / (k3 - k1) ** 2


class SplineInteractions(BaseEstimator, TransformerMixin):
    """Adds one spline term per variable and the prespecified interaction products."""

    def __init__(self, splines=SPLINE_TERMS, interactions=INTERACTIONS) -> None:
        self.splines = splines
        self.interactions = interactions

    def fit(self, x: pd.DataFrame, y=None) -> SplineInteractions:
        self.knots_ = {
            name: tuple(float(v) for v in np.nanpercentile(x[name], KNOT_PERCENTILES))
            for name in self.splines
        }
        self.feature_names_in_ = np.asarray(x.columns)
        return self

    def transform(self, x: pd.DataFrame) -> pd.DataFrame:
        out = x.copy()
        for name, knots in self.knots_.items():
            out[f"{name}_rcs"] = spline_term(x[name].to_numpy(dtype=float), knots)
        for left, right in self.interactions:
            out[f"{left}_x_{right}"] = x[left] * x[right]
        return out
