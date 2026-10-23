"""Liveness and artefact identity."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from webapp.app.api.deps import model_service
from webapp.app.core.settings import INTERVAL_LABEL, LIMITATION, SYNTHETIC_BANNER
from webapp.app.services.model_service import ModelService
from webapp.app.services.validation import EntryRules

router = APIRouter(tags=["health"])
Model = Annotated[ModelService, Depends(model_service)]


@router.get("/health")
def health(model: Model) -> dict[str, object]:
    """Artefact version and checksums, data checksum, prevalence and feature count."""
    return model.health()


@router.get("/api/artefact")
def artefact(model: Model) -> dict[str, object]:
    """The artefact's version record (version.json)."""
    return model.version_record


@router.get("/api/interface-text")
def interface_text() -> dict[str, object]:
    """The fixed banner, limitation and interval wording, and the entry ranges for the hints."""
    return {
        "banner": SYNTHETIC_BANNER,
        "limitation": LIMITATION,
        "interval_label": INTERVAL_LABEL,
        "ranges": EntryRules().ranges(),
    }
