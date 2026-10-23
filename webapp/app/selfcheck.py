"""Check that this installation serves the frozen model end to end.

It starts a second server of this code on a free local port with a throwaway
database, creates a temporary researcher there, and over real HTTP checks that a
request without sign in is refused, signs in, replaces the first password, scores a
reference synthetic case and refuses an out of range one. The probability served
over HTTP must equal the frozen artefact scored directly to 1e-9. The live database
and its accounts are never touched, and the throwaway database is deleted. On the
host: ``fly ssh console --app antenatal-caseload -C "python -m webapp.app.selfcheck"``.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from http.cookies import SimpleCookie
from pathlib import Path

from webapp.app.core.settings import Settings
from webapp.app.db.database import create_session_factory
from webapp.app.schemas.cases import CaseCreate, VisitCreate
from webapp.app.services.auth_service import RESEARCHER, AuthService
from webapp.app.services.model_service import ModelService, study_values

ROOT = Path(__file__).resolve().parents[2]
CASE = {
    "synthetic": True,
    "age": 24,
    "gravidity": 2,
    "prior_deliveries": 1,
    "height_cm": 156,
    "registration_weight": 58,
}
VISIT_ONE = {"gestational_week": 16, "systolic": 110, "diastolic": 70, "weight_kg": 56, "pulse": 80}
VISIT_TWO = {"gestational_week": 22, "systolic": 118, "diastolic": 76, "weight_kg": 58, "pulse": 88}
NEW_PASSWORD = "throwaway self check password"


def _call(base: str, path: str, body: dict | None, headers: dict) -> tuple[int, dict, str]:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        f"{base}{path}",
        data=data,
        headers={"Content-Type": "application/json", **headers},
        method="POST" if data else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read()
            return response.status, json.loads(raw or b"{}"), response.headers.get("Set-Cookie", "")
    except urllib.error.HTTPError as refused:
        return refused.code, {}, ""


def _start(database: Path) -> tuple[subprocess.Popen, str]:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = {**os.environ, "ANTENATAL_DATABASE_URL": f"sqlite:///{database}"}
    command = [sys.executable, "-m", "uvicorn", "webapp.app.main:app", "--port", str(port)]
    server = subprocess.Popen(
        command, cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    base = f"http://127.0.0.1:{port}"
    for _ in range(600):
        try:
            urllib.request.urlopen(f"{base}/health", timeout=1)
            return server, base
        except OSError:
            time.sleep(0.1)
    server.kill()
    raise RuntimeError("the check server did not start")


def _http_checks(base: str, first_password: str) -> dict[str, object]:
    status_anon, _, _ = _call(base, "/api/caseload", None, {})
    status, signed, cookie = _call(
        base, "/api/auth/sign-in", {"username": "selfcheck", "password": first_password}, {}
    )
    headers = {
        "Cookie": f"antenatal_session={SimpleCookie(cookie)['antenatal_session'].value}",
        "X-CSRF-Token": signed.get("csrf_token", ""),
    }
    _call(
        base,
        "/api/auth/password",
        {"current_password": first_password, "new_password": NEW_PASSWORD},
        headers,
    )
    payload = {"case": CASE, "visit_one": VISIT_ONE, "visit_two": VISIT_TWO}
    status_ok, served, _ = _call(base, "/api/predict", payload, headers)
    bad = {**payload, "case": {**CASE, "age": 121}}
    status_bad, _, _ = _call(base, "/api/predict", bad, headers)
    return {
        "refused_without_sign_in": status_anon == 401,
        "signed_in": status == 200,
        "scored": status_ok == 200,
        "out_of_range_refused": status_bad == 422,
        "served": served,
    }


def run() -> dict[str, object]:
    """Every check, with the served and the direct probability side by side."""
    settings = Settings.from_env()
    model = ModelService(settings.model_dir)
    direct = model.predict(
        study_values(CaseCreate(**CASE), VisitCreate(**VISIT_ONE), VisitCreate(**VISIT_TWO))
    )
    with tempfile.TemporaryDirectory() as tmp:
        database = Path(tmp) / "selfcheck.sqlite3"
        auth = AuthService(create_session_factory(f"sqlite:///{database}"))
        _, first = auth.create_user("selfcheck", RESEARCHER, "self check")
        server, base = _start(database)
        try:
            checks = _http_checks(base, first)
        finally:
            server.terminate()
            server.wait(timeout=30)
    served = checks.pop("served")
    probability = served.get("probability", float("nan"))
    checks["served_equals_direct_to_1e-9"] = abs(probability - direct.probability) <= 1e-9
    return {
        "artefact_version": model.version,
        "artefact_sha256": model.sha256,
        "probability_served": probability,
        "probability_direct": direct.probability,
        "interval": [served.get("interval_low"), served.get("interval_high")],
        "rank": served.get("rank_position"),
        "label": served.get("classification", {}).get("label"),
        "checks": checks,
        "all_passed": all(checks.values()),
    }


def main() -> int:
    result = run()
    print(json.dumps(result, indent=2))
    return 0 if result["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
