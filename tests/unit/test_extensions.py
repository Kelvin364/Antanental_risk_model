"""Stage 5: methods on toy data, and the shape of every output file."""

import json

import numpy as np
import pandas as pd
import pytest

from antenatal.artefact.artefact import FittedPipelineArtefact
from antenatal.evaluation.learning_curve import FRACTIONS, subsample_groups
from antenatal.evaluation.missingness_signal import newcombe_difference
from antenatal.extensions import POOLED, pool_imputations
from antenatal.models.factory import ITERATIVE_MODELS

TABLES = "outputs/tables"


def test_newcombe_interval_contains_difference():
    d, low, high = newcombe_difference(10, 100, 30, 150)
    assert d == pytest.approx(0.1 - 0.2)
    assert low < d < high
    assert all(np.isnan(v) for v in newcombe_difference(1, 0, 1, 10))


def test_subsample_keeps_groups_whole():
    train = pd.DataFrame({"group_key": list("aabbccddee"), "lbw": [0] * 10})
    kept = subsample_groups(train, 0.4, seed=1)
    assert kept["group_key"].nunique() == 2 and len(kept) == 4
    assert subsample_groups(train, 1.0, seed=1) is train


def test_pooling_averages_the_five_imputations():
    rows = [
        {"record_id": 1, "feature_set": "C", "repeat": 0, "fold": 0, "model": m, "probability": p}
        for m, p in zip(ITERATIVE_MODELS, [0.1, 0.2, 0.3, 0.4, 0.5], strict=True)
    ]
    pooled = pool_imputations(pd.DataFrame(rows))
    assert pooled.loc[pooled["model"] == POOLED, "probability"].item() == pytest.approx(0.3)


def _table(root, name):
    return pd.read_csv(root / TABLES / f"{name}.csv")


def test_learning_curve_shape(root):
    table = _table(root, "learning_curve")
    assert len(table) == len(FRACTIONS) * 2
    assert table["n_train"].is_monotonic_increasing


@pytest.mark.parametrize(
    ("name", "rows"),
    [
        ("ablation", 5 * 2),
        ("parameterisation", 7 * 2),
        ("missingness_indicator_signal", 2 * 2),
        ("missingness_outcome_rates", 6),
        ("gbt_missing_value_handling", 7 * 2),
        ("multiple_imputation", 7 * 2),
    ],
)
def test_extension_table_shapes(root, name, rows):
    table = _table(root, name)
    assert len(table) == rows
    if "n" in table:
        assert (table["n"] == 3126).all()


def test_subgroups_follow_the_event_rule(root):
    table = _table(root, "subgroups")
    reported = table[table["reported"]]
    assert (reported["events"] >= 30).all()
    assert (table.loc[~table["reported"], "events"] < 30).all()


def test_extension_figures_exist(root):
    names = {p.name for p in (root / "outputs" / "figures").glob("fig1*.png")}
    for expected in (
        "fig12_learning_curve",
        "fig13_ablation",
        "fig14_parameterisation",
        "fig15_missingness_rates",
    ):
        assert f"{expected}.png" in names


def test_secondary_artefact_is_set_b_and_not_served(root):
    directory = root / "webapp" / "model" / "secondary_set_b"
    secondary = FittedPipelineArtefact.load(directory)
    primary = json.loads((root / "webapp" / "model" / "version.json").read_text())
    version = json.loads((directory / "version.json").read_text())
    assert secondary.feature_set == "B" and "not served" in secondary.role
    assert version["artefact_sha256"] != primary["artefact_sha256"]
    assert version["version"] != primary["version"]
    assert not [c for c in secondary.feature_names if c.endswith("_v1")]


def test_meeting_evidence_is_generated_from_tables(root, tmp_path):
    from antenatal.paths import ProjectPaths
    from antenatal.reporting.meeting_evidence import write_meeting_evidence

    paths = ProjectPaths.from_root(root)
    text = write_meeting_evidence(paths)
    assert "## Not yet complete" in text and "Stage 4" in text and "Stage 6" in text
    assert "| Held out partition (sealed, not opened) | 782 | 41 |" in text
    summary = pd.read_csv(root / TABLES / "results_summary.csv")
    assert summary["source"].str.startswith("outputs/tables/").all()


def test_readme_generated_blocks_are_current(root):
    from antenatal.paths import ProjectPaths
    from antenatal.reporting.readme import render_readme

    text = (root / "README.md").read_text()
    assert render_readme(ProjectPaths.from_root(root), text) == text


def test_technical_report_fills_every_field_from_files(root, tmp_path):
    import shutil

    from antenatal.paths import ProjectPaths
    from antenatal.reporting.technical_report import write_technical_report

    for folder in ("outputs", "docs/evidence"):
        shutil.copytree(root / folder, tmp_path / folder)
    (tmp_path / "docs").mkdir(exist_ok=True)
    text = write_technical_report(ProjectPaths.from_root(tmp_path)).read_text()
    assert "{" not in text and "}" not in text
    summary = pd.read_csv(root / TABLES / "results_summary.csv").set_index("key")
    assert f"{summary.loc['primary_c_over_b_logistic', 'value']:+.4f}" in text
    assert "## 5. Results and limitations" in text
