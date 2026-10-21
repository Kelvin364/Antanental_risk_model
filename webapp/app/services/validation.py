"""Entry rules of the prototype: the synthetic flag (R10), cleaning ranges and timing (R9).

The ranges are those of ``StudySpec``, the same object the cohort cleaning
uses, so the prototype cannot accept a value the study would have discarded.
"""

from __future__ import annotations

from antenatal.config import PRIMARY, StudySpec
from webapp.app.schemas.cases import CaseCreate, FieldError, VisitCreate

REGISTRATION_RULES = {
    "age": ("age", "Maternal age", "years"),
    "gravidity": ("gravidity", "Number of pregnancies", ""),
    "prior_deliveries": ("prior_deliveries", "Prior deliveries", ""),
    "height_cm": ("height", "Height", "cm"),
    "registration_weight": ("weight", "Registration weight", "kg"),
}
VISIT_RULES = {
    "gestational_week": ("ga", "Gestational week", "weeks", True),
    "systolic": ("sbp", "Systolic blood pressure", "mmHg", True),
    "diastolic": ("dbp", "Diastolic blood pressure", "mmHg", True),
    "weight_kg": ("weight", "Weight", "kg", True),
    "pulse": ("pulse", "Pulse rate", "beats per minute", False),
    "haemoglobin": ("hb", "Haemoglobin", "g/dL", False),
}


class EntryRefused(ValueError):
    """Raised with every refused field so the interface can show each reason."""

    def __init__(self, errors: list[FieldError]) -> None:
        super().__init__("; ".join(f"{e.field}: {e.message}" for e in errors))
        self.errors = errors


class EntryRules:
    """Checks a case or a visit before it is saved or scored."""

    def __init__(self, spec: StudySpec = PRIMARY) -> None:
        self._spec = spec

    def _check(self, field: str, value: float | None, range_name: str, label: str, unit: str):
        rng = self._spec.ranges.get(range_name)
        if value is None:
            return FieldError(field=field, message=f"{label} is required")
        if not rng.contains(value):
            unit_text = f" {unit}" if unit else ""
            return FieldError(
                field=field,
                message=f"{label} must be between {rng.low:g} and {rng.high:g}{unit_text}; "
                f"{value:g} is outside the cleaning range",
            )
        return None

    def check_case(self, case: CaseCreate) -> None:
        """Refuse a case without the synthetic flag or with a value outside its range."""
        errors = []
        if case.synthetic is not True:
            errors.append(
                FieldError(
                    field="synthetic",
                    message=(
                        "Saving is blocked: tick the synthetic flag. "
                        "No real pregnancy may be entered."
                    ),
                )
            )
        for field, (range_name, label, unit) in REGISTRATION_RULES.items():
            error = self._check(field, getattr(case, field), range_name, label, unit)
            if error:
                errors.append(error)
        if errors:
            raise EntryRefused(errors)

    def check_visit(self, visit: VisitCreate, number: int, first_week: float | None = None) -> None:
        """Refuse out of range values and visits that break the timing rule."""
        errors = []
        for field, (range_name, label, unit, required) in VISIT_RULES.items():
            value = getattr(visit, field)
            if value is None and not required:
                continue
            error = self._check(field, value, range_name, label, unit)
            if error:
                errors.append(error)
        errors += self._timing(visit.gestational_week, number, first_week)
        if errors:
            raise EntryRefused(errors)

    def _timing(
        self, week: float | None, number: int, first_week: float | None
    ) -> list[FieldError]:
        cutoff = self._spec.gestational_cutoff
        if week is None:
            return []
        if week > cutoff:
            return [
                FieldError(
                    field="gestational_week",
                    message=(
                        f"Visit {number} must be at or before {cutoff} weeks; " f"{week:g} is later"
                    ),
                )
            ]
        if number == 2 and first_week is not None and week <= first_week:
            return [
                FieldError(
                    field="gestational_week",
                    message=f"Visit two must be later than visit one ({first_week:g} weeks); "
                    f"{week:g} is not",
                )
            ]
        return []
