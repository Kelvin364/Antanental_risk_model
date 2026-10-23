"""Authentication and authorisation, enforced on the server (decision D1)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from tests.integration.accounts import NEW_PASSWORD, sign_in_as
from webapp.app.core.settings import Settings
from webapp.app.main import create_app

CASE = {
    "synthetic": True,
    "age": 24,
    "gravidity": 2,
    "prior_deliveries": 1,
    "height_cm": 156,
    "registration_weight": 58,
}
PROTECTED = [
    ("post", "/api/cases", CASE),
    ("get", "/api/cases/1", None),
    ("put", "/api/cases/1/visits/1", {}),
    ("post", "/api/cases/1/assessment", None),
    ("get", "/api/caseload", None),
    ("post", "/api/predict", {}),
    ("get", "/api/admin/users", None),
    ("post", "/api/admin/users", {"username": "x", "role": "researcher"}),
    ("get", "/api/admin/audit", None),
    ("get", "/api/auth/me", None),
]


@pytest.fixture
def app(root, tmp_path):
    settings = Settings(
        root / "webapp" / "model",
        f"sqlite:///{tmp_path / 'app.sqlite3'}",
        root / "frontend" / "out",
    )
    return create_app(settings)


@pytest.mark.parametrize("method, path, body", PROTECTED)
def test_every_protected_route_refuses_without_sign_in(app, method, path, body):
    response = getattr(TestClient(app), method)(path, **({"json": body} if body else {}))
    assert response.status_code == 401


def test_public_routes_stay_open(app):
    client = TestClient(app)
    for path in ("/health", "/api/interface-text", "/api/artefact"):
        assert client.get(path).status_code == 200


def test_researcher_cannot_reach_administration(app):
    client = sign_in_as(TestClient(app), "ruth")
    assert client.get("/api/admin/users").status_code == 403
    assert (
        client.post("/api/admin/users", json={"username": "z1", "role": "researcher"}).status_code
        == 403
    )


def test_administrator_creates_an_account_that_must_change_its_password(app):
    admin = sign_in_as(TestClient(app), "ada", "administrator")
    created = admin.post("/api/admin/users", json={"username": "rhea", "role": "researcher"}).json()
    newcomer = TestClient(app)
    signed = newcomer.post("/api/auth/sign-in", json=created).json()
    assert signed["must_change_password"]
    newcomer.headers["X-CSRF-Token"] = signed["csrf_token"]
    assert newcomer.post("/api/cases", json=CASE).status_code == 403


def test_five_failures_lock_the_account(app):
    client = sign_in_as(TestClient(app), "lena")
    other = TestClient(app)
    for _ in range(5):
        assert (
            other.post(
                "/api/auth/sign-in", json={"username": "lena", "password": "wrong"}
            ).status_code
            == 401
        )
    right = other.post("/api/auth/sign-in", json={"username": "lena", "password": NEW_PASSWORD})
    assert right.status_code == 401 and "Too many failed attempts" in right.text
    assert client.get("/api/auth/me").status_code == 200


def test_session_cookie_flags(app):
    _, first = app.state.auth.create_user("cora", "researcher", "test")
    plain = TestClient(app).post("/api/auth/sign-in", json={"username": "cora", "password": first})
    cookie = plain.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie and "secure" not in cookie
    secure = TestClient(app, base_url="https://testserver").post(
        "/api/auth/sign-in", json={"username": "cora", "password": first}
    )
    assert "secure" in secure.headers["set-cookie"].lower()


def test_changes_without_the_csrf_token_are_refused(app):
    client = sign_in_as(TestClient(app), "cleo")
    del client.headers["X-CSRF-Token"]
    assert client.post("/api/cases", json=CASE).status_code == 403


def test_passwords_are_never_stored_in_clear(app):
    _, first = app.state.auth.create_user("pia", "researcher", "test")
    with app.state.auth._sessions() as session:
        stored = session.execute(
            text("select password_hash from users where username='pia'")
        ).scalar()
    assert stored.startswith("scrypt$") and first not in stored


def test_researchers_see_only_their_own_cases(app):
    owner = sign_in_as(TestClient(app), "olga")
    case_id = owner.post("/api/cases", json=CASE).json()["id"]
    stranger = sign_in_as(TestClient(app), "sam")
    assert stranger.get(f"/api/cases/{case_id}").status_code == 404
    admin = sign_in_as(TestClient(app), "abe", "administrator")
    assert admin.get(f"/api/cases/{case_id}").status_code == 200


def test_sign_out_ends_the_session_on_the_server(app):
    client = sign_in_as(TestClient(app), "sid")
    token = client.cookies.get("antenatal_session")
    assert client.post("/api/auth/sign-out").status_code == 204
    replay = TestClient(app)
    replay.cookies.set("antenatal_session", token)
    assert replay.get("/api/auth/me").status_code == 401


def test_audit_trail_holds_no_clinical_values(app):
    client = sign_in_as(TestClient(app), "ann", "administrator")
    client.post("/api/cases", json=CASE)
    events = client.get("/api/admin/audit").json()
    assert {"sign_in", "account_created", "password_changed"} <= {e["event"] for e in events}
    assert not any("156" in e["detail"] or "58" in e["detail"] for e in events)


def test_sign_in_rate_limit_and_security_headers(app):
    client = TestClient(app)
    codes = [
        client.post("/api/auth/sign-in", json={"username": "nobody", "password": "x"}).status_code
        for _ in range(21)
    ]
    assert codes[-1] == 429 and set(codes[:20]) == {401}
    headers = client.get("/health").headers
    assert (
        headers["x-frame-options"] == "DENY"
        and "default-src 'self'" in headers["content-security-policy"]
    )


def test_first_administrator_comes_from_the_command_line(tmp_path, monkeypatch, capsys):
    from webapp.app.admin import main

    monkeypatch.setenv("ANTENATAL_DATABASE_URL", f"sqlite:///{tmp_path / 'admin.sqlite3'}")
    assert main(["create-admin", "boss"]) == 0
    printed = capsys.readouterr().out
    assert "Administrator boss created" in printed and "shown once" in printed


def test_account_rules_and_administration_actions(app):
    admin = sign_in_as(TestClient(app), "root1", "administrator")
    taken = admin.post("/api/admin/users", json={"username": "root1", "role": "researcher"})
    bad_role = admin.post("/api/admin/users", json={"username": "newbie", "role": "chief"})
    bad_name = admin.post("/api/admin/users", json={"username": "A B", "role": "researcher"})
    assert {taken.status_code, bad_role.status_code, bad_name.status_code} == {422}
    created = admin.post("/api/admin/users", json={"username": "rae", "role": "researcher"}).json()
    users = {u["username"]: u["id"] for u in admin.get("/api/admin/users").json()}
    reset = admin.post(f"/api/admin/users/{users['rae']}/reset-password").json()
    assert reset["password"] != created["password"]
    assert (
        admin.post(f"/api/admin/users/{users['rae']}/active", json={"active": False}).status_code
        == 204
    )
    refused = TestClient(app).post("/api/auth/sign-in", json=reset)
    assert refused.status_code == 401
    short = admin.post(
        "/api/auth/password", json={"current_password": NEW_PASSWORD, "new_password": "short"}
    )
    wrong = admin.post(
        "/api/auth/password", json={"current_password": "nope", "new_password": "x" * 12}
    )
    assert short.status_code == wrong.status_code == 422
    assert admin.post("/api/admin/users/9999/reset-password").status_code == 422


def test_selfcheck_scores_like_the_development_machine():
    from webapp.app import selfcheck

    result = selfcheck.run()
    assert result["matches_development_machine_to_1e-9"] and result["artefact_version"] == "1.0.0"
    assert result["label"] in ("Likely low birth weight", "Not likely low birth weight")
