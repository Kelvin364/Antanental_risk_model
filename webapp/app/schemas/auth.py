"""Request and response shapes for sign in, accounts and the audit trail (decision D1)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SignIn(BaseModel):
    username: str = Field(max_length=40)
    password: str = Field(max_length=200)


class SignedIn(BaseModel):
    """Who is signed in, the CSRF token to send with every change, and their consent."""

    username: str
    role: str
    csrf_token: str
    must_change_password: bool
    terms_accepted: bool
    terms_version: str | None = None
    terms_accepted_at: datetime | None = None
    deletion_requested_at: datetime | None = None


class Consent(BaseModel):
    """Agreement to the Terms of Use version the user was shown."""

    version: str = Field(max_length=20)


class PolicySection(BaseModel):
    heading: str
    text: str


class PolicyOut(BaseModel):
    """The Privacy Policy and Terms of Use, from webapp/app/core/policy.py."""

    version: str
    consent_sentence: str
    terms_of_use: str
    sentences: dict[str, str]
    sections: list[PolicySection]


class PasswordChange(BaseModel):
    current_password: str = Field(max_length=200)
    new_password: str = Field(max_length=200)


class NewAccount(BaseModel):
    username: str = Field(max_length=40)
    role: str


class ActiveChange(BaseModel):
    active: bool


class AccountOut(BaseModel):
    id: int
    username: str
    role: str
    active: bool
    must_change_password: bool
    created_at: datetime
    deletion_requested_at: datetime | None = None


class GeneratedPassword(BaseModel):
    """A generated password, shown once to the administrator and never stored in clear."""

    username: str
    password: str
    note: str = "Shown once. Give it to the user, who must change it at first sign in."


class AuditOut(BaseModel):
    at: datetime
    event: str
    username: str
    detail: str
