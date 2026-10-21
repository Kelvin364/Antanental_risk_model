"""Figures that describe the cohort and the development data.

Each function takes a prepared table or frame, draws one figure and writes it
to the figures directory. None of them computes a study result.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import numpy as np
import pandas as pd

from antenatal.data.dictionary import VISIT_MEASUREMENTS, visit_column
from antenatal.reporting.style import INK_SECONDARY, MUTED, ORDERED, SERIES, count_label, plt, save


def cohort_flow(flow: pd.DataFrame, directory: Path) -> Path:
    """Records remaining after each eligibility step (Table 3.5)."""
    fig, ax = plt.subplots(figsize=(10, 6))
    labels = [
        (
            textwrap.fill(f"Step {r.number}, removes: {r.criterion}", 48)
            if r.number
            else "Records in the file"
        )
        for r in flow.itertuples()
    ]
    y = np.arange(len(flow))[::-1]
    colours = [SERIES["A"] if n in (3, len(flow) - 1) else MUTED for n in flow["number"]]
    ax.barh(y, flow["remaining"], color=colours, height=0.6)
    for yi, r in zip(y, flow.itertuples(), strict=True):
        text = f"{r.remaining:,}" + (f"  (excluded {r.excluded:,})" if r.number else "")
        ax.text(r.remaining + 80, yi, text, va="center", fontsize=8.5, color=INK_SECONDARY)
    ax.set_yticks(y, labels, fontsize=8)
    ax.set_xlim(0, flow["remaining"].max() * 1.35)
    ax.set_xlabel("Pregnancies remaining")
    ax.grid(axis="y", visible=False)
    last = flow.iloc[-1]
    ax.set_title(
        "Cohort derivation; blue bars are the eligible and analysis cohorts\n"
        + count_label(int(last["remaining"]), int(last["events_remaining"]))
    )
    return save(fig, directory, "fig01_cohort_flow")


def outcome_prevalence(development: pd.DataFrame, directory: Path) -> Path:
    """Birth weight distribution of development records with the 2.5 kg threshold."""
    fig, ax = plt.subplots(figsize=(8, 4))
    weights = development["birth_weight_kg"]
    bins = np.arange(1.0, 6.01, 0.1)
    counts, edges, patches = ax.hist(weights, bins=bins, color=MUTED, edgecolor="white")
    for patch, left in zip(patches, edges[:-1], strict=True):
        if left < 2.5 - 1e-9:
            patch.set_facecolor(SERIES["A"])
    ax.axvline(2.5, color=INK_SECONDARY, linestyle="--", linewidth=1)
    ax.set_xlabel("Recorded birth weight, kg (blue: below 2.5 kg)")
    ax.set_ylabel("Pregnancies")
    events = int(development["lbw"].sum())
    ax.set_title(
        f"Low birth weight in development records: {100 * events / len(development):.2f} percent\n"
        + count_label(len(development), events)
    )
    return save(fig, directory, "fig02_outcome_prevalence")


def measurement_distributions(development: pd.DataFrame, directory: Path) -> Path:
    """Visit two measurements by outcome, development records."""
    items = [m for m in VISIT_MEASUREMENTS]
    fig, axes = plt.subplots(2, 3, figsize=(12, 6.5))
    for ax, item in zip(axes.ravel(), items, strict=True):
        column = visit_column(item.name, 2)
        groups = [development.loc[development["lbw"] == g, column].dropna() for g in (0, 1)]
        parts = ax.boxplot(
            groups,
            tick_labels=["2.5 kg or more", "Below 2.5 kg"],
            widths=0.5,
            patch_artist=True,
            showfliers=False,
        )
        for patch, colour in zip(parts["boxes"], ("#d9d8d3", SERIES["A"]), strict=True):
            patch.set_facecolor(colour)
        for median in parts["medians"]:
            median.set_color("#0b0b0b")
        ax.set_title(f"{item.label} at visit two, {item.unit}", fontsize=9.5)
        ax.text(
            0.02,
            0.97,
            f"recorded for {sum(len(g) for g in groups):,}",
            transform=ax.transAxes,
            va="top",
            fontsize=8,
            color=INK_SECONDARY,
        )
    fig.suptitle(
        "Visit two measurements by outcome, development records ("
        + count_label(len(development), int(development["lbw"].sum()))
        + ")",
        x=0.01,
        ha="left",
        fontweight="bold",
    )
    fig.tight_layout()
    return save(fig, directory, "fig03_measurements_by_outcome")


def missingness(table: pd.DataFrame, n: int, events: int, directory: Path) -> Path:
    """Percent missing per measurement and visit."""
    pivot = table.pivot(index="measurement", columns="visit", values="percent_missing")
    fig, ax = plt.subplots(figsize=(8, 3.8))
    y = np.arange(len(pivot))
    for offset, visit, colour in ((-0.18, 1, ORDERED[0]), (0.18, 2, ORDERED[1])):
        ax.barh(y + offset, pivot[visit], height=0.34, color=colour, label=f"Visit {visit}")
        for yi, v in zip(y + offset, pivot[visit], strict=True):
            ax.text(v + 1, yi, f"{v:.1f}", va="center", fontsize=8, color=INK_SECONDARY)
    ax.set_yticks(y, pivot.index)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Percent missing")
    ax.legend(loc="lower right")
    ax.grid(axis="y", visible=False)
    ax.set_title(
        "Missing values by measurement and visit, development records\n" + count_label(n, events)
    )
    return save(fig, directory, "fig04_missingness")


def availability_screen(screen: pd.DataFrame, n: int, events: int, directory: Path) -> Path:
    """Availability at both visits against the 60 percent threshold."""
    ordered = screen.sort_values("available_both_visits_percent")
    fig, ax = plt.subplots(figsize=(8, 3.6))
    colours = [SERIES["A"] if r == "pass" else MUTED for r in ordered["result"]]
    ax.barh(
        ordered["measurement"], ordered["available_both_visits_percent"], color=colours, height=0.6
    )
    threshold = float(ordered["threshold_percent"].iloc[0])
    ax.axvline(threshold, color=INK_SECONDARY, linestyle="--", linewidth=1)
    for yi, r in enumerate(ordered.itertuples()):
        ax.text(
            r.available_both_visits_percent + 1,
            yi,
            f"{r.available_both_visits_percent:.1f} {r.result}",
            va="center",
            fontsize=8.5,
            color=INK_SECONDARY,
        )
    ax.set_xlim(0, 115)
    ax.set_xlabel(
        f"Percent of records with the measurement at both visits (threshold {threshold:g})"
    )
    ax.grid(axis="y", visible=False)
    ax.set_title(
        "Availability screen, development records (blue: passes)\n" + count_label(n, events)
    )
    return save(fig, directory, "fig05_availability_screen")
