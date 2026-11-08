"""Protocol Sections 6 and 7: measures, paired group bootstrap, selection and decision curves."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from scoring import calibration_slope, interval, resamples  # noqa: E402

OUT = HERE / "outputs"
SEED, RESAMPLES = 20261109, 2000
SERVED = ("l2_logistic", "F0")
TARGETS = {"roc_auc": 0.80, "specificity": 0.90, "cases_found": 90, "sensitivity": 90 / 165}
DRAW_KEYS = ("roc_auc", "pr_auc", "calibration_slope", "t90_sensitivity", "t90_specificity",
             "t54_sensitivity", "t54_specificity")  # fmt: skip


def calibration_intercept(y: np.ndarray, p: np.ndarray) -> float:
    """Calibration in the large: the offset a in logit P(y) = a + logit(p), by Newton steps."""
    z = np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))
    a = 0.0
    for _ in range(50):
        q = 1 / (1 + np.exp(-(a + z)))
        a += (y - q).sum() / max((q * (1 - q)).sum(), 1e-12)
    return float(a)


def flags(y, f, prefix):
    tp, fp = float((f * y).sum()), float((f * (1 - y)).sum())
    fn, tn = float(y.sum()) - tp, float((1 - y).sum()) - fp
    return {
        f"{prefix}_cases_found": tp, f"{prefix}_false_alarms": fp,
        f"{prefix}_cases_missed": fn, f"{prefix}_correct_clear": tn,
        f"{prefix}_sensitivity": tp / (tp + fn), f"{prefix}_specificity": tn / (tn + fp),
        f"{prefix}_ppv": tp / max(tp + fp, 1e-9), f"{prefix}_npv": tn / max(tn + fn, 1e-9),
    }  # fmt: skip


def sensitivity_at_specificity(y, p, specificity=0.90) -> float:
    """Descriptive best case: the cut off is placed using these same outcomes."""
    return float((p[y == 1] > np.quantile(p[y == 0], specificity)).mean())


def measures(y, part: pd.DataFrame, slopes: bool = True) -> dict[str, float]:
    p = part["p"].to_numpy()
    out = {"roc_auc": roc_auc_score(y, p), "pr_auc": average_precision_score(y, p)}
    if slopes:
        out |= {"calibration_slope": calibration_slope(y, p)}
    out |= flags(y, part["flag_t90"].to_numpy(), "t90")
    out |= flags(y, part["flag_t54"].to_numpy(), "t54")
    return out


def pooled(predictions: pd.DataFrame, outcome: pd.Series) -> dict[tuple, pd.DataFrame]:
    columns = ["p", "flag_t90", "flag_t54", "train_auc", "honest_train_auc"]
    grouped = predictions.groupby(["model", "set", "record_id"])[columns].mean()
    out = {}
    for key, part in grouped.groupby(level=[0, 1]):
        part = part.droplevel([0, 1]).loc[outcome.index]
        out[key] = part
    return out


def point(key, part, y) -> dict:
    p = part["p"].to_numpy()
    row = {"model": key[0], "set": key[1]} | measures(y, part)
    row |= {
        "base_rate": float(y.mean()), "brier": brier_score_loss(y, p),
        "calibration_intercept": calibration_intercept(y, p),
        "best_case_sensitivity_at_90_specificity": sensitivity_at_specificity(y, p),
        "train_auc": part["train_auc"].mean(), "honest_train_auc": part["honest_train_auc"].mean(),
    }  # fmt: skip
    return row


def draws(part, y, groups) -> pd.DataFrame:
    rows = []
    for picks in resamples(groups, RESAMPLES, SEED):
        if 0 < y[picks].sum() < len(picks):
            m = measures(y[picks], part.iloc[picks])
            rows.append({k: m[k] for k in DRAW_KEYS})
        else:
            rows.append({k: np.nan for k in DRAW_KEYS})
    return pd.DataFrame(rows)


def with_intervals(rows, all_draws) -> pd.DataFrame:
    table = pd.DataFrame(rows)
    for k in DRAW_KEYS:
        bounds = [interval(all_draws[(r["model"], r["set"])][k].tolist()) for r in rows]
        table[f"{k}_low"], table[f"{k}_high"], table[f"{k}_se"] = zip(*bounds, strict=True)
    return table


def comparisons(table, all_draws) -> pd.DataFrame:
    base, rows = all_draws[SERVED], []
    for key, d in all_draws.items():
        for k in ("roc_auc", "pr_auc", "t90_sensitivity", "t54_specificity"):
            diff = (d[k] - base[k]).dropna().to_numpy()
            low, high, _ = interval(diff.tolist())
            share = min((diff <= 0).mean(), (diff >= 0).mean())
            est = (
                table.set_index(["model", "set"]).loc[key, k]
                - table.set_index(["model", "set"]).loc[SERVED, k]
            )
            rows.append({"model": key[0], "set": key[1], "measure": k, "difference": est,
                         "low": low, "high": high, "p_value": min(1.0, 2 * share)})  # fmt: skip
    return pd.DataFrame(rows)


def select(table: pd.DataFrame) -> pd.Series:
    """Protocol Section 7: average precision, then calibration, then fewer inputs, then linear."""
    best = table.loc[table["pr_auc"].idxmax()]
    near = table[table["pr_auc"] >= best["pr_auc"] - best["pr_auc_se"]].copy()
    near["slope_gap"] = (near["calibration_slope"] - 1).abs()
    near["size"] = near["set"].map({"F0": 0, "F1": 1, "F2": 2})
    linear = ("l2_logistic", "lasso", "elastic_net", "spline_gam", "weighted_l2",
              "multiple_imputation")  # fmt: skip
    near["tree"] = (~near["model"].isin(linear)).astype(int)
    return near.sort_values(["slope_gap", "size", "tree"]).iloc[0]


def decision_curve(parts: dict, y: np.ndarray) -> pd.DataFrame:
    rows, n = [], len(y)
    for pt in np.round(np.arange(0.02, 0.201, 0.01), 2):
        odds = pt / (1 - pt)
        rows.append({"threshold": pt, "option": "treat all",
                     "net_benefit": y.mean() - (1 - y.mean()) * odds})  # fmt: skip
        rows.append({"threshold": pt, "option": "treat none", "net_benefit": 0.0})
        for name, part in parts.items():
            f = part["p"].to_numpy() >= pt
            tp, fp = (f & (y == 1)).sum(), (f & (y == 0)).sum()
            rows.append({"threshold": pt, "option": name, "net_benefit": tp / n - fp / n * odds})
    return pd.DataFrame(rows)


def targets(row: pd.Series) -> dict:
    checks = {}
    for prefix in ("t90", "t54"):
        checks[prefix] = {
            "roc_auc": [row["roc_auc"], row["roc_auc_low"]],
            "specificity": [row[f"{prefix}_specificity"], row[f"{prefix}_specificity_low"]],
            "sensitivity": [row[f"{prefix}_sensitivity"], row[f"{prefix}_sensitivity_low"]],
            "cases_found": row[f"{prefix}_cases_found"],
        }
        est = checks[prefix]
        checks[prefix]["all_met"] = bool(
            est["roc_auc"][0] >= 0.80 and est["specificity"][0] >= 0.90
            and est["cases_found"] >= 90
        )  # fmt: skip
    return checks


def main() -> None:
    import predictors

    data = predictors.build()
    outcome = pd.Series(data["y"], index=data["ids"])
    parts = pooled(pd.read_parquet(OUT / "nested_predictions.parquet"), outcome)
    y, groups = outcome.to_numpy(), data["groups"]
    rows = [point(k, part, y) for k, part in parts.items()]
    computed = Parallel(n_jobs=-1)(delayed(draws)(part, y, groups) for part in parts.values())
    all_draws = dict(zip(parts.keys(), computed, strict=True))
    table = with_intervals(rows, all_draws).sort_values("pr_auc", ascending=False)
    table.to_csv(OUT / "results.csv", index=False)
    comparisons(table, all_draws).to_csv(OUT / "comparisons.csv", index=False)
    chosen = select(table)
    top_roc = table.loc[table["roc_auc"].idxmax()]
    curves = {"served": parts[SERVED], "selected": parts[(chosen["model"], chosen["set"])],
              "highest ROC AUC": parts[(top_roc["model"], top_roc["set"])]}  # fmt: skip
    decision_curve(curves, y).to_csv(OUT / "decision_curve.csv", index=False)
    record = {"selected": [chosen["model"], chosen["set"]],
              "highest_roc_auc": [top_roc["model"], top_roc["set"]],
              "targets_selected": targets(chosen), "targets_highest_roc": targets(top_roc),
              "any_model_meets_all_targets": bool(any(
                  targets(r)[t]["all_met"] for _, r in table.iterrows() for t in ("t90", "t54")
              ))}  # fmt: skip
    (OUT / "selection.json").write_text(json.dumps(record, indent=1, default=float))
    print(json.dumps(record, indent=1, default=float))


if __name__ == "__main__":
    main()
