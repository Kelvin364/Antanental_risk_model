"""Accounts, sign in, sessions and the audit trail (decision D1).

Passwords are hashed with scrypt from the Python standard library, with a
random salt per password. Sessions are random tokens: the browser keeps the
token in an HttpOnly cookie and the database keeps only its SHA 256, so a
copy of the database cannot be used to sign in and signing out ends the
session on the server. Five failed attempts lock an account for fifteen
minutes. The audit trail records who did what, never a clinical value.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from webapp.app.db.models import AuditEvent, User, UserSession

ADMINISTRATOR, RESEARCHER = "administrator", "researcher"
ROLES = (ADMINISTRATOR, RESEARCHER)
SESSION_HOURS = 8
MAX_FAILURES = 5
LOCK_MINUTES = 15
MIN_PASSWORD = 12
USERNAME = re.compile(r"^[a-z0-9._-]{3,40}$")
_SCRYPT = {"n": 2**14, "r": 8, "p": 1, "dklen": 32}


class SignInRefused(PermissionError):
    """Wrong username or password, an inactive account, or a locked account."""


class AccountRefused(ValueError):
    """An account change that breaks a rule (name, role or password length)."""


@dataclass(frozen=True)
class CurrentUser:
    """The signed in user a request acts for."""

    id: int
    username: str
    role: str
    csrf_token: str
    must_change_password: bool

    @property
    def is_administrator(self) -> bool:
        return self.role == ADMINISTRATOR


def hash_password(password: str) -> str:
    """scrypt with a random 16 byte salt, stored as ``scrypt$salt$hash`` in hex."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Constant time comparison of a password against its stored hash."""
    _, salt, digest = stored.split("$")
    candidate = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), **_SCRYPT)
    return hmac.compare_digest(candidate.hex(), digest)


def _aware(moment: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes; every stored time is UTC."""
    return moment.replace(tzinfo=UTC) if moment and moment.tzinfo is None else moment


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class AuthService:
    """Every account, session and audit operation of the application."""

    def __init__(self, sessions: sessionmaker) -> None:
        self._sessions = sessions

    def audit(self, event: str, username: str, detail: str = "") -> None:
        with self._sessions() as session:
            session.add(AuditEvent(event=event, username=username, detail=detail[:200]))
            session.commit()

    def create_user(self, username: str, role: str, actor: str) -> tuple[User, str]:
        """Create an account with a generated password, returned once and never stored."""
        if not USERNAME.match(username):
            raise AccountRefused("Usernames are 3 to 40 lower case letters, digits, . _ or -")
        if role not in ROLES:
            raise AccountRefused(f"Role must be one of {', '.join(ROLES)}")
        password = secrets.token_urlsafe(12)
        with self._sessions() as session:
            if session.scalar(select(User).where(User.username == username)):
                raise AccountRefused(f"The username {username} is taken")
            user = User(username=username, password_hash=hash_password(password), role=role)
            session.add(user)
            session.commit()
        self.audit("account_created", actor, f"{username} as {role}")
        return user, password

    def sign_in(self, username: str, password: str) -> tuple[str, CurrentUser]:
        """Check the password, apply the lockout, and open a session."""
        now = datetime.now(UTC)
        with self._sessions() as session:
            user = session.scalar(select(User).where(User.username == username))
            if user and _aware(user.locked_until) and _aware(user.locked_until) > now:
                self._fail(username, "locked")
                raise SignInRefused(
                    f"Too many failed attempts. Try again in {LOCK_MINUTES} minutes."
                )
            if not user or not user.active or not verify_password(password, user.password_hash):
                if user:
                    user.failed_attempts += 1
                    if user.failed_attempts >= MAX_FAILURES:
                        user.locked_until, user.failed_attempts = (
                            now + timedelta(minutes=LOCK_MINUTES),
                            0,
                        )
                    session.commit()
                self._fail(username, "wrong password or unknown user")
                raise SignInRefused("The username or password is incorrect.")
            user.failed_attempts, user.locked_until = 0, None
            token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
            expires = now + timedelta(hours=SESSION_HOURS)
            session.add(
                UserSession(
                    token_sha256=_token_hash(token),
                    csrf_token=csrf,
                    user_id=user.id,
                    expires_at=expires,
                )
            )
            session.commit()
            current = CurrentUser(
                user.id, user.username, user.role, csrf, user.must_change_password
            )
        self.audit("sign_in", username)
        return token, current

    def _fail(self, username: str, reason: str) -> None:
        self.audit("sign_in_failed", username[:40], reason)

    def resolve(self, token: str | None) -> CurrentUser | None:
        """The user of a live session, or None."""
        if not token:
            return None
        with self._sessions() as session:
            row = session.scalar(
                select(UserSession).where(UserSession.token_sha256 == _token_hash(token))
            )
            if not row or _aware(row.expires_at) <= datetime.now(UTC) or not row.user.active:
                return None
            user = row.user
            return CurrentUser(
                user.id, user.username, user.role, row.csrf_token, user.must_change_password
            )

    def sign_out(self, token: str, username: str) -> None:
        with self._sessions() as session:
            row = session.scalar(
                select(UserSession).where(UserSession.token_sha256 == _token_hash(token))
            )
            if row:
                session.delete(row)
                session.commit()
        self.audit("sign_out", username)

    def change_password(self, user: CurrentUser, current: str, new: str) -> None:
        if len(new) < MIN_PASSWORD:
            raise AccountRefused(f"A new password needs at least {MIN_PASSWORD} characters")
        with self._sessions() as session:
            row = session.get(User, user.id)
            if not verify_password(current, row.password_hash):
                raise AccountRefused("The current password is incorrect")
            row.password_hash, row.must_change_password = hash_password(new), False
            session.commit()
        self.audit("password_changed", user.username)

    def reset_password(self, user_id: int, actor: str) -> tuple[str, str]:
        """Give an account a new generated password and end its sessions."""
        password = secrets.token_urlsafe(12)
        with self._sessions() as session:
            row = session.get(User, user_id)
            if row is None:
                raise AccountRefused(f"No account with id {user_id}")
            row.password_hash, row.must_change_password = hash_password(password), True
            row.failed_attempts, row.locked_until = 0, None
            for live in session.scalars(select(UserSession).where(UserSession.user_id == user_id)):
                session.delete(live)
            session.commit()
            username = row.username
        self.audit("password_reset", actor, username)
        return username, password

    def set_active(self, user_id: int, active: bool, actor: str) -> None:
        with self._sessions() as session:
            row = session.get(User, user_id)
            if row is None:
                raise AccountRefused(f"No account with id {user_id}")
            row.active = active
            session.commit()
            username = row.username
        self.audit("account_activated" if active else "account_deactivated", actor, username)

    def users(self) -> list[User]:
        with self._sessions() as session:
            return list(session.scalars(select(User).order_by(User.id)))

    def audit_log(self, limit: int = 200) -> list[AuditEvent]:
        with self._sessions() as session:
            query = select(AuditEvent).order_by(AuditEvent.id.desc()).limit(limit)
            return list(session.scalars(query))
