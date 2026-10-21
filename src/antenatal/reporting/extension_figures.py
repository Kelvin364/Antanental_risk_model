"""Figures for the Stage 5 analyses. Each reads a table written by ``run-extensions``."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from antenatal.reporting.style import INK, INK_SECONDARY, MUTED, SERIES, count_label, plt, save


def learning_curve(summary: pd.DataFrame, n: int, events: int, directory: Path) -> Path:
    """PR AUC and ROC AUC of sets B and C against the share of training data."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for ax, metric, label in (
        (axes[0], "pr_auc", "Precision recall area"),
        (axes[1], "roc_auc", "ROC area"),
    ):
        for name in ("B", "C"):
            rows = summary[summary["feature_set"] == name]
            ax.errorbar(
                rows["fraction"] * 100,
                rows[f"{metric}_mean"],
                yerr=rows[f"{metric}_sd"],
                color=SERIES[name],
                marker="o",
                capsize=3,
                label=f"Set {name}",
            )
        ax.set_xlabel("Share of each outer training fold used, percent")
        ax.set_ylabel(f"{label}, mean over repeats")
        ax.set_xticks([20, 40, 60, 80, 100])
    axes[0].axhline(events / n, color=INK_SECONDARY, linestyle="--", linewidth=1)
    axes[0].text(21, events / n, " no skill", fontsize=8, color=INK_SECONDARY, va="bottom")
    axes[1].legend(loc="lower right")
    fig.suptitle(
        "Learning curve, logistic regression, error bars are one standard deviation across "
        f"repeats\n{count_label(n, events)}",
        x=0.01,
        ha="left",
        fontweight="bold",
    )
    fig.tight_layout()
    return save(fig, directory, "fig12_learning_curve")


def forest(table: pd.DataFrame, title: str, name: str, directory: Path) -> Path:
    """Paired differences with intervals, one row per comparison, PR AUC only."""
    rows = table[table["metric"] == "pr_auc"]
    fig, ax = plt.subplots(figsize=(8.5, 0.5 * len(rows) + 1.6))
    y = np.arange(len(rows))[::-1]
    for yi, r in zip(y, rows.itertuples(), strict=True):
        ax.plot([r.ci_low, r.ci_high], [yi, yi], color=SERIES["A"], linewidth=2)
        ax.plot(
            r.difference,
            yi,
            "o",
            color=SERIES["A"],
            markersize=8,
            markeredgecolor="white",
            markeredgewidth=2,
        )
    ax.set_yticks(y, rows["comparison"].str.replace("_", " "))
    ax.axvline(0, color=INK, linewidth=1)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Paired difference in precision recall area, 95 percent group bootstrap interval")
    first = rows.iloc[0]
    ax.set_title(f"{title}\n{count_label(int(first['n']), int(first['events']))}")
    return save(fig, directory, name)


def missingness_rates(rates: pd.DataFrame, n: int, events: int, directory: Path) -> Path:
    """Low birth weight rate with and without each visit two value."""
    rows = rates[rates["missing_n"] > 0]
    fig, ax = plt.subplots(figsize=(8.5, 1.1 * len(rows) + 1.6))
    y = np.arange(len(rows))[::-1]
    for offset, prefix, colour, label in (
        (0.15, "recorded", SERIES["A"], "value recorded"),
        (-0.15, "missing", SERIES["B"], "value missing"),
    ):
        ax.errorbar(
            rows[f"{prefix}_rate"] * 100,
            y + offset,
            xerr=[
                (rows[f"{prefix}_rate"] - rows[f"{prefix}_low"]) * 100,
                (rows[f"{prefix}_high"] - rows[f"{prefix}_rate"]) * 100,
            ],
            fmt="o",
            color=colour,
            capsize=3,
            label=label,
        )
    ax.axvline(100 * events / n, color=MUTED, linestyle="--", linewidth=1)
    ax.set_yticks(y, rows["measurement"] + " at visit two")
    ax.set_xlabel("Low birth weight rate, percent, Wilson 95 percent interval")
    ax.legend(loc="lower right")
    ax.grid(axis="y", visible=False)
    ax.set_title(
        "Outcome rate by whether a visit two value was recorded\n" + count_label(n, events)
    )
    return save(fig, directory, "fig15_missingness_rates")


def retrieval(table: pd.DataFrame, directory: Path) -> Path:
    """Share of low birth weight births in the top of the ranking against random ranking."""
    fig, ax = plt.subplots(figsize=(7, 4))
    x = np.arange(len(table))
    ax.bar(
        x - 0.18, table["random_expectation"] * 100, width=0.34, color=MUTED, label="random ranking"
    )
    ax.bar(x + 0.18, table["retrieval"] * 100, width=0.34, color=SERIES["A"], label="model ranking")
    ax.errorbar(
        x + 0.18,
        table["retrieval"] * 100,
        yerr=[
            (table["retrieval"] - table["ci_low"]) * 100,
            (table["ci_high"] - table["retrieval"]) * 100,
        ],
        fmt="none",
        ecolor=INK,
        capsize=4,
    )
    ax.set_xticks(x, [f"Top {b} percent" for b in table["budget_percent"]])
    ax.set_ylabel("Share of low birth weight births found, percent")
    ax.legend(loc="upper left")
    ax.grid(axis="x", visible=False)
    first = table.iloc[0]
    ax.set_title(
        "Retrospective retrieval within ranking budgets, logistic regression, set C\n"
        + count_label(int(first["n"]), int(first["events_total"]))
    )
    return save(fig, directory, "fig16_retrieval_at_budget")
