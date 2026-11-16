# Designs

The twelve images in `web/` are screenshots of the running interface, not drawings. `scripts/render_designs.py` starts the server with a temporary database, creates a temporary account, signs in, agrees to the Terms of Use, enters one synthetic pregnancy in Chromium at 1366 by 768 and saves one image per screen, then captures the consent, privacy and deletion screens and the stored consent row. It stops with an error if a screen shows triage wording. To redraw them after an interface change, run `make browsers` once and then `.venv/bin/python scripts/render_designs.py`.

| File | Screen |
| --- | --- |
| `web/00-sign-in.png` | Sign in |
| `web/01-register.png` | Register a synthetic pregnancy |
| `web/02-visit-one.png` | Visit one measurements |
| `web/03-visit-two.png` | Visit two measurements |
| `web/04-assessment.png` | Rank position and predicted probability with its interval |
| `web/05-caseload.png` | Caseload ordered by predicted probability |
| `web/06-consent.png` | Before you continue: the Terms of Use, the checkbox and "I agree" |
| `web/07-privacy.png` | Privacy Policy and Terms of Use, open without sign in |
| `web/08-delete-case.png` | Deleting a case from the assessment screen, with the confirmation in the page |
| `web/09-account-removal.png` | A researcher's account page after requesting removal |
| `web/10-admin-removal.png` | The administrator's list of removal requests, and the audit trail |
| `web/11-consent-row.png` | The stored user row: consent version and time, password only as its scrypt hash |

The earlier Figma screens, which included sign up and sign in screens and triage wording, were removed. Sign in returns with the authentication work of decision D1, and the assessment now shows a label at a fixed threshold (decision D6); no triage wording is shown.

## Figma design

The interface follows the Figma file "Antenatal Caseload, App Screens" (Web App page): its
colours, Host Grotesk and IBM Plex Mono type, top bar, step tabs, banner, field style with
unit and range hints, section headings, cards, the visit two change panel, the assessment
position bar and the caseload table. Elements of that file that break the project rules
are left out: the "see sooner" and "routine" badges and wording (rule 7), round number
pills and initials avatars (rule 11), invented names, a health post and a work email
(synthetic, unidentified cases only), self sign up and email password reset (accounts come
from an administrator, decision D1), and registration fields the model does not use.
