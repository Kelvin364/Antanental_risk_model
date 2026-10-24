"""Guideline version 2 Stage 3: the research questions answered from saved predictions.

``python -m antenatal research-results`` reads the stored out of fold predictions and
result tables, never fits a model and never touches the held out records. Every
comparison computed here is a paired group bootstrap on the same development records,
with a two sided bootstrap p value. The prespecified primary and secondary hypotheses
are not adjusted; every other tested row forms one exploratory family with a Holm
adjustment. DeLong's test is added beside each ROC AUC difference as descriptive only.
Sensitivity analyses on other cohorts are read from their saved tables, whose
predictions are not stored, so their p values use the normal approximation with the
saved bootstrap standard error.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import NormalDist

import numpy as np
import pandas as pd

from antenatal.config import PRIMARY, StudySpec
from antenatal.evaluation.bootstrap import GroupBootstrap
from antenatal.evaluation.comparisons import ComparisonRunner, primary_comparisons
from antenatal.evaluation.delong import delong_paired
from antenatal.evaluation.metrics import (
    Brier,
    CalibrationIntercept,
    CalibrationSlope,
    MetricStrategy,
)
from antenatal.evaluation.missingness_signal import indicator_comparisons
from antenatal.evaluation.nested_cv import CVResults
from antenatal.evaluation.power import detectable_difference
from antenatal.evaluation.retrieval import BUDGETS, RetrievalAtBudget
from antenatal.experiments_v2 import holm
from antenatal.extensions import EXTENSION_OOF
from antenatal.paths import ProjectPaths
from antenatal.study import load_context, load_results

MODELS = ("logistic_l2", "gradient_boosting")
SERVED = ("logistic_l2", "C")
PRESPECIFIED = ("primary", "secondary")
BOOTSTRAP_P = "paired group bootstrap"
NORMAL_P = "normal approximation with the saved bootstrap standard error"
# Saved sensitivity rows for question 4: (table, analysis or model, what it is sensitive to).
SAVED_SENSITIVITY = (
    ("sensitivity_analyses.csv", "S4", "missing measurements"),
    ("multiple_imputation.csv", "logistic_l2_iterative_pooled", "missing measurements"),
    ("sensitivity_analyses.csv", "GBT, uniform imputation", "missing measurements"),
    ("sensitivity_analyses.csv", "S3", "questionable outcome records"),
    ("sensitivity_analyses.csv", "S6", "questionable outcome records"),
    ("sensitivity_analyses.csv", "S1", "timing of the second visit"),
    ("sensitivity_analyses.csv", "S2", "timing of the second visit"),
    ("sensitivity_analyses.csv", "S5", "form of the visit one values"),
)


@dataclass(frozen=True)
class ResearchQuestion:
    """One research question of the proposal, quoted, and how it is answered."""

    number: int
    question: str
    endpoint: str
    method: str
    null_hypothesis: str


QUESTIONS = (
    ResearchQuestion(
        1,
        "Do measurements from the first antenatal visit improve prediction of recorded low "
        "birth weight beyond the second visit alone in the eligible cohort?",
        "Average precision of set C minus set B",
        "Paired group bootstrap, both model families; the prespecified primary hypothesis",
        "Adding first visit values changes average precision by zero",
    ),
    ResearchQuestion(
        2,
        "Does a learned model outperform constant prevalence prediction, and does adding the "
        "earlier visit improve both discrimination and calibration over the second visit "
        "features alone?",
        "Average precision of sets A, B and C minus the prevalence only model; ROC AUC, "
        "Brier score, calibration slope and intercept of set C minus set B",
        "Paired group bootstrap; DeLong's test beside each ROC AUC as descriptive",
        "Each difference is zero",
    ),
    ResearchQuestion(
        3,
        "Optionally, within fixed ranking budgets, what proportion of pregnancies "
        "subsequently recorded as low birth weight is retrieved by model ranking relative "
        "to ranking at random?",
        "Share of events in the top 10, 20 and 30 percent of the served ranking, minus the "
        "share random ranking retrieves",
        "Group bootstrap of retrieval minus the random expectation",
        "The served ranking retrieves no more than random",
    ),
    ResearchQuestion(
        4,
        "What sensitivity do the feature set comparisons show to missing measurements and "
        "to questionable outcome records?",
        "The primary comparison, C minus B average precision, under each sensitivity "
        "analysis, and missingness indicators added to sets B and C",
        "Paired group bootstrap; saved sensitivity analyses use the normal approximation",
        "Each difference is zero",
    ),
)


class RetrievalGain(MetricStrategy):
    """Retrieval at a budget minus the share a random ranking retrieves on average."""

    def __init__(self, budget: float) -> None:
        self._retrieval = RetrievalAtBudget(budget)
        self.budget = budget
        self.name = f"retrieval_gain_top_{round(budget * 100)}"

    def compute(self, y: np.ndarray, p: np.ndarray) -> float:
        return self._retrieval.compute(y, p) - self.budget


def check_alignment(results: CVResults, key: tuple[str, str]) -> None:
    """Refuse a paired test unless every development record has a prediction for ``key``."""
    rows = results.oof[(results.oof["model"] == key[0]) & (results.oof["feature_set"] == key[1])]
    expected = set(results.development["record_id"])
    if set(rows["record_id"]) != expected or np.isnan(results.averaged(*key)).any():
        raise ValueError(f"Predictions for {key} are not aligned with the development records")


def load_all(paths: ProjectPaths, spec: StudySpec = PRIMARY) -> CVResults:
    """The primary and extension out of fold predictions over the development records."""
    primary = load_results(paths, load_context(paths, spec))
    extensions = pd.read_parquet(paths.outputs / EXTENSION_OOF)
    oof = pd.concat([primary.oof, extensions], ignore_index=True)
    return CVResults(primary.development, oof, primary.fold_metrics)


def _question(label: str, metric: str) -> tuple[str, str | None]:
    """The question a comparison answers, and its role when that differs from the runner's."""
    if label.startswith("C over B ("):
        return ("1", None) if metric == "pr_auc" else ("2", "exploratory")
    if label.startswith("B over A ("):
        return "secondary hypothesis", None
    if "over B0" in label:
        return "2", None
    return ("4", None) if label.startswith("Indicators") else ("supporting", None)


def _comparisons(results: CVResults, spec: StudySpec) -> pd.DataFrame:
    comparisons = [c for m in MODELS for c in primary_comparisons(m)] + indicator_comparisons()
    for c in comparisons:
        check_alignment(results, c.new)
        check_alignment(results, c.old)
    table = ComparisonRunner(results, spec).run(comparisons, analysis="Stage 3")
    mapped = [_question(c, m) for c, m in zip(table["comparison"], table["metric"], strict=True)]
    table["question"] = [q for q, _ in mapped]
    table["role"] = [r or role for (_, r), role in zip(mapped, table["role"], strict=True)]
    # ComparisonRunner writes one row per metric in this order for each comparison.
    by_row = [c for c in comparisons for _ in ComparisonRunner.METRICS]
    table["delong_p_value"] = [
        (
            delong_paired(results.y, results.averaged(*c.new), results.averaged(*c.old)).p_value
            if metric == "roc_auc"
            else np.nan
        )
        for c, metric in zip(by_row, table["metric"], strict=True)
    ]
    return table


def _row(model, comparison, metric, role, question, interval, new, old, y) -> dict:
    return {
        "analysis": "Stage 3",
        "model": model,
        "comparison": comparison,
        "metric": metric,
        "role": role,
        "new_value": new,
        "old_value": old,
        "difference": interval.estimate,
        "ci_low": interval.low,
        "ci_high": interval.high,
        "bootstrap_se": interval.se,
        "detectable_difference": detectable_difference(interval.se),
        "excludes_zero": interval.excludes_zero,
        "p_value": interval.p_value,
        "n": len(y),
        "events": int(y.sum()),
        "question": question,
    }


def _calibration(results: CVResults, spec: StudySpec) -> pd.DataFrame:
    """Question 2: does set C improve calibration over set B? Brier is tested; the
    calibration slope and intercept are shown with intervals as descriptive."""
    bootstrap = GroupBootstrap(results.groups, spec.bootstrap_resamples, spec.seed)
    y, rows = results.y, []
    metrics = ((Brier(), "exploratory"), (CalibrationSlope(), "descriptive"))
    metrics += ((CalibrationIntercept(), "descriptive"),)
    for model in MODELS:
        p_new, p_old = results.averaged(model, "C"), results.averaged(model, "B")
        for metric, role in metrics:
            interval = bootstrap.paired_difference(y, p_new, p_old, metric)
            new, old = metric.compute(y, p_new), metric.compute(y, p_old)
            label = "C over B (first visit added)"
            rows.append(_row(model, label, metric.name, role, "2", interval, new, old, y))
    return pd.DataFrame(rows)


def _retrieval(results: CVResults, spec: StudySpec) -> pd.DataFrame:
    check_alignment(results, SERVED)
    y, p = results.y, results.averaged(*SERVED)
    bootstrap = GroupBootstrap(results.groups, spec.bootstrap_resamples, spec.seed)
    rows = []
    for budget in BUDGETS:
        interval = bootstrap.single(y, p, RetrievalGain(budget))
        label = f"Top {round(budget * 100)} percent, set C over random ranking"
        row = _row(SERVED[0], label, "retrieval_gain", "exploratory", "3", interval, 0, 0, y)
        rows.append(row | {"new_value": interval.estimate + budget, "old_value": budget})
    return pd.DataFrame(rows)


def _saved_sensitivity(paths: ProjectPaths) -> pd.DataFrame:
    """Question 4 rows read from the saved sensitivity tables, primary comparison only."""
    rows = []
    for file, key, sensitive_to in SAVED_SENSITIVITY:
        table = pd.read_csv(paths.tables / file)
        column = "model" if file == "multiple_imputation.csv" else "analysis"
        row = table[(table[column] == key) & (table["role"] == "primary")].iloc[0]
        z = abs(row["difference"]) / row["bootstrap_se"]
        label = row.get("specification", "Iterative imputation, five draws pooled")
        rows.append(
            row.to_dict()
            | {
                "analysis": key,
                "comparison": f"{label}: {row['comparison']}",
                "role": "exploratory",
                "p_value": 2 * (1 - NormalDist().cdf(z)),
                "p_method": NORMAL_P,
                "sensitive_to": sensitive_to,
                "question": "4",
            }
        )
    return pd.DataFrame(rows).drop(columns=["specification"], errors="ignore")


def results_table(paths: ProjectPaths, spec: StudySpec = PRIMARY) -> pd.DataFrame:
    """Every row of research questions 1 to 4, with its family and adjusted p value."""
    results = load_all(paths, spec)
    computed = pd.concat(
        [_comparisons(results, spec), _calibration(results, spec), _retrieval(results, spec)],
        ignore_index=True,
    ).assign(p_method=BOOTSTRAP_P)
    computed.loc[computed["question"] == "4", "sensitive_to"] = "missing measurements"
    table = pd.concat([computed, _saved_sensitivity(paths)], ignore_index=True)
    table["family"] = np.where(
        table["role"].isin(PRESPECIFIED),
        "prespecified, not adjusted",
        np.where(table["role"] == "descriptive", "descriptive, not tested", "exploratory, Holm"),
    )
    exploratory = table["family"] == "exploratory, Holm"
    table["p_holm"] = np.nan
    table.loc[exploratory, "p_holm"] = holm(table.loc[exploratory, "p_value"])
    return table


def questions_table() -> pd.DataFrame:
    """The research questions as a table."""
    return pd.DataFrame([asdict(q) for q in QUESTIONS])
