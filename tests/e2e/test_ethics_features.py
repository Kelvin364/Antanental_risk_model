"""Consent, the Privacy Policy and Terms of Use page, and case deletion, in Chromium.

These run at 1366 by 768 in the browser the compatibility test also uses. Each
new account is made on the test server's own temporary database, so nothing
outlives the run.
"""

from __future__ import annotations

import json
import urllib.request


def _sign_in(page, base_url: str, account) -> None:
    page.goto(f"{base_url}/register/")
    page.wait_for_selector("#sign-in-screen")
    page.fill("#username", account.username)
    page.fill("#password", account.password)
    page.click("#sign-in")


def test_first_sign_in_asks_for_consent_once(launch, server, fresh_account):
    base_url, _ = server
    account = fresh_account("consenter")
    browser = launch("chromium")
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    _sign_in(page, base_url, account)
    page.wait_for_selector("#consent")
    page.locator("#terms-of-use", has_text="synthetic").wait_for()
    assert page.is_disabled("#agree")
    page.check("#consent-box")
    assert page.is_enabled("#agree")
    page.click("#agree")
    page.wait_for_selector("#register:not([hidden])")
    again = browser.new_page(viewport={"width": 1366, "height": 768})
    _sign_in(again, base_url, account)
    again.wait_for_selector("#register:not([hidden])")
    assert again.locator("#consent").count() == 0


SECTION_HEADINGS = (
    "What this application is",
    "Who can use it",
    "What is stored",
    "What is not stored",
    "How long it is kept",
    "Who can see what",
    "Your rights",
    "Security",
    "The research behind it",
    "Terms of Use",
)


def test_privacy_page_is_open_and_linked(launch, server):
    base_url, account = server
    browser = launch("chromium")
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    page.goto(f"{base_url}/privacy/")
    page.locator("#policy-version", has_text="Version 2026-11-16").wait_for()
    headings = page.locator("#privacy h2").all_inner_texts()
    assert tuple(headings) == SECTION_HEADINGS
    for path in ("/sign-in/", "/about/"):
        page.goto(f"{base_url}{path}")
        assert page.locator('#privacy-link[href="/privacy/"]').count() == 1
    _sign_in(page, base_url, account)
    page.wait_for_selector("#register:not([hidden])")
    page.goto(f"{base_url}/account/")
    page.wait_for_selector("#change-password")
    assert page.locator('#privacy-link[href="/privacy/"]').count() == 1


def _api(base_url: str, account, method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        f"{base_url}{path}", data=data, method=method, headers=account.headers()
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read() or b"{}")


def test_a_case_is_deleted_from_the_assessment_screen(launch, server):
    base_url, account = server
    case = {"synthetic": True, "label": "Delete me", "age": 24, "gravidity": 2}
    case |= {"prior_deliveries": 1, "height_cm": 156, "registration_weight": 58}
    case_id = _api(base_url, account, "POST", "/api/cases", case)["id"]
    visits = (
        {"gestational_week": 16, "systolic": 110, "diastolic": 70, "weight_kg": 56},
        {"gestational_week": 22, "systolic": 118, "diastolic": 76, "weight_kg": 58},
    )
    for number, visit in enumerate(visits, 1):
        _api(base_url, account, "PUT", f"/api/cases/{case_id}/visits/{number}", visit)
    _api(base_url, account, "POST", f"/api/cases/{case_id}/assessment")
    page = launch("chromium").new_page(viewport={"width": 1366, "height": 768})
    _sign_in(page, base_url, account)
    page.wait_for_selector("#register:not([hidden])")
    page.goto(f"{base_url}/assessment/?case={case_id}")
    page.locator("#rank", has_text=" of ").wait_for()
    page.click(f"#delete-case-{case_id}")
    confirm = page.locator(f"#confirm-delete-{case_id}")
    confirm.locator("text=Delete case Delete me? This cannot be undone.").wait_for()
    confirm.locator("button.keep").click()
    assert confirm.count() == 0
    assert _api(base_url, account, "GET", f"/api/cases/{case_id}")["id"] == case_id
    page.click(f"#delete-case-{case_id}")
    page.locator(f"#confirm-delete-{case_id} button.confirm").click()
    page.wait_for_selector("#caseload:not([hidden])")
    page.wait_for_load_state("networkidle")
    assert "Delete me" not in page.inner_text("#caseload")
