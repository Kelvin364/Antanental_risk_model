"""Subgroup performance by age band and parity (Table 3.7).

A stratum is reported only when it holds at least 30 events, as the proposal
specifies; below that, the row states that it is not reported and why.
Intervals are group bootstraps within the stratum. Parity comes from the
recorded prior deliveries, which the data audit found inconsistent with the
number of pregnancies in many records, so the parity strata are read with
that caution.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from antenatal.config import PRIMARY, StudySpec
from antenatal.evaluation.bootstrap import GroupBootstrap
from antenatal.evaluation.metrics import AveragePrecision, RocAuc
from antenatal.evaluation.nested_cv import CVResults

MIN_EVENTS = 30
MODEL = "logistic_l2"


def strata(development: pd.DataFrame) -> dict[str, pd.Series]:
    """Named boolean masks over the development records."""
    age = development["age"]
    deliveries = development["prior_deliveries"]
    return {
        "Age under 20": age < 20,
        "Age 20 to 34": age.between(20, 34),
        "Age 35 or over": age >= 35,
        "Age missing": age.isna(),
        "No prior delivery": deliveries == 0,
        "One or more prior deliveries": deliveries >= 1,
    }


def subgroup_table(results: CVResults, spec: StudySpec = PRIMARY) -> pd.DataFrame:
    """Performance of sets B and C and their difference within each stratum."""
    y, groups = results.y, results.groups
    p_b, p_c = results.averaged(MODEL, "B"), results.averaged(MODEL, "C")
    rows = []
    for name, mask in strata(results.development).items():
        mask = mask.to_numpy()
        events = int(y[mask].sum())
        row = {"stratum": name, "n": int(mask.sum()), "events": events}
        if events < MIN_EVENTS:
            rows.append({**row, "reported": False, "reason": f"Fewer than {MIN_EVENTS} events"})
            continue
        bootstrap = GroupBootstrap(groups[mask], spec.bootstrap_resamples, spec.seed)
        for metric in (AveragePrecision(), RocAuc()):
            c = bootstrap.single(y[mask], p_c[mask], metric)
            d = bootstrap.paired_difference(y[mask], p_c[mask], p_b[mask], metric)
            rows.append(
                {
                    **row,
                    "reported": True,
                    "reason": "",
                    "metric": metric.name,
                    "prevalence": float(np.mean(y[mask])),
                    "set_c": c.estimate,
                    "set_c_low": c.low,
                    "set_c_high": c.high,
                    "c_minus_b": d.estimate,
                    "c_minus_b_low": d.low,
                    "c_minus_b_high": d.high,
                }
            )
    return pd.DataFrame(rows)
