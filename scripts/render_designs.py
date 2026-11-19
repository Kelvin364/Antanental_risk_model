"""Regenerate the design images in designs/web/ from the live interface.

Usage: ``python scripts/render_designs.py`` (needs ``make browsers`` once).
The script starts its own server with a temporary database, signs in, agrees to the
Terms of Use, walks the five screens in Chromium at 1366 by 768 with a synthetic case,
and saves ``00-sign-in.png`` to ``05-caseload.png``. It then captures the consent page
(06), the Privacy Policy and Terms of Use (07), the in page confirmation of a case
deletion (08), a researcher's removal request (09), the administrator's list of removal
requests (10), and the stored consent row of the user table (11), whose password
appears only as its scrypt hash. It stops with an error if any screen shows triage
wording, so a design image can never carry it.
"""

from __future__ import annotations

import html
import json
import os
import re
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_account import PASSWORD, create_account, sign_in  # noqa: E402

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
    text = page.locator(f"#{section}").inner_text()
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
    page.locator("#terms-of-use", has_text="real pregnancy").wait_for()
    page.check("#consent-box")
    shots.append(_capture(page, "consent", "06-consent"))
    page.click("#agree")
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
    page.click(".delete-case")
    page.locator(".confirm-delete", has_text="cannot be undone").wait_for()
    page.locator(".confirm-delete").scroll_into_view_if_needed()
    shots.append(_capture(page, "assessment", "08-delete-case"))
    page.click(".confirm-delete .keep")
    page.click("#to-caseload")
    page.wait_for_selector("#caseload-body tr")
    shots.append(_capture(page, "caseload", "05-caseload"))
    page.goto(page.url.split("/caseload")[0] + "/privacy/")
    page.locator("#policy-version", has_text="Version").wait_for()
    shots.append(_capture(page, "privacy", "07-privacy"))
    return shots


def _call(base: str, token: str, csrf: str, path: str, body: dict | None = None) -> dict:
    headers = {"Cookie": f"antenatal_session={token}", "X-CSRF-Token": csrf}
    headers["Content-Type"] = "application/json"
    data = json.dumps(body if body is not None else {}).encode()
    request = urllib.request.Request(f"{base}{path}", data=data, method="POST", headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read() or b"{}")


def _researcher(base: str, admin) -> tuple[str, str]:
    """A researcher made by the administrator, with a chosen password and the terms accepted."""
    made = _call(
        base,
        admin.token,
        admin.csrf,
        "/api/admin/users",
        {"username": "rehema", "role": "researcher"},
    )
    token, csrf = sign_in(base, "rehema", made["password"])
    _call(base, token, csrf, "/api/auth/password",
          {"current_password": made["password"], "new_password": PASSWORD})  # fmt: skip
    version = json.loads(urllib.request.urlopen(f"{base}/api/policy", timeout=30).read())["version"]
    _call(base, token, csrf, "/api/auth/consent", {"version": version})
    return "rehema", PASSWORD


def _removal(browser, url: str, admin_page: Page, admin) -> list[Path]:
    username, password = _researcher(url, admin)
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    page.goto(f"{url}/sign-in/")
    page.fill("#username", username)
    page.fill("#password", password)
    page.click("#sign-in")
    page.wait_for_selector("#register:not([hidden])")
    page.goto(f"{url}/account/")
    page.click("#request-removal")
    page.wait_for_selector("#removal-pending")
    shots = [_capture(page, "account", "09-account-removal")]
    admin_page.goto(f"{url}/admin/")
    admin_page.wait_for_selector("#removal-requests .remove-account")
    shots.append(_capture(admin_page, "administration", "10-admin-removal"))
    return shots


def _consent_row(browser, database: Path, username: str) -> Path:
    """The stored user row as a query result: version and time of consent, hash only."""
    query = (
        "SELECT id, username, role, password_hash, terms_version, terms_accepted_at "
        f"FROM users WHERE username = '{username}';"
    )
    with sqlite3.connect(database) as connection:
        cursor = connection.execute(query)
        names = [d[0] for d in cursor.description]
        row = cursor.fetchone()
    lines = "".join(
        f"<tr><th>{html.escape(n)}</th><td>{html.escape(str(v))}</td></tr>"
        for n, v in zip(names, row, strict=True)
    )
    page = browser.new_page(viewport={"width": 1366, "height": 400})
    page.set_content(
        "<body style='font:14px ui-monospace,Menlo,monospace;padding:24px;background:#fff'>"
        f"<p>$ sqlite3 app.sqlite3</p><p>sqlite&gt; {html.escape(query)}</p>"
        "<table style='border-collapse:collapse' cellpadding='6' border='1'>"
        f"{lines}</table></body>"
    )
    path = OUT / "11-consent-row.png"
    page.screenshot(path=str(path), full_page=True)
    return path


def main() -> int:
    if not (ROOT / "frontend" / "out" / "index.html").exists():
        raise SystemExit("The interface is not built; run `make frontend` first.")
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        database = Path(tmp) / "designs.sqlite3"
        server, url = _server(database)
        try:
            account = create_account(f"sqlite:///{database}", url, "designer", consent=False)
            with sync_playwright() as session:
                browser = session.chromium.launch()
                page = browser.new_page(viewport={"width": 1366, "height": 768})
                page.goto(f"{url}/register/")
                shots = _walk(page, account.username, account.password)
                admin = sign_in(url, account.username, account.password)
                admin = type("Admin", (), {"token": admin[0], "csrf": admin[1]})
                shots += _removal(browser, url, page, admin)
                shots.append(_consent_row(browser, database, account.username))
                browser.close()
        finally:
            server.terminate()
            server.wait(timeout=30)
    for path in shots:
        print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
