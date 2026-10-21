"""Construction of every model pipeline used in the study (Sections 3.3.5 and 3.3.6).

Missing values are treated in one of three ways, set per model:

* ``median``: median imputation with a missingness indicator for every
  imputed column. Used by every family except the gradient boosted trees.
* ``native``: no imputation. The gradient boosted trees handle missing values
  themselves, as Section 3.3.6 of the proposal states.
* ``iterative``: iterative imputation drawing from the posterior, used only
  by the multiple imputation sensitivity analysis.

Scaling follows for models that need it, then the estimator. Every step is
fitted inside the training data only and serialised together. No class
weighting and no resampling is used anywhere, so probabilities stay on the
natural scale.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sklearn.base import ClassifierMixin
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.impute import IterativeImputer, SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from antenatal.config import PRIMARY
from antenatal.features.sets import LINEAR, TREE

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

    @property
    def estimator_key(self) -> str:
        """The estimator this model uses; defaults to its own key."""
        return self.estimator or self.key


BASE_SPECS: tuple[ModelSpec, ...] = (
    ModelSpec("baseline_prevalence", "B0 constant prevalence", LINEAR, False),
    ModelSpec("logistic_l2", "Logistic regression, L2", LINEAR, True, LOGISTIC_GRID),
    ModelSpec("logistic_l1", "Logistic regression, L1", LINEAR, True, LOGISTIC_GRID),
    ModelSpec("lda", "Linear discriminant analysis", LINEAR, True, {"shrinkage": [None, "auto"]}),
    ModelSpec("knn", "Nearest neighbours", LINEAR, True, {"n_neighbors": [25, 50, 100]}),
    ModelSpec(
        "naive_bayes",
        "Gaussian naive Bayes",
        LINEAR,
        True,
        {"var_smoothing": [1e-9, 1e-6, 1e-3]},
    ),
    ModelSpec(
        "decision_tree",
        "Decision tree",
        TREE,
        False,
        {"max_depth": [2, 3, 4], "min_samples_leaf": [25, 50]},
    ),
    ModelSpec(
        "random_forest",
        "Random forest",
        TREE,
        False,
        {"max_depth": [3, 5], "min_samples_leaf": [25, 50]},
    ),
    ModelSpec("gradient_boosting", "Gradient boosted trees", TREE, False, BOOSTING_GRID, NATIVE),
    ModelSpec(
        "gradient_boosting_uniform",
        "GBT, uniform imputation",
        TREE,
        False,
        BOOSTING_GRID,
        estimator="gradient_boosting",
    ),
    ModelSpec(
        "logistic_l2_no_indicator",
        "Logistic regression, L2, no missingness indicators",
        LINEAR,
        True,
        LOGISTIC_GRID,
        indicator=False,
        estimator="logistic_l2",
    ),
)
ITERATIVE_SPECS: tuple[ModelSpec, ...] = tuple(
    ModelSpec(
        f"logistic_l2_iterative_{k}",
        f"Logistic regression, L2, iterative imputation {k + 1}",
        LINEAR,
        True,
        LOGISTIC_GRID,
        ITERATIVE,
        estimator="logistic_l2",
        imputation_seed=SEED + k,
    )
    for k in range(IMPUTATIONS)
)


MODEL_SPECS: dict[str, ModelSpec] = {spec.key: spec for spec in BASE_SPECS + ITERATIVE_SPECS}

FAMILY_SCREEN: tuple[str, ...] = (
    "logistic_l2",
    "logistic_l1",
    "lda",
    "knn",
    "naive_bayes",
    "decision_tree",
    "random_forest",
    "gradient_boosting",
)
PRIMARY_MODELS: tuple[str, ...] = ("logistic_l2", "gradient_boosting")
ITERATIVE_MODELS: tuple[str, ...] = tuple(f"logistic_l2_iterative_{k}" for k in range(IMPUTATIONS))


def _estimator(key: str) -> ClassifierMixin:
    estimators = {
        "baseline_prevalence": lambda: DummyClassifier(strategy="prior"),
        "logistic_l2": lambda: LogisticRegression(max_iter=5000),
        "logistic_l1": lambda: LogisticRegression(l1_ratio=1.0, solver="saga", max_iter=5000),
        "lda": lambda: LinearDiscriminantAnalysis(solver="lsqr"),
        "knn": lambda: KNeighborsClassifier(),
        "naive_bayes": lambda: GaussianNB(),
        "decision_tree": lambda: DecisionTreeClassifier(random_state=SEED),
        "random_forest": lambda: RandomForestClassifier(
            n_estimators=300, random_state=SEED, n_jobs=1
        ),
        "gradient_boosting": lambda: HistGradientBoostingClassifier(
            max_iter=200, early_stopping=True, validation_fraction=0.2, random_state=SEED
        ),
    }
    return estimators[key]()


def _imputer(spec: ModelSpec):
    if spec.imputer == ITERATIVE:
        return IterativeImputer(
            sample_posterior=True,
            max_iter=10,
            random_state=spec.imputation_seed,
            add_indicator=spec.indicator,
        )
    return SimpleImputer(strategy="median", add_indicator=spec.indicator)


class ModelFactory:
    """Builds an unfitted pipeline and its tuning grid for a model."""

    def spec(self, key: str) -> ModelSpec:
        """Return the specification of model ``key``."""
        return MODEL_SPECS[key]

    def build(self, key: str) -> tuple[Pipeline, dict[str, list]]:
        """Return the pipeline and its grid, with grid keys prefixed for the estimator step."""
        spec = MODEL_SPECS[key]
        steps = []
        if spec.imputer != NATIVE:
            steps.append(("impute", _imputer(spec)))
        if spec.scaled:
            steps.append(("scale", StandardScaler()))
        steps.append(("model", _estimator(spec.estimator_key)))
        grid = {f"model__{name}": values for name, values in spec.grid.items()}
        return Pipeline(steps), grid
