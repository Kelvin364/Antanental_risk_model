"""The research side of the data model (proposal Section 3.4.4), stored in SQLite.

``python -m antenatal load-db`` writes four tables into the application's
SQLite file, beside the synthetic case tables of the prototype:

* ``pregnancy_records``: one row per record of the released file, from
  ``outputs/cohort_manifest.csv`` (eligibility, exclusion step and reason,
  outcome, hashed registration group).
* ``visit_measurements``: the cleaned visit one and visit two values of every
  record, unique on record and visit number.
* ``model_configurations``: the frozen artefacts' version records and
  hyperparameters, unique on version.
* ``evaluation_results``: every outer fold result of the nested cross
  validation, unique on model, feature set, repeat and fold.

The held out partition is not read: no table records which records are held
out, and held out results do not exist until Stage 4. The tables are dropped
and rebuilt on every run, so the command can be repeated safely.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from antenatal.cohort.cleaning import RecordCleaner
from antenatal.config import PRIMARY, StudySpec
from antenatal.data.dictionary import VISITS, visit_column
from antenatal.data.loader import DataLoader
from antenatal.paths import ProjectPaths

VISIT_FIELDS = {
    "gestational_week": "ga",
    "systolic": "sbp",
    "diastolic": "dbp",
    "weight_kg": "weight",
    "pulse": "pulse",
    "haemoglobin": "hb",
}


class ResearchBase(DeclarativeBase):
    """Declarative base of the research tables, separate from the prototype's tables."""


class PregnancyRecord(ResearchBase):
    """PREGNANCY_RECORD: one released record and its eligibility."""

    __tablename__ = "pregnancy_records"

    record_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_key_hash: Mapped[str] = mapped_column(String(16))
    birth_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    lbw: Mapped[int] = mapped_column(Integer)
    eligible: Mapped[bool] = mapped_column(Boolean)
    in_analysis_cohort: Mapped[bool] = mapped_column(Boolean)
    exclusion_step: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exclusion_reason: Mapped[str] = mapped_column(Text)


class VisitMeasurement(ResearchBase):
    """VISIT_MEASUREMENT: cleaned values of one visit of one record."""

    __tablename__ = "visit_measurements"
    __table_args__ = (
        UniqueConstraint("record_id", "visit_number", name="one_row_per_record_and_visit"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    record_id: Mapped[int] = mapped_column(ForeignKey("pregnancy_records.record_id"))
    visit_number: Mapped[int] = mapped_column(Integer)
    gestational_week: Mapped[float | None] = mapped_column(Float, nullable=True)
    systolic: Mapped[float | None] = mapped_column(Float, nullable=True)
    diastolic: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    pulse: Mapped[float | None] = mapped_column(Float, nullable=True)
    haemoglobin: Mapped[float | None] = mapped_column(Float, nullable=True)
    haemoglobin_missing: Mapped[bool] = mapped_column(Boolean)


class ModelConfiguration(ResearchBase):
    """MODEL_CONFIGURATION and PIPELINE_ARTEFACT identity of one frozen artefact."""

    __tablename__ = "model_configurations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[str] = mapped_column(String(40), unique=True)
    role: Mapped[str] = mapped_column(String(80))
    model_family: Mapped[str] = mapped_column(String(40))
    feature_set: Mapped[str] = mapped_column(String(40))
    hyperparameters: Mapped[str] = mapped_column(Text)
    selected_columns: Mapped[str] = mapped_column(Text)
    seed: Mapped[int] = mapped_column(Integer)
    artefact_sha256: Mapped[str] = mapped_column(String(64))
    data_sha256: Mapped[str] = mapped_column(String(64))
    partition_sha256: Mapped[str] = mapped_column(String(64))
    frozen_at: Mapped[str] = mapped_column(String(40))


class EvaluationResult(ResearchBase):
    """EVALUATION_RESULT: one outer fold of the nested cross validation."""

    __tablename__ = "evaluation_results"
    __table_args__ = (
        UniqueConstraint("model", "feature_set", "repeat", "fold", name="one_row_per_fold"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    design: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(60))
    feature_set: Mapped[str] = mapped_column(String(40))
    repeat: Mapped[int] = mapped_column(Integer)
    fold: Mapped[int] = mapped_column(Integer)
    n: Mapped[int] = mapped_column(Integer)
    events: Mapped[int] = mapped_column(Integer)
    pr_auc: Mapped[float] = mapped_column(Float)
    roc_auc: Mapped[float] = mapped_column(Float)
    brier: Mapped[float] = mapped_column(Float)
    calibration_slope: Mapped[float] = mapped_column(Float)
    calibration_intercept: Mapped[float] = mapped_column(Float)
    params: Mapped[str] = mapped_column(Text)


def database_url(paths: ProjectPaths) -> str:
    """The application's SQLite file, or ``ANTENATAL_DATABASE_URL`` when it is set."""
    default = paths.root / "webapp" / "data" / "app.sqlite3"
    return os.environ.get("ANTENATAL_DATABASE_URL", f"sqlite:///{default}")


def pregnancy_frame(paths: ProjectPaths) -> pd.DataFrame:
    """Rows of ``pregnancy_records`` from the cohort manifest."""
    frame = pd.read_csv(paths.outputs / "cohort_manifest.csv")
    frame["exclusion_step"] = frame["exclusion_step"].astype("Int64")
    frame["exclusion_reason"] = frame["exclusion_reason"].fillna("")
    return frame


def visit_frame(paths: ProjectPaths, spec: StudySpec = PRIMARY) -> pd.DataFrame:
    """Rows of ``visit_measurements``: cleaned values, one row per recorded visit."""
    records = RecordCleaner(spec).clean(DataLoader(spec, paths.root).load())
    parts = []
    for visit in VISITS:
        part = pd.DataFrame({"record_id": records["record_id"], "visit_number": visit})
        for field, short in VISIT_FIELDS.items():
            part[field] = records[visit_column(short, visit)]
        parts.append(part)
    frame = pd.concat(parts, ignore_index=True)
    recorded = frame[list(VISIT_FIELDS)].notna().any(axis=1)
    frame = frame[recorded].reset_index(drop=True)
    frame["haemoglobin_missing"] = frame["haemoglobin"].isna()
    return frame


def configuration_frame(paths: ProjectPaths) -> pd.DataFrame:
    """Rows of ``model_configurations`` from every frozen artefact directory."""
    rows = []
    for version_file in sorted(paths.model.rglob("version.json")):
        version = json.loads(version_file.read_text())
        params = json.loads((version_file.parent / "model_params.json").read_text())
        rows.append(
            {
                "version": version["version"],
                "role": version.get("role", "primary, served"),
                "model_family": version["family"],
                "feature_set": version["feature_set"],
                "hyperparameters": json.dumps({"C": params.get("C")}),
                "selected_columns": json.dumps(params["feature_names"]),
                "seed": version["seed"],
                "artefact_sha256": version["artefact_sha256"],
                "data_sha256": version["data_sha256"],
                "partition_sha256": version["partition_sha256"],
                "frozen_at": version["created_at"],
            }
        )
    return pd.DataFrame(rows)


def evaluation_frame(paths: ProjectPaths) -> pd.DataFrame:
    """Rows of ``evaluation_results`` from the outer fold metrics."""
    frame = pd.read_csv(paths.tables / "cv_fold_metrics.csv").drop(columns=["n_features"])
    return frame.assign(design="repeated nested grouped cross validation")


def load_database(paths: ProjectPaths, spec: StudySpec = PRIMARY) -> dict[str, int]:
    """Drop, recreate and fill the four research tables; return their row counts."""
    engine = create_engine(database_url(paths))
    Path(engine.url.database or ".").parent.mkdir(parents=True, exist_ok=True)
    ResearchBase.metadata.drop_all(engine)
    ResearchBase.metadata.create_all(engine)
    frames = {
        PregnancyRecord.__tablename__: pregnancy_frame(paths),
        VisitMeasurement.__tablename__: visit_frame(paths, spec),
        ModelConfiguration.__tablename__: configuration_frame(paths),
        EvaluationResult.__tablename__: evaluation_frame(paths),
    }
    with engine.begin() as connection:
        for table, frame in frames.items():
            frame.to_sql(table, connection, if_exists="append", index=False)
    engine.dispose()
    return {table: len(frame) for table, frame in frames.items()}
