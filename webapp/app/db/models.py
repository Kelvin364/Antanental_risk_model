"""Database tables for synthetic cases (Figure 3.7, interface side).

Synthetic cases are stored apart from cohort data. The synthetic flag is a
database check constraint, so no row can exist without it. Each assessment
records the artefact version and checksum that produced it and the size of the
reference caseload its rank was computed against (R16).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Declarative base of every table."""


class SyntheticCase(Base):
    """A synthetic pregnancy with the registration fields of set A."""

    __tablename__ = "synthetic_cases"
    __table_args__ = (CheckConstraint("synthetic = 1", name="synthetic_flag_always_true"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    label: Mapped[str] = mapped_column(String(80))
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False)
    age: Mapped[float] = mapped_column(Float)
    gravidity: Mapped[float] = mapped_column(Float)
    prior_deliveries: Mapped[float] = mapped_column(Float)
    height_cm: Mapped[float] = mapped_column(Float)
    registration_weight: Mapped[float] = mapped_column(Float)
    prior_caesarean: Mapped[bool] = mapped_column(Boolean)
    prior_hypertension_pregnancy: Mapped[bool] = mapped_column(Boolean)
    chronic_hypertension: Mapped[bool] = mapped_column(Boolean)
    diabetes: Mapped[bool] = mapped_column(Boolean)
    hiv: Mapped[bool] = mapped_column(Boolean)
    tuberculosis: Mapped[bool] = mapped_column(Boolean)
    sickle_cell: Mapped[bool] = mapped_column(Boolean)
    smoking: Mapped[bool] = mapped_column(Boolean)
    intimate_partner_violence: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    visits: Mapped[list[SyntheticVisit]] = relationship(
        back_populates="case", cascade="all, delete-orphan", order_by="SyntheticVisit.visit_number"
    )
    assessments: Mapped[list[Assessment]] = relationship(
        back_populates="case", cascade="all, delete-orphan", order_by="Assessment.id"
    )


class SyntheticVisit(Base):
    """One of the two antenatal visits of a synthetic case."""

    __tablename__ = "synthetic_visits"
    __table_args__ = (
        UniqueConstraint("case_id", "visit_number", name="one_row_per_case_and_visit"),
        CheckConstraint("visit_number in (1, 2)", name="visit_one_or_two"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("synthetic_cases.id"))
    visit_number: Mapped[int] = mapped_column(Integer)
    gestational_week: Mapped[float] = mapped_column(Float)
    systolic: Mapped[float] = mapped_column(Float)
    diastolic: Mapped[float] = mapped_column(Float)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    pulse: Mapped[float | None] = mapped_column(Float, nullable=True)
    haemoglobin: Mapped[float | None] = mapped_column(Float, nullable=True)

    case: Mapped[SyntheticCase] = relationship(back_populates="visits")


class Assessment(Base):
    """One scoring of a case by a specific artefact."""

    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("synthetic_cases.id"))
    artefact_version: Mapped[str] = mapped_column(String(40))
    artefact_sha256: Mapped[str] = mapped_column(String(64))
    reference_caseload_size: Mapped[int] = mapped_column(Integer)
    rank_position: Mapped[int] = mapped_column(Integer)
    probability: Mapped[float] = mapped_column(Float)
    interval_low: Mapped[float] = mapped_column(Float)
    interval_high: Mapped[float] = mapped_column(Float)
    interval_method: Mapped[str] = mapped_column(String(80))
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    case: Mapped[SyntheticCase] = relationship(back_populates="assessments")
