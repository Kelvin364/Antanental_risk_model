"""Run twelve input variations against a running API and record what happened.

Usage: start the server (``make serve``), then
``python scripts/input_variation.py --base-url http://127.0.0.1:8000``.
Writes ``docs/evidence/input_tests.csv`` and ``docs/evidence/input_tests.md``
and exits with status 1 if any observed behaviour differs from the expected one.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CASE = {
    "synthetic": True,
    "age": 24,
    "gravidity": 2,
    "prior_deliveries": 1,
    "height_cm": 156,
    "registration_weight": 58,
}
VISIT_ONE = {
    "gestational_week": 16,
    "systolic": 110,
    "diastolic": 70,
    "weight_kg": 56,
    "pulse": 80,
    "haemoglobin": 11.2,
}
VISIT_TWO = {
    "gestational_week": 22,
    "systolic": 118,
    "diastolic": 76,
    "weight_kg": 58,
    "pulse": 88,
    "haemoglobin": 10.9,
}


@dataclass
class Variation:
    """One input, the step it is entered at, and what should happen."""

    name: str
    case: dict = field(default_factory=dict)
    visit_one: dict | None = field(default_factory=dict)
    visit_two: dict | None = field(default_factory=dict)
    expected_status: int = 201
    expected_message: str = ""
    skip_visit_one: bool = False


VARIATIONS = [
    Variation("Typical complete case"),
    Variation(
        "Synthetic flag not set",
        case={"synthetic": False},
        expected_status=422,
        expected_message="synthetic flag",
    ),
    Variation(
        "Age 121",
        case={"age": 121},
        expected_status=422,
        expected_message="Maternal age must be between 12 and 55",
    ),
    Variation("Age 55, upper boundary"),
    Variation(
        "Height missing",
        case={"height_cm": None},
        expected_status=422,
        expected_message="Height is required",
    ),
    Variation(
        "Visit one systolic 300",
        visit_one={"systolic": 300},
        expected_status=422,
        expected_message="Systolic blood pressure must be between 60 and 250",
    ),
    Variation(
        "Visit one diastolic 20",
        visit_one={"diastolic": 20},
        expected_status=422,
        expected_message="Diastolic blood pressure must be between 30 and 160",
    ),
    Variation(
        "Visit one at 30 weeks",
        visit_one={"gestational_week": 30},
        expected_status=422,
        expected_message="at or before 28 weeks",
    ),
    Variation(
        "Visit two at the same week as visit one",
        visit_two={"gestational_week": 16},
        expected_status=422,
        expected_message="later than visit one",
    ),
    Variation("Visit two at 28 weeks, upper boundary", visit_two={"gestational_week": 28}),
    Variation(
        "Visit two pulse and haemoglobin missing", visit_two={"pulse": None, "haemoglobin": None}
    ),
    Variation(
        "Visit two entered before visit one",
        skip_visit_one=True,
        expected_status=409,
        expected_message="Record visit one before visit two",
    ),
]
VARIATIONS[3].case = {"age": 55}


def _messages(response: httpx.Response) -> str:
    body = response.json()
    if isinstance(body, dict) and isinstance(body.get("detail"), list):
        return "; ".join(e.get("message", "") for e in body["detail"])
    return ""


def run_one(client: httpx.Client, v: Variation) -> dict[str, object]:
    """Enter the case step by step and stop at the first refusal."""
    steps = [("POST", "/api/cases", {**CASE, "label": v.name, **v.case})]
    response = client.request(*steps[0][:2], json=steps[0][2])
    if response.status_code == 201:
        case_id = response.json()["id"]
        visits = [] if v.skip_visit_one else [(1, {**VISIT_ONE, **v.visit_one})]
        visits.append((2, {**VISIT_TWO, **v.visit_two}))
        for number, payload in visits:
            response = client.put(f"/api/cases/{case_id}/visits/{number}", json=payload)
            if response.status_code != 200:
                break
        else:
            response = client.post(f"/api/cases/{case_id}/assessment")
    observed = _messages(response) if response.status_code != 201 else ""
    if response.status_code == 201 and "probability" in response.json():
        a = response.json()
        size = a["reference_caseload_size"] + 1
        observed = f"probability {a['probability']:.4f}, rank {a['rank_position']} of {size}"
    passed = response.status_code == v.expected_status and v.expected_message in observed
    expected = f"{v.expected_status}" + (
        f', message contains "{v.expected_message}"'
        if v.expected_message
        else ", assessment returned"
    )
    return {
        "input": v.name,
        "expected": expected,
        "observed_status": response.status_code,
        "observed": observed,
        "result": "pass" if passed else "FAIL",
    }


def write(rows: list[dict], base_url: str) -> None:
    """Write the CSV and the markdown table."""
    out = ROOT / "docs" / "evidence"
    out.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows)
    frame.insert(0, "number", range(1, len(frame) + 1))
    frame.to_csv(out / "input_tests.csv", index=False)
    lines = [
        "| No. | Input | Expected | Observed status | Observed | Result |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    lines += [
        f"| {r.number} | {r.input} | {r.expected} | {r.observed_status} | {r.observed} "
        f"| {r.result} |"
        for r in frame.itertuples()
    ]
    stamp = datetime.now(UTC).isoformat(timespec="seconds")
    passed = int((frame["result"] == "pass").sum())
    text = (
        "# Input variation tests\n\nTwelve inputs entered through the API, step by step as the "
        f"interface enters them, against the server at {base_url} on {stamp}. Generated by "
        "`scripts/input_variation.py`; the raw results are in `input_tests.csv`.\n\n"
        f"{passed} of {len(frame)} behaved as expected.\n\n" + "\n".join(lines) + "\n"
    )
    (out / "input_tests.md").write_text(text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    with httpx.Client(base_url=args.base_url, timeout=30) as client:
        rows = [run_one(client, v) for v in VARIATIONS]
    write(rows, args.base_url)
    return 0 if all(r["result"] == "pass" for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
