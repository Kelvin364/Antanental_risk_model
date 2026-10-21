"""The frozen artefact and the files written by the analysis."""

import json
import shutil

import numpy as np
import pandas as pd
import pytest

from antenatal.artefact.artefact import FittedPipelineArtefact
from antenatal.artefact.interval import design_rows
from antenatal.cohort.builder import Cohort
from antenatal.cohort.exclusion_log import ExclusionLog
from antenatal.cohort.partition import PartitionWriter
from antenatal.config import PRIMARY
from antenatal.data.loader import ChecksumMismatch
from antenatal.evaluation.holdout import HoldoutAccessRefused, HoldoutEvaluator

CASE = {
    "age": 24,
    "gravidity": 2,
    "prior_deliveries": 1,
    "height_cm": 156,
    "registration_weight": 58,
    "prior_caesarean": 0,
    "prior_hypertension_pregnancy": 0,
    "chronic_hypertension": 0,
    "diabetes": 0,
    "hiv": 0,
    "tuberculosis": 0,
    "sickle_cell": 0,
    "smoking": 0,
    "intimate_partner_violence": 0,
    "sbp_v1": 110,
    "dbp_v1": 70,
    "weight_v1": 56,
    "ga_v1": 16,
    "pulse_v1": 80,
    "hb_v1": 11,
    "sbp_v2": 112,
    "dbp_v2": 70,
    "weight_v2": 58,
    "ga_v2": 22,
    "pulse_v2": 82,
    "hb_v2": None,
}


@pytest.fixture(scope="module")
def artefact(root):
    return FittedPipelineArtefact.load(root / "webapp" / "model")


def test_reference_probabilities_cover_development(artefact):
    assert len(artefact.reference_probabilities) == 3126
    assert artefact.n_development == 3126 and artefact.events == 165


def test_artefact_is_linear_set_c_without_change_terms(artefact):
    assert (artefact.family, artefact.feature_set) == ("logistic_l2", "C")
    assert not [c for c in artefact.feature_names if c.startswith("d_")]
    assert "hb_v2" in artefact.feature_names and "hb_v1" not in artefact.feature_names


def test_assessment_matches_pipeline(artefact):
    result = artefact.assess(CASE)
    frame = pd.DataFrame([CASE], dtype=float)[artefact.feature_names]
    direct = artefact.pipeline.predict_proba(frame)[0, 1]
    assert result.probability == pytest.approx(direct, abs=1e-12)
    assert result.interval_low < result.probability < result.interval_high
    assert 1 <= result.rank <= result.caseload_size


def test_wald_logit_matches_estimator(artefact):
    frame = pd.DataFrame([CASE], dtype=float)[artefact.feature_names]
    z = design_rows(artefact.pipeline, frame)
    model = artefact.pipeline[-1]
    eta = z @ np.concatenate([model.intercept_, model.coef_[0]])
    assert eta[0] == pytest.approx(
        model.decision_function(artefact.pipeline[:-1].transform(frame))[0]
    )


def test_rank_is_one_for_the_highest(artefact):
    assert artefact.rank_of(1.0) == 1
    assert artefact.rank_of(0.0) == len(artefact.reference_probabilities) + 1


def test_tampered_artefact_is_refused(root, tmp_path):
    shutil.copytree(root / "webapp" / "model", tmp_path / "model")
    with open(tmp_path / "model" / "lbw_model.joblib", "ab") as handle:
        handle.write(b"x")
    with pytest.raises(ChecksumMismatch):
        FittedPipelineArtefact.load(tmp_path / "model")


def test_version_record_matches_checksum(root):
    model = root / "webapp" / "model"
    version = json.loads((model / "version.json").read_text())
    assert version["artefact_sha256"] == (model / "lbw_model.sha256").read_text().split()[0]
    assert version["data_sha256"] == PRIMARY.data_sha256


def test_out_of_fold_predictions_never_include_held_out_records(root):
    oof = pd.read_parquet(root / "outputs" / "oof_predictions.parquet")
    held = PartitionWriter(root / "partitions").load().holdout_ids
    assert not set(oof["record_id"]) & held
    assert oof.groupby(["model", "feature_set", "repeat"])["record_id"].nunique().eq(3126).all()


def test_manifest_records_inputs_and_environment(root):
    manifest = json.loads((root / "outputs" / "manifest.json").read_text())
    assert manifest["inputs"]["data"]["sha256"] == PRIMARY.data_sha256
    assert manifest["seed"] == PRIMARY.seed and "scikit-learn" in manifest["environment"]
    assert all(len(digest) == 64 for digest in manifest["outputs"].values())


@pytest.mark.parametrize(
    ("name", "rows"),
    [
        ("cohort_flow.csv", 8),
        ("availability_screen.csv", 6),
        ("feature_set_comparisons.csv", 24),
        ("sensitivity_analyses.csv", 24),
        ("cv_fold_metrics.csv", 13 * 50),
    ],
)
def test_result_tables_have_expected_shape(root, name, rows):
    assert len(pd.read_csv(root / "outputs" / "tables" / name)) == rows


def test_every_figure_exists(root):
    figures = sorted(p.name for p in (root / "outputs" / "figures").glob("fig*.png"))
    assert len(figures) >= 11


class _ConstantArtefact:
    version = "test"
    partition_sha256 = "test"

    def score(self, frame):
        p = np.linspace(0.01, 0.2, len(frame))
        return p, p, p


def test_evaluate_once_on_a_synthetic_cohort(tmp_path):
    """Exercises the gate without ever scoring the real held out records."""
    n = 200
    records = pd.DataFrame(
        {
            "record_id": np.arange(n),
            "group_key": [f"g{i // 2}" for i in range(n)],
            "lbw": (np.arange(n) % 7 == 0).astype(int),
            "in_analysis_cohort": True,
        }
    )
    cohort = Cohort(PRIMARY, records, ExclusionLog())
    pd.DataFrame({"record_id": np.arange(0, n, 2)}).to_csv(
        tmp_path / "holdout_ids.csv", index=False
    )
    digest = __import__("hashlib").sha256((tmp_path / "holdout_ids.csv").read_bytes()).hexdigest()
    (tmp_path / "holdout.sha256").write_text(f"{digest}  holdout_ids.csv\n")
    evaluator = HoldoutEvaluator(tmp_path)
    spec = PRIMARY.variant("test", bootstrap_resamples=50)
    with pytest.raises(HoldoutAccessRefused):
        evaluator.evaluate_once(
            _ConstantArtefact(),
            cohort,
            tmp_path / "r.csv",
            confirm_supervisor_reviewed=False,
            spec=spec,
        )
    table = evaluator.evaluate_once(
        _ConstantArtefact(), cohort, tmp_path / "r.csv", confirm_supervisor_reviewed=True, spec=spec
    )
    assert set(table["metric"]) >= {"pr_auc", "roc_auc"} and table["n"].iloc[0] == 100
    with pytest.raises(HoldoutAccessRefused):
        evaluator.evaluate_once(
            _ConstantArtefact(),
            cohort,
            tmp_path / "r.csv",
            confirm_supervisor_reviewed=True,
            spec=spec,
        )
    assert evaluator.evaluations_logged() == 1
