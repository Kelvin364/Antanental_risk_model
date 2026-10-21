"""Derived columns shared by the analysis and the prototype.

The analysis and the application both call ``FeatureBuilder.derive`` on a
frame of cleaned values, so a case scored in the prototype is built by exactly
the same code as a record in the study.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from antenatal.data.dictionary import REGISTRATION_FIELDS, VISIT_MEASUREMENTS, VISITS, visit_column

GAP = "d_ga"


def input_columns() -> list[str]:
    """Cleaned values a case must provide: registration fields and both visits."""
    registration = [f.name for f in REGISTRATION_FIELDS]
    visits = [visit_column(m.name, v) for v in VISITS for m in VISIT_MEASUREMENTS]
    return registration + visits


def change_column(name: str) -> str:
    """Name of the visit two minus visit one change of measurement ``name``."""
    return f"d_{name}"


def rate_column(name: str) -> str:
    """Name of the change per week of gestation of measurement ``name``."""
    return f"{name}_per_week"


class FeatureBuilder:
    """Adds change and rate columns to a frame that holds visit one and two values."""

    def derive(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Return a copy of ``frame`` with every change and rate column added.

        Input columns that are absent are added as missing values.
        """
        out = frame.copy()
        for column in input_columns():
            if column not in out:
                out[column] = np.nan
        for item in VISIT_MEASUREMENTS:
            first, second = visit_column(item.name, 1), visit_column(item.name, 2)
            out[change_column(item.name)] = out[second] - out[first]
        weeks = out[GAP].where(out[GAP] > 0, np.nan)
        for item in VISIT_MEASUREMENTS:
            if item.name != "ga":
                out[rate_column(item.name)] = out[change_column(item.name)] / weeks
        return out

    @staticmethod
    def matrix(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
        """Select ``columns`` as a float frame, in the given order."""
        return frame[columns].astype(float)
