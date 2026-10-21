"""Calibration curve data: predicted against observed risk in equal sized groups."""

from __future__ import annotations

import numpy as np
import pandas as pd

from antenatal.audit.missingness import wilson_interval


def calibration_table(y: np.ndarray, p: np.ndarray, bins: int = 8) -> pd.DataFrame:
    """Mean predicted and observed rate in ``bins`` groups of equal size by predicted risk.

    Each observed rate carries a Wilson 95 percent interval, so a reader can see
    how much of the scatter around the diagonal is sampling noise.
    """
    order = np.argsort(p, kind="stable")
    rows = []
    for chunk in np.array_split(order, bins):
        events, n = int(np.sum(y[chunk])), len(chunk)
        low, high = wilson_interval(events, n)
        rows.append(
            {
                "mean_predicted": float(np.mean(p[chunk])),
                "observed": events / n,
                "observed_low": low,
                "observed_high": high,
                "n": n,
                "events": events,
            }
        )
    return pd.DataFrame(rows)
