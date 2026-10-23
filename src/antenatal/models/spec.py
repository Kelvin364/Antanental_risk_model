"""The description of one model, shared by the study models and the Stage 2 experiments."""

from __future__ import annotations

from dataclasses import dataclass, field

from antenatal.config import PRIMARY

SEED = PRIMARY.seed
MEDIAN, NATIVE, ITERATIVE = "median", "native", "iterative"
IMPUTATIONS = 5
LOGISTIC_GRID = {"C": [0.01, 0.1, 1.0, 10.0]}
BOOSTING_GRID = {"learning_rate": [0.05, 0.1], "max_depth": [2, 3], "l2_regularization": [0.0, 1.0]}


@dataclass(frozen=True)
class ModelSpec:
    """One model: label, how it reads features, missing value treatment, scaling and grid."""

    key: str
    label: str
    family: str
    scaled: bool
    grid: dict[str, list] = field(default_factory=dict)
    imputer: str = MEDIAN
    indicator: bool = True
    estimator: str = ""
    imputation_seed: int = SEED
    params: dict[str, object] = field(default_factory=dict)
    pre: str = ""
    calibration: str = ""

    @property
    def estimator_key(self) -> str:
        """The estimator this model uses; defaults to its own key."""
        return self.estimator or self.key
