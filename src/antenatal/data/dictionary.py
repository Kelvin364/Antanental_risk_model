"""Mapping from study fields to columns of the released file.

Every feature in Table 3.6 of the proposal maps to one named source column
here, and the prototype input fields use the same names. Changing a mapping in
this file changes it for the cohort, the features and the application at once.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FieldKind(Enum):
    """How a raw cell is read."""

    NUMERIC = "numeric"
    YES_NO = "yes_no"


@dataclass(frozen=True)
class RegistrationField:
    """One registration characteristic of set A."""

    name: str
    column: str
    kind: FieldKind
    range_name: str | None = None
    label: str = ""


@dataclass(frozen=True)
class VisitMeasurement:
    """One measurement recorded at each antenatal visit.

    ``column`` holds a ``{v}`` placeholder for the visit number. Blood pressure
    is stored as one text column that yields both ``sbp`` and ``dbp``.
    """

    name: str
    column: str
    range_name: str
    label: str
    unit: str

    def column_for(self, visit: int) -> str:
        """Return the raw column name of this measurement at ``visit``."""
        return self.column.format(v=visit)


REGISTRATION_FIELDS: tuple[RegistrationField, ...] = (
    RegistrationField("age", "age", FieldKind.NUMERIC, "age", "Maternal age, years"),
    RegistrationField(
        "gravidity", "no_pregnancy", FieldKind.NUMERIC, "gravidity", "Number of pregnancies"
    ),
    RegistrationField(
        "prior_deliveries",
        "number_of_prior_deliveries",
        FieldKind.NUMERIC,
        "prior_deliveries",
        "Prior deliveries",
    ),
    RegistrationField("height_cm", "height_cm", FieldKind.NUMERIC, "height", "Height, cm"),
    RegistrationField(
        "registration_weight", "weight_kg", FieldKind.NUMERIC, "weight", "Registration weight, kg"
    ),
    RegistrationField(
        "prior_caesarean", "prior_caesarean_delivery", FieldKind.YES_NO, label="Prior caesarean"
    ),
    RegistrationField(
        "prior_hypertension_pregnancy",
        "presence_of_hypertension_in_previous_pregnancies",
        FieldKind.YES_NO,
        label="Hypertension in a previous pregnancy",
    ),
    RegistrationField(
        "chronic_hypertension", "hypertension", FieldKind.YES_NO, label="Chronic hypertension"
    ),
    RegistrationField("diabetes", "diabetes_mellitus", FieldKind.YES_NO, label="Diabetes"),
    RegistrationField("hiv", "hiv", FieldKind.YES_NO, label="HIV"),
    RegistrationField("tuberculosis", "tuberculosis", FieldKind.YES_NO, label="Tuberculosis"),
    RegistrationField(
        "sickle_cell",
        "sickle_cell_or_haematological_disorders",
        FieldKind.YES_NO,
        label="Sickle cell or haematological disorder",
    ),
    RegistrationField("smoking", "smoking", FieldKind.YES_NO, label="Smoking"),
    RegistrationField(
        "intimate_partner_violence",
        "intimate_partner_violence",
        FieldKind.YES_NO,
        label="Intimate partner violence",
    ),
)

BLOOD_PRESSURE_COLUMN = "blood_pressure_v{v}"

VISIT_MEASUREMENTS: tuple[VisitMeasurement, ...] = (
    VisitMeasurement("sbp", BLOOD_PRESSURE_COLUMN, "sbp", "Systolic blood pressure", "mmHg"),
    VisitMeasurement("dbp", BLOOD_PRESSURE_COLUMN, "dbp", "Diastolic blood pressure", "mmHg"),
    VisitMeasurement("weight", "weight_kg_v{v}", "weight", "Weight", "kg"),
    VisitMeasurement("ga", "pregnant_week_number_v{v}", "ga", "Gestational week", "weeks"),
    VisitMeasurement("pulse", "pulse_rate_v{v}", "pulse", "Pulse rate", "beats per minute"),
    VisitMeasurement("hb", "hemoglobin_check_result_v{v}", "hb", "Haemoglobin", "g/dL"),
)

VISITS: tuple[int, int] = (1, 2)

OUTCOME_FIELDS = {
    "live_birth": "live_births",
    "multiple_delivery": "twins_delivery",
    "term_labour": "labour_at_term",
    "preterm_labour": "preterm_labour",
}

EXCLUDED_PREDICTORS: tuple[str, ...] = (
    "Risk",
    "total_antenatal_visits",
    "preterm_labour_1",
    "labour_at_term_1",
    "miscarriages_or_abortions",
    "miscarriages_or_abortions_1",
    "number_of_miscarriages_or_abortions",
)


def measurement(name: str) -> VisitMeasurement:
    """Return the visit measurement called ``name``."""
    for item in VISIT_MEASUREMENTS:
        if item.name == name:
            return item
    raise KeyError(name)


def visit_column(name: str, visit: int) -> str:
    """Return the cleaned column name of measurement ``name`` at ``visit``, as in ``sbp_v2``."""
    return f"{name}_v{visit}"


def source_columns() -> set[str]:
    """Every raw column that can feed a predictor."""
    columns = {f.column for f in REGISTRATION_FIELDS}
    columns |= {m.column_for(v) for m in VISIT_MEASUREMENTS for v in VISITS}
    return columns
