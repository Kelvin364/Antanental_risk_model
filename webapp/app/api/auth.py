"""Sign in, sign out, the current user, password change, and administration (decision D1)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from webapp.app.api.deps import (
    SESSION_COOKIE,
    administrator,
    auth_service,
    current_user,
)
from webapp.app.schemas.auth import (
    AccountOut,
    ActiveChange,
    AuditOut,
    GeneratedPassword,
    NewAccount,
    PasswordChange,
    SignedIn,
    SignIn,
)
from webapp.app.services.auth_service import SESSION_HOURS, AuthService, CurrentUser

router = APIRouter(prefix="/api", tags=["accounts"])
Auth = Annotated[AuthService, Depends(auth_service)]
User = Annotated[CurrentUser, Depends(current_user)]
Admin = Annotated[CurrentUser, Depends(administrator)]


def _signed_in(user: CurrentUser) -> SignedIn:
    return SignedIn(
        username=user.username,
        role=user.role,
        csrf_token=user.csrf_token,
        must_change_password=user.must_change_password,
    )


@router.post("/auth/sign-in", response_model=SignedIn)
def sign_in(payload: SignIn, request: Request, response: Response, auth: Auth):
    """Open a session. The cookie is HttpOnly, SameSite strict, and Secure over HTTPS."""
    token, user = auth.sign_in(payload.username.strip().lower(), payload.password)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_HOURS * 3600,
        httponly=True,
        samesite="strict",
        secure=request.url.scheme == "https",
        path="/",
    )
    return _signed_in(user)


@router.post("/auth/sign-out", status_code=204)
def sign_out(request: Request, response: Response, user: User, auth: Auth):
    """End the session on the server and remove the cookie."""
    auth.sign_out(request.cookies.get(SESSION_COOKIE, ""), user.username)
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/auth/me", response_model=SignedIn)
def me(user: User):
    """Who is signed in."""
    return _signed_in(user)


@router.post("/auth/password", status_code=204)
def change_password(payload: PasswordChange, user: User, auth: Auth):
    """Replace one's own password; at least 12 characters."""
    auth.change_password(user, payload.current_password, payload.new_password)


@router.get("/admin/users", response_model=list[AccountOut])
def users(_: Admin, auth: Auth):
    """Every account."""
    return [AccountOut.model_validate(u, from_attributes=True) for u in auth.users()]


@router.post("/admin/users", response_model=GeneratedPassword, status_code=201)
def create_user(payload: NewAccount, admin: Admin, auth: Auth):
    """Create an administrator or researcher account with a generated first password."""
    user, password = auth.create_user(
        payload.username.strip().lower(), payload.role, admin.username
    )
    return GeneratedPassword(username=user.username, password=password)


@router.post("/admin/users/{user_id}/reset-password", response_model=GeneratedPassword)
def reset_password(user_id: int, admin: Admin, auth: Auth):
    """Give an account a new generated password and end its sessions."""
    username, password = auth.reset_password(user_id, admin.username)
    return GeneratedPassword(username=username, password=password)


@router.post("/admin/users/{user_id}/active", status_code=204)
def set_active(user_id: int, payload: ActiveChange, admin: Admin, auth: Auth):
    """Activate or deactivate an account."""
    auth.set_active(user_id, payload.active, admin.username)


@router.get("/admin/audit", response_model=list[AuditOut])
def audit(_: Admin, auth: Auth):
    """The latest 200 audit events, newest first."""
    return [AuditOut.model_validate(e, from_attributes=True) for e in auth.audit_log()]
