"""The research tables written by load-db, one test per table, on a temporary database."""

import json

import pandas as pd
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from antenatal.paths import ProjectPaths
from antenatal.storage import load_database


@pytest.fixture(scope="module")
def database(root, tmp_path_factory):
    url = f"sqlite:///{tmp_path_factory.mktemp('db') / 'app.sqlite3'}"
    patch = pytest.MonkeyPatch()
    patch.setenv("ANTENATAL_DATABASE_URL", url)
    counts = load_database(ProjectPaths.from_root(root))
    yield create_engine(url), counts
    patch.undo()


def _read(engine, table: str) -> pd.DataFrame:
    return pd.read_sql_table(table, engine)


def test_pregnancy_records_hold_every_released_record(database):
    engine, counts = database
    frame = _read(engine, "pregnancy_records")
    assert counts["pregnancy_records"] == len(frame) == 8817
    assert int(frame["in_analysis_cohort"].sum()) == 3908
    assert int(frame.loc[frame["in_analysis_cohort"], "lbw"].sum()) == 206


def test_visit_measurements_are_unique_per_record_and_visit(database):
    engine, _ = database
    frame = _read(engine, "visit_measurements")
    assert not frame.duplicated(["record_id", "visit_number"]).any()
    assert set(frame["visit_number"]) == {1, 2}
    assert (frame["haemoglobin_missing"] == frame["haemoglobin"].isna()).all()
    with engine.begin() as connection, pytest.raises(IntegrityError):
        connection.execute(
            text(
                "INSERT INTO visit_measurements (record_id, visit_number, haemoglobin_missing) "
                "VALUES (1, 1, 1)"
            )
        )


def test_model_configurations_match_the_frozen_artefacts(database, root):
    engine, _ = database
    frame = _read(engine, "model_configurations").set_index("feature_set")
    primary = json.loads((root / "webapp" / "model" / "version.json").read_text())
    assert frame.loc["C", "artefact_sha256"] == primary["artefact_sha256"]
    assert set(frame.index) == {"B", "C"} and frame["version"].is_unique


def test_evaluation_results_match_the_fold_metrics(database, root):
    engine, _ = database
    frame = _read(engine, "evaluation_results")
    folds = pd.read_csv(root / "outputs" / "tables" / "cv_fold_metrics.csv")
    assert len(frame) == len(folds)
    assert not frame.duplicated(["model", "feature_set", "repeat", "fold"]).any()
    merged = frame.merge(
        folds, on=["model", "feature_set", "repeat", "fold"], suffixes=("", "_csv")
    )
    assert (merged["pr_auc"] - merged["pr_auc_csv"]).abs().max() == 0


def test_load_db_can_run_twice(database, root):
    _, first = database
    assert load_database(ProjectPaths.from_root(root)) == first
