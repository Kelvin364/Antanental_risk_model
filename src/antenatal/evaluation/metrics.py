"""Evaluation metrics of Table 3.7, as interchangeable strategies.

Each ``MetricStrategy`` subclass computes one number from outcomes and
predicted probabilities. The cross validation runner and the bootstrap loop
over a list of strategies and never branch on a metric's name.

Area under the precision recall curve is average precision: the sum over
thresholds of precision weighted by the increase in recall, with no
interpolation between operating points (Davis and Goadrich, 2006). Its no
skill value equals the prevalence. Calibration slope and intercept follow the
logistic recalibration framework (Van Calster et al., 2019).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
from scipy.special import expit
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

EPS = 1e-12


def logit(p: np.ndarray) -> np.ndarray:
    """Log odds of probabilities clipped away from 0 and 1."""
    p = np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS)
    return np.log(p / (1 - p))


def sigmoid(x: np.ndarray) -> np.ndarray:
    """Inverse of ``logit``, computed without overflow."""
    return expit(np.asarray(x, dtype=float))


def _fit_logistic(
    y: np.ndarray, design: np.ndarray, offset: np.ndarray, steps: int = 50
) -> np.ndarray:
    """Unpenalised logistic regression by Newton steps; returns the coefficients."""
    beta = np.zeros(design.shape[1])
    for _ in range(steps):
        p = sigmoid(design @ beta + offset)
        gradient = design.T @ (y - p)
        hessian = design.T @ (design * (p * (1 - p))[:, None])
        step = np.linalg.solve(hessian + 1e-10 * np.eye(len(beta)), gradient)
        beta = beta + step
        if np.max(np.abs(step)) < 1e-10:
            break
    return beta


def calibration_slope_intercept(y: np.ndarray, p: np.ndarray) -> tuple[float, float]:
    """Calibration slope and calibration in the large.

    The slope is the coefficient of the logit of ``p`` in a logistic model of
    ``y``; one is ideal and below one means predictions are too extreme. The
    intercept is estimated with the slope fixed at one (the logit as an offset);
    zero is ideal.
    """
    y = np.asarray(y, dtype=float)
    lp = logit(p)
    ones = np.ones((len(y), 1))
    slope = _fit_logistic(y, np.column_stack([ones, lp]), np.zeros(len(y)))[1]
    intercept = _fit_logistic(y, ones, lp)[0]
    return float(slope), float(intercept)


def net_benefit(y: np.ndarray, p: np.ndarray, thresholds: np.ndarray) -> np.ndarray:
    """Net benefit of acting on ``p >= t`` at each threshold t (Vickers and Elkin, 2006)."""
    y = np.asarray(y)
    p = np.asarray(p)
    n = len(y)
    out = []
    for t in np.asarray(thresholds, dtype=float):
        act = p >= t
        tp = np.sum(act & (y == 1))
        fp = np.sum(act & (y == 0))
        out.append(tp / n - fp / n * t / (1 - t))
    return np.array(out)


def net_benefit_treat_all(y: np.ndarray, thresholds: np.ndarray) -> np.ndarray:
    """Net benefit of acting for every pregnancy."""
    prevalence = float(np.mean(y))
    t = np.asarray(thresholds, dtype=float)
    return prevalence - (1 - prevalence) * t / (1 - t)


class MetricStrategy(ABC):
    """One evaluation metric."""

    name: str = ""
    higher_is_better: bool = True

    @abstractmethod
    def compute(self, y: np.ndarray, p: np.ndarray) -> float:
        """Return the metric for outcomes ``y`` and probabilities ``p``."""


class AveragePrecision(MetricStrategy):
    """Area under the precision recall curve, computed as average precision."""

    name = "pr_auc"

    def compute(self, y: np.ndarray, p: np.ndarray) -> float:
        return float(average_precision_score(y, p))


class RocAuc(MetricStrategy):
    """Area under the receiver operating characteristic curve."""

    name = "roc_auc"

    def compute(self, y: np.ndarray, p: np.ndarray) -> float:
        return float(roc_auc_score(y, p))


class Brier(MetricStrategy):
    """Mean squared difference between probability and outcome."""

    name = "brier"
    higher_is_better = False

    def compute(self, y: np.ndarray, p: np.ndarray) -> float:
        return float(brier_score_loss(y, p))


class CalibrationSlope(MetricStrategy):
    """Slope of the logistic recalibration model."""

    name = "calibration_slope"

    def compute(self, y: np.ndarray, p: np.ndarray) -> float:
        return calibration_slope_intercept(y, p)[0]


class CalibrationIntercept(MetricStrategy):
    """Calibration in the large."""

    name = "calibration_intercept"

    def compute(self, y: np.ndarray, p: np.ndarray) -> float:
        return calibration_slope_intercept(y, p)[1]


def average_precision(y: np.ndarray, p: np.ndarray) -> float:
    """Average precision with no interpolation."""
    return AveragePrecision().compute(y, p)


def roc_auc(y: np.ndarray, p: np.ndarray) -> float:
    """Area under the ROC curve."""
    return RocAuc().compute(y, p)


def brier(y: np.ndarray, p: np.ndarray) -> float:
    """Brier score."""
    return Brier().compute(y, p)


ALL_METRICS: tuple[MetricStrategy, ...] = (
    AveragePrecision(),
    RocAuc(),
    Brier(),
    CalibrationSlope(),
    CalibrationIntercept(),
)

METRICS_BY_NAME: dict[str, MetricStrategy] = {m.name: m for m in ALL_METRICS}


def score_all(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    """Every metric of ``ALL_METRICS`` as a dictionary."""
    return {m.name: m.compute(y, p) for m in ALL_METRICS}
