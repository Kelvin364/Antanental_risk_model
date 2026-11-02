"""Read only checks of the connected database and a copy of it into a local SQLite file.

``check`` answers "is the online system really writing to the hosted database?" without
printing the address or any credential: the database kind, the host, the server version,
whether the connection is encrypted, a round trip time, and the row count of every
application table. ``copy_to_sqlite`` replaces the Fly.io volume backup: it copies every
application table from the hosted database into ``backups/online.sqlite3``, which
``make restore-local`` loads so the local system can stand in for the online one.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.engine import make_url

from webapp.app.db.database import backend, create_session_factory, with_driver
from webapp.app.db.models import Base


def _encrypted(connection, kind: str) -> str:
    if kind == "sqlite":
        return "not applicable (local file)"
    row = connection.execute(text("SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()"))
    return "yes" if row.scalar() else "no"


def _version(connection, kind: str) -> str:
    query = "SELECT sqlite_version()" if kind == "sqlite" else "SHOW server_version"
    return str(connection.execute(text(query)).scalar())


def check(database_url: str) -> dict[str, object]:
    """Describe the database an address names, reading only."""
    kind = backend(database_url)
    engine = create_engine(with_driver(database_url))
    present = set(inspect(engine).get_table_names())
    with engine.connect() as connection:
        started = time.perf_counter()
        connection.execute(text("SELECT 1"))
        round_trip = (time.perf_counter() - started) * 1000
        counts = {
            table.name: connection.execute(select(func.count()).select_from(table)).scalar()
            for table in Base.metadata.sorted_tables
            if table.name in present
        }
        report = {
            "database": kind,
            "host": make_url(with_driver(database_url)).host or "local file",
            "server_version": _version(connection, kind),
            "encrypted": _encrypted(connection, kind),
            "round_trip_ms": round(round_trip, 1),
            "missing_tables": sorted(set(Base.metadata.tables) - present),
            "rows": counts,
        }
    engine.dispose()
    return report


def copy_to_sqlite(source_url: str, target: Path) -> dict[str, int]:
    """Copy every application table into a new SQLite file; returns rows copied per table.

    The copy is written beside the target and renamed into place only once complete, so an
    interrupted run never leaves a half written backup.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(".partial")
    partial.unlink(missing_ok=True)
    create_session_factory(f"sqlite:///{partial}")
    source = create_engine(with_driver(source_url))
    destination = create_engine(f"sqlite:///{partial}")
    counts: dict[str, int] = {}
    with source.connect() as reader, destination.begin() as writer:
        for table in Base.metadata.sorted_tables:
            rows = [dict(row._mapping) for row in reader.execute(table.select())]
            if rows:
                writer.execute(table.insert(), rows)
            counts[table.name] = len(rows)
    source.dispose()
    destination.dispose()
    os.replace(partial, target)
    return counts
