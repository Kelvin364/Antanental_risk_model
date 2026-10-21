"""Command line outputs and the missingness summaries."""

import math

import pandas as pd
import pytest

from antenatal.audit.missingness import missingness_mechanism, missingness_table, wilson_interval
from antenatal.audit.quality import non_numeric_tokens, registration_ranges
from antenatal.cli import main


@pytest.fixture(scope="module")
def project(tmp_path_factory, root):
    """A throwaway project root that links to the real data file."""
    project = tmp_path_factory.mktemp("project")
    (project / "data").mkdir()
    (project / "data" / "maternal_dataset_csv.csv").symlink_to(
        root / "data" / "maternal_dataset_csv.csv"
    )
    main(["derive-cohort", "--root", str(project)])
    main(["seal-partition", "--root", str(project)])
    return project


def test_derive_cohort_writes_manifest_and_flow(project):
    manifest = pd.read_csv(project / "outputs" / "cohort_manifest.csv")
    flow = pd.read_csv(project / "outputs" / "tables" / "cohort_flow.csv")
    assert len(manifest) == 8817
    assert flow["remaining"].tolist() == [8817, 8609, 8193, 8161, 7994, 6203, 6065, 3908]


def test_seal_partition_writes_files(project):
    partitions = project / "partitions"
    assert len(pd.read_csv(partitions / "holdout_ids.csv")) == 782
    assert (partitions / "holdout.sha256").read_text().split()[1] == "holdout_ids.csv"
    assert len(pd.read_parquet(partitions / "folds.parquet")) == 3126 * 10


def test_seal_partition_is_repeatable_without_regenerating(project):
    before = (project / "partitions" / "holdout.sha256").read_text()
    main(["seal-partition", "--root", str(project)])
    assert (project / "partitions" / "holdout.sha256").read_text() == before


def test_wilson_interval_known_value():
    low, high = wilson_interval(10, 100)
    assert low == pytest.approx(0.0552, abs=1e-4) and high == pytest.approx(0.1744, abs=1e-4)
    assert all(math.isnan(v) for v in wilson_interval(0, 0))


def test_missingness_on_development(cohort, sealed):
    development = sealed[1].development(cohort)
    table = missingness_table(development)
    assert set(table["visit"]) == {1, 2}
    blood_pressure = table[table["measurement"] == "sbp"]["percent_missing"]
    assert (blood_pressure == 0).all()
    mechanism = missingness_mechanism(development)
    assert mechanism.groupby("measurement")["n"].sum().eq(len(development)).all()


def test_token_audit_finds_sentinels(raw):
    tokens = non_numeric_tokens(raw)
    assert tokens.loc[tokens["token"] == "not_checked", "treated_as_missing"].all()
    assert tokens.loc[tokens["token"] == "36.5.", "repaired_as_number"].all()


def test_registration_ranges_show_implausible_values(raw):
    ranges = registration_ranges(raw).set_index("field")
    assert ranges.loc["age", "maximum"] == 121 and ranges.loc["height, cm", "minimum"] == 0
