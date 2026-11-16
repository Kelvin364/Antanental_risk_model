"""Sign a test client in through the real sign in route (decision D1)."""

from __future__ import annotations

from fastapi.testclient import TestClient

NEW_PASSWORD = "a long synthetic test password"


def sign_in_as(
    client: TestClient, username: str, role: str = "researcher", consent: bool = True
) -> TestClient:
    """Create the account, sign in, replace the first password and keep the CSRF header.

    With ``consent`` (the default) the account also agrees to the current Terms of Use,
    as a user does on the consent page before any case work.
    """
    _, first = client.app.state.auth.create_user(username, role, "test")
    response = client.post("/api/auth/sign-in", json={"username": username, "password": first})
    assert response.status_code == 200, response.text
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    change = {"current_password": first, "new_password": NEW_PASSWORD}
    assert client.post("/api/auth/password", json=change).status_code == 204
    if consent:
        version = client.get("/api/policy").json()["version"]
        assert client.post("/api/auth/consent", json={"version": version}).status_code == 204
    return client
