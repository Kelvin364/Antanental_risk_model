"""Measure the accessibility of the five screens with Lighthouse.

Usage: ``python scripts/accessibility_audit.py``. The script starts its own
server on a free local port with a temporary database, records one synthetic
case through the API so every screen has content, then runs the Lighthouse
accessibility category (the axe-core rules) on each screen at phone and
desktop sizes in the Chromium that Playwright installs. It writes
``docs/evidence/accessibility.md`` and ``docs/evidence/accessibility.json``.

Lighthouse is fetched by ``npx`` at a pinned version rather than installed in
``frontend/``, so it never enters the interface's dependencies or its image.
It needs Node.js, the built interface (``make frontend``) and ``make browsers``.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from benchmark_api import PAYLOAD, free_port, start_server  # noqa: E402
from evidence_account import create_account  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LIGHTHOUSE = "lighthouse@12.8.2"
SCREENS = (
    ("Sign in", "/sign-in/"),
    ("About", "/about/"),
    ("Administration", "/admin/"),
    ("Register", "/register/"),
    ("Visit one", "/visit-one/"),
    ("Visit two", "/visit-two/"),
    ("Assessment", "/assessment/"),
    ("Caseload", "/caseload/"),
)
# Lighthouse's default is a phone (412 by 823, touch); the desktop preset is 1350 by 940.
SIZES = (("phone", []), ("desktop", ["--preset=desktop"]))


def call(base: str, headers: dict, method: str, path: str, body: dict | None = None) -> dict:
    """One signed in JSON request to the API."""
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(f"{base}{path}", data=data, method=method, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def record_case(base: str, headers: dict) -> int:
    """Register the benchmark's synthetic case, save both visits and assess it."""
    payload = json.loads(PAYLOAD)
    case = call(base, headers, "POST", "/api/cases", {**payload["case"], "label": "Audit case"})
    call(base, headers, "PUT", f"/api/cases/{case['id']}/visits/1", payload["visit_one"])
    call(base, headers, "PUT", f"/api/cases/{case['id']}/visits/2", payload["visit_two"])
    call(base, headers, "POST", f"/api/cases/{case['id']}/assessment")
    return case["id"]


def lighthouse(url: str, flags: list[str], chrome: str, cookie: str) -> dict:
    """The accessibility score and every failed audit of one page."""
    npx = shutil.which("npx")
    if npx is None:
        raise RuntimeError("npx not found; install Node.js 20.9 or newer")
    command = [
        npx,
        "--yes",
        LIGHTHOUSE,
        url,
        "--only-categories=accessibility",
        "--output=json",
        "--quiet",
        "--chrome-flags=--headless=new --no-sandbox",
        f"--extra-headers={json.dumps({'Cookie': cookie})}",
        *flags,
    ]
    env = {**os.environ, "CHROME_PATH": chrome}
    # Under WSL the Chrome launcher names its profile folder after the Windows
    # user directory, relative to the working directory; keep it out of the repository.
    with tempfile.TemporaryDirectory() as scratch:
        done = subprocess.run(
            command, capture_output=True, text=True, env=env, cwd=scratch, check=False
        )
    if done.returncode != 0:
        raise RuntimeError(f"Lighthouse failed on {url}: {done.stderr[-2000:]}")
    report = json.loads(done.stdout)
    category = report["categories"]["accessibility"]
    audits = report["audits"]
    failed = [
        {"id": ref["id"], "title": audits[ref["id"]]["title"], "weight": ref["weight"]}
        for ref in category["auditRefs"]
        if ref["weight"] > 0 and audits[ref["id"]]["score"] == 0
    ]
    passed = sum(
        1 for ref in category["auditRefs"] if ref["weight"] > 0 and audits[ref["id"]]["score"] == 1
    )
    return {
        "score": round(category["score"] * 100),
        "audits_passed": passed,
        "failed": failed,
        "lighthouse": report["lighthouseVersion"],
        "user_agent": report["environment"]["hostUserAgent"],
    }


def run() -> dict[str, object]:
    if not (ROOT / "frontend" / "out" / "index.html").exists():
        raise RuntimeError("frontend/out is missing; run `make frontend` first")
    with sync_playwright() as session:
        chrome = session.chromium.executable_path
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        database = Path(tmp) / "audit.sqlite3"
        server, _ = start_server(port, database)
        try:
            headers = create_account(f"sqlite:///{database}", base).headers()
            case_id = record_case(base, headers)
            for screen, path in SCREENS:
                for size, flags in SIZES:
                    url = f"{base}{path}?case={case_id}"
                    result = lighthouse(url, flags, chrome, headers["Cookie"])
                    rows.append({"screen": screen, "path": path, "size": size, **result})
                    print(f"{screen:<11} {size:<7} {result['score']}", flush=True)
        finally:
            server.terminate()
            server.wait(timeout=30)
    return {
        "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "lighthouse": rows[0]["lighthouse"],
        "browser": rows[0]["user_agent"],
        "os": platform.platform(),
        "results": [
            {k: v for k, v in r.items() if k not in ("lighthouse", "user_agent")} for r in rows
        ],
    }


def failed_audits(rows: list[dict]) -> str:
    """Every failed audit with the screens and sizes it failed on, as a Markdown list."""
    failures = sorted({(f["id"], f["title"]) for r in rows for f in r["failed"]})
    if not failures:
        return "None. Every weighted audit passed on every screen at both sizes."
    return "\n".join(
        f"* `{fid}`: {title} (on "
        + ", ".join(
            f"{r['screen']} {r['size']}" for r in rows if fid in {f["id"] for f in r["failed"]}
        )
        + ")"
        for fid, title in failures
    )


def write(result: dict[str, object]) -> None:
    out = ROOT / "docs" / "evidence"
    out.mkdir(parents=True, exist_ok=True)
    (out / "accessibility.json").write_text(json.dumps(result, indent=2) + "\n")
    rows = result["results"]
    scores = {(r["screen"], r["size"]): r for r in rows}
    table = "\n".join(
        f"| {screen} | {scores[(screen, 'phone')]['score']} "
        f"| {scores[(screen, 'desktop')]['score']} |"
        for screen, _ in SCREENS
    )
    found = failed_audits(rows)
    lowest = min(r["score"] for r in rows)
    text = f"""# Accessibility evidence

Measured by `scripts/accessibility_audit.py` on {result["recorded_at"]} with Lighthouse
{result["lighthouse"]} (accessibility category only, which runs the axe-core rules) in
{result["browser"]} on {result["os"]}. The script started its own server with a temporary
database, recorded one synthetic case with both visits and an assessment through the API,
and audited each screen with that case open. The phone run uses Lighthouse's default
mobile emulation and the desktop run its desktop preset. The raw results are in
`accessibility.json`.

## Scores out of 100

| Screen | Phone | Desktop |
| --- | --- | --- |
{table}

The lowest score is {lowest}.

## Failed audits

{found}

An automated audit checks only what a program can detect, such as contrast, labels,
names, roles and document structure. It does not show that the screens are usable with
a screen reader or by keyboard alone, which needs a person to test them.
"""
    (out / "accessibility.md").write_text(text)


if __name__ == "__main__":
    outcome = run()
    write(outcome)
    print(json.dumps({k: v for k, v in outcome.items() if k != "results"}, indent=2))
