"""Browser test fixtures: one local server, browsers launched on demand, and the result matrix.

Every test here is marked ``e2e``. When Playwright or a browser is not
installed, the affected tests are skipped, so ``make test`` still runs on a
machine without browsers. When any e2e test ran, the session writes
``docs/evidence/compatibility.md`` with the pass or fail matrix, the browser
versions and the operating system.
"""

from __future__ import annotations

import os
import platform
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs" / "evidence"
RESULTS: dict[tuple[str, str], str] = {}
VERSIONS: dict[str, str] = {}

playwright_api = pytest.importorskip("playwright.sync_api")


def pytest_collection_modifyitems(items):
    for item in items:
        if "tests/e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)


@pytest.fixture(scope="session")
def base_url(tmp_path_factory):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    database = tmp_path_factory.mktemp("e2e") / "app.sqlite3"
    env = {**os.environ, "ANTENATAL_DATABASE_URL": f"sqlite:///{database}"}
    command = [sys.executable, "-m", "uvicorn", "webapp.app.main:app", "--port", str(port)]
    server = subprocess.Popen(
        command, cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    url = f"http://127.0.0.1:{port}"
    for _ in range(600):
        try:
            urllib.request.urlopen(f"{url}/health", timeout=1)
            break
        except OSError:
            time.sleep(0.1)
    yield url
    server.terminate()
    server.wait(timeout=30)


@pytest.fixture(scope="session")
def playwright_session():
    with playwright_api.sync_playwright() as session:
        yield session


@pytest.fixture
def launch(playwright_session):
    opened = []

    def _launch(name: str):
        try:
            browser = getattr(playwright_session, name).launch()
        except Exception as error:  # noqa: BLE001  any launch failure means the browser is absent
            pytest.skip(f"{name} is not installed: {error}")
        VERSIONS[name] = browser.version
        opened.append(browser)
        return browser

    yield _launch
    for browser in opened:
        browser.close()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    key = getattr(item, "compatibility_key", None)
    if key and report.when == "call":
        RESULTS[key] = "pass" if report.passed else "fail"


def pytest_sessionfinish(session):
    if not RESULTS:
        return
    browsers = sorted({b for b, _ in RESULTS})
    sizes = sorted({s for _, s in RESULTS}, reverse=True)
    lines = ["| Browser | Version | " + " | ".join(sizes) + " |"]
    lines.append("| --- | --- | " + " | ".join("---" for _ in sizes) + " |")
    for browser in browsers:
        cells = [RESULTS.get((browser, size), "not run") for size in sizes]
        lines.append(
            f"| {browser} | {VERSIONS.get(browser, 'unknown')} | " + " | ".join(cells) + " |"
        )
    failures = sum(1 for value in RESULTS.values() if value != "pass")
    text = (
        "# Compatibility evidence\n\n"
        f"Recorded by `pytest tests/e2e` on {datetime.now(UTC).isoformat(timespec='seconds')} "
        f"on {platform.platform()} with Playwright. Each cell is the full five screen flow "
        "(register, visit one, visit two, assessment, caseload) at that window size. "
        "Screenshots are in `compatibility/`, one per screen per browser per size.\n\n"
        + "\n".join(lines)
        + f"\n\n{len(RESULTS) - failures} of {len(RESULTS)} runs passed.\n"
    )
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "compatibility.md").write_text(text)
