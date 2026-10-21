"""Engine and session factory. The SQLite file and its tables are created on startup."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from webapp.app.db.models import Base


def _enable_foreign_keys(dbapi_connection, _record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_session_factory(database_url: str) -> sessionmaker:
    """Create the database if needed and return a session factory bound to it."""
    if database_url.startswith("sqlite:///"):
        Path(database_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    engine: Engine = create_engine(database_url, connect_args={"check_same_thread": False})
    if engine.dialect.name == "sqlite":
        event.listen(engine, "connect", _enable_foreign_keys)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)
