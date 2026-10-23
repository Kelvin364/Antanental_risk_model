"""The Stage 2 experiment models, exactly as prespecified in ``configs/experiment_plan.yaml``.

Elastic net (2.1a), a bounded random search for the boosted trees (2.1b), balanced
class weights alone and paired with Platt recalibration (2.2), splines with
interactions (2.4), and cross fitted Platt and isotonic recalibration (2.5).
"""

from __future__ import annotations

import numpy as np
from scipy.stats import loguniform, randint, uniform
from sklearn.model_selection import ParameterSampler

from antenatal.features.sets import LINEAR, TREE
from antenatal.models.spec import BOOSTING_GRID, LOGISTIC_GRID, NATIVE, SEED, ModelSpec

ELASTIC_GRID = {
    "l1_ratio": [0.25, 0.5, 0.75],
    "C": [float(c) for c in np.round(np.logspace(np.log10(0.003), np.log10(30), 8), 5)],
}
SEARCH_SPACE = {
    "learning_rate": loguniform(0.03, 0.2),
    "max_depth": [2, 3, 4],
    "min_samples_leaf": randint(20, 81),
    "max_leaf_nodes": randint(15, 64),
    "l2_regularization": uniform(0, 3),
    "max_features": uniform(0.5, 0.5),
}
# 30 seeded draws, the same for every training fold (experiment 2.1b).
BOOSTING_SEARCH: list[dict[str, list]] = [
    {k: [v] for k, v in draw.items()}
    for draw in ParameterSampler(SEARCH_SPACE, n_iter=30, random_state=SEED)
]
BALANCED = {"class_weight": "balanced"}


def _calibrated(base: ModelSpec, method: str, key: str) -> ModelSpec:
    return ModelSpec(
        key,
        f"{base.label}, {method} recalibration",
        base.family,
        base.scaled,
        base.grid,
        base.imputer,
        base.indicator,
        base.estimator_key,
        params=base.params,
        calibration=method,
    )


_LR = ModelSpec("logistic_l2", "Logistic regression, L2", LINEAR, True, LOGISTIC_GRID)
_GB = ModelSpec("gradient_boosting", "Gradient boosted trees", TREE, False, BOOSTING_GRID, NATIVE)
_LR_W = ModelSpec(
    "logistic_l2_weighted",
    "Logistic regression, L2, balanced weights",
    LINEAR,
    True,
    LOGISTIC_GRID,
    estimator="logistic_l2",
    params=BALANCED,
)
_GB_W = ModelSpec(
    "gradient_boosting_weighted",
    "Gradient boosted trees, balanced weights",
    TREE,
    False,
    BOOSTING_GRID,
    NATIVE,
    estimator="gradient_boosting",
    params=BALANCED,
)
EXPERIMENT_SPECS: tuple[ModelSpec, ...] = (
    ModelSpec(
        "logistic_elastic_net",
        "Logistic regression, elastic net (2.1a)",
        LINEAR,
        True,
        ELASTIC_GRID,
        estimator="logistic_elastic_net",
    ),
    ModelSpec(
        "gradient_boosting_search",
        "Gradient boosted trees, random search (2.1b)",
        TREE,
        False,
        BOOSTING_SEARCH,
        NATIVE,
        estimator="gradient_boosting_search",
    ),
    _LR_W,
    _GB_W,
    _calibrated(_LR_W, "sigmoid", "logistic_l2_weighted_platt"),
    _calibrated(_GB_W, "sigmoid", "gradient_boosting_weighted_platt"),
    ModelSpec(
        "logistic_l2_splines",
        "Logistic regression, L2, splines and interactions (2.4)",
        LINEAR,
        True,
        LOGISTIC_GRID,
        estimator="logistic_l2",
        pre="splines",
    ),
    _calibrated(_LR, "sigmoid", "logistic_l2_platt"),
    _calibrated(_LR, "isotonic", "logistic_l2_isotonic"),
    _calibrated(_GB, "sigmoid", "gradient_boosting_platt"),
    _calibrated(_GB, "isotonic", "gradient_boosting_isotonic"),
)
