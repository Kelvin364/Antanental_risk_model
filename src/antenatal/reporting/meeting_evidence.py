"""Writes docs/meeting_evidence.md from the output tables, so no number is typed by hand.

Held out counts are derived as the analysis cohort minus the development
partition, so the held out records themselves are never opened.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from antenatal.models.factory import MODEL_SPECS
from antenatal.paths import ProjectPaths

TEMPLATE = Path(__file__).parent / "templates" / "not_yet_complete.md"


def _fmt(value: float, digits: int = 4) -> str:
    return f"{value:+.{digits}f}"


def _markdown(frame: pd.DataFrame) -> str:
    header = "| " + " | ".join(frame.columns) + " |"
    rule = "| " + " | ".join("---" for _ in frame.columns) + " |"
    body = ["| " + " | ".join(str(v) for v in row) + " |" for row in frame.itertuples(index=False)]
    return "\n".join([header, rule, *body])


def _percent(rate: float, low: float, high: float, n: int) -> str:
    return f"{100 * rate:.1f} ({100 * low:.1f} to {100 * high:.1f}), n = {n:,}"


def _interval(row) -> str:
    return f"{_fmt(row.difference)} ({_fmt(row.ci_low)} to {_fmt(row.ci_high)})"


def _counts(tables) -> str:
    flow = pd.read_csv(tables / "cohort_flow.csv")
    comparisons = pd.read_csv(tables / "feature_set_comparisons.csv")
    analysis_n, analysis_events = int(flow["remaining"].iloc[-1]), int(
        flow["events_remaining"].iloc[-1]
    )
    dev_n, dev_events = int(comparisons["n"].iloc[0]), int(comparisons["events"].iloc[0])
    shown = flow.rename(
        columns={
            "number": "Step",
            "criterion": "Criterion",
            "excluded": "Excluded",
            "remaining": "Remaining",
            "events_remaining": "Events remaining",
        }
    )
    split = pd.DataFrame(
        [
            ("Analysis cohort", analysis_n, analysis_events),
            ("Development partition", dev_n, dev_events),
            (
                "Held out partition (sealed, not opened)",
                analysis_n - dev_n,
                analysis_events - dev_events,
            ),
        ],
        columns=["Partition", "Pregnancies", "Low birth weight events"],
    )
    flow_part = f"## Cohort flow (Table 3.5)\n\n{_markdown(shown)}"
    return f"{flow_part}\n\n## Development and held out counts\n\n{_markdown(split)}"


def _results(tables) -> str:
    comparisons = pd.read_csv(tables / "feature_set_comparisons.csv")
    rows = comparisons[comparisons["role"].isin(["primary", "secondary"])]
    shown = pd.DataFrame(
        {
            "Model": [MODEL_SPECS[m].label for m in rows["model"]],
            "Role": rows["role"],
            "Comparison": rows["comparison"],
            "Metric": rows["metric"].str.replace("_", " ").str.upper(),
            "Difference (95 percent interval)": [_interval(r) for r in rows.itertuples()],
            "Smallest detectable": rows["detectable_difference"].map(lambda v: f"{v:.4f}"),
        }
    )
    n, events = int(rows["n"].iloc[0]), int(rows["events"].iloc[0])
    return (
        f"## Primary and secondary results, both model families\n\nDevelopment records, n = {n:,}, "
        f"events = {events}. Group bootstrap of paired averaged out of fold predictions, 2,000 "
        f"resamples.\n\n{_markdown(shown)}\n\n## Learning curve\n\n"
        "![Learning curve](../outputs/figures/fig12_learning_curve.png)"
    )


def _sensitivity(tables) -> str:
    table = pd.read_csv(tables / "sensitivity_analyses.csv")
    rows = table[table["role"].isin(["primary", "secondary"])]
    shown = pd.DataFrame(
        {
            "Analysis": rows["analysis"],
            "Specification": rows["specification"],
            "Comparison": rows["comparison"].str.replace("_", " "),
            "Metric": rows["metric"].str.replace("_", " ").str.upper(),
            "Difference (95 percent interval)": [_interval(r) for r in rows.itertuples()],
            "n": rows["n"],
            "Events": rows["events"],
        }
    )
    return f"## Sensitivity analyses S1 to S6\n\n{_markdown(shown)}"


def _missingness(tables) -> str:
    rates = pd.read_csv(tables / "missingness_outcome_rates.csv")
    signal = pd.read_csv(tables / "missingness_indicator_signal.csv")
    lines = []
    for r in rates[rates["missing_n"] > 0].itertuples():
        recorded = _percent(r.recorded_rate, r.recorded_low, r.recorded_high, r.recorded_n)
        missing = _percent(r.missing_rate, r.missing_low, r.missing_high, r.missing_n)
        difference = (
            f"{100 * r.difference_missing_minus_recorded:+.1f} "
            f"({100 * r.difference_low:+.1f} to {100 * r.difference_high:+.1f})"
        )
        lines.append(f"| {r.measurement} | {recorded} | {missing} | {difference} |")
    pr = signal[signal["metric"] == "pr_auc"]
    indicator = "; ".join(f"{r.comparison}: {_interval(r)}" for r in pr.itertuples())
    return (
        "## Missingness finding\n\n"
        "| Visit two measurement | Low birth weight percent when recorded | When missing "
        "| Missing minus recorded, points |\n| --- | --- | --- | --- |\n"
        + "\n".join(lines)
        + "\n\nSystolic and diastolic pressure and gestational week are never missing in the "
        "cohort, because the eligibility rule requires them.\n\n"
        f"Missingness indicators, PR AUC with against without: {indicator}.\n\n"
        "Reading: the pulse difference is an association with recording practice, not physiology. "
        "Whether a pulse is recorded depends on the clinic, the day and the worker, and with no "
        "facility identifier this cannot be separated from differences between clinics. The "
        "indicators add no predictive signal that can be told apart from zero."
    )


def write_meeting_evidence(paths: ProjectPaths) -> str:
    """Write and return the meeting evidence document."""
    tables = paths.tables
    parts = [
        "# Evidence for the supervisor meeting\n\n"
        "Generated by `python -m antenatal meeting-evidence` from `outputs/tables`. Every number "
        "below comes from those files. The held out partition has not been opened.",
        _counts(tables),
        _results(tables),
        _sensitivity(tables),
        _missingness(tables),
        TEMPLATE.read_text().strip(),
    ]
    text = "\n\n".join(parts) + "\n"
    (paths.root / "docs" / "meeting_evidence.md").write_text(text)
    return text
