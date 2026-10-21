"""Is missingness informative? Two views, on development records only.

1. Outcome rate by recording status. For each visit two measurement, the low
   birth weight rate among records with and without the value, each with a
   Wilson 95 percent interval, and the difference with a Newcombe hybrid score
   interval (Newcombe, 1998, method 10).
2. Predictive signal of the indicators. The same L2 logistic model is fitted
   with and without missingness indicators on sets B and C, on the same folds,
   and the paired difference is given a group bootstrap interval.

A difference in outcome rate shows association, not that missingness causes
anything: a value is often missing because of how a clinic works, and the
same clinics may differ in their outcomes.
"""

from __future__ import annotations

import math

import pandas as pd

from antenatal.audit.missingness import wilson_interval
from antenatal.data.dictionary import VISIT_MEASUREMENTS, visit_column
from antenatal.evaluation.comparisons import Comparison

WITH, WITHOUT = "logistic_l2", "logistic_l2_no_indicator"


def newcombe_difference(e1: int, n1: int, e2: int, n2: int) -> tuple[float, float, float]:
    """Difference of two proportions with the Newcombe hybrid score interval."""
    if n1 == 0 or n2 == 0:
        return (math.nan, math.nan, math.nan)
    p1, p2 = e1 / n1, e2 / n2
    l1, u1 = wilson_interval(e1, n1)
    l2, u2 = wilson_interval(e2, n2)
    d = p1 - p2
    return (
        d,
        d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2),
        d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2),
    )


def _group(frame: pd.DataFrame, mask: pd.Series) -> dict[str, float]:
    events, n = int(frame.loc[mask, "lbw"].sum()), int(mask.sum())
    low, high = wilson_interval(events, n)
    return {
        "n": n,
        "events": events,
        "rate": events / n if n else math.nan,
        "low": low,
        "high": high,
    }


def outcome_by_recording(development: pd.DataFrame) -> pd.DataFrame:
    """One row per visit two measurement: rates with and without the value recorded."""
    rows = []
    for item in VISIT_MEASUREMENTS:
        recorded = development[visit_column(item.name, 2)].notna()
        a, b = _group(development, recorded), _group(development, ~recorded)
        difference = newcombe_difference(b["events"], b["n"], a["events"], a["n"])
        rows.append(
            {
                "measurement": item.label,
                "recorded_n": a["n"],
                "recorded_events": a["events"],
                "recorded_rate": a["rate"],
                "recorded_low": a["low"],
                "recorded_high": a["high"],
                "missing_n": b["n"],
                "missing_events": b["events"],
                "missing_rate": b["rate"],
                "missing_low": b["low"],
                "missing_high": b["high"],
                "difference_missing_minus_recorded": difference[0],
                "difference_low": difference[1],
                "difference_high": difference[2],
                "note": "" if b["n"] else "Recorded for every record by the cohort rule",
            }
        )
    return pd.DataFrame(rows)


def indicator_comparisons() -> list[Comparison]:
    """Sets B and C with indicators against the same sets without them."""
    return [
        Comparison(f"Indicators added, set {s}", (WITH, s), (WITHOUT, s), "pr_auc", "extension")
        for s in ("B", "C")
    ]
