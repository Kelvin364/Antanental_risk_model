"""FastAPI entry point for the antenatal caseload prototype.

Run:  uvicorn app.main:app --reload   (from the demo/ directory)
Then open http://127.0.0.1:8000/

The server verifies the model checksum on startup, serves the prototype
interface, and exposes a small JSON API that runs the frozen model.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.model_service import ModelService, RANGES

BASE = Path(__file__).resolve().parent.parent
STATIC = BASE / "static"

app = FastAPI(
    title="Antenatal Caseload Prototype",
    description="Research prototype — predicts recorded low birth weight at the "
                "second antenatal visit. Synthetic data only; not for clinical use.",
    version="0.1.0",
)

# Model is loaded and checksum-verified once, at startup.
service = ModelService()


class VisitInput(BaseModel):
    age: float = Field(..., ge=RANGES["age"][0], le=RANGES["age"][1])
    height_cm: float
    booking_weight: float
    gravidity: float
    prior_deliveries: float
    prior_livebirths: float
    prior_stillbirths: float
    miscarriage_count: float
    ga_v1: float
    sbp_v1: float
    dbp_v1: float
    weight_v1: float
    ga_v2: float
    sbp_v2: float
    dbp_v2: float
    weight_v2: float
    pulse_v2: float


@app.get("/health")
def health():
    """Liveness plus the checksum of the loaded artefact."""
    return {
        "status": "ok",
        "model_sha256": service.sha256,
        "n_features": len(service.feature_names),
        "cohort_prevalence": service.prevalence,
        "spec": service.spec,
    }


@app.post("/api/predict")
def predict(payload: VisitInput):
    """Return the calibrated probability, interval, and cohort position."""
    data = payload.model_dump()
    errors = service.validate(data)
    if errors:
        raise HTTPException(status_code=422, detail=errors)
    return service.predict(data)


# Serve the single-page interface.
@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
