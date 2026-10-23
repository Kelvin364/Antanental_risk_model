"""The fixed classification threshold and how far each label can be trusted (decision D6).

The threshold is the predicted probability that marks the highest 20 percent of
the served model's out of fold predictions on development records, the middle
of the proposal's three ranking budgets. It is fixed once from development
data, never from the held out partition, and saved beside the artefact with
the artefact's checksum so it cannot be paired with another model.

Two kinds of confidence are reported. How often the label is right comes from
the sensitivity, specificity and predictive values at that fixed threshold,
each with a group bootstrap interval over the same out of fold predictions.
How settled the label is for one case comes from where the case's 95 percent
interval sits against the threshold: wholly above, wholly below, or across it.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from antenatal.config import PRIMARY, StudySpec
from antenatal.evaluation.bootstrap import GroupBootstrap
from antenatal.evaluation.metrics import MetricStrategy

CLASSIFICATION_FILE = "classification.json"
BUDGET = 0.20
LIKELY = "Likely low birth weight"
NOT_LIKELY = "Not likely low birth weight"
ABOVE, BELOW, ACROSS, UNAVAILABLE = (
    "interval_above",
    "interval_below",
    "interval_crosses",
    "interval_unavailable",
)
CERTAINTY_TEXT = {
    ABOVE: "The whole 95 percent interval lies above the threshold, so the label holds "
    "across the model's estimated uncertainty.",
    BELOW: "The whole 95 percent interval lies below the threshold, so the label holds "
    "across the model's estimated uncertainty.",
    ACROSS: "The 95 percent interval crosses the threshold, so the model cannot place this "
    "case firmly on either side. Treat the label as uncertain.",
    UNAVAILABLE: "This model gives no interval, so how settled the label is cannot be shown.",
}


class ClassificationMismatch(RuntimeError):
    """The saved threshold belongs to a different artefact than the one loaded."""


class AtThreshold(MetricStrategy):
    """Sensitivity, specificity or a predictive value at a fixed probability threshold."""

    def __init__(self, threshold: float, kind: str) -> None:
        self.threshold, self.kind, self.name = threshold, kind, kind

    def compute(self, y: np.ndarray, p: np.ndarray) -> float:
        flagged, events = np.asarray(p) >= self.threshold, np.asarray(y) == 1
        tp, fp = int((flagged & events).sum()), int((flagged & ~events).sum())
        fn, tn = int((~flagged & events).sum()), int((~flagged & ~events).sum())
        num, den = {
            "sensitivity": (tp, tp + fn),
            "specificity": (tn, tn + fp),
            "ppv": (tp, tp + fp),
            "npv": (tn, tn + fn),
        }[self.kind]
        return num / den if den else float("nan")


@dataclass(frozen=True)
class ClassificationRule:
    """The threshold, where it came from, and how often its label is right."""

    threshold: float
    budget_percent: int
    artefact_version: str
    artefact_sha256: str
    source: str
    n: int
    events: int
    counts: dict[str, int]
    performance: dict[str, dict[str, float]]

    def likely(self, probability: float) -> bool:
        """True when the probability reaches the threshold."""
        return probability >= self.threshold

    def save(self, model_dir: Path) -> Path:
        path = Path(model_dir) / CLASSIFICATION_FILE
        path.write_text(json.dumps(asdict(self), indent=2) + "\n")
        return path

    @classmethod
    def load(cls, model_dir: Path, artefact_sha256: str) -> ClassificationRule:
        """Read the rule and refuse it if it was fixed for another artefact."""
        rule = cls(**json.loads((Path(model_dir) / CLASSIFICATION_FILE).read_text()))
        if rule.artefact_sha256 != artefact_sha256:
            raise ClassificationMismatch(
                f"{CLASSIFICATION_FILE} was fixed for artefact {rule.artefact_sha256[:12]}, "
                f"not {artefact_sha256[:12]}; run `python -m antenatal freeze-classification`"
            )
        return rule


@dataclass(frozen=True)
class Classification:
    """The label for one case and how settled it is."""

    likely: bool
    label: str
    certainty: str
    certainty_statement: str


def classify(
    rule: ClassificationRule, probability: float, low: float, high: float
) -> Classification:
    """Label one case and say where its interval sits against the threshold."""
    likely = rule.likely(probability)
    if math.isnan(low) or math.isnan(high):
        certainty = UNAVAILABLE
    elif low >= rule.threshold:
        certainty = ABOVE
    elif high < rule.threshold:
        certainty = BELOW
    else:
        certainty = ACROSS
    return Classification(
        likely, LIKELY if likely else NOT_LIKELY, certainty, CERTAINTY_TEXT[certainty]
    )


def derive_rule(
    y: np.ndarray,
    p: np.ndarray,
    groups: np.ndarray,
    artefact_version: str,
    artefact_sha256: str,
    source: str,
    spec: StudySpec = PRIMARY,
    budget: float = BUDGET,
) -> ClassificationRule:
    """Fix the threshold at the top ``budget`` of out of fold predictions and measure it."""
    y, p = np.asarray(y), np.asarray(p)
    k = int(np.ceil(budget * len(p)))
    threshold = float(np.sort(p)[::-1][k - 1])
    flagged, events = p >= threshold, y == 1
    counts = {
        "true_positives": int((flagged & events).sum()),
        "false_positives": int((flagged & ~events).sum()),
        "false_negatives": int((~flagged & events).sum()),
        "true_negatives": int((~flagged & ~events).sum()),
    }
    bootstrap = GroupBootstrap(groups, spec.bootstrap_resamples, spec.seed)
    performance = {}
    for kind in ("sensitivity", "specificity", "ppv", "npv"):
        interval = bootstrap.single(y, p, AtThreshold(threshold, kind))
        performance[kind] = {
            "estimate": interval.estimate,
            "low": interval.low,
            "high": interval.high,
        }
    return ClassificationRule(
        threshold=threshold,
        budget_percent=round(budget * 100),
        artefact_version=artefact_version,
        artefact_sha256=artefact_sha256,
        source=source,
        n=len(y),
        events=int(y.sum()),
        counts=counts,
        performance=performance,
    )
