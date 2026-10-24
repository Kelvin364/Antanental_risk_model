"""The only gate to the held out partition (Requirements R3 and R5).

Every attempt to read held out records goes through ``HoldoutEvaluator``. Each
attempt, allowed or refused, is appended to ``holdout_access.log`` with a UTC
timestamp. Reading is refused unless the caller confirms that the supervisor
has reviewed the analysis plan, and a second evaluation is refused unless it
is forced, in which case the force is logged.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from antenatal.artefact.classification import ClassificationRule
from antenatal.cohort.builder import Cohort
from antenatal.cohort.partition import PartitionWriter
from antenatal.config import PRIMARY, StudySpec
from antenatal.evaluation import holdout_tables

ACCESS_LOG = "holdout_access.log"


@dataclass(frozen=True)
class LockedModel:
    """A frozen model for the held out evaluation: its role name, artefact and checksum."""

    name: str
    artefact: object
    sha256: str


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

    def record_evaluation(
        self, artefact_version: str, artefact_sha256: str, detail: str = ""
    ) -> None:
        """Append the completed evaluation, with its provenance, to the access log."""
        self._log(f"EVALUATED\tartefact {artefact_version} {artefact_sha256}\t{detail}".rstrip())

    def evaluate_once(
        self,
        models: list[LockedModel],
        cohort: Cohort,
        out_dir: Path,
        *,
        confirm_supervisor_reviewed: bool,
        rule: ClassificationRule | None = None,
        provenance: str = "",
        force: bool = False,
        spec: StudySpec = PRIMARY,
    ) -> dict[str, pd.DataFrame]:
        """Score the held out records once with the locked models and write every table.

        ``models`` holds the locked candidate as "C" and the frozen comparators as "B"
        and "A". The tables are each model's metrics, the prespecified paired
        comparisons and, with ``rule``, the label at the threshold fixed on development
        records. Every value has its own group bootstrap interval over held out
        registration groups. With 41 events the result confirms or questions the
        direction of the development estimates; it cannot establish small differences.
        """
        if not confirm_supervisor_reviewed:
            self._log("REFUSED\tevaluation without supervisor confirmation")
            raise HoldoutAccessRefused("Evaluation needs confirm_supervisor_reviewed=True")
        self.check_first_evaluation(force=force)
        held = self.load_holdout(cohort, confirm_supervisor_reviewed=True)
        y, groups = held["lbw"].to_numpy(), held["group_key"].to_numpy()
        probabilities = {m.name: np.asarray(m.artefact.score(held)[0]) for m in models}
        tables = {
            "holdout_result": holdout_tables.model_metrics(y, probabilities, groups, spec),
            "holdout_comparisons": holdout_tables.comparisons(y, probabilities, groups, spec),
            "holdout_net_benefit": holdout_tables.net_benefit_table(
                y, probabilities, groups, rule, spec
            ),
        }
        if rule is not None and "C" in probabilities:
            tables["holdout_classification"] = holdout_tables.classification(
                y, probabilities["C"], groups, rule, spec
            )
        stamp = datetime.now(UTC).isoformat(timespec="seconds")
        out_dir.mkdir(parents=True, exist_ok=True)
        for name, table in tables.items():
            table.assign(n=len(held), events=int(y.sum()), evaluated_at=stamp).to_csv(
                out_dir / f"{name}.csv", index=False
            )
        locked = " ".join(f"{m.name}={m.artefact.version}:{m.sha256[:12]}" for m in models)
        detail = f"models {locked}; data {spec.data_sha256[:12]}; results {out_dir}; {provenance}"
        self.record_evaluation(models[0].artefact.version, models[0].sha256, detail)
        return tables
