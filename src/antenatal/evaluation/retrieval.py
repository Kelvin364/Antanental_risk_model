"""Retrospective retrieval within fixed ranking budgets (Research Question 3, Section 3.3.8.1).

Pregnancies are ranked by predicted probability. For a budget of k percent,
retrieval is the share of all low birth weight births that fall in the top k
percent of the ranking. Ranking at random retrieves k percent on average, so
that is the reference. This describes retrospective ranking only. It does
not show that earlier or more frequent contact would change any outcome.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from antenatal.config import PRIMARY, StudySpec
from antenatal.evaluation.bootstrap import GroupBootstrap
from antenatal.evaluation.metrics import MetricStrategy

BUDGETS = (0.10, 0.20, 0.30)


class RetrievalAtBudget(MetricStrategy):
    """Share of events among the top ``budget`` fraction of pregnancies by predicted probability."""

    def __init__(self, budget: float) -> None:
        self.budget = budget
        self.name = f"retrieval_top_{round(budget * 100)}"

    def compute(self, y: np.ndarray, p: np.ndarray) -> float:
        y = np.asarray(y)
        k = int(np.ceil(self.budget * len(y)))
        order = np.argsort(-np.asarray(p), kind="stable")
        return float(y[order[:k]].sum() / y.sum())


def retrieval_table(
    y: np.ndarray, p: np.ndarray, groups: np.ndarray, spec: StudySpec = PRIMARY, label: str = ""
) -> pd.DataFrame:
    """Retrieval at each budget with a group bootstrap interval, beside the random expectation."""
    bootstrap = GroupBootstrap(groups, spec.bootstrap_resamples, spec.seed)
    rows = []
    for budget in BUDGETS:
        metric = RetrievalAtBudget(budget)
        interval = bootstrap.single(y, p, metric)
        k = int(np.ceil(budget * len(y)))
        rows.append(
            {
                "model": label,
                "budget_percent": round(budget * 100),
                "pregnancies_in_budget": k,
                "events_found": int(np.round(interval.estimate * y.sum())),
                "events_total": int(y.sum()),
                "retrieval": interval.estimate,
                "ci_low": interval.low,
                "ci_high": interval.high,
                "random_expectation": budget,
                "ratio_to_random": interval.estimate / budget,
                "n": len(y),
            }
        )
    return pd.DataFrame(rows)
