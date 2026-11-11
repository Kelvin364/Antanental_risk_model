"""Protocol Sections 2 and 3: the week 36 frame with a summary of every visit up to 36 weeks.

Only visits whose recorded week is 36 or earlier are read. The P2 frame, used only as a
leakage demonstration, takes the latest visit whenever it happened.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
TRACK = HERE.parent
if str(TRACK) not in sys.path:
    sys.path.insert(0, str(TRACK))

from features import SETS, _registration, _visit_grid, at_landmark  # noqa: E402

WEEK = 36
MEASURES = ("sbp", "dbp", "weight", "hb", "pulse")
SUMMARIES = ("mean", "min", "max", "slope")
SET_H = SETS["C"] + [f"{m}_{s}" for m in MEASURES for s in SUMMARIES] + [
    "visits_by_36", "anaemia_ever", "malaria_ever",
]  # fmt: skip
SET_NAMES = {"B": SETS["B"], "C": SETS["C"], "H": SET_H}


def slope(values: np.ndarray, weeks: np.ndarray) -> np.ndarray:
    """Least squares change per week for each row, where two or more weeks differ."""
    mask = np.isfinite(values) & np.isfinite(weeks)
    n = mask.sum(axis=1)
    safe = np.maximum(n, 1)
    mean_x = np.where(mask, weeks, 0).sum(axis=1) / safe
    mean_y = np.where(mask, values, 0).sum(axis=1) / safe
    dx = np.where(mask, weeks - mean_x[:, None], 0)
    dy = np.where(mask, values - mean_y[:, None], 0)
    sxx = (dx**2).sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where((n >= 2) & (sxx > 0), (dx * dy).sum(axis=1) / sxx, np.nan)


def _ever(values: np.ndarray, condition: np.ndarray) -> np.ndarray:
    known = np.isfinite(values).any(axis=1)
    return np.where(known, condition.any(axis=1).astype(float), np.nan)


def history(raw: pd.DataFrame) -> pd.DataFrame:
    """Summaries over every visit at or before 36 weeks, one row per record."""
    grid = _visit_grid(raw)
    allowed = np.nan_to_num(grid["ga"], nan=np.inf) <= WEEK
    weeks = np.where(allowed, grid["ga"], np.nan)
    out = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for m in MEASURES:
            values = np.where(allowed, grid[m], np.nan)
            out[f"{m}_mean"] = np.nanmean(values, axis=1)
            out[f"{m}_min"] = np.nanmin(values, axis=1)
            out[f"{m}_max"] = np.nanmax(values, axis=1)
            out[f"{m}_slope"] = slope(values, weeks)
    hb = np.where(allowed, grid["hb"], np.nan)
    malaria = np.where(allowed, grid["malaria"], np.nan)
    out["visits_by_36"] = allowed.sum(axis=1).astype(float)
    out["anaemia_ever"] = _ever(hb, hb < 11)
    out["malaria_ever"] = _ever(malaria, malaria == 1)
    return pd.DataFrame(out, index=raw.index)


def primary_frame(raw: pd.DataFrame) -> pd.DataFrame:
    """P1: records with a usable visit in weeks 33 to 36, as the locked model."""
    base = at_landmark(raw, WEEK)
    return base.join(history(raw).loc[base.index])


def any_visit_frame(raw: pd.DataFrame) -> pd.DataFrame:
    """P2, leakage demonstration only: the latest visit at or before 36 weeks, whenever."""
    grid = _visit_grid(raw)
    allowed = np.nan_to_num(grid["ga"], nan=np.inf) <= WEEK
    latest = np.where(allowed, grid["ga"], -np.inf).argmax(axis=1)
    rows = np.arange(len(raw))
    frame = _registration(raw)
    for m in ("sbp", "dbp", "weight", "ga", "pulse", "hb"):
        frame[m] = grid[m][rows, latest]
    frame["visits_by_36"] = allowed.sum(axis=1).astype(float)
    frame["lbw"] = raw["lbw"].astype(int)
    frame["group"] = raw["group_key_hash"]
    return frame[allowed.any(axis=1)]
