"""The two record frames of the fusion analysis, built without opening the held out list.

The main study's development records are taken from the record ids of its stored out of
fold predictions, so ``partitions/holdout_ids.csv`` is never read. The week 36 frame
comes from this track's development pool.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

TRACK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TRACK))

from features import ROOT, SETS, at_landmark, load_raw  # noqa: E402

from antenatal.cohort.builder import CohortBuilder  # noqa: E402
from antenatal.cohort.partition import TrainingGuard  # noqa: E402
from antenatal.config import PRIMARY  # noqa: E402
from antenatal.data.loader import DataLoader  # noqa: E402
from antenatal.features.builder import FeatureBuilder  # noqa: E402

LANDMARK = 36
SET_TWO = SETS["B"]
SEALED = TRACK / "sealed"


def sealed_ids(name: str) -> set[int]:
    return set(pd.read_csv(SEALED / f"{name}.csv")["record_id"].astype(int))


def forbidden_ids() -> frozenset[int]:
    """Quarantined records (the old held out set plus one) and this track's test set."""
    return frozenset(sealed_ids("quarantine_ids") | sealed_ids("test_ids"))


@dataclass
class Frames:
    """``served``: 3,126 development records, one row each, indexed by record id.
    ``week36``: every development pool record with a usable visit in weeks 33 to 36."""

    served: pd.DataFrame
    week36: pd.DataFrame
    guard: TrainingGuard

    @property
    def has_two(self) -> np.ndarray:
        return self.served.index.isin(self.week36.index)


def served_frame() -> pd.DataFrame:
    ids = set(pd.read_parquet(ROOT / "outputs/oof_predictions.parquet")["record_id"])
    raw = DataLoader(PRIMARY, ROOT).load()
    analysis = CohortBuilder(PRIMARY).build(raw).analysis
    frame = FeatureBuilder().derive(analysis[analysis["record_id"].isin(ids)])
    manifest = pd.read_csv(
        ROOT / "outputs/cohort_manifest.csv", usecols=["record_id", "group_key_hash"]
    )
    frame = frame.merge(manifest, on="record_id", how="left", validate="one_to_one")
    return frame.set_index("record_id", drop=False).sort_index()


def week36_frame() -> pd.DataFrame:
    raw = load_raw(pd.Series(sorted(sealed_ids("development_ids"))))
    return at_landmark(raw, LANDMARK).sort_index()


def check(frames: Frames) -> dict[str, int]:
    """Counts and the integrity assertions of protocol Sections 2 and 6."""
    served, week36, blocked = frames.served, frames.week36, frames.guard.blocked
    if blocked & set(served.index) or blocked & set(week36.index):
        raise RuntimeError("A quarantined or test record is in a fusion frame.")
    keys = served.groupby("group_key")["group_key_hash"].nunique().max()
    hashes = served.groupby("group_key_hash")["group_key"].nunique().max()
    if keys != 1 or hashes != 1:
        raise RuntimeError("Registration group keys and their hashes do not match one to one.")
    shared = served.index.intersection(week36.index)
    if not (served.loc[shared, "lbw"].to_numpy() == week36.loc[shared, "lbw"].to_numpy()).all():
        raise RuntimeError("The two frames disagree on an outcome.")
    extra = week36.index.difference(served.index)
    return {
        "served_records": len(served),
        "served_events": int(served["lbw"].sum()),
        "with_week36_visit": len(shared),
        "with_week36_visit_events": int(served.loc[shared, "lbw"].sum()),
        "extra_week36_training_records": len(extra),
        "extra_week36_training_events": int(week36.loc[extra, "lbw"].sum()),
    }


def load() -> Frames:
    return Frames(served_frame(), week36_frame(), TrainingGuard(forbidden_ids()))
