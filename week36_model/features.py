"""Build predictors at a landmark: only values recorded at or before that week of pregnancy."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from antenatal.config import PRIMARY, Range
from antenatal.data.dictionary import REGISTRATION_FIELDS, FieldKind
from antenatal.data.parsers import BloodPressureParser, NumericParser, YesNoParser

ROOT = Path(__file__).resolve().parents[1]
TRACK = Path(__file__).resolve().parent
LANDMARKS = (28, 32, 36)
WINDOW = 4
VISITS = range(1, 9)
RANGES = PRIMARY.ranges
BANNED = {
    "Risk", "total_antenatal_visits", "mode_of_delivery", "live_births", "still_births",
    "labour_at_term", "post_term", "preterm_labour", "twins_delivery", "number_of_twins",
    "newborn_birth_weight_kg_", "newborn_with_weight_4kg_and_above",
    "gender_of_new_born_child", "new_born_with_complication", "immunization_status",
    "miscarriages_or_abortions_1", "bleeding_during_pregnancy", "bleeding_during_delivery",
    "bleeding_after_delivery", "other_problems_during_pregnancy", "preterm_labour_1",
    "labour_at_term_1", "miscarriages_or_abortions", "number_of_miscarriages_or_abortions",
    "twin_pregnancy", "congenital_malformations",
    "type_of_cognital_malfomation_baby_born_with",
}  # fmt: skip
HISTORY_YES_NO = {
    "bleeding_before": "bleeding_in_previous_pregnancies",
    "second_hand_smoke": "exposure_to_second_handsmoke",
    "alcohol": "use_of_alcohol",
    "bleeding_now": "vaginal_bleeding",
    "current_problems": "problems_in_current_pregnancy",
}
VISIT_YES_NO = {
    "social_support": "social_support_v{}",
    "gender_violence": "gbv_v{}",
    "iron_folic": "iron_and_folic_v{}",
    "folic": "folic_v{}",
    "bed_net": "provide_long_lasting_v{}",
}
NUMERIC_VISIT = {
    "weight": ("weight_kg_v{}", RANGES.weight),
    "ga": ("pregnant_week_number_v{}", RANGES.ga),
    "pulse": ("pulse_rate_v{}", RANGES.pulse),
    "hb": ("hemoglobin_check_result_v{}", RANGES.hb),
    "temperature": ("body_temperature_v{}", Range(34, 42)),
    "breathing": ("respiratory_rate_v{}", Range(8, 40)),
}
SET_A = [field.name for field in REGISTRATION_FIELDS]
SET_B = SET_A + ["sbp", "dbp", "weight", "ga", "pulse", "hb"]
SET_C = SET_B + [
    "sbp_first", "dbp_first", "weight_first", "ga_first", "pulse_first", "weight_gain_week",
]  # fmt: skip
SET_D = SET_C + [
    "bmi", "anaemia", "stillbirths", "temperature", "breathing", "fetal_heart", "breech",
    "malaria", *HISTORY_YES_NO, *VISIT_YES_NO,
]  # fmt: skip
SETS = {"A": SET_A, "B": SET_B, "C": SET_C, "D": SET_D}


def source_columns() -> set[str]:
    """Every raw column this module reads; the banned list must not meet it."""
    columns = {field.column for field in REGISTRATION_FIELDS} | set(HISTORY_YES_NO.values())
    columns |= {"number_of_prior_pregnancies_with_stillbirths"}
    for visit in VISITS:
        columns |= {pattern.format(visit) for pattern in VISIT_YES_NO.values()}
        columns |= {pattern.format(visit) for pattern, _ in NUMERIC_VISIT.values()}
        columns |= {f"blood_pressure_v{visit}", f"fetal_auscaltation_v{visit}"}
        columns |= {f"abdominal_palpation_v{visit}", f"malaria_rapid_test_result_v{visit}"}
    return columns


def load_raw(ids: pd.Series) -> pd.DataFrame:
    """Only the listed records and only allowed columns are kept, plus the outcome."""
    overlap = source_columns() & BANNED
    if overlap or any(column.endswith("_p") for column in source_columns()):
        raise RuntimeError(f"Banned columns requested: {overlap}")
    keep = source_columns() | {"SN"}
    raw = pd.read_csv(ROOT / "data/maternal_dataset_csv.csv", dtype=str, usecols=list(keep))
    raw["SN"] = raw["SN"].astype(int)
    raw = raw[raw["SN"].isin(set(ids))].set_index("SN").sort_index()
    manifest = pd.read_csv(
        ROOT / "outputs/cohort_manifest.csv",
        usecols=["record_id", "group_key_hash", "lbw"],
        index_col="record_id",
    )
    return raw.join(manifest)


def _numbers(series: pd.Series, bounds: Range | None) -> np.ndarray:
    parser = NumericParser()
    values = (parser.parse(value, bounds) for value in series)
    return np.array([np.nan if v is None else v for v in values], dtype=float)


def _yes_no(series: pd.Series) -> np.ndarray:
    values = (YesNoParser().parse(value) for value in series)
    return np.array([np.nan if v is None else v for v in values], dtype=float)


def _coded(series: pd.Series, mapping: dict[str, float]) -> np.ndarray:
    text = series.astype(str).str.strip().str.lower()
    return np.array([mapping.get(value, np.nan) for value in text], dtype=float)


def _malaria(series: pd.Series) -> np.ndarray:
    text = series.astype(str).str.strip().str.lower()
    positive = text.str.startswith(("pos", "p0s"))
    negative = text.str.startswith(("neg", "ngat"))
    return np.where(positive, 1.0, np.where(negative, 0.0, np.nan))


def _visit_grid(raw: pd.DataFrame) -> dict[str, np.ndarray]:
    """Each measurement as a records by visits array."""
    grid = {
        name: np.column_stack([_numbers(raw[col.format(v)], limit) for v in VISITS])
        for name, (col, limit) in NUMERIC_VISIT.items()
    }
    parser = BloodPressureParser()
    readings = [
        [parser.parse_in_range(x, RANGES.sbp, RANGES.dbp) for x in raw[f"blood_pressure_v{v}"]]
        for v in VISITS
    ]
    grid["sbp"] = np.array([[r.systolic if r else np.nan for r in row] for row in readings]).T
    grid["dbp"] = np.array([[r.diastolic if r else np.nan for r in row] for row in readings]).T
    for name, pattern in VISIT_YES_NO.items():
        grid[name] = np.column_stack([_yes_no(raw[pattern.format(v)]) for v in VISITS])
    heart = {"present": 1.0, "not present": 0.0}
    grid["fetal_heart"] = np.column_stack(
        [_coded(raw[f"fetal_auscaltation_v{v}"], heart) for v in VISITS]
    )
    lie = {"longitudinal/breech": 1.0, "longitudinal/cephalic": 0.0}
    grid["breech"] = np.column_stack(
        [_coded(raw[f"abdominal_palpation_v{v}"], lie) for v in VISITS]
    )
    grid["malaria"] = np.column_stack(
        [_malaria(raw[f"malaria_rapid_test_result_v{v}"]) for v in VISITS]
    )
    return grid


def _registration(raw: pd.DataFrame) -> pd.DataFrame:
    frame = {}
    for field in REGISTRATION_FIELDS:
        if field.kind is FieldKind.NUMERIC:
            frame[field.name] = _numbers(raw[field.column], getattr(RANGES, field.range_name))
        else:
            frame[field.name] = _yes_no(raw[field.column])
    for name, column in HISTORY_YES_NO.items():
        frame[name] = _yes_no(raw[column])
    frame["stillbirths"] = _numbers(raw["number_of_prior_pregnancies_with_stillbirths"], None)
    return pd.DataFrame(frame, index=raw.index)


def at_landmark(raw: pd.DataFrame, week: int) -> pd.DataFrame:
    """One row per pregnancy with a usable visit in the window ending at ``week``."""
    grid = _visit_grid(raw)
    ga = grid["ga"]
    allowed = ga <= week
    in_window = allowed & (ga > week - WINDOW)
    reachable = in_window.any(axis=1)
    latest = np.where(in_window, ga, -np.inf).argmax(axis=1)
    first = np.where(allowed, ga, np.inf).argmin(axis=1)
    rows = np.arange(len(raw))
    frame = _registration(raw)
    for name, values in grid.items():
        if name != "malaria":
            frame[name] = values[rows, latest]
    frame["malaria"] = np.nanmax(np.where(allowed, grid["malaria"], -np.inf), axis=1)
    frame.loc[frame["malaria"] < 0, "malaria"] = np.nan
    two_visits = first != latest
    for name in ("sbp", "dbp", "weight", "ga", "pulse"):
        frame[f"{name}_first"] = np.where(two_visits, grid[name][rows, first], np.nan)
    gap = frame["ga"] - frame["ga_first"]
    frame["weight_gain_week"] = (frame["weight"] - frame["weight_first"]) / gap.where(gap >= 1)
    frame["bmi"] = frame["weight"] / (frame["height_cm"] / 100) ** 2
    frame["anaemia"] = (frame["hb"] < 11).astype(float).where(frame["hb"].notna())
    frame["lbw"] = raw["lbw"].astype(int)
    frame["group"] = raw["group_key_hash"]
    return frame[reachable]
