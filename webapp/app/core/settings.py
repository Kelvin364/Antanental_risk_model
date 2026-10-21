"""Application settings, read from environment variables with repository relative defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

WEBAPP = Path(__file__).resolve().parents[2]

LIMITATION = (
    "Research estimate from a study on one Tanzanian dataset. Not validated for any pregnancy. "
    "Not a clinical risk category and not a recommendation for care."
)
SYNTHETIC_BANNER = "Synthetic cases only. Do not enter any real pregnancy."
INTERVAL_LABEL = (
    "95 percent confidence interval for the estimated probability, reflecting uncertainty in "
    "the fitted model. It is not a range for this pregnancy's outcome."
)


@dataclass(frozen=True)
class Settings:
    """Where the application finds its artefact, its database and its static files."""

    model_dir: Path
    database_url: str
    static_dir: Path

    @classmethod
    def from_env(cls) -> Settings:
        """Read ``ANTENATAL_MODEL_DIR``, ``ANTENATAL_DATABASE_URL`` and ``ANTENATAL_STATIC_DIR``."""
        database = WEBAPP / "data" / "app.sqlite3"
        return cls(
            model_dir=Path(os.environ.get("ANTENATAL_MODEL_DIR", WEBAPP / "model")),
            database_url=os.environ.get("ANTENATAL_DATABASE_URL", f"sqlite:///{database}"),
            static_dir=Path(os.environ.get("ANTENATAL_STATIC_DIR", WEBAPP / "static")),
        )
