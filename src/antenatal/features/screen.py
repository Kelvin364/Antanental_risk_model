"""The availability screen of Section 3.3.4.

A visit measurement enters set C (as its visit one value) only when it is
recorded at both visits for at least the availability threshold of the records
the screen is fitted on. The screen never sees the outcome. It is fitted on
development records for the reported result and refitted inside every outer
training fold so that no test fold information reaches it.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from antenatal.config import PRIMARY, StudySpec
from antenatal.data.dictionary import VISIT_MEASUREMENTS, visit_column


@dataclass(frozen=True)
class ScreenResult:
    """Availability of each measurement at both visits and the pass or fail decision."""

    availability: dict[str, float]
    threshold: float
    n_records: int

    @property
    def passed(self) -> tuple[str, ...]:
        """Measurements available at both visits for at least the threshold share."""
        return tuple(m for m, share in self.availability.items() if share >= self.threshold)

    def to_frame(self) -> pd.DataFrame:
        """One row per measurement with its availability and result."""
        rows = [
            {
                "measurement": name,
                "available_both_visits_percent": round(100 * share, 1),
                "threshold_percent": round(100 * self.threshold, 1),
                "result": "pass" if share >= self.threshold else "fail",
                "n_records": self.n_records,
            }
            for name, share in self.availability.items()
        ]
        return pd.DataFrame(rows)


class AvailabilityScreen:
    """Computes availability at both visits; uses no outcome column."""

    def __init__(self, spec: StudySpec = PRIMARY) -> None:
        self._threshold = spec.availability_threshold

    def fit(self, frame: pd.DataFrame) -> ScreenResult:
        """Return the screen result for the records in ``frame``."""
        availability = {}
        for item in VISIT_MEASUREMENTS:
            both = (
                frame[visit_column(item.name, 1)].notna()
                & frame[visit_column(item.name, 2)].notna()
            )
            availability[item.name] = float(both.mean())
        return ScreenResult(availability, self._threshold, len(frame))
