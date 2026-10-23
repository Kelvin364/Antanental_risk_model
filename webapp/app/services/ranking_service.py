"""The Caseload screen: assessed synthetic cases ordered by predicted probability.

Each case shows its position within the recorded synthetic caseload and its
rank within the reference caseload of development pregnancies, and its label
at the fixed classification threshold (decision D6). No band, tier or priority
label is produced.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from webapp.app.core.settings import INTERVAL_LABEL, LIMITATION, SYNTHETIC_BANNER
from webapp.app.db.models import SyntheticCase
from webapp.app.schemas.cases import CaseloadOut, CaseloadRow
from webapp.app.services.model_service import ModelService


class RankingService:
    """Orders the latest assessment of every case."""

    def __init__(self, sessions: sessionmaker, model: ModelService) -> None:
        self._sessions = sessions
        self._model = model

    def caseload(self) -> CaseloadOut:
        """Every assessed case, highest probability first."""
        with self._sessions() as session:
            cases = session.scalars(select(SyntheticCase)).all()
            latest = [(case, case.assessments[-1]) for case in cases if case.assessments]
        latest.sort(key=lambda pair: (-pair[1].probability, pair[0].id))
        rows = [self._row(position, case, a) for position, (case, a) in enumerate(latest, 1)]
        artefact = self._model.artefact
        return CaseloadOut(
            rows=rows,
            reference_caseload_size=len(artefact.reference_probabilities),
            prevalence=artefact.prevalence,
            events=artefact.events,
            artefact_version=artefact.version,
            classification_threshold=self._model.rule.threshold,
            interval_label=INTERVAL_LABEL,
            limitation=LIMITATION,
            banner=SYNTHETIC_BANNER,
        )

    def _row(self, position: int, case: SyntheticCase, assessment) -> CaseloadRow:
        result = self._model.classify(
            assessment.probability, assessment.interval_low, assessment.interval_high
        )
        return CaseloadRow(
            case_id=case.id,
            label=case.label,
            caseload_position=position,
            reference_rank_position=assessment.rank_position,
            probability=assessment.probability,
            interval_low=assessment.interval_low,
            interval_high=assessment.interval_high,
            classification=result.label,
            certainty=result.certainty,
            artefact_version=assessment.artefact_version,
        )
