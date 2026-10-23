"""Check that this installation's model answers as the frozen model does.

``python -m webapp.app.selfcheck`` loads the artefact through ``ModelService``, which
verifies its SHA 256 and its classification threshold, scores one reference synthetic
case and prints the probability, interval, rank, label and the installed library
versions. The same reference case scored on the development machine gives
0.06345433774713931, so the two printouts can be compared directly.

It starts no server and touches no database, so it is safe on a small host beside
the running server: an earlier version that started a second server ran a 512 MB
machine out of memory. The signed in HTTP path is checked by ``scripts/smoke_test.py``
and by the integration tests. On the host:
``fly ssh console --app antenatal-caseload -C "python -m webapp.app.selfcheck"``.
"""

from __future__ import annotations

import json
import platform

import joblib
import sklearn

from webapp.app.core.settings import Settings
from webapp.app.schemas.cases import CaseCreate, VisitCreate
from webapp.app.services.model_service import ModelService, study_values

CASE = {
    "synthetic": True,
    "age": 24,
    "gravidity": 2,
    "prior_deliveries": 1,
    "height_cm": 156,
    "registration_weight": 58,
}
VISIT_ONE = {"gestational_week": 16, "systolic": 110, "diastolic": 70, "weight_kg": 56, "pulse": 80}
VISIT_TWO = {"gestational_week": 22, "systolic": 118, "diastolic": 76, "weight_kg": 58, "pulse": 88}
EXPECTED_PROBABILITY = 0.06345433774713931


def run() -> dict[str, object]:
    """Score the reference case and compare it with the development machine's answer."""
    model = ModelService(Settings.from_env().model_dir)
    values = study_values(CaseCreate(**CASE), VisitCreate(**VISIT_ONE), VisitCreate(**VISIT_TWO))
    result = model.predict(values)
    label = model.classify(result.probability, result.interval_low, result.interval_high)
    agrees = abs(result.probability - EXPECTED_PROBABILITY) <= 1e-9
    return {
        "artefact_version": model.version,
        "artefact_sha256": model.sha256,
        "classification_threshold": model.rule.threshold,
        "probability": result.probability,
        "interval": [result.interval_low, result.interval_high],
        "rank": result.rank,
        "label": label.label,
        "matches_development_machine_to_1e-9": agrees,
        "python": platform.python_version(),
        "scikit_learn": sklearn.__version__,
        "joblib": joblib.__version__,
    }


def main() -> int:
    result = run()
    print(json.dumps(result, indent=2))
    return 0 if result["matches_development_machine_to_1e-9"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
