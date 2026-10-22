"""The recorded performance evidence holds every measure Section 5 item 11 asks for."""

import json


def test_performance_evidence_is_complete(root):
    result = json.loads((root / "docs" / "evidence" / "performance.json").read_text())
    assert result["startup_seconds"] > 0 and result["peak_rss_mb"] > 0
    for mode, count in (("sequential", 500), ("concurrent", 50)):
        assert result[mode]["requests"] == count
        assert 0 < result[mode]["p50_ms"] <= result[mode]["p95_ms"]
    assert {"cpu", "ram_gb", "os", "python"} <= set(result["machine"])
    text = (root / "docs" / "evidence" / "performance.md").read_text()
    for label in ("Start up", "Peak resident memory", "p50 latency", "p95 latency", "CPU", "RAM"):
        assert label in text
