"""A user deletes their own case at once; an administrator removes an account on request."""

from __future__ import annotations

from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from tests.integration.accounts import sign_in_as
from webapp.app.core import policy
from webapp.app.core.settings import Settings
from webapp.app.db.models import (
    Assessment,
    AuditEvent,
    SyntheticCase,
    SyntheticVisit,
    User,
    UserSession,
)
from webapp.app.main import create_app
from webapp.app.services.auth_service import CurrentUser
from webapp.app.services.removal import RemovalRefused

CASE = {
    "synthetic": True,
    "label": "To delete",
    "age": 24,
    "gravidity": 2,
    "prior_deliveries": 1,
    "height_cm": 156,
    "registration_weight": 58,
}
VISIT_ONE = {"gestational_week": 16, "systolic": 110, "diastolic": 70, "weight_kg": 56}
VISIT_TWO = {"gestational_week": 22, "systolic": 118, "diastolic": 76, "weight_kg": 58}


@pytest.fixture
def app(root, tmp_path):
    settings = Settings(
        root / "webapp" / "model",
        f"sqlite:///{tmp_path / 'app.sqlite3'}",
        root / "frontend" / "out",
    )
    return create_app(settings)


def _assessed_case(client: TestClient) -> int:
    case_id = client.post("/api/cases", json=CASE).json()["id"]
    assert client.put(f"/api/cases/{case_id}/visits/1", json=VISIT_ONE).status_code == 200
    assert client.put(f"/api/cases/{case_id}/visits/2", json=VISIT_TWO).status_code == 200
    assert client.post(f"/api/cases/{case_id}/assessment").status_code == 201
    return case_id


def _count(app, table, *where) -> int:
    with app.state.auth._sessions() as session:
        return session.scalar(select(func.count()).select_from(table).where(*where))


def _events(app, name: str) -> list[tuple[str, str]]:
    with app.state.auth._sessions() as session:
        rows = session.scalars(select(AuditEvent).where(AuditEvent.event == name))
        return [(e.username, e.detail) for e in rows]


def test_the_owner_deletes_a_case_with_its_visits_and_assessment(app):
    owner = sign_in_as(TestClient(app), "uma")
    case_id = _assessed_case(owner)
    assert owner.delete(f"/api/cases/{case_id}").status_code == 204
    assert _count(app, SyntheticCase, SyntheticCase.id == case_id) == 0
    assert _count(app, SyntheticVisit, SyntheticVisit.case_id == case_id) == 0
    assert _count(app, Assessment, Assessment.case_id == case_id) == 0
    assert _events(app, "case_deleted") == [("uma", f"case {case_id}")]
    assert owner.get(f"/api/cases/{case_id}").status_code == 404
    assert owner.get("/api/caseload").json()["rows"] == []


def test_nobody_else_can_delete_a_case_and_an_unknown_id_looks_the_same(app):
    owner = sign_in_as(TestClient(app), "vic")
    case_id = _assessed_case(owner)
    stranger = sign_in_as(TestClient(app), "wes")
    refused = stranger.delete(f"/api/cases/{case_id}")
    unknown = stranger.delete("/api/cases/9999")
    assert refused.status_code == unknown.status_code == 404
    assert refused.json()["detail"][0]["message"].startswith("No synthetic case with id")
    assert _count(app, SyntheticCase, SyntheticCase.id == case_id) == 1
    administrator = sign_in_as(TestClient(app), "xena", "administrator")
    assert administrator.delete(f"/api/cases/{case_id}").status_code == 404
    assert _events(app, "case_deleted") == []


def test_deleting_a_case_needs_the_csrf_token(app):
    owner = sign_in_as(TestClient(app), "yan")
    case_id = _assessed_case(owner)
    del owner.headers["X-CSRF-Token"]
    assert owner.delete(f"/api/cases/{case_id}").status_code == 403
    assert _count(app, SyntheticCase, SyntheticCase.id == case_id) == 1


def test_a_removal_request_is_completed_by_an_administrator(app):
    leaver = sign_in_as(TestClient(app), "zoe")
    _assessed_case(leaver)
    assert leaver.post("/api/auth/deletion-request").status_code == 204
    first = leaver.get("/api/auth/me").json()["deletion_requested_at"]
    assert first
    assert leaver.post("/api/auth/deletion-request").status_code == 204
    assert leaver.get("/api/auth/me").json()["deletion_requested_at"] == first
    assert _events(app, "deletion_requested") == [("zoe", "")]
    administrator = sign_in_as(TestClient(app), "ada", "administrator")
    listed = {a["username"]: a for a in administrator.get("/api/admin/users").json()}
    assert listed["zoe"]["deletion_requested_at"] and listed["ada"]["deletion_requested_at"] is None
    user_id = listed["zoe"]["id"]
    assert administrator.post(f"/api/admin/users/{user_id}/remove").status_code == 204
    assert _count(app, User, User.id == user_id) == 0
    assert _count(app, SyntheticCase, SyntheticCase.owner_id == user_id) == 0
    assert _count(app, UserSession, UserSession.user_id == user_id) == 0
    assert _count(app, SyntheticVisit) == 0 and _count(app, Assessment) == 0
    assert _events(app, "account_removed") == [("ada", "zoe")]
    assert leaver.get("/api/auth/me").status_code == 401


def test_only_an_administrator_removes_accounts(app):
    researcher = sign_in_as(TestClient(app), "bob")
    assert researcher.post("/api/admin/users/1/remove").status_code == 403


def test_self_removal_and_the_last_administrator_are_refused(app):
    administrator = sign_in_as(TestClient(app), "cyd", "administrator")
    own_id = next(
        a["id"] for a in administrator.get("/api/admin/users").json() if a["username"] == "cyd"
    )
    refused = administrator.post(f"/api/admin/users/{own_id}/remove")
    assert refused.status_code == 409
    assert refused.json()["detail"][0]["message"] == policy.SELF_REMOVAL
    other, _ = app.state.auth.create_user("dee", "administrator", "test")
    app.state.auth.set_active(own_id, False, "test")
    actor = replace(CurrentUser(own_id, "cyd", "administrator", "x", False), terms_version="any")
    with pytest.raises(RemovalRefused, match=policy.LAST_ADMINISTRATOR):
        app.state.removal.remove(other.id, actor)
    assert _count(app, User, User.id == other.id) == 1
    assert _events(app, "account_removed") == []
