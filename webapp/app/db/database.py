"""Engine and session factory. The database and its tables are created on startup.

Locally the database is a SQLite file. Online it can be a hosted PostgreSQL
database instead (docs/deviations.md, Render deployment): only the address in
``ANTENATAL_DATABASE_URL`` changes, never the tables or the code that uses them.
"""

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


def with_driver(database_url: str) -> str:
    """Point a PostgreSQL address at the installed psycopg driver.

    Hosts hand out ``postgres://`` or ``postgresql://`` addresses; SQLAlchemy
    reads the first as unknown and the second as the psycopg2 driver, which is
    not installed. Any other address is returned unchanged.
    """
    for prefix in ("postgres://", "postgresql://"):
        if database_url.startswith(prefix):
            return "postgresql+psycopg://" + database_url.removeprefix(prefix)
    return database_url


def create_session_factory(database_url: str) -> sessionmaker:
    """Create the database if needed and return a session factory bound to it."""
    database_url = with_driver(database_url)
    if database_url.startswith("sqlite:///"):
        Path(database_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    if database_url.startswith("sqlite"):
        engine: Engine = create_engine(database_url, connect_args={"check_same_thread": False})
        event.listen(engine, "connect", _enable_foreign_keys)
    else:
        # A hosted database can close idle connections; test each one before use.
        engine = create_engine(database_url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)
