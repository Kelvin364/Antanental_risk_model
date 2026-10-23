"""Storing synthetic cases and visits, and recording assessments.

Every write goes through ``EntryRules`` first. An assessment is computed by
``ModelService`` and stored with the artefact version and checksum that
produced it and the reference caseload size its rank refers to (R16).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from webapp.app.core.settings import INTERVAL_LABEL, LIMITATION
from webapp.app.db.models import Assessment, SyntheticCase, SyntheticVisit
from webapp.app.schemas.cases import AssessmentOut, CaseCreate, CaseOut, VisitCreate, VisitOut
from webapp.app.services.model_service import ModelService, study_values
from webapp.app.services.validation import EntryRefused, EntryRules

INTERVAL_METHOD = "Wald interval on the logit from the coefficient covariance"


class CaseNotFound(LookupError):
    """Raised when a case identifier does not exist."""


class StepOutOfOrder(ValueError):
    """Raised when a visit or an assessment is requested before its prerequisite."""


def _visit_schema(visit: SyntheticVisit) -> VisitCreate:
    return VisitCreate(
        gestational_week=visit.gestational_week,
        systolic=visit.systolic,
        diastolic=visit.diastolic,
        weight_kg=visit.weight_kg,
        pulse=visit.pulse,
        haemoglobin=visit.haemoglobin,
    )


def _case_schema(case: SyntheticCase) -> CaseCreate:
    fields = CaseCreate.model_fields
    return CaseCreate(**{name: getattr(case, name) for name in fields})


class CaseService:
    """Decides whether a case or visit can be stored, and scores complete cases."""

    def __init__(self, sessions: sessionmaker, model: ModelService, rules: EntryRules) -> None:
        self._sessions = sessions
        self._model = model
        self._rules = rules

    def _get(self, session: Session, case_id: int) -> SyntheticCase:
        case = session.get(SyntheticCase, case_id)
        if case is None:
            raise CaseNotFound(f"No synthetic case with id {case_id}")
        return case

    def create(self, payload: CaseCreate) -> CaseOut:
        """Store a new synthetic case after the flag and range checks."""
        self._rules.check_case(payload)
        with self._sessions() as session:
            count = session.scalar(select(SyntheticCase.id).order_by(SyntheticCase.id.desc()))
            data = payload.model_dump()
            data["label"] = payload.label or f"Synthetic case {(count or 0) + 1}"
            case = SyntheticCase(**data)
            session.add(case)
            session.commit()
            return self.describe(case.id)

    def save_visit(self, case_id: int, number: int, payload: VisitCreate) -> CaseOut:
        """Insert or replace visit ``number``; visit two needs visit one first."""
        with self._sessions() as session:
            case = self._get(session, case_id)
            visits = {v.visit_number: v for v in case.visits}
            if number == 2 and 1 not in visits:
                raise StepOutOfOrder("Record visit one before visit two")
            first_week = visits[1].gestational_week if number == 2 else None
            self._rules.check_visit(payload, number, first_week)
            if number == 1 and 2 in visits:
                self._rules.check_visit(_visit_schema(visits[2]), 2, payload.gestational_week)
            row = visits.get(number) or SyntheticVisit(case_id=case_id, visit_number=number)
            for field, value in payload.model_dump().items():
                setattr(row, field, value)
            session.add(row)
            session.commit()
        return self.describe(case_id)

    def assess(self, case_id: int) -> AssessmentOut:
        """Score a case with both visits, store the assessment and return it."""
        with self._sessions() as session:
            case = self._get(session, case_id)
            visits = {v.visit_number: _visit_schema(v) for v in case.visits}
            if set(visits) != {1, 2}:
                raise StepOutOfOrder("Both visits must be recorded before an assessment")
            values = study_values(_case_schema(case), visits[1], visits[2])
            result = self._model.predict(values)
            row = Assessment(
                case_id=case_id,
                artefact_version=self._model.version,
                artefact_sha256=self._model.sha256,
                reference_caseload_size=result.reference_size,
                rank_position=result.rank,
                probability=result.probability,
                interval_low=result.interval_low,
                interval_high=result.interval_high,
                interval_method=INTERVAL_METHOD,
            )
            session.add(row)
            session.commit()
            return self.assessment_out(row)

    def assessment_out(self, row: Assessment) -> AssessmentOut:
        """The stored assessment in the shape the interface shows."""
        artefact = self._model.artefact
        return AssessmentOut(
            probability=row.probability,
            interval_low=row.interval_low,
            interval_high=row.interval_high,
            interval_label=INTERVAL_LABEL,
            rank_position=row.rank_position,
            reference_caseload_size=row.reference_caseload_size,
            prevalence=artefact.prevalence,
            events=artefact.events,
            artefact_version=row.artefact_version,
            artefact_sha256=row.artefact_sha256,
            limitation=LIMITATION,
            classification=self._model.classification_out(
                row.probability, row.interval_low, row.interval_high
            ),
            assessed_at=row.assessed_at,
        )

    def describe(self, case_id: int) -> CaseOut:
        """A case with its visits and latest assessment."""
        with self._sessions() as session:
            case = self._get(session, case_id)
            latest = case.assessments[-1] if case.assessments else None
            return CaseOut(
                id=case.id,
                **_case_schema(case).model_dump(),
                visits=[
                    VisitOut(visit_number=v.visit_number, **_visit_schema(v).model_dump())
                    for v in case.visits
                ],
                latest_assessment=self.assessment_out(latest) if latest else None,
            )

    def score(self, case: CaseCreate, first: VisitCreate, second: VisitCreate) -> AssessmentOut:
        """Score a complete case without storing it, after the same entry rules."""
        errors = []
        for check in (
            lambda: self._rules.check_case(case),
            lambda: self._rules.check_visit(first, 1),
            lambda: self._rules.check_visit(second, 2, first.gestational_week),
        ):
            try:
                check()
            except EntryRefused as refused:
                errors += refused.errors
        if errors:
            raise EntryRefused(errors)
        result = self._model.predict(study_values(case, first, second))
        row = Assessment(
            artefact_version=self._model.version,
            artefact_sha256=self._model.sha256,
            reference_caseload_size=result.reference_size,
            rank_position=result.rank,
            probability=result.probability,
            interval_low=result.interval_low,
            interval_high=result.interval_high,
        )
        return self.assessment_out(row)
