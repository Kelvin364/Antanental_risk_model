"""The whole command sequence on a throwaway project, with a reduced specification.

One repeat and 100 bootstrap resamples keep the run short. The full study
uses ten repeats and 2,000 resamples through the same code.
"""

import json

import pandas as pd
import pytest

from antenatal.analysis import run_analysis
from antenatal.artefact.artefact import FittedPipelineArtefact
from antenatal.cli import main
from antenatal.config import PRIMARY
from antenatal.paths import ProjectPaths
from antenatal.study import freeze_artefact

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
    freeze_artefact(paths, QUICK)
    return paths


def test_analysis_writes_tables_and_figures(project):
    comparisons = pd.read_csv(project.tables / "feature_set_comparisons.csv")
    assert set(comparisons["role"]) >= {"primary", "secondary", "supporting"}
    assert (comparisons["n"] == 3126).all()
    assert len(list(project.figures.glob("fig*.png"))) == 11
    sensitivity = pd.read_csv(project.tables / "sensitivity_analyses.csv")
    assert set(sensitivity["analysis"]) == {"S1", "S2", "S3", "S4", "S5", "S6"}


def test_one_repeat_covers_every_development_record_once(project):
    oof = pd.read_parquet(project.outputs / "oof_predictions.parquet")
    counts = oof.groupby(["model", "feature_set"])["record_id"].agg(["count", "nunique"])
    assert (counts["count"] == 3126).all() and (counts["nunique"] == 3126).all()


def test_frozen_artefact_loads_and_matches_manifest(project):
    artefact = FittedPipelineArtefact.load(project.model)
    assert len(artefact.reference_probabilities) == 3126
    manifest = json.loads((project.outputs / "manifest.json").read_text())
    assert manifest["inputs"]["data"]["sha256"] == PRIMARY.data_sha256
