"""Protocol Sections 5 to 7: estimates, paired comparisons, the decision and attendance.

Run after run_nested.py: ``python lbw_detection_track/sequential/evaluate.py``.
Writes outputs/estimates.csv, comparisons.csv, decision.json, attendance.csv and
baseline_reproduction.json.
"""

from __future__ import annotations

import json
import warnings

import _paths  # noqa: F401  (import path to the fusion and track code)
import frames as frames_module
import numpy as np
import pandas as pd
import strategy_measures as sm
from _paths import OUT, ROOT, TRACK
from rules import PRIMARY, TARGETS
from scoring import interval, resamples

SEED, RESAMPLES = 20261111, 2000
DIFFERENCES = ("sensitivity", "specificity", "cases_found", "false_alarms")


def comparison_list() -> list[tuple[str, str, str, str, str]]:
    """Protocol Section 7, in order: role, population, new, against, measure."""
    rows = [
        ("primary", "all", f"seq_{PRIMARY}", "flag_base", "sensitivity"),
        ("primary", "all", f"seq_{PRIMARY}", f"match_{PRIMARY}", "sensitivity"),
    ]
    for k in TARGETS:
        role = "secondary" if k != PRIMARY else "descriptive"
        rows += [(role, "all", f"seq_{k}", "flag_base", m) for m in DIFFERENCES]
        rows += [(role, "all", f"seq_{k}", f"match_{k}", m) for m in DIFFERENCES]
        rows += [("secondary", "all", f"upd_{k}", f"seq_{k}", "sensitivity")]
    rows += [("descriptive", "all", "seq_75", "flag_base", m) for m in DIFFERENCES]
    for population in ("cleared", "reassessed"):
        rows += [("secondary", population, s, "p1", "roc_auc") for s in ("p2", "pu")]
    return [r for r in rows if r[0] != "descriptive" or r[4] != "sensitivity"]


def bootstrap(frame: pd.DataFrame, groups: np.ndarray) -> pd.DataFrame:
    """Paired resamples of whole registration groups; every strategy sees the same records."""
    rows = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for picks in resamples(groups, RESAMPLES, SEED):
            sample = frame.iloc[picks]
            cleared = sample[sample["cleared"]]
            if 0 < cleared["lbw"].sum() < len(cleared):
                rows.append(sm.measure_all(sample))
    return pd.DataFrame(rows)


def estimates(point: dict, draws: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for key, value in point.items():
        low, high, se = interval(draws[key].tolist())
        rows.append(dict(zip(("population", "strategy", "measure"), key, strict=True)))
        rows[-1] |= {"estimate": value, "low": low, "high": high, "se": se}
    return pd.DataFrame(rows)


def comparisons(point: dict, draws: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for role, population, new, old, measure in comparison_list():
        a, b = (population, new, measure), (population, old, measure)
        diff = (draws[a] - draws[b]).dropna().to_numpy()
        low, high, se = interval(diff.tolist())
        share = min((diff <= 0).mean(), (diff >= 0).mean())
        rows.append(
            {
                "role": role, "population": population, "strategy": new, "against": old,
                "measure": measure, "difference": point[a] - point[b], "low": low,
                "high": high, "se": se, "p_value": min(1.0, 2 * share), "resamples": len(diff),
            }
        )  # fmt: skip
    return pd.DataFrame(rows)


def decision(point: dict, table: pd.DataFrame) -> dict:
    """Protocol Section 7: all four conditions at the primary target."""
    seq, base = ("all", f"seq_{PRIMARY}"), ("all", "flag_base")
    first = table[(table["role"] == "primary") & (table["against"] == "flag_base")].iloc[0]
    second = table[(table["role"] == "primary") & (table["against"] != "flag_base")].iloc[0]
    ratio = point[(*seq, "false_alarms_per_extra_case")]
    ceiling = point[(*base, "false_alarms_per_case_found")]
    drop = point[(*base, "specificity")] - point[(*seq, "specificity")]
    conditions = {
        "1_gain_over_baseline_interval_above_zero": bool(first["low"] > 0),
        "2_gain_over_matched_baseline_interval_above_zero": bool(second["low"] > 0),
        "3_false_alarms_per_extra_case_within_baseline_ratio": bool(ratio <= ceiling),
        "4_specificity_drop_at_most_5_points": bool(drop <= 0.05),
    }
    return {
        "target": PRIMARY,
        "conditions": conditions,
        "late_model_adds_useful_information": all(conditions.values()),
        "false_alarms_per_extra_case": ratio,
        "baseline_false_alarms_per_case_found": ceiling,
        "specificity_drop": drop,
    }


def attendance(frame: pd.DataFrame) -> pd.DataFrame:
    """Who could be reassessed at all, by recorded preterm birth and baseline flag."""
    missed = frame["flag_base"] < 0.5
    rows = []
    for seen in (True, False):
        for preterm in (True, False):
            part = frame[(frame["reassessed"] == seen) & (frame["preterm"] == preterm)]
            y, cut = part["lbw"] == 1, missed[part.index]
            rows.append({
                "reassessed": seen, "recorded_preterm": preterm, "records": len(part),
                "cases": int(y.sum()), "cases_missed_by_baseline": int((y & cut).sum()),
            })  # fmt: skip
    return pd.DataFrame(rows)


def _frozen_rule() -> dict:
    frozen = json.loads((ROOT / "webapp/model/classification.json").read_text())["threshold"]
    stored = pd.read_csv(TRACK / "fusion/outputs/reference_check.csv").iloc[0]
    return {"frozen_threshold": frozen} | stored.drop("option").to_dict()


def baseline_reproduction(point: dict) -> dict:
    """The baseline as recorded by the main study, the fusion rebuild and this rebuild."""
    table = pd.read_csv(ROOT / "outputs/tables/model_performance.csv")
    served = table[(table["model"] == "logistic_l2") & (table["feature_set"] == "C")]
    held = pd.read_csv(ROOT / "outputs/tables/holdout_result.csv")
    held = held[(held["model"] == "C") & (held["metric"] == "roc_auc")].iloc[0]
    late_test = pd.read_csv(TRACK / "outputs/test_results.csv").set_index("set").loc["B"]
    return {
        "main_study_development": served.set_index("metric")[
            ["value", "ci_low", "ci_high"]
        ].T.to_dict(),
        "stored_out_of_fold_at_frozen_threshold": _frozen_rule(),
        "held_out_single_evaluation_roc_auc": held[
            ["estimate", "ci_low", "ci_high", "n"]
        ].to_dict(),
        "this_rebuild": {m: point[("all", "flag_base", m)] for m in DIFFERENCES}
        | {"roc_auc": point[("all", "p1", "roc_auc")]},
        "late_model_track_test_set_roc_auc": late_test[
            ["roc_auc", "roc_auc_low", "roc_auc_high"]
        ].to_dict(),
    }


def main() -> None:
    served = frames_module.load().served
    frame = sm.pooled(pd.read_parquet(OUT / "nested_predictions.parquet"), served)
    point = sm.measure_all(frame)
    draws = bootstrap(frame, served.loc[frame.index, "group_key_hash"].to_numpy())
    estimates(point, draws).to_csv(OUT / "estimates.csv", index=False)
    table = comparisons(point, draws)
    table.to_csv(OUT / "comparisons.csv", index=False)
    attendance(frame).to_csv(OUT / "attendance.csv", index=False)
    record = decision(point, table) | {"bootstrap_resamples_used": len(draws)}
    (OUT / "decision.json").write_text(json.dumps(record, indent=1) + "\n")
    reproduction = baseline_reproduction(point)
    text = json.dumps(reproduction, indent=1, default=float)
    (OUT / "baseline_reproduction.json").write_text(text + "\n")
    print(table.round(4).to_string(), json.dumps(record, indent=1), sep="\n")


if __name__ == "__main__":
    main()
