"""Run the test suite and linters and record the results for the technical report.

Usage: ``python scripts/record_test_results.py``. Writes
``docs/evidence/test_summary.json`` with test counts per suite, the run time,
line coverage and the linter results, all read from the tools' own output.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def _suites(junit: Path) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for case in ET.parse(junit).getroot().iter("testcase"):
        suite = (
            case.get("classname", "").split(".")[1] if "." in case.get("classname", "") else "other"
        )
        entry = counts.setdefault(suite, {"tests": 0, "failed": 0, "skipped": 0})
        entry["tests"] += 1
        if case.find("failure") is not None or case.find("error") is not None:
            entry["failed"] += 1
        if case.find("skipped") is not None:
            entry["skipped"] += 1
    return counts


def _lint(command: list[str]) -> bool:
    return subprocess.run(command, cwd=ROOT, capture_output=True).returncode == 0


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        junit, coverage = Path(tmp) / "junit.xml", Path(tmp) / "coverage.json"
        run = subprocess.run(
            [
                PYTHON,
                "-m",
                "pytest",
                "-q",
                "-W",
                "ignore",
                f"--junitxml={junit}",
                "--cov",
                f"--cov-report=json:{coverage}",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        root = ET.parse(junit).getroot()
        suite = root if root.tag == "testsuite" else root.find("testsuite")
        totals = json.loads(coverage.read_text())["totals"]
        summary = {
            "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "tests": int(suite.get("tests")),
            "failures": int(suite.get("failures")) + int(suite.get("errors")),
            "skipped": int(suite.get("skipped")),
            "seconds": round(float(suite.get("time")), 1),
            "by_suite": _suites(junit),
            "line_coverage_percent": round(totals["percent_covered"], 1),
            "statements": totals["num_statements"],
            "ruff_clean": _lint(
                [PYTHON, "-m", "ruff", "check", "src", "tests", "webapp", "scripts"]
            ),
            "black_clean": _lint(
                [PYTHON, "-m", "black", "--check", "src", "tests", "webapp", "scripts"]
            ),
        }
    out = ROOT / "docs" / "evidence" / "test_summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return run.returncode


if __name__ == "__main__":
    sys.exit(main())
