"""Experiment 2.8: how the models use their inputs, reported as model behaviour, not cause.

Standardised coefficients of the served logistic model come with group bootstrap
intervals from refits on resampled development records with the served model's
penalty. Permutation importance is the fall in average precision when one input is
shuffled in an outer test fold, using that fold's own fitted model, for both
families on set C, averaged over all 50 folds.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.base import clone
from sklearn.inspection import permutation_importance

from antenatal.artefact.artefact import FittedPipelineArtefact
from antenatal.config import PRIMARY, StudySpec
from antenatal.evaluation.bootstrap import GroupBootstrap
from antenatal.evaluation.nested_cv import Experiment, NestedCVRunner
from antenatal.features.builder import FeatureBuilder
from antenatal.features.sets import SetC
from antenatal.study import StudyContext

LABEL = "model behaviour, not cause"


def coefficients(
    artefact: FittedPipelineArtefact, development: pd.DataFrame, spec: StudySpec = PRIMARY
) -> pd.DataFrame:
    """Standardised coefficients with 95 percent group bootstrap intervals."""
    x = FeatureBuilder.matrix(FeatureBuilder().derive(development), artefact.feature_names)
    y = development["lbw"].to_numpy()
    names = artefact.pipeline[:-1].get_feature_names_out(artefact.feature_names)
    boot = GroupBootstrap(development["group_key"].to_numpy(), spec.bootstrap_resamples, spec.seed)
    draws = []
    for index in boot.indices():
        if 0 < y[index].sum() < len(index):
            refit = clone(artefact.pipeline).fit(x.iloc[index], y[index])
            # A resample without missing values in a column has no indicator for it,
            # so coefficients are matched by name, not position.
            drawn = dict(zip(refit[:-1].get_feature_names_out(), refit[-1].coef_[0], strict=True))
            draws.append([drawn.get(name, np.nan) for name in names])
    draws = np.asarray(draws, dtype=float)
    return pd.DataFrame(
        {
            "input": names,
            "coefficient": artefact.pipeline[-1].coef_[0],
            "ci_low": np.nanpercentile(draws, 2.5, axis=0),
            "ci_high": np.nanpercentile(draws, 97.5, axis=0),
            "resamples_with_input": np.sum(~np.isnan(draws), axis=0),
            "label": LABEL,
        }
    )


def _fold_importance(runner, development, train_idx, test_idx, model, repeat, fold, seed):
    train, test = development.iloc[train_idx], development.iloc[test_idx]
    fitted = runner.fit(train, Experiment(model, SetC()), seed + repeat)
    x_test = FeatureBuilder.matrix(test, fitted.columns)
    result = permutation_importance(
        fitted.pipeline,
        x_test,
        test["lbw"].to_numpy(),
        scoring="average_precision",
        n_repeats=10,
        random_state=seed,
    )
    return pd.DataFrame(
        {
            "model": model,
            "repeat": repeat,
            "fold": fold,
            "input": fitted.columns,
            "drop": result.importances_mean,
        }
    )


def permutation_table(context: StudyContext, spec: StudySpec = PRIMARY) -> pd.DataFrame:
    """Mean and spread over the 50 folds of each input's permutation importance."""
    runner = NestedCVRunner(context.partition.guard(), spec, n_jobs=1)
    development = FeatureBuilder().derive(context.development).reset_index(drop=True)
    tasks = [
        (model, repeat, fold, train, test)
        for model in ("logistic_l2", "gradient_boosting")
        for repeat in range(spec.repeats)
        for fold, (train, test) in enumerate(context.folds.splits(development, repeat))
    ]
    parts = Parallel(n_jobs=-1)(
        delayed(_fold_importance)(runner, development, tr, te, m, r, f, spec.seed)
        for m, r, f, tr, te in tasks
    )
    folds = pd.concat(parts, ignore_index=True)
    table = folds.groupby(["model", "input"])["drop"].agg(["mean", "std", "count"]).reset_index()
    return table.rename(
        columns={"mean": "ap_drop_mean", "std": "ap_drop_sd", "count": "folds"}
    ).assign(label=LABEL)
