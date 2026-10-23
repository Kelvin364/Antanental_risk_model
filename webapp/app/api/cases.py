"""Synthetic cases, their two visits, assessments and the caseload. Sign in required (D1)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path

from webapp.app.api.deps import auth_service, case_service, ranking_service, working_user
from webapp.app.schemas.cases import AssessmentOut, CaseCreate, CaseloadOut, CaseOut, VisitCreate
from webapp.app.services.auth_service import AuthService, CurrentUser
from webapp.app.services.case_service import CaseService
from webapp.app.services.ranking_service import RankingService

router = APIRouter(prefix="/api", tags=["cases"])
Cases = Annotated[CaseService, Depends(case_service)]
User = Annotated[CurrentUser, Depends(working_user)]


@router.post("/cases", response_model=CaseOut, status_code=201)
def create_case(payload: CaseCreate, cases: Cases, user: User):
    """Register a synthetic pregnancy. Refused unless the synthetic flag is set."""
    return cases.create(payload, user)


@router.get("/cases/{case_id}", response_model=CaseOut)
def get_case(case_id: int, cases: Cases, user: User):
    """A case with its visits and latest assessment."""
    return cases.describe(case_id, user)


@router.put("/cases/{case_id}/visits/{visit_number}", response_model=CaseOut)
def save_visit(
    case_id: int,
    payload: VisitCreate,
    cases: Cases,
    user: User,
    visit_number: Annotated[int, Path(ge=1, le=2)],
):
    """Record or replace visit one or visit two, with range and timing rules."""
    return cases.save_visit(case_id, visit_number, payload, user)


@router.post("/cases/{case_id}/assessment", response_model=AssessmentOut, status_code=201)
def assess(
    case_id: int,
    cases: Cases,
    user: User,
    auth: Annotated[AuthService, Depends(auth_service)],
):
    """Score the case with the frozen artefact and store the assessment."""
    result = cases.assess(case_id, user)
    auth.audit("assessment_created", user.username, f"case {case_id}")
    return result


@router.get("/caseload", response_model=CaseloadOut)
def caseload(ranking: Annotated[RankingService, Depends(ranking_service)], user: User):
    """The signed in user's assessed synthetic cases, ordered by predicted probability."""
    return ranking.caseload(user)
