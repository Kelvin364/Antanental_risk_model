"""Agreement to the Terms of Use before any case work, recorded with its version and time."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select, text

from tests.integration.accounts import sign_in_as
from webapp.app.core import policy
from webapp.app.core.settings import Settings
from webapp.app.db.database import create_session_factory
from webapp.app.db.models import AuditEvent, User
from webapp.app.main import create_app

CASE = {
    "synthetic": True,
    "age": 24,
    "gravidity": 2,
    "prior_deliveries": 1,
    "height_cm": 156,
    "registration_weight": 58,
}
VISIT_ONE = {"gestational_week": 16, "systolic": 110, "diastolic": 70, "weight_kg": 56}
VISIT_TWO = {"gestational_week": 22, "systolic": 118, "diastolic": 76, "weight_kg": 58}
PREDICT = {"case": CASE, "visit_one": VISIT_ONE, "visit_two": VISIT_TWO}


@pytest.fixture
def app(root, tmp_path):
    settings = Settings(
        root / "webapp" / "model",
        f"sqlite:///{tmp_path / 'app.sqlite3'}",
        root / "frontend" / "out",
    )
    return create_app(settings)


def _case_calls(client: TestClient) -> list[int]:
    return [
        client.post("/api/cases", json=CASE).status_code,
        client.get("/api/caseload").status_code,
        client.post("/api/predict", json=PREDICT).status_code,
    ]


def _stored(app, username: str) -> User:
    with app.state.auth._sessions() as session:
        return session.scalar(select(User).where(User.username == username))


def _events(app, name: str) -> list[AuditEvent]:
    with app.state.auth._sessions() as session:
        return list(session.scalars(select(AuditEvent).where(AuditEvent.event == name)))


def test_case_work_is_refused_until_the_terms_are_accepted(app):
    client = sign_in_as(TestClient(app), "nora", consent=False)
    me = client.get("/api/auth/me").json()
    assert me["terms_accepted"] is False and me["terms_version"] is None
    for response in (
        client.post("/api/cases", json=CASE),
        client.get("/api/caseload"),
        client.post("/api/predict", json=PREDICT),
    ):
        assert response.status_code == 403
        assert response.json()["detail"] == [
            {"field": "consent", "message": "Accept the Terms of Use before using the application"}
        ]


def test_accepting_records_the_version_the_time_and_an_audit_event(app):
    client = sign_in_as(TestClient(app), "omar", consent=False)
    response = client.post("/api/auth/consent", json={"version": policy.POLICY_VERSION})
    assert response.status_code == 204
    row = _stored(app, "omar")
    assert row.terms_version == policy.POLICY_VERSION and row.terms_accepted_at is not None
    events = _events(app, "consent_accepted")
    assert [(e.username, e.detail) for e in events] == [
        ("omar", f"version {policy.POLICY_VERSION}")
    ]
    me = client.get("/api/auth/me").json()
    assert me["terms_accepted"] is True and me["terms_accepted_at"]
    assert _case_calls(client) == [201, 200, 200]


def test_another_version_is_refused_and_nothing_is_recorded(app):
    client = sign_in_as(TestClient(app), "pia", consent=False)
    response = client.post("/api/auth/consent", json={"version": "2020-01-01"})
    assert response.status_code == 409
    assert response.json()["detail"][0]["message"] == policy.TERMS_CHANGED
    row = _stored(app, "pia")
    assert row.terms_version is None and row.terms_accepted_at is None
    assert _events(app, "consent_accepted") == []


def test_a_new_policy_version_asks_again(app, monkeypatch):
    client = sign_in_as(TestClient(app), "quinn")
    assert client.get("/api/auth/me").json()["terms_accepted"] is True
    monkeypatch.setattr(policy, "POLICY_VERSION", "2027-01-01")
    assert client.get("/api/auth/me").json()["terms_accepted"] is False
    assert client.get("/api/caseload").status_code == 403


def test_consent_needs_the_csrf_token(app):
    client = sign_in_as(TestClient(app), "rex", consent=False)
    del client.headers["X-CSRF-Token"]
    response = client.post("/api/auth/consent", json={"version": policy.POLICY_VERSION})
    assert response.status_code == 403 and response.json()["detail"][0]["field"] == "csrf"
    assert _stored(app, "rex").terms_version is None


def test_consent_needs_a_signed_in_user_and_the_policy_is_open(app):
    anonymous = TestClient(app)
    response = anonymous.post("/api/auth/consent", json={"version": policy.POLICY_VERSION})
    assert response.status_code == 401
    body = anonymous.get("/api/policy").json()
    assert body["version"] == policy.POLICY_VERSION
    assert body["consent_sentence"] == policy.CONSENT_SENTENCE


def test_an_older_database_gains_the_new_columns_without_losing_rows(tmp_path):
    url = f"sqlite:///{tmp_path / 'old.sqlite3'}"
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE users (id INTEGER PRIMARY KEY, username VARCHAR(40), "
                "password_hash VARCHAR(200), role VARCHAR(20), active BOOLEAN, "
                "must_change_password BOOLEAN, failed_attempts INTEGER, "
                "locked_until DATETIME, created_at DATETIME)"
            )
        )
        connection.execute(text("INSERT INTO users (username, role) VALUES ('old', 'researcher')"))
    create_session_factory(url)
    columns = {c["name"] for c in inspect(create_engine(url)).get_columns("users")}
    assert {"terms_version", "terms_accepted_at"} <= columns
    with create_engine(url).connect() as connection:
        assert connection.execute(text("SELECT username FROM users")).scalars().all() == ["old"]
