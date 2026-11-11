"""Folders of the sequential analysis, and the import path to the fusion code it reuses."""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRACK = HERE.parent
ROOT = TRACK.parent
OUT = HERE / "outputs"
FUSION = TRACK / "fusion"
for folder in (TRACK, FUSION):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))
