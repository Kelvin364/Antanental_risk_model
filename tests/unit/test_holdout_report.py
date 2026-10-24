"""The held out results page is generated from saved files and proves independence."""

import pytest

from antenatal.paths import ProjectPaths
from antenatal.reporting.holdout_report import _worse, write_holdout_report


def test_the_held_out_page_fills_every_section(root, tmp_path):
    paths = ProjectPaths.from_root(root)
    if not (paths.partitions / "holdout_access.log").exists():
        pytest.fail("The held out evaluation has been run; its log must be committed")
    text = write_holdout_report(paths, target=tmp_path / "holdout.md")
    assert "{" not in text and "}" not in text
    for heading in ("Proof that the model did not learn", "Reading the results", "label"):
        assert heading in text
    assert "11 of 11 checks passed" in text and "after the run 11 of 11 passed" in text
    assert "1 evaluation" in text


def test_worse_is_judged_by_where_each_measure_is_best():
    assert _worse("roc_auc", 0.55, 0.62)
    assert not _worse("brier", 0.04, 0.05)
    assert _worse("calibration_slope", 0.45, 0.98)
    assert not _worse("calibration_slope", 1.1, 1.3)
