"""Sign a test client in through the real sign in route (decision D1)."""

from __future__ import annotations

from fastapi.testclient import TestClient

NEW_PASSWORD = "a long synthetic test password"


def sign_in_as(client: TestClient, username: str, role: str = "researcher") -> TestClient:
    """Create the account, sign in, replace the first password and keep the CSRF header."""
    _, first = client.app.state.auth.create_user(username, role, "test")
    response = client.post("/api/auth/sign-in", json={"username": username, "password": first})
    assert response.status_code == 200, response.text
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    change = {"current_password": first, "new_password": NEW_PASSWORD}
    assert client.post("/api/auth/password", json=change).status_code == 204
    return client
