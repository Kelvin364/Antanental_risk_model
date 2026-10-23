# Compatibility evidence

Recorded by `pytest tests/e2e` on 2026-10-23T17:30:51+00:00 on macOS-15.5-arm64-arm-64bit with Playwright. Each cell is the full five screen flow (register, visit one, visit two, assessment, caseload) at that window size. Screenshots are in `compatibility/`, one per screen per browser per size.

| Browser | Version | 390x844 | 1366x768 |
| --- | --- | --- | --- |
| chromium | 156.0.8078.4 | pass | pass |
| firefox | 157.0 | pass | pass |
| webkit | 27.2 | pass | pass |

6 of 6 runs passed.
