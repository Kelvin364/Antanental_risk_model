"""Create the first administrator: ``python -m webapp.app.admin create-admin USERNAME``.

``python -m webapp.app.admin purge-cases`` deletes synthetic cases older than the
retention period (``ANTENATAL_CASE_RETENTION_DAYS``, default 7).

The generated password is printed once and stored only as a scrypt hash. There
is no default account and no default password. On the host, run it once with
``fly ssh console -C "python -m webapp.app.admin create-admin admin"``.
"""

from __future__ import annotations

import argparse

from webapp.app.core.settings import Settings
from webapp.app.db.database import create_session_factory
from webapp.app.services.auth_service import ADMINISTRATOR, AuthService
from webapp.app.services.retention import purge_old_cases


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["create-admin", "purge-cases"])
    parser.add_argument("username", nargs="?")
    args = parser.parse_args(argv)
    settings = Settings.from_env()
    sessions = create_session_factory(settings.database_url)
    if args.command == "purge-cases":
        removed = purge_old_cases(sessions, settings.case_retention_days)
        print(f"Deleted {removed} synthetic cases older than {settings.case_retention_days} days.")
        return 0
    if not args.username:
        parser.error("create-admin needs a username")
    auth = AuthService(sessions)
    user, password = auth.create_user(args.username, ADMINISTRATOR, "command line")
    print(f"Administrator {user.username} created.")
    print(f"Password (shown once, change it at first sign in): {password}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
