"""``python -m antenatal audit-report``: the Stage 1 implementation audit of guideline version 2.

Writes ``docs/implementation_audit.md`` and three tables (``feature_quality.csv``,
``group_integrity.csv``, ``missingness_by_outcome_age.csv``). Every number comes from a
file in ``outputs/``, the data file, the code or git, read at generation time.
"""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from importlib.metadata import version

import pandas as pd

from antenatal.audit.extended import feature_quality, group_integrity, missingness_by_outcome_age
from antenatal.audit.quality import consistency_checks, quality_findings
from antenatal.config import PRIMARY, StudySpec
from antenatal.paths import ProjectPaths
from antenatal.study import load_context

LIBRARIES = ("scikit-learn", "pandas", "numpy", "fastapi", "sqlalchemy")
CODE_CHECKS = (
    ("evaluation/nested_cv.py", "self._guard.check(train)", "every fit refuses held out records"),
    (
        "evaluation/nested_cv.py",
        "self._screen.fit(train)",
        "availability screen fitted on the training fold",
    ),
    (
        "evaluation/nested_cv.py",
        'inner.split(x, y, train["group_key"])',
        "tuning folds drawn inside the training fold",
    ),
    (
        "evaluation/nested_cv.py",
        "GridSearchCV(pipeline",
        "tuning and refit inside the training fold",
    ),
    (
        "models/factory.py",
        'steps.append(("impute", _imputer(spec)))',
        "imputer is a pipeline step, fitted on training data",
    ),
    (
        "models/factory.py",
        'steps.append(("scale", StandardScaler()))',
        "scaler is a pipeline step, fitted on training data",
    ),
)
OUTPUTS = (
    ("Sensitivity analyses S1 to S6", "sensitivity_analyses.csv"),
    ("Learning curve", "learning_curve.csv"),
    ("Per measurement ablation", "ablation.csv"),
    ("Parameterisation comparison", "parameterisation.csv"),
    ("Informative missingness", "missingness_indicator_signal.csv"),
    ("Multiple imputation", "multiple_imputation.csv"),
    ("Subgroups", "subgroups.csv"),
    ("Retrieval at ranking budgets", "retrieval_at_budget.csv"),
    ("Calibration by set", "calibration_by_set.csv"),
    ("Decision curve", "decision_curve.csv"),
    ("Stage 2 experiments", "experiments_v2.csv"),
    ("Held out evaluation", "holdout_result.csv"),
)


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True).stdout.strip()


def _cell(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    if isinstance(value, float) and value.is_integer() and abs(value) >= 1:
        value = int(value)
    return f"{value:,}" if isinstance(value, int) else str(value)


def _table(frame: pd.DataFrame) -> str:
    """A Markdown table with readable headers and whole numbers without decimals."""
    head = "| " + " | ".join(str(c).replace("_", " ").capitalize() for c in frame.columns) + " |"
    rule = "| " + " | ".join("---" for _ in frame.columns) + " |"
    body = [
        "| " + " | ".join(_cell(v) for v in row) + " |" for row in frame.itertuples(index=False)
    ]
    return "\n".join([head, rule, *body])


def _code_lines(paths: ProjectPaths) -> pd.DataFrame:
    rows = []
    for file, text, meaning in CODE_CHECKS:
        lines = (paths.root / "src" / "antenatal" / file).read_text().splitlines()
        found = [i + 1 for i, line in enumerate(lines) if text in line]
        rows.append(
            {
                "file": f"src/antenatal/{file}",
                "line": found[0] if found else "not found",
                "what it shows": meaning,
            }
        )
    return pd.DataFrame(rows)


def _baseline(
    paths: ProjectPaths, spec: StudySpec, development: pd.DataFrame, holdout: int
) -> pd.DataFrame:
    summary = pd.read_csv(paths.tables / "results_summary.csv").set_index("key")
    experiments = pd.read_csv(paths.tables / "summary_by_experiment.csv")
    base = experiments[experiments["model"] == "baseline_prevalence"]["pr_auc"].iloc[0]

    def cell(key: str) -> str:
        r = summary.loc[key]
        return f"{r['value']:+.4f} ({r['ci_low']:+.4f} to {r['ci_high']:+.4f})"

    return pd.DataFrame(
        [
            (
                "Development records, events",
                f"{len(development):,}, {int(development['lbw'].sum())}",
            ),
            ("Held out records (sealed, not opened)", f"{holdout:,}"),
            (
                "Repeats, outer folds, inner folds",
                f"{spec.repeats}, {spec.outer_folds}, {spec.inner_folds}",
            ),
            ("Average precision of the prevalence only model", f"{base:.4f}"),
            ("Primary, C over B, average precision, logistic", cell("primary_c_over_b_logistic")),
            ("Primary, C over B, average precision, boosting", cell("primary_c_over_b_gbt")),
            ("Secondary, B over A, ROC AUC, logistic", cell("secondary_b_over_a_logistic")),
            ("Secondary, B over A, ROC AUC, boosting", cell("secondary_b_over_a_gbt")),
        ],
        columns=["quantity", "value"],
    )


def _outputs(paths: ProjectPaths) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "analysis": name,
                "file": f"outputs/tables/{file}",
                "status": "run" if (paths.tables / file).exists() else "not run",
            }
            for name, file in OUTPUTS
        ]
    )


def _write_tables(paths: ProjectPaths, context) -> dict[str, pd.DataFrame]:
    tables = {
        "feature_quality": feature_quality(context.raw, context.development),
        "group_integrity": group_integrity(context.raw, context.cohort.analysis),
        "missingness_by_outcome_age": missingness_by_outcome_age(context.development),
    }
    for name, table in tables.items():
        table.to_csv(paths.tables / f"{name}.csv", index=False)
    return tables


def write_audit_report(paths: ProjectPaths, spec: StudySpec = PRIMARY) -> str:
    """Write the audit report and its tables; return the report text."""
    context = load_context(paths, spec)
    tables = _write_tables(paths, context)
    holdout = context.partition.holdout_size
    integrity = pd.read_csv(paths.tables / "holdout_integrity.csv")
    missing = (
        tables["missingness_by_outcome_age"]
        .pivot_table(index="predictor", columns="group", values="missing_percent")
        .reset_index()
    )
    missing = missing[missing.drop(columns="predictor").max(axis=1) > 0].round(1)
    log_commits = _git("log", "--all", "--oneline", "--", "partitions/holdout_access.log")
    text = _template().format(
        stamp=datetime.now(UTC).isoformat(timespec="seconds"),
        branch=_git("rev-parse", "--abbrev-ref", "HEAD"),
        commit=_git("rev-parse", "--short", "HEAD"),
        commits=_git("rev-list", "--count", "HEAD"),
        libraries=", ".join(f"{name} {version(name)}" for name in LIBRARIES),
        baseline=_table(_baseline(paths, spec, context.development, holdout)),
        outputs=_table(_outputs(paths)),
        code=_table(_code_lines(paths)),
        integrity=_table(integrity[["check", "result", "value"]]),
        log_exists=(
            "exists" if (paths.partitions / "holdout_access.log").exists() else "does not exist"
        ),
        log_commits=len(log_commits.splitlines()) if log_commits else 0,
        findings=_table(quality_findings(context.raw, spec)),
        consistency=_table(consistency_checks(context.raw)),
        groups=_table(tables["group_integrity"]),
        features=_table(tables["feature_quality"]),
        missing=_table(missing),
    )
    (paths.root / "docs" / "implementation_audit.md").write_text(text)
    return text


def _template() -> str:
    from pathlib import Path

    return (Path(__file__).parent / "templates" / "implementation_audit.md").read_text()
