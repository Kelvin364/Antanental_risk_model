"""The cohort must reproduce Table 3.5 of the proposal exactly (Requirement R1)."""

import pytest

from antenatal.cohort.builder import CohortBuilder
from antenatal.config import PRIMARY, sensitivity_specs

EXPECTED_FLOW = [8817, 8609, 8193, 8161, 7994, 6203, 6065, 3908]


@pytest.mark.parametrize(("step", "remaining"), list(enumerate(EXPECTED_FLOW)))
def test_flow_count(cohort, step, remaining):
    assert cohort.log.counts()[step] == remaining


def test_analysis_events_and_prevalence(cohort):
    assert cohort.events == 206
    assert round(100 * cohort.events / len(cohort.analysis), 2) == 5.27


def test_eligible_cohort(cohort):
    eligible = cohort.records[cohort.records["eligible"]]
    assert len(eligible) == 8161
    assert int(eligible["lbw"].sum()) == 360


def test_manifest_has_one_row_per_record_with_reasons(cohort):
    manifest = cohort.manifest()
    assert len(manifest) == 8817
    assert manifest["record_id"].is_unique
    excluded = manifest[~manifest["in_analysis_cohort"]]
    assert (excluded["exclusion_reason"] != "").all()
    assert (manifest.loc[manifest["in_analysis_cohort"], "exclusion_reason"] == "").all()


def test_excluded_counts_sum_to_removed_records(cohort):
    flow = cohort.flow_table()
    assert flow["excluded"].sum() == 8817 - 3908


def test_analysis_respects_timing_rule(cohort):
    analysis = cohort.analysis
    assert (analysis["ga_v2"] > analysis["ga_v1"]).all()
    assert (analysis["ga_v2"] <= PRIMARY.gestational_cutoff).all()


def test_no_birth_weight_outside_bounds(cohort):
    low, high = PRIMARY.weight_bounds
    assert cohort.analysis["birth_weight_kg"].between(low, high).all()


@pytest.mark.parametrize(
    ("name", "size", "events"),
    [("S1", 2449, 142), ("S2", 5083, 240), ("S3", 3848, 201), ("S6", 3908, 206)],
)
def test_sensitivity_cohorts(raw, name, size, events):
    variant = CohortBuilder(sensitivity_specs()[name]).build(raw)
    assert (len(variant.analysis), variant.events) == (size, events)


def test_raw_frame_is_not_modified(raw):
    before = raw.copy()
    CohortBuilder().build(raw)
    assert raw.equals(before)
