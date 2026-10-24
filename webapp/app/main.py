"""Application factory. Run with ``uvicorn webapp.app.main:app`` from the repository root.

The factory loads the artefact and verifies its SHA 256 before anything else,
so a changed artefact stops the server from starting (R12).
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from webapp.app.api import auth, cases, health, predict
from webapp.app.core import security
from webapp.app.core.settings import Settings
from webapp.app.db.database import create_session_factory
from webapp.app.services.auth_service import AccountRefused, AuthService, SignInRefused
from webapp.app.services.case_service import CaseNotFound, CaseService, StepOutOfOrder
from webapp.app.services.model_service import ModelService
from webapp.app.services.ranking_service import RankingService
from webapp.app.services.retention import purge_old_cases
from webapp.app.services.validation import EntryRefused, EntryRules


def _handlers(app: FastAPI) -> None:
    @app.exception_handler(EntryRefused)
    def refused(_: Request, exc: EntryRefused) -> JSONResponse:
        return JSONResponse(
            status_code=422, content={"detail": [e.model_dump() for e in exc.errors]}
        )

    @app.exception_handler(CaseNotFound)
    def missing(_: Request, exc: CaseNotFound) -> JSONResponse:
        return JSONResponse(
            status_code=404, content={"detail": [{"field": "case", "message": str(exc)}]}
        )

    @app.exception_handler(SignInRefused)
    def sign_in_refused(_: Request, exc: SignInRefused) -> JSONResponse:
        return JSONResponse(
            status_code=401, content={"detail": [{"field": "sign_in", "message": str(exc)}]}
        )

    @app.exception_handler(AccountRefused)
    def account_refused(_: Request, exc: AccountRefused) -> JSONResponse:
        return JSONResponse(
            status_code=422, content={"detail": [{"field": "account", "message": str(exc)}]}
        )

    @app.exception_handler(StepOutOfOrder)
    def order(_: Request, exc: StepOutOfOrder) -> JSONResponse:
        return JSONResponse(
            status_code=409, content={"detail": [{"field": "step", "message": str(exc)}]}
        )


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application; raises ``ChecksumMismatch`` if the artefact has changed."""
    settings = settings or Settings.from_env()
    model = ModelService(settings.model_dir)
    sessions = create_session_factory(settings.database_url)
    purge_old_cases(sessions, settings.case_retention_days)
    app = FastAPI(
        title="Antenatal caseload prototype",
        description="Research prototype. Synthetic cases only. Not for clinical use.",
        version=model.version,
    )
    app.state.model = model
    app.state.cases = CaseService(sessions, model, EntryRules())
    app.state.ranking = RankingService(sessions, model)
    app.state.auth = AuthService(sessions)
    _handlers(app)
    security.install(app)
    for router in (health.router, auth.router, predict.router, cases.router):
        app.include_router(router)
    # Mounted last so the API routes match first. With ``html`` a path such as
    # /visit-one/ serves visit-one/index.html from the Next.js export.
    if (settings.static_dir / "index.html").exists():
        app.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="interface")
    return app


app = create_app()
