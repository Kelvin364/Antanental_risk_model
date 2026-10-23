"""The recorded accessibility evidence covers every screen at both sizes."""

import json

SCREENS = {"Register", "Visit one", "Visit two", "Assessment", "Caseload"}


def test_accessibility_evidence_is_complete(root):
    result = json.loads((root / "docs" / "evidence" / "accessibility.json").read_text())
    assert result["lighthouse"] and result["browser"] and result["os"]
    seen = {(r["screen"], r["size"]) for r in result["results"]}
    assert seen == {(screen, size) for screen in SCREENS for size in ("phone", "desktop")}
    for row in result["results"]:
        assert 0 <= row["score"] <= 100 and row["audits_passed"] > 0
    text = (root / "docs" / "evidence" / "accessibility.md").read_text()
    for label in ("Scores out of 100", "Phone", "Desktop", "Failed audits", *SCREENS):
        assert label in text
