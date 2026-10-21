"""Cohort derivation (Table 3.5 of the proposal).

``CohortBuilder`` applies one named method per eligibility step. Each method
keeps the records that pass, records the reason for every record it removes,
and appends a ``Step`` to the ``ExclusionLog``. Sensitivity cohorts come from
the same builder given a different ``StudySpec``.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from antenatal.cohort.cleaning import RecordCleaner, hash_key
from antenatal.cohort.exclusion_log import ExclusionLog, Step
from antenatal.config import PRIMARY, StudySpec

ELIGIBLE_AFTER_STEP = 3


@dataclass
class Cohort:
    """The cleaned records of the whole file with eligibility decided for each."""

    spec: StudySpec
    records: pd.DataFrame
    log: ExclusionLog

    @property
    def analysis(self) -> pd.DataFrame:
        """Records in the analysis cohort, in file order."""
        return self.records[self.records["in_analysis_cohort"]].reset_index(drop=True)

    @property
    def events(self) -> int:
        """Number of low birth weight records in the analysis cohort."""
        return int(self.analysis["lbw"].sum())

    def flow_table(self) -> pd.DataFrame:
        """The exclusion log as Table 3.5."""
        return self.log.to_frame()

    def manifest(self) -> pd.DataFrame:
        """One row per record of the file: eligibility, reason, outcome and hashed group key."""
        frame = self.records
        return pd.DataFrame(
            {
                "record_id": frame["record_id"],
                "group_key_hash": frame["group_key"].map(hash_key),
                "birth_weight_kg": frame["birth_weight_kg"],
                "lbw": frame["lbw"],
                "eligible": frame["eligible"],
                "in_analysis_cohort": frame["in_analysis_cohort"],
                "exclusion_step": frame["exclusion_step"],
                "exclusion_reason": frame["exclusion_reason"],
            }
        )


class CohortBuilder:
    """Derives the eligible and analysis cohorts from the raw file."""

    def __init__(self, spec: StudySpec = PRIMARY) -> None:
        self._spec = spec
        self._cleaner = RecordCleaner(spec)

    def build(self, raw: pd.DataFrame) -> Cohort:
        """Clean ``raw``, apply every step in order and return the ``Cohort``."""
        records = self._cleaner.clean(raw)
        records["exclusion_step"] = pd.array([pd.NA] * len(records), dtype="Int64")
        records["exclusion_reason"] = pd.Series([""] * len(records), index=records.index)
        log = ExclusionLog()
        self._keep(records, log, pd.Series(True, index=records.index), 0, "Records in the file")
        steps = [
            self.require_live_birth,
            self.require_singleton,
            self.require_birth_weight_in_range,
            self.require_visit_one_usable,
            self.require_visit_two_usable,
            self.require_increasing_gestation,
            self.require_visit_two_by_cutoff,
        ]
        if self._spec.exclude_term_and_preterm:
            steps.append(self.exclude_term_and_preterm)
        remaining = pd.Series(True, index=records.index)
        for number, step in enumerate(steps, start=1):
            criterion, passes = step(records)
            remaining = self._keep(records, log, remaining & passes, number, criterion, remaining)
            if number == ELIGIBLE_AFTER_STEP:
                records["eligible"] = remaining
        records["in_analysis_cohort"] = remaining
        return Cohort(self._spec, records, log)

    @staticmethod
    def _keep(
        records: pd.DataFrame,
        log: ExclusionLog,
        kept: pd.Series,
        number: int,
        criterion: str,
        before: pd.Series | None = None,
    ) -> pd.Series:
        before = kept if before is None else before
        dropped = before & ~kept
        records.loc[dropped, "exclusion_step"] = number
        records.loc[dropped, "exclusion_reason"] = criterion
        excluded = int(dropped.sum())
        events = int(records.loc[kept, "lbw"].sum())
        log.append(Step(number, criterion, excluded, int(kept.sum()), events))
        return kept

    def require_live_birth(self, records: pd.DataFrame) -> tuple[str, pd.Series]:
        """Step 1: a live birth is recorded."""
        return "No recorded live birth", records["live_birth"]

    def require_singleton(self, records: pd.DataFrame) -> tuple[str, pd.Series]:
        """Step 2: the delivery is not recorded as multiple."""
        return "Multiple delivery", ~records["multiple_delivery"]

    def require_birth_weight_in_range(self, records: pd.DataFrame) -> tuple[str, pd.Series]:
        """Step 3: the recorded birth weight lies within the analysis bounds."""
        low, high = self._spec.weight_bounds
        criterion = f"Recorded birth weight outside {low:g} to {high:g} kilograms"
        return criterion, records["birth_weight_kg"].between(low, high)

    def require_visit_one_usable(self, records: pd.DataFrame) -> tuple[str, pd.Series]:
        """Step 4: visit one has an in range blood pressure and gestational age."""
        criterion = "Visit one lacks a parsed blood pressure in range or a gestational age in range"
        return criterion, self._visit_usable(records, 1)

    def require_visit_two_usable(self, records: pd.DataFrame) -> tuple[str, pd.Series]:
        """Step 5: visit two exists and meets the same two conditions."""
        criterion = (
            "Visit two absent, or lacks a parsed blood pressure in range or a gestational age "
            "in range"
        )
        return criterion, self._visit_usable(records, 2)

    def require_increasing_gestation(self, records: pd.DataFrame) -> tuple[str, pd.Series]:
        """Step 6: gestational age at visit two is greater than at visit one."""
        return "Gestational age at visit two not greater than at visit one", records["ga_v2"].gt(
            records["ga_v1"]
        )

    def require_visit_two_by_cutoff(self, records: pd.DataFrame) -> tuple[str, pd.Series]:
        """Step 7: visit two happens at or before the gestational cutoff."""
        cutoff = self._spec.gestational_cutoff
        return f"Visit two later than {cutoff} weeks", records["ga_v2"].le(cutoff)

    def exclude_term_and_preterm(self, records: pd.DataFrame) -> tuple[str, pd.Series]:
        """Sensitivity S3: drop records marked as both term delivery and preterm labour."""
        both = records["term_labour"] & records["preterm_labour"]
        return "Recorded as both term delivery and preterm labour", ~both

    @staticmethod
    def _visit_usable(records: pd.DataFrame, visit: int) -> pd.Series:
        return (
            records[f"sbp_v{visit}"].notna()
            & records[f"dbp_v{visit}"].notna()
            & records[f"ga_v{visit}"].notna()
        )
