"""Write the API's OpenAPI schema to frontend/openapi.json for the typed client.

The interface's TypeScript types are generated from this file, so a change to
a request or response shape reaches the interface through one path. With
``--check`` the script writes nothing and exits with status 1 if the stored
schema differs from the running application's, which continuous integration
uses to catch a stale client.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "frontend" / "openapi.json"


def schema() -> str:
    """The application's OpenAPI document as stable, indented JSON."""
    sys.path.insert(0, str(ROOT))
    from webapp.app.main import create_app

    return json.dumps(create_app().openapi(), indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if the stored schema is stale")
    args = parser.parse_args()
    text = schema()
    if args.check:
        current = TARGET.read_text() if TARGET.exists() else ""
        if current != text:
            print(f"{TARGET.relative_to(ROOT)} is stale; run scripts/export_openapi.py")
            return 1
        print(f"{TARGET.relative_to(ROOT)} is current")
        return 0
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(text)
    print(f"Wrote {TARGET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
