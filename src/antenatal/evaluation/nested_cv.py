"""Repeated nested grouped cross validation on development records (Figure 3.3).

Algorithm. For every repeat and every outer fold of the sealed fold
assignment: the availability screen is refitted on the outer training records,
the feature set's columns are chosen from that screen, the hyperparameters are
chosen by grouped stratified inner cross validation on the outer training
records (scored by average precision), the selected pipeline is refitted on
all outer training records, and the outer test records are predicted. Outer
test records take no part in any choice. Predictions are kept per record per
repeat, so they can be averaged per record for the paired group bootstrap.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold
from sklearn.pipeline import Pipeline

from antenatal.cohort.partition import FoldAssignment
from antenatal.config import PRIMARY, StudySpec
from antenatal.evaluation.metrics import score_all
from antenatal.features.builder import FeatureBuilder
from antenatal.features.screen import AvailabilityScreen
from antenatal.features.sets import FeatureSet
from antenatal.models.factory import ModelFactory


@dataclass(frozen=True)
class Experiment:
    """One model family fitted to one feature set."""

    model: str
    feature_set: FeatureSet

    @property
    def key(self) -> tuple[str, str]:
        """(model, feature set name)."""
        return (self.model, self.feature_set.name)


@dataclass(frozen=True)
class FittedModel:
    """A pipeline fitted on some records, with the columns and settings it used."""

    pipeline: Pipeline
    columns: list[str]
    params: dict[str, object]


@dataclass
class CVResults:
    """Out of fold predictions and per fold metrics of every experiment."""

    development: pd.DataFrame
    oof: pd.DataFrame
    fold_metrics: pd.DataFrame

    @property
    def y(self) -> np.ndarray:
        """Outcomes of the development records, in development order."""
        return self.development["lbw"].to_numpy()

    @property
    def groups(self) -> np.ndarray:
        """Registration group of each development record."""
        return self.development["group_key"].to_numpy()

    def averaged(self, model: str, feature_set: str) -> np.ndarray:
        """Out of fold probability per record averaged across repeats, in development order."""
        rows = self.oof[(self.oof["model"] == model) & (self.oof["feature_set"] == feature_set)]
        if rows.empty:
            raise KeyError((model, feature_set))
        mean = rows.groupby("record_id")["probability"].mean()
        return self.development["record_id"].map(mean).to_numpy()

    def merge(self, other: CVResults) -> CVResults:
        """Combine the results of two runs on the same development records."""
        return CVResults(
            self.development,
            pd.concat([self.oof, other.oof], ignore_index=True),
            pd.concat([self.fold_metrics, other.fold_metrics], ignore_index=True),
        )


class NestedCVRunner:
    """Runs experiments over a fixed fold assignment."""

    def __init__(self, spec: StudySpec = PRIMARY, n_jobs: int = -1) -> None:
        self._spec = spec
        self._factory = ModelFactory()
        self._screen = AvailabilityScreen(spec)
        self._builder = FeatureBuilder()
        self._n_jobs = n_jobs

    def fit(self, train: pd.DataFrame, experiment: Experiment, seed: int) -> FittedModel:
        """Screen, choose columns, tune by inner grouped folds and refit on ``train``."""
        screen = self._screen.fit(train)
        family = self._factory.spec(experiment.model).family
        columns = experiment.feature_set.columns(screen, family)
        x = self._builder.matrix(train, columns)
        y = train["lbw"].to_numpy()
        pipeline, grid = self._factory.build(experiment.model)
        if not grid:
            return FittedModel(pipeline.fit(x, y), columns, {})
        inner = StratifiedGroupKFold(self._spec.inner_folds, shuffle=True, random_state=seed)
        splits = list(inner.split(x, y, train["group_key"]))
        search = GridSearchCV(pipeline, grid, scoring="average_precision", cv=splits, refit=True)
        search.fit(x, y)
        return FittedModel(search.best_estimator_, columns, search.best_params_)

    def _fold(self, development, train_idx, test_idx, experiment, repeat, fold):
        train, test = development.iloc[train_idx], development.iloc[test_idx]
        fitted = self.fit(train, experiment, self._spec.seed + repeat)
        x_test = self._builder.matrix(test, fitted.columns)
        probability = fitted.pipeline.predict_proba(x_test)[:, 1]
        y_test = test["lbw"].to_numpy()
        model, feature_set = experiment.key
        oof = pd.DataFrame(
            {
                "record_id": test["record_id"].to_numpy(),
                "model": model,
                "feature_set": feature_set,
                "repeat": repeat,
                "fold": fold,
                "probability": probability,
            }
        )
        metrics = {
            "model": model,
            "feature_set": feature_set,
            "repeat": repeat,
            "fold": fold,
            "n": len(test),
            "events": int(y_test.sum()),
            "n_features": len(fitted.columns),
            **score_all(y_test, probability),
            "params": repr(fitted.params),
        }
        return oof, metrics

    def _repeats(self, folds: FoldAssignment) -> list[int]:
        """Repeats of the fold assignment that the specification asks for."""
        return [r for r in folds.repeats if r < self._spec.repeats]

    def run(
        self,
        development: pd.DataFrame,
        folds: FoldAssignment,
        experiments: list[Experiment],
        repeats: list[int] | None = None,
    ) -> CVResults:
        """Run every experiment on every (repeat, fold) and collect the results."""
        development = self._builder.derive(development).reset_index(drop=True)
        tasks = [
            (experiment, repeat, fold, train, test)
            for experiment in experiments
            for repeat in (repeats if repeats is not None else self._repeats(folds))
            for fold, (train, test) in enumerate(folds.splits(development, repeat))
        ]
        outputs = Parallel(n_jobs=self._n_jobs)(
            delayed(self._fold)(development, train, test, experiment, repeat, fold)
            for experiment, repeat, fold, train, test in tasks
        )
        oof = pd.concat([o for o, _ in outputs], ignore_index=True)
        metrics = pd.DataFrame([m for _, m in outputs])
        return CVResults(development, oof, metrics)
