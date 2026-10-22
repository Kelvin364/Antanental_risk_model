"""The frozen study specification.

Every constant used anywhere in the analysis, the application or the tests is
defined once here. The values follow Tables 3.4 to 3.8 of the proposal. A
sensitivity analysis is expressed as a copy of the primary specification with
one field changed, through ``StudySpec.variant``.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Range:
    """An inclusive numeric range used to accept or reject one value."""

    low: float
    high: float

    def contains(self, value: float) -> bool:
        """Return True when ``value`` lies inside the range, ends included."""
        return self.low <= value <= self.high


@dataclass(frozen=True)
class PhysiologicalRanges:
    """Range rules of Section 3.3.3. Values outside a range become missing."""

    sbp: Range = Range(60, 250)
    dbp: Range = Range(30, 160)
    hb: Range = Range(3, 20)
    weight: Range = Range(30, 150)
    ga: Range = Range(1, 45)
    age: Range = Range(12, 55)
    height: Range = Range(120, 200)
    gravidity: Range = Range(0, 20)
    prior_deliveries: Range = Range(0, 15)
    # Pulse was not in the proposal's range rules. It is added here and is being added to
    # Section 3.3.3: 30 to 200 beats per minute, the range the earlier prototype enforced.
    pulse: Range = Range(30, 200)

    def get(self, name: str) -> Range:
        """Return the range called ``name``; raise KeyError when it is unknown."""
        if name not in {f.name for f in dataclasses.fields(self)}:
            raise KeyError(name)
        return getattr(self, name)


SENTINEL_TOKENS: frozenset[str] = frozenset(
    {
        "",
        "invalid",
        "n/r",
        "na",
        "nil",
        "no",
        "none",
        "not applicable",
        "not applied",
        "not checked",
        "not checkedt",
        "not measured",
        "not taken",
        "not tested",
        "not_checked",
        "unknown",
        "nan",
    }
)


LIMITATION = (
    "Research estimate from a study on one Tanzanian dataset. Not validated for any pregnancy. "
    "Not a clinical risk category and not a recommendation for care."
)
"""The fixed limitation line shown on every interface screen and every figure (R7)."""


@dataclass(frozen=True)
class StudySpec:
    """Frozen specification of the study (Table 3.4 and Sections 3.3.2 to 3.3.9)."""

    name: str = "primary"
    data_path: Path = Path("data/maternal_dataset_csv.csv")
    data_sha256: str = "ab95366ef22dde5d13df93f10723942f5faffda8fbf0007e8efe85e4f25c1126"
    data_shape: tuple[int, int] = (8817, 683)
    data_doi: str = "10.5281/zenodo.15309733"
    data_licence: str = "CC BY 4.0"
    record_id: str = "SN"
    outcome_column: str = "newborn_birth_weight_kg_"
    lbw_threshold: float = 2.5
    weight_bounds: tuple[float, float] = (1.0, 6.0)
    gestational_cutoff: int = 28
    sensitivity_cutoffs: tuple[int, int] = (24, 32)
    exclude_term_and_preterm: bool = False
    ranges: PhysiologicalRanges = field(default_factory=PhysiologicalRanges)
    sentinel_tokens: frozenset[str] = SENTINEL_TOKENS
    availability_threshold: float = 0.60
    seed: int = 20260930
    holdout_fraction: float = 0.20
    outer_folds: int = 5
    repeats: int = 10
    inner_folds: int = 3
    bootstrap_resamples: int = 2000
    group_key_columns: tuple[str, ...] = (
        "age",
        "last_normal_menustration_date",
        "height_cm",
        "weight_kg",
        "number_of_prior_deliveries",
    )

    @property
    def holdout_splits(self) -> int:
        """Number of grouped folds whose first fold forms the held out partition."""
        return round(1 / self.holdout_fraction)

    def variant(self, name: str, **changes: object) -> StudySpec:
        """Return a copy of this specification with a new name and some fields changed."""
        return dataclasses.replace(self, name=name, **changes)

    def as_dict(self) -> dict[str, object]:
        """Return a JSON friendly dictionary of every field."""
        out = dataclasses.asdict(self)
        out["data_path"] = str(self.data_path)
        out["sentinel_tokens"] = sorted(self.sentinel_tokens)
        return out


PRIMARY = StudySpec()


def sensitivity_specs(base: StudySpec = PRIMARY) -> dict[str, StudySpec]:
    """Cohort level sensitivity analyses of Table 3.8 that change the cohort rule.

    S4 (complete measurements) and S5 (rate per week) keep the primary cohort and
    change the feature construction, so they are defined in the features package.
    """
    early, late = base.sensitivity_cutoffs
    return {
        "S1": base.variant("S1", gestational_cutoff=early),
        "S2": base.variant("S2", gestational_cutoff=late),
        "S3": base.variant("S3", exclude_term_and_preterm=True),
        "S6": base.variant("S6", weight_bounds=(0.5, base.weight_bounds[1])),
    }
