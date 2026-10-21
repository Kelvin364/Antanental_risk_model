"""Load, verify, and serve the frozen low-birth-weight model.

The service never retrains. It loads a single serialised artefact, verifies it
against a stored SHA-256 checksum before use, and refuses to start if the
artefact has changed. Predictions are expressed as a calibrated probability
with a 95% interval and a position (percentile) within the study cohort — never
a clinical risk category.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Dict, List

import joblib
import numpy as np

MODEL_DIR = Path(__file__).resolve().parent.parent / "model"
ARTEFACT = MODEL_DIR / "lbw_model.joblib"
CHECKSUM = MODEL_DIR / "lbw_model.sha256"
PARAMS = MODEL_DIR / "model_params.json"

# Raw clinical inputs the caller supplies (all others are derived).
RAW_INPUTS = [
    "age", "height_cm", "booking_weight", "gravidity", "prior_deliveries",
    "prior_livebirths", "prior_stillbirths", "miscarriage_count",
    "ga_v1", "sbp_v1", "dbp_v1", "weight_v1",
    "ga_v2", "sbp_v2", "dbp_v2", "weight_v2", "pulse_v2",
]

# Enforced physiological ranges (mirrors the notebook's data engineering).
RANGES = {
    "age": (12, 55), "height_cm": (120, 210), "booking_weight": (30, 150),
    "gravidity": (1, 20), "prior_deliveries": (0, 20), "prior_livebirths": (0, 20),
    "prior_stillbirths": (0, 20), "miscarriage_count": (0, 20),
    "ga_v1": (1, 28), "sbp_v1": (60, 250), "dbp_v1": (30, 160), "weight_v1": (30, 150),
    "ga_v2": (1, 28), "sbp_v2": (60, 250), "dbp_v2": (30, 160), "weight_v2": (30, 150),
    "pulse_v2": (30, 200),
}


class ModelService:
    def __init__(self) -> None:
        self._verify_checksum()
        self.artefact = joblib.load(ARTEFACT)
        self.model = self.artefact["model"]
        self.feature_names: List[str] = list(self.artefact["feature_names"])
        self.cohort_probs = np.sort(np.asarray(self.artefact["cohort_probs"], dtype=float))
        self.prevalence = float(self.artefact["prevalence"])
        self.spec = self.artefact.get("spec", {})
        self.sha256 = self._read_checksum()
        # Exported linear-model parameters for the Wald interval (identical to
        # the interval shown by the browser prototype).
        p = json.loads(PARAMS.read_text())
        self._mean = np.asarray(p["scale_mean"], dtype=float)
        self._std = np.asarray(p["scale_std"], dtype=float)
        self._median = np.asarray(p["impute_median"], dtype=float)
        self._coef = np.asarray(p["coef"], dtype=float)
        self._intercept = float(p["intercept"])
        self._cov = np.asarray(p["cov"], dtype=float)  # [intercept, coefs]

    # ---- integrity -------------------------------------------------------
    @staticmethod
    def _read_checksum() -> str:
        return CHECKSUM.read_text().split()[0]

    def _verify_checksum(self) -> None:
        if not ARTEFACT.exists() or not CHECKSUM.exists():
            raise FileNotFoundError("Model artefact or checksum missing from ./model")
        digest = hashlib.sha256(ARTEFACT.read_bytes()).hexdigest()
        expected = self._read_checksum()
        if digest != expected:
            raise ValueError(
                "Model checksum mismatch — the artefact has changed and will not be "
                f"loaded.\n  expected {expected}\n  found    {digest}"
            )

    # ---- feature engineering (identical to the notebook) -----------------
    def _feature_vector(self, s: Dict[str, float]) -> Dict[str, float]:
        f = dict(s)
        f["miscarriage_any"] = 1 if s.get("miscarriage_count", 0) > 0 else 0
        f["d_sbp"] = s["sbp_v2"] - s["sbp_v1"]
        f["d_dbp"] = s["dbp_v2"] - s["dbp_v1"]
        f["d_ga"] = s["ga_v2"] - s["ga_v1"]
        f["d_weight"] = s["weight_v2"] - s["weight_v1"]
        gap = (s["ga_v2"] - s["ga_v1"]) or float("nan")
        f["sbp_per_week"] = f["d_sbp"] / gap
        f["weight_per_week"] = f["d_weight"] / gap
        return f

    def _row(self, s: Dict[str, float]) -> np.ndarray:
        f = self._feature_vector(s)
        return np.array([[f.get(name, np.nan) for name in self.feature_names]], dtype=float)

    # ---- validation ------------------------------------------------------
    @staticmethod
    def validate(s: Dict[str, float]) -> List[str]:
        errors = []
        for k in RAW_INPUTS:
            if k not in s or s[k] is None:
                errors.append(f"missing: {k}")
                continue
            lo, hi = RANGES[k]
            if not (lo <= s[k] <= hi):
                errors.append(f"out of range: {k} must be {lo}-{hi}")
        if not errors and not (s["ga_v2"] > s["ga_v1"]):
            errors.append("visit-2 gestational age must be later than visit-1")
        return errors

    # ---- prediction ------------------------------------------------------
    def predict(self, s: Dict[str, float]) -> Dict[str, float]:
        prob = float(self.model.predict_proba(self._row(s))[0, 1])
        # Rank within the cohort (percentile position).
        pct = float(np.searchsorted(self.cohort_probs, prob) / len(self.cohort_probs) * 100)
        # 95% interval: Wald interval on the logit from the coefficient
        # covariance (matches the browser prototype exactly).
        f = self._feature_vector(s)
        x = np.array([f.get(name, np.nan) for name in self.feature_names], dtype=float)
        x = np.where(np.isnan(x), self._median, x)
        z = (x - self._mean) / self._std
        logit = self._intercept + float(self._coef @ z)
        zaug = np.concatenate([[1.0], z])
        se = math.sqrt(max(float(zaug @ self._cov @ zaug), 0.0))
        lo = 1.0 / (1.0 + math.exp(-(logit - 1.96 * se)))
        hi = 1.0 / (1.0 + math.exp(-(logit + 1.96 * se)))
        return {
            "probability": round(prob, 4),
            "interval_low": round(lo, 4),
            "interval_high": round(hi, 4),
            "cohort_percentile": round(pct, 1),
            "prevalence": round(self.prevalence, 4),
        }
