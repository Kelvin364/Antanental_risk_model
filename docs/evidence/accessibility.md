# Accessibility evidence

Measured by `scripts/accessibility_audit.py` on 2026-10-23T21:16:22+00:00 with Lighthouse
12.8.2 (accessibility category only, which runs the axe-core rules) in
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/156.0.0.0 Safari/537.36 on macOS-15.5-arm64-arm-64bit. The script started its own server with a temporary
database, recorded one synthetic case with both visits and an assessment through the API,
and audited each screen with that case open. The phone run uses Lighthouse's default
mobile emulation and the desktop run its desktop preset. The raw results are in
`accessibility.json`.

## Scores out of 100

| Screen | Phone | Desktop |
| --- | --- | --- |
| Sign in | 100 | 100 |
| About | 100 | 100 |
| Administration | 100 | 100 |
| Register | 100 | 100 |
| Visit one | 100 | 100 |
| Visit two | 100 | 100 |
| Assessment | 100 | 100 |
| Caseload | 100 | 100 |

The lowest score is 100.

## Failed audits

None. Every weighted audit passed on every screen at both sizes.

An automated audit checks only what a program can detect, such as contrast, labels,
names, roles and document structure. It does not show that the screens are usable with
a screen reader or by keyboard alone, which needs a person to test them.
