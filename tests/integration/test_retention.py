"""Synthetic cases older than the retention period are deleted with their visits."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from webapp.app.db.database import create_session_factory
from webapp.app.db.models import SyntheticCase, SyntheticVisit, User
from webapp.app.schemas.cases import CaseCreate
from webapp.app.services.retention import purge_old_cases

NOW = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)
CASE = {
    "synthetic": True,
    "age": 24,
    "gravidity": 2,
    "prior_deliveries": 1,
    "height_cm": 156,
    "registration_weight": 58,
}


def _store(sessions, label: str, created: datetime) -> None:
    with sessions() as session:
        owner = session.scalar(select(User)) or User(
            username="rae", password_hash="x", role="researcher"
        )
        session.add(owner)
        session.flush()
        case = SyntheticCase(
            owner_id=owner.id, created_at=created, **CaseCreate(**CASE, label=label).model_dump()
        )
        case.visits.append(
            SyntheticVisit(visit_number=1, gestational_week=12, systolic=110, diastolic=70)
        )
        session.add(case)
        session.commit()


def test_cases_past_the_retention_period_are_deleted_with_their_visits(tmp_path):
    sessions = create_session_factory(f"sqlite:///{tmp_path / 'r.sqlite3'}")
    _store(sessions, "old", NOW - timedelta(days=8))
    _store(sessions, "recent", NOW - timedelta(days=6))
    assert purge_old_cases(sessions, 7, now=NOW) == 1
    with sessions() as session:
        assert [c.label for c in session.scalars(select(SyntheticCase))] == ["recent"]
        assert session.scalar(select(func.count()).select_from(SyntheticVisit)) == 1
    assert purge_old_cases(sessions, 7, now=NOW) == 0
    with pytest.raises(ValueError):
        purge_old_cases(sessions, 0)


def test_the_purge_command_reports_what_it_deleted(tmp_path, monkeypatch, capsys):
    from webapp.app.admin import main

    monkeypatch.setenv("ANTENATAL_DATABASE_URL", f"sqlite:///{tmp_path / 'p.sqlite3'}")
    monkeypatch.setenv("ANTENATAL_CASE_RETENTION_DAYS", "7")
    assert main(["purge-cases"]) == 0
    assert "Deleted 0 synthetic cases older than 7 days" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        main(["create-admin"])
