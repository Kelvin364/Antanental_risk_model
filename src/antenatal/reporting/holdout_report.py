"""``python -m antenatal holdout-report``: the held out results and the proof of independence.

Writes ``docs/holdout_results.md`` from the tables the single held out evaluation wrote,
the access log, the integrity audits before and after the run, the development results
and git. It never reads the held out records and fits nothing; every number is read
from a file at generation time.
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime

import pandas as pd

from antenatal.paths import ProjectPaths

EVIDENCE = "docs/evidence/holdout_run"
TIMELINE = (
    ("Held out records sealed (their checksum)", "partitions/holdout.sha256", "first"),
    ("Served model (set C, 1.0.0) last changed", "webapp/model/lbw_model.joblib", "last"),
    ("Set B comparator frozen", "webapp/model/secondary_set_b/lbw_model.joblib", "last"),
    ("Label threshold fixed", "webapp/model/classification.json", "last"),
    ("Set A comparator frozen", "webapp/model/comparator_set_a/lbw_model.joblib", "last"),
    ("Integrity audit before the run committed", f"{EVIDENCE}/audit_before.txt", "first"),
)
NAMES = {
    "pr_auc": "Average precision",
    "roc_auc": "ROC AUC",
    "brier": "Brier score",
    "calibration_slope": "Calibration slope",
    "calibration_intercept": "Calibration intercept",
}


def _git(root, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True).stdout.strip()


def _table(frame: pd.DataFrame) -> str:
    head = "| " + " | ".join(frame.columns) + " |"
    rule = "| " + " | ".join("---" for _ in frame.columns) + " |"
    body = ["| " + " | ".join(str(v) for v in row) + " |" for row in frame.itertuples(index=False)]
    return "\n".join([head, rule, *body])


def _span(estimate: float, low: float, high: float) -> str:
    if pd.isna(low):
        return f"{estimate:.4f}"
    return f"{estimate:.4f} ({low:.4f} to {high:.4f})"


def _timeline(paths: ProjectPaths, log: list[str]) -> pd.DataFrame:
    rows = []
    for event, path, which in TIMELINE:
        history = _git(paths.root, "log", "--follow", "--format=%h %ci", "--", path).splitlines()
        commit = (history[-1] if which == "first" else history[0]) if history else "not in git"
        rows.append((event, f"`{path}`", commit))
    opened = next(line.split("\t")[0] for line in log if "\tOPENED\t" in line)
    rows.append(
        ("Held out outcomes read for the first time", "`partitions/holdout_access.log`", opened)
    )
    return pd.DataFrame(rows, columns=["Event", "File", "Commit and time"])


def _audit_counts(paths: ProjectPaths) -> tuple[int, int, int]:
    before = (paths.root / EVIDENCE / "audit_before.txt").read_text().splitlines()
    after = pd.read_csv(paths.tables / "holdout_integrity.csv")
    passed_before = sum(" pass " in line for line in before)
    return passed_before, int((after["result"] == "pass").sum()), len(after)


def _development(paths: ProjectPaths) -> dict[str, tuple[float, float, float]]:
    """The served model's development estimates with their intervals."""
    s = pd.read_csv(paths.tables / "summary_by_experiment.csv")
    s = s[(s["model"] == "logistic_l2") & (s["feature_set"] == "C")].iloc[0]
    c = pd.read_csv(paths.tables / "calibration_by_set.csv")
    c = c[(c["model"] == "logistic_l2") & (c["feature_set"] == "C")].iloc[0]
    rule = json.loads((paths.model / "classification.json").read_text())["performance"]
    out = {
        "pr_auc": (s["pr_auc"], s["pr_auc_low"], s["pr_auc_high"]),
        "roc_auc": (s["roc_auc"], s["roc_auc_low"], s["roc_auc_high"]),
        "brier": (s["brier"], float("nan"), float("nan")),
    }
    for kind in ("slope", "intercept"):
        key = f"calibration_{kind}"
        out[key] = (c[key], c[f"{key}_low"], c[f"{key}_high"])
    for kind, values in rule.items():
        out[kind] = (values["estimate"], values["low"], values["high"])
    return out


def _consistency(paths: ProjectPaths) -> pd.DataFrame:
    """Development against held out for the served model, measure by measure."""
    development = _development(paths)
    held = pd.read_csv(paths.tables / "holdout_result.csv")
    held = held[held["model"] == "C"].set_index("metric")
    labels = pd.read_csv(paths.tables / "holdout_classification.csv").set_index("measure")
    rows = []
    for key, (estimate, low, high) in development.items():
        source = held.loc[key] if key in held.index else labels.loc[key]
        h_estimate = source["estimate"]
        inside = "yes" if pd.isna(low) or low <= h_estimate <= high else "no"
        h_span = _span(h_estimate, source["ci_low"], source["ci_high"])
        rows.append(
            (
                NAMES.get(key, key.upper() if len(key) == 3 else key.capitalize()),
                _span(estimate, low, high),
                h_span,
                inside,
            )
        )
    columns = [
        "Measure",
        "Development (95% interval)",
        "Held out (95% interval)",
        "Held out estimate inside the development interval",
    ]
    return pd.DataFrame(rows, columns=columns)


def _comparisons(paths: ProjectPaths) -> pd.DataFrame:
    table = pd.read_csv(paths.tables / "holdout_comparisons.csv")
    return pd.DataFrame(
        {
            "Comparison": table["comparison"],
            "Measure": table["metric"].map(NAMES),
            "Role": table["role"],
            "Difference (95% interval)": [
                f"{d:+.4f} ({lo:+.4f} to {hi:+.4f})"
                for d, lo, hi in zip(
                    table["difference"], table["ci_low"], table["ci_high"], strict=True
                )
            ],
            "p": table["p_value"].map(lambda p: f"{p:.3f}"),
            "Detectable difference": table["detectable_difference"].map(lambda d: f"{d:.4f}"),
        }
    )


def _models(paths: ProjectPaths) -> pd.DataFrame:
    table = pd.read_csv(paths.tables / "holdout_result.csv")
    wide = {}
    for (model, metric), row in table.set_index(["model", "metric"]).iterrows():
        wide.setdefault(NAMES[metric], {})[f"Set {model}"] = _span(
            row["estimate"], row["ci_low"], row["ci_high"]
        )
    return pd.DataFrame(wide).T.reset_index(names="Measure")[["Measure", "Set C", "Set B", "Set A"]]


def _labels(paths: ProjectPaths) -> pd.DataFrame:
    table = pd.read_csv(paths.tables / "holdout_classification.csv")
    return pd.DataFrame(
        {
            "Measure": table["measure"],
            "Held out (95% interval)": [
                _span(e, lo, hi) if pd.notna(lo) else f"{int(e)}"
                for e, lo, hi in zip(
                    table["estimate"], table["ci_low"], table["ci_high"], strict=True
                )
            ],
            "Note": table["detail"],
        }
    )


def _reading(paths: ProjectPaths, consistency: pd.DataFrame) -> str:
    """Plain sentences built from the numbers: one per comparison, one on consistency."""
    table = pd.read_csv(paths.tables / "holdout_comparisons.csv")
    lines = []
    for _, r in table[table["role"] != "descriptive"].iterrows():
        verdict = "excludes zero" if r["ci_low"] > 0 or r["ci_high"] < 0 else "contains zero"
        lines.append(
            f"* The {r['role']} comparison, {r['comparison']} on {NAMES[r['metric']]}, is "
            f"{r['difference']:+.4f} and its interval {verdict}. The smallest difference these "
            f"records could detect is {r['detectable_difference']:.4f}."
        )
    inside = int((consistency.iloc[:, -1] == "yes").sum())
    lines.append(
        f"* For the served model, {inside} of {len(consistency)} held out estimates fall inside "
        "the interval of the same measure on development records."
    )
    lines += [f"* {sentence}" for sentence in _outside(paths, consistency)]
    return "\n".join(lines)


# Where each measure is best: higher, lower, or nearest a target value.
IDEAL = {"brier": ("lower", None), "calibration_slope": ("near", 1.0)}
IDEAL["calibration_intercept"] = ("near", 0.0)


def _worse(key: str, held: float, development: float) -> bool:
    kind, target = IDEAL.get(key, ("higher", None))
    if kind == "near":
        return abs(held - target) > abs(development - target)
    return held > development if kind == "lower" else held < development


def _outside(paths: ProjectPaths, consistency: pd.DataFrame) -> list[str]:
    """Say whether each held out estimate outside its development interval is worse or
    better, and whether the held out ROC AUC interval reaches ranking at random."""
    held = pd.read_csv(paths.tables / "holdout_result.csv")
    held = held[held["model"] == "C"].set_index("metric")["estimate"]
    labels = pd.read_csv(paths.tables / "holdout_classification.csv")
    held = pd.concat([held, labels.set_index("measure")["estimate"]])
    development = _development(paths)
    keys = dict(zip(consistency["Measure"], development, strict=True))
    out, worse = [], []
    for measure in consistency.loc[consistency.iloc[:, -1] == "no", "Measure"]:
        key = keys[measure]
        worse.append(_worse(key, held[key], development[key][0]))
        quality = "worse" if worse[-1] else "better"
        name = measure if measure[:2].isupper() else measure.lower()
        out.append(
            f"The held out {name} ({held[key]:.4f}) is {quality} than on development "
            f"records ({development[key][0]:.4f})."
        )
    roc = pd.read_csv(paths.tables / "holdout_result.csv").set_index(["model", "metric"])
    if roc.loc[("C", "roc_auc"), "ci_low"] <= 0.5:
        out.append(
            "The held out ROC AUC interval includes 0.5, the value of ranking at random, so "
            "on these records the served model's discrimination cannot be told apart from "
            "chance."
        )
    if worse and all(worse):
        out.append(
            "Every held out estimate outside its development interval is worse, not better, "
            "which is the opposite of what a model that had learned from these records would "
            "show."
        )
    return out


def write_holdout_report(paths: ProjectPaths, target=None) -> str:
    """Write ``docs/holdout_results.md`` and return its text."""
    log = (paths.partitions / "holdout_access.log").read_text().splitlines()
    evaluations = [line for line in log if "\tEVALUATED\t" in line]
    first = pd.read_csv(paths.tables / "holdout_result.csv").iloc[0]
    before, after, total = _audit_counts(paths)
    consistency = _consistency(paths)
    template = (paths.root / "src/antenatal/reporting/templates/holdout_results.md").read_text()
    text = template.format(
        stamp=datetime.now(UTC).isoformat(timespec="seconds"),
        evaluated=first["evaluated_at"],
        n=f"{int(first['n']):,}",
        events=int(first["events"]),
        log_lines=len(log),
        evaluations=len(evaluations),
        refused=sum("\tREFUSED\t" in line for line in log),
        evidence=EVIDENCE,
        before=before,
        after=after,
        total=total,
        timeline=_table(_timeline(paths, log)),
        consistency=_table(consistency),
        reading=_reading(paths, consistency),
        models=_table(_models(paths)),
        comparisons=_table(_comparisons(paths)),
        labels=_table(_labels(paths)),
    )
    (target or paths.root / "docs" / "holdout_results.md").write_text(text)
    return text
