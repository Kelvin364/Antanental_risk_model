"""Protocol Section 3: the three predictor sets, using only registration, visit one and visit two.

F0 is the served set C. F1 adds clinically motivated derived values and the track's extra
fields at visits one and two. F2 is every usable column recorded by visit two.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "fusion"))
sys.path.insert(0, str(HERE.parent))

import frames as fusion_frames  # noqa: E402
from features import (  # noqa: E402
    BANNED,
    HISTORY_YES_NO,
    VISIT_YES_NO,
    _coded,
    _malaria,
    _numbers,
    _yes_no,
)

ROOT = fusion_frames.ROOT
F0 = list(pd.read_json(ROOT / "webapp/model/model_params.json", typ="series")["feature_names"])
UNUSABLE = {
    "SN", "Risk", "total_antenatal_visits", "visit_number", "last_normal_menustration_date",
    "expected_date_of_delivery", "duration_of_pregnancy_weeks_", "duaration_of_pregnancy_days_",
}  # fmt: skip
FREE_TEXT = ("specify_", "indicate_", "other_")
LATER = re.compile(r"(_p\d*|_[1-7]|_v[3-8])$")
NUMERIC_SHARE, MAX_MISSING = 0.90, 0.95


def usable(column: str) -> bool:
    """Recorded at registration, visit one or visit two, and allowed by the protocol."""
    stem = re.sub(r"_v[12]$", "", column)
    return not (
        column in BANNED | UNUSABLE
        or LATER.search(column)
        or stem.startswith(FREE_TEXT)
        or "date" in stem
        or stem == "blood_pressure"
    )


def _f1_extra(raw: pd.DataFrame, served: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=served.index)
    for v in (1, 2):
        out[f"temperature_v{v}"] = _numbers(raw[f"body_temperature_v{v}"], None)
        out[f"breathing_v{v}"] = _numbers(raw[f"respiratory_rate_v{v}"], None)
        heart = {"present": 1.0, "not present": 0.0}
        out[f"fetal_heart_v{v}"] = _coded(raw[f"fetal_auscaltation_v{v}"], heart)
        out[f"malaria_v{v}"] = _malaria(raw[f"malaria_rapid_test_result_v{v}"])
        for name, pattern in VISIT_YES_NO.items():
            out[f"{name}_v{v}"] = _yes_no(raw[pattern.format(v)])
    for name, column in HISTORY_YES_NO.items():
        out[name] = _yes_no(raw[column])
    out["stillbirths"] = _numbers(raw["number_of_prior_pregnancies_with_stillbirths"], None)
    return out


def _f1_derived(served: pd.DataFrame) -> pd.DataFrame:
    s, out = served, pd.DataFrame(index=served.index)
    for m in ("sbp", "dbp", "weight", "pulse"):
        out[f"d_{m}"] = s[f"d_{m}"]
        out[f"{m}_per_week"] = s[f"{m}_per_week"]
    out["bmi"] = s["weight_v2"] / (s["height_cm"] / 100) ** 2
    out["map_v2"] = (s["sbp_v2"] + 2 * s["dbp_v2"]) / 3
    out["pulse_pressure_v2"] = s["sbp_v2"] - s["dbp_v2"]
    out["anaemia"] = (s["hb_v2"] < 11).astype(float).where(s["hb_v2"].notna())
    raised = (s["sbp_v2"] >= 140) | (s["dbp_v2"] >= 90)
    out["raised_bp"] = raised.astype(float)
    out["short_stature"] = (s["height_cm"] < 150).astype(float).where(s["height_cm"].notna())
    out["low_bmi"] = (out["bmi"] < 18.5).astype(float).where(out["bmi"].notna())
    out["first_pregnancy"] = (
        (s["prior_deliveries"] == 0).astype(float).where(s["prior_deliveries"].notna())
    )
    out["age_squared"] = s["age"] ** 2
    return out


def _wide_columns(raw: pd.DataFrame) -> tuple[list[str], list[str]]:
    numeric, categorical = [], []
    for column in filter(usable, raw.columns):
        values = raw[column].dropna().astype(str).str.strip()
        values = values[values != ""]
        if values.empty:
            continue
        parsed = pd.to_numeric(values, errors="coerce")
        if parsed.notna().mean() >= NUMERIC_SHARE:
            if 1 - len(values) / len(raw) <= MAX_MISSING:
                numeric.append(column)
        else:
            categorical.append(column)
    return numeric, categorical


def build() -> dict[str, object]:
    """Frames for F0, F1 and F2 on the 3,126 records, plus outcome and groups."""
    frames = fusion_frames.load()
    served = frames.served
    raw = pd.read_csv(ROOT / "data/maternal_dataset_csv.csv", dtype=str)
    raw = raw.assign(SN=raw["SN"].astype(int)).set_index("SN").loc[served.index]
    f1 = pd.concat([served[F0], _f1_derived(served), _f1_extra(raw, served)], axis=1)
    numeric, categorical = _wide_columns(raw)
    wide_numeric = raw[numeric].apply(pd.to_numeric, errors="coerce").add_prefix("raw_")
    wide_text = raw[categorical].apply(lambda c: c.str.strip().str.lower()).add_prefix("cat_")
    f2 = pd.concat([f1, wide_numeric, wide_text], axis=1)
    f2 = f2.loc[:, ~f2.columns.duplicated()]
    return {
        "F0": served[F0].astype(float),
        "F1": f1.astype(float),
        "F2": f2,
        "y": served["lbw"].to_numpy(),
        "groups": served["group_key_hash"].to_numpy(),
        "group_key": served["group_key"].to_numpy(),
        "ga_v2": served["ga_v2"].to_numpy(),
        "categorical": [c for c in f2.columns if c.startswith("cat_")],
        "guard": frames.guard,
        "ids": served.index,
        "raw_numeric": numeric,
        "raw_categorical": categorical,
    }
