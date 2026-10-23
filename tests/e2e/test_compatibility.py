"""The five screen flow in Chromium, Firefox and WebKit at desktop and phone sizes.

Each run registers a synthetic pregnancy, records two visits, reads the
assessment and opens the caseload, saving one screenshot per screen to
``docs/evidence/compatibility/``. It checks the synthetic banner on every
screen, the locked synthetic box, that the assessment shows a rank and an
interval from the API, that the classification and its confidence are shown,
and that no triage wording appears.
"""

from __future__ import annotations

import re

import pytest

from tests.e2e.conftest import EVIDENCE

BROWSERS = ("chromium", "firefox", "webkit")
SIZES = ((1366, 768), (390, 844))
REGISTER = {
    "age": "24",
    "gravidity": "2",
    "prior_deliveries": "1",
    "height_cm": "156",
    "registration_weight": "58",
}
VISIT_ONE = {
    "gestational_week": "16",
    "systolic": "110",
    "diastolic": "70",
    "weight_kg": "56",
    "pulse": "80",
    "haemoglobin": "11.2",
}
VISIT_TWO = {
    "gestational_week": "22",
    "systolic": "118",
    "diastolic": "76",
    "weight_kg": "58",
    "pulse": "88",
}
FORBIDDEN = re.compile(r"see sooner|routine|high risk|low risk|priority", re.IGNORECASE)


def _fill(page, prefix: str, values: dict[str, str]) -> None:
    for field, value in values.items():
        page.fill(f"#{prefix}-{field}", value)


def _snap(page, browser: str, size: str, number: int, screen: str) -> None:
    folder = EVIDENCE / "compatibility"
    folder.mkdir(parents=True, exist_ok=True)
    page.evaluate("window.scrollTo(0, 0)")
    page.screenshot(
        path=str(folder / f"{browser}_{size}_{number:02d}-{screen}.png"), full_page=True
    )
    # A full page capture in Chromium at phone width leaves the scroll state stale,
    # so the next click lands on no element; returning to the top restores it.
    page.evaluate("window.scrollTo(0, 0)")


def _check_screen(page, section: str) -> None:
    assert page.locator(f"#{section}").is_visible()
    assert "Synthetic cases only" in page.locator("#banner").inner_text()
    assert not FORBIDDEN.search(page.locator(f"#{section}").inner_text())


@pytest.mark.parametrize("size", SIZES, ids=lambda s: f"{s[0]}x{s[1]}")
@pytest.mark.parametrize("browser_name", BROWSERS)
def test_five_screen_flow(request, launch, server, browser_name, size):
    width, height = size
    label = f"{width}x{height}"
    request.node.compatibility_key = (browser_name, label)
    page = launch(browser_name).new_page(viewport={"width": width, "height": height})
    base_url, account = server
    page.goto(f"{base_url}/register/")
    page.wait_for_selector("#sign-in-screen")
    assert "Synthetic cases only" in page.locator("#banner").inner_text()
    page.fill("#username", account.username)
    page.fill("#password", account.password)
    page.click("#sign-in")
    page.wait_for_selector("#register:not([hidden])")
    _check_screen(page, "register")
    assert page.is_checked("#synthetic") and page.is_disabled("#synthetic")
    _fill(page, "reg", REGISTER)
    _snap(page, browser_name, label, 1, "register")
    page.click("#save-register")
    page.wait_for_selector("#visit1:not([hidden])")
    _check_screen(page, "visit1")
    _fill(page, "v1", VISIT_ONE)
    _snap(page, browser_name, label, 2, "visit-one")
    page.click("#save-visit1")
    page.wait_for_selector("#visit2:not([hidden])")
    _check_screen(page, "visit2")
    _fill(page, "v2", VISIT_TWO)
    _snap(page, browser_name, label, 3, "visit-two")
    page.click("#save-visit2")
    page.wait_for_selector("#assessment:not([hidden])")
    page.locator("#rank", has_text=" of ").wait_for()
    _check_screen(page, "assessment")
    assert re.search(
        r"95% interval [\d.]+% to [\d.]+%", page.inner_text("#interval")
    )
    assert "Not a diagnosis" in page.inner_text("#limit-assessment")
    assert page.inner_text("#class-label") in (
        "Likely low birth weight",
        "Not likely low birth weight",
    )
    assert "95 percent interval" in page.inner_text("#certainty")
    assert re.search(
        r"Of every 100 labelled likely, \d+ \(95 percent interval", page.inner_text("#ppv")
    )
    _snap(page, browser_name, label, 4, "assessment")
    page.click("#to-caseload")
    page.wait_for_selector("#caseload:not([hidden])")
    page.wait_for_selector("#caseload-body tr")
    _check_screen(page, "caseload")
    assert "Not a diagnosis" in page.inner_text("#limit-caseload")
    _snap(page, browser_name, label, 5, "caseload")
