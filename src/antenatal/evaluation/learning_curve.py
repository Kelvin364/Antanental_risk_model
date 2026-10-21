"""Learning curve: is the null result limited by the amount of data?

Algorithm. For each training fraction and each repeat of the sealed outer
folds, every outer training fold is reduced to that fraction of its
registration groups (chosen at random with the repeat's seed, so groups stay
whole), the model is tuned and fitted on the reduced fold exactly as in the
primary design, and the full outer test fold is predicted. Out of fold
predictions are pooled per repeat. If the gap between sets B and C stays flat
as the training data grows, more data of this kind is unlikely to reveal a
difference.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from antenatal.cohort.partition import FoldAssignment
from antenatal.config import PRIMARY, StudySpec
from antenatal.evaluation.metrics import average_precision, roc_auc
from antenatal.evaluation.nested_cv import Experiment, NestedCVRunner
from antenatal.features.builder import FeatureBuilder

FRACTIONS = (0.2, 0.4, 0.6, 0.8, 1.0)


def subsample_groups(train: pd.DataFrame, fraction: float, seed: int) -> pd.DataFrame:
    """Keep a random ``fraction`` of the registration groups in ``train``, groups whole."""
    if fraction >= 1:
        return train
    groups = train["group_key"].unique()
    rng = np.random.default_rng(seed)
    keep = rng.permutation(groups)[: int(np.ceil(fraction * len(groups)))]
    return train[train["group_key"].isin(keep)]


class LearningCurve:
    """Runs the learning curve for a list of experiments."""

    def __init__(self, spec: StudySpec = PRIMARY, n_jobs: int = -1) -> None:
        self._spec = spec
        self._runner = NestedCVRunner(spec, n_jobs=1)
        self._n_jobs = n_jobs

    def _task(self, development, train_idx, test_idx, experiment, repeat, fraction):
        seed = self._spec.seed + repeat
        train = subsample_groups(development.iloc[train_idx], fraction, seed)
        fitted = self._runner.fit(train, experiment, seed)
        test = development.iloc[test_idx]
        p = fitted.pipeline.predict_proba(FeatureBuilder.matrix(test, fitted.columns))[:, 1]
        return {
            "fraction": fraction,
            "feature_set": experiment.feature_set.name,
            "repeat": repeat,
            "record_id": test["record_id"].to_numpy(),
            "lbw": test["lbw"].to_numpy(),
            "probability": p,
            "n_train": len(train),
            "events_train": int(train["lbw"].sum()),
        }

    def run(
        self, development: pd.DataFrame, folds: FoldAssignment, experiments: list[Experiment]
    ) -> pd.DataFrame:
        """One row per fraction, feature set and repeat with pooled out of fold metrics."""
        development = FeatureBuilder().derive(development).reset_index(drop=True)
        repeats = [r for r in folds.repeats if r < self._spec.repeats]
        tasks = [
            (train, test, experiment, repeat, fraction)
            for fraction in FRACTIONS
            for experiment in experiments
            for repeat in repeats
            for train, test in folds.splits(development, repeat)
        ]
        parts = Parallel(n_jobs=self._n_jobs)(
            delayed(self._task)(development, *task) for task in tasks
        )
        return _pool(parts)


def _pool(parts: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(parts)
    rows = []
    for (fraction, feature_set, repeat), block in frame.groupby(
        ["fraction", "feature_set", "repeat"]
    ):
        y = np.concatenate(block["lbw"].to_list())
        p = np.concatenate(block["probability"].to_list())
        rows.append(
            {
                "fraction": fraction,
                "feature_set": feature_set,
                "repeat": repeat,
                "n_train_mean": float(block["n_train"].mean()),
                "events_train_mean": float(block["events_train"].mean()),
                "pr_auc": average_precision(y, p),
                "roc_auc": roc_auc(y, p),
            }
        )
    return pd.DataFrame(rows)


def summarise(curve: pd.DataFrame) -> pd.DataFrame:
    """Mean and spread across repeats, and the C minus B gap per repeat summarised."""
    summary = (
        curve.groupby(["fraction", "feature_set"])
        .agg(
            n_train=("n_train_mean", "mean"),
            events_train=("events_train_mean", "mean"),
            pr_auc_mean=("pr_auc", "mean"),
            pr_auc_sd=("pr_auc", "std"),
            roc_auc_mean=("roc_auc", "mean"),
            roc_auc_sd=("roc_auc", "std"),
        )
        .reset_index()
    )
    wide = curve.pivot_table(
        index=["fraction", "repeat"], columns="feature_set", values=["pr_auc", "roc_auc"]
    )
    gap = (
        pd.DataFrame(
            {
                "pr_auc_gap": wide[("pr_auc", "C")] - wide[("pr_auc", "B")],
                "roc_auc_gap": wide[("roc_auc", "C")] - wide[("roc_auc", "B")],
            }
        )
        .groupby(level="fraction")
        .agg(["mean", "std"])
    )
    gap.columns = [f"{a}_{b}" for a, b in gap.columns]
    return summary.merge(gap.reset_index(), on="fraction")
