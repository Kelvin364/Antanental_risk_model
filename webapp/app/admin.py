"""Create the first administrator: ``python -m webapp.app.admin create-admin USERNAME``.

``python -m webapp.app.admin purge-cases`` deletes synthetic cases older than the
retention period (``ANTENATAL_CASE_RETENTION_DAYS``, default 7).

``python -m webapp.app.admin check-database`` describes the database that
``ANTENATAL_DATABASE_URL`` names, reading only and never printing the address.
``python -m webapp.app.admin backup [PATH]`` copies every application table from that
database into a SQLite file (default ``backups/online.sqlite3``).

The generated password is printed once and stored only as a scrypt hash. There
is no default account and no default password. To choose the first password
instead, put it in ``ANTENATAL_ADMIN_PASSWORD``; it is read from the environment,
never from the command line or a file in git, and is not printed. Either way the
administrator must replace it at first sign in. For the online system, run it once on
your own machine with ``ANTENATAL_DATABASE_URL`` set to the hosted database's address: a
free Render instance has no shell, and the account lives in the database, not the host.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from webapp.app.core.settings import Settings
from webapp.app.db.database import create_session_factory
from webapp.app.db.maintenance import check, copy_to_sqlite
from webapp.app.services.auth_service import ADMINISTRATOR, AuthService
from webapp.app.services.retention import purge_old_cases


def _maintenance(command: str, database_url: str, path: str | None) -> int:
    if command == "check-database":
        print(json.dumps(check(database_url), indent=1))
        return 0
    target = Path(path or "backups/online.sqlite3")
    for table, rows in copy_to_sqlite(database_url, target).items():
        print(f"{table}: {rows} rows")
    print(f"Copied into {target}; load it locally with make restore-local CONFIRM=yes")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "command", choices=["create-admin", "purge-cases", "check-database", "backup"]
    )
    parser.add_argument("username", nargs="?", help="create-admin: the username; backup: a path")
    args = parser.parse_args(argv)
    settings = Settings.from_env()
    if args.command in ("check-database", "backup"):
        return _maintenance(args.command, settings.database_url, args.username)
    sessions = create_session_factory(settings.database_url)
    if args.command == "purge-cases":
        removed = purge_old_cases(sessions, settings.case_retention_days)
        print(f"Deleted {removed} synthetic cases older than {settings.case_retention_days} days.")
        return 0
    if not args.username:
        parser.error("create-admin needs a username")
    auth = AuthService(sessions)
    chosen = os.environ.get("ANTENATAL_ADMIN_PASSWORD") or None
    user, password = auth.create_user(args.username, ADMINISTRATOR, "command line", chosen)
    print(f"Administrator {user.username} created.")
    if chosen:
        print("Password taken from ANTENATAL_ADMIN_PASSWORD; change it at first sign in.")
    else:
        print(f"Password (shown once, change it at first sign in): {password}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
