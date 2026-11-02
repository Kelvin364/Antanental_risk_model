"""The prototype on a PostgreSQL database, as deployed on Render (docs/deviations.md).

These tests run only when ``ANTENATAL_TEST_POSTGRES_URL`` names an empty
PostgreSQL database that may be wiped, for example the service database in
CI. Every test drops and recreates the application tables first.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from tests.integration.accounts import NEW_PASSWORD, sign_in_as
from tests.integration.test_api import CASE, VISIT_ONE, VISIT_TWO
from webapp.app.core.settings import Settings
from webapp.app.db.database import with_driver
from webapp.app.db.models import Base
from webapp.app.main import create_app
from webapp.app.schemas.cases import CaseCreate, VisitCreate
from webapp.app.services.model_service import ModelService, study_values

URL = os.environ.get("ANTENATAL_TEST_POSTGRES_URL", "")
pytestmark = [
    pytest.mark.postgres,
    pytest.mark.skipif(not URL, reason="ANTENATAL_TEST_POSTGRES_URL is not set"),
]


@pytest.fixture
def settings(root) -> Settings:
    engine = create_engine(with_driver(URL))
    Base.metadata.drop_all(engine)
    engine.dispose()
    return Settings(
        model_dir=root / "webapp" / "model",
        database_url=URL,
        static_dir=root / "frontend" / "out",
    )


@pytest.fixture
def client(settings) -> TestClient:
    return sign_in_as(TestClient(create_app(settings)), "tester")


def _assessed_case(client: TestClient) -> tuple[int, dict]:
    case_id = client.post("/api/cases", json=CASE).json()["id"]
    assert client.put(f"/api/cases/{case_id}/visits/1", json=VISIT_ONE).status_code == 200
    assert client.put(f"/api/cases/{case_id}/visits/2", json=VISIT_TWO).status_code == 200
    response = client.post(f"/api/cases/{case_id}/assessment")
    assert response.status_code == 201, response.text
    return case_id, response.json()


def test_stored_assessment_equals_the_model_service(client, settings):
    """Saving through PostgreSQL does not change a score: equal to 1e-9."""
    case_id, body = _assessed_case(client)
    values = study_values(CaseCreate(**CASE), VisitCreate(**VISIT_ONE), VisitCreate(**VISIT_TWO))
    direct = ModelService(settings.model_dir).predict(values)
    stored = client.get(f"/api/cases/{case_id}").json()["latest_assessment"]
    assert stored["probability"] == pytest.approx(direct.probability, abs=1e-9)
    assert stored["interval_high"] == pytest.approx(direct.interval_high, abs=1e-9)
    assert body["rank_position"] == direct.rank


def test_cases_survive_a_restart(client, settings):
    """The reason for the hosted database: a fresh process still sees every row."""
    case_id, body = _assessed_case(client)
    restarted = TestClient(create_app(settings))
    signed_in = restarted.post(
        "/api/auth/sign-in",
        json={"username": "tester", "password": NEW_PASSWORD},
    )
    assert signed_in.status_code == 200
    rows = restarted.get("/api/caseload").json()["rows"]
    assert [(r["case_id"], r["probability"]) for r in rows] == [(case_id, body["probability"])]


def test_database_refuses_a_case_without_the_synthetic_flag(client, settings):
    """The check constraint holds on PostgreSQL, not only in the entry rules."""
    _assessed_case(client)
    engine = create_engine(with_driver(settings.database_url))
    with engine.begin() as connection, pytest.raises(IntegrityError):
        connection.execute(text("UPDATE synthetic_cases SET synthetic = false"))
    engine.dispose()


def test_health_names_postgresql_and_a_required_persistent_database_starts(client, settings):
    """What the Render service runs with: the guard admits PostgreSQL, /health says so."""
    from dataclasses import replace

    TestClient(create_app(replace(settings, require_persistent_database=True)))
    assert client.get("/health").json()["database"] == "postgresql"


def test_check_and_backup_read_the_hosted_tables(client, settings, tmp_path):
    """The check reports the server and every table; the backup copies each row."""
    from webapp.app.db.maintenance import check, copy_to_sqlite

    _assessed_case(client)
    report = check(settings.database_url)
    assert report["database"] == "postgresql" and report["missing_tables"] == []
    assert report["rows"]["assessments"] == 1 and report["server_version"]
    assert copy_to_sqlite(settings.database_url, tmp_path / "online.sqlite3") == report["rows"]
