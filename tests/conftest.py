"""Shared fixtures: the raw file and the primary cohort are built once per session."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from antenatal.cohort.builder import Cohort, CohortBuilder
from antenatal.cohort.partition import Partition, PartitionWriter
from antenatal.data.loader import DataLoader

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def raw() -> pd.DataFrame:
    return DataLoader(root=ROOT).load()


@pytest.fixture(scope="session")
def cohort(raw: pd.DataFrame) -> Cohort:
    return CohortBuilder().build(raw)


@pytest.fixture(scope="session")
def sealed(tmp_path_factory: pytest.TempPathFactory, cohort: Cohort) -> tuple[Path, Partition]:
    directory = tmp_path_factory.mktemp("partitions")
    return directory, PartitionWriter(directory).seal_holdout(cohort)
