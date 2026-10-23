"""Stage 2 candidates: their metrics, operating points, and the Stage 4 selection rule.

The rule is read as written in ``configs/experiment_plan.yaml`` before any experiment
ran. A candidate replaces artefact 1.0.0 (L2 logistic regression on set C) only if
(a) its average precision beats the artefact's by more than the detectable difference
of that paired comparison with an interval excluding zero, its calibration slope
interval contains 1, and its Brier score is not clearly worse; among those passing,
(b) the simpler wins: fewer inputs, then linear over tree, then no recalibration, then
no weighting. If none passes, (c) the artefact stays.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from antenatal.config import PRIMARY, StudySpec
from antenatal.evaluation.bootstrap import GroupBootstrap
from antenatal.evaluation.metrics import (
    AveragePrecision,
    Brier,
    CalibrationIntercept,
    CalibrationSlope,
    RocAuc,
    net_benefit,
    net_benefit_treat_all,
)
from antenatal.evaluation.nested_cv import CVResults
from antenatal.evaluation.power import detectable_difference
from antenatal.models.factory import MODEL_SPECS

ARTEFACT = ("logistic_l2", "C")
SINGLE = (AveragePrecision(), RocAuc(), Brier(), CalibrationSlope(), CalibrationIntercept())
BUDGETS = (0.10, 0.20, 0.30)
NET_BENEFIT = np.round(np.arange(0.03, 0.121, 0.01), 2)


def _family_rank(model: str) -> tuple[int, int, int]:
    spec = MODEL_SPECS.get(model)
    tree = 1 if (spec is None or spec.family == "tree") else 0
    recalibrated = int(bool(spec and spec.calibration))
    weighted = int(bool(spec and spec.params.get("class_weight")))
    return tree, recalibrated, weighted


def candidate_table(results: CVResults, keys, inputs: dict, spec: StudySpec = PRIMARY):
    """One row per candidate: metrics with intervals, the comparison with the artefact, the rule."""
    y, boot = results.y, GroupBootstrap(results.groups, spec.bootstrap_resamples, spec.seed)
    reference = results.averaged(*ARTEFACT)
    rows = []
    for model, feature_set in keys:
        p = results.averaged(model, feature_set)
        row = {
            "model": model,
            "feature_set": feature_set,
            "inputs": inputs.get((model, feature_set)),
        }
        for metric in SINGLE:
            interval = boot.single(y, p, metric)
            row[metric.name] = interval.estimate
            row[f"{metric.name}_low"], row[f"{metric.name}_high"] = interval.low, interval.high
        ap = boot.paired_difference(y, p, reference, AveragePrecision())
        brier = boot.paired_difference(y, p, reference, Brier())
        row.update(
            ap_vs_artefact=ap.estimate,
            ap_vs_artefact_low=ap.low,
            ap_vs_artefact_high=ap.high,
            detectable_difference=detectable_difference(ap.se),
            brier_vs_artefact=brier.estimate,
            brier_vs_artefact_low=brier.low,
        )
        rows.append(row)
    return apply_rule(pd.DataFrame(rows))


def apply_rule(table: pd.DataFrame) -> pd.DataFrame:
    """Mark which candidates pass part (a) and rank the passers by part (b)."""
    is_artefact = (table["model"] == ARTEFACT[0]) & (table["feature_set"] == ARTEFACT[1])
    table["passes_rule"] = (
        ~is_artefact
        & (table["ap_vs_artefact"] > table["detectable_difference"])
        & (table["ap_vs_artefact_low"] > 0)
        & (table["calibration_slope_low"] <= 1)
        & (table["calibration_slope_high"] >= 1)
        & (table["brier_vs_artefact_low"] <= 0)
    )
    ranks = table["model"].map(_family_rank)
    table["tree"] = [r[0] for r in ranks]
    table["recalibrated"] = [r[1] for r in ranks]
    table["weighted"] = [r[2] for r in ranks]
    return table


def selection(table: pd.DataFrame) -> dict[str, object]:
    """The outcome of the selection rule."""
    passing = table[table["passes_rule"]].sort_values(
        ["inputs", "tree", "recalibrated", "weighted", "pr_auc"],
        ascending=[True, True, True, True, False],
    )
    if passing.empty:
        return {
            "outcome": "c",
            "chosen": "logistic_l2 on C, artefact 1.0.0 stays",
            "candidates_passing": 0,
        }
    best = passing.iloc[0]
    return {
        "outcome": "b",
        "chosen": f"{best['model']} on {best['feature_set']}",
        "candidates_passing": len(passing),
    }


def _counts(y: np.ndarray, flagged: np.ndarray) -> dict[str, float]:
    tp, fp = int((flagged & (y == 1)).sum()), int((flagged & (y == 0)).sum())
    fn, tn = int((~flagged & (y == 1)).sum()), int((~flagged & (y == 0)).sum())
    ratio = lambda a, b: a / b if b else float("nan")  # noqa: E731
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "sensitivity": ratio(tp, tp + fn),
        "specificity": ratio(tn, tn + fp),
        "ppv": ratio(tp, tp + fp),
        "npv": ratio(tn, tn + fn),
        "f1": ratio(2 * tp, 2 * tp + fp + fn),
    }


def operating_points(results: CVResults, keys) -> pd.DataFrame:
    """Each candidate at the 10, 20 and 30 percent budgets and at the prevalence threshold."""
    y, prevalence = results.y, float(results.y.mean())
    rows = []
    for model, feature_set in keys:
        p = results.averaged(model, feature_set)
        order = np.argsort(-p, kind="stable")
        for budget in BUDGETS:
            flagged = np.zeros(len(p), dtype=bool)
            flagged[order[: int(np.ceil(budget * len(p)))]] = True
            rows.append(
                {
                    "model": model,
                    "feature_set": feature_set,
                    "operating_point": f"top {round(budget * 100)} percent",
                    **_counts(y, flagged),
                }
            )
        rows.append(
            {
                "model": model,
                "feature_set": feature_set,
                "operating_point": f"probability at least {prevalence:.4f}",
                **_counts(y, p >= prevalence),
            }
        )
    development = results.development
    rule = ((development["sbp_v2"] >= 140) | (development["dbp_v2"] >= 90)).to_numpy()
    rows.append(
        {
            "model": "clinical rule B3",
            "feature_set": "visit two",
            "operating_point": "140/90 or above",
            **_counts(y, rule),
        }
    )
    return pd.DataFrame(rows)


def net_benefit_table(results: CVResults, keys) -> pd.DataFrame:
    """Net benefit of each candidate from 0.03 to 0.12, beside acting for everyone."""
    y = results.y
    table = pd.DataFrame(
        {"threshold": NET_BENEFIT, "act for everyone": net_benefit_treat_all(y, NET_BENEFIT)}
    )
    for model, feature_set in keys:
        table[f"{model} on {feature_set}"] = net_benefit(
            y, results.averaged(model, feature_set), NET_BENEFIT
        )
    return table
