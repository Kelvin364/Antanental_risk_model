"""Regenerate the design images in designs/web/ from the live interface.

Usage: ``python scripts/render_designs.py`` (needs ``make browsers`` once).
The script starts its own server with a temporary database, signs in, walks the five
screens in Chromium at 1366 by 768 with a synthetic case, and saves
``01-register.png`` to ``05-caseload.png``. It stops with an error if any
screen shows triage wording, so a design image can never carry it.
"""

from __future__ import annotations

import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_account import create_account  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "designs" / "web"
FORBIDDEN = re.compile(r"see sooner|routine|high risk|low risk|priority", re.IGNORECASE)
REGISTER = {"age": "24", "gravidity": "2", "prior_deliveries": "1", "height_cm": "156"}
REGISTER["registration_weight"] = "58"
VISIT_ONE = {"gestational_week": "16", "systolic": "110", "diastolic": "70", "weight_kg": "56"}
VISIT_ONE.update({"pulse": "80", "haemoglobin": "11.2"})
VISIT_TWO = {"gestational_week": "22", "systolic": "118", "diastolic": "76", "weight_kg": "58"}
VISIT_TWO["pulse"] = "88"


def _server(database: Path) -> tuple[subprocess.Popen, str]:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = {**os.environ, "ANTENATAL_DATABASE_URL": f"sqlite:///{database}"}
    command = [sys.executable, "-m", "uvicorn", "webapp.app.main:app", "--port", str(port)]
    server = subprocess.Popen(
        command, cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    url = f"http://127.0.0.1:{port}"
    for _ in range(600):
        try:
            urllib.request.urlopen(f"{url}/health", timeout=1)
            return server, url
        except OSError:
            time.sleep(0.1)
    server.kill()
    raise RuntimeError("server did not start")


def _capture(page: Page, section: str, name: str) -> Path:
    text = page.locator(f"#{section}").inner_text() + page.locator("#banner").inner_text()
    if FORBIDDEN.search(text):
        raise RuntimeError(f"{name} shows triage wording")
    page.evaluate("window.scrollTo(0, 0)")
    path = OUT / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    page.evaluate("window.scrollTo(0, 0)")
    return path


def _fill(page: Page, prefix: str, values: dict[str, str]) -> None:
    for field, value in values.items():
        page.fill(f"#{prefix}-{field}", value)


def _walk(page: Page, username: str, password: str) -> list[Path]:
    page.wait_for_selector("#sign-in-screen")
    page.fill("#username", username)
    shots = [_capture(page, "sign-in-screen", "00-sign-in")]
    page.fill("#password", password)
    page.click("#sign-in")
    page.wait_for_selector("#register:not([hidden])")
    _fill(page, "reg", REGISTER)
    shots.append(_capture(page, "register", "01-register"))
    page.click("#save-register")
    page.wait_for_selector("#visit1:not([hidden])")
    _fill(page, "v1", VISIT_ONE)
    shots.append(_capture(page, "visit1", "02-visit-one"))
    page.click("#save-visit1")
    page.wait_for_selector("#visit2:not([hidden])")
    _fill(page, "v2", VISIT_TWO)
    shots.append(_capture(page, "visit2", "03-visit-two"))
    page.click("#save-visit2")
    page.wait_for_selector("#assessment:not([hidden])")
    page.locator("#rank", has_text=" of ").wait_for()
    shots.append(_capture(page, "assessment", "04-assessment"))
    page.click("#to-caseload")
    page.wait_for_selector("#caseload-body tr")
    shots.append(_capture(page, "caseload", "05-caseload"))
    return shots


def main() -> int:
    if not (ROOT / "frontend" / "out" / "index.html").exists():
        raise SystemExit("The interface is not built; run `make frontend` first.")
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        database = Path(tmp) / "designs.sqlite3"
        server, url = _server(database)
        try:
            account = create_account(f"sqlite:///{database}", url, "designer")
            with sync_playwright() as session:
                browser = session.chromium.launch()
                page = browser.new_page(viewport={"width": 1366, "height": 768})
                page.goto(f"{url}/register/")
                shots = _walk(page, account.username, account.password)
                browser.close()
        finally:
            server.terminate()
            server.wait(timeout=30)
    for path in shots:
        print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
