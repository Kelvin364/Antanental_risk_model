"""Access to the services created once by the application factory, and who is signed in.

``current_user`` resolves the session cookie and, for every request that
changes something, checks the CSRF token header against the session's token.
``working_user`` also requires a changed first password before any case work,
and ``administrator`` requires the administrator role. Every check runs on the
server; the interface never decides access on its own (decision D1).
"""

from __future__ import annotations

import hmac
from typing import Annotated

from fastapi import Depends, HTTPException, Request

from webapp.app.services.auth_service import AuthService, CurrentUser
from webapp.app.services.case_service import CaseService
from webapp.app.services.model_service import ModelService
from webapp.app.services.ranking_service import RankingService

SESSION_COOKIE = "antenatal_session"
CSRF_HEADER = "X-CSRF-Token"
CHANGES = {"POST", "PUT", "PATCH", "DELETE"}


def _refuse(status: int, field: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail=[{"field": field, "message": message}])


def model_service(request: Request) -> ModelService:
    """The loaded, checksum verified model service."""
    return request.app.state.model


def case_service(request: Request) -> CaseService:
    """The case service."""
    return request.app.state.cases


def ranking_service(request: Request) -> RankingService:
    """The caseload ranking service."""
    return request.app.state.ranking


def auth_service(request: Request) -> AuthService:
    """Accounts, sessions and the audit trail."""
    return request.app.state.auth


def current_user(request: Request) -> CurrentUser:
    """The signed in user; 401 without a live session, 403 without a matching CSRF token."""
    user = request.app.state.auth.resolve(request.cookies.get(SESSION_COOKIE))
    if user is None:
        raise _refuse(401, "session", "Sign in to continue.")
    if request.method in CHANGES:
        sent = request.headers.get(CSRF_HEADER, "")
        if not hmac.compare_digest(sent, user.csrf_token):
            raise _refuse(403, "csrf", "The request could not be verified. Sign in again.")
    return user


def working_user(user: Annotated[CurrentUser, Depends(current_user)]) -> CurrentUser:
    """A signed in user who has replaced the generated first password."""
    if user.must_change_password:
        raise _refuse(403, "password", "Change your password before working with cases.")
    return user


def administrator(user: Annotated[CurrentUser, Depends(working_user)]) -> CurrentUser:
    """A signed in administrator."""
    if not user.is_administrator:
        raise _refuse(403, "role", "Only an administrator can do this.")
    return user
