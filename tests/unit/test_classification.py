"""The fixed classification threshold and the confidence of each label (decision D6)."""

import json

import numpy as np
import pytest

from antenatal.artefact.classification import (
    ABOVE,
    ACROSS,
    BELOW,
    LIKELY,
    NOT_LIKELY,
    UNAVAILABLE,
    AtThreshold,
    classify,
    derive_rule,
)


def _rule(n=400, seed=3):
    rng = np.random.default_rng(seed)
    p = rng.uniform(0, 0.3, n)
    y = (rng.uniform(0, 1, n) < p).astype(int)
    return derive_rule(y, p, np.arange(n), "9.9.9", "f" * 64, "synthetic"), y, p


def test_threshold_marks_the_top_twenty_percent():
    rule, y, p = _rule()
    assert (p >= rule.threshold).sum() == int(np.ceil(0.2 * len(p)))
    assert sum(rule.counts.values()) == len(y) and rule.events == y.sum()


def test_performance_matches_the_counts_and_has_intervals():
    rule, _, _ = _rule()
    c = rule.counts
    sens = c["true_positives"] / (c["true_positives"] + c["false_negatives"])
    assert rule.performance["sensitivity"]["estimate"] == pytest.approx(sens)
    for value in rule.performance.values():
        assert value["low"] <= value["estimate"] <= value["high"]


@pytest.mark.parametrize(
    "p, low, high, label, certainty",
    [
        (0.20, 0.15, 0.25, LIKELY, ABOVE),
        (0.02, 0.01, 0.03, NOT_LIKELY, BELOW),
        (0.11, 0.05, 0.16, LIKELY, ACROSS),
        (0.09, float("nan"), float("nan"), NOT_LIKELY, UNAVAILABLE),
    ],
)
def test_classify_reports_where_the_interval_sits(p, low, high, label, certainty):
    rule, _, _ = _rule()
    rule = rule.__class__(**{**rule.__dict__, "threshold": 0.10})
    result = classify(rule, p, low, high)
    assert (result.label, result.certainty) == (label, certainty)


def test_at_threshold_metrics_on_a_hand_example():
    y, p = np.array([1, 1, 0, 0]), np.array([0.9, 0.2, 0.8, 0.1])
    assert AtThreshold(0.5, "sensitivity").compute(y, p) == 0.5
    assert AtThreshold(0.5, "ppv").compute(y, p) == 0.5
    assert AtThreshold(0.5, "npv").compute(y, p) == 0.5


def test_served_rule_belongs_to_the_served_artefact(root):
    rule = json.loads((root / "webapp" / "model" / "classification.json").read_text())
    checksum = (root / "webapp" / "model" / "lbw_model.sha256").read_text().split()[0]
    assert rule["artefact_sha256"] == checksum and rule["budget_percent"] == 20
    assert rule["n"] == 3126 and rule["events"] == 165
