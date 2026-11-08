"""Protocol Section 3: every option rebuilt inside the same outer folds.

Option 1 uses the main study's own fitting code, option 2 this track's, and option 4
learns only from inner scores of outer training records.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from frames import SET_TWO, Frames
from methods import Logistic
from scoring import threshold_for
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold

from antenatal.config import PRIMARY
from antenatal.evaluation.nested_cv import Experiment, NestedCVRunner
from antenatal.features.builder import FeatureBuilder
from antenatal.features.sets import SetC

SEED = 20261108
REPEATS, FOLDS, INNER = 5, 5, 5
BUDGET = 0.20
SERVED = Experiment("logistic_l2", SetC())


def logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def top_share(p: np.ndarray, share: float = BUDGET) -> float:
    """The served model's rule: the score that marks the highest ``share`` of records."""
    return float(np.sort(p)[::-1][int(np.ceil(share * len(p))) - 1])


def splits(frame: pd.DataFrame, folds: int, seed: int):
    """Grouped stratified folds; refuses any split where a registration group crosses."""
    y, groups = frame["lbw"].to_numpy(), frame["group_key_hash"].to_numpy()
    for train, test in StratifiedGroupKFold(folds, shuffle=True, random_state=seed).split(
        frame, y, groups
    ):
        if set(groups[train]) & set(groups[test]):
            raise RuntimeError("A registration group crosses a fold.")
        yield frame.index[train], frame.index[test]


class Bases:
    """Option 1 and option 2 fitted on one set of training records."""

    def __init__(self, frames: Frames, train: pd.Index, blocked: set[str], seed: int) -> None:
        served, week36 = frames.served, frames.week36
        frames.guard.check(served.loc[train])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.one = NestedCVRunner(frames.guard, PRIMARY, n_jobs=1).fit(
                served.loc[train], SERVED, seed
            )
            outside = served.index.difference(train)
            keep = ~week36.index.isin(outside) & ~week36["group"].isin(blocked)
            two = week36[keep]
            if frames.guard.blocked & set(two.index) or set(two["group"]) & blocked:
                raise RuntimeError("Option 2 training touched a test record or group.")
            self.two = Logistic().fit(
                two[SET_TWO].to_numpy(float), two["lbw"].to_numpy(), two["group"].to_numpy()
            )
            self.trained_on = len(two)

    def score(self, frames: Frames, ids: pd.Index) -> tuple[np.ndarray, np.ndarray]:
        x = FeatureBuilder.matrix(frames.served.loc[ids], self.one.columns)
        p1 = self.one.pipeline.predict_proba(x)[:, 1]
        p2 = np.full(len(ids), np.nan)
        seen = ids.isin(frames.week36.index)
        if seen.any():
            rows = frames.week36.loc[ids[seen], SET_TWO].to_numpy(float)
            p2[seen] = self.two.predict_proba(rows)[:, 1]
        return p1, p2


def stack_inputs(p1: np.ndarray, p2: np.ndarray) -> np.ndarray:
    has = ~np.isnan(p2)
    return np.column_stack([logit(p1), has.astype(float), np.where(has, logit(p2), 0.0)])


def average(p1: np.ndarray, p2: np.ndarray) -> np.ndarray:
    """Exploratory: mean log odds where both scores exist, otherwise option 1."""
    mean = (logit(p1) + logit(np.where(np.isnan(p2), p1, p2))) / 2
    return np.where(np.isnan(p2), p1, 1 / (1 + np.exp(-mean)))


def inner_scores(frames, train, outer_groups, seed):
    """Honest scores of every outer training record from both base models."""
    p1, p2 = pd.Series(np.nan, index=train), pd.Series(np.nan, index=train)
    for inner_train, inner_test in splits(frames.served.loc[train], INNER, seed):
        groups = set(frames.served.loc[inner_test, "group_key_hash"]) | outer_groups
        bases = Bases(frames, inner_train, groups, seed)
        p1.loc[inner_test], p2.loc[inner_test] = bases.score(frames, inner_test)
    if p1.isna().any():
        raise RuntimeError("An outer training record has no inner score.")
    return p1.to_numpy(), p2.to_numpy()


def rules(y: np.ndarray, p1: np.ndarray, p2: np.ndarray):
    """The stacker and every threshold, learnt from inner scores only (step 2.5)."""
    stacker = LogisticRegression(C=1e9, max_iter=5000).fit(stack_inputs(p1, p2), y)
    p4 = stacker.predict_proba(stack_inputs(p1, p2))[:, 1]
    has = ~np.isnan(p2)
    return stacker, {
        "t1": top_share(p1),
        "t2": threshold_for(y[has], p2[has]),
        "t4_20": top_share(p4),
        "t4_75": threshold_for(y, p4),
        "t_avg": top_share(average(p1, p2)),
    }


def outer_fold(frames: Frames, repeat: int, fold: int, train, test) -> pd.DataFrame:
    seed = SEED + repeat
    outer_groups = set(frames.served.loc[test, "group_key_hash"])
    y_train = frames.served.loc[train, "lbw"].to_numpy()
    stacker, t = rules(y_train, *inner_scores(frames, train, outer_groups, seed))
    bases = Bases(frames, train, outer_groups, seed)
    p1, p2 = bases.score(frames, test)
    p4, pa = stacker.predict_proba(stack_inputs(p1, p2))[:, 1], average(p1, p2)
    f1, f2 = p1 >= t["t1"], np.nan_to_num(p2, nan=-1.0) >= t["t2"]
    return pd.DataFrame(
        {
            "record_id": test, "repeat": repeat, "fold": fold,
            "p1": p1, "p2": p2, "p4": p4, "p_avg": pa,
            "flag1": f1, "flag2": f2, "flag3": f1 | f2,
            "flag4_20": p4 >= t["t4_20"], "flag4_75": p4 >= t["t4_75"],
            "flag_avg": pa >= t["t_avg"],
            "stack_w1": stacker.coef_[0, 0], "stack_has2": stacker.coef_[0, 1],
            "stack_w2": stacker.coef_[0, 2], "two_trained_on": bases.trained_on,
            **{f"threshold_{k}": v for k, v in t.items()},
        }
    )  # fmt: skip


def tasks(frames: Frames, repeats: int = REPEATS):
    for repeat in range(repeats):
        for fold, (train, test) in enumerate(splits(frames.served, FOLDS, SEED + repeat)):
            yield repeat, fold, train, test
