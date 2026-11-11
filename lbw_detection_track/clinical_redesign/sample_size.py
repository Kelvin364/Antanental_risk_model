"""Deliverable 6: how many pregnancies and events a stronger model would need.

Development: the three criteria of Riley et al. (BMJ 2020; 368: m441), small overfitting
(shrinkage 0.9), small optimism in Nagelkerke R squared (0.05) and a precise overall risk.
Validation: precision targets in the spirit of Riley et al. (Stat Med 2021; 40: 4230),
computed from closed forms and the anticipated linear predictor. Anticipated Cox Snell
R squared is obtained from an anticipated ROC AUC by simulating a binormal linear predictor.
Confirm final numbers with the pmsampsize and pmvalsampsize packages before any protocol
is registered.

Reads outputs/outcome_decomposition.csv (run outcome_study.py first) and the main study's
outputs/tables/cohort_flow.csv. Writes sample_size_development.csv,
sample_size_validation.csv and feasibility.json.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
from common import OUT, ROOT
from scipy.optimize import brentq
from scipy.stats import norm

Z = norm.ppf(0.975)
AUCS = (0.65, 0.70, 0.75, 0.80, 0.85)
PARAMETERS = (10, 20, 30)
COLLECTION_DAYS = (pd.Timestamp("2025-03-30") - pd.Timestamp("2024-05-20")).days  # data/README
SIM = 400_000


def prevalences() -> dict[str, float]:
    d = pd.read_csv(OUT / "outcome_decomposition.csv").set_index("group")["records"]
    total = d.sum()
    return {
        "low birth weight": (d["lbw_preterm"] + d["lbw_not_preterm"]) / total,
        "recorded preterm birth": (d["lbw_preterm"] + d["not_lbw_preterm"]) / total,
        "low birth weight without recorded preterm birth": d["lbw_not_preterm"] / total,
    }


def linear_predictor(auc: float, prevalence: float, seed: int = 20261111):
    """Binormal scores with the anticipated AUC, mapped to calibrated log odds."""
    rng = np.random.default_rng(seed)
    y = rng.random(SIM) < prevalence
    shift = np.sqrt(2) * norm.ppf(auc)
    score = rng.normal(0, 1, SIM) + shift * y
    log_ratio = shift * score - shift**2 / 2
    lp = np.log(prevalence / (1 - prevalence)) + log_ratio
    return y, lp


def _log_lik(y, lp) -> float:
    p = 1 / (1 + np.exp(-lp))
    return float(np.sum(np.where(y, np.log(p), np.log1p(-p))))


def r_squared(auc: float, prevalence: float) -> tuple[float, float]:
    """Anticipated Cox Snell R squared and its maximum for this prevalence."""
    y, lp = linear_predictor(auc, prevalence)
    phi = y.mean()
    null = len(y) * (phi * np.log(phi) + (1 - phi) * np.log(1 - phi))
    r2 = 1 - np.exp(2 * (null - _log_lik(y, lp)) / len(y))
    return float(r2), float(1 - np.exp(2 * null / len(y)))


def development(auc: float, prevalence: float, parameters: int) -> dict:
    r2, max_r2 = r_squared(auc, prevalence)
    shrink = 0.9
    n1 = parameters / ((shrink - 1) * np.log(1 - r2 / shrink))
    s2 = r2 / (r2 + 0.05 * max_r2)
    n2 = parameters / ((s2 - 1) * np.log(1 - r2 / s2))
    n3 = (Z / 0.05) ** 2 * prevalence * (1 - prevalence)
    n = int(np.ceil(max(n1, n2, n3)))
    return {"cox_snell_r2": r2, "n_shrinkage": n1, "n_optimism": n2, "n_overall_risk": n3,
            "required_records": n, "required_events": int(np.ceil(n * prevalence)),
            "events_per_parameter": n * prevalence / parameters}  # fmt: skip


def _auc_se(auc: float, cases: float, others: float) -> float:
    """Hanley and McNeil standard error of the ROC AUC."""
    q1, q2 = auc / (2 - auc), 2 * auc**2 / (1 + auc)
    var = auc * (1 - auc) + (cases - 1) * (q1 - auc**2) + (others - 1) * (q2 - auc**2)
    return float(np.sqrt(var / (cases * others)))


def validation(auc: float, prevalence: float) -> dict:
    y, lp = linear_predictor(auc, prevalence)
    p = 1 / (1 + np.exp(-lp))
    w = p * (1 - p)
    info = np.array([[w.mean(), (w * lp).mean()], [(w * lp).mean(), (w * lp**2).mean()]])
    slope_var = np.linalg.inv(info)[1, 1]
    se_width_02 = 0.2 / (2 * Z)
    need = {
        "calibration_slope_interval_width_0.2": slope_var / se_width_02**2,
        "observed_expected_within_10_percent": (1 - prevalence)
        / (prevalence * (np.log(1.1) / Z) ** 2),
        "roc_auc_interval_width_0.1": brentq(
            lambda n: 2 * Z * _auc_se(auc, n * prevalence, n * (1 - prevalence)) - 0.1, 50, 1e8
        ),
        "sensitivity_0.545_within_5_points": Z**2 * 0.545 * 0.455 / 0.05**2 / prevalence,
        "specificity_0.90_within_2_points": Z**2 * 0.9 * 0.1 / 0.02**2 / (1 - prevalence),
    }
    n = int(np.ceil(max(need.values())))
    return {k: int(np.ceil(v)) for k, v in need.items()} | {
        "required_records": n, "required_events": int(np.ceil(n * prevalence)),
        "driving_criterion": max(need, key=need.get),
    }  # fmt: skip


def feasibility(table_dev: pd.DataFrame, table_val: pd.DataFrame) -> dict:
    flow = pd.read_csv(ROOT / "outputs/tables/cohort_flow.csv").set_index("number")
    months = COLLECTION_DAYS / (365.25 / 12)
    usable = flow.loc[3]
    per_month = usable["remaining"] / months
    lbw = table_dev[table_dev["outcome"] == "low birth weight"]
    target = lbw[(lbw["anticipated_auc"] == 0.80) & (lbw["parameters"] == 20)].iloc[0]
    val = table_val[(table_val["outcome"] == "low birth weight")
                    & (table_val["anticipated_auc"] == 0.80)].iloc[0]  # fmt: skip
    return {
        "collection_months": months,
        "singleton_live_births_with_weight": int(usable["remaining"]),
        "lbw_events_among_them": int(usable["events_remaining"]),
        "records_per_month_all_five_districts": per_month,
        "lbw_events_per_month": usable["events_remaining"] / months,
        "development_records_for_auc_080_20_parameters": int(target["required_records"]),
        "months_at_current_yield_development": target["required_records"] / per_month,
        "validation_records_for_auc_080": int(val["required_records"]),
        "months_at_current_yield_validation": val["required_records"] / per_month,
    }


def main() -> None:
    dev_rows, val_rows = [], []
    for outcome, prevalence in prevalences().items():
        for auc in AUCS:
            base = {"outcome": outcome, "prevalence": prevalence, "anticipated_auc": auc}
            val_rows.append(base | validation(auc, prevalence))
            for parameters in PARAMETERS:
                dev_rows.append(base | {"parameters": parameters}
                                | development(auc, prevalence, parameters))  # fmt: skip
    dev, val = pd.DataFrame(dev_rows), pd.DataFrame(val_rows)
    dev.to_csv(OUT / "sample_size_development.csv", index=False)
    val.to_csv(OUT / "sample_size_validation.csv", index=False)
    plan = feasibility(dev, val)
    (OUT / "feasibility.json").write_text(json.dumps(plan, indent=1) + "\n")
    columns = ["outcome", "anticipated_auc", "parameters", "required_records", "required_events"]
    print(dev[columns].to_string(index=False), val.to_string(index=False), plan, sep="\n")


if __name__ == "__main__":
    main()
