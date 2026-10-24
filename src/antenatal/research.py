"""Guideline version 2 Stage 3: the research questions answered from saved predictions.

``python -m antenatal research-results`` reads the stored out of fold predictions,
never fits a model and never touches the held out records. Every comparison is a
paired group bootstrap on the same development records, with a two sided bootstrap
p value. The prespecified primary and secondary comparisons are not adjusted; every
other tested row forms one exploratory family with a Holm adjustment. DeLong's test
is added beside each ROC AUC difference as descriptive only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from antenatal.config import PRIMARY, StudySpec
from antenatal.evaluation.bootstrap import GroupBootstrap
from antenatal.evaluation.comparisons import ComparisonRunner, primary_comparisons
from antenatal.evaluation.delong import delong_paired
from antenatal.evaluation.metrics import MetricStrategy
from antenatal.evaluation.missingness_signal import indicator_comparisons
from antenatal.evaluation.nested_cv import CVResults
from antenatal.evaluation.retrieval import BUDGETS, RetrievalAtBudget
from antenatal.experiments_v2 import holm
from antenatal.extensions import EXTENSION_OOF
from antenatal.paths import ProjectPaths
from antenatal.study import load_context, load_results

MODELS = ("logistic_l2", "gradient_boosting")
SERVED = ("logistic_l2", "C")
PRESPECIFIED = ("primary", "secondary")


@dataclass(frozen=True)
class ResearchQuestion:
    """One research question of the proposal, mapped to how it is answered."""

    number: int
    question: str
    endpoint: str
    population: str
    method: str
    null_hypothesis: str


QUESTIONS = (
    ResearchQuestion(
        1,
        "Do first visit values add predictive value beyond the second visit (set C over set B)?",
        "Average precision, the area under the precision recall curve",
        "Development records",
        "Paired group bootstrap of C minus B on pooled out of fold predictions",
        "The difference in average precision is zero",
    ),
    ResearchQuestion(
        2,
        "Do second visit values add discrimination beyond registration (set B over set A)?",
        "ROC AUC, the area under the receiver operating characteristic curve",
        "Development records",
        "Paired group bootstrap of B minus A; DeLong's test as descriptive",
        "The difference in ROC AUC is zero",
    ),
    ResearchQuestion(
        3,
        "What share of low birth weight births falls in the top 10, 20 and 30 percent "
        "of the served model's ranking, against ranking at random?",
        "Retrieval at each budget minus the budget itself",
        "Development records",
        "Group bootstrap of retrieval minus the random expectation",
        "The served ranking retrieves no more than random",
    ),
    ResearchQuestion(
        4,
        "Is missingness informative: do missingness indicators improve sets B and C?",
        "Average precision with indicators minus without",
        "Development records",
        "Paired group bootstrap on the same folds",
        "Indicators change average precision by zero",
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


def _question(label: str) -> str:
    if label.startswith("C over B ("):
        return "1"
    if label.startswith("B over A ("):
        return "2"
    return "4" if label.startswith("Indicators") else "supporting"


def _comparisons(results: CVResults, spec: StudySpec) -> pd.DataFrame:
    comparisons = [c for m in MODELS for c in primary_comparisons(m)] + indicator_comparisons()
    for c in comparisons:
        check_alignment(results, c.new)
        check_alignment(results, c.old)
    table = ComparisonRunner(results, spec).run(comparisons, analysis="Stage 3")
    table["question"] = [_question(c) for c in table["comparison"]]
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


def _retrieval(results: CVResults, spec: StudySpec) -> pd.DataFrame:
    check_alignment(results, SERVED)
    y, p = results.y, results.averaged(*SERVED)
    bootstrap = GroupBootstrap(results.groups, spec.bootstrap_resamples, spec.seed)
    rows = []
    for budget in BUDGETS:
        interval = bootstrap.single(y, p, RetrievalGain(budget))
        rows.append(
            {
                "analysis": "Stage 3",
                "model": SERVED[0],
                "comparison": f"Top {round(budget * 100)} percent, set C over random ranking",
                "metric": "retrieval_gain",
                "role": "exploratory",
                "new_value": interval.estimate + budget,
                "old_value": budget,
                "difference": interval.estimate,
                "ci_low": interval.low,
                "ci_high": interval.high,
                "bootstrap_se": interval.se,
                "excludes_zero": interval.excludes_zero,
                "p_value": interval.p_value,
                "n": len(y),
                "events": int(y.sum()),
                "question": "3",
            }
        )
    return pd.DataFrame(rows)


def results_table(paths: ProjectPaths, spec: StudySpec = PRIMARY) -> pd.DataFrame:
    """Every tested row of research questions 1 to 4, with its family and adjusted p value."""
    results = load_all(paths, spec)
    table = pd.concat([_comparisons(results, spec), _retrieval(results, spec)], ignore_index=True)
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
