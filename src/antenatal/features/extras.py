"""The usable visit two extras of amendment 1 (experiment 2.10, ``configs/experiment_plan.yaml``).

They were chosen from availability in development records alone, before any link
to the outcome was looked at. Fields that copy the delivery outcome
(``preterm_labour_1``, ``labour_at_term_1``), count visits after the prediction
(``total_antenatal_visits``) or have no stated origin (``Risk``) are never read.
"""

from __future__ import annotations

import pandas as pd

from antenatal.config import PRIMARY, Range, StudySpec
from antenatal.data.parsers import NumericParser, SentinelPolicy, YesNoParser

EXTRA_COLUMNS = (
    "second_hand_smoke",
    "alcohol",
    "current_problems",
    "malaria_positive_v1",
    "fetal_heart_heard_v2",
    "temperature_v2",
    "respiratory_rate_v2",
)
YES_NO = {
    "second_hand_smoke": "exposure_to_second_handsmoke",
    "alcohol": "use_of_alcohol",
    "current_problems": "problems_in_current_pregnancy",
}
NUMBERS = {
    "temperature_v2": ("body_temperature_v2", Range(34, 42)),
    "respiratory_rate_v2": ("respiratory_rate_v2", Range(8, 40)),
}


def malaria(value: object) -> float | None:
    """Positive 1.0, negative 0.0; the typing variants in the file are mapped, others missing."""
    text = str(value).strip().lower()
    if text.startswith(("pos", "p0s")):
        return 1.0
    if text.startswith(("neg", "ngat", "nega")):
        return 0.0
    return None


def heartbeat(value: object) -> float | None:
    """Fetal heartbeat heard at visit two: present 1.0, not present 0.0."""
    return {"present": 1.0, "not present": 0.0}.get(str(value).strip().lower())


def extra_values(raw: pd.DataFrame, spec: StudySpec = PRIMARY) -> pd.DataFrame:
    """One row per record: ``record_id`` and the seven extras, missing where unusable."""
    yes_no, numbers = YesNoParser(), NumericParser(SentinelPolicy())
    out = pd.DataFrame({"record_id": raw[spec.record_id].astype(int)})
    for name, column in YES_NO.items():
        out[name] = raw[column].map(yes_no.parse).astype(float)
    out["malaria_positive_v1"] = raw["malaria_rapid_test_result_v1"].map(malaria).astype(float)
    out["fetal_heart_heard_v2"] = raw["fetal_auscaltation_v2"].map(heartbeat).astype(float)
    for name, (column, bounds) in NUMBERS.items():
        out[name] = raw[column].map(lambda v, b=bounds: numbers.parse(v, b)).astype(float)
    return out
