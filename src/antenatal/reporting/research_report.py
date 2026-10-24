"""Write the Stage 3 results: ``outputs/research/`` and ``docs/research_results.md``.

Every number in the Markdown is read from the table written beside it, never typed.
The held out section is filled only when the single held out evaluation has written
its tables; until then it says the evaluation has not been run.
"""

from __future__ import annotations

from datetime import UTC, datetime

import matplotlib.pyplot as plt
import pandas as pd

from antenatal.config import PRIMARY, StudySpec
from antenatal.paths import ProjectPaths
from antenatal.reporting.style import INK_SECONDARY, ORDERED, count_label, save
from antenatal.research import QUESTIONS, questions_table, results_table

RESULTS_FILE = "results_table.csv"
HOLDOUT_RESULTS = "holdout_comparisons.csv"
METRIC_NAMES = {
    "pr_auc": "average precision",
    "roc_auc": "ROC AUC",
    "retrieval_gain": "retrieval minus random",
}


def _number(value: float, signed: bool = True) -> str:
    if pd.isna(value):
        return "not defined"
    return f"{value:+.4f}" if signed else f"{value:.4f}"


def _p(value: float) -> str:
    if pd.isna(value):
        return ""
    return "below 0.001" if value < 0.001 else f"{value:.3f}"


def _reading(row: pd.Series) -> str:
    """One plain sentence for a tested row, built from its numbers."""
    if row["family"].startswith("descriptive"):
        return "descriptive, not tested"
    if row["excludes_zero"]:
        direction = "higher" if row["difference"] > 0 else "lower"
        return f"the interval excludes zero: the first model is {direction}"
    detectable = row.get("detectable_difference")
    if pd.notna(detectable):
        return f"the interval contains zero; no difference of {detectable:.4f} or more was found"
    return "the interval contains zero"


def _rows(table: pd.DataFrame) -> list[str]:
    lines = [
        "| Question | Model | Comparison | Measure | Difference (95% interval) | p | p, Holm "
        "| DeLong p, descriptive | Reading |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for _, r in table.iterrows():
        interval = f"{_number(r['difference'])} ({_number(r['ci_low'])} to {_number(r['ci_high'])})"
        lines.append(
            f"| {r['question']} | {r['model']} | {r['comparison']} | "
            f"{METRIC_NAMES.get(r['metric'], r['metric'])} | {interval} | {_p(r['p_value'])} | "
            f"{_p(r['p_holm'])} | {_p(r['delong_p_value'])} | {_reading(r)} |"
        )
    return lines


def _questions() -> list[str]:
    lines = ["| Number | Question | Endpoint | Method | Null hypothesis |", "| --- " * 5 + "|"]
    for q in QUESTIONS:
        lines.append(
            f"| {q.number} | {q.question} | {q.endpoint} | {q.method} | {q.null_hypothesis} |"
        )
    return lines


def _holdout(paths: ProjectPaths) -> list[str]:
    path = paths.tables / HOLDOUT_RESULTS
    if not path.exists():
        return [
            "The single held out evaluation has not been run. It runs once, after the "
            "supervisor's approval, by the protocol in `docs/holdout_protocol.md`; this "
            "section is then filled from `outputs/tables/holdout_comparisons.csv`."
        ]
    table = pd.read_csv(path)
    lines = ["| Comparison | Measure | Role | Difference (95% interval) | p |", "| --- " * 5 + "|"]
    for _, r in table.iterrows():
        interval = f"{_number(r['difference'])} ({_number(r['ci_low'])} to {_number(r['ci_high'])})"
        lines.append(
            f"| {r['comparison']} | {METRIC_NAMES.get(r['metric'], r['metric'])} | {r['role']} "
            f"| {interval} | {_p(r['p_value'])} |"
        )
    return lines


def _figure(table: pd.DataFrame, directory) -> None:
    tested = table[table["family"] != "descriptive, not tested"].iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 0.42 * len(tested) + 1.4))
    for position, (_, r) in enumerate(tested.iterrows()):
        colour = ORDERED[0] if r["family"].startswith("prespecified") else ORDERED[1]
        ax.plot([r["ci_low"], r["ci_high"]], [position, position], color=colour)
        ax.plot(r["difference"], position, "o", color=colour)
    labels = [
        f"{'Q' + r['question'] if r['question'].isdigit() else 'Supporting'} {r['model']}: "
        f"{r['comparison']}"
        for _, r in tested.iterrows()
    ]
    ax.set_yticks(range(len(tested)), labels, fontsize=7.5)
    ax.axvline(0, color=INK_SECONDARY, linewidth=1)
    ax.set_xlabel(
        "Difference on each row's own measure, with its 95 percent group bootstrap interval"
    )
    for colour, label in ((ORDERED[0], "prespecified, not adjusted"), (ORDERED[1], "exploratory")):
        ax.plot([], [], "o-", color=colour, label=label)
    ax.legend(loc="upper right", fontsize=8)
    first = table.iloc[0]
    ax.set_title(
        f"Research questions 1 to 4 ({count_label(int(first['n']), int(first['events']))})"
    )
    save(fig, directory, "research_differences")


def _text(table: pd.DataFrame, paths: ProjectPaths, spec: StudySpec) -> str:
    first = table.iloc[0]
    return "\n".join(
        [
            "# Research results",
            "",
            f"*Generated by `python -m antenatal research-results` on "
            f"{datetime.now(UTC).isoformat(timespec='seconds')} from `outputs/research/"
            f"{RESULTS_FILE}`. No model was fitted to produce it.*",
            "",
            "## Research questions",
            "",
            *_questions(),
            "",
            "## Results on development records",
            "",
            f"Pooled out of fold predictions averaged over {spec.repeats} repeats, "
            f"{int(first['n']):,} records with {int(first['events'])} events. Each interval is "
            f"a paired group bootstrap with {spec.bootstrap_resamples:,} resamples; p is twice "
            "the smaller share of resamples on either side of zero. Questions 1 and 2 are "
            "prespecified and not adjusted; the other tested rows are one exploratory family "
            "with a Holm adjustment. DeLong's test ignores registration groups and is "
            "descriptive only. No test is made over fold level results.",
            "",
            *_rows(table),
            "",
            "## Held out records",
            "",
            *_holdout(paths),
            "",
        ]
    )


def write_research_results(paths: ProjectPaths, spec: StudySpec = PRIMARY, target=None) -> str:
    """Compute the table, save it with its figure, and write the Markdown summary."""
    out = paths.outputs / "research"
    (out / "figures").mkdir(parents=True, exist_ok=True)
    table = results_table(paths, spec)
    table.to_csv(out / RESULTS_FILE, index=False)
    questions_table().to_csv(out / "research_questions.csv", index=False)
    _figure(table, out / "figures")
    text = _text(table, paths, spec)
    (target or paths.root / "docs" / "research_results.md").write_text(text)
    return text
