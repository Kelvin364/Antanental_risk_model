"""Protocol Section 8: are the targets possible with these records? Run after evaluate.py."""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import predictors
import run_targets as rt
import zoo
from joblib import Parallel, delayed
from scipy.stats import norm
from sklearn.metrics import average_precision_score, roc_auc_score

OUT = Path(__file__).resolve().parent / "outputs"
FRACTIONS = (0.25, 0.5, 0.75, 1.0)
VISIT_TWO = re.compile(r"(_v2$|^d_|_per_week$|^bmi$|^map_v2|^pulse_pressure|^anaemia$"
                       r"|^raised_bp$|^low_bmi$)")  # fmt: skip


def geometry(served_auc: float, prevalence_cases: int = 165, others: int = 2961) -> dict:
    sens, spec = 90 / 165, 0.90
    d_target = norm.ppf(sens) + norm.ppf(spec)
    d_served = np.sqrt(2) * norm.ppf(served_auc)
    return {
        "minimum_auc_of_any_curve_through_target": 0.5 * (1 - spec) * sens + spec * (sens + 1) / 2,
        "binormal_auc_through_target": float(norm.cdf(d_target / np.sqrt(2))),
        "binormal_sensitivity_at_90_specificity_for_served_auc": float(
            norm.cdf(d_served - norm.ppf(spec))
        ),
        "ppv_at_target": 90 / (90 + (1 - spec) * others),
        "false_alarms_at_target": (1 - spec) * others,
    }


def subsample(train, groups, fraction, seed):
    if fraction == 1.0:
        return train
    unique = np.unique(groups[train])
    keep = set(np.random.default_rng(seed).choice(unique, int(fraction * len(unique)), False))
    return train[np.isin(groups[train], list(keep))]


def learning_curve(data, models) -> pd.DataFrame:
    splits = rt.grouped(data["y"], data["groups"], rt.FOLDS, zoo.SEED)
    jobs = [
        (name, set_name, fraction, fold, subsample(tr, data["groups"], fraction, fold), te)
        for name, set_name in models
        for fraction in FRACTIONS
        for fold, (tr, te) in enumerate(splits)
    ]
    done = Parallel(n_jobs=-1)(
        delayed(rt.fit_one)(data, n, s, 0, f, tr, te) for n, s, _, f, tr, te in jobs
    )
    rows = []
    for (_, _, fraction, *_), frame in zip(jobs, done, strict=True):
        rows.append(frame.assign(fraction=fraction))
    pooled = pd.concat(rows)
    y = pd.Series(data["y"], index=data["ids"])
    out = []
    for (name, set_name, fraction), part in pooled.groupby(["model", "set", "fraction"]):
        p = part.set_index("record_id")["p"].loc[y.index]
        out.append({"model": name, "set": set_name, "fraction": fraction,
                    "roc_auc": roc_auc_score(y, p), "pr_auc": average_precision_score(y, p),
                    "train_auc": part["train_auc"].mean()})  # fmt: skip
    return pd.DataFrame(out)


def single_predictor_screen(data) -> pd.DataFrame:
    """Each wide input alone, in sample, so optimistic: descriptive only."""
    x, y, rows = data["F2"], data["y"], []
    for column in x.columns:
        values = x[column]
        if column.startswith("cat_"):
            codes = values.fillna("missing")
            rate = pd.Series(y, index=x.index).groupby(codes).transform("mean")
            score, known = rate.to_numpy(), np.ones(len(y), bool)
        else:
            known = values.notna().to_numpy()
            score = values.to_numpy(float)
        if known.sum() > 50 and len(np.unique(score[known])) > 1 and y[known].sum() > 0:
            auc = roc_auc_score(y[known], score[known])
            rows.append({"input": column, "known": int(known.sum()), "auc": max(auc, 1 - auc)})
    return pd.DataFrame(rows).sort_values("auc", ascending=False)


def timing(data, name, set_name) -> dict:
    columns = [c for c in data[set_name].columns if not VISIT_TWO.search(c)]
    data = dict(data, V1=data[set_name][columns])
    splits = [(r, f, tr, te) for r in range(rt.REPEATS)
              for f, (tr, te) in enumerate(rt.grouped(data["y"], data["groups"], rt.FOLDS,
                                                      zoo.SEED + r))]  # fmt: skip
    done = Parallel(n_jobs=-1)(delayed(rt.fit_one)(data, name, "V1", *s) for s in splits)
    y = pd.Series(data["y"], index=data["ids"])
    p = pd.concat(done).groupby("record_id")["p"].mean().loc[y.index]
    return {"visit_one_inputs": len(columns), "visit_one_roc_auc": roc_auc_score(y, p),
            "visit_one_pr_auc": average_precision_score(y, p)}  # fmt: skip


def by_week(data, name, set_name) -> pd.DataFrame:
    predictions = pd.read_parquet(OUT / "nested_predictions.parquet")
    part = predictions[(predictions["model"] == name) & (predictions["set"] == set_name)]
    p = part.groupby("record_id")["p"].mean().loc[data["ids"]].to_numpy()
    week, y, rows = data["ga_v2"], data["y"], []
    for label, low, high in (("up to 20", 0, 20), ("21 to 24", 20, 24), ("25 to 28", 24, 28)):
        keep = (week > low) & (week <= high)
        rows.append(
            {
                "visit_two_week": label,
                "records": int(keep.sum()),
                "cases": int(y[keep].sum()),
                "roc_auc": roc_auc_score(y[keep], p[keep]),
            }
        )
    return pd.DataFrame(rows)


def data_quality(data) -> dict:
    raw = pd.read_csv(predictors.ROOT / "data/maternal_dataset_csv.csv", dtype=str)
    n = {c: pd.to_numeric(raw[c], errors="coerce") for c in raw.columns}
    births = (
        n["number_of_prior_pregnancies_with_live_births"]
        + n["number_of_prior_pregnancies_with_stillbirths"]
    )
    served = predictors.fusion_frames.load().served
    preterm = served["preterm_labour"] == 1
    lbw = served["lbw"] == 1
    return {
        "births_exceed_prior_deliveries": float((births > n["number_of_prior_deliveries"]).mean()),
        "living_children_exceed_prior_deliveries": float(
            (n["number_of_living_children_and_birth_weight"] > n["number_of_prior_deliveries"])
            .mean()
        ),
        "stillbirth_count_distribution": n["number_of_prior_pregnancies_with_stillbirths"]
        .value_counts().sort_index().head(6).to_dict(),
        "cases_with_recorded_preterm_birth": int((preterm & lbw).sum()),
        "share_of_cases_preterm": float(preterm[lbw].mean()),
        "share_of_others_preterm": float(preterm[~lbw].mean()),
    }  # fmt: skip


def main() -> None:
    data = predictors.build()
    zoo.GROUPS.update(dict(zip(data["ids"], data["groups"], strict=True)))
    selection = json.loads((OUT / "selection.json").read_text())
    name, set_name = selection["selected"]
    results = pd.read_csv(OUT / "results.csv").set_index(["model", "set"])
    record = {"geometry": geometry(results.loc[("l2_logistic", "F0"), "roc_auc"])}
    record["timing"] = timing(data, name, set_name)
    record["data_quality"] = data_quality(data)
    by_week(data, name, set_name).to_csv(OUT / "roc_by_visit_two_week.csv", index=False)
    single_predictor_screen(data).to_csv(OUT / "single_predictor_screen.csv", index=False)
    models = sorted({(name, set_name), ("l2_logistic", "F0")})
    learning_curve(data, models).to_csv(OUT / "learning_curve.csv", index=False)
    (OUT / "ceiling.json").write_text(json.dumps(record, indent=1, default=float))
    print(json.dumps(record, indent=1, default=float))


if __name__ == "__main__":
    main()
