"""Figures that show the study results. Each reads a table written by the analysis."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from antenatal.models.factory import MODEL_SPECS
from antenatal.reporting.style import (
    INK,
    INK_SECONDARY,
    MUTED,
    ORDERED,
    SERIES,
    count_label,
    plt,
    save,
)


def _interval_rows(ax, labels, values, lows, highs, colours) -> None:
    y = np.arange(len(labels))[::-1]
    for yi, v, lo, hi, c in zip(y, values, lows, highs, colours, strict=True):
        ax.plot([lo, hi], [yi, yi], color=c, linewidth=2)
        ax.plot(v, yi, "o", color=c, markersize=8, markeredgecolor="white", markeredgewidth=2)
    ax.set_yticks(y, labels)
    ax.grid(axis="y", visible=False)


def model_comparison(performance: pd.DataFrame, prevalence: float, directory: Path) -> Path:
    """Precision recall area of every family on set C, with group bootstrap intervals."""
    rows = performance[(performance["metric"] == "pr_auc") & (performance["feature_set"] == "C")]
    rows = rows.sort_values("value", ascending=False)
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    labels = [MODEL_SPECS[m].label for m in rows["model"]]
    _interval_rows(
        ax, labels, rows["value"], rows["ci_low"], rows["ci_high"], [SERIES["A"]] * len(rows)
    )
    ax.axvline(prevalence, color=INK_SECONDARY, linestyle="--", linewidth=1)
    ax.text(prevalence, len(rows) - 0.4, " no skill (prevalence)", fontsize=8, color=INK_SECONDARY)
    ax.set_xlabel("Area under the precision recall curve, 95 percent group bootstrap interval")
    first = rows.iloc[0]
    ax.set_title(
        "Eight model families on set C, development records\n"
        + count_label(int(first["n"]), int(first["events"]))
    )
    return save(fig, directory, "fig06_model_families")


def feature_set_differences(comparisons: pd.DataFrame, directory: Path) -> Path:
    """Paired differences between feature sets with their intervals."""
    rows = comparisons[
        comparisons["role"].isin(["primary", "secondary"])
        | (
            comparisons["comparison"].str.startswith("C over A")
            & (comparisons["metric"] == "pr_auc")
        )
    ]
    fig, ax = plt.subplots(figsize=(9, 3.8))
    labels = [
        f"{MODEL_SPECS[r.model].label}: {r.comparison}, {r.metric.replace('_', ' ')}"
        for r in rows.itertuples()
    ]
    colours = [ORDERED[0] if m == "logistic_l2" else ORDERED[1] for m in rows["model"]]
    _interval_rows(ax, labels, rows["difference"], rows["ci_low"], rows["ci_high"], colours)
    ax.axvline(0, color=INK, linewidth=1)
    ax.set_xlabel(
        "Paired difference (newer set minus older set), 95 percent group bootstrap interval"
    )
    first = rows.iloc[0]
    ax.set_title(
        "Does each added visit improve prediction?\n"
        + count_label(int(first["n"]), int(first["events"]))
    )
    return save(fig, directory, "fig07_feature_set_differences")


def calibration(tables: dict[str, pd.DataFrame], n: int, events: int, directory: Path) -> Path:
    """Predicted against observed risk for sets A, B and C."""
    fig, ax = plt.subplots(figsize=(6, 5.2))
    top = (
        max(max(t["mean_predicted"].max(), t["observed_high"].max()) for t in tables.values()) * 1.1
    )
    ax.plot(
        [0, top], [0, top], color=MUTED, linestyle="--", linewidth=1, label="perfect calibration"
    )
    for name, table in tables.items():
        colour = SERIES[name]
        ax.errorbar(
            table["mean_predicted"],
            table["observed"],
            yerr=[
                table["observed"] - table["observed_low"],
                table["observed_high"] - table["observed"],
            ],
            color=colour,
            marker="o",
            capsize=3,
            linewidth=2,
            label=f"Set {name}",
        )
    ax.set_xlim(0, top)
    ax.set_ylim(0, top)
    ax.set_xlabel("Mean predicted probability in each eighth")
    ax.set_ylabel("Observed low birth weight rate")
    ax.legend(loc="upper left")
    ax.set_title(
        "Calibration, logistic regression, averaged out of fold\n" + count_label(n, events)
    )
    return save(fig, directory, "fig08_calibration")


def decision_curve(table: pd.DataFrame, n: int, events: int, directory: Path) -> Path:
    """Net benefit against threshold for sets A, B and C and the two simple policies."""
    fig, ax = plt.subplots(figsize=(8, 4.6))
    for name in ("A", "B", "C"):
        ax.plot(
            table["threshold"] * 100, table[f"Set {name}"], color=SERIES[name], label=f"Set {name}"
        )
    ax.plot(
        table["threshold"] * 100,
        table["act for everyone"],
        color=MUTED,
        linestyle=":",
        label="act for everyone",
    )
    ax.axhline(0, color=INK_SECONDARY, linewidth=1, label="act for no one")
    low = min(-0.01, float(table[["Set A", "Set B", "Set C"]].min().min()) - 0.005)
    ax.set_ylim(low, float(table["act for everyone"].max()) * 1.2)
    ax.set_xlabel("Threshold probability, percent")
    ax.set_ylabel("Net benefit per pregnancy")
    ax.legend(loc="upper right")
    ax.set_title(
        "Decision curve, logistic regression, averaged out of fold\n" + count_label(n, events)
    )
    return save(fig, directory, "fig09_decision_curve")


def detectable_difference(comparisons: pd.DataFrame, directory: Path) -> Path:
    """Observed difference beside the smallest difference the design could detect."""
    rows = comparisons[comparisons["role"].isin(["primary", "secondary"])]
    fig, ax = plt.subplots(figsize=(8.5, 3.4))
    y = np.arange(len(rows))[::-1]
    ax.barh(
        y + 0.18,
        rows["detectable_difference"],
        height=0.34,
        color=MUTED,
        label="smallest detectable difference",
    )
    ax.barh(
        y - 0.18, rows["difference"], height=0.34, color=SERIES["A"], label="observed difference"
    )
    labels = [
        f"{MODEL_SPECS[r.model].label}: {r.comparison}, {r.metric.replace('_', ' ')}"
        for r in rows.itertuples()
    ]
    ax.set_yticks(y, labels, fontsize=8.5)
    ax.axvline(0, color=INK, linewidth=1)
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(axis="y", visible=False)
    first = rows.iloc[0]
    ax.set_title(
        "What this design could detect against what it observed\n"
        + count_label(int(first["n"]), int(first["events"]))
    )
    return save(fig, directory, "fig10_detectable_difference")


def sensitivity(table: pd.DataFrame, directory: Path) -> Path:
    """Forest plot of the primary comparison in every sensitivity analysis."""
    rows = table[table["role"] == "primary"]
    fig, ax = plt.subplots(figsize=(9, 4))
    labels = [
        f"{r.analysis} {r.specification} (n = {r.n:,}, events = {r.events})"
        for r in rows.itertuples()
    ]
    _interval_rows(
        ax, labels, rows["difference"], rows["ci_low"], rows["ci_high"], [SERIES["A"]] * len(rows)
    )
    ax.axvline(0, color=INK, linewidth=1)
    ax.set_xlabel("Set C minus set B, precision recall area, 95 percent group bootstrap interval")
    ax.set_title("Primary comparison under each pre specified sensitivity analysis")
    return save(fig, directory, "fig11_sensitivity")
