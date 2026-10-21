"""Loads the frozen research artefact and scores cases with it (R12).

The service never trains and never reimplements a calculation. Feature
construction, the probability, the Wald interval and the rank all come from
``antenatal.artefact.FittedPipelineArtefact``. The artefact's SHA 256 is
verified when the service is created, so the application refuses to start if
the file has changed.
"""

from __future__ import annotations

import json
from pathlib import Path

from antenatal.artefact.artefact import (
    CHECKSUM_FILE,
    VERSION_FILE,
    Assessment,
    FittedPipelineArtefact,
)
from webapp.app.schemas.cases import CaseCreate, VisitCreate

VISIT_FIELDS = {
    "gestational_week": "ga",
    "systolic": "sbp",
    "diastolic": "dbp",
    "weight_kg": "weight",
    "pulse": "pulse",
    "haemoglobin": "hb",
}
FLAGS = (
    "prior_caesarean",
    "prior_hypertension_pregnancy",
    "chronic_hypertension",
    "diabetes",
    "hiv",
    "tuberculosis",
    "sickle_cell",
    "smoking",
    "intimate_partner_violence",
)
NUMBERS = ("age", "gravidity", "prior_deliveries", "height_cm", "registration_weight")


def study_values(
    case: CaseCreate, first: VisitCreate, second: VisitCreate
) -> dict[str, float | None]:
    """Translate interface fields to the study field names the artefact expects."""
    values: dict[str, float | None] = {name: getattr(case, name) for name in NUMBERS}
    values.update({name: float(getattr(case, name)) for name in FLAGS})
    for number, visit in ((1, first), (2, second)):
        for field, short in VISIT_FIELDS.items():
            values[f"{short}_v{number}"] = getattr(visit, field)
    return values


class ModelService:
    """The single scoring path of the application."""

    def __init__(self, model_dir: Path) -> None:
        self._dir = Path(model_dir)
        self.artefact = FittedPipelineArtefact.load(self._dir, verify=True)
        self.sha256 = (self._dir / CHECKSUM_FILE).read_text().split()[0]
        self.version_record = json.loads((self._dir / VERSION_FILE).read_text())

    @property
    def version(self) -> str:
        """Semantic version of the loaded artefact."""
        return self.artefact.version

    def predict(self, values: dict[str, float | None]) -> Assessment:
        """Probability, interval and reference rank for cleaned study values."""
        return self.artefact.assess(values)

    def health(self) -> dict[str, object]:
        """What ``/health`` reports."""
        return {
            "status": "ok",
            "artefact_version": self.artefact.version,
            "artefact_sha256": self.sha256,
            "data_sha256": self.artefact.data_sha256,
            "partition_sha256": self.artefact.partition_sha256,
            "prevalence": self.artefact.prevalence,
            "events": self.artefact.events,
            "n_features": len(self.artefact.feature_names),
            "reference_caseload_size": len(self.artefact.reference_probabilities),
        }
