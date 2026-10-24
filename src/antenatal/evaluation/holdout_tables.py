"""The tables of the single held out evaluation (``docs/holdout_protocol.md``).

Pure functions of labels, probabilities and registration groups: they never read the
partition themselves. ``HoldoutEvaluator.evaluate_once`` is the only caller with held
out records, and it calls them once.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from antenatal.artefact.classification import AtThreshold, ClassificationRule
from antenatal.config import PRIMARY, StudySpec
from antenatal.evaluation.bootstrap import GroupBootstrap
from antenatal.evaluation.metrics import ALL_METRICS, AveragePrecision, RocAuc
from antenatal.evaluation.power import detectable_difference
from antenatal.evaluation.retrieval import BUDGETS, RetrievalAtBudget

# (label, new model, old model, metric, role), as prespecified in the protocol.
COMPARISONS = (
    ("C over B (first visit added)", "C", "B", AveragePrecision(), "primary"),
    ("C over B (first visit added)", "C", "B", RocAuc(), "descriptive"),
    ("B over A (second visit added)", "B", "A", RocAuc(), "secondary"),
    ("B over A (second visit added)", "B", "A", AveragePrecision(), "descriptive"),
)


def model_metrics(y, probabilities: dict[str, np.ndarray], groups, spec: StudySpec = PRIMARY):
    """Every metric of every locked model, each with its own group bootstrap interval."""
    boot = GroupBootstrap(groups, spec.bootstrap_resamples, spec.seed)
    rows = []
    for name, p in probabilities.items():
        for metric in ALL_METRICS:
            interval = boot.single(y, p, metric)
            rows.append(
                {
                    "model": name,
                    "metric": metric.name,
                    "estimate": interval.estimate,
                    "ci_low": interval.low,
                    "ci_high": interval.high,
                }
            )
    return pd.DataFrame(rows)


def comparisons(y, probabilities: dict[str, np.ndarray], groups, spec: StudySpec = PRIMARY):
    """The primary and secondary paired comparisons on the held out records."""
    boot = GroupBootstrap(groups, spec.bootstrap_resamples, spec.seed)
    rows = []
    for label, new, old, metric, role in COMPARISONS:
        if new not in probabilities or old not in probabilities:
            continue
        interval = boot.paired_difference(y, probabilities[new], probabilities[old], metric)
        rows.append(
            {
                "comparison": label,
                "metric": metric.name,
                "role": role,
                "difference": interval.estimate,
                "ci_low": interval.low,
                "ci_high": interval.high,
                "bootstrap_se": interval.se,
                "detectable_difference": detectable_difference(interval.se),
                "p_value": interval.p_value,
            }
        )
    return pd.DataFrame(rows)


def classification(y, p, groups, rule: ClassificationRule, spec: StudySpec = PRIMARY):
    """The label at the threshold fixed on development records, and retrieval at each budget."""
    boot = GroupBootstrap(groups, spec.bootstrap_resamples, spec.seed)
    flagged, events = np.asarray(p) >= rule.threshold, np.asarray(y) == 1
    rows = [
        {
            "measure": "flagged as likely",
            "estimate": int(flagged.sum()),
            "ci_low": None,
            "ci_high": None,
            "detail": f"threshold {rule.threshold:.4f}, events {int(events.sum())}",
        }
    ]
    for kind in ("sensitivity", "specificity", "ppv", "npv"):
        interval = boot.single(y, p, AtThreshold(rule.threshold, kind))
        rows.append(
            {
                "measure": kind,
                "estimate": interval.estimate,
                "ci_low": interval.low,
                "ci_high": interval.high,
                "detail": "at the fixed threshold",
            }
        )
    for budget in BUDGETS:
        interval = boot.single(y, p, RetrievalAtBudget(budget))
        rows.append(
            {
                "measure": f"retrieval in the top {round(budget * 100)} percent",
                "estimate": interval.estimate,
                "ci_low": interval.low,
                "ci_high": interval.high,
                "detail": f"random ranking gives {budget:.2f}",
            }
        )
    return pd.DataFrame(rows)
