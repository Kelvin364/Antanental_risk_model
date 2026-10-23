# Deployment evidence

Checked by `scripts/smoke_test.py` against https://antenatal-caseload.fly.dev at commit `67d6f9c` on
2026-10-23T16:59:39+00:00, without an account (the signed in checks run once the first accounts exist).
Synthetic cases only; the image holds no data file and no partition file.

| Check | Result | Detail |
| --- | --- | --- |
| Health answers with the frozen artefact | pass | 7358b0b26f83aa60 |
| Sign in page is served | pass | 200 |
| Security headers present | pass | default-src 'self'; script-src 'self' 'u |
| Caseload refused without sign in | pass | 401 |
| HSTS over HTTPS | pass |  |

5 of 5 checks passed. A changed artefact refusing to start is tested
locally (`tests/integration/test_api.py::test_tampered_artefact_refuses_to_start`).
