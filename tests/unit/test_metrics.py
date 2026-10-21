"""Metrics, bootstrap and power against reference implementations on toy data."""

import numpy as np
import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from antenatal.evaluation.bootstrap import GroupBootstrap
from antenatal.evaluation.calibration import calibration_table
from antenatal.evaluation.decision_curve import decision_curve_table
from antenatal.evaluation.metrics import (
    AveragePrecision,
    RocAuc,
    average_precision,
    brier,
    calibration_slope_intercept,
    logit,
    net_benefit,
    roc_auc,
    score_all,
)
from antenatal.evaluation.power import detectable_difference


@pytest.fixture
def toy():
    rng = np.random.default_rng(0)
    x = rng.normal(size=600)
    y = (rng.random(600) < 1 / (1 + np.exp(-(x - 2)))).astype(int)
    p = 1 / (1 + np.exp(-(0.8 * x - 1.9)))
    return y, p


def test_average_precision_matches_sklearn(toy):
    y, p = toy
    assert average_precision(y, p) == pytest.approx(average_precision_score(y, p))


def test_roc_and_brier_match_sklearn(toy):
    y, p = toy
    assert roc_auc(y, p) == pytest.approx(roc_auc_score(y, p))
    assert brier(y, p) == pytest.approx(brier_score_loss(y, p))


def test_constant_prediction_precision_equals_prevalence(toy):
    y, _ = toy
    assert average_precision(y, np.full(len(y), 0.1)) == pytest.approx(y.mean())


def test_calibration_slope_matches_unpenalised_logistic(toy):
    y, p = toy
    slope, _ = calibration_slope_intercept(y, p)
    reference = LogisticRegression(C=np.inf).fit(logit(p).reshape(-1, 1), y)
    assert slope == pytest.approx(reference.coef_[0, 0], rel=1e-4)


def test_perfectly_calibrated_predictions_have_slope_one():
    rng = np.random.default_rng(1)
    p = rng.uniform(0.01, 0.6, 50000)
    y = (rng.random(50000) < p).astype(int)
    slope, intercept = calibration_slope_intercept(y, p)
    assert slope == pytest.approx(1, abs=0.05) and intercept == pytest.approx(0, abs=0.05)


def test_net_benefit_by_hand():
    y = np.array([1, 0, 1, 0, 0])
    p = np.array([0.9, 0.8, 0.2, 0.1, 0.05])
    assert net_benefit(y, p, np.array([0.5]))[0] == pytest.approx(1 / 5 - 1 / 5 * 1)


def test_decision_curve_has_reference_policies(toy):
    y, p = toy
    table = decision_curve_table(y, {"model": p})
    assert {"act for everyone", "act for no one", "model"} <= set(table.columns)


def test_calibration_table_counts(toy):
    y, p = toy
    table = calibration_table(y, p, bins=6)
    assert table["n"].sum() == len(y) and table["events"].sum() == y.sum()


def test_score_all_names(toy):
    y, p = toy
    assert set(score_all(y, p)) == {
        "pr_auc",
        "roc_auc",
        "brier",
        "calibration_slope",
        "calibration_intercept",
    }


def test_bootstrap_is_reproducible_and_contains_estimate(toy):
    y, p = toy
    groups = np.arange(len(y)) // 2
    first = GroupBootstrap(groups, 200, 7).single(y, p, RocAuc())
    second = GroupBootstrap(groups, 200, 7).single(y, p, RocAuc())
    assert first == second
    assert first.low <= first.estimate <= first.high


def test_paired_difference_of_identical_predictions_is_zero(toy):
    y, p = toy
    interval = GroupBootstrap(np.arange(len(y)), 100, 1).paired_difference(
        y, p, p, AveragePrecision()
    )
    assert interval.estimate == 0 and interval.low == 0 and interval.high == 0
    assert not interval.excludes_zero


def test_bootstrap_resamples_whole_groups():
    groups = np.array(["a", "a", "b", "c", "c", "c"])
    for idx in GroupBootstrap(groups, 20, 3).indices():
        chosen = groups[idx]
        for g in "abc":
            assert (chosen == g).sum() % (groups == g).sum() == 0


def test_detectable_difference_formula():
    assert detectable_difference(0.01) == pytest.approx(0.028016, abs=1e-6)
    with pytest.raises(ValueError):
        detectable_difference(-1)
