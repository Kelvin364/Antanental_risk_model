"""Request and response shapes for sign in, accounts and the audit trail (decision D1)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SignIn(BaseModel):
    username: str = Field(max_length=40)
    password: str = Field(max_length=200)


class SignedIn(BaseModel):
    """Who is signed in, and the CSRF token to send with every change."""

    username: str
    role: str
    csrf_token: str
    must_change_password: bool


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
