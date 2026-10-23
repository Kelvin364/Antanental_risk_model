"""``python -m antenatal run-experiments-v2``: run Stage 2 and write every table it produces.

The experiments, references and selection rule come from ``configs/experiment_plan.yaml``
(amendment 1 included), which was committed before this command first ran.
"""

from __future__ import annotations

import json

import pandas as pd

from antenatal.artefact.artefact import FittedPipelineArtefact
from antenatal.config import PRIMARY, StudySpec
from antenatal.evaluation.candidates import (
    candidate_table,
    net_benefit_table,
    operating_points,
    selection,
)
from antenatal.evaluation.interpretation import coefficients, permutation_table
from antenatal.experiments_v2 import ENSEMBLE, compare, planned, reused, run_all
from antenatal.paths import ProjectPaths
from antenatal.study import load_context

REFERENCES = [(m, s) for m in ("logistic_l2", "gradient_boosting") for s in ("A", "B", "C")]
BENCHMARK = [("baseline_prevalence", "A")]


def candidate_keys() -> list[tuple[str, str]]:
    """References, benchmark, every new run, the reused run and the ensemble, without repeats."""
    keys = REFERENCES + BENCHMARK + [p.experiment.key for p in planned() + reused()]
    return list(dict.fromkeys(keys + [(ENSEMBLE, "B")]))


def _inputs(log: pd.DataFrame, fold_metrics: pd.DataFrame) -> dict[tuple[str, str], int]:
    counts = fold_metrics.groupby(["model", "feature_set"])["n_features"].max().to_dict()
    counts.update({(r.model, r.feature_set): r.n_features for r in log.itertuples()})
    counts[(ENSEMBLE, "B")] = counts[("logistic_l2", "B")]
    counts[("logistic_l2_no_indicator", "C")] = counts[("logistic_l2", "C")]
    return counts


def _missing_data(candidates: pd.DataFrame, paths: ProjectPaths) -> pd.DataFrame:
    """Experiment 2.6 in one table: the new rows beside the existing imputation results."""
    keep = candidates[
        candidates["model"].isin(["logistic_l2", "logistic_l2_no_indicator", "gradient_boosting"])
        & (candidates["feature_set"] == "C")
    ]
    rows = keep[["model", "feature_set", "pr_auc", "pr_auc_low", "pr_auc_high"]].assign(
        source="outputs/tables/candidates_v2.csv"
    )
    pooled = pd.read_csv(paths.tables / "multiple_imputation.csv").assign(
        source="outputs/tables/multiple_imputation.csv"
    )
    return pd.concat([rows, pooled], ignore_index=True)


def run(paths: ProjectPaths, spec: StudySpec = PRIMARY) -> dict[str, object]:
    """Run every experiment once and write the Stage 2 tables."""
    results, log = run_all(paths, spec)
    tables = paths.tables
    log.to_csv(tables / "experiments_v2_runs.csv", index=False)
    compare(results, spec).to_csv(tables / "experiments_v2.csv", index=False)
    keys = candidate_keys()
    candidates = candidate_table(results, keys, _inputs(log, results.fold_metrics), spec)
    candidates.to_csv(tables / "candidates_v2.csv", index=False)
    chosen = selection(candidates)
    (tables / "selection_v2.json").write_text(json.dumps(chosen, indent=2) + "\n")
    operating_points(results, keys).to_csv(tables / "operating_points_v2.csv", index=False)
    net_benefit_table(results, keys).to_csv(tables / "net_benefit_v2.csv", index=False)
    _missing_data(candidates, paths).to_csv(tables / "missing_data_v2.csv", index=False)
    context = load_context(paths, spec)
    artefact = FittedPipelineArtefact.load(paths.model, verify=True)
    coefficients(artefact, context.development, spec).to_csv(
        tables / "coefficients_v2.csv", index=False
    )
    permutation_table(context, spec).to_csv(tables / "permutation_importance_v2.csv", index=False)
    return chosen
