"""Deleting synthetic cases after a fixed number of days (guideline version 2, Stage 6).

The online system holds synthetic cases only, and none needs to be kept: a case older
than the retention period is deleted with its visits and assessments. It runs when the
application starts, which on the host happens whenever the machine wakes, and on demand
with ``python -m webapp.app.admin purge-cases``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from webapp.app.db.models import SyntheticCase

DEFAULT_RETENTION_DAYS = 7


def _aware(moment: datetime) -> datetime:
    """SQLite returns times without a zone; they are stored in UTC."""
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def purge_old_cases(
    sessions: sessionmaker, days: int = DEFAULT_RETENTION_DAYS, now: datetime | None = None
) -> int:
    """Delete every synthetic case created more than ``days`` days ago; return how many."""
    if days < 1:
        raise ValueError("The retention period must be at least one day")
    cutoff = (now or datetime.now(UTC)) - timedelta(days=days)
    with sessions() as session:
        old = [c for c in session.scalars(select(SyntheticCase)) if _aware(c.created_at) < cutoff]
        for case in old:
            session.delete(case)
        session.commit()
    return len(old)
