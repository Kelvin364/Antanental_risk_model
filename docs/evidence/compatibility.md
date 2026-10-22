# Compatibility evidence

Recorded by `pytest tests/e2e` on 2026-10-22T21:25:49+00:00 on Linux-6.18.54.1-microsoft-standard-WSL2-x86_64-with-glibc2.35 with Playwright. Each cell is the full five screen flow (register, visit one, visit two, assessment, caseload) at that window size. Screenshots are in `compatibility/`, one per screen per browser per size.

| Browser | Version | 390x844 | 1366x768 |
| --- | --- | --- | --- |
| chromium | 156.0.8078.4 | pass | pass |
| firefox | 157.0 | pass | pass |
| webkit | 27.2 | pass | pass |

6 of 6 runs passed.
