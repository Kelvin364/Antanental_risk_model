"""Check a running deployment end to end, online or local (decision D7).

Usage: ``python scripts/smoke_test.py --base-url https://ADDRESS --username U --password P``
with a researcher account whose first password has been changed. With
``--record`` the result is written to ``docs/evidence/deployment.md`` with the
address, the commit and the date. Exits with status 1 if any check fails.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
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


def _public_checks(base: str) -> list[tuple[str, bool, str]]:
    """What anyone can see: health, the sign in page, headers, and refusal without sign in."""
    expected = (ROOT / "webapp" / "model" / "lbw_model.sha256").read_text().split()[0]
    with httpx.Client(base_url=base, timeout=60, follow_redirects=True) as anon:
        served = anon.get("/health").json().get("artefact_sha256", "")
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


def _checks(base: str, username: str, password: str) -> list[tuple[str, bool, str]]:
    return _public_checks(base) + _signed_in_checks(base, username, password)


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
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    if args.public_only:
        results = _public_checks(base)
    elif args.username and args.password:
        results = _checks(base, args.username, args.password)
    else:
        parser.error("pass --username and --password of a researcher, or --public-only")
    for name, ok, detail in results:
        print(f"{'pass' if ok else 'FAIL'}  {name}  {detail}")
    if args.record:
        _record(args.base_url, results, signed_in=not args.public_only)
    return 0 if all(ok for _, ok, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
