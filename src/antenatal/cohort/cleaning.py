"""Cleaning of the raw file into one typed row per record (Section 3.3.3).

The raw frame is never changed. ``RecordCleaner.clean`` returns a new frame
with one row per record of the released file, holding the outcome, the
eligibility facts, the group key, the registration fields and the visit one and
visit two measurements. Values outside their physiological range are set to
missing and the record is kept.
"""

from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

from antenatal.config import PRIMARY, StudySpec
from antenatal.data.dictionary import (
    BLOOD_PRESSURE_COLUMN,
    OUTCOME_FIELDS,
    REGISTRATION_FIELDS,
    VISIT_MEASUREMENTS,
    VISITS,
    FieldKind,
    visit_column,
)
from antenatal.data.parsers import BloodPressureParser, NumericParser, SentinelPolicy, YesNoParser


def group_key_of(raw: pd.DataFrame, columns: tuple[str, ...]) -> pd.Series:
    """Join the raw text of the registration profile columns into one key per record.

    Records with the same age, last menstrual date, height, registration weight
    and prior deliveries share a key, so they are kept on the same side of every
    split.
    """
    parts = [raw[c].astype(str) for c in columns]
    key = parts[0]
    for part in parts[1:]:
        key = key + "|" + part
    return key


def hash_key(key: str) -> str:
    """Short stable hash of a group key, safe to publish in the manifest."""
    return hashlib.sha256(key.encode()).hexdigest()[:16]


class RecordCleaner:
    """Applies the parsing and range rules to every record of the raw file."""

    def __init__(self, spec: StudySpec = PRIMARY) -> None:
        self._spec = spec
        sentinels = SentinelPolicy(spec.sentinel_tokens)
        self._numbers = NumericParser(sentinels)
        self._pressure = BloodPressureParser(sentinels)
        self._yes_no = YesNoParser()

    def clean(self, raw: pd.DataFrame) -> pd.DataFrame:
        """Return the cleaned frame, indexed like ``raw``."""
        out = pd.DataFrame(index=raw.index)
        out["record_id"] = raw[self._spec.record_id].astype(int)
        out["group_key"] = group_key_of(raw, self._spec.group_key_columns)
        self._add_outcome(raw, out)
        self._add_registration(raw, out)
        for visit in VISITS:
            self._add_visit(raw, out, visit)
        return out

    def _numeric(self, series: pd.Series, range_name: str | None) -> pd.Series:
        bounds = self._spec.ranges.get(range_name) if range_name else None
        values = [self._numbers.parse(v, bounds) for v in series]
        return pd.Series(values, index=series.index, dtype=float)

    def _flag(self, series: pd.Series) -> pd.Series:
        return pd.Series([self._yes_no.parse(v) for v in series], index=series.index, dtype=float)

    def _add_outcome(self, raw: pd.DataFrame, out: pd.DataFrame) -> None:
        out["birth_weight_kg"] = self._numeric(raw[self._spec.outcome_column], None)
        out["lbw"] = (out["birth_weight_kg"] < self._spec.lbw_threshold).astype(int)
        for name, column in OUTCOME_FIELDS.items():
            out[name] = self._flag(raw[column]).eq(1.0)

    def _add_registration(self, raw: pd.DataFrame, out: pd.DataFrame) -> None:
        for field in REGISTRATION_FIELDS:
            if field.kind is FieldKind.NUMERIC:
                out[field.name] = self._numeric(raw[field.column], field.range_name)
            else:
                out[field.name] = self._flag(raw[field.column])

    def _add_visit(self, raw: pd.DataFrame, out: pd.DataFrame, visit: int) -> None:
        ranges = self._spec.ranges
        text = raw[BLOOD_PRESSURE_COLUMN.format(v=visit)]
        readings = [self._pressure.parse(v) for v in text]
        out[f"bp_parsed_v{visit}"] = [r is not None for r in readings]
        in_range = [
            r if r is not None and r.within(ranges.sbp, ranges.dbp) else None for r in readings
        ]
        out[visit_column("sbp", visit)] = [r.systolic if r else np.nan for r in in_range]
        out[visit_column("dbp", visit)] = [r.diastolic if r else np.nan for r in in_range]
        for item in VISIT_MEASUREMENTS:
            if item.column == BLOOD_PRESSURE_COLUMN:
                continue
            values = self._numeric(raw[item.column_for(visit)], item.range_name)
            out[visit_column(item.name, visit)] = values
