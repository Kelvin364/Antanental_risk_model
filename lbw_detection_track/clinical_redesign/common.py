"""Shared paths, loaders and interval helpers for the clinical redesign investigation.

Nothing here fits a model. Outcome values are only ever read for the 3,126 development
records of the main study, taken from the served frame, so neither held out list is opened.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
TRACK = HERE.parent
ROOT = TRACK.parent
OUT = HERE / "outputs"
STUDY = TRACK / "target_study" / "outputs"
SOURCE = ROOT / "data" / "maternal_dataset_csv.csv"
for folder in (TRACK, TRACK / "fusion", TRACK / "target_study"):
    sys.path.insert(0, str(folder))

from scoring import interval, resamples  # noqa: E402

SEED, RESAMPLES = 20261111, 2000
VISITS = range(1, 9)
SERVED = ("l2_logistic", "F0")
SELECTED = ("stacking", "F2")
CONFIGS = (SERVED, ("l2_logistic", "F2"), SELECTED, ("random_forest", "F2"))


def header() -> list[str]:
    """Column names of the source file, read without any values."""
    return list(pd.read_csv(SOURCE, nrows=0).columns)


def predictor_fields(columns: list[str]) -> pd.DataFrame:
    """Whole file, the named fields only, as text. Callers never pass an outcome field."""
    raw = pd.read_csv(SOURCE, dtype=str, usecols=["SN", *columns])
    return raw.assign(SN=raw["SN"].astype(int)).set_index("SN").sort_index()


def number(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def development() -> pd.DataFrame:
    """The 3,126 development records with outcome, visit weeks and registration groups."""
    import frames

    return frames.load().served


def stored_scores(model: str, set_name: str, ids: pd.Index) -> pd.DataFrame:
    """Mean out of fold probability and flag rates per record from the target study."""
    stored = pd.read_parquet(STUDY / "nested_predictions.parquet")
    part = stored[(stored["model"] == model) & (stored["set"] == set_name)]
    return part.groupby("record_id")[["p", "flag_t90", "flag_t54"]].mean().loc[ids]


def auc_between(score: np.ndarray, cases: np.ndarray, controls: np.ndarray) -> float:
    """ROC AUC of one case group against one control group, other records ignored."""
    keep = cases | controls
    if cases.sum() == 0 or controls.sum() == 0:
        return float("nan")
    return float(roc_auc_score(cases[keep], score[keep]))


def group_draws(groups: np.ndarray, statistic) -> list:
    """The statistic over group bootstrap resamples, whole registration groups at a time."""
    return [statistic(picks) for picks in resamples(groups, RESAMPLES, SEED)]


def bounds(values: list[float]) -> tuple[float, float]:
    low, high, _ = interval(values)
    return low, high
