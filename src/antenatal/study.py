"""Orchestration of the analysis and of the artefact freeze, on development records only.

The served configuration is fixed here before any result is read: L2 logistic
regression on set C. Two reasons decide it. Set C is the set the research
question is about, and Table 3.7 asks the prototype to show a confidence
interval computed from the fitted coefficient covariance, which only a linear
model provides.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from antenatal.artefact.artefact import FittedPipelineArtefact, build_timestamp
from antenatal.artefact.interval import coefficient_covariance
from antenatal.cohort.builder import Cohort, CohortBuilder
from antenatal.cohort.partition import FoldAssignment, Partition, PartitionWriter
from antenatal.config import PRIMARY, StudySpec
from antenatal.data.loader import DataLoader
from antenatal.evaluation.nested_cv import CVResults, Experiment, NestedCVRunner
from antenatal.features.builder import FeatureBuilder
from antenatal.features.screen import AvailabilityScreen
from antenatal.features.sets import PRIMARY_SETS, FeatureSet, SetA, SetB, SetC
from antenatal.models.factory import FAMILY_SCREEN, PRIMARY_MODELS
from antenatal.paths import ProjectPaths

SERVED_MODEL = "logistic_l2"
UNIFORM_GBT = "gradient_boosting_uniform"
SERVED_SET = SetC()
ARTEFACT_VERSION = "1.0.0"
OOF_FILE = "oof_predictions.parquet"


@dataclass
class StudyContext:
    """Everything the analysis reads: the cohort, the sealed partition and the folds."""

    raw: pd.DataFrame
    cohort: Cohort
    partition: Partition
    folds: FoldAssignment

    @property
    def development(self) -> pd.DataFrame:
        """Development records only."""
        return self.partition.development(self.cohort)


def load_context(paths: ProjectPaths, spec: StudySpec = PRIMARY) -> StudyContext:
    """Load the verified data, rebuild the cohort and read the sealed partition files."""
    raw = DataLoader(spec, paths.root).load()
    cohort = CohortBuilder(spec).build(raw)
    writer = PartitionWriter(paths.partitions, spec)
    return StudyContext(raw, cohort, writer.load(), writer.load_folds())


def experiments() -> list[Experiment]:
    """Baseline B0, the primary models on A, B and C, the family screen on C, and the
    gradient boosted trees with uniform median imputation on A, B and C (sensitivity)."""
    out = [Experiment("baseline_prevalence", PRIMARY_SETS[0])]
    out += [Experiment(m, s) for m in PRIMARY_MODELS for s in PRIMARY_SETS]
    out += [Experiment(m, SetC()) for m in FAMILY_SCREEN if m not in PRIMARY_MODELS]
    out += [Experiment(UNIFORM_GBT, s) for s in PRIMARY_SETS]
    return out


def load_results(paths: ProjectPaths, context: StudyContext) -> CVResults:
    """Rebuild cross validation results from the stored out of fold predictions."""
    oof = pd.read_parquet(paths.outputs / OOF_FILE)
    metrics = pd.read_csv(paths.tables / "cv_fold_metrics.csv")
    development = FeatureBuilder().derive(context.development)
    return CVResults(development, oof, metrics)


def clinical_rule(development: pd.DataFrame) -> pd.DataFrame:
    """Baseline B3, descriptive only: visit two blood pressure of 140/90 or above."""
    flagged = (development["sbp_v2"] >= 140) | (development["dbp_v2"] >= 90)
    y = development["lbw"].astype(bool)
    true_positive = int((flagged & y).sum())
    return pd.DataFrame(
        [
            {
                "rule": "Visit two blood pressure at or above 140/90",
                "n": len(development),
                "events": int(y.sum()),
                "flagged": int(flagged.sum()),
                "events_flagged": true_positive,
                "sensitivity": true_positive / max(int(y.sum()), 1),
                "positive_predictive_value": true_positive / max(int(flagged.sum()), 1),
            }
        ]
    )


@dataclass(frozen=True)
class ArtefactPlan:
    """Which configuration to freeze, where, and under which version and role."""

    model: str
    feature_set: FeatureSet
    subdirectory: str
    version: str
    role: str


PRIMARY_PLAN = ArtefactPlan(SERVED_MODEL, SERVED_SET, "", ARTEFACT_VERSION, "primary, served")
SECONDARY_PLAN = ArtefactPlan(
    SERVED_MODEL, SetB(), "secondary_set_b", "1.0.0+set-b", "secondary, not served by default"
)
# Frozen before the single held out evaluation so the secondary comparison (B over A)
# can be repeated there with locked models (docs/holdout_protocol.md).
COMPARATOR_PLAN = ArtefactPlan(
    SERVED_MODEL,
    SetA(),
    "comparator_set_a",
    "1.0.0+set-a",
    "comparator for the secondary comparison on the held out records, not served",
)


def freeze_artefact(
    paths: ProjectPaths, spec: StudySpec = PRIMARY, plan: ArtefactPlan = PRIMARY_PLAN
) -> FittedPipelineArtefact:
    """Fit one pre specified configuration once on all development records and save it."""
    context = load_context(paths, spec)
    results = load_results(paths, context)
    development = results.development
    experiment = Experiment(plan.model, plan.feature_set)
    fitted = NestedCVRunner(context.partition.guard(), spec).fit(development, experiment, spec.seed)
    x_train = FeatureBuilder.matrix(development, fitted.columns)
    events = int(development["lbw"].sum())
    artefact = FittedPipelineArtefact(
        version=plan.version,
        created_at=build_timestamp().isoformat(),
        data_sha256=spec.data_sha256,
        partition_sha256=context.partition.sha256,
        seed=spec.seed,
        family=plan.model,
        feature_set=plan.feature_set.name,
        feature_names=fitted.columns,
        pipeline=fitted.pipeline,
        coefficient_covariance=coefficient_covariance(fitted.pipeline, x_train),
        reference_probabilities=np.asarray(results.averaged(*experiment.key), dtype=float),
        prevalence=events / len(development),
        events=events,
        n_development=len(development),
        availability=AvailabilityScreen(spec).fit(development).availability,
        availability_threshold=spec.availability_threshold,
        spec=spec.as_dict(),
        role=plan.role,
    )
    artefact.save(paths.model / plan.subdirectory if plan.subdirectory else paths.model)
    return artefact


def freeze_classification(paths: ProjectPaths, spec: StudySpec = PRIMARY):
    """Fix the classification threshold of the served artefact from its out of fold predictions.

    Reads only development records and the stored out of fold predictions of
    the served configuration; nothing is refitted (decision D6).
    """
    from antenatal.artefact.artefact import CHECKSUM_FILE
    from antenatal.artefact.classification import derive_rule

    context = load_context(paths, spec)
    results = load_results(paths, context)
    artefact = FittedPipelineArtefact.load(paths.model, verify=True)
    sha = (paths.model / CHECKSUM_FILE).read_text().split()[0]
    source = f"{OOF_FILE}, {SERVED_MODEL} on set {SERVED_SET.name}, averaged across repeats"
    rule = derive_rule(
        results.y,
        results.averaged(SERVED_MODEL, SERVED_SET.name),
        results.groups,
        artefact.version,
        sha,
        source,
        spec,
    )
    rule.save(paths.model)
    return rule
