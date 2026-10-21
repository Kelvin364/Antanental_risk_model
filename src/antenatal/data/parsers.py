"""Pure value parsers for the text fields of the released file.

Nothing here imports pandas. Each parser takes one raw cell and returns a typed
value or ``None``. The cohort and feature code apply these parsers cell by cell,
so the rule for reading a value is written exactly once and is unit tested
against the odd values found in the file, such as "121/20", "not_checked",
"invalid", "120 / 80", "36.5." and blank cells.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from antenatal.config import SENTINEL_TOKENS, Range

_BP_PATTERN = re.compile(r"(\d{2,3})\s*/\s*(\d{2,3})")
_REPEATED_DOTS = re.compile(r"\.{2,}")
_TRAILING_DOT = re.compile(r"\.$")


def _normalise(value: object) -> str | None:
    """Lower case and strip a cell; return None for a missing cell."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return str(value).strip().lower()


@dataclass(frozen=True)
class BloodPressure:
    """One parsed blood pressure reading in mmHg."""

    systolic: float
    diastolic: float

    def within(self, systolic_range: Range, diastolic_range: Range) -> bool:
        """Return True when both values lie inside their physiological ranges."""
        return systolic_range.contains(self.systolic) and diastolic_range.contains(self.diastolic)


class SentinelPolicy:
    """Decides whether a text cell stands for "no measurement".

    The tokens come from the type audit of the released file: words such as
    "not_checked" or "invalid" stored in fields that should hold numbers.
    """

    def __init__(self, tokens: frozenset[str] = SENTINEL_TOKENS) -> None:
        self._tokens = tokens

    def is_missing(self, value: object) -> bool:
        """Return True for a missing cell or a sentinel token."""
        text = _normalise(value)
        return text is None or text in self._tokens


class BloodPressureParser:
    """Parses "systolic/diastolic" text into a ``BloodPressure``.

    The first pair of two or three digit numbers separated by a slash is taken,
    with spaces allowed around the slash. Sentinel tokens and text without such
    a pair give ``None``. Range checking is a separate step so that a reading
    such as "121/20" is reported as parsed but out of range.
    """

    def __init__(self, sentinels: SentinelPolicy | None = None) -> None:
        self._sentinels = sentinels or SentinelPolicy()

    def parse(self, value: object) -> BloodPressure | None:
        """Return the reading in ``value`` or None when there is none."""
        if self._sentinels.is_missing(value):
            return None
        match = _BP_PATTERN.search(str(value))
        if match is None:
            return None
        return BloodPressure(float(match.group(1)), float(match.group(2)))

    def parse_in_range(
        self, value: object, systolic_range: Range, diastolic_range: Range
    ) -> BloodPressure | None:
        """Return the reading only when it parses and both values are in range."""
        reading = self.parse(value)
        if reading is None or not reading.within(systolic_range, diastolic_range):
            return None
        return reading


class NumericParser:
    """Parses a numeric cell, repairing unambiguous typing slips.

    A doubled full stop ("12..4") and a trailing full stop ("36.5.") are
    repaired. Sentinel tokens, other text and values outside ``bounds`` give
    ``None``.
    """

    def __init__(self, sentinels: SentinelPolicy | None = None) -> None:
        self._sentinels = sentinels or SentinelPolicy()

    def parse(self, value: object, bounds: Range | None = None) -> float | None:
        """Return the number in ``value``, or None when absent or out of bounds."""
        if self._sentinels.is_missing(value):
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, int | float):
            number = float(value)
        else:
            text = _TRAILING_DOT.sub("", _REPEATED_DOTS.sub(".", _normalise(value) or ""))
            try:
                number = float(text)
            except ValueError:
                return None
        if math.isnan(number) or (bounds is not None and not bounds.contains(number)):
            return None
        return number


class YesNoParser:
    """Maps "yes" to 1.0 and "no" to 0.0; anything else, including blanks, to None."""

    _MAP = {"yes": 1.0, "no": 0.0}

    def parse(self, value: object) -> float | None:
        """Return 1.0, 0.0 or None."""
        text = _normalise(value)
        return None if text is None else self._MAP.get(text)
