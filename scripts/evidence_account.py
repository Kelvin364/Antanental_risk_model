"""A signed in account for the evidence scripts that start their own server (decision D1).

The account is made the way an operator makes one: ``python -m webapp.app.admin
create-admin`` against the server's database, then a sign in and a password
change through the API. The database is the script's own temporary file, so
nothing outlives the run.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from http.cookies import SimpleCookie
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COOKIE = "antenatal_session"
PASSWORD = "synthetic evidence password"


@dataclass(frozen=True)
class Account:
    username: str
    password: str
    token: str
    csrf: str

    def headers(self) -> dict[str, str]:
        """Headers that authenticate a JSON request as this account."""
        return {
            "Cookie": f"{COOKIE}={self.token}",
            "X-CSRF-Token": self.csrf,
            "Content-Type": "application/json",
        }


def _post(base: str, path: str, body: dict, headers: dict[str, str]):
    request = urllib.request.Request(
        f"{base}{path}", data=json.dumps(body).encode(), method="POST", headers=headers
    )
    return urllib.request.urlopen(request, timeout=30)


def sign_in(base: str, username: str, password: str) -> tuple[str, str]:
    """The session token and CSRF token of a fresh sign in."""
    plain = {"Content-Type": "application/json"}
    with _post(base, "/api/auth/sign-in", {"username": username, "password": password}, plain) as r:
        cookie = SimpleCookie(r.headers["Set-Cookie"])
        return cookie[COOKIE].value, json.loads(r.read())["csrf_token"]


def create_account(database_url: str, base: str, username: str = "evidence") -> Account:
    """Create an administrator, sign in, and replace the generated first password."""
    env = {**os.environ, "ANTENATAL_DATABASE_URL": database_url}
    command = [sys.executable, "-m", "webapp.app.admin", "create-admin", username]
    out = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, check=True)
    first = out.stdout.strip().rsplit(": ", 1)[1]
    token, csrf = sign_in(base, username, first)
    account = Account(username, first, token, csrf)
    change = {"current_password": first, "new_password": PASSWORD}
    with _post(base, "/api/auth/password", change, account.headers()):
        pass
    return Account(username, PASSWORD, token, csrf)
