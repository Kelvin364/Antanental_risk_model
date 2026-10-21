"""Request and response shapes. Ranges are read from ``StudySpec`` for the API documentation.

Pydantic checks types only. The range and timing rules are applied by
``services.validation`` so that every refusal carries a specific message
naming the field and its permitted range.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from antenatal.config import PRIMARY

R = PRIMARY.ranges


def _range(name: str, unit: str) -> str:
    rng = R.get(name)
    return f"{rng.low:g} to {rng.high:g} {unit}".strip()


class CaseCreate(BaseModel):
    """Registration of a synthetic pregnancy (screen 1, set A fields)."""

    synthetic: bool = Field(description="Must be true. No real pregnancy may be entered (R10).")
    label: str | None = Field(default=None, max_length=80, description="Free label, not a name")
    age: float | None = Field(description=f"Maternal age, {_range('age', 'years')}")
    gravidity: float | None = Field(description=f"Number of pregnancies, {_range('gravidity', '')}")
    prior_deliveries: float | None = Field(
        description=f"Prior deliveries, {_range('prior_deliveries', '')}"
    )
    height_cm: float | None = Field(description=f"Height, {_range('height', 'cm')}")
    registration_weight: float | None = Field(description=f"Weight, {_range('weight', 'kg')}")
    prior_caesarean: bool = False
    prior_hypertension_pregnancy: bool = False
    chronic_hypertension: bool = False
    diabetes: bool = False
    hiv: bool = False
    tuberculosis: bool = False
    sickle_cell: bool = False
    smoking: bool = False
    intimate_partner_violence: bool = False


class VisitCreate(BaseModel):
    """Measurements of one antenatal visit (screens 2 and 3)."""

    gestational_week: float | None = Field(description=f"Gestational week, {_range('ga', 'weeks')}")
    systolic: float | None = Field(description=f"Systolic pressure, {_range('sbp', 'mmHg')}")
    diastolic: float | None = Field(description=f"Diastolic pressure, {_range('dbp', 'mmHg')}")
    weight_kg: float | None = Field(description=f"Weight, {_range('weight', 'kg')}")
    pulse: float | None = Field(default=None, description=f"Pulse, {_range('pulse', 'per minute')}")
    haemoglobin: float | None = Field(
        default=None, description=f"Haemoglobin, {_range('hb', 'g/dL')}"
    )


class PredictRequest(BaseModel):
    """A complete case scored without being saved."""

    case: CaseCreate
    visit_one: VisitCreate
    visit_two: VisitCreate


class VisitOut(VisitCreate):
    """A stored visit."""

    visit_number: int


class AssessmentOut(BaseModel):
    """What the Assessment screen shows (Table 3.10, screen 4)."""

    probability: float
    interval_low: float
    interval_high: float
    interval_label: str
    rank_position: int
    reference_caseload_size: int
    prevalence: float
    events: int
    artefact_version: str
    artefact_sha256: str
    limitation: str
    assessed_at: datetime | None = None


class CaseOut(CaseCreate):
    """A stored case with its visits and its latest assessment."""

    id: int
    label: str
    visits: list[VisitOut]
    latest_assessment: AssessmentOut | None = None


class CaseloadRow(BaseModel):
    """One row of the Caseload screen."""

    case_id: int
    label: str
    caseload_position: int
    reference_rank_position: int
    probability: float
    interval_low: float
    interval_high: float
    artefact_version: str


class CaseloadOut(BaseModel):
    """The Caseload screen."""

    rows: list[CaseloadRow]
    reference_caseload_size: int
    prevalence: float
    events: int
    artefact_version: str
    interval_label: str
    limitation: str
    banner: str


class FieldError(BaseModel):
    """One refused value with the reason."""

    field: str
    message: str
