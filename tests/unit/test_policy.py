"""The Privacy Policy and Terms of Use: version, order, plain wording and the facts it states."""

from __future__ import annotations

import re
from datetime import date

from webapp.app.api.auth import terms
from webapp.app.core import policy
from webapp.app.core.security import MAX_BODY_BYTES
from webapp.app.core.settings import Settings
from webapp.app.services.auth_service import MAX_FAILURES, SESSION_HOURS

HEADINGS = [
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
]
APPROVAL = "SEPT26-BSE-064"


def _all_text() -> str:
    sentences = " ".join(policy.SENTENCES.values())
    sections = " ".join(f"{h} {t}" for h, t in policy.SECTIONS)
    return " ".join([sections, sentences, policy.CONSENT_SENTENCE, policy.CONSENT_REQUIRED])


def test_version_is_a_date_and_the_ten_sections_come_in_order():
    assert date.fromisoformat(policy.POLICY_VERSION).isoformat() == policy.POLICY_VERSION
    assert [heading for heading, _ in policy.SECTIONS] == HEADINGS
    assert all(text.strip() for _, text in policy.SECTIONS)
    assert sum(len(f"{h} {t}".split()) for h, t in policy.SECTIONS) <= 600


def test_no_dash_is_used_as_punctuation():
    text = _all_text().replace(APPROVAL, "")
    assert not re.search(r"[\-‐-―]", text)
    assert "lorem" not in text.lower()


def test_the_policy_names_what_the_code_does():
    text = _all_text()
    for phrase in ("synthetic", "seven days", "scrypt", "MIT", "CC BY 4.0", APPROVAL):
        assert phrase in text
    assert Settings.from_env().case_retention_days == 7
    assert f"{MAX_BODY_BYTES // 1024} KB" in text
    assert "eight hours" in text and SESSION_HOURS == 8
    assert "five failures" in text and MAX_FAILURES == 5


def test_the_api_serves_these_exact_sentences():
    served = terms()
    assert served.version == policy.POLICY_VERSION
    assert served.consent_sentence == policy.CONSENT_SENTENCE
    assert served.terms_of_use == policy.TERMS_OF_USE == dict(policy.SECTIONS)["Terms of Use"]
    assert [(s.heading, s.text) for s in served.sections] == list(policy.SECTIONS)
    assert served.sentences == policy.SENTENCES
