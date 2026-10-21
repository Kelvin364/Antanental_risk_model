"""One visual style for every figure, so the report reads as one system.

Colours are the first three slots of a palette validated for colour vision
deficiency on a light surface. Text always uses the ink colours, never a series
colour. Every figure title states the number of pregnancies and events
(Requirement R6).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SERIES = {"A": "#2a78d6", "B": "#eb6834", "C": "#1baf7a"}
ORDERED = ("#2a78d6", "#eb6834", "#1baf7a")
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
MUTED = "#a3a29c"
GRID = "#e6e5e0"
SURFACE = "#ffffff"

plt.rcParams.update(
    {
        "figure.dpi": 100,
        "savefig.dpi": 150,
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.edgecolor": MUTED,
        "axes.labelcolor": INK,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "xtick.color": INK_SECONDARY,
        "ytick.color": INK_SECONDARY,
        "text.color": INK,
        "legend.frameon": False,
        "lines.linewidth": 2,
        "lines.markersize": 7,
        "figure.facecolor": SURFACE,
    }
)


def count_label(n: int, events: int) -> str:
    """The standard count suffix of a figure title."""
    return f"n = {n:,}, events = {events}"


def save(fig: plt.Figure, directory: Path, name: str) -> Path:
    """Write ``fig`` as a PNG and close it."""
    path = Path(directory) / f"{name}.png"
    fig.savefig(path, bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)
    return path
