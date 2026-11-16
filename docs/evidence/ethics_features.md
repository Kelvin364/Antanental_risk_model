# Ethics features: consent, privacy policy and deletion

Recorded on 16 November 2026. These three features answer the ethics summative: a consent step that the user accepts and the database records; a Privacy Policy and Terms of Use page inside the application; and a way for a user to delete their own data. The study's approval from the African Leadership University Research Ethics Committee (code SEPT26-BSE-064, 2 November 2026, valid six months) is recorded in [`docs/ethics_and_ai.md`](../ethics_and_ai.md), section 2.2, and section 9 of that note describes the three features.

Nothing in the research side changed: no file under `data/`, `partitions/`, `outputs/`, `webapp/model/`, `week36_model/`, `configs/` or `src/antenatal/`. The model artefact, the data checksum and the sealed partition are untouched, and the prediction endpoint returns the same scores (`tests/integration/test_api.py` passes unchanged).

## What was built

| Feature | Commit | What it does |
| --- | --- | --- |
| Restored documents | 6385043 | Brings back `docs/ethics_and_ai.md`, `docs/decisions_log.md` and `docs/tripod_ai_checklist.md`, removed in 588d5e9 and cited by the report |
| Consent at first sign in | 8bb882b | "Before you continue" page; no case work or prediction until the current Terms of Use are accepted; version and time stored on the user row with a `consent_accepted` audit event |
| Privacy Policy and Terms of Use | d19e833 | `/privacy`, open without sign in, version 2026-11-16, ten sections served from `webapp/app/core/policy.py` |
| Deletion | 190e05b | The owner deletes a case at once from the assessment screen or the caseload; a user requests removal of their account and an administrator completes it |

## Where the wording differs from the brief, and why

The brief asked for two statements that the code does not support. The policy follows the code, because the instruction also required every statement to be true and the system's behaviour not to change.

* **Administrator access to cases.** The brief's policy said an administrator cannot see other users' cases. The application lets an administrator open any case (`webapp/app/services/case_service.py`, and `tests/integration/test_auth.py::test_researchers_see_only_their_own_cases` asserts it). The policy says so: "An administrator manages accounts, reads the audit trail and can also open any case, to support researchers."
* **Network addresses.** The web server's request log (the uvicorn default), kept by the host, records network addresses. The policy says the database never stores them, and that the request log does.
* **What removal keeps.** The audit trail keeps every earlier record of the removed user, not only the record of the removal, and the page says so.

Deleting a case is owner only, including for administrators, as the brief asked.

## Tests

| Test file | What it proves |
| --- | --- |
| `tests/integration/test_consent.py` (7 tests) | Case work, caseload and prediction refused with the exact message until consent; consent stores version, time and audit event; another version refused with 409 and nothing stored; a new policy version asks again; CSRF token required; sign in required; an older database gains the new columns without losing rows |
| `tests/unit/test_policy.py` (4 tests) | Version is a date; ten sections in order and non empty, at most 600 words; no dash used as punctuation; the facts it names match the code (seven days, 64 KB, eight hours, five failures, scrypt, MIT, CC BY 4.0, SEPT26-BSE-064); the API serves exactly these sentences |
| `tests/integration/test_deletion.py` (6 tests) | The owner deletes a case with its visits and assessment, with a `case_deleted` event; another researcher, an administrator or an unknown id get the same 404; CSRF required; a removal request is completed by an administrator, deleting cases, sessions and user, with `account_removed`, after which the old session gets 401; only administrators remove; self removal and the last administrator are refused with 409 |
| `tests/integration/test_retention.py` (one added test) | The seven day purge leaves consent and removal dates untouched |
| `tests/e2e/test_ethics_features.py` (3 tests) | In Chromium: the consent page appears once, with the button disabled until the box is ticked; `/privacy` opens without sign in with the version and all ten headings, and is linked from the sign in, About and account pages; a case is deleted from the assessment screen after Keep and then Delete |
| `tests/unit/test_accessibility_evidence.py` | The accessibility evidence now also covers the Privacy, Consent and Account pages; every page scored 100 at phone and desktop sizes (`docs/evidence/accessibility.md`) |

The final line of the full run (`pytest`, unit, integration and browser tests):

```
371 passed, 5 skipped, 2 warnings in 248.20s (0:04:08)
```

The 5 skipped tests are the PostgreSQL tests in `tests/postgres`, which run only when `ANTENATAL_TEST_POSTGRES_URL` points at a database that may be wiped. Before this work the unit and integration suites held 344 tests and the browser suite 6; they now hold 362 and 9.

## Screenshots

Taken by `scripts/render_designs.py` from the running interface in Chromium at 1366 pixels wide, on a temporary database.

| File | Shows |
| --- | --- |
| [`designs/web/06-consent.png`](../../designs/web/06-consent.png) | Before you continue: Terms of Use, the ticked square checkbox and "I agree" |
| [`designs/web/07-privacy.png`](../../designs/web/07-privacy.png) | The Privacy Policy and Terms of Use with its version |
| [`designs/web/08-delete-case.png`](../../designs/web/08-delete-case.png) | The in page confirmation before a case is deleted |
| [`designs/web/09-account-removal.png`](../../designs/web/09-account-removal.png) | A researcher's account page after requesting removal |
| [`designs/web/10-admin-removal.png`](../../designs/web/10-admin-removal.png) | The administrator's list of removal requests, with `consent accepted` and `deletion requested` in the audit trail |
| [`designs/web/11-consent-row.png`](../../designs/web/11-consent-row.png) | The stored user row: `terms_version` and `terms_accepted_at` filled, the password only as its scrypt hash |
