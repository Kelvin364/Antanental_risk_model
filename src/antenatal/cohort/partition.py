"""The sealed held out partition and the grouped outer folds (Section 3.3.7).

Algorithm. Grouped stratified partitioning assigns whole registration groups
to folds so that no group is split, while balancing the number of events per
fold (scikit-learn ``StratifiedGroupKFold``, shuffled with the study seed). The
first of five such folds is the held out partition, about 20 percent of the
analysis cohort. It is written to file with a SHA 256 before any screen, model
choice or cross validation step, and the writer refuses to overwrite it.

The ``Partition`` object only exposes development records. The held out
records can be read only through ``evaluation.holdout.HoldoutEvaluator``, and
their predictors (never their outcome) through ``holdout_predictors`` for the
integrity audit. ``TrainingGuard`` is required by every model fit and refuses
any training frame that contains a held out record (decision D7).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

from antenatal.cohort.builder import Cohort
from antenatal.config import PRIMARY, StudySpec

HOLDOUT_FILE = "holdout_ids.csv"
HOLDOUT_CHECKSUM = "holdout.sha256"
FOLDS_FILE = "folds.parquet"


class PartitionAlreadySealed(RuntimeError):
    """Raised when sealing would overwrite an existing held out partition."""


class PartitionTampered(RuntimeError):
    """Raised when the held out file no longer matches its recorded SHA 256."""


class HoldoutLeak(RuntimeError):
    """Raised when a frame about to be used for training contains a held out record."""


@dataclass(frozen=True)
class TrainingGuard:
    """Refuses training data that contains any held out record (decision D7)."""

    blocked: frozenset[int]
    armed: bool = True

    @classmethod
    def unarmed(cls) -> TrainingGuard:
        """For tests on synthetic data without a sealed partition; never used by the study."""
        return cls(frozenset(), armed=False)

    def check(self, frame: pd.DataFrame) -> None:
        """Raise ``HoldoutLeak`` if any record of ``frame`` is a held out record."""
        if not self.armed:
            return
        leaked = int(frame["record_id"].isin(self.blocked).sum())
        if leaked:
            raise HoldoutLeak(f"{leaked} held out records reached a training step; refused")


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True)
class Partition:
    """The sealed split of the analysis cohort, exposing development records only."""

    holdout_ids: frozenset[int]
    sha256: str

    @property
    def holdout_size(self) -> int:
        """Number of sealed held out records, without exposing which they are."""
        return len(self.holdout_ids)

    def guard(self) -> TrainingGuard:
        """The guard every model fit must carry."""
        return TrainingGuard(self.holdout_ids)

    def holdout_predictors(self, cohort: Cohort, columns: list[str]) -> pd.DataFrame:
        """Held out predictor values for the integrity audit; the outcome is never returned."""
        forbidden = {"lbw", "birth_weight_kg", "live_birth", "multiple_delivery"}
        if forbidden & set(columns):
            raise ValueError("the integrity audit may not read outcome columns")
        frame = cohort.analysis
        held = frame[frame["record_id"].isin(self.holdout_ids)]
        return held[["record_id", "group_key", *columns]].reset_index(drop=True)

    def development(self, cohort: Cohort) -> pd.DataFrame:
        """Analysis cohort records that are not in the held out partition."""
        frame = cohort.analysis
        return frame[~frame["record_id"].isin(self.holdout_ids)].reset_index(drop=True)


@dataclass(frozen=True)
class FoldAssignment:
    """Outer fold of every development record in every repeat."""

    table: pd.DataFrame

    def splits(self, development: pd.DataFrame, repeat: int):
        """Yield (train positions, test positions) for each outer fold of ``repeat``."""
        rows = self.table[self.table["repeat"] == repeat].set_index("record_id")["fold"]
        folds = development["record_id"].map(rows).to_numpy()
        for fold in np.unique(folds):
            yield np.flatnonzero(folds != fold), np.flatnonzero(folds == fold)

    @property
    def repeats(self) -> list[int]:
        """Repeat numbers present in the assignment."""
        return sorted(self.table["repeat"].unique().tolist())


def grouped_outer_folds(development: pd.DataFrame, spec: StudySpec = PRIMARY) -> FoldAssignment:
    """Grouped stratified outer folds for every repeat, seeded with ``spec.seed + repeat``."""
    rows = []
    for repeat in range(spec.repeats):
        splitter = StratifiedGroupKFold(
            n_splits=spec.outer_folds, shuffle=True, random_state=spec.seed + repeat
        )
        split = splitter.split(development, development["lbw"], development["group_key"])
        for fold, (_, test) in enumerate(split):
            ids = development["record_id"].iloc[test]
            rows.append(pd.DataFrame({"record_id": ids, "repeat": repeat, "fold": fold}))
    table = pd.concat(rows, ignore_index=True)
    return FoldAssignment(table.sort_values(["repeat", "record_id"], ignore_index=True))


class PartitionWriter:
    """Seals the held out partition and writes the outer fold assignment."""

    def __init__(self, directory: Path, spec: StudySpec = PRIMARY) -> None:
        self._dir = Path(directory)
        self._spec = spec

    @property
    def holdout_path(self) -> Path:
        """Path of the sealed held out identifiers."""
        return self._dir / HOLDOUT_FILE

    def seal_holdout(self, cohort: Cohort) -> Partition:
        """Draw, write and checksum the held out partition; refuse if one exists."""
        if self.holdout_path.exists():
            raise PartitionAlreadySealed(f"{self.holdout_path} exists and is never regenerated")
        frame = cohort.analysis
        splitter = StratifiedGroupKFold(
            n_splits=self._spec.holdout_splits, shuffle=True, random_state=self._spec.seed
        )
        _, held = next(splitter.split(frame, frame["lbw"], frame["group_key"]))
        ids = sorted(frame["record_id"].iloc[held].astype(int).tolist())
        self._dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({"record_id": ids}).to_csv(self.holdout_path, index=False)
        digest = _digest(self.holdout_path)
        (self._dir / HOLDOUT_CHECKSUM).write_text(f"{digest}  {HOLDOUT_FILE}\n")
        return Partition(frozenset(ids), digest)

    def load(self) -> Partition:
        """Read the sealed identifiers after verifying their SHA 256."""
        if not self.holdout_path.exists():
            raise FileNotFoundError(
                f"No sealed partition at {self.holdout_path}; run seal-partition"
            )
        expected = (self._dir / HOLDOUT_CHECKSUM).read_text().split()[0]
        digest = _digest(self.holdout_path)
        if digest != expected:
            raise PartitionTampered(f"{self.holdout_path} changed: {digest} != {expected}")
        ids = pd.read_csv(self.holdout_path)["record_id"].astype(int)
        return Partition(frozenset(ids.tolist()), digest)

    def outer_folds(self, development: pd.DataFrame) -> FoldAssignment:
        """Assign development records to grouped stratified folds for every repeat."""
        return grouped_outer_folds(development, self._spec)

    def write_folds(self, folds: FoldAssignment) -> Path:
        """Write the fold assignment; an existing file must hold identical content."""
        path = self._dir / FOLDS_FILE
        if path.exists():
            existing = pd.read_parquet(path)
            if not existing.equals(folds.table):
                raise PartitionAlreadySealed(f"{path} exists with a different assignment")
            return path
        folds.table.to_parquet(path, index=False)
        return path

    def load_folds(self) -> FoldAssignment:
        """Read the fold assignment written by ``write_folds``."""
        return FoldAssignment(pd.read_parquet(self._dir / FOLDS_FILE))
