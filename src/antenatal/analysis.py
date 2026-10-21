"""The ``run-analysis`` command: every development result, table and figure.

No step here reads the held out partition. Every table is written under
``outputs/tables`` and every figure under ``outputs/figures``, and the run
manifest records a checksum for each.
"""

from __future__ import annotations

import time

import pandas as pd

from antenatal.audit.missingness import missingness_table
from antenatal.config import PRIMARY, StudySpec
from antenatal.evaluation.calibration import calibration_table
from antenatal.evaluation.comparisons import ComparisonRunner, primary_comparisons
from antenatal.evaluation.decision_curve import decision_curve_table
from antenatal.evaluation.metrics import score_all
from antenatal.evaluation.nested_cv import CVResults, NestedCVRunner
from antenatal.evaluation.sensitivity import SensitivityRunner
from antenatal.features.screen import AvailabilityScreen
from antenatal.models.factory import PRIMARY_MODELS
from antenatal.paths import ProjectPaths
from antenatal.reporting import figures, result_figures
from antenatal.reporting.manifest import write_manifest
from antenatal.study import OOF_FILE, StudyContext, clinical_rule, experiments, load_context

SETS = ("A", "B", "C")


def summary_by_experiment(results: CVResults) -> pd.DataFrame:
    """Every metric on the averaged out of fold predictions of each experiment."""
    rows = []
    for (model, feature_set), _ in results.oof.groupby(["model", "feature_set"]):
        p = results.averaged(model, feature_set)
        rows.append({"model": model, "feature_set": feature_set, **score_all(results.y, p)})
    folds = results.fold_metrics.groupby(["model", "feature_set"])
    spread = folds[["pr_auc", "roc_auc"]].std().add_suffix("_fold_sd").reset_index()
    return pd.DataFrame(rows).merge(spread, on=["model", "feature_set"])


def write_tables(paths: ProjectPaths, context: StudyContext, results: CVResults, spec: StudySpec):
    """Write every result table and return those the figures need."""
    tables = paths.tables
    development = context.development
    results.oof.to_parquet(paths.outputs / OOF_FILE, index=False)
    results.fold_metrics.to_csv(tables / "cv_fold_metrics.csv", index=False)
    screen = AvailabilityScreen(spec).fit(development).to_frame()
    screen.to_csv(tables / "availability_screen.csv", index=False)
    missing = missingness_table(development)
    missing.to_csv(tables / "missingness.csv", index=False)
    runner = ComparisonRunner(results, spec)
    comparisons = runner.run([c for m in PRIMARY_MODELS for c in primary_comparisons(m)])
    comparisons.to_csv(tables / "feature_set_comparisons.csv", index=False)
    keys = sorted(
        set(map(tuple, results.oof[["model", "feature_set"]].drop_duplicates().to_numpy()))
    )
    performance = runner.performance(keys)
    performance.to_csv(tables / "model_performance.csv", index=False)
    summary_by_experiment(results).to_csv(tables / "summary_by_experiment.csv", index=False)
    power_columns = [
        "model",
        "comparison",
        "metric",
        "role",
        "difference",
        "bootstrap_se",
        "detectable_difference",
    ]
    comparisons.loc[comparisons["role"] != "descriptive", power_columns].to_csv(
        tables / "detectable_difference.csv", index=False
    )
    clinical_rule(development).to_csv(tables / "clinical_rule_b3.csv", index=False)
    return {
        "screen": screen,
        "missing": missing,
        "comparisons": comparisons,
        "performance": performance,
    }


def curves(paths: ProjectPaths, results: CVResults) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    """Calibration and decision curve tables for the logistic model on A, B and C."""
    predictions = {s: results.averaged("logistic_l2", s) for s in SETS}
    calibration = {s: calibration_table(results.y, p) for s, p in predictions.items()}
    pd.concat([t.assign(feature_set=s) for s, t in calibration.items()]).to_csv(
        paths.tables / "calibration_curves.csv", index=False
    )
    decision = decision_curve_table(results.y, {f"Set {s}": p for s, p in predictions.items()})
    decision.to_csv(paths.tables / "decision_curve.csv", index=False)
    return calibration, decision


def draw(paths: ProjectPaths, context: StudyContext, tables: dict, results: CVResults) -> None:
    """Write every figure from the tables already computed."""
    out = paths.figures
    development = context.development
    n, events = len(development), int(development["lbw"].sum())
    calibration, decision = curves(paths, results)
    figures.cohort_flow(context.cohort.flow_table(), out)
    figures.outcome_prevalence(development, out)
    figures.measurement_distributions(development, out)
    figures.missingness(tables["missing"], n, events, out)
    figures.availability_screen(tables["screen"], n, events, out)
    result_figures.model_comparison(tables["performance"], events / n, out)
    result_figures.feature_set_differences(tables["comparisons"], out)
    result_figures.calibration(calibration, n, events, out)
    result_figures.decision_curve(decision, n, events, out)
    result_figures.detectable_difference(tables["comparisons"], out)


def run_analysis(paths: ProjectPaths, spec: StudySpec = PRIMARY) -> None:
    """Run the nested cross validation, the comparisons, the sensitivity analyses and figures."""
    started = time.time()
    context = load_context(paths, spec)
    results = NestedCVRunner(spec).run(context.development, context.folds, experiments())
    tables = write_tables(paths, context, results, spec)
    draw(paths, context, tables, results)
    sensitivity = SensitivityRunner(context.raw, context.partition, spec).run_all(
        context.development
    )
    sensitivity.to_csv(paths.tables / "sensitivity_analyses.csv", index=False)
    result_figures.sensitivity(sensitivity, paths.figures)
    write_manifest(paths, spec, {"analysis_seconds": round(time.time() - started, 1)})
    primary = tables["comparisons"]
    print(primary[primary["role"] != "descriptive"].round(4).to_string(index=False))
