"""Database addresses and the synthetic flag rule on the local SQLite file."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from webapp.app.db.database import create_session_factory, with_driver
from webapp.app.db.models import SyntheticCase, User
from webapp.app.services.model_service import FLAGS


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("postgres://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        (
            "postgresql://u:p@host/db?sslmode=require",
            "postgresql+psycopg://u:p@host/db?sslmode=require",
        ),
        ("postgresql+psycopg://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        ("sqlite:////app/state/app.sqlite3", "sqlite:////app/state/app.sqlite3"),
    ],
)
def test_hosted_addresses_use_the_installed_driver(given, expected):
    assert with_driver(given) == expected


def _case(owner_id: int, synthetic: bool) -> SyntheticCase:
    flags = dict.fromkeys(FLAGS, False)
    return SyntheticCase(
        owner_id=owner_id,
        label="x",
        synthetic=synthetic,
        age=24,
        gravidity=1,
        prior_deliveries=0,
        height_cm=156,
        registration_weight=58,
        **flags,
    )


def test_sqlite_refuses_a_case_without_the_synthetic_flag(tmp_path):
    """The check constraint itself refuses the row, below the entry rules."""
    sessions = create_session_factory(f"sqlite:///{tmp_path / 'app.sqlite3'}")
    with sessions() as session:
        owner = User(username="owner", password_hash="x", role="researcher")
        session.add(owner)
        session.commit()
        session.add(_case(owner.id, synthetic=True))
        session.commit()
        session.add(_case(owner.id, synthetic=False))
        with pytest.raises(IntegrityError, match="synthetic_flag_always_true"):
            session.commit()
