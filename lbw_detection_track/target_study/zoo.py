"""Protocol Section 4: the model types, each a full pipeline so every learnt step stays in fold."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin, TransformerMixin, clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    ExtraTreesClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.impute import IterativeImputer, SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, SplineTransformer, StandardScaler
from sklearn.svm import SVC

SEED = 20261109
GROUPS: dict[int, str] = {}


class Clip(TransformerMixin, BaseEstimator):
    """Limit each column to the training 1st and 99th percentiles."""

    def fit(self, x, y=None):
        self.low_, self.high_ = np.nanpercentile(x, 1, axis=0), np.nanpercentile(x, 99, axis=0)
        return self

    def transform(self, x):
        return np.clip(x, self.low_, self.high_)


def prepare(columns: list[str], categorical: list[str], kind: str) -> ColumnTransformer:
    numbers = [c for c in columns if c not in categorical]
    steps = [SimpleImputer(strategy="median", add_indicator=True)]
    if kind == "linear":
        steps += [Clip(), StandardScaler()]
    if kind == "spline":
        steps = [SimpleImputer(strategy="median"), Clip(), SplineTransformer(4, 3)]
    if kind == "chained":
        steps = []
    parts = [("numbers", make_pipeline(*steps) if steps else "passthrough", numbers)]
    if categorical:
        encode = OneHotEncoder(
            min_frequency=20, handle_unknown="infrequent_if_exist", sparse_output=False
        )
        fill = SimpleImputer(strategy="constant", fill_value="missing")
        parts.append(("categories", make_pipeline(fill, encode), categorical))
    return ColumnTransformer(parts)


def _logistic(**params):
    return LogisticRegression(max_iter=5000, **params)


def _boost(depth: int, rate: float = 0.05, rounds: int = 300, leaf: int = 30):
    return HistGradientBoostingClassifier(
        max_depth=depth, learning_rate=rate, max_iter=rounds, min_samples_leaf=leaf,
        l2_regularization=1.0, early_stopping=False, random_state=SEED,
    )  # fmt: skip


class Chained(ClassifierMixin, BaseEstimator):
    """Multiple imputation by chained equations: 5 posterior draws, predictions averaged."""

    def __init__(self, columns=None, C: float = 0.1, draws: int = 5) -> None:  # noqa: N803
        self.columns, self.C, self.draws = columns, C, draws

    def fit(self, x, y):
        self.models_ = [
            make_pipeline(
                IterativeImputer(sample_posterior=True, max_iter=10, random_state=k,
                                 add_indicator=True),
                Clip(), StandardScaler(), _logistic(C=self.C),
            ).fit(x, y)
            for k in range(self.draws)
        ]  # fmt: skip
        self.classes_ = self.models_[0].classes_
        return self

    def predict_proba(self, x):
        return np.mean([m.predict_proba(x) for m in self.models_], axis=0)

    def predict(self, x):
        return self.classes_[(self.predict_proba(x)[:, 1] >= 0.5).astype(int)]


class GroupStack(ClassifierMixin, BaseEstimator):
    """Stacking whose base predictions come from grouped inner folds of the training records."""

    def __init__(self, bases=None) -> None:
        self.bases = bases

    def fit(self, x: pd.DataFrame, y):
        y, groups = np.asarray(y), np.array([GROUPS[i] for i in x.index])
        inner = np.zeros((len(y), len(self.bases)))
        splitter = StratifiedGroupKFold(3, shuffle=True, random_state=SEED)
        for train, test in splitter.split(x, y, groups):
            for k, base in enumerate(self.bases):
                fitted = clone(base).fit(x.iloc[train], y[train])
                inner[test, k] = fitted.predict_proba(x.iloc[test])[:, 1]
        self.final_ = _logistic(C=1.0).fit(_logit(inner), y)
        self.fitted_ = [clone(b).fit(x, y) for b in self.bases]
        self.classes_ = self.final_.classes_
        return self

    def predict_proba(self, x):
        scores = np.column_stack([b.predict_proba(x)[:, 1] for b in self.fitted_])
        return self.final_.predict_proba(_logit(scores))

    def predict(self, x):
        return self.classes_[(self.predict_proba(x)[:, 1] >= 0.5).astype(int)]


def _logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def model(name: str, columns: list[str], categorical: list[str]):
    """Unfitted pipeline and its tuning grid (prefixed for the final step)."""
    cats = [c for c in categorical if c in columns]
    lin, tree = prepare(columns, cats, "linear"), prepare(columns, cats, "tree")
    specs = {
        "l2_logistic": (lin, _logistic(), {"C": [0.01, 0.1, 1.0]}),
        "lasso": (lin, _logistic(l1_ratio=1.0, solver="saga"), {"C": [0.01, 0.03, 0.1, 0.3]}),
        "elastic_net": (
            lin, _logistic(solver="saga"), {"l1_ratio": [0.2, 0.5, 0.8], "C": [0.03, 0.1, 0.3]},
        ),
        "spline_gam": (prepare(columns, cats, "spline"), _logistic(), {"C": [0.01, 0.1, 1.0]}),
        "additive_boosting": (tree, _boost(1), {"max_iter": [200, 500]}),
        "pairwise_boosting": (tree, _boost(2), {"max_iter": [150, 400]}),
        "gradient_boosting": (
            tree, _boost(3), {"max_depth": [3, 5], "min_samples_leaf": [30, 80],
                              "learning_rate": [0.03]},
        ),
        "random_forest": (
            tree, RandomForestClassifier(300, max_features="sqrt", random_state=SEED, n_jobs=1),
            {"min_samples_leaf": [5, 20]},
        ),
        "extra_trees": (
            tree, ExtraTreesClassifier(300, max_features="sqrt", random_state=SEED, n_jobs=1),
            {"min_samples_leaf": [5, 20]},
        ),
        "svm": (lin, SVC(probability=True, random_state=SEED), {"C": [0.1, 1.0]}),
        "weighted_l2": (lin, _logistic(class_weight="balanced"), {"C": [0.01, 0.1, 1.0]}),
    }  # fmt: skip
    if name == "stacking":
        bases = [
            make_pipeline(clone(lin), _logistic(solver="saga", l1_ratio=0.5, C=0.1)),
            make_pipeline(clone(tree), _boost(3, 0.05, 150)),
            make_pipeline(clone(tree), RandomForestClassifier(300, min_samples_leaf=20,
                                                              random_state=SEED, n_jobs=1)),
        ]  # fmt: skip
        return GroupStack(bases), {}
    if name == "multiple_imputation":
        return make_pipeline(prepare(columns, cats, "chained"), Chained()), {
            "chained__C": [0.01, 0.1, 1.0]
        }
    prep, final, grid = specs[name]
    step = type(final).__name__.lower()
    return make_pipeline(prep, final), {f"{step}__{k}": v for k, v in grid.items()}


NAMES = (
    "l2_logistic", "lasso", "elastic_net", "spline_gam", "additive_boosting",
    "pairwise_boosting", "gradient_boosting", "random_forest", "extra_trees", "svm",
    "stacking", "weighted_l2",
)  # fmt: skip
