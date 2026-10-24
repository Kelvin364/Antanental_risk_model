"""Stage 3: the research questions are answered from saved predictions, with valid tests."""

from dataclasses import replace

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import roc_auc_score

from antenatal.config import PRIMARY
from antenatal.evaluation.delong import delong_paired
from antenatal.paths import ProjectPaths
from antenatal.reporting.research_report import _text
from antenatal.research import QUESTIONS, check_alignment, load_all, results_table


def test_delong_matches_the_roc_auc_and_is_antisymmetric():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 400)
    p_new, p_old = y + rng.normal(0, 1.0, 400), y + rng.normal(0, 1.5, 400)
    forward, backward = delong_paired(y, p_new, p_old), delong_paired(y, p_old, p_new)
    assert forward.auc_new == pytest.approx(roc_auc_score(y, p_new), abs=1e-12)
    assert forward.difference == pytest.approx(-backward.difference, abs=1e-12)
    assert forward.p_value == pytest.approx(backward.p_value, abs=1e-12)
    assert 0 < forward.se < 0.1


def test_delong_of_identical_predictions_has_no_difference():
    y = np.array([0, 0, 1, 1, 0, 1])
    result = delong_paired(y, np.arange(6.0), np.arange(6.0))
    assert result.difference == 0 and result.p_value == 1.0


@pytest.fixture(scope="module")
def table(root):
    return results_table(ProjectPaths.from_root(root), replace(PRIMARY, bootstrap_resamples=20))


def test_results_reproduce_the_saved_comparisons_and_cover_every_question(table, root):
    saved = pd.read_csv(root / "outputs" / "tables" / "feature_set_comparisons.csv")
    merged = table.merge(saved, on=["model", "comparison", "metric"], suffixes=("", "_saved"))
    assert len(merged) == 24
    assert np.allclose(merged["difference"], merged["difference_saved"], atol=1e-12)
    assert set(table["question"]) == {"1", "2", "3", "4", "supporting", "secondary hypothesis"}
    assert len(QUESTIONS) == 4
    assert QUESTIONS[0].question.startswith("Do measurements from the first antenatal visit")
    saved = table[table["p_method"].str.startswith("normal")]
    assert set(saved["analysis"]) >= {"S3", "S4", "S6"} and saved["p_value"].between(0, 1).all()
    assert {"brier", "calibration_slope"} <= set(table.loc[table["question"] == "2", "metric"])


def test_prespecified_rows_are_unadjusted_and_the_rest_are_holm_adjusted(table):
    prespecified = table[table["role"].isin(["primary", "secondary"])]
    assert len(prespecified) == 4 and prespecified["p_holm"].isna().all()
    exploratory = table[table["family"] == "exploratory, Holm"]
    assert (exploratory["p_holm"] >= exploratory["p_value"]).all()
    roc = table[table["metric"] == "roc_auc"]
    assert roc["delong_p_value"].between(0, 1).all()
    assert table[table["metric"] != "roc_auc"]["delong_p_value"].isna().all()


def test_the_summary_is_filled_including_the_held_out_section(table, root):
    text = _text(table, ProjectPaths.from_root(root), PRIMARY)
    assert "{" not in text and "## Held out records" in text
    held_out = text.split("## Held out records")[1]
    assert "has not been run" in held_out or "| C over B (first visit added) |" in held_out
    assert text.count("\n| ") >= len(table) + len(QUESTIONS)


def test_a_paired_test_refuses_misaligned_predictions(root):
    results = load_all(ProjectPaths.from_root(root))
    results = replace(results, oof=results.oof[results.oof["record_id"] != 1])
    with pytest.raises(ValueError, match="not aligned"):
        check_alignment(results, ("logistic_l2", "C"))


def test_the_statistics_notebook_executes_without_errors(root):
    import nbformat
    from nbclient import NotebookClient

    notebook = nbformat.read(root / "notebooks" / "03_statistical_analysis.ipynb", as_version=4)
    NotebookClient(
        notebook, timeout=600, resources={"metadata": {"path": root / "notebooks"}}
    ).execute()
    errors = [
        o for c in notebook.cells for o in c.get("outputs", []) if o["output_type"] == "error"
    ]
    assert errors == []
