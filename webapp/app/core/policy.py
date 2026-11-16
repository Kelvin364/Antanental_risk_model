"""The Terms of Use, the consent sentence and the other fixed sentences of the consent step.

Every sentence here is written once and reaches the interface through ``GET /api/policy``,
the way the synthetic banner travels through ``/api/interface-text``. Changing
``POLICY_VERSION`` asks every user to agree again at their next request.
"""

from __future__ import annotations

POLICY_VERSION = "2026-11-16"

CONSENT_SENTENCE = (
    "I will enter synthetic cases only, never a real pregnancy, and I understand that my "
    "actions in this application are logged"
)
CONSENT_REQUIRED = "Accept the Terms of Use before using the application"
TERMS_CHANGED = (
    "These terms have changed since this page opened. Read the current Terms of Use and "
    "agree again."
)

# Sentences the interface shows around consent and deletion; {placeholders} are filled in
# by the interface with the date or the case label.
SENTENCES = {
    "consent_lead": (
        "Read the Terms of Use below. You can open the application once you agree to them."
    ),
    "consent_done": "You agreed to this version of the Terms of Use on {date}.",
}

TERMS_OF_USE = (
    "Enter synthetic cases only. Do not enter data about a real person, and never a real "
    "pregnancy. Do not share your account; it is for you alone. Your actions in this "
    "application are logged in an audit trail. The application may be withdrawn at any time. "
    "The author gives no warranty, and the outputs must not inform the care of any pregnancy."
)
