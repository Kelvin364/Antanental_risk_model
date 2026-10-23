"""The whole command sequence on a throwaway project, with a reduced specification.

One repeat and 100 bootstrap resamples keep the run short. The full study
uses ten repeats and 2,000 resamples through the same code. The sequence is
the one ``run-all`` uses: derive the cohort, seal the partition, run the
analysis, run the Stage 5 extensions, freeze both artefacts and summarise the
results.
"""

import json

import pandas as pd
import pytest

from antenatal.analysis import run_analysis
from antenatal.artefact.artefact import FittedPipelineArtefact
from antenatal.cli import main
from antenatal.config import PRIMARY
from antenatal.extensions import run_extensions
from antenatal.paths import ProjectPaths
from antenatal.reporting.results_summary import build_results_summary
from antenatal.study import SECONDARY_PLAN, freeze_artefact

pytestmark = pytest.mark.slow
QUICK = PRIMARY.variant("quick", repeats=1, bootstrap_resamples=100)


@pytest.fixture(scope="module")
def project(tmp_path_factory, root):
    project = tmp_path_factory.mktemp("study")
    (project / "data").mkdir()
    (project / "data" / "maternal_dataset_csv.csv").symlink_to(
        root / "data" / "maternal_dataset_csv.csv"
    )
    main(["derive-cohort", "--root", str(project)])
    main(["seal-partition", "--root", str(project)])
    paths = ProjectPaths.from_root(project).ensure()
    run_analysis(paths, QUICK)
    run_extensions(paths, QUICK)
    freeze_artefact(paths, QUICK)
    freeze_artefact(paths, QUICK, SECONDARY_PLAN)
    build_results_summary(paths)
    return paths


def test_analysis_writes_tables_and_figures(project):
    comparisons = pd.read_csv(project.tables / "feature_set_comparisons.csv")
    assert set(comparisons["role"]) >= {"primary", "secondary", "supporting"}
    assert (comparisons["n"] == 3126).all()
    assert len(list(project.figures.glob("fig*.png"))) == 16
    sensitivity = pd.read_csv(project.tables / "sensitivity_analyses.csv")
    assert set(sensitivity["analysis"]) == {
        "S1",
        "S2",
        "S3",
        "S4",
        "S5",
        "S6",
        "GBT, uniform imputation",
    }


def test_one_repeat_covers_every_development_record_once(project):
    oof = pd.read_parquet(project.outputs / "oof_predictions.parquet")
    counts = oof.groupby(["model", "feature_set"])["record_id"].agg(["count", "nunique"])
    assert (counts["count"] == 3126).all() and (counts["nunique"] == 3126).all()


def test_frozen_artefact_loads_and_matches_manifest(project):
    artefact = FittedPipelineArtefact.load(project.model)
    assert len(artefact.reference_probabilities) == 3126
    manifest = json.loads((project.outputs / "manifest.json").read_text())
    assert manifest["inputs"]["data"]["sha256"] == PRIMARY.data_sha256


@pytest.mark.parametrize(
    ("name", "rows"),
    [
        ("learning_curve", 10),
        ("ablation", 10),
        ("parameterisation", 14),
        ("missingness_outcome_rates", 6),
        ("missingness_indicator_signal", 4),
        ("gbt_missing_value_handling", 14),
        ("multiple_imputation", 14),
        ("retrieval_at_budget", 3),
        ("calibration_by_set", 6),
    ],
)
def test_extensions_write_every_table(project, name, rows):
    assert len(pd.read_csv(project.tables / f"{name}.csv")) == rows


def test_subgroups_apply_the_event_rule(project):
    table = pd.read_csv(project.tables / "subgroups.csv")
    assert (table.loc[table["reported"], "events"] >= 30).all()


def test_results_summary_traces_every_number(project):
    summary = pd.read_csv(project.tables / "results_summary.csv")
    assert summary["key"].is_unique and summary["value"].notna().all()
    assert summary["source"].str.startswith("outputs/tables/").all()
    assert summary.set_index("key").loc["development_records", "value"] == 3126


def test_secondary_artefact_sits_beside_the_primary(project):
    primary = FittedPipelineArtefact.load(project.model)
    secondary = FittedPipelineArtefact.load(project.model / "secondary_set_b")
    assert (primary.feature_set, secondary.feature_set) == ("C", "B")
    assert "not served" in secondary.role


def test_stage2_runs_every_prespecified_experiment_and_labels_short_runs(project):
    from antenatal.evaluation.integrity import run_audit
    from antenatal.stage2 import candidate_keys, run

    outcome = run(project, QUICK)
    runs = pd.read_csv(project.tables / "experiments_v2_runs.csv")
    assert len(runs) == 28 and set(runs["status"]) == {"reduced"}  # one repeat, never "complete"
    candidates = pd.read_csv(project.tables / "candidates_v2.csv")
    assert len(candidates) == len(candidate_keys())
    assert outcome["outcome"] in {"b", "c"}
    comparisons = pd.read_csv(project.tables / "experiments_v2.csv")
    assert comparisons["p_holm"].notna().any() and (comparisons["n"] == 3126).all()
    for name in (
        "operating_points_v2.csv",
        "net_benefit_v2.csv",
        "missing_data_v2.csv",
        "coefficients_v2.csv",
        "permutation_importance_v2.csv",
    ):
        assert (project.tables / name).exists()
    assert (run_audit(project, QUICK)["result"] == "pass").all()
