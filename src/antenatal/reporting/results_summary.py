"""One table of every headline number, each traced to the output file it came from.

The README and the technical report read their numbers from
``outputs/tables/results_summary.csv``. No number is typed by hand.
"""

from __future__ import annotations

import pandas as pd

from antenatal.paths import ProjectPaths

COLUMNS = ["key", "description", "value", "ci_low", "ci_high", "source"]


class SummaryBuilder:
    """Collects rows from the result tables."""

    def __init__(self, paths: ProjectPaths) -> None:
        self._tables = paths.tables
        self.rows: list[dict[str, object]] = []

    def table(self, name: str) -> pd.DataFrame:
        """Read one result table."""
        return pd.read_csv(self._tables / f"{name}.csv")

    def add(self, key, description, value, source, low=None, high=None) -> None:
        """Add one row."""
        self.rows.append(
            dict(
                zip(
                    COLUMNS,
                    [key, description, value, low, high, f"outputs/tables/{source}.csv"],
                    strict=True,
                )
            )
        )

    def add_comparison(self, key, description, row: pd.Series, source: str) -> None:
        """Add a paired difference with its interval, and its detectable difference."""
        self.add(key, description, row["difference"], source, row["ci_low"], row["ci_high"])
        if "detectable_difference" in row:
            self.add(
                f"{key}_detectable",
                f"Smallest detectable difference: {description}",
                row["detectable_difference"],
                source,
            )


def _row(table: pd.DataFrame, **match) -> pd.Series:
    mask = pd.Series(True, index=table.index)
    for column, value in match.items():
        mask &= table[column] == value
    found = table[mask]
    if len(found) != 1:
        raise LookupError(f"Expected one row for {match}, found {len(found)}")
    return found.iloc[0]


def _cohort(s: SummaryBuilder) -> None:
    flow = s.table("cohort_flow")
    s.add(
        "records_in_file",
        "Records in the released file",
        int(flow["remaining"].iloc[0]),
        "cohort_flow",
    )
    s.add(
        "eligible_cohort",
        "Eligible cohort",
        int(flow.loc[flow["number"] == 3, "remaining"].item()),
        "cohort_flow",
    )
    s.add("analysis_cohort", "Analysis cohort", int(flow["remaining"].iloc[-1]), "cohort_flow")
    s.add(
        "analysis_events",
        "Low birth weight events in the analysis cohort",
        int(flow["events_remaining"].iloc[-1]),
        "cohort_flow",
    )
    comparisons = s.table("feature_set_comparisons")
    s.add(
        "development_records",
        "Development records",
        int(comparisons["n"].iloc[0]),
        "feature_set_comparisons",
    )
    s.add(
        "development_events",
        "Development events",
        int(comparisons["events"].iloc[0]),
        "feature_set_comparisons",
    )


def _primary(s: SummaryBuilder) -> None:
    table = s.table("feature_set_comparisons")
    for model, name in (("logistic_l2", "logistic"), ("gradient_boosting", "gbt")):
        s.add_comparison(
            f"primary_c_over_b_{name}",
            f"C over B, PR AUC, {model}",
            _row(table, model=model, role="primary"),
            "feature_set_comparisons",
        )
        s.add_comparison(
            f"secondary_b_over_a_{name}",
            f"B over A, ROC AUC, {model}",
            _row(table, model=model, role="secondary"),
            "feature_set_comparisons",
        )
    for feature_set in ("A", "B", "C"):
        row = _row(s.table("summary_by_experiment"), model="logistic_l2", feature_set=feature_set)
        for metric in ("pr_auc", "roc_auc", "calibration_slope", "calibration_intercept"):
            s.add(
                f"logistic_{feature_set}_{metric}",
                f"Logistic regression, set {feature_set}, {metric}",
                row[metric],
                "summary_by_experiment",
            )


def _extensions(s: SummaryBuilder) -> None:
    sensitivity = s.table("sensitivity_analyses")
    primary_rows = sensitivity[sensitivity["role"] == "primary"]
    s.add(
        "sensitivity_primary_excluding_zero",
        "Sensitivity analyses whose C over B interval excludes zero",
        int(primary_rows["excludes_zero"].sum()),
        "sensitivity_analyses",
    )
    s.add(
        "sensitivity_analyses_run",
        "Sensitivity analyses run",
        len(primary_rows),
        "sensitivity_analyses",
    )
    curve = s.table("learning_curve")
    full = curve[(curve["fraction"] == 1.0) & (curve["feature_set"] == "C")].iloc[0]
    s.add(
        "learning_curve_gap_full",
        "C minus B PR AUC with all training data, mean over repeats",
        full["pr_auc_gap_mean"],
        "learning_curve",
    )


def _stage_five(s: SummaryBuilder) -> None:
    ablation = s.table("ablation")
    best = ablation[ablation["metric"] == "pr_auc"].sort_values("difference").iloc[-1]
    s.add_comparison(
        "ablation_largest",
        f"Largest single first visit contribution: {best['comparison']}",
        best,
        "ablation",
    )
    signal = s.table("missingness_indicator_signal")
    for feature_set in ("B", "C"):
        s.add_comparison(
            f"indicator_signal_{feature_set}",
            f"Missingness indicators added, set {feature_set}, PR AUC",
            _row(signal, comparison=f"Indicators added, set {feature_set}", metric="pr_auc"),
            "missingness_indicator_signal",
        )
    mi = s.table("multiple_imputation")
    s.add_comparison(
        "multiple_imputation_c_over_b",
        "C over B, PR AUC, pooled iterative imputation",
        _row(mi, model="logistic_l2_iterative_pooled", metric="pr_auc"),
        "multiple_imputation",
    )
    subgroups = s.table("subgroups")
    s.add(
        "subgroups_reported",
        "Strata with at least 30 events",
        int(subgroups.drop_duplicates("stratum")["reported"].sum()),
        "subgroups",
    )


def _questions(s: SummaryBuilder) -> None:
    retrieval = s.table("retrieval_at_budget")
    for row in retrieval.itertuples():
        s.add(
            f"retrieval_top_{row.budget_percent}",
            f"Share of events in the top {row.budget_percent} percent of the ranking",
            row.retrieval,
            "retrieval_at_budget",
            row.ci_low,
            row.ci_high,
        )
    calibration = s.table("calibration_by_set")
    for row in calibration.itertuples():
        s.add(
            f"calibration_slope_{row.model}_{row.feature_set}",
            f"Calibration slope, {row.model}, set {row.feature_set}",
            row.calibration_slope,
            "calibration_by_set",
            row.calibration_slope_low,
            row.calibration_slope_high,
        )
    rates = s.table("missingness_outcome_rates")
    pulse = rates[rates["measurement"] == "Pulse rate"].iloc[0]
    s.add(
        "pulse_missing_minus_recorded",
        "Low birth weight rate, pulse missing minus recorded",
        pulse["difference_missing_minus_recorded"],
        "missingness_outcome_rates",
        pulse["difference_low"],
        pulse["difference_high"],
    )


def build_results_summary(paths: ProjectPaths) -> pd.DataFrame:
    """Write and return outputs/tables/results_summary.csv."""
    builder = SummaryBuilder(paths)
    for part in (_cohort, _primary, _extensions, _stage_five, _questions):
        part(builder)
    table = pd.DataFrame(builder.rows, columns=COLUMNS)
    table.to_csv(paths.tables / "results_summary.csv", index=False)
    return table
