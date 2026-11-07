"""The seven methods of protocol Section 5. Every step that learns sits inside the pipeline."""

from __future__ import annotations

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

SEED = 20261107
METHODS = (
    "logistic", "logistic_weighted", "logistic_smote", "boosting", "boosting_weighted", "forest",
)  # fmt: skip
ENSEMBLE = "logistic_boosting_average"
PENALTIES = (0.01, 0.1, 1.0)


def _prepare():
    return make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler())


def smote(x: np.ndarray, y: np.ndarray, seed: int, neighbours: int = 5):
    """Synthetic minority records up to balance, built from training records only."""
    rng = np.random.default_rng(seed)
    minority = x[y == 1]
    needed = int((y == 0).sum() - len(minority))
    index = NearestNeighbors(n_neighbors=neighbours + 1).fit(minority)
    near = index.kneighbors(minority, return_distance=False)[:, 1:]
    base = rng.integers(0, len(minority), needed)
    partner = near[base, rng.integers(0, neighbours, needed)]
    step = rng.random((needed, 1))
    synthetic = minority[base] + step * (minority[partner] - minority[base])
    return np.vstack([x, synthetic]), np.concatenate([y, np.ones(needed, dtype=y.dtype)])


class Logistic(ClassifierMixin, BaseEstimator):
    """L2 logistic regression; the penalty is tuned on grouped inner folds of the training fold."""

    def __init__(self, weighted: bool = False, resample: bool = False) -> None:
        self.weighted = weighted
        self.resample = resample

    def fit(self, x, y, groups):
        self.prepare_ = _prepare().fit(x)
        z = self.prepare_.transform(x)
        y = np.asarray(y)
        model = LogisticRegression(
            max_iter=2000, class_weight="balanced" if self.weighted else None
        )
        inner = StratifiedGroupKFold(3, shuffle=True, random_state=SEED)
        search = GridSearchCV(
            model, {"C": PENALTIES}, scoring="average_precision", cv=inner, n_jobs=1
        ).fit(z, y, groups=groups)
        self.penalty_ = search.best_params_["C"]
        if self.resample:
            z, y = smote(z, y, SEED)
        self.model_ = model.set_params(C=self.penalty_).fit(z, y)
        self.classes_ = self.model_.classes_
        return self

    def predict_proba(self, x):
        return self.model_.predict_proba(self.prepare_.transform(x))


class Trees(ClassifierMixin, BaseEstimator):
    """Conservative fixed settings: 165 to 240 events cannot support a wide search."""

    def __init__(self, kind: str = "boosting", weighted: bool = False) -> None:
        self.kind = kind
        self.weighted = weighted

    def fit(self, x, y, groups=None):
        weight = "balanced" if self.weighted else None
        if self.kind == "boosting":
            self.model_ = HistGradientBoostingClassifier(
                learning_rate=0.05, max_iter=150, max_depth=3, min_samples_leaf=30,
                l2_regularization=1.0, class_weight=weight, random_state=SEED,
            )  # fmt: skip
            self.prepare_ = None
            self.model_.fit(x, y)
        else:
            self.prepare_ = SimpleImputer(strategy="median", add_indicator=True).fit(x)
            self.model_ = RandomForestClassifier(
                n_estimators=200, min_samples_leaf=10, class_weight=weight,
                random_state=SEED, n_jobs=1,
            )  # fmt: skip
            self.model_.fit(self.prepare_.transform(x), y)
        self.classes_ = self.model_.classes_
        return self

    def predict_proba(self, x):
        return self.model_.predict_proba(self.prepare_.transform(x) if self.prepare_ else x)


def build(method: str):
    """A fresh unfitted estimator for ``method``."""
    return {
        "logistic": Logistic(),
        "logistic_weighted": Logistic(weighted=True),
        "logistic_smote": Logistic(resample=True),
        "boosting": Trees("boosting"),
        "boosting_weighted": Trees("boosting", weighted=True),
        "forest": Trees("forest"),
    }[method]
