"""Check a running deployment end to end, online or local (decision D7).

Usage: ``python scripts/smoke_test.py --base-url https://ADDRESS --username U --password P``
with a researcher account whose first password has been changed. With
``--record`` the result is written to ``docs/evidence/deployment.md`` with the
address, the commit and the date. Exits with status 1 if any check fails.

``--expect-database postgresql`` adds a check that ``/health`` reports the hosted
database, so a Render service that lost its database address is caught.

Persistence across a restart takes two runs. ``--leave-case`` registers and assesses one
synthetic case, leaves it in place and prints its number and probability. Restart the
service (Render dashboard, Manual Deploy or Restart), then run again with
``--expect-case NUMBER:PROBABILITY``: the check passes only if the same case comes back
with the same stored probability.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
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


def _public_checks(base: str, database: str | None = None) -> list[tuple[str, bool, str]]:
    """What anyone can see: health, the sign in page, headers, and refusal without sign in."""
    expected = (ROOT / "webapp" / "model" / "lbw_model.sha256").read_text().split()[0]
    with httpx.Client(base_url=base, timeout=90, follow_redirects=True) as anon:
        health = anon.get("/health").json()
        served = health.get("artefact_sha256", "")
        page = anon.get("/sign-in/")
        refused = anon.get("/api/caseload").status_code
    headers = page.headers
    out = [
        ("Health answers with the frozen artefact", served == expected, served[:16]),
        ("Sign in page is served", page.status_code == 200, str(page.status_code)),
        (
            "Security headers present",
            headers.get("x-frame-options") == "DENY",
            headers.get("content-security-policy", "")[:40],
        ),
        ("Caseload refused without sign in", refused == 401, str(refused)),
    ]
    if base.startswith("https"):
        out.append(("HSTS over HTTPS", "strict-transport-security" in headers, ""))
    if database:
        connected = str(health.get("database", "not reported"))
        out.append((f"Health reports a {database} database", connected == database, connected))
    return out


def _signed_in_checks(base: str, username: str, password: str) -> list[tuple[str, bool, str]]:
    """What a signed in researcher can and cannot do."""
    with httpx.Client(base_url=base, timeout=60) as client:
        signed = client.post("/api/auth/sign-in", json={"username": username, "password": password})
        cookie = signed.headers.get("set-cookie", "").lower()
        no_csrf = client.post("/api/predict", json=PREDICT).status_code
        client.headers["X-CSRF-Token"] = signed.json().get("csrf_token", "")
        valid = client.post("/api/predict", json=PREDICT)
        label = valid.json().get("classification", {}).get("label", "") if valid.is_success else ""
        bad = client.post("/api/predict", json={**PREDICT, "case": {**CASE, "age": 121}})
        flagless = client.post(
            "/api/predict", json={**PREDICT, "case": {**CASE, "synthetic": False}}
        )
        role = client.get("/api/admin/users").status_code
    out = [
        ("Sign in succeeds", signed.status_code == 200, str(signed.status_code)),
        (
            "Session cookie is HttpOnly and SameSite strict",
            "httponly" in cookie and "samesite=strict" in cookie,
            "",
        ),
        ("Change refused without the CSRF token", no_csrf == 403, str(no_csrf)),
        ("Valid synthetic case is scored and labelled", bool(label), label),
        ("Age 121 refused", bad.status_code == 422, str(bad.status_code)),
        ("Missing synthetic flag refused", flagless.status_code == 422, str(flagless.status_code)),
        ("Researcher refused administration", role == 403, str(role)),
    ]
    if base.startswith("https"):
        out.append(("Session cookie is Secure", "secure" in cookie, ""))
    return out


def _checks(
    base: str, username: str, password: str, database: str | None = None
) -> list[tuple[str, bool, str]]:
    return _public_checks(base, database) + _signed_in_checks(base, username, password)


def _session(base: str, username: str, password: str) -> httpx.Client:
    client = httpx.Client(base_url=base, timeout=90)
    signed = client.post("/api/auth/sign-in", json={"username": username, "password": password})
    signed.raise_for_status()
    client.headers["X-CSRF-Token"] = signed.json()["csrf_token"]
    return client


def leave_case(base: str, username: str, password: str) -> tuple[int, float]:
    """Register, record and assess one synthetic case and leave it stored."""
    with closing(_session(base, username, password)) as client:
        case = client.post("/api/cases", json={**CASE, "label": "persistence check"})
        case.raise_for_status()
        number = case.json()["id"]
        for visit, values in ((1, VISIT_ONE), (2, VISIT_TWO)):
            client.put(f"/api/cases/{number}/visits/{visit}", json=values).raise_for_status()
        assessed = client.post(f"/api/cases/{number}/assessment")
        assessed.raise_for_status()
        return number, assessed.json()["probability"]


def persistence_check(
    base: str, username: str, password: str, expected: str
) -> tuple[str, bool, str]:
    """The case left before a restart comes back with the same stored probability."""
    number, probability = expected.split(":")
    with closing(_session(base, username, password)) as client:
        found = client.get(f"/api/cases/{number}")
    latest = (found.json().get("latest_assessment") or {}) if found.is_success else {}
    stored = latest.get("probability")
    same = stored is not None and abs(stored - float(probability)) < 1e-12
    return ("Case survives a restart unchanged", same, f"case {number}, {stored}")


def _record(base: str, results: list[tuple[str, bool, str]], signed_in: bool = True) -> None:
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True
    ).stdout.strip()
    rows = "\n".join(
        f"| {name} | {'pass' if ok else 'fail'} | {detail} |" for name, ok, detail in results
    )
    passed = sum(ok for _, ok, _ in results)
    who = (
        "signed in as a researcher account"
        if signed_in
        else "without an account (the signed in checks run once the first accounts exist)"
    )
    (ROOT / "docs" / "evidence" / "deployment.md").write_text(f"""# Deployment evidence

Checked by `scripts/smoke_test.py` against {base} at commit `{commit}` on
{datetime.now(UTC).isoformat(timespec="seconds")}, {who}.
Synthetic cases only; the image holds no data file and no partition file.

| Check | Result | Detail |
| --- | --- | --- |
{rows}

{passed} of {len(results)} checks passed. A changed artefact refusing to start is tested
locally (`tests/integration/test_api.py::test_tampered_artefact_refuses_to_start`).
""")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--username", help="a researcher account")
    parser.add_argument("--password")
    parser.add_argument(
        "--public-only", action="store_true", help="only the checks without sign in"
    )
    parser.add_argument("--record", action="store_true", help="write docs/evidence/deployment.md")
    parser.add_argument(
        "--expect-database", choices=["postgresql", "sqlite"], help="the database /health names"
    )
    parser.add_argument(
        "--leave-case", action="store_true", help="store one case to check after a restart"
    )
    parser.add_argument("--expect-case", metavar="NUMBER:PROBABILITY")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    if args.public_only:
        results = _public_checks(base, args.expect_database)
    elif args.username and args.password:
        results = _checks(base, args.username, args.password, args.expect_database)
    else:
        parser.error("pass --username and --password of a researcher, or --public-only")
    if args.expect_case and not args.public_only:
        results.append(persistence_check(base, args.username, args.password, args.expect_case))
    if args.leave_case and not args.public_only:
        number, probability = leave_case(base, args.username, args.password)
        print(
            f"Left case {number}. After a restart, rerun with "
            f"--expect-case {number}:{probability!r}"
        )
    for name, ok, detail in results:
        print(f"{'pass' if ok else 'FAIL'}  {name}  {detail}")
    if args.record:
        _record(args.base_url, results, signed_in=not args.public_only)
    return 0 if all(ok for _, ok, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
