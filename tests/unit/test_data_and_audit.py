"""Loader integrity, configuration and the data quality audit of Table 3.3."""

import ast
from pathlib import Path

import pytest

from antenatal.audit.quality import consistency_checks, quality_findings, suspect_field_crosstabs
from antenatal.config import PRIMARY, Range, StudySpec
from antenatal.data.loader import ChecksumMismatch, DataLoader


def test_checksum_mismatch_is_raised(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "maternal_dataset_csv.csv").write_text("SN\n1\n")
    with pytest.raises(ChecksumMismatch):
        DataLoader(root=tmp_path).load()


def test_missing_file_is_reported(tmp_path):
    with pytest.raises(FileNotFoundError):
        DataLoader(root=tmp_path).verify_checksum()


def test_provenance_records_checksum(root):
    provenance = DataLoader(root=root).provenance()
    assert provenance["sha256"] == PRIMARY.data_sha256
    assert provenance["licence"] == "CC BY 4.0"


def test_range_is_inclusive():
    assert Range(1, 6).contains(1) and Range(1, 6).contains(6) and not Range(1, 6).contains(6.01)


def test_variant_changes_only_named_fields():
    variant = PRIMARY.variant("S2", gestational_cutoff=32)
    assert variant.gestational_cutoff == 32 and variant.seed == PRIMARY.seed
    assert isinstance(variant, StudySpec) and PRIMARY.gestational_cutoff == 28


def test_holdout_splits_follow_fraction():
    assert PRIMARY.holdout_splits == 5


def test_quality_findings_match_table_3_3(raw):
    findings = quality_findings(raw).set_index("finding")["count"]
    assert findings["preterm_labour_1 agrees with preterm_labour"] == 8808
    assert findings["labour_at_term_1 agrees with labour_at_term"] == 8530
    key = "miscarriages_or_abortions positive where miscarriages_or_abortions_1 is positive"
    assert findings[key] == 84
    assert findings["Records marked as both term delivery and preterm labour"] == 157
    assert findings["Recorded birth weight above 6 kg"] == 35
    assert findings["Exact duplicate rows ignoring the sequence number"] == 1


def test_suspect_crosstab_preterm(raw):
    table = suspect_field_crosstabs(raw)["preterm_labour_1 by preterm_labour"]
    assert table.loc["yes", "no"] == 0 and table.loc["no", "yes"] == 9


def test_consistency_identical_answers(raw):
    checks = consistency_checks(raw).set_index("check")["count"]
    assert checks["Visit one violence answer identical to visit one substance answer"] == 8817


def test_only_the_gate_reads_holdout_identifiers():
    """No module outside the partition writer and the holdout gate may name the held out file."""
    package = Path(__file__).resolve().parents[2] / "src" / "antenatal"
    allowed = {"partition.py", "holdout.py"}
    offenders = []
    for path in package.rglob("*.py"):
        if path.name in allowed:
            continue
        source = path.read_text()
        names = {n.id for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Name)}
        if "holdout_ids.csv" in source or "HOLDOUT_FILE" in names or "load_holdout" in source:
            offenders.append(path.name)
    assert offenders == []
