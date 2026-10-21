"""Pre specified sensitivity analyses S1 to S6 (Table 3.8).

S1, S2, S3 and S6 change the cohort rule. Their development records are the
variant cohort minus every record in the primary sealed held out partition,
so the held out records stay unseen. Each variant gets its own grouped outer
folds with the study seed. S4 restricts the primary development records to
those with every screened measurement at both visits. S5 adds the change per
week of gestation to set C. Every analysis repeats the primary comparison
(C against B on precision recall) and the secondary one (B against A on ROC).
"""

from __future__ import annotations

import pandas as pd

from antenatal.cohort.builder import CohortBuilder
from antenatal.cohort.partition import Partition, grouped_outer_folds
from antenatal.config import PRIMARY, StudySpec, sensitivity_specs
from antenatal.data.dictionary import visit_column
from antenatal.evaluation.comparisons import Comparison, ComparisonRunner
from antenatal.evaluation.nested_cv import Experiment, NestedCVRunner
from antenatal.features.screen import AvailabilityScreen
from antenatal.features.sets import PRIMARY_SETS, SetCRate

MODEL = "logistic_l2"
DESCRIPTIONS = {
    "S1": "Visit two by 24 weeks",
    "S2": "Visit two by 32 weeks",
    "S3": "Excluding records marked both term and preterm",
    "S4": "Every screened measurement recorded at both visits",
    "S5": "Rate of change per week added to set C",
    "S6": "Lower birth weight bound relaxed to 0.5 kg",
}


def _comparisons(new_c: str = "C") -> list[Comparison]:
    return [
        Comparison(f"{new_c} over B", (MODEL, new_c), (MODEL, "B"), "pr_auc", "primary"),
        Comparison("B over A", (MODEL, "B"), (MODEL, "A"), "roc_auc", "secondary"),
    ]


class SensitivityRunner:
    """Runs every sensitivity analysis and returns one table."""

    def __init__(self, raw: pd.DataFrame, partition: Partition, spec: StudySpec = PRIMARY) -> None:
        self._raw = raw
        self._partition = partition
        self._spec = spec
        self._runner = NestedCVRunner(spec)

    def _evaluate(
        self, name: str, development: pd.DataFrame, experiments, comparisons
    ) -> pd.DataFrame:
        folds = grouped_outer_folds(development, self._spec)
        results = self._runner.run(development, folds, experiments)
        table = ComparisonRunner(results, self._spec).run(comparisons, analysis=name)
        table.insert(1, "specification", DESCRIPTIONS[name])
        return table

    def cohort_variant(self, name: str, spec: StudySpec) -> pd.DataFrame:
        """S1, S2, S3 or S6: a changed cohort rule, held out records removed."""
        cohort = CohortBuilder(spec).build(self._raw)
        development = self._partition.development(cohort)
        experiments = [Experiment(MODEL, s) for s in PRIMARY_SETS]
        return self._evaluate(name, development, experiments, _comparisons())

    def complete_measurements(self, development: pd.DataFrame) -> pd.DataFrame:
        """S4: development records with every screened measurement at both visits."""
        screen = AvailabilityScreen(self._spec).fit(development)
        mask = pd.Series(True, index=development.index)
        for name in screen.passed:
            mask &= development[visit_column(name, 1)].notna()
            mask &= development[visit_column(name, 2)].notna()
        subset = development[mask].reset_index(drop=True)
        experiments = [Experiment(MODEL, s) for s in PRIMARY_SETS]
        return self._evaluate("S4", subset, experiments, _comparisons())

    def rate_per_week(self, development: pd.DataFrame) -> pd.DataFrame:
        """S5: set C plus the change per week, against set B."""
        experiments = [Experiment(MODEL, s) for s in (*PRIMARY_SETS, SetCRate())]
        return self._evaluate("S5", development, experiments, _comparisons(SetCRate.name))

    def run_all(self, development: pd.DataFrame) -> pd.DataFrame:
        """Every analysis of Table 3.8 except the primary, in order."""
        variants = sensitivity_specs(self._spec)
        tables = [
            self.cohort_variant("S1", variants["S1"]),
            self.cohort_variant("S2", variants["S2"]),
            self.cohort_variant("S3", variants["S3"]),
            self.complete_measurements(development),
            self.rate_per_week(development),
            self.cohort_variant("S6", variants["S6"]),
        ]
        return pd.concat(tables, ignore_index=True)
