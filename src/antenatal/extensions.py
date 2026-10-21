"""The ``run-extensions`` command: Stage 5 analyses on development records only.

Every analysis reuses the sealed outer folds and the primary out of fold
predictions, so each comparison is paired on the same pregnancies and the
same splits as the primary result. Nothing here reads the held out partition.
"""

from __future__ import annotations

import pandas as pd

from antenatal.config import PRIMARY, StudySpec
from antenatal.evaluation.bootstrap import GroupBootstrap
from antenatal.evaluation.comparisons import Comparison, ComparisonRunner
from antenatal.evaluation.learning_curve import LearningCurve, summarise
from antenatal.evaluation.metrics import CalibrationIntercept, CalibrationSlope
from antenatal.evaluation.missingness_signal import indicator_comparisons, outcome_by_recording
from antenatal.evaluation.nested_cv import CVResults, Experiment, NestedCVRunner
from antenatal.evaluation.retrieval import retrieval_table
from antenatal.evaluation.subgroups import subgroup_table
from antenatal.features.screen import AvailabilityScreen
from antenatal.features.sets import (
    PRIMARY_SETS,
    SetB,
    SetC,
    SetCChangeOnly,
    SetCRate,
    SetCWithChange,
    SetCWithout,
)
from antenatal.models.factory import ITERATIVE_MODELS
from antenatal.paths import ProjectPaths
from antenatal.reporting import extension_figures
from antenatal.study import StudyContext, load_context, load_results

LOGISTIC = "logistic_l2"
POOLED = "logistic_l2_iterative_pooled"
EXTENSION_OOF = "oof_extensions.parquet"
PARAMETERISATIONS = (SetCWithChange(), SetCChangeOnly(), SetCRate())


def extension_experiments(context: StudyContext) -> list[Experiment]:
    """Ablation, parameterisation, indicator and multiple imputation experiments."""
    passed = AvailabilityScreen().fit(context.development).passed
    out = [Experiment(LOGISTIC, SetCWithout(m)) for m in passed]
    out += [Experiment(LOGISTIC, s) for s in PARAMETERISATIONS]
    out += [Experiment("logistic_l2_no_indicator", s) for s in (SetB(), SetC())]
    out += [Experiment(m, s) for m in ITERATIVE_MODELS for s in (SetB(), SetC())]
    return out


def pool_imputations(oof: pd.DataFrame) -> pd.DataFrame:
    """Average the probabilities of the five imputations per record, repeat and set."""
    rows = oof[oof["model"].isin(ITERATIVE_MODELS)]
    keys = ["record_id", "feature_set", "repeat", "fold"]
    pooled = rows.groupby(keys, as_index=False)["probability"].mean().assign(model=POOLED)
    return pd.concat([oof, pooled], ignore_index=True)


def ablation(runner: ComparisonRunner, passed: tuple[str, ...]) -> pd.DataFrame:
    """Set C against set C without each visit one measurement."""
    comparisons = [
        Comparison(
            f"Visit one {m} kept",
            (LOGISTIC, "C"),
            (LOGISTIC, f"C_without_{m}"),
            "pr_auc",
            "extension",
        )
        for m in passed
    ]
    return runner.run(comparisons, analysis="Ablation")


def parameterisation(runner: ComparisonRunner) -> pd.DataFrame:
    """Each way of entering the first visit, against set B and against values only."""
    comparisons = []
    for feature_set in (SetC(), *PARAMETERISATIONS):
        comparisons.append(
            Comparison(
                f"{feature_set.name} over B",
                (LOGISTIC, feature_set.name),
                (LOGISTIC, "B"),
                "pr_auc",
                "extension",
            )
        )
    for feature_set in PARAMETERISATIONS:
        comparisons.append(
            Comparison(
                f"{feature_set.name} over C",
                (LOGISTIC, feature_set.name),
                (LOGISTIC, "C"),
                "pr_auc",
                "extension",
            )
        )
    return runner.run(comparisons, analysis="Parameterisation")


def gbt_native(runner: ComparisonRunner) -> pd.DataFrame:
    """Native handling against uniform imputation for the trees, and both models' tests."""
    comparisons = [
        Comparison(
            f"Native over uniform, set {s.name}",
            ("gradient_boosting", s.name),
            ("gradient_boosting_uniform", s.name),
            "pr_auc",
            "extension",
        )
        for s in PRIMARY_SETS
    ]
    for model in ("gradient_boosting", "gradient_boosting_uniform"):
        comparisons += [
            Comparison("C over B", (model, "C"), (model, "B"), "pr_auc", "primary"),
            Comparison("B over A", (model, "B"), (model, "A"), "roc_auc", "secondary"),
        ]
    return runner.run(comparisons, analysis="GBT missing value handling")


def multiple_imputation(runner: ComparisonRunner) -> pd.DataFrame:
    """The primary comparison under median imputation, pooled iterative imputation and each draw."""
    models = (LOGISTIC, POOLED, *ITERATIVE_MODELS)
    comparisons = [Comparison("C over B", (m, "C"), (m, "B"), "pr_auc", "primary") for m in models]
    return runner.run(comparisons, analysis="Multiple imputation")


def calibration_by_set(results: CVResults, spec: StudySpec) -> pd.DataFrame:
    """Calibration slope and intercept of sets A, B and C for both model families."""
    bootstrap = GroupBootstrap(results.groups, spec.bootstrap_resamples, spec.seed)
    rows = []
    for model in (LOGISTIC, "gradient_boosting"):
        for feature_set in ("A", "B", "C"):
            p = results.averaged(model, feature_set)
            row = {
                "model": model,
                "feature_set": feature_set,
                "n": len(p),
                "events": int(results.y.sum()),
            }
            for metric in (CalibrationSlope(), CalibrationIntercept()):
                interval = bootstrap.single(results.y, p, metric)
                row.update(
                    {
                        metric.name: interval.estimate,
                        f"{metric.name}_low": interval.low,
                        f"{metric.name}_high": interval.high,
                    }
                )
            rows.append(row)
    return pd.DataFrame(rows)


def run_primary_model_tables(paths: ProjectPaths, results: CVResults, spec: StudySpec) -> None:
    """Question 3 retrieval and Question 2 calibration tables from the primary predictions."""
    p = results.averaged(LOGISTIC, "C")
    table = retrieval_table(results.y, p, results.groups, spec, label=f"{LOGISTIC}, set C")
    table.to_csv(paths.tables / "retrieval_at_budget.csv", index=False)
    extension_figures.retrieval(table, paths.figures)
    calibration_by_set(results, spec).to_csv(paths.tables / "calibration_by_set.csv", index=False)


def run_learning_curve(paths: ProjectPaths, context: StudyContext, spec: StudySpec) -> None:
    """Learning curve table and figure for sets B and C."""
    experiments = [Experiment(LOGISTIC, SetB()), Experiment(LOGISTIC, SetC())]
    curve = LearningCurve(spec).run(context.development, context.folds, experiments)
    curve.to_csv(paths.tables / "learning_curve_by_repeat.csv", index=False)
    summary = summarise(curve)
    summary.to_csv(paths.tables / "learning_curve.csv", index=False)
    extension_figures.learning_curve(
        summary, len(context.development), _events(context), paths.figures
    )


def _events(context: StudyContext) -> int:
    return int(context.development["lbw"].sum())


def run_extensions(paths: ProjectPaths, spec: StudySpec = PRIMARY) -> None:
    """Every Stage 5 analysis, in the order agreed with the supervisor."""
    context = load_context(paths, spec)
    run_learning_curve(paths, context, spec)
    extra = NestedCVRunner(spec).run(
        context.development, context.folds, extension_experiments(context)
    )
    extra.oof.to_parquet(paths.outputs / EXTENSION_OOF, index=False)
    primary = load_results(paths, context)
    results = CVResults(
        primary.development,
        pool_imputations(pd.concat([primary.oof, extra.oof])),
        primary.fold_metrics,
    )
    runner = ComparisonRunner(results, spec)
    run_primary_model_tables(paths, primary, spec)
    n, events = len(context.development), _events(context)
    passed = AvailabilityScreen(spec).fit(context.development).passed
    tables = paths.tables
    table = ablation(runner, passed)
    table.to_csv(tables / "ablation.csv", index=False)
    extension_figures.forest(
        table,
        "Set C minus set C without one visit one measurement",
        "fig13_ablation",
        paths.figures,
    )
    table = parameterisation(runner)
    table.to_csv(tables / "parameterisation.csv", index=False)
    extension_figures.forest(
        table, "Ways of entering the first visit", "fig14_parameterisation", paths.figures
    )
    rates = outcome_by_recording(context.development)
    rates.to_csv(tables / "missingness_outcome_rates.csv", index=False)
    runner.run(indicator_comparisons(), analysis="Missingness indicators").to_csv(
        tables / "missingness_indicator_signal.csv", index=False
    )
    extension_figures.missingness_rates(rates, n, events, paths.figures)
    gbt_native(runner).to_csv(tables / "gbt_missing_value_handling.csv", index=False)
    multiple_imputation(runner).to_csv(tables / "multiple_imputation.csv", index=False)
    subgroup_table(results, spec).to_csv(tables / "subgroups.csv", index=False)
