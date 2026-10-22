"""The prototype API: the happy path, every refusal path and score equality."""

from __future__ import annotations

import shutil

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from antenatal.artefact.artefact import FittedPipelineArtefact
from antenatal.data.loader import ChecksumMismatch
from webapp.app.core.settings import Settings
from webapp.app.main import create_app
from webapp.app.schemas.cases import CaseCreate, VisitCreate
from webapp.app.services.model_service import ModelService, study_values

CASE = {
    "synthetic": True,
    "label": "Test A",
    "age": 24,
    "gravidity": 2,
    "prior_deliveries": 1,
    "height_cm": 156,
    "registration_weight": 58,
    "hiv": False,
    "smoking": False,
}
VISIT_ONE = {
    "gestational_week": 16,
    "systolic": 110,
    "diastolic": 70,
    "weight_kg": 56,
    "pulse": 80,
    "haemoglobin": 11.2,
}
VISIT_TWO = {
    "gestational_week": 22,
    "systolic": 118,
    "diastolic": 76,
    "weight_kg": 58,
    "pulse": 88,
    "haemoglobin": None,
}


@pytest.fixture
def settings(root, tmp_path) -> Settings:
    return Settings(
        model_dir=root / "webapp" / "model",
        database_url=f"sqlite:///{tmp_path / 'app.sqlite3'}",
        static_dir=root / "webapp" / "static",
    )


@pytest.fixture
def client(settings) -> TestClient:
    return TestClient(create_app(settings))


def _complete_case(client: TestClient, case: dict = CASE) -> int:
    case_id = client.post("/api/cases", json=case).json()["id"]
    assert client.put(f"/api/cases/{case_id}/visits/1", json=VISIT_ONE).status_code == 200
    assert client.put(f"/api/cases/{case_id}/visits/2", json=VISIT_TWO).status_code == 200
    return case_id


def _messages(response) -> list[str]:
    return [e["message"] for e in response.json()["detail"]]


def test_health_reports_artefact(client, root):
    body = client.get("/health").json()
    version = FittedPipelineArtefact.load(root / "webapp" / "model")
    assert body["artefact_version"] == version.version and body["n_features"] == 25
    assert body["data_sha256"] == version.data_sha256 and body["events"] == 165


def test_artefact_endpoint_returns_version_record(client):
    body = client.get("/api/artefact").json()
    assert body["feature_set"] == "C" and body["availability_screen"]["hb"]["passed"] is False


def test_create_case(client):
    response = client.post("/api/cases", json=CASE)
    assert response.status_code == 201
    assert response.json()["synthetic"] is True and response.json()["visits"] == []


def test_add_visits_and_assess(client):
    case_id = _complete_case(client)
    response = client.post(f"/api/cases/{case_id}/assessment")
    assert response.status_code == 201
    body = response.json()
    assert body["interval_low"] < body["probability"] < body["interval_high"]
    assert body["reference_caseload_size"] == 3126 and body["artefact_version"] == "1.0.0"
    assert "Not a clinical risk category" in body["limitation"]
    stored = client.get(f"/api/cases/{case_id}").json()
    assert stored["latest_assessment"]["probability"] == body["probability"]


def test_caseload_orders_by_probability(client):
    low = _complete_case(client, {**CASE, "label": "Low", "registration_weight": 80})
    high = _complete_case(client, {**CASE, "label": "High", "registration_weight": 40})
    for case_id in (low, high):
        client.post(f"/api/cases/{case_id}/assessment")
    rows = client.get("/api/caseload").json()["rows"]
    assert [r["caseload_position"] for r in rows] == [1, 2]
    assert rows[0]["probability"] >= rows[1]["probability"]
    assert {r["label"] for r in rows} == {"Low", "High"}


def test_synthetic_flag_required(client):
    response = client.post("/api/cases", json={**CASE, "synthetic": False})
    assert response.status_code == 422
    assert any("synthetic flag" in m for m in _messages(response))


def test_registration_range_refused(client):
    response = client.post("/api/cases", json={**CASE, "age": 121})
    assert response.status_code == 422
    assert _messages(response) == [
        "Maternal age must be between 12 and 55 years; 121 is outside the cleaning range"
    ]


def test_missing_required_field_refused(client):
    response = client.post("/api/cases", json={**CASE, "height_cm": None})
    assert response.status_code == 422 and "Height is required" in _messages(response)


@pytest.mark.parametrize(
    ("field", "value", "fragment"),
    [
        ("systolic", 300, "Systolic blood pressure must be between 60 and 250"),
        ("diastolic", 20, "Diastolic blood pressure must be between 30 and 160"),
        ("haemoglobin", 25, "Haemoglobin must be between 3 and 20"),
    ],
)
def test_visit_range_refused(client, field, value, fragment):
    case_id = client.post("/api/cases", json=CASE).json()["id"]
    response = client.put(f"/api/cases/{case_id}/visits/1", json={**VISIT_ONE, field: value})
    assert response.status_code == 422 and any(fragment in m for m in _messages(response))


def test_visit_two_not_later_than_visit_one_refused(client):
    case_id = client.post("/api/cases", json=CASE).json()["id"]
    client.put(f"/api/cases/{case_id}/visits/1", json=VISIT_ONE)
    response = client.put(
        f"/api/cases/{case_id}/visits/2", json={**VISIT_TWO, "gestational_week": 16}
    )
    assert response.status_code == 422 and any(
        "later than visit one" in m for m in _messages(response)
    )


def test_visit_two_after_cutoff_refused(client):
    case_id = client.post("/api/cases", json=CASE).json()["id"]
    client.put(f"/api/cases/{case_id}/visits/1", json=VISIT_ONE)
    response = client.put(
        f"/api/cases/{case_id}/visits/2", json={**VISIT_TWO, "gestational_week": 30}
    )
    assert response.status_code == 422 and any(
        "at or before 28 weeks" in m for m in _messages(response)
    )


def test_visit_two_before_visit_one_refused(client):
    case_id = client.post("/api/cases", json=CASE).json()["id"]
    response = client.put(f"/api/cases/{case_id}/visits/2", json=VISIT_TWO)
    assert response.status_code == 409


def test_assessment_needs_both_visits(client):
    case_id = client.post("/api/cases", json=CASE).json()["id"]
    assert client.post(f"/api/cases/{case_id}/assessment").status_code == 409


def test_unknown_case_is_404(client):
    assert client.get("/api/cases/999").status_code == 404


def test_visit_is_replaced_not_duplicated(client):
    case_id = client.post("/api/cases", json=CASE).json()["id"]
    client.put(f"/api/cases/{case_id}/visits/1", json=VISIT_ONE)
    body = client.put(f"/api/cases/{case_id}/visits/1", json={**VISIT_ONE, "weight_kg": 57}).json()
    assert len(body["visits"]) == 1 and body["visits"][0]["weight_kg"] == 57


def test_predict_refuses_without_flag_and_lists_every_error(client):
    payload = {
        "case": {**CASE, "synthetic": False, "age": 5},
        "visit_one": VISIT_ONE,
        "visit_two": {**VISIT_TWO, "gestational_week": 10},
    }
    fields = {e["field"] for e in client.post("/api/predict", json=payload).json()["detail"]}
    assert {"synthetic", "age", "gestational_week"} <= fields


def test_tampered_artefact_refuses_to_start(settings, tmp_path):
    shutil.copytree(settings.model_dir, tmp_path / "model")
    with open(tmp_path / "model" / "lbw_model.joblib", "ab") as handle:
        handle.write(b"tampered")
    with pytest.raises(ChecksumMismatch):
        create_app(Settings(tmp_path / "model", settings.database_url, settings.static_dir))


def test_api_equals_service_equals_package_pipeline(client, settings):
    """A case scored through the API equals ModelService and the package pipeline to 1e-9."""
    payload = {"case": CASE, "visit_one": VISIT_ONE, "visit_two": VISIT_TWO}
    api = client.post("/api/predict", json=payload).json()
    service = ModelService(settings.model_dir)
    values = study_values(CaseCreate(**CASE), VisitCreate(**VISIT_ONE), VisitCreate(**VISIT_TWO))
    direct = service.predict(values)
    artefact = FittedPipelineArtefact.load(settings.model_dir)
    frame = pd.DataFrame([values], dtype=float)[artefact.feature_names]
    pipeline = artefact.pipeline.predict_proba(frame)[0, 1]
    assert api["probability"] == pytest.approx(direct.probability, abs=1e-9)
    assert direct.probability == pytest.approx(pipeline, abs=1e-9)
    assert api["interval_low"] == pytest.approx(direct.interval_low, abs=1e-9)
    assert api["rank_position"] == direct.rank


def test_stored_assessment_records_artefact_identity(client, settings):
    case_id = _complete_case(client)
    body = client.post(f"/api/cases/{case_id}/assessment").json()
    expected = (settings.model_dir / "lbw_model.sha256").read_text().split()[0]
    assert body["artefact_sha256"] == expected


def test_interface_text_has_no_triage_language(client):
    text = " ".join(client.get("/api/interface-text").json().values()).lower()
    for word in ("see sooner", "routine", "high risk", "low risk", "priority"):
        assert word not in text


def test_interface_export_is_served_beside_the_api(settings, tmp_path):
    """Each screen of the Next.js export resolves to its page, and the API routes still win."""
    out = tmp_path / "out"
    pages = ("register", "visit-one", "visit-two", "assessment", "caseload")
    for page in ("", *pages):
        (out / page).mkdir(parents=True, exist_ok=True)
        (out / page / "index.html").write_text(f"<p>{page or 'home'}</p>")
    client = TestClient(create_app(Settings(settings.model_dir, settings.database_url, out)))
    assert client.get("/").text == "<p>home</p>"
    for page in pages:
        assert client.get(f"/{page}/").text == f"<p>{page}</p>"
        assert client.get(f"/{page}").text == f"<p>{page}</p>"
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/api/caseload").json()["rows"] == []
