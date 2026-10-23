"""Measurable evidence that the held out partition never reached training (decision D7).

``python -m antenatal audit-holdout`` runs every check below and writes
``outputs/tables/holdout_integrity.csv`` and ``docs/evidence/holdout_integrity.md``.
Each check reads identifiers, predictor values or stored outputs only. No check
reads a held out outcome, fits a model or scores the held out records, so the
audit can run at any time without spending the single evaluation.
"""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pandas as pd

from antenatal.artefact.artefact import FittedPipelineArtefact
from antenatal.cohort.partition import HoldoutLeak
from antenatal.config import PRIMARY, StudySpec
from antenatal.evaluation.holdout import HoldoutEvaluator
from antenatal.paths import ProjectPaths
from antenatal.study import SERVED_MODEL, SERVED_SET, load_context, load_results

STORED_PREDICTIONS = (
    "oof_predictions.parquet",
    "oof_extensions.parquet",
    "learning_curve_predictions.parquet",
    "oof_experiments_v2.parquet",
)


def _row(check: str, passed: bool, value: object, evidence: str) -> dict[str, object]:
    return {
        "check": check,
        "result": "pass" if passed else "fail",
        "value": value,
        "evidence": evidence,
    }


def _guard_refuses(guard, held: pd.DataFrame) -> bool:
    try:
        guard.check(held.head(1))
    except HoldoutLeak:
        return True
    return False


def _duplicates(development: pd.DataFrame, held: pd.DataFrame, columns: list[str]) -> int:
    """Held out records whose whole predictor vector equals some development record's."""

    def key(frame: pd.DataFrame) -> pd.Series:
        values = frame[columns].astype(float).round(6)
        return pd.util.hash_pandas_object(values, index=False)

    return int(key(held).isin(set(key(development))).sum())


def _split_checks(development, held, partition, guard) -> list[dict[str, object]]:
    """The split is the sealed one, and no record or registration group is on both sides."""
    inside = int(development["record_id"].isin(guard.blocked).sum())
    shared = len(set(development["group_key"]) & set(held["group_key"]))
    return [
        _row(
            "Held out file matches its recorded SHA 256",
            True,
            partition.sha256[:16],
            "partitions/holdout.sha256, verified on load",
        ),
        _row("Development records that are held out", inside == 0, inside, "Partition.development"),
        _row(
            "Registration groups shared by both partitions",
            shared == 0,
            shared,
            "group_key of both partitions",
        ),
        _row(
            "Training guard refuses a held out record",
            _guard_refuses(guard, held),
            f"{partition.holdout_size} records blocked",
            "TrainingGuard, required by every model fit",
        ),
    ]


def _output_checks(paths, context, artefact, guard) -> list[dict[str, object]]:
    """No stored prediction scored a held out record, and the served reference is development."""
    rows = []
    for name in STORED_PREDICTIONS:
        stored = pd.read_parquet(paths.outputs / name, columns=["record_id"])
        leaked = int(stored["record_id"].isin(guard.blocked).sum())
        rows.append(_row(f"Held out records in {name}", leaked == 0, leaked, f"outputs/{name}"))
    reference = load_results(paths, context).averaged(SERVED_MODEL, SERVED_SET.name)
    same = len(reference) == len(artefact.reference_probabilities) and np.allclose(
        np.sort(reference), np.sort(artefact.reference_probabilities), atol=1e-12
    )
    rows.append(
        _row(
            "Served reference caseload equals development out of fold predictions",
            same,
            artefact.n_development,
            "webapp/model/lbw_model.joblib",
        )
    )
    return rows


def run_audit(paths: ProjectPaths, spec: StudySpec = PRIMARY) -> pd.DataFrame:
    """Every integrity check as one row: check, result, value, evidence."""
    context = load_context(paths, spec)
    development, partition = context.development, context.partition
    artefact = FittedPipelineArtefact.load(paths.model, verify=True)
    columns = artefact.feature_names
    held = partition.holdout_predictors(context.cohort, columns)
    guard = partition.guard()
    rows = _split_checks(development, held, partition, guard)
    rows += _output_checks(paths, context, artefact, guard)
    duplicates = _duplicates(development, held, columns)
    rows.append(
        _row(
            "Held out records with a predictor vector identical to a development record",
            duplicates == 0,
            duplicates,
            f"{len(columns)} predictors of the served model",
        )
    )
    evaluations = HoldoutEvaluator(paths.partitions).evaluations_logged()
    rows.append(
        _row(
            "Held out evaluations recorded",
            evaluations <= 1,
            evaluations,
            "partitions/holdout_access.log",
        )
    )
    return pd.DataFrame(rows)


def write_audit(paths: ProjectPaths, spec: StudySpec = PRIMARY) -> pd.DataFrame:
    """Run the audit and write the table and the evidence page."""
    table = run_audit(paths, spec)
    table.to_csv(paths.tables / "holdout_integrity.csv", index=False)
    lines = ["| Check | Result | Value | Evidence |", "| --- | --- | --- | --- |"]
    lines += [
        f"| {r.check} | {r.result} | {r.value} | `{r.evidence}` |" for r in table.itertuples()
    ]
    failed = int((table["result"] == "fail").sum())
    text = f"""# Held out partition integrity

Written by `python -m antenatal audit-holdout` on {datetime.now(UTC).isoformat(timespec="seconds")}.
The supervisor's one absolute rule is that the held out records never reach training
(decision D7). Each check below reads identifiers, predictor values or stored outputs
only; none reads a held out outcome, fits a model or scores the held out records.

{chr(10).join(lines)}

{len(table) - failed} of {len(table)} checks passed.

What the checks mean. The first three show the split itself is clean: the file is the
sealed one, no record and no registration group is on both sides. The guard check shows
that a held out record offered to any model fit is refused. The stored prediction checks
show that no saved cross validation output ever scored a held out record. The reference
check shows that the served model's caseload was built from development predictions only.
The duplicate check looks for held out records that copy a development record value for
value, which would let a model recognise them. The last check counts evaluations of the
held out records: more than one would mean the held out records had been used to choose.
"""
    target = paths.root / "docs" / "evidence" / "holdout_integrity.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
    return table
