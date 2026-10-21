"""Missingness of visit measurements and how it relates to time and outcome.

These summaries use the outcome, so they take development records only. The
held out partition is never passed to them.
"""

from __future__ import annotations

import math

import pandas as pd

from antenatal.data.dictionary import VISIT_MEASUREMENTS, VISITS, visit_column

Z_95 = 1.959963984540054


def wilson_interval(events: int, total: int, z: float = Z_95) -> tuple[float, float]:
    """Wilson score interval for a proportion, returned as (low, high)."""
    if total == 0:
        return (math.nan, math.nan)
    p = events / total
    denominator = 1 + z**2 / total
    centre = (p + z**2 / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denominator
    return (centre - half, centre + half)


def missingness_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Percent missing for every measurement at each visit."""
    rows = []
    for item in VISIT_MEASUREMENTS:
        for visit in VISITS:
            column = visit_column(item.name, visit)
            rows.append(
                {
                    "measurement": item.name,
                    "visit": visit,
                    "n": len(frame),
                    "missing": int(frame[column].isna().sum()),
                    "percent_missing": round(frame[column].isna().mean() * 100, 1),
                }
            )
    return pd.DataFrame(rows)


def missingness_mechanism(
    development: pd.DataFrame, measurements: tuple[str, ...] = ("hb", "pulse"), deciles: int = 10
) -> pd.DataFrame:
    """Outcome rate with and without each visit two value, and presence over record order.

    If the low birth weight rate barely differs between records with and without
    a value, and presence changes with record order, missingness looks driven
    by clinic practice over time rather than by the outcome. That supports median
    imputation with a missingness indicator.
    """
    order = pd.qcut(development["record_id"].rank(method="first"), deciles, labels=False) + 1
    rows = []
    for name in measurements:
        present = development[visit_column(name, 2)].notna()
        by_decile = present.groupby(order).mean().mul(100).round(0).astype(int).tolist()
        for label, mask in (("value present", present), ("value missing", ~present)):
            events, total = int(development.loc[mask, "lbw"].sum()), int(mask.sum())
            low, high = wilson_interval(events, total)
            rows.append(
                {
                    "measurement": f"{name} at visit two",
                    "group": label,
                    "n": total,
                    "events": events,
                    "lbw_percent": round(100 * events / total, 2) if total else math.nan,
                    "ci_low_percent": round(100 * low, 2),
                    "ci_high_percent": round(100 * high, 2),
                    "percent_present_by_record_decile": by_decile,
                }
            )
    return pd.DataFrame(rows)
