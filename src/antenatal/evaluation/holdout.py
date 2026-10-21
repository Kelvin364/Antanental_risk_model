"""The only gate to the held out partition (Requirements R3 and R5).

Every attempt to read held out records goes through ``HoldoutEvaluator``. Each
attempt, allowed or refused, is appended to ``holdout_access.log`` with a UTC
timestamp. Reading is refused unless the caller confirms that the supervisor
has reviewed the analysis plan, and a second evaluation is refused unless it
is forced, in which case the force is logged.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from antenatal.cohort.builder import Cohort
from antenatal.cohort.partition import PartitionWriter

ACCESS_LOG = "holdout_access.log"


class HoldoutAccessRefused(PermissionError):
    """Raised when the held out partition is requested without the required confirmation."""


class HoldoutEvaluator:
    """Guards, logs and performs access to the held out partition."""

    def __init__(self, partition_dir: Path) -> None:
        self._dir = Path(partition_dir)
        self._writer = PartitionWriter(self._dir)

    @property
    def log_path(self) -> Path:
        """Path of the append only access log."""
        return self._dir / ACCESS_LOG

    def _log(self, event: str) -> None:
        stamp = datetime.now(UTC).isoformat(timespec="seconds")
        with open(self.log_path, "a") as handle:
            handle.write(f"{stamp}\t{event}\n")

    def evaluations_logged(self) -> int:
        """Number of completed evaluations recorded in the access log."""
        if not self.log_path.exists():
            return 0
        lines = self.log_path.read_text().splitlines()
        return sum(1 for line in lines if "\tEVALUATED" in line)

    def load_holdout(self, cohort: Cohort, *, confirm_supervisor_reviewed: bool) -> pd.DataFrame:
        """Return the held out records; refuse and log unless confirmation is given."""
        if not confirm_supervisor_reviewed:
            self._log("REFUSED\tno supervisor confirmation")
            raise HoldoutAccessRefused(
                "The held out partition opens only after the supervisor has reviewed the plan"
            )
        partition = self._writer.load()
        self._log(f"OPENED\tpartition {partition.sha256}")
        frame = cohort.analysis
        return frame[frame["record_id"].isin(partition.holdout_ids)].reset_index(drop=True)

    def check_first_evaluation(self, *, force: bool) -> None:
        """Refuse a repeat evaluation unless forced; log the decision."""
        if self.evaluations_logged() == 0:
            return
        if not force:
            self._log("REFUSED\trepeat evaluation without force")
            raise HoldoutAccessRefused("The held out partition has already been evaluated once")
        self._log("FORCED\trepeat evaluation requested with force")

    def record_evaluation(self, artefact_version: str, artefact_sha256: str) -> None:
        """Append the completed evaluation to the access log."""
        self._log(f"EVALUATED\tartefact {artefact_version} {artefact_sha256}")
