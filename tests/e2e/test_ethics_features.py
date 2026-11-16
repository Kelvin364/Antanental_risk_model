"""Consent, the Privacy Policy and Terms of Use page, and case deletion, in Chromium.

These run at 1366 by 768 in the browser the compatibility test also uses. Each
new account is made on the test server's own temporary database, so nothing
outlives the run.
"""

from __future__ import annotations


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
