"""Deleting a user's own case, and removing an account on request (ethics: user rights).

A user deletes their own synthetic case at once, with its visits and assessments, and
nobody else can: someone else's case is reported as not found, exactly like a case that
does not exist, so case numbers cannot be probed. A user asks for their account to be
removed; an administrator then deletes the user's cases, sessions and account in one
transaction. The audit trail keeps every record, including the removal.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from webapp.app.core import policy
from webapp.app.db.models import SyntheticCase, User, UserSession
from webapp.app.services.auth_service import (
    ADMINISTRATOR,
    AccountRefused,
    AuthService,
    CurrentUser,
)
from webapp.app.services.case_service import CaseNotFound


class RemovalRefused(ValueError):
    """An account removal that would leave no administrator, or remove the actor."""


class RemovalService:
    """Case deletion by its owner, removal requests, and account removal by an administrator."""

    def __init__(self, sessions: sessionmaker, auth: AuthService) -> None:
        self._sessions = sessions
        self._auth = auth

    def delete_case(self, case_id: int, owner: CurrentUser) -> None:
        """Delete the owner's case with its visits and assessments."""
        with self._sessions() as session:
            case = session.get(SyntheticCase, case_id)
            if case is None or case.owner_id != owner.id:
                raise CaseNotFound(f"No patient with id {case_id}")
            session.delete(case)
            session.commit()
        self._auth.audit("case_deleted", owner.username, f"case {case_id}")

    def request(self, user: CurrentUser) -> datetime:
        """Record a request for removal; a repeated request keeps the first date."""
        with self._sessions() as session:
            row = session.get(User, user.id)
            if row.deletion_requested_at is None:
                row.deletion_requested_at = datetime.now(UTC)
                session.commit()
                self._auth.audit("deletion_requested", user.username)
            requested = row.deletion_requested_at
        return requested if requested.tzinfo else requested.replace(tzinfo=UTC)

    def remove(self, user_id: int, actor: CurrentUser) -> None:
        """Delete a user's cases, sessions and account in one transaction."""
        if user_id == actor.id:
            raise RemovalRefused(policy.SELF_REMOVAL)
        with self._sessions() as session:
            row = session.get(User, user_id)
            if row is None:
                raise AccountRefused(f"No account with id {user_id}")
            administrators = select(func.count()).where(
                User.role == ADMINISTRATOR, User.active.is_(True)
            )
            if row.role == ADMINISTRATOR and row.active and session.scalar(administrators) <= 1:
                raise RemovalRefused(policy.LAST_ADMINISTRATOR)
            for case in session.scalars(
                select(SyntheticCase).where(SyntheticCase.owner_id == user_id)
            ):
                session.delete(case)
            for live in session.scalars(select(UserSession).where(UserSession.user_id == user_id)):
                session.delete(live)
            username = row.username
            session.delete(row)
            session.commit()
        self._auth.audit("account_removed", actor.username, username)
