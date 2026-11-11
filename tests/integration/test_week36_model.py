"""The week 36 model's sealed test set and locked models stay as they were evaluated.

These checks read record lists and checksums only. No test record is loaded or scored.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

FOLDER = Path(__file__).resolve().parents[2] / "week36_model"
SEALED, LOCKED = FOLDER / "sealed", FOLDER / "locked"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ids(name: str) -> set[int]:
    return set(pd.read_csv(SEALED / f"{name}.csv")["record_id"])


def test_sealed_test_list_matches_its_recorded_checksum():
    recorded = (SEALED / "test_ids.sha256").read_text().split()[0]
    assert _sha256(SEALED / "test_ids.csv") == recorded


def test_test_set_was_evaluated_exactly_once():
    lines = (SEALED / "test_access.log").read_text().strip().splitlines()
    assert len(lines) == 1


def test_development_test_and_quarantine_lists_do_not_overlap():
    development, test = _ids("development_ids"), _ids("test_ids")
    quarantine = _ids("quarantine_ids")
    assert not development & test
    assert not development & quarantine
    assert not test & quarantine


@pytest.mark.parametrize("name", ["A", "B", "C"])
def test_locked_model_files_match_their_recorded_checksums(name):
    locked = json.loads((LOCKED / "locked.json").read_text())
    assert _sha256(LOCKED / f"model_set_{name}.joblib") == locked["models"][name]["sha256"]


def test_locked_choice_is_logistic_set_b_at_week_36():
    locked = json.loads((LOCKED / "locked.json").read_text())
    assert (locked["landmark"], locked["primary_set"], locked["method"]) == (36, "B", "logistic")
