"""Guideline version 2, Stage 2: the prespecified experiments on development records only.

Every experiment is listed in ``configs/experiment_plan.yaml`` (with amendment 1)
and was written there before this module first ran. Each runs through
``NestedCVRunner`` with the sealed partition's ``TrainingGuard``, on the same sealed
folds and seed as the study, and is compared with its prespecified reference by a
paired group bootstrap. ``python -m antenatal run-experiments-v2`` writes:

* ``outputs/oof_experiments_v2.parquet``: out of fold predictions of every new run.
* ``outputs/tables/experiments_v2.csv``: every comparison with its interval,
  detectable difference, bootstrap p value and Holm adjusted p value.
* ``outputs/tables/experiments_v2_runs.csv``: runtime, folds, convergence warnings and
  the parameters chosen in each fold, per experiment.
* the candidate, operating point, selection and interpretation tables of
  ``evaluation.candidates`` and ``evaluation.interpretation``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
import pandas as pd

from antenatal.config import PRIMARY, StudySpec
from antenatal.evaluation.comparisons import Comparison, ComparisonRunner
from antenatal.evaluation.nested_cv import CVResults, Experiment, NestedCVRunner
from antenatal.features.extras import extra_values
from antenatal.features.sets import SetA, SetAPlus, SetB, SetBExtras, SetBWithout, SetC
from antenatal.paths import ProjectPaths
from antenatal.study import load_context, load_results

OOF_V2 = "oof_experiments_v2.parquet"
ENSEMBLE = "average_logistic_gbt"
LR, GB = "logistic_l2", "gradient_boosting"
VISIT_TWO = ("sbp", "dbp", "weight", "ga", "pulse", "hb")


@dataclass(frozen=True)
class Planned:
    """One prespecified run with the reference it is compared against."""

    plan_id: str
    experiment: Experiment
    reference: tuple[str, str]


def planned() -> list[Planned]:
    """Every new run of Stage 2, in plan order."""
    a, b, c = SetA(), SetB(), SetC()
    runs = [Planned("2.1a", Experiment("logistic_elastic_net", s), (LR, s.name)) for s in (a, b, c)]
    runs += [
        Planned("2.1b", Experiment("gradient_boosting_search", s), (GB, s.name)) for s in (a, b, c)
    ]
    for s in (b, c):
        runs += [
            Planned("2.2", Experiment("logistic_l2_weighted", s), (LR, s.name)),
            Planned("2.2", Experiment("logistic_l2_weighted_platt", s), (LR, s.name)),
            Planned("2.2", Experiment("gradient_boosting_weighted", s), (GB, s.name)),
            Planned("2.2", Experiment("gradient_boosting_weighted_platt", s), (GB, s.name)),
        ]
    runs += [Planned("2.3", Experiment(LR, SetAPlus(m)), (LR, "A")) for m in VISIT_TWO]
    runs.append(Planned("2.3", Experiment(LR, SetBWithout("hb")), (LR, "B")))
    runs.append(Planned("2.4", Experiment("logistic_l2_splines", b), (LR, "B")))
    for model, reference in (("logistic_l2", LR), ("gradient_boosting", GB)):
        for method in ("platt", "isotonic"):
            runs.append(Planned("2.5", Experiment(f"{model}_{method}", c), (reference, "C")))
    extras = SetBExtras()
    runs += [Planned("2.10", Experiment(m, extras), (m, "B")) for m in (LR, GB)]
    return runs


def reused() -> list[Planned]:
    """Runs whose identical configuration already exists in ``oof_extensions.parquet``."""
    return [Planned("2.3 and 2.6", Experiment("logistic_l2_no_indicator", SetC()), (LR, "C"))]


def _ensemble(oof: pd.DataFrame) -> pd.DataFrame:
    """Experiment 2.9: the mean of the logistic and boosted probabilities on set B, per fold."""
    keys = ["record_id", "repeat", "fold"]
    lr = oof[(oof["model"] == LR) & (oof["feature_set"] == "B")].set_index(keys)["probability"]
    gb = oof[(oof["model"] == GB) & (oof["feature_set"] == "B")].set_index(keys)["probability"]
    mean = ((lr + gb.reindex(lr.index)) / 2).rename("probability").reset_index()
    return mean.assign(model=ENSEMBLE, feature_set="B")[
        ["record_id", "model", "feature_set", "repeat", "fold", "probability"]
    ]


def _run_log(planned_run: Planned, metrics: pd.DataFrame, seconds: float) -> dict[str, object]:
    model, feature_set = planned_run.experiment.key
    rows = metrics[(metrics["model"] == model) & (metrics["feature_set"] == feature_set)]
    return {
        "plan_id": planned_run.plan_id,
        "model": model,
        "feature_set": feature_set,
        "reference": f"{planned_run.reference[0]} on {planned_run.reference[1]}",
        "folds": len(rows),
        "repeats": rows["repeat"].nunique(),
        "status": "complete" if rows["repeat"].nunique() == 10 else "reduced",
        "runtime_seconds": round(seconds, 1),
        "convergence_warnings": int(rows["convergence_warnings"].sum()),
        "n_features": int(rows["n_features"].max()),
        "selected_parameters": " ; ".join(rows["params"].astype(str)),
    }


def run_all(paths: ProjectPaths, spec: StudySpec = PRIMARY) -> tuple[CVResults, pd.DataFrame]:
    """Run every new experiment once; return all predictions merged and the run log."""
    context = load_context(paths, spec)
    development = context.development.merge(extra_values(context.raw, spec), on="record_id")
    runner = NestedCVRunner(context.partition.guard(), spec)
    oof_parts, logs = [], []
    for planned_run in planned():
        started = time.time()
        result = runner.run(development, context.folds, [planned_run.experiment])
        oof_parts.append(result.oof)
        logs.append(_run_log(planned_run, result.fold_metrics, time.time() - started))
        print(f"{planned_run.plan_id} {planned_run.experiment.key} done", flush=True)
    primary = load_results(paths, context)
    extensions = pd.read_parquet(paths.outputs / "oof_extensions.parquet")
    oof = pd.concat([primary.oof, extensions, *oof_parts], ignore_index=True)
    oof = pd.concat([oof, _ensemble(primary.oof)], ignore_index=True)
    pd.concat([*oof_parts, _ensemble(primary.oof)]).to_parquet(paths.outputs / OOF_V2, index=False)
    return CVResults(primary.development, oof, primary.fold_metrics), pd.DataFrame(logs)


def comparisons() -> list[Comparison]:
    """Each run against its reference, the tuned primary and secondary tests, and the ensemble."""
    rows = [
        Comparison(
            f"{p.plan_id}: {p.experiment.key[0]} on {p.experiment.key[1]}",
            p.experiment.key,
            p.reference,
            "pr_auc",
            "exploratory",
        )
        for p in planned() + reused()
    ]
    rows.append(
        Comparison(
            "2.9: average of logistic and boosting on B",
            (ENSEMBLE, "B"),
            (LR, "B"),
            "pr_auc",
            "exploratory",
        )
    )
    for model in ("logistic_elastic_net", "gradient_boosting_search"):
        rows.append(
            Comparison(
                f"tuned primary: {model}, C over B",
                (model, "C"),
                (model, "B"),
                "pr_auc",
                "primary, tuned sensitivity",
            )
        )
        rows.append(
            Comparison(
                f"tuned secondary: {model}, B over A",
                (model, "B"),
                (model, "A"),
                "roc_auc",
                "secondary, tuned sensitivity",
            )
        )
    return rows


def holm(p_values: pd.Series) -> pd.Series:
    """Holm step down adjusted p values."""
    order = np.argsort(p_values.to_numpy())
    m, adjusted, running = len(p_values), np.empty(len(p_values)), 0.0
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p_values.iloc[index]))
        adjusted[index] = running
    return pd.Series(adjusted, index=p_values.index)


def compare(results: CVResults, spec: StudySpec = PRIMARY) -> pd.DataFrame:
    """Every comparison; Holm adjustment over the exploratory average precision family."""
    table = ComparisonRunner(results, spec).run(comparisons(), analysis="Stage 2")
    family = table["role"] == "exploratory"
    table["p_holm"] = np.nan
    table.loc[family, "p_holm"] = holm(table.loc[family, "p_value"])
    return table
