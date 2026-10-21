"""Parser cases taken from values that occur in the released file."""

import math

import pytest

from antenatal.config import Range
from antenatal.data.parsers import (
    BloodPressure,
    BloodPressureParser,
    NumericParser,
    SentinelPolicy,
    YesNoParser,
)

SBP, DBP = Range(60, 250), Range(30, 160)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("120/80", BloodPressure(120, 80)),
        ("120 / 80", BloodPressure(120, 80)),
        ("119/65", BloodPressure(119, 65)),
        ("121/20", BloodPressure(121, 20)),
        (" 110/ 70 ", BloodPressure(110, 70)),
    ],
)
def test_blood_pressure_parses_valid_text(text, expected):
    assert BloodPressureParser().parse(text) == expected


@pytest.mark.parametrize("text", ["not_checked", "invalid", "", None, float("nan"), "Not Checked"])
def test_blood_pressure_sentinels_are_missing(text):
    assert BloodPressureParser().parse(text) is None


def test_blood_pressure_without_a_pair_is_missing():
    assert BloodPressureParser().parse("normal") is None


def test_out_of_range_diastolic_is_rejected_after_parsing():
    parser = BloodPressureParser()
    assert parser.parse("121/20") is not None
    assert parser.parse_in_range("121/20", SBP, DBP) is None
    assert parser.parse_in_range("121/70", SBP, DBP) == BloodPressure(121, 70)


@pytest.mark.parametrize("token", ["not_checked", "not checked", "invalid", "no", "NIL", "  "])
def test_sentinel_policy_recognises_tokens(token):
    assert SentinelPolicy().is_missing(token)


def test_sentinel_policy_keeps_numbers():
    assert not SentinelPolicy().is_missing("11.2")


@pytest.mark.parametrize(
    ("text", "expected"),
    [("60", 60.0), ("36.5.", 36.5), ("12..4", 12.4), (" 11.3 ", 11.3), (72, 72.0), (5.5, 5.5)],
)
def test_numeric_parser_reads_and_repairs(text, expected):
    assert NumericParser().parse(text) == pytest.approx(expected)


@pytest.mark.parametrize("text", ["not_checked", "abc", "11.8.9", "", None, math.nan, True])
def test_numeric_parser_rejects_non_numbers(text):
    assert NumericParser().parse(text) is None


def test_numeric_parser_applies_bounds():
    assert NumericParser().parse("121", Range(12, 55)) is None
    assert NumericParser().parse("12", Range(12, 55)) == 12.0


@pytest.mark.parametrize(
    ("text", "expected"), [("yes", 1.0), ("No ", 0.0), ("maybe", None), (None, None)]
)
def test_yes_no_parser(text, expected):
    assert YesNoParser().parse(text) == expected
