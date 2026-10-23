# Designs

The six images in `web/` are screenshots of the running interface, not drawings. `scripts/render_designs.py` starts the server with a temporary database, creates a temporary account, signs in, enters one synthetic pregnancy in Chromium at 1366 by 768 and saves one image per screen. It stops with an error if a screen shows triage wording. To redraw them after an interface change, run `make browsers` once and then `.venv/bin/python scripts/render_designs.py`.

| File | Screen |
| --- | --- |
| `web/00-sign-in.png` | Sign in |
| `web/01-register.png` | Register a synthetic pregnancy |
| `web/02-visit-one.png` | Visit one measurements |
| `web/03-visit-two.png` | Visit two measurements |
| `web/04-assessment.png` | Rank position and predicted probability with its interval |
| `web/05-caseload.png` | Caseload ordered by predicted probability |

The earlier Figma screens, which included sign up and sign in screens and triage wording, were removed. Sign in returns with the authentication work of decision D1, and the assessment now shows a label at a fixed threshold (decision D6); no triage wording is shown.
