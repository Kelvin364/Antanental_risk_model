"""The pre specified comparisons of Table 1.1, each with its interval and power.

Primary: set C against set B on area under the precision recall curve.
Secondary: set B against set A on area under the ROC curve.
Supporting: each set against the constant prevalence baseline B0.
Both metrics are reported for every pair so the reader sees the whole picture,
and the ``role`` column marks which row answers which hypothesis.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from antenatal.config import PRIMARY, StudySpec
from antenatal.evaluation.bootstrap import GroupBootstrap
from antenatal.evaluation.metrics import AveragePrecision, MetricStrategy, RocAuc
from antenatal.evaluation.nested_cv import CVResults
from antenatal.evaluation.power import detectable_difference

BASELINE = ("baseline_prevalence", "A")


@dataclass(frozen=True)
class Comparison:
    """One paired comparison: (model, newer set) against (model, older set)."""

    label: str
    new: tuple[str, str]
    old: tuple[str, str]
    primary_metric: str
    role: str


def primary_comparisons(model: str) -> list[Comparison]:
    """The comparisons of Table 1.1 for one model family."""
    return [
        Comparison("C over B (first visit added)", (model, "C"), (model, "B"), "pr_auc", "primary"),
        Comparison(
            "B over A (second visit added)", (model, "B"), (model, "A"), "roc_auc", "secondary"
        ),
        Comparison(
            "C over A (both visits added)", (model, "C"), (model, "A"), "pr_auc", "supporting"
        ),
        Comparison(
            "A over B0 (registration over prevalence)",
            (model, "A"),
            BASELINE,
            "pr_auc",
            "supporting",
        ),
        Comparison("B over B0", (model, "B"), BASELINE, "pr_auc", "supporting"),
        Comparison("C over B0", (model, "C"), BASELINE, "pr_auc", "supporting"),
    ]


class ComparisonRunner:
    """Computes paired group bootstrap intervals for a list of comparisons."""

    METRICS: tuple[MetricStrategy, ...] = (AveragePrecision(), RocAuc())

    def __init__(self, results: CVResults, spec: StudySpec = PRIMARY) -> None:
        self._results = results
        self._bootstrap = GroupBootstrap(results.groups, spec.bootstrap_resamples, spec.seed)

    def run(self, comparisons: list[Comparison], analysis: str = "Primary") -> pd.DataFrame:
        """One row per comparison and metric."""
        y = self._results.y
        rows = []
        for comparison in comparisons:
            p_new = self._results.averaged(*comparison.new)
            p_old = self._results.averaged(*comparison.old)
            for metric in self.METRICS:
                interval = self._bootstrap.paired_difference(y, p_new, p_old, metric)
                rows.append(
                    {
                        "analysis": analysis,
                        "model": comparison.new[0],
                        "comparison": comparison.label,
                        "metric": metric.name,
                        "role": (
                            comparison.role
                            if metric.name == comparison.primary_metric
                            else "descriptive"
                        ),
                        "new_value": metric.compute(y, p_new),
                        "old_value": metric.compute(y, p_old),
                        "difference": interval.estimate,
                        "ci_low": interval.low,
                        "ci_high": interval.high,
                        "bootstrap_se": interval.se,
                        "detectable_difference": detectable_difference(interval.se),
                        "excludes_zero": interval.excludes_zero,
                        "p_value": interval.p_value,
                        "n": len(y),
                        "events": int(y.sum()),
                    }
                )
        return pd.DataFrame(rows)

    def performance(self, keys: list[tuple[str, str]]) -> pd.DataFrame:
        """Metric of each averaged prediction with its own group bootstrap interval."""
        y = self._results.y
        rows = []
        for model, feature_set in keys:
            p = self._results.averaged(model, feature_set)
            for metric in self.METRICS:
                interval = self._bootstrap.single(y, p, metric)
                rows.append(
                    {
                        "model": model,
                        "feature_set": feature_set,
                        "metric": metric.name,
                        "value": interval.estimate,
                        "ci_low": interval.low,
                        "ci_high": interval.high,
                        "n": len(y),
                        "events": int(y.sum()),
                    }
                )
        return pd.DataFrame(rows)
