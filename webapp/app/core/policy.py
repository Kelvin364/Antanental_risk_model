"""The Terms of Use, the consent sentence and the other fixed sentences of the consent step.

Every sentence here is written once and reaches the interface through ``GET /api/policy``,
the way the limitation line travels through ``/api/interface-text``. Changing
``POLICY_VERSION`` asks every user to agree again at their next request.
"""

from __future__ import annotations

POLICY_VERSION = "2026-11-19"

CONSENT_SENTENCE = (
    "I will never enter data about a real pregnancy, and I understand that my "
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
    "delete_confirm": "Delete case {label}? This cannot be undone.",
    "removal_explained": (
        "Removal deletes your cases, your sessions and your account; the audit trail keeps its "
        "records, including the record of the removal."
    ),
    "removal_pending": "Removal requested on {date}. An administrator will complete it.",
}
SELF_REMOVAL = "An administrator cannot remove their own account."
LAST_ADMINISTRATOR = "The last active administrator cannot be removed."

TERMS_OF_USE = (
    "Do not enter data about a real person, and never a real pregnancy. Do not share your "
    "account; it is for you alone. Your actions in this "
    "application are logged in an audit trail. The application may be withdrawn at any time. "
    "The author gives no warranty, and the outputs must not inform the care of any pregnancy."
)

# The Privacy Policy and Terms of Use page (/privacy), in order. Every statement must stay
# true to the code; tests/unit/test_policy.py checks the facts it can.
SECTIONS: tuple[tuple[str, str], ...] = (
    (
        "What this application is",
        "A research demonstration of the prediction model from the capstone study on two "
        "antenatal visits and recorded low birth weight. It is "
        "not a medical device, it gives no clinical advice, and it must not be used for any real "
        "pregnancy.",
    ),
    (
        "Who can use it",
        "Accounts are created by an administrator. There is no public sign up. There are two "
        "roles, researcher and administrator. A new account must replace its first password and "
        "agree to these terms before any case work.",
    ),
    (
        "What is stored",
        "Your username and a scrypt hash of your password; the password itself is never stored. "
        "Your sign in sessions and when they expire, with only a hash of each session token. The "
        "version and time of your agreement to these terms. An audit trail of account actions "
        "(sign in, sign out, password changes and resets, consent, assessments, case deletion, "
        "removal requests and account changes) with the username and the time, and never a "
        "clinical value. Your cases with their visits and assessments, each marked "
        "synthetic by a database rule that cannot be switched off.",
    ),
    (
        "What is not stored",
        "No real patient data, no names of pregnant women, no location and no device "
        "identifiers. There is no analytics or tracking, and the only cookie is the session "
        "cookie. The database never stores network addresses; the sign in rate limit counts "
        "them in memory for one minute, and the web server's request log, kept by the host, "
        "lists them.",
    ),
    (
        "How long it is kept",
        "Cases, with their visits and assessments, are deleted once they are more than "
        "seven days old, each time the application starts (the setting "
        "ANTENATAL_CASE_RETENTION_DAYS). Sessions stop working eight hours after sign in. Audit "
        "events are kept for the life of the deployment. Accounts are kept until an "
        "administrator removes them.",
    ),
    (
        "Who can see what",
        "A researcher sees only the cases they registered. An administrator manages accounts, "
        "reads the audit trail and can also open any case, to support researchers.",
    ),
    (
        "Your rights",
        "You can delete any of your cases at once from the assessment or caseload screen. You "
        "can ask for your account to be removed from the account page; an administrator then "
        "removes it, which deletes your cases, your sessions and your account. The audit trail "
        "keeps its records, including the record of the removal. You can ask the study author "
        "questions through the issues page of the project repository named in the README.",
    ),
    (
        "Security",
        "The hosted application is served over HTTPS. Sessions are kept on the server and the "
        "browser holds only an HttpOnly cookie. Every change carries a CSRF token, sign in "
        "attempts are rate limited and an account locks after five failures, every response "
        "carries security headers, and requests larger than 64 KB are refused.",
    ),
    (
        "The research behind it",
        "The model was built from a public Tanzanian dataset released under CC BY 4.0 "
        "(Mwifunyi et al., 2025), which holds no names, facility codes or other direct "
        "identifiers. The study holds ALU Research Ethics Committee approval SEPT26-BSE-064, "
        "dated 2 November 2026. The code is released under the MIT licence.",
    ),
    ("Terms of Use", TERMS_OF_USE),
)
