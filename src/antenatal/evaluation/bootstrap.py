"""Paired group bootstrap of a difference between two sets of predictions.

Algorithm (Section 3.3.7). Out of fold predictions are first averaged per
pregnancy across the repeats, because fold level scores from repeated cross
validation are correlated and their spread is not a valid interval (Nadeau and
Bengio, 2003). The paired difference in a metric is then computed on the same
pregnancies, and whole registration groups are resampled with replacement
2,000 times. The 2.5th and 97.5th percentiles of the resampled differences
form the 95 percent interval; their standard deviation is the bootstrap
standard error used by the power calculation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from antenatal.evaluation.metrics import MetricStrategy


@dataclass(frozen=True)
class Interval:
    """A point estimate with a percentile interval and a bootstrap standard error."""

    estimate: float
    low: float
    high: float
    se: float
    resamples: int
    p_value: float = float("nan")

    @property
    def excludes_zero(self) -> bool:
        """True when the whole interval lies on one side of zero."""
        return self.low > 0 or self.high < 0

    def as_dict(self) -> dict[str, float]:
        """Fields as a dictionary for tables."""
        return asdict(self)


class GroupBootstrap:
    """Resamples whole groups of records with replacement, reproducibly from a seed."""

    def __init__(self, groups: np.ndarray, n_resamples: int, seed: int) -> None:
        codes, self._inverse = np.unique(np.asarray(groups), return_inverse=True)
        order = np.argsort(self._inverse, kind="stable")
        bounds = np.searchsorted(self._inverse[order], np.arange(len(codes) + 1))
        self._members = [order[bounds[i] : bounds[i + 1]] for i in range(len(codes))]
        self._n = n_resamples
        self._seed = seed

    def indices(self):
        """Yield one array of record positions per resample."""
        rng = np.random.default_rng(self._seed)
        n_groups = len(self._members)
        for _ in range(self._n):
            chosen = rng.integers(0, n_groups, n_groups)
            yield np.concatenate([self._members[g] for g in chosen])

    def _summarise(self, estimate: float, draws: list[float]) -> Interval:
        values = np.asarray(draws, dtype=float)
        values = values[~np.isnan(values)]
        low, high = np.percentile(values, [2.5, 97.5])
        # Two sided bootstrap p value for a difference: twice the smaller share of
        # resamples on either side of zero, capped at 1.
        p_value = min(1.0, 2 * min(float((values <= 0).mean()), float((values >= 0).mean())))
        return Interval(
            estimate, float(low), float(high), float(values.std(ddof=1)), len(values), p_value
        )

    def single(self, y: np.ndarray, p: np.ndarray, metric: MetricStrategy) -> Interval:
        """Interval for one metric of one set of predictions."""
        estimate = metric.compute(y, p)
        draws = [
            metric.compute(y[i], p[i]) if 0 < y[i].sum() < len(i) else np.nan
            for i in self.indices()
        ]
        return self._summarise(estimate, draws)

    def paired_difference(
        self, y: np.ndarray, p_new: np.ndarray, p_old: np.ndarray, metric: MetricStrategy
    ) -> Interval:
        """Interval for ``metric(p_new) - metric(p_old)`` on the same records."""
        estimate = metric.compute(y, p_new) - metric.compute(y, p_old)
        draws = []
        for i in self.indices():
            if not 0 < y[i].sum() < len(i):
                draws.append(np.nan)
                continue
            draws.append(metric.compute(y[i], p_new[i]) - metric.compute(y[i], p_old[i]))
        return self._summarise(estimate, draws)
