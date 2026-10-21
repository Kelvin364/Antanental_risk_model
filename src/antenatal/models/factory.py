"""Construction of every model pipeline used in the study (Sections 3.3.5 and 3.3.6).

Each pipeline is median imputation with a missingness indicator for every
imputed column, standard scaling for models that need it, then the estimator.
All three steps are fitted inside the training data only and serialised
together. No class weighting and no resampling is used anywhere: models are
fitted on the observed prevalence so their probabilities stay on the natural
scale.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sklearn.base import ClassifierMixin
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from antenatal.config import PRIMARY
from antenatal.features.sets import LINEAR, TREE

SEED = PRIMARY.seed


@dataclass(frozen=True)
class ModelSpec:
    """One model family: its label, how it reads features, scaling and tuning grid."""

    key: str
    label: str
    family: str
    scaled: bool
    grid: dict[str, list] = field(default_factory=dict)


MODEL_SPECS: dict[str, ModelSpec] = {
    spec.key: spec
    for spec in (
        ModelSpec("baseline_prevalence", "B0 constant prevalence", LINEAR, False),
        ModelSpec(
            "logistic_l2", "Logistic regression, L2", LINEAR, True, {"C": [0.01, 0.1, 1.0, 10.0]}
        ),
        ModelSpec(
            "logistic_l1", "Logistic regression, L1", LINEAR, True, {"C": [0.01, 0.1, 1.0, 10.0]}
        ),
        ModelSpec(
            "lda", "Linear discriminant analysis", LINEAR, True, {"shrinkage": [None, "auto"]}
        ),
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
        ModelSpec(
            "gradient_boosting",
            "Gradient boosted trees",
            TREE,
            False,
            {"learning_rate": [0.05, 0.1], "max_depth": [2, 3], "l2_regularization": [0.0, 1.0]},
        ),
    )
}

FAMILY_SCREEN: tuple[str, ...] = tuple(k for k in MODEL_SPECS if k != "baseline_prevalence")
PRIMARY_MODELS: tuple[str, ...] = ("logistic_l2", "gradient_boosting")


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


class ModelFactory:
    """Builds an unfitted pipeline and its tuning grid for a model family."""

    def spec(self, key: str) -> ModelSpec:
        """Return the specification of model ``key``."""
        return MODEL_SPECS[key]

    def build(self, key: str) -> tuple[Pipeline, dict[str, list]]:
        """Return the pipeline and its grid, with grid keys prefixed for the estimator step."""
        spec = MODEL_SPECS[key]
        steps = [("impute", SimpleImputer(strategy="median", add_indicator=True))]
        if spec.scaled:
            steps.append(("scale", StandardScaler()))
        steps.append(("model", _estimator(key)))
        grid = {f"model__{name}": values for name, values in spec.grid.items()}
        return Pipeline(steps), grid
