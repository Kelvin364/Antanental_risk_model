"""Deliverables 1 and 2: which priority predictors exist in the source file, and how reliable.

Whole file, predictor fields only. No birth outcome field is read, so the audit cannot be
shaped by outcomes. Writes outputs/field_audit.json and outputs/predictor_inventory.csv.
"""

from __future__ import annotations

import json
import re

import numpy as np
import pandas as pd
from common import OUT, VISITS, header, number, predictor_fields

COLLECTION = (pd.Timestamp("2024-05-20"), pd.Timestamp("2025-03-30"))  # data/README.md
HISTORY = [
    "no_pregnancy", "number_of_prior_deliveries", "number_of_prior_pregnancies_with_live_births",
    "number_of_living_children_and_birth_weight", "preterm_labour_1", "labour_at_term_1",
    "infant_weight_of_4kg_and_above", "presence_of_hypertension_in_previous_pregnancies",
    "hypertension", "height_cm", "weight_kg", "last_normal_menustration_date",
    "expected_date_of_delivery", "duration_of_pregnancy_weeks_", "date_of_first_foetal_movement_v1",
]  # fmt: skip
PER_VISIT = [
    "pregnant_week_number", "weight_kg", "blood_pressure", "hemoglobin_check",
    "hemoglobin_check_result", "uterine_size_symphysis_fundal_height",
    "obstetric_ultrasound_scan", "obstetric_ultrasound_scan_result", "urine_albumin_check_result",
]  # fmt: skip
SEARCHED = {
    "mid upper arm circumference": r"muac|arm_circ",
    "estimated fetal weight": r"fetal_weight|foetal_weight|efw",
    "abdominal circumference": r"abdominal_circ",
    "Doppler": r"doppler|pulsatility|resistance_index",
    "crown rump length or dating scan": r"crown|crl|dating",
    "date of delivery": r"^(?!expected).*(date_of_delivery|delivery_date|birth_date|date_of_birth)",
    "gestational age at birth": r"gestation.*birth|ga_at|age_at_delivery",
    "facility identifier": r"facility|clinic|district|region|site",
    "visit date": r"visit_date|date_of_visit",
    "previous birth weight": r"previous.*weight|prior.*weight|last_baby",
}  # fmt: skip


def _fields() -> pd.DataFrame:
    visits = [f"{name}_v{v}" for name in PER_VISIT for v in VISITS]
    available = set(header())
    return predictor_fields(HISTORY + [c for c in visits if c in available])


def _share(mask: pd.Series, among: pd.Series | None = None) -> float:
    base = mask if among is None else mask[among]
    return float(base.mean())


def dating(raw: pd.DataFrame) -> dict:
    lmp = pd.to_datetime(raw["last_normal_menustration_date"], format="%m/%d/%Y", errors="coerce")
    edd = pd.to_datetime(raw["expected_date_of_delivery"], format="%m/%d/%Y", errors="coerce")
    gap = (edd - lmp).dt.days
    weeks = number(raw["duration_of_pregnancy_weeks_"])
    booked = lmp + pd.to_timedelta(weeks * 7, unit="D")
    v1 = number(raw["pregnant_week_number_v1"])
    both = gap.notna()
    return {
        "lmp_parsed": int(lmp.notna().sum()),
        "edd_parsed": int(edd.notna().sum()),
        "edd_within_7_days_of_lmp_plus_280": _share((gap - 280).abs() <= 7, both),
        "edd_minus_lmp_median_days": float(gap.median()),
        "lmp_outside_2023_to_2025": _share(~lmp.dt.year.between(2023, 2025), lmp.notna()),
        "implied_booking_inside_collection_period": _share(
            booked.between(*COLLECTION), booked.notna()
        ),
        "booking_weeks_within_2_of_visit_one_week": _share((weeks - v1).abs() <= 2, v1.notna()),
        "first_fetal_movement_v1_recorded_no": int(
            (raw["date_of_first_foetal_movement_v1"].str.strip().str.lower() == "no").sum()
        ),
    }


def visit_weeks(raw: pd.DataFrame) -> dict:
    weeks = pd.DataFrame({v: number(raw[f"pregnant_week_number_v{v}"]) for v in VISITS})
    counts = weeks.notna().sum(axis=1)
    steps = weeks.diff(axis=1)
    rising = (steps.isna() | (steps > 0)).all(axis=1)
    weights = pd.DataFrame({v: number(raw[f"weight_kg_v{v}"]) for v in VISITS})
    return {
        "records": len(raw),
        "visits_recorded_distribution": counts.value_counts().sort_index().to_dict(),
        "weeks_strictly_rising_among_two_or_more": _share(rising, counts >= 2),
        "numeric_weight_at_three_or_more_visits": int((weights.notna().sum(axis=1) >= 3).sum()),
        "any_visit_after_week_36": int((weeks > 36).any(axis=1).sum()),
    }


def history(raw: pd.DataFrame) -> dict:
    first = number(raw["no_pregnancy"]) == 1
    yes = {
        c: raw[c].str.strip().str.lower() == "yes"
        for c in HISTORY
        if raw[c].isin(["yes", "no"]).any()
    }
    prior = number(raw["number_of_prior_deliveries"])
    return {
        "first_pregnancies": int(first.sum()),
        "first_pregnancies_with_prior_preterm_yes": int((yes["preterm_labour_1"] & first).sum()),
        "prior_preterm_yes_share_first": _share(yes["preterm_labour_1"], first),
        "prior_preterm_yes_share_later": _share(yes["preterm_labour_1"], ~first),
        "first_pregnancies_with_prior_term_labour_yes": int(
            (yes["labour_at_term_1"] & first).sum()
        ),
        "first_pregnancies_with_prior_deliveries": int((first & (prior >= 1)).sum()),
        "prior_hypertension_yes": int(
            yes["presence_of_hypertension_in_previous_pregnancies"].sum()
        ),
        "chronic_hypertension_yes": int(yes["hypertension"].sum()),
        "prior_infants_4kg_or_more_distribution": number(raw["infant_weight_of_4kg_and_above"])
        .value_counts()
        .sort_index()
        .to_dict(),
        "first_pregnancies_with_prior_infant_4kg_or_more": int(
            (first & (number(raw["infant_weight_of_4kg_and_above"]) >= 1)).sum()
        ),
    }


def _blood_pressure(text: pd.Series) -> tuple[pd.Series, pd.Series]:
    parts = text.str.extract(r"^\s*(\d{2,3})\s*/\s*(\d{2,3})\s*$").astype(float)
    return parts[0], parts[1]


def measures(raw: pd.DataFrame) -> dict:
    height = number(raw["height_cm"])
    out = {
        "height_numeric": _share(height.notna()),
        "height_outside_130_to_190": _share(~height.between(130, 190), height.notna()),
        "height_below_150": _share(height < 150, height.notna()),
    }
    for v in (1, 2):
        hb = number(raw[f"hemoglobin_check_result_v{v}"])
        sbp, dbp = _blood_pressure(raw[f"blood_pressure_v{v}"].fillna(""))
        fundal = raw[f"uterine_size_symphysis_fundal_height_v{v}"]
        scan = raw[f"obstetric_ultrasound_scan_result_v{v}"]
        out |= {
            f"hb_numeric_v{v}": _share(hb.between(4, 18)),
            f"anaemia_below_11_v{v}": _share(hb < 11, hb.between(4, 18)),
            f"bp_parsed_v{v}": _share(sbp.notna()),
            f"bp_140_90_or_more_v{v}": _share((sbp >= 140) | (dbp >= 90), sbp.notna()),
            f"fundal_height_categories_v{v}": fundal.value_counts().to_dict(),
            f"fundal_height_numeric_v{v}": int(number(fundal).notna().sum()),
            f"scan_done_v{v}": _share(raw[f"obstetric_ultrasound_scan_v{v}"] == "yes"),
            f"scan_result_categories_v{v}": scan.value_counts().to_dict(),
            f"urine_protein_positive_v{v}": int(
                (raw[f"urine_albumin_check_result_v{v}"] == "protein_positive").sum()
            ),
        }
    return out


def searched_names(columns: list[str]) -> dict[str, list[str]]:
    return {k: [c for c in columns if re.search(p, c.lower())] for k, p in SEARCHED.items()}


ABSENT = {
    "Previous low birth weight baby": "previous birth weight",
    "Mid upper arm circumference": "mid upper arm circumference",
    "Gestational age at delivery": "gestational age at birth",
    "Estimated fetal weight": "estimated fetal weight",
    "Fetal abdominal circumference": "abdominal circumference",
    "Uterine artery Doppler": "Doppler",
    "Umbilical artery Doppler": "Doppler",
}


def _present_rows(audit: dict) -> list[tuple[str, str, str, str]]:
    h, m, d = audit["history"], audit["measures"], audit["dating"]
    weights = audit["visit_weeks"]["numeric_weight_at_three_or_more_visits"]
    agree = d["edd_within_7_days_of_lmp_plus_280"]
    return [
        ("Previous preterm delivery", "preterm_labour_1", "present but not history",
         f"yes in {h['first_pregnancies_with_prior_preterm_yes']} first pregnancies"),
        ("Previous stillbirth", "number_of_prior_pregnancies_with_stillbirths", "unreliable",
         "see target study ceiling.json"),
        ("Parity and gravidity", "no_pregnancy, number_of_prior_deliveries", "inconsistent",
         f"{h['first_pregnancies_with_prior_deliveries']} first pregnancies, prior deliveries"),
        ("Maternal height", "height_cm", "available", f"numeric share {m['height_numeric']:.3f}"),
        ("Pre pregnancy body mass index", "weight_kg at booking", "proxy only",
         "booking weight, not pre pregnancy"),
        ("Haemoglobin and anaemia", "hemoglobin_check_result_v1, v2", "available, partly missing",
         f"numeric v1 {m['hb_numeric_v1']:.3f}, v2 {m['hb_numeric_v2']:.3f}"),
        ("Hypertension and pre eclampsia", "blood_pressure_v*, urine albumin", "rare and coarse",
         f"prior {h['prior_hypertension_yes']}, chronic {h['chronic_hypertension_yes']}"),
        ("Early ultrasound dating", "obstetric_ultrasound_scan_result_v1", "categories only",
         f"scan at v1 {m['scan_done_v1']:.3f}; LMP and EDD agree {agree:.3f}"),
        ("Numeric fundal height", "uterine_size_symphysis_fundal_height_v*", "categories only",
         f"numeric values at v1: {m['fundal_height_numeric_v1']}"),
        ("Maternal weight gain trajectory", "weight_kg_v1 to v8", "available, sparse",
         f"{weights} records with 3 or more weights"),
    ]  # fmt: skip


def inventory(audit: dict) -> pd.DataFrame:
    names = audit["searched_names"]
    absent = [(k, "none", "absent", f"name search: {names[v]}") for k, v in ABSENT.items()]
    rows = absent + _present_rows(audit)
    return pd.DataFrame(rows, columns=["predictor", "source_field", "status", "evidence"])


def main() -> None:
    raw = _fields()
    audit = {
        "dating": dating(raw),
        "visit_weeks": visit_weeks(raw),
        "history": history(raw),
        "measures": measures(raw),
        "searched_names": searched_names(header()),
    }
    OUT.mkdir(exist_ok=True)
    text = json.dumps(
        audit, indent=1, default=lambda x: x.item() if isinstance(x, np.generic) else str(x)
    )
    (OUT / "field_audit.json").write_text(text + "\n")
    table = inventory(audit)
    table.to_csv(OUT / "predictor_inventory.csv", index=False)
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
