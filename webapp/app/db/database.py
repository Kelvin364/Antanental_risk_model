"""Engine and session factory. The database and its tables are created on startup.

Locally the database is a SQLite file. Online it can be a hosted PostgreSQL
database instead (docs/deviations.md, Render deployment): only the address in
``ANTENATAL_DATABASE_URL`` changes, never the tables or the code that uses them.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event, inspect, text
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


def backend(database_url: str) -> str:
    """The database kind an address names, "sqlite" or "postgresql", never the address itself."""
    return "sqlite" if database_url.startswith("sqlite") else "postgresql"


class EphemeralDatabase(RuntimeError):
    """A persistent database was required but the address names a local SQLite file."""


def require_persistent(database_url: str) -> None:
    """Refuse a SQLite address on a host whose files a restart wipes (Render free instance).

    Without this, a missing ``ANTENATAL_DATABASE_URL`` would quietly fall back to the image's
    SQLite file, and every account and synthetic case would vanish at the next restart.
    """
    if backend(database_url) == "sqlite":
        raise EphemeralDatabase(
            "ANTENATAL_REQUIRE_PERSISTENT_DATABASE is set but ANTENATAL_DATABASE_URL names a "
            "SQLite file, which this host wipes on restart. Set it to the PostgreSQL address."
        )


def add_missing_columns(engine: Engine) -> list[str]:
    """Add any nullable column the models define but an existing table lacks; return them.

    ``create_all`` creates missing tables but never alters an existing one, so a database
    made before a column was added (the local file, or the hosted one) would otherwise
    fail on the first query. Only nullable columns are added, so no existing row changes.
    """
    present = inspect(engine)
    tables = set(present.get_table_names())
    added = []
    with engine.begin() as connection:
        for table in Base.metadata.sorted_tables:
            if table.name not in tables:
                continue
            have = {column["name"] for column in present.get_columns(table.name)}
            for column in table.columns:
                if column.name in have or not column.nullable:
                    continue
                kind = column.type.compile(engine.dialect)
                connection.execute(
                    text(f'ALTER TABLE {table.name} ADD COLUMN "{column.name}" {kind}')
                )
                added.append(f"{table.name}.{column.name}")
    return added


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
    add_missing_columns(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)
