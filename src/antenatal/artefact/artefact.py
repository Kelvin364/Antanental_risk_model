"""The fitted development pipeline, frozen as one artefact (Section 3.3.6, R12, R16).

The artefact is the configuration frozen at the end of the primary analysis,
fitted once on the development partition and serialised with a SHA 256 and a
version record. The prototype loads only this artefact, verified by checksum,
and scores a case through ``assess``, so the interface cannot differ from the
study.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

from antenatal.artefact.interval import wald_interval
from antenatal.data.loader import ChecksumMismatch
from antenatal.features.builder import FeatureBuilder

ARTEFACT_FILE = "lbw_model.joblib"
CHECKSUM_FILE = "lbw_model.sha256"
PARAMS_FILE = "model_params.json"
VERSION_FILE = "version.json"
QUANTILES = (0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99)


def build_timestamp() -> datetime:
    """Creation time; honours SOURCE_DATE_EPOCH so a rebuild can be byte identical."""
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:
        return datetime.fromtimestamp(int(epoch), UTC)
    return datetime.now(UTC).replace(microsecond=0)


@dataclass(frozen=True)
class Assessment:
    """Everything the interface shows for one scored case."""

    probability: float
    interval_low: float
    interval_high: float
    rank: int
    reference_size: int

    @property
    def caseload_size(self) -> int:
        """The reference caseload plus the scored case."""
        return self.reference_size + 1


@dataclass
class FittedPipelineArtefact:
    """Fitted pipeline plus everything needed to verify, score and rank a case."""

    version: str
    created_at: str
    data_sha256: str
    partition_sha256: str
    seed: int
    family: str
    feature_set: str
    feature_names: list[str]
    pipeline: Pipeline
    coefficient_covariance: np.ndarray | None
    reference_probabilities: np.ndarray
    prevalence: float
    events: int
    n_development: int
    spec: dict[str, object] = field(default_factory=dict)

    def score(self, cases: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Probability and interval for each row of cleaned case values."""
        x = FeatureBuilder().derive(cases)[self.feature_names].astype(float)
        if self.coefficient_covariance is None:
            p = self.pipeline.predict_proba(x)[:, 1]
            return p, np.full_like(p, np.nan), np.full_like(p, np.nan)
        return wald_interval(self.pipeline, self.coefficient_covariance, x)

    def rank_of(self, probability: float) -> int:
        """Position among the reference caseload: 1 means the highest probability."""
        return int(np.sum(self.reference_probabilities > probability)) + 1

    def assess(self, case: dict[str, float | None]) -> Assessment:
        """Score one case given as cleaned values keyed by study field name."""
        frame = pd.DataFrame([case], dtype=float)
        p, low, high = (float(v[0]) for v in self.score(frame))
        return Assessment(p, low, high, self.rank_of(p), len(self.reference_probabilities))

    def params(self) -> dict[str, object]:
        """Human readable parameters written to model_params.json."""
        steps = self.pipeline.named_steps
        out: dict[str, object] = {
            "feature_names": self.feature_names,
            "impute_medians": steps["impute"].statistics_.tolist(),
            "indicator_features": [
                self.feature_names[i] for i in steps["impute"].indicator_.features_
            ],
            "probability_quantiles": {
                str(q): float(np.quantile(self.reference_probabilities, q)) for q in QUANTILES
            },
        }
        if "scale" in steps:
            out["scale_mean"] = steps["scale"].mean_.tolist()
            out["scale_std"] = steps["scale"].scale_.tolist()
        model = steps["model"]
        if hasattr(model, "coef_"):
            out["coefficients"] = model.coef_[0].tolist()
            out["intercept"] = float(model.intercept_[0])
            out["C"] = float(model.C)
        if self.coefficient_covariance is not None:
            out["covariance"] = self.coefficient_covariance.tolist()
        return out

    def version_record(self, sha256: str) -> dict[str, object]:
        """Contents of version.json."""
        return {
            "version": self.version,
            "created_at": self.created_at,
            "artefact_sha256": sha256,
            "data_sha256": self.data_sha256,
            "partition_sha256": self.partition_sha256,
            "seed": self.seed,
            "family": self.family,
            "feature_set": self.feature_set,
            "n_features": len(self.feature_names),
            "n_development": self.n_development,
            "events": self.events,
            "prevalence": self.prevalence,
            "reference_caseload_size": len(self.reference_probabilities),
        }

    def save(self, directory: Path) -> str:
        """Write the joblib file, its SHA 256, the parameters and the version record."""
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / ARTEFACT_FILE
        joblib.dump(self, path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        (directory / CHECKSUM_FILE).write_text(f"{digest}  {ARTEFACT_FILE}\n")
        (directory / PARAMS_FILE).write_text(json.dumps(self.params(), indent=2))
        (directory / VERSION_FILE).write_text(json.dumps(self.version_record(digest), indent=2))
        return digest

    @staticmethod
    def load(directory: Path, verify: bool = True) -> FittedPipelineArtefact:
        """Load the artefact; with ``verify`` the SHA 256 is checked before unpickling."""
        directory = Path(directory)
        path = directory / ARTEFACT_FILE
        if verify:
            expected = (directory / CHECKSUM_FILE).read_text().split()[0]
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != expected:
                raise ChecksumMismatch(f"{path.name} has SHA 256 {digest}, expected {expected}")
        artefact = joblib.load(path)
        if not isinstance(artefact, FittedPipelineArtefact):
            raise TypeError(f"{path} does not hold a FittedPipelineArtefact")
        return artefact
