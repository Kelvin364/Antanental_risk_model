"""The held out records can never reach a model fit, and the audit proves it (decision D7)."""

import pytest

from antenatal.cohort.partition import HoldoutLeak, TrainingGuard
from antenatal.evaluation.nested_cv import Experiment, NestedCVRunner
from antenatal.features.sets import SetA


def test_guard_refuses_a_frame_with_one_held_out_record(cohort, sealed):
    partition = sealed[1]
    analysis = cohort.analysis
    mixed = analysis[analysis["record_id"].isin(list(partition.guard().blocked)[:1])]
    with pytest.raises(HoldoutLeak):
        partition.guard().check(mixed)
    partition.guard().check(partition.development(cohort))


def test_every_fit_carries_the_guard(cohort, sealed):
    with pytest.raises(TypeError):
        NestedCVRunner()  # a runner cannot be built without a guard
    runner = NestedCVRunner(sealed[1].guard(), n_jobs=1)
    with pytest.raises(HoldoutLeak):
        runner.fit(cohort.analysis, Experiment("logistic_l2", SetA()), 1)


def test_unarmed_guard_is_only_for_synthetic_tests():
    assert not TrainingGuard.unarmed().armed


def test_audit_never_reads_an_outcome(cohort, sealed):
    with pytest.raises(ValueError):
        sealed[1].holdout_predictors(cohort, ["age", "lbw"])
    held = sealed[1].holdout_predictors(cohort, ["age"])
    assert list(held.columns) == ["record_id", "group_key", "age"]


def test_repository_audit_passes_every_check(root):
    from antenatal.evaluation.integrity import run_audit
    from antenatal.paths import ProjectPaths

    table = run_audit(ProjectPaths.from_root(root))
    assert (table["result"] == "pass").all() and len(table) == 10
    assert not (root / "partitions" / "holdout_access.log").exists()
