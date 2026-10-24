"""Stage 1 of guideline version 2: the data quality tables the earlier audit lacked.

Missingness by outcome and age band, duplicate and registration group integrity, and
one quality row per predictor: source column, when it is available, how much is
missing in development records, how many implausible values the range rules set to
missing, and whether it is used and why. Development records only wherever the
outcome is involved; the held out records are counted only by identifier.
"""

from __future__ import annotations

import pandas as pd

from antenatal.config import PRIMARY, StudySpec
from antenatal.data.dictionary import (
    EXCLUDED_PREDICTORS,
    REGISTRATION_FIELDS,
    VISIT_MEASUREMENTS,
    FieldKind,
)
from antenatal.data.parsers import BloodPressureParser, NumericParser, SentinelPolicy

AGE_BANDS = ((0, 20, "under 20"), (20, 35, "20 to 34"), (35, 100, "35 or over"))
WHEN = {1: "visit one", 2: "visit two (the prediction moment)"}
EXCLUSION_REASONS = {
    "Risk": "a high or low label of unknown origin that may encode the outcome",
    "total_antenatal_visits": "counts visits that happen after the prediction moment",
    "preterm_labour_1": "a copy of the current pregnancy's delivery outcome field",
    "labour_at_term_1": "a copy of the current pregnancy's delivery outcome field",
    "miscarriages_or_abortions": "excluded by the proposal; agrees with the outcome field",
    "miscarriages_or_abortions_1": "an outcome of the current pregnancy",
    "number_of_miscarriages_or_abortions": "excluded by the proposal with the field above",
}


def _age_band(age: pd.Series) -> pd.Series:
    band = pd.Series("age missing", index=age.index)
    for low, high, label in AGE_BANDS:
        band[(age >= low) & (age < high)] = label
    return band


def predictor_columns() -> list[str]:
    """Every predictor any study feature set can use, in dictionary order."""
    visits = [f"{m.name}_v{v}" for v in (1, 2) for m in VISIT_MEASUREMENTS]
    return [f.name for f in REGISTRATION_FIELDS] + visits


def missingness_by_outcome_age(development: pd.DataFrame) -> pd.DataFrame:
    """Percent missing of each predictor by outcome and by age band, development records."""
    frame = development.assign(
        outcome=development["lbw"].map({1: "low birth weight", 0: "not low birth weight"}),
        age_band=_age_band(development["age"]),
    )
    rows = []
    for column in predictor_columns():
        for by in ("outcome", "age_band"):
            for group, part in frame.groupby(by):
                rows.append(
                    {
                        "predictor": column,
                        "split": by,
                        "group": group,
                        "n": len(part),
                        "missing_percent": round(100 * part[column].isna().mean(), 1),
                    }
                )
    return pd.DataFrame(rows)


def group_integrity(raw: pd.DataFrame, analysis: pd.DataFrame, spec: StudySpec = PRIMARY):
    """Duplicate records and registration group sizes in the analysis cohort."""
    sizes = analysis.groupby("group_key").size()
    rows = [
        ("Records in the file", len(raw)),
        ("Duplicate sequence numbers in the file", int(raw[spec.record_id].duplicated().sum())),
        (
            "Exact duplicate rows ignoring the sequence number",
            int(raw.drop(columns=spec.record_id).duplicated().sum()),
        ),
        ("Records in the analysis cohort", len(analysis)),
        ("Registration groups in the analysis cohort", len(sizes)),
        ("Groups holding more than one record", int((sizes > 1).sum())),
        ("Largest group, records", int(sizes.max())),
    ]
    return pd.DataFrame(rows, columns=["check", "count"])


def _implausible(raw_values: pd.Series, cleaned: pd.Series, parsed) -> int:
    """Values that parse as numbers but were set to missing by the range rules."""
    readable = raw_values.map(parsed).notna()
    return int((readable & cleaned.isna()).sum())


def _registration_rows(raw_dev, development, numbers) -> list[dict]:
    rows = []
    for f in REGISTRATION_FIELDS:
        numeric = f.kind is FieldKind.NUMERIC
        implausible = (
            _implausible(
                raw_dev[f.column].reset_index(drop=True),
                development[f.name].reset_index(drop=True),
                numbers.parse,
            )
            if numeric
            else 0
        )
        rows.append(
            {
                "predictor": f.name,
                "source_column": f.column,
                "available": "registration",
                "missing_percent": round(100 * development[f.name].isna().mean(), 1),
                "implausible_set_missing": implausible,
                "used": "yes, sets A, B and C",
                "reason": "recorded at booking",
            }
        )
    return rows


def _visit_rows(raw_dev, development, numbers, pressure) -> list[dict]:
    rows = []
    for visit in (1, 2):
        for m in VISIT_MEASUREMENTS:
            name, column = f"{m.name}_v{visit}", m.column_for(visit)
            parse = pressure.parse if m.name in ("sbp", "dbp") else numbers.parse
            used, reason = _visit_use(m.name, visit)
            rows.append(
                {
                    "predictor": name,
                    "source_column": column,
                    "available": WHEN[visit],
                    "missing_percent": round(100 * development[name].isna().mean(), 1),
                    "implausible_set_missing": _implausible(
                        raw_dev[column].reset_index(drop=True),
                        development[name].reset_index(drop=True),
                        parse,
                    ),
                    "used": used,
                    "reason": reason,
                }
            )
    return rows


def feature_quality(raw: pd.DataFrame, development: pd.DataFrame, spec: StudySpec = PRIMARY):
    """One row per predictor and per excluded field."""
    raw_dev = raw.set_index(spec.record_id).loc[development["record_id"]]
    numbers, pressure = NumericParser(SentinelPolicy()), BloodPressureParser(SentinelPolicy())
    excluded = [
        {
            "predictor": column,
            "source_column": column,
            "available": "not used",
            "missing_percent": None,
            "implausible_set_missing": None,
            "used": "no",
            "reason": EXCLUSION_REASONS[column],
        }
        for column in EXCLUDED_PREDICTORS
    ]
    rows = _registration_rows(raw_dev, development, numbers)
    rows += _visit_rows(raw_dev, development, numbers, pressure) + excluded
    return pd.DataFrame(rows)


def _visit_use(measure: str, visit: int) -> tuple[str, str]:
    if visit == 2:
        note = "sets B and C"
        if measure == "hb":
            return "yes, " + note, (
                "whether the laboratory result is available at the visit "
                "itself is not recorded in the file"
            )
        return "yes, " + note, "measured at the prediction moment"
    if measure == "hb":
        return "no", "fails the availability screen (recorded at both visits in under 60 percent)"
    return "yes, set C", "passes the availability screen"
