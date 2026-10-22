"""The ``draw-figures`` command: redraw every figure from the saved tables.

No model is fitted and no result is recomputed. The descriptive figures need
the development records, which are rebuilt from the verified data file and
the sealed partition; every other figure reads a table in ``outputs/tables``.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from antenatal.paths import ProjectPaths
from antenatal.reporting import extension_figures, figures, result_figures
from antenatal.study import load_context


def _table(paths: ProjectPaths, name: str) -> pd.DataFrame:
    return pd.read_csv(paths.tables / f"{name}.csv")


def _descriptive(paths: ProjectPaths) -> list[Path]:
    context = load_context(paths)
    development = context.development
    n, events = len(development), int(development["lbw"].sum())
    return [
        figures.cohort_flow(_table(paths, "cohort_flow"), paths.figures),
        figures.outcome_prevalence(development, paths.figures),
        figures.measurement_distributions(development, paths.figures),
        figures.missingness(_table(paths, "missingness"), n, events, paths.figures),
        figures.availability_screen(_table(paths, "availability_screen"), n, events, paths.figures),
    ]


def _results(paths: ProjectPaths) -> list[Path]:
    comparisons = _table(paths, "feature_set_comparisons")
    first = comparisons.iloc[0]
    n, events = int(first["n"]), int(first["events"])
    curves = _table(paths, "calibration_curves")
    calibration = {s: curves[curves["feature_set"] == s] for s in ("A", "B", "C")}
    out = paths.figures
    return [
        result_figures.model_comparison(_table(paths, "model_performance"), events / n, out),
        result_figures.feature_set_differences(comparisons, out),
        result_figures.calibration(calibration, n, events, out),
        result_figures.decision_curve(_table(paths, "decision_curve"), n, events, out),
        result_figures.detectable_difference(comparisons, out),
        result_figures.sensitivity(_table(paths, "sensitivity_analyses"), out),
    ]


def _extensions(paths: ProjectPaths) -> list[Path]:
    rates = _table(paths, "missingness_outcome_rates")
    n = int(rates["recorded_n"].iloc[0] + rates["missing_n"].iloc[0])
    events = int(rates["recorded_events"].iloc[0] + rates["missing_events"].iloc[0])
    out = paths.figures
    return [
        extension_figures.learning_curve(_table(paths, "learning_curve"), n, events, out),
        extension_figures.forest(
            _table(paths, "ablation"),
            "Set C minus set C without one visit one measurement",
            "fig13_ablation",
            out,
        ),
        extension_figures.forest(
            _table(paths, "parameterisation"),
            "Ways of entering the first visit",
            "fig14_parameterisation",
            out,
        ),
        extension_figures.missingness_rates(rates, n, events, out),
        extension_figures.retrieval(_table(paths, "retrieval_at_budget"), out),
    ]


def redraw_all(paths: ProjectPaths) -> list[Path]:
    """Redraw every figure and return their paths."""
    return _descriptive(paths) + _results(paths) + _extensions(paths)
