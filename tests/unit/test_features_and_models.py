"""Availability screen, feature sets, model factory and the cross validation runner."""

import numpy as np
import pandas as pd
import pytest

from antenatal.cohort.partition import grouped_outer_folds
from antenatal.config import PRIMARY
from antenatal.data.dictionary import REGISTRATION_FIELDS
from antenatal.evaluation.nested_cv import Experiment, NestedCVRunner
from antenatal.features.builder import FeatureBuilder, input_columns
from antenatal.features.screen import AvailabilityScreen, ScreenResult
from antenatal.features.sets import (
    LINEAR,
    TREE,
    SetA,
    SetB,
    SetC,
    SetCChangeOnly,
    SetCRate,
    SetCWithChange,
    SetCWithout,
)
from antenatal.models.factory import FAMILY_SCREEN, MODEL_SPECS, NATIVE, ModelFactory

SCREEN = ScreenResult(
    {"sbp": 1.0, "dbp": 1.0, "weight": 0.99, "ga": 1.0, "pulse": 0.8, "hb": 0.35}, 0.6, 100
)


def test_screen_passes_and_fails_on_development(cohort, sealed):
    result = AvailabilityScreen().fit(sealed[1].development(cohort))
    assert set(result.passed) == {"sbp", "dbp", "weight", "ga", "pulse"}
    assert result.to_frame().set_index("measurement").loc["hb", "result"] == "fail"


def test_screen_never_reads_the_outcome(cohort, sealed):
    development = sealed[1].development(cohort)
    shuffled = development.assign(lbw=np.random.default_rng(0).permutation(development["lbw"]))
    assert AvailabilityScreen().fit(development) == AvailabilityScreen().fit(shuffled)


def test_sets_are_nested():
    a, b, c = (s.columns(SCREEN, LINEAR) for s in (SetA(), SetB(), SetC()))
    assert set(a) < set(b) < set(c)
    assert a == [f.name for f in REGISTRATION_FIELDS]


def test_set_b_keeps_haemoglobin_and_set_c_drops_its_first_visit():
    assert "hb_v2" in SetB().columns(SCREEN, LINEAR)
    assert "hb_v1" not in SetC().columns(SCREEN, LINEAR)


def test_linear_set_c_has_no_change_or_rate_terms():
    columns = SetC().columns(SCREEN, LINEAR)
    assert not [c for c in columns if c.startswith("d_") or c.endswith("_per_week")]


def test_tree_set_c_adds_change_terms():
    extra = set(SetC().columns(SCREEN, TREE)) - set(SetC().columns(SCREEN, LINEAR))
    assert extra == {"d_sbp", "d_dbp", "d_weight", "d_ga", "d_pulse"}


def test_parameterisation_variants():
    assert "sbp_v1" not in SetCChangeOnly().columns(SCREEN, LINEAR)
    assert "d_sbp" in SetCWithChange().columns(SCREEN, LINEAR)
    assert "weight_per_week" in SetCRate().columns(SCREEN, LINEAR)
    assert "ga_per_week" not in SetCRate().columns(SCREEN, LINEAR)
    assert "pulse_v1" not in SetCWithout("pulse").columns(SCREEN, TREE)


def test_unknown_family_is_rejected():
    with pytest.raises(ValueError):
        SetA().columns(SCREEN, "deep")


def test_builder_derives_changes_and_fills_missing_inputs():
    frame = pd.DataFrame([{"weight_v1": 50.0, "weight_v2": 53.0, "ga_v1": 10.0, "ga_v2": 16.0}])
    out = FeatureBuilder().derive(frame)
    assert out.loc[0, "d_weight"] == 3 and out.loc[0, "weight_per_week"] == 0.5
    assert set(input_columns()) <= set(out.columns) and np.isnan(out.loc[0, "hb_v2"])


@pytest.mark.parametrize("key", list(MODEL_SPECS))
def test_factory_builds_unweighted_pipelines(key):
    pipeline, grid = ModelFactory().build(key)
    spec = MODEL_SPECS[key]
    assert ("impute" in pipeline.named_steps) == (spec.imputer != NATIVE)
    if "impute" in pipeline.named_steps:
        assert pipeline.named_steps["impute"].add_indicator == spec.indicator
    assert ("scale" in pipeline.named_steps) == spec.scaled
    model = pipeline.named_steps["model"]
    assert getattr(model, "class_weight", None) == spec.params.get("class_weight")
    names = [n for draw in grid for n in draw] if isinstance(grid, list) else list(grid)
    assert all(name.startswith("model__") for name in names)


def test_no_study_model_is_weighted():
    """Weighting exists only in the Stage 2 experiment models (decision D4)."""
    from antenatal.models.factory import BASE_SPECS, ITERATIVE_SPECS

    assert all("class_weight" not in spec.params for spec in BASE_SPECS + ITERATIVE_SPECS)


def test_gradient_boosting_handles_missing_values_natively():
    pipeline, _ = ModelFactory().build("gradient_boosting")
    assert list(pipeline.named_steps) == ["model"]
    uniform, _ = ModelFactory().build("gradient_boosting_uniform")
    assert list(uniform.named_steps) == ["impute", "model"]


def test_family_screen_has_eight_families():
    assert len(FAMILY_SCREEN) == 8 and "gradient_boosting_uniform" not in FAMILY_SCREEN


def test_runner_on_development_subset(cohort, sealed):
    development = sealed[1].development(cohort)
    small = development.iloc[:800].reset_index(drop=True)
    folds = grouped_outer_folds(small, PRIMARY.variant("small", repeats=2))
    results = NestedCVRunner(sealed[1].guard(), n_jobs=1).run(
        small, folds, [Experiment("logistic_l2", SetC())]
    )
    assert len(results.oof) == 2 * len(small)
    averaged = results.averaged("logistic_l2", "C")
    assert len(averaged) == len(small) and np.all((averaged > 0) & (averaged < 1))
    assert set(results.fold_metrics["fold"]) == set(range(5))


@pytest.mark.parametrize("key", list(MODEL_SPECS))
def test_every_random_estimator_is_seeded(key):
    """R4: an estimator that draws random numbers must carry the study seed.

    Deterministic configurations are exempt: the lbfgs solver of logistic
    regression and the prior strategy of the constant prevalence baseline.
    """
    model = ModelFactory().build(key)[0].named_steps["model"]
    params = model.get_params()
    deterministic = params.get("solver") == "lbfgs" or params.get("strategy") == "prior"
    if "random_state" in params and not deterministic:
        assert params["random_state"] == PRIMARY.seed
