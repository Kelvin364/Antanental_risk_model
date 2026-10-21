"""Stateless scoring of a complete synthetic case."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from webapp.app.api.deps import case_service
from webapp.app.schemas.cases import AssessmentOut, PredictRequest
from webapp.app.services.case_service import CaseService

router = APIRouter(prefix="/api", tags=["predict"])


@router.post("/predict", response_model=AssessmentOut)
def predict(payload: PredictRequest, cases: Annotated[CaseService, Depends(case_service)]):
    """Apply the entry rules and score the case with the frozen artefact, without saving it."""
    return cases.score(payload.case, payload.visit_one, payload.visit_two)
