"""Learning curve: is the null result limited by the amount of data?

Algorithm. For each training fraction and each repeat of the sealed outer
folds, every outer training fold is reduced to that fraction of its
registration groups (chosen at random with the repeat's seed, so groups stay
whole), the model is tuned and fitted on the reduced fold exactly as in the
primary design, and the full outer test fold is predicted. Out of fold
predictions are pooled per repeat for the mean and spread across repeats, and
averaged per pregnancy across repeats for a group bootstrap 95 percent
interval on each set and on the paired gap between sets C and B (R6). If the
gap stays flat as the training data grows, more data of this kind is unlikely
to reveal a difference.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from antenatal.cohort.partition import FoldAssignment
from antenatal.config import PRIMARY, StudySpec
from antenatal.evaluation.bootstrap import GroupBootstrap
from antenatal.evaluation.metrics import AveragePrecision, RocAuc, average_precision, roc_auc
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


@dataclass
class LearningCurveResult:
    """Metrics per repeat, and predictions averaged per pregnancy across repeats."""

    by_repeat: pd.DataFrame
    predictions: pd.DataFrame


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
    ) -> LearningCurveResult:
        """Metrics per fraction, set and repeat, and averaged predictions for intervals."""
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
        return LearningCurveResult(_pool(parts), _average(parts, development))


def _average(parts: list[dict], development: pd.DataFrame) -> pd.DataFrame:
    """Probability per record averaged across repeats, with outcome and group."""
    frame = pd.DataFrame(parts).explode(["record_id", "lbw", "probability"])
    frame = frame.astype({"record_id": int, "lbw": int, "probability": float})
    keys = ["fraction", "feature_set", "record_id"]
    mean = frame.groupby(keys, as_index=False).agg(
        lbw=("lbw", "first"), probability=("probability", "mean")
    )
    groups = development.set_index("record_id")["group_key"]
    return mean.assign(group_key=mean["record_id"].map(groups))


def intervals(predictions: pd.DataFrame, spec: StudySpec = PRIMARY) -> pd.DataFrame:
    """Group bootstrap intervals per fraction for sets B and C and for C minus B."""
    rows = []
    for fraction, block in predictions.groupby("fraction"):
        wide = block.pivot_table(
            index=["record_id", "lbw", "group_key"], columns="feature_set", values="probability"
        ).reset_index()
        y = wide["lbw"].to_numpy()
        bootstrap = GroupBootstrap(
            wide["group_key"].to_numpy(), spec.bootstrap_resamples, spec.seed
        )
        row: dict[str, float] = {"fraction": fraction}
        for metric in (AveragePrecision(), RocAuc()):
            for name in ("B", "C"):
                i = bootstrap.single(y, wide[name].to_numpy(), metric)
                row.update(
                    {
                        f"{metric.name}_{name}_pooled": i.estimate,
                        f"{metric.name}_{name}_low": i.low,
                        f"{metric.name}_{name}_high": i.high,
                    }
                )
            gap = bootstrap.paired_difference(y, wide["C"].to_numpy(), wide["B"].to_numpy(), metric)
            row.update(
                {
                    f"{metric.name}_gap_pooled": gap.estimate,
                    f"{metric.name}_gap_low": gap.low,
                    f"{metric.name}_gap_high": gap.high,
                }
            )
        rows.append(row)
    return pd.DataFrame(rows)


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


def summarise(curve: pd.DataFrame, interval_table: pd.DataFrame | None = None) -> pd.DataFrame:
    """Mean and spread across repeats, the C minus B gap, and bootstrap intervals beside them."""
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
    summary = summary.merge(gap.reset_index(), on="fraction")
    if interval_table is None:
        return summary
    return summary.merge(_long_intervals(interval_table), on=["fraction", "feature_set"])


def _long_intervals(table: pd.DataFrame) -> pd.DataFrame:
    """One row per fraction and set: that set's intervals plus the shared gap interval."""
    rows = []
    for row in table.to_dict("records"):
        shared = {k: v for k, v in row.items() if "_gap_" in k}
        for name in ("B", "C"):
            own = {k.replace(f"_{name}_", "_"): v for k, v in row.items() if f"_{name}_" in k}
            rows.append({"fraction": row["fraction"], "feature_set": name, **own, **shared})
    return pd.DataFrame(rows)
