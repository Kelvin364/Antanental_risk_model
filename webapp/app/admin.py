"""Create the first administrator: ``python -m webapp.app.admin create-admin USERNAME``.

The generated password is printed once and stored only as a scrypt hash. There
is no default account and no default password. On the host, run it once with
``fly ssh console -C "python -m webapp.app.admin create-admin admin"``.
"""

from __future__ import annotations

import argparse

from webapp.app.core.settings import Settings
from webapp.app.db.database import create_session_factory
from webapp.app.services.auth_service import ADMINISTRATOR, AuthService


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["create-admin"])
    parser.add_argument("username")
    args = parser.parse_args(argv)
    auth = AuthService(create_session_factory(Settings.from_env().database_url))
    user, password = auth.create_user(args.username, ADMINISTRATOR, "command line")
    print(f"Administrator {user.username} created.")
    print(f"Password (shown once, change it at first sign in): {password}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
