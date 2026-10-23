# Deployment evidence

Checked by `scripts/smoke_test.py` against https://antenatal-caseload.fly.dev at commit `9e13fef` on
2026-10-23T21:05:20+00:00, signed in as a researcher account.
Synthetic cases only; the image holds no data file and no partition file.

| Check | Result | Detail |
| --- | --- | --- |
| Health answers with the frozen artefact | pass | 7358b0b26f83aa60 |
| Sign in page is served | pass | 200 |
| Security headers present | pass | default-src 'self'; script-src 'self' 'u |
| Caseload refused without sign in | pass | 401 |
| HSTS over HTTPS | pass |  |
| Sign in succeeds | pass | 200 |
| Session cookie is HttpOnly and SameSite strict | pass |  |
| Change refused without the CSRF token | pass | 403 |
| Valid synthetic case is scored and labelled | pass | Not likely low birth weight |
| Age 121 refused | pass | 422 |
| Missing synthetic flag refused | pass | 422 |
| Researcher refused administration | fail | 200 |
| Session cookie is Secure | pass |  |

12 of 13 checks passed. A changed artefact refusing to start is tested
locally (`tests/integration/test_api.py::test_tampered_artefact_refuses_to_start`).
