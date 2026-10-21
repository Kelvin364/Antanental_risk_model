"""Data quality audit of the released file (Table 3.3 and Figure 3.1).

These checks run on the whole released file because they describe the file
itself, before any cohort or partition exists. None of them uses the low birth
weight outcome, so none of them can leak held out information into a modelling
decision.
"""

from __future__ import annotations

import re

import pandas as pd

from antenatal.config import PRIMARY, StudySpec
from antenatal.data.parsers import NumericParser, SentinelPolicy

SUSPECT_PAIRS: tuple[tuple[str, str], ...] = (
    ("preterm_labour_1", "preterm_labour"),
    ("labour_at_term_1", "labour_at_term"),
    ("miscarriages_or_abortions", "miscarriages_or_abortions_1"),
)


def _text(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower()


def suspect_field_crosstabs(raw: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Cross tables of each suspect history field against its outcome field (Figure 3.1)."""
    return {
        f"{a} by {b}": pd.crosstab(_text(raw[a]), _text(raw[b]), rownames=[a], colnames=[b])
        for a, b in SUSPECT_PAIRS
    }


def quality_findings(raw: pd.DataFrame, spec: StudySpec = PRIMARY) -> pd.DataFrame:
    """The findings of Table 3.3, each counted from the file."""
    rows = []
    for history, outcome in SUSPECT_PAIRS[:2]:
        agree = int((_text(raw[history]) == _text(raw[outcome])).sum())
        rows.append((f"{history} agrees with {outcome}", agree, len(raw)))
    mis_hist = _text(raw["miscarriages_or_abortions"]) == "yes"
    mis_out = _text(raw["miscarriages_or_abortions_1"]) == "yes"
    rows.append(
        (
            "miscarriages_or_abortions positive where miscarriages_or_abortions_1 is positive",
            int((mis_hist & mis_out).sum()),
            int(mis_out.sum()),
        )
    )
    both = (_text(raw["labour_at_term"]) == "yes") & (_text(raw["preterm_labour"]) == "yes")
    rows.append(
        ("Records marked as both term delivery and preterm labour", int(both.sum()), len(raw))
    )
    weight = pd.to_numeric(raw[spec.outcome_column], errors="coerce")
    high = spec.weight_bounds[1]
    rows.append((f"Recorded birth weight above {high:g} kg", int((weight > high).sum()), len(raw)))
    rows.append(("Maximum recorded birth weight, kg", float(weight.max()), len(raw)))
    duplicates = int(raw.drop(columns=spec.record_id).duplicated().sum())
    rows.append(("Exact duplicate rows ignoring the sequence number", duplicates, len(raw)))
    return pd.DataFrame(rows, columns=["finding", "count", "denominator"])


def registration_ranges(raw: pd.DataFrame) -> pd.DataFrame:
    """Observed minimum and maximum of the registration numbers before range rules."""
    columns = {
        "age": "age",
        "no_pregnancy": "number of pregnancies",
        "height_cm": "height, cm",
        "weight_kg": "registration weight, kg",
    }
    parser = NumericParser()
    rows = []
    for column, label in columns.items():
        values = pd.Series([parser.parse(v) for v in raw[column]], dtype=float)
        rows.append({"field": label, "minimum": values.min(), "maximum": values.max()})
    return pd.DataFrame(rows)


def consistency_checks(raw: pd.DataFrame) -> pd.DataFrame:
    """Checks of related fields that should tell the same story."""
    gravidity = pd.to_numeric(raw["no_pregnancy"], errors="coerce")
    prior = pd.to_numeric(raw["number_of_prior_deliveries"], errors="coerce")
    lmp = pd.to_datetime(raw["last_normal_menustration_date"], format="%m/%d/%Y", errors="coerce")
    edd = pd.to_datetime(raw["expected_date_of_delivery"], format="%m/%d/%Y", errors="coerce")
    days = (edd - lmp).dt.days
    same = _text(raw["intimate_partner_violence_v1"]) == _text(raw["alcohol_and_drugs_abuse_v1"])
    rows = [
        (
            "Prior deliveries at or above number of pregnancies",
            int((prior >= gravidity).sum()),
            len(raw),
        ),
        (
            "Expected delivery 275 to 285 days after last menstrual date",
            int(days.between(275, 285).sum()),
            int(days.notna().sum()),
        ),
        (
            "Visit one violence answer identical to visit one substance answer",
            int(same.sum()),
            len(raw),
        ),
    ]
    return pd.DataFrame(rows, columns=["check", "count", "denominator"])


def non_numeric_tokens(raw: pd.DataFrame, minimum_numeric_share: float = 0.5) -> pd.DataFrame:
    """Text tokens found in columns that mostly hold numbers, with counts.

    These tokens are the evidence for the sentinel list in ``StudySpec``.
    """
    policy = SentinelPolicy()
    rows = []
    for column in raw.columns:
        series = raw[column]
        if pd.api.types.is_numeric_dtype(series):
            continue
        values = series.dropna()
        numeric = pd.to_numeric(values, errors="coerce")
        if len(values) == 0 or numeric.notna().mean() < minimum_numeric_share:
            continue
        tokens = _text(values[numeric.isna()])
        for token, count in tokens.value_counts().items():
            repairable = bool(re.fullmatch(r"[\d.]+", token))
            rows.append((column, token, int(count), policy.is_missing(token), repairable))
    columns = ["column", "token", "rows", "treated_as_missing", "repaired_as_number"]
    return pd.DataFrame(rows, columns=columns)
