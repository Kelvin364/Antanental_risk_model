"""The Stage 1 implementation audit is generated from files, with every section filled."""

import pandas as pd

from antenatal.paths import ProjectPaths
from antenatal.reporting.audit_report import write_audit_report


def test_audit_report_fills_every_section(root):
    text = write_audit_report(ProjectPaths.from_root(root))
    assert "{" not in text and "}" not in text
    for heading in (
        "Baseline",
        "Leakage review",
        "Population and applicability",
        "Predictor quality",
    ):
        assert heading in text
    assert "| Prior deliveries at or above number of pregnancies | 4,881 | 8,817 |" in text
    assert "not found" not in text  # every cited code line still exists


def test_feature_quality_covers_every_predictor_and_exclusion(root):
    table = pd.read_csv(root / "outputs" / "tables" / "feature_quality.csv")
    assert len(table) == 14 + 12 + 7
    assert set(table.loc[table["used"] == "no", "predictor"]) >= {"preterm_labour_1", "hb_v1"}
    groups = pd.read_csv(root / "outputs" / "tables" / "group_integrity.csv").set_index("check")
    assert groups.loc["Records in the analysis cohort", "count"] == 3908
