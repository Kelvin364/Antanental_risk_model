"""Access to the services created once by the application factory."""

from __future__ import annotations

from fastapi import Request

from webapp.app.services.case_service import CaseService
from webapp.app.services.model_service import ModelService
from webapp.app.services.ranking_service import RankingService


def model_service(request: Request) -> ModelService:
    """The loaded, checksum verified model service."""
    return request.app.state.model


def case_service(request: Request) -> CaseService:
    """The case service."""
    return request.app.state.cases


def ranking_service(request: Request) -> RankingService:
    """The caseload ranking service."""
    return request.app.state.ranking
