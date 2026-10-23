"""The Stage 2 building blocks: splines, extras, new feature sets, Holm, the selection rule."""

import numpy as np
import pandas as pd
import pytest

from antenatal.evaluation.candidates import apply_rule, selection
from antenatal.experiments_v2 import comparisons, holm, planned
from antenatal.features.extras import EXTRA_COLUMNS, extra_values, heartbeat, malaria
from antenatal.features.screen import ScreenResult
from antenatal.features.sets import LINEAR, SetAPlus, SetB, SetBExtras, SetBWithout
from antenatal.models.transforms import SplineInteractions, spline_term

SCREEN = ScreenResult({"sbp": 1, "dbp": 1, "weight": 1, "ga": 1, "pulse": 0.8, "hb": 0.3}, 0.6, 10)


def test_spline_knots_come_from_the_training_fold_only():
    train = pd.DataFrame(
        {
            c: np.arange(100.0)
            for c in ("age", "registration_weight", "weight_v2", "sbp_v2", "gravidity", "ga_v2")
        }
    )
    model = SplineInteractions().fit(train)
    assert model.knots_["age"] == pytest.approx((9.9, 49.5, 89.1))
    shifted = model.transform(train + 1000)
    assert "age_rcs" in shifted and "sbp_v2_x_ga_v2" in shifted
    assert spline_term(np.array([0.0, 5.0]), (10, 50, 90)).tolist() == [0.0, 0.0]


def test_extras_map_the_typing_variants():
    assert [malaria(v) for v in ("positive", "p0sitive", "pos(pf)", "ngative", "x")] == [
        1.0,
        1.0,
        1.0,
        0.0,
        None,
    ]
    assert (heartbeat("present"), heartbeat("not present"), heartbeat("?")) == (1.0, 0.0, None)


def test_extras_never_read_outcome_copies(raw):
    values = extra_values(raw)
    assert set(values.columns) == {"record_id", *EXTRA_COLUMNS}
    assert values["temperature_v2"].dropna().between(34, 42).all()


def test_new_feature_sets():
    base = SetB().columns(SCREEN, LINEAR)
    assert SetAPlus("ga").columns(SCREEN, LINEAR)[-1] == "ga_v2"
    assert "hb_v2" not in SetBWithout("hb").columns(SCREEN, LINEAR)
    assert SetBExtras().columns(SCREEN, LINEAR) == base + list(EXTRA_COLUMNS)


def test_holm_matches_a_hand_example():
    adjusted = holm(pd.Series([0.01, 0.04, 0.03]))
    assert adjusted.round(4).tolist() == [0.03, 0.06, 0.06]


def test_plan_runs_and_comparisons_are_complete():
    ids = {p.plan_id for p in planned()}
    assert ids == {"2.1a", "2.1b", "2.2", "2.3", "2.4", "2.5", "2.10"}
    labels = [c.label for c in comparisons()]
    assert any(label.startswith("2.9") for label in labels)
    assert sum("tuned primary" in label for label in labels) == 2


def _row(model, ap_diff, low, dd, slope=(0.8, 1.2), brier_low=-0.001, inputs=20):
    return {
        "model": model,
        "feature_set": "C",
        "inputs": inputs,
        "ap_vs_artefact": ap_diff,
        "ap_vs_artefact_low": low,
        "detectable_difference": dd,
        "calibration_slope_low": slope[0],
        "calibration_slope_high": slope[1],
        "brier_vs_artefact_low": brier_low,
        "pr_auc": 0.1,
    }


@pytest.mark.parametrize(
    "row, passes",
    [
        (_row("logistic_elastic_net", 0.02, 0.005, 0.011), True),
        (_row("logistic_elastic_net", 0.009, 0.001, 0.011), False),
        (_row("logistic_elastic_net", 0.02, -0.001, 0.011), False),
        (_row("logistic_elastic_net", 0.02, 0.005, 0.011, slope=(1.1, 1.5)), False),
        (_row("logistic_elastic_net", 0.02, 0.005, 0.011, brier_low=0.001), False),
        (_row("logistic_l2", 0.5, 0.4, 0.011), False),
    ],
)
def test_selection_rule_part_a(row, passes):
    assert bool(apply_rule(pd.DataFrame([row]))["passes_rule"].iloc[0]) is passes


def test_selection_prefers_the_simpler_and_keeps_the_artefact_otherwise():
    table = apply_rule(
        pd.DataFrame(
            [
                _row("gradient_boosting_search", 0.03, 0.01, 0.011, inputs=20),
                _row("logistic_elastic_net", 0.02, 0.005, 0.011, inputs=20),
            ]
        )
    )
    assert selection(table)["chosen"] == "logistic_elastic_net on C"
    none = apply_rule(pd.DataFrame([_row("logistic_elastic_net", 0.001, -0.01, 0.011)]))
    assert selection(none)["outcome"] == "c"
