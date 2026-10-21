"""Decision curve data: net benefit of acting on the model against simple policies.

Net benefit at threshold t counts true positives minus false positives
weighted by t / (1 - t), per pregnancy (Vickers and Elkin, 2006). A model is
useful at t only when its net benefit exceeds both acting for everyone and
acting for no one (net benefit zero).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from antenatal.evaluation.metrics import net_benefit, net_benefit_treat_all

THRESHOLDS = np.round(np.arange(0.01, 0.301, 0.01), 2)


def decision_curve_table(
    y: np.ndarray, predictions: dict[str, np.ndarray], thresholds: np.ndarray = THRESHOLDS
) -> pd.DataFrame:
    """Net benefit per threshold for each named prediction and the two simple policies."""
    table = pd.DataFrame({"threshold": thresholds})
    for name, p in predictions.items():
        table[name] = net_benefit(y, p, thresholds)
    table["act for everyone"] = net_benefit_treat_all(y, thresholds)
    table["act for no one"] = 0.0
    return table
