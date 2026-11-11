"""Deliverable 3: is one combined low birth weight outcome limiting the models?

Development records only (3,126 with 165 cases). Splits the cases by recorded preterm birth,
checks the quality of the outcome fields, and re-reads the target study's stored out of
fold scores to see how well each kind of case is ranked. No model is fitted.

Writes outputs/outcome_decomposition.csv, outputs/outcome_quality.json and
outputs/discrimination_by_case_type.csv.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
from common import (
    CONFIGS,
    OUT,
    VISITS,
    auc_between,
    bounds,
    development,
    group_draws,
    number,
    predictor_fields,
    stored_scores,
)


def case_types(frame: pd.DataFrame) -> dict[str, np.ndarray]:
    lbw = frame["lbw"].to_numpy() == 1
    preterm = frame["preterm_labour"].to_numpy().astype(bool)
    return {
        "lbw_preterm": lbw & preterm,
        "lbw_not_preterm": lbw & ~preterm,
        "not_lbw_preterm": ~lbw & preterm,
        "not_lbw_not_preterm": ~lbw & ~preterm,
    }


def decomposition(frame: pd.DataFrame) -> pd.DataFrame:
    types = case_types(frame)
    weight = frame["birth_weight_kg"].to_numpy()
    term = frame["term_labour"].to_numpy().astype(bool)
    rows = []
    for name, mask in types.items():
        rows.append(
            {
                "group": name,
                "records": int(mask.sum()),
                "share_of_records": float(mask.mean()),
                "recorded_term_labour": int((mask & term).sum()),
                "median_birth_weight_kg": float(np.median(weight[mask])),
            }
        )
    return pd.DataFrame(rows)


def quality(frame: pd.DataFrame) -> dict:
    """Do the outcome fields agree with each other and with antenatal attendance?"""
    raw = predictor_fields(["preterm_labour_1", *[f"pregnant_week_number_v{v}" for v in VISITS]])
    raw = raw.loc[frame.index]
    last_week = raw[[f"pregnant_week_number_v{v}" for v in VISITS]].apply(number).max(axis=1)
    preterm = frame["preterm_labour"].astype(bool)
    term = frame["term_labour"].astype(bool)
    history = raw["preterm_labour_1"].str.strip().str.lower() == "yes"
    weight = frame["birth_weight_kg"]
    both = pd.crosstab(history, preterm)
    return {
        "preterm_and_term_both_recorded": int((preterm & term).sum()),
        "neither_preterm_nor_term_recorded": int((~preterm & ~term).sum()),
        "preterm_recorded_with_antenatal_visit_at_37_weeks_or_later": int(
            (preterm & (last_week >= 37)).sum()
        ),
        "preterm_recorded": int(preterm.sum()),
        "registration_preterm_field_by_outcome_preterm": {
            f"registration_{r}_outcome_{c}": int(both.loc[r, c])
            for r in both.index for c in both.columns
        },  # fmt: skip
        "birth_weight_on_whole_or_half_kg": float(((weight * 2) % 1 == 0).mean()),
        "birth_weight_on_tenth_kg": float(((weight * 10).round(6) % 1 == 0).mean()),
    }


def _pair(score, types, groups, cases: str, controls: str) -> dict:
    a, b = types[cases], types[controls]
    point = auc_between(score, a, b)
    draws = group_draws(groups, lambda i: auc_between(score[i], a[i], b[i]))
    low, high = bounds(draws)
    return {"auc": point, "low": low, "high": high, "draws": draws}


def discrimination(frame: pd.DataFrame) -> pd.DataFrame:
    types = case_types(frame)
    controls = types["not_lbw_preterm"] | types["not_lbw_not_preterm"]
    types = types | {
        "not_lbw": controls,
        "preterm_any": types["lbw_preterm"] | types["not_lbw_preterm"],
        "not_preterm": types["lbw_not_preterm"] | types["not_lbw_not_preterm"],
    }
    groups = frame["group_key_hash"].to_numpy()
    rows = []
    for model, set_name in CONFIGS:
        scores = stored_scores(model, set_name, frame.index)
        p, t90 = scores["p"].to_numpy(), scores["flag_t90"].to_numpy()
        early = _pair(p, types, groups, "lbw_preterm", "not_lbw")
        growth = _pair(p, types, groups, "lbw_not_preterm", "not_lbw")
        preterm = _pair(p, types, groups, "preterm_any", "not_preterm")
        gap = np.array(growth["draws"]) - np.array(early["draws"])
        low, high = bounds(gap.tolist())
        rows.append(
            {
                "model": model,
                "set": set_name,
                "auc_lbw_preterm_vs_not_lbw": early["auc"],
                "low_1": early["low"],
                "high_1": early["high"],
                "auc_lbw_not_preterm_vs_not_lbw": growth["auc"],
                "low_2": growth["low"],
                "high_2": growth["high"],
                "difference_2_minus_1": growth["auc"] - early["auc"],
                "diff_low": low,
                "diff_high": high,
                "auc_any_preterm_vs_not_preterm": preterm["auc"],
                "low_3": preterm["low"],
                "high_3": preterm["high"],
                "t90_flag_rate_lbw_preterm": t90[types["lbw_preterm"]].mean(),
                "t90_flag_rate_lbw_not_preterm": t90[types["lbw_not_preterm"]].mean(),
                "t90_flag_rate_not_lbw": t90[controls].mean(),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    frame = development()
    OUT.mkdir(exist_ok=True)
    table = decomposition(frame)
    table.to_csv(OUT / "outcome_decomposition.csv", index=False)
    checks = quality(frame)
    (OUT / "outcome_quality.json").write_text(json.dumps(checks, indent=1) + "\n")
    ranked = discrimination(frame)
    ranked.to_csv(OUT / "discrimination_by_case_type.csv", index=False)
    print(table.to_string(index=False), json.dumps(checks, indent=1), sep="\n")
    print(ranked.round(3).T.to_string())


if __name__ == "__main__":
    main()
