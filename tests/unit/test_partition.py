"""The held out partition is sealed first, grouped, stratified and never regenerated."""

import pandas as pd
import pytest

from antenatal.cohort.partition import PartitionAlreadySealed, PartitionTampered, PartitionWriter
from antenatal.evaluation.holdout import HoldoutAccessRefused, HoldoutEvaluator


def _holdout(cohort, partition):
    frame = cohort.analysis
    return frame[frame["record_id"].isin(partition.holdout_ids)]


def test_partition_sizes(cohort, sealed):
    _, partition = sealed
    development = partition.development(cohort)
    held = _holdout(cohort, partition)
    assert (len(development), int(development["lbw"].sum())) == (3126, 165)
    assert (len(held), int(held["lbw"].sum())) == (782, 41)


def test_groups_are_disjoint(cohort, sealed):
    _, partition = sealed
    development = set(partition.development(cohort)["group_key"])
    held = set(_holdout(cohort, partition)["group_key"])
    assert development.isdisjoint(held)


def test_holdout_is_stratified_within_one_event(cohort, sealed):
    _, partition = sealed
    held = _holdout(cohort, partition)
    expected = len(held) * cohort.events / len(cohort.analysis)
    assert abs(int(held["lbw"].sum()) - expected) <= 1


def test_sealing_twice_is_refused(cohort, sealed):
    directory, _ = sealed
    with pytest.raises(PartitionAlreadySealed):
        PartitionWriter(directory).seal_holdout(cohort)


def test_load_verifies_checksum(cohort, tmp_path):
    writer = PartitionWriter(tmp_path)
    writer.seal_holdout(cohort)
    assert writer.load().holdout_ids
    with open(writer.holdout_path, "a") as handle:
        handle.write("1\n")
    with pytest.raises(PartitionTampered):
        writer.load()


def test_outer_folds_cover_each_record_once_per_repeat(cohort, sealed):
    _, partition = sealed
    development = partition.development(cohort)
    folds = PartitionWriter(sealed[0]).outer_folds(development)
    counts = folds.table.groupby("repeat")["record_id"].agg(["count", "nunique"])
    assert (counts["count"] == len(development)).all()
    assert (counts["nunique"] == len(development)).all()
    assert folds.repeats == list(range(10))


def test_outer_folds_keep_groups_whole_and_balance_events(cohort, sealed):
    _, partition = sealed
    development = partition.development(cohort)
    folds = PartitionWriter(sealed[0]).outer_folds(development)
    merged = folds.table.merge(development[["record_id", "group_key", "lbw"]], on="record_id")
    per_group = merged.groupby(["repeat", "group_key"])["fold"].nunique()
    assert (per_group == 1).all()
    events = merged.groupby(["repeat", "fold"])["lbw"].sum()
    assert events.groupby(level="repeat").agg(lambda s: s.max() - s.min()).max() <= 1


def test_write_folds_is_idempotent(cohort, sealed):
    directory, partition = sealed
    writer = PartitionWriter(directory)
    folds = writer.outer_folds(partition.development(cohort))
    writer.write_folds(folds)
    writer.write_folds(folds)
    assert writer.load_folds().table.equals(folds.table)


def test_holdout_refused_without_confirmation_and_logged(cohort, sealed):
    directory, _ = sealed
    evaluator = HoldoutEvaluator(directory)
    with pytest.raises(HoldoutAccessRefused):
        evaluator.load_holdout(cohort, confirm_supervisor_reviewed=False)
    assert "REFUSED" in evaluator.log_path.read_text()


def test_second_evaluation_needs_force(cohort, tmp_path):
    PartitionWriter(tmp_path).seal_holdout(cohort)
    evaluator = HoldoutEvaluator(tmp_path)
    held = evaluator.load_holdout(cohort, confirm_supervisor_reviewed=True)
    assert isinstance(held, pd.DataFrame) and len(held) == 782
    evaluator.check_first_evaluation(force=False)
    evaluator.record_evaluation("1.0.0", "abc")
    with pytest.raises(HoldoutAccessRefused):
        evaluator.check_first_evaluation(force=False)
    evaluator.check_first_evaluation(force=True)
    assert "FORCED" in evaluator.log_path.read_text()
