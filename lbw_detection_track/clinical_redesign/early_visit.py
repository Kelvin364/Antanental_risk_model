"""Deliverable 4 support: is the ROC AUC of 0.730 for second visits by 20 weeks real?

Development records only, stored out of fold scores only, no model fitted. Checks the
finding across all 37 configurations, its case mix, a group bootstrap difference, the
same question using visit one week (known earlier), and how many pregnancies a landmark
at each week could reach in the track's development pool.

Writes outputs/early_visit_by_config.csv, early_visit_case_mix.csv, early_visit_summary.json
and landmark_reach.csv.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
from common import (
    OUT,
    ROOT,
    SELECTED,
    STUDY,
    TRACK,
    VISITS,
    auc_between,
    bounds,
    development,
    group_draws,
    number,
    predictor_fields,
    stored_scores,
)
from outcome_study import case_types

BANDS = (("up to 20", 0, 20), ("21 to 24", 20, 24), ("25 to 28", 24, 28))
VISIT_ONE_BANDS = (
    ("up to 12", 0, 12),
    ("13 to 16", 12, 16),
    ("17 to 20", 16, 20),
    ("21 to 27", 20, 27),
)
LANDMARKS = (16, 20, 24, 28, 32)


def _band(values: np.ndarray, low: float, high: float) -> np.ndarray:
    return (values > low) & (values <= high)


def by_config(frame: pd.DataFrame) -> pd.DataFrame:
    y, ga = frame["lbw"].to_numpy() == 1, frame["ga_v2"].to_numpy()
    stored = pd.read_parquet(STUDY / "nested_predictions.parquet")
    means = stored.groupby(["model", "set", "record_id"])["p"].mean()
    rows = []
    for (model, set_name), part in means.groupby(level=[0, 1]):
        p = part.droplevel([0, 1]).loc[frame.index].to_numpy()
        row = {"model": model, "set": set_name}
        for label, low, high in BANDS:
            keep = _band(ga, low, high)
            row[label] = auc_between(p, y & keep, ~y & keep)
        rows.append(row)
    table = pd.DataFrame(rows)
    table["early_band_highest"] = table[[b[0] for b in BANDS]].idxmax(axis=1) == "up to 20"
    return table


def case_mix(frame: pd.DataFrame, p: np.ndarray) -> pd.DataFrame:
    types, ga = case_types(frame), frame["ga_v2"].to_numpy()
    y = frame["lbw"].to_numpy() == 1
    rows = []
    for label, low, high in BANDS:
        keep = _band(ga, low, high)
        rows.append({
            "visit_two_week": label, "records": int(keep.sum()), "cases": int((y & keep).sum()),
            "cases_preterm": int((types["lbw_preterm"] & keep).sum()),
            "case_rate": float(y[keep].mean()),
            "median_visit_one_week": float(np.median(frame["ga_v1"].to_numpy()[keep])),
            "median_age": float(np.nanmedian(frame["age"].to_numpy(dtype=float)[keep])),
            "share_first_pregnancy": float((frame["gravidity"].to_numpy()[keep] == 1).mean()),
            "hb_v2_missing": float(np.isnan(frame["hb_v2"].to_numpy()[keep]).mean()),
            "auc_lbw_preterm": auc_between(p, types["lbw_preterm"] & keep, ~y & keep),
            "auc_lbw_not_preterm": auc_between(p, types["lbw_not_preterm"] & keep, ~y & keep),
            "mean_score_cases": float(p[y & keep].mean()),
            "mean_score_others": float(p[~y & keep].mean()),
        })  # fmt: skip
    return pd.DataFrame(rows)


def difference(frame: pd.DataFrame, p: np.ndarray) -> dict:
    y, ga = frame["lbw"].to_numpy() == 1, frame["ga_v2"].to_numpy()
    early = ga <= 20

    def gap(i: np.ndarray) -> float:
        yi, pi, ei = y[i], p[i], early[i]
        return auc_between(pi, yi & ei, ~yi & ei) - auc_between(pi, yi & ~ei, ~yi & ~ei)

    draws = group_draws(frame["group_key_hash"].to_numpy(), gap)
    low, high = bounds(draws)
    share = float(np.mean(np.array(draws) <= 0))
    return {"early_minus_later": gap(np.arange(len(y))), "low": low, "high": high,
            "share_of_draws_at_or_below_zero": share}  # fmt: skip


def visit_one(frame: pd.DataFrame, p: np.ndarray) -> list[dict]:
    y, ga = frame["lbw"].to_numpy() == 1, frame["ga_v1"].to_numpy()
    rows = []
    for label, low, high in VISIT_ONE_BANDS:
        keep = _band(ga, low, high)
        rows.append(
            {
                "visit_one_week": label,
                "records": int(keep.sum()),
                "cases": int((y & keep).sum()),
                "auc": auc_between(p, y & keep, ~y & keep),
            }
        )
    return rows


def landmark_reach() -> pd.DataFrame:
    """Track development pool: who has one, or two, usable visits by each week."""
    ids = pd.read_csv(TRACK / "sealed" / "development_ids.csv")["record_id"].astype(int)
    manifest = pd.read_csv(ROOT / "outputs/cohort_manifest.csv", index_col="record_id")
    pool = manifest.loc[sorted(ids)]
    pool = pool[pool["eligible"]]
    weeks = predictor_fields([f"pregnant_week_number_v{v}" for v in VISITS]).loc[pool.index]
    weeks = weeks.apply(number)
    y = pool["lbw"].to_numpy() == 1
    rows = []
    for week in LANDMARKS:
        seen = (weeks <= week).sum(axis=1).to_numpy()
        for visits in (1, 2):
            keep = seen >= visits
            rows.append({"landmark_week": week, "visits_by_landmark": visits,
                         "records": int(keep.sum()), "cases": int((y & keep).sum()),
                         "share_of_pool_cases": float((y & keep).sum() / y.sum())})  # fmt: skip
    return pd.DataFrame(rows).assign(pool_records=len(pool), pool_cases=int(y.sum()))


def main() -> None:
    frame = development()
    p = stored_scores(*SELECTED, frame.index)["p"].to_numpy()
    OUT.mkdir(exist_ok=True)
    configs = by_config(frame)
    configs.to_csv(OUT / "early_visit_by_config.csv", index=False)
    mix = case_mix(frame, p)
    mix.to_csv(OUT / "early_visit_case_mix.csv", index=False)
    summary = {
        "configurations": len(configs),
        "early_band_highest_in": int(configs["early_band_highest"].sum()),
        "median_auc_by_band": {b[0]: float(configs[b[0]].median()) for b in BANDS},
        "selected_early_minus_later": difference(frame, p),
        "selected_by_visit_one_week": visit_one(frame, p),
    }
    (OUT / "early_visit_summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    reach = landmark_reach()
    reach.to_csv(OUT / "landmark_reach.csv", index=False)
    print(mix.round(3).T.to_string(), json.dumps(summary, indent=1), reach.to_string(), sep="\n")


if __name__ == "__main__":
    main()
