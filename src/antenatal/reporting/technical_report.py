"""Writes docs/Technical-Report.md by filling a template with numbers read from files.

The prose lives in ``templates/technical_report.md``. Every number is a named
field filled here from ``outputs/tables``, ``docs/evidence`` or ``StudySpec``.
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from antenatal.config import PRIMARY
from antenatal.models.factory import FAMILY_SCREEN
from antenatal.paths import ProjectPaths

TEMPLATE = Path(__file__).parent / "templates" / "technical_report.md"


def _diff(row: pd.Series) -> str:
    return f"{row['value']:+.4f} ({row['ci_low']:+.4f} to {row['ci_high']:+.4f})"


def _share(row: pd.Series) -> str:
    low, high = 100 * row["ci_low"], 100 * row["ci_high"]
    return f"{100 * row['value']:.1f} percent ({low:.1f} to {high:.1f})"


def _results(summary: pd.DataFrame) -> dict[str, str]:
    s = summary.set_index("key")

    def value(key: str) -> float:
        return float(s.loc[key, "value"])

    def count(key: str) -> str:
        return f"{int(value(key)):,}"

    return {
        "analysis_cohort": count("analysis_cohort"),
        "analysis_events": count("analysis_events"),
        "eligible": count("eligible_cohort"),
        "records": count("records_in_file"),
        "dev_n": count("development_records"),
        "dev_events": count("development_events"),
        "holdout_n": f"{int(value('analysis_cohort') - value('development_records')):,}",
        "holdout_events": f"{int(value('analysis_events') - value('development_events'))}",
        "primary_lr": _diff(s.loc["primary_c_over_b_logistic"]),
        "primary_gbt": _diff(s.loc["primary_c_over_b_gbt"]),
        "secondary_lr": _diff(s.loc["secondary_b_over_a_logistic"]),
        "secondary_gbt": _diff(s.loc["secondary_b_over_a_gbt"]),
        "detect_lr": f"{s.loc['primary_c_over_b_logistic_detectable', 'value']:.4f}",
        "sens_excluding": count("sensitivity_primary_excluding_zero"),
        "sens_run": count("sensitivity_analyses_run"),
        "lc_gap": f"{s.loc['learning_curve_gap_full', 'value']:+.4f}",
        "mi": _diff(s.loc["multiple_imputation_c_over_b"]),
        "cal_c": f"{s.loc['calibration_slope_logistic_l2_C', 'value']:.2f} "
        f"({s.loc['calibration_slope_logistic_l2_C', 'ci_low']:.2f} to "
        f"{s.loc['calibration_slope_logistic_l2_C', 'ci_high']:.2f})",
        "retrieval10": _share(s.loc["retrieval_top_10"]),
        "retrieval20": _share(s.loc["retrieval_top_20"]),
        "retrieval30": _share(s.loc["retrieval_top_30"]),
        "pulse_diff": f"{100 * s.loc['pulse_missing_minus_recorded', 'value']:+.1f} points "
        f"({100 * s.loc['pulse_missing_minus_recorded', 'ci_low']:+.1f} to "
        f"{100 * s.loc['pulse_missing_minus_recorded', 'ci_high']:+.1f})",
    }


def _span(estimate: float, low: float, high: float, signed: bool = False) -> str:
    form = "+.4f" if signed else ".4f"
    return f"{estimate:{form}} ({low:{form}} to {high:{form}})"


def _stage2(tables: Path) -> dict[str, str]:
    """Stage 2: how many prespecified runs, how many passed, and the largest gain."""
    runs = pd.read_csv(tables / "experiments_v2_runs.csv")
    selection = json.loads((tables / "selection_v2.json").read_text())
    exp = pd.read_csv(tables / "experiments_v2.csv")
    exp = exp[(exp["role"] == "exploratory") & (exp["metric"] == "pr_auc")]
    best = exp.sort_values("difference").iloc[-1]
    return {
        "stage2_runs": str(len(runs)),
        "stage2_passing": str(selection["candidates_passing"]),
        "stage2_best_label": best["comparison"].split(": ", 1)[-1],
        "stage2_best": _span(best["difference"], best["ci_low"], best["ci_high"], signed=True),
        "stage2_best_detectable": f"{best['detectable_difference']:.4f}",
    }


def _holdout(tables: Path) -> dict[str, str]:
    """The single held out evaluation, from its saved tables only."""
    result = pd.read_csv(tables / "holdout_result.csv")
    c = result[result["model"] == "C"].set_index("metric")
    comp = pd.read_csv(tables / "holdout_comparisons.csv")
    labels = pd.read_csv(tables / "holdout_classification.csv").set_index("measure")
    audit = pd.read_csv(tables / "holdout_integrity.csv")

    def metric(name: str) -> str:
        return _span(c.loc[name, "estimate"], c.loc[name, "ci_low"], c.loc[name, "ci_high"])

    def compared(role: str) -> str:
        r = comp[comp["role"] == role].iloc[0]
        interval = _span(r["difference"], r["ci_low"], r["ci_high"], signed=True)
        return f"{interval}, p {r['p_value']:.3f}"

    def label(name: str) -> str:
        r = labels.loc[name]
        return _span(r["estimate"], r["ci_low"], r["ci_high"])

    return {
        "holdout_date": str(result["evaluated_at"].iloc[0])[:10],
        "holdout_ap": metric("pr_auc"),
        "holdout_roc": metric("roc_auc"),
        "holdout_slope": metric("calibration_slope"),
        "holdout_primary": compared("primary"),
        "holdout_secondary": compared("secondary"),
        "holdout_sens": label("sensitivity"),
        "holdout_spec": label("specificity"),
        "holdout_ppv": label("ppv"),
        "audit_pass": str(int((audit["result"] == "pass").sum())),
        "audit_total": str(len(audit)),
    }


def _tests(evidence: Path) -> dict[str, str]:
    t = json.loads((evidence / "test_summary.json").read_text())
    inputs = pd.read_csv(evidence / "input_tests.csv")
    shown = inputs[["number", "input", "expected", "observed_status", "result"]]
    rows = [
        "| No. | Input | Expected | Observed status | Result |",
        "| --- | --- | --- | --- | --- |",
    ]
    rows += ["| " + " | ".join(str(v) for v in r) + " |" for r in shown.itertuples(index=False)]
    return {
        "tests": str(t["tests"]),
        "seconds": str(t["seconds"]),
        "failures": str(t["failures"]),
        "unit_tests": str(t["by_suite"].get("unit", {}).get("tests", 0)),
        "integration_tests": str(t["by_suite"].get("integration", {}).get("tests", 0)),
        "browser_tests": str(t["by_suite"].get("e2e", {}).get("tests", 0)),
        "coverage": str(t["line_coverage_percent"]),
        "statements": f"{t['statements']:,}",
        "ruff": "no findings" if t["ruff_clean"] else "findings",
        "black": "no changes needed" if t["black_clean"] else "changes needed",
        "input_pass": str(int((inputs["result"] == "pass").sum())),
        "input_total": str(len(inputs)),
        "input_table": "\n".join(rows),
    }


def _commits(root: Path) -> str:
    out = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"], cwd=root, capture_output=True, text=True
    )
    return out.stdout.strip() or "unknown"


def write_technical_report(paths: ProjectPaths) -> Path:
    """Fill the template and write docs/Technical-Report.md."""
    fields = {
        "generated_at": datetime.now(UTC).date().isoformat(),
        "availability_percent": f"{100 * PRIMARY.availability_threshold:g}",
        "repeats": str(PRIMARY.repeats),
        "outer_folds": str(PRIMARY.outer_folds),
        "families": str(len(FAMILY_SCREEN)),
        "inner_folds": str(PRIMARY.inner_folds),
        "resamples": f"{PRIMARY.bootstrap_resamples:,}",
        "commits": _commits(paths.root),
        **_results(pd.read_csv(paths.tables / "results_summary.csv")),
        **_stage2(paths.tables),
        **_holdout(paths.tables),
        **_tests(paths.root / "docs" / "evidence"),
    }
    target = paths.root / "docs" / "Technical-Report.md"
    target.write_text(TEMPLATE.read_text().format_map(fields))
    return target
