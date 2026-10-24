"""Generated blocks of the README, so its numbers and its tree are never typed by hand.

Three blocks are replaced between HTML comment markers: the development results, read
from ``outputs/tables/results_summary.csv``; the held out and Stage 2 results, read from
the tables the single held out evaluation and Stage 2 wrote; and the repository
structure, built from the files tracked by git to a depth of two.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pandas as pd

from antenatal.paths import ProjectPaths

RESULT_ROWS = (
    ("analysis_cohort", "analysis_events", "Analysis cohort", "count"),
    ("development_records", "development_events", "Development partition", "count"),
    (
        "primary_c_over_b_logistic",
        None,
        "Primary: first visit added (C over B), average precision, logistic",
        "diff",
    ),
    (
        "primary_c_over_b_gbt",
        None,
        "Primary: first visit added (C over B), average precision, trees",
        "diff",
    ),
    (
        "secondary_b_over_a_logistic",
        None,
        "Secondary: second visit added (B over A), ROC AUC, logistic",
        "diff",
    ),
    (
        "secondary_b_over_a_gbt",
        None,
        "Secondary: second visit added (B over A), ROC AUC, trees",
        "diff",
    ),
    (
        "primary_c_over_b_logistic_detectable",
        None,
        "Smallest detectable C over B, average precision, logistic",
        "value",
    ),
    ("learning_curve_gap_full", None, "C minus B with all training data (learning curve)", "value"),
    ("multiple_imputation_c_over_b", None, "C over B under pooled multiple imputation", "diff"),
    ("retrieval_top_10", None, "Share of events in the top 10 percent of the ranking", "share"),
    ("calibration_slope_logistic_l2_C", None, "Calibration slope, logistic, set C", "ratio"),
)


def _value(row: pd.Series, kind: str) -> str:
    if kind == "count":
        return f"{int(row['value']):,}"
    if kind == "share":
        low, high = 100 * row["ci_low"], 100 * row["ci_high"]
        return f"{100 * row['value']:.1f} percent ({low:.1f} to {high:.1f})"
    if kind == "ratio":
        return f"{row['value']:.2f} ({row['ci_low']:.2f} to {row['ci_high']:.2f})"
    if kind == "diff":
        return f"{row['value']:+.4f} ({row['ci_low']:+.4f} to {row['ci_high']:+.4f})"
    return f"{row['value']:+.4f}" if row["value"] < 0 else f"{row['value']:.4f}"


def results_block(summary: pd.DataFrame) -> str:
    """Markdown table of the headline results with 95 percent intervals."""
    indexed = summary.set_index("key")
    lines = ["| Result | Value (95 percent interval) |", "| --- | --- |"]
    for key, events_key, label, kind in RESULT_ROWS:
        text = _value(indexed.loc[key], kind)
        if events_key:
            text += f" pregnancies, {int(indexed.loc[events_key, 'value'])} events"
        lines.append(f"| {label} | {text} |")
    return "\n".join(lines)


def _span(estimate: float, low: float, high: float, signed: bool = True) -> str:
    form = "+.4f" if signed else ".4f"
    return f"{estimate:{form}} ({low:{form}} to {high:{form}})"


def heldout_block(tables: Path) -> str:
    """Markdown table of the single held out evaluation and the Stage 2 outcome."""
    result = pd.read_csv(tables / "holdout_result.csv")
    served = result[result["model"] == "C"].set_index("metric")
    comp = pd.read_csv(tables / "holdout_comparisons.csv").set_index("role")
    labels = pd.read_csv(tables / "holdout_classification.csv").set_index("measure")
    runs = len(pd.read_csv(tables / "experiments_v2_runs.csv"))
    passing = pd.read_json(tables / "selection_v2.json", typ="series")["candidates_passing"]

    def measured(frame, key, signed=False):
        r = frame.loc[key]
        return _span(r["estimate"], r["ci_low"], r["ci_high"], signed)

    def compared(role):
        r = comp.loc[role]
        return f"{_span(r['difference'], r['ci_low'], r['ci_high'])}, p {r['p_value']:.3f}"

    rows = [
        (
            "Held out partition",
            f"{int(result['n'].iloc[0]):,} pregnancies, "
            f"{int(result['events'].iloc[0])} events, evaluated once",
        ),
        ("Held out: first visit added (C over B), average precision", compared("primary")),
        ("Held out: second visit added (B over A), ROC AUC", compared("secondary")),
        ("Held out: served model, average precision", measured(served, "pr_auc")),
        ("Held out: served model, ROC AUC", measured(served, "roc_auc")),
        ("Held out: label sensitivity at the fixed threshold", measured(labels, "sensitivity")),
        ("Held out: label specificity at the fixed threshold", measured(labels, "specificity")),
        (
            "Stage 2 prespecified experiments that passed the selection rule",
            f"{int(passing)} of {runs}",
        ),
    ]
    lines = ["| Result | Value (95 percent interval) |", "| --- | --- |"]
    return "\n".join(lines + [f"| {label} | {text} |" for label, text in rows])


def tree_block(root: Path) -> str:
    """Tracked files and folders to a depth of two, in the style of ``tree -L 2``."""
    files = subprocess.run(
        ["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.split()
    tree: dict[str, set[str]] = {}
    for name in files:
        parts = name.split("/")
        tree.setdefault(parts[0], set())
        if len(parts) > 1:
            tree[parts[0]].add(parts[1])
    lines = ["."]
    tops = sorted(tree)
    for i, top in enumerate(tops):
        last = i == len(tops) - 1
        lines.append(("└── " if last else "├── ") + top)
        children = sorted(tree[top])
        for j, child in enumerate(children):
            branch = "└── " if j == len(children) - 1 else "├── "
            lines.append(("    " if last else "│   ") + branch + child)
    return "```\n" + "\n".join(lines) + "\n```"


def _replace(text: str, name: str, block: str) -> str:
    pattern = re.compile(rf"(<!-- {name}:start -->\n).*?(<!-- {name}:end -->)", re.S)
    if not pattern.search(text):
        raise ValueError(f"README has no {name} markers")
    return pattern.sub(lambda m: m.group(1) + block + "\n" + m.group(2), text)


def render_readme(paths: ProjectPaths, text: str) -> str:
    """Return ``text`` with every generated block refreshed."""
    summary = pd.read_csv(paths.tables / "results_summary.csv")
    text = _replace(text, "results", results_block(summary))
    text = _replace(text, "heldout", heldout_block(paths.tables))
    return _replace(text, "tree", tree_block(paths.root))


def update_readme(paths: ProjectPaths) -> None:
    """Rewrite the generated blocks of README.md in place."""
    readme = paths.root / "README.md"
    readme.write_text(render_readme(paths, readme.read_text()))
