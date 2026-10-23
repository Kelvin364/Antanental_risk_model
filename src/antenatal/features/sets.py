"""The nested feature sets of Table 3.6.

``FeatureSet.columns`` is polymorphic: each subclass decides its columns from
the availability screen and the model family, so the cross validation runner
never branches on a set's name.

Family ``"linear"`` means a model that receives values only. The change
between visits is an exact linear combination of the two values, so it is not
entered for such a model. Family ``"tree"`` means a tree model, which cannot
form a difference by itself, so set C adds the explicit change for it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from antenatal.data.dictionary import REGISTRATION_FIELDS, VISIT_MEASUREMENTS, visit_column
from antenatal.features.builder import change_column, rate_column
from antenatal.features.screen import ScreenResult

LINEAR = "linear"
TREE = "tree"
FAMILIES = (LINEAR, TREE)


class FeatureSet(ABC):
    """A named list of columns built from the screen result and the model family."""

    name: str = ""
    description: str = ""

    @abstractmethod
    def columns(self, screen: ScreenResult, family: str) -> list[str]:
        """Return the columns of this set, in a fixed order."""

    @staticmethod
    def _check(family: str) -> None:
        if family not in FAMILIES:
            raise ValueError(f"Unknown family {family!r}; expected one of {FAMILIES}")


class SetA(FeatureSet):
    """Registration characteristics only."""

    name = "A"
    description = "Registration characteristics"

    def columns(self, screen: ScreenResult, family: str) -> list[str]:
        self._check(family)
        return [f.name for f in REGISTRATION_FIELDS]


class SetB(SetA):
    """Set A plus every visit two measurement, haemoglobin included."""

    name = "B"
    description = "Set A plus the second visit measurements"

    def columns(self, screen: ScreenResult, family: str) -> list[str]:
        return super().columns(screen, family) + [
            visit_column(m.name, 2) for m in VISIT_MEASUREMENTS
        ]


class SetC(SetB):
    """Set B plus the visit one value of every measurement that passes the screen."""

    name = "C"
    description = "Set B plus the first visit value of each screened measurement"

    def columns(self, screen: ScreenResult, family: str) -> list[str]:
        base = super().columns(screen, family)
        earlier = [visit_column(m, 1) for m in screen.passed]
        if family == TREE:
            earlier += [change_column(m) for m in screen.passed]
        return base + earlier


class SetCWithChange(SetB):
    """Parameterisation: set B plus visit one values and the change, for every family."""

    name = "C_values_and_change"
    description = "Set B plus visit one values and the change between visits"

    def columns(self, screen: ScreenResult, family: str) -> list[str]:
        base = super().columns(screen, family)
        return (
            base
            + [visit_column(m, 1) for m in screen.passed]
            + [change_column(m) for m in screen.passed]
        )


class SetCChangeOnly(SetB):
    """Parameterisation: set B plus the change between visits, no visit one values."""

    name = "C_change_only"
    description = "Set B plus the change between visits only"

    def columns(self, screen: ScreenResult, family: str) -> list[str]:
        return super().columns(screen, family) + [change_column(m) for m in screen.passed]


class SetCRate(SetC):
    """Sensitivity S5: set C plus the change per week of gestation."""

    name = "C_rate_per_week"
    description = "Set C plus the change per week of gestation"

    def columns(self, screen: ScreenResult, family: str) -> list[str]:
        rates = [rate_column(m) for m in screen.passed if m != "ga"]
        return super().columns(screen, family) + rates


class SetCWithout(SetC):
    """Ablation: set C with one visit one measurement (and its change) removed."""

    def __init__(self, dropped: str) -> None:
        self.dropped = dropped
        self.name = f"C_without_{dropped}"
        self.description = f"Set C without the visit one {dropped}"

    def columns(self, screen: ScreenResult, family: str) -> list[str]:
        removed = {visit_column(self.dropped, 1), change_column(self.dropped)}
        return [c for c in super().columns(screen, family) if c not in removed]


class SetAPlus(SetA):
    """Ablation 2.3: set A plus one visit two measurement."""

    def __init__(self, measure: str) -> None:
        self.measure = measure
        self.name = f"A_plus_{measure}"
        self.description = f"Set A plus the visit two {measure}"

    def columns(self, screen: ScreenResult, family: str) -> list[str]:
        return super().columns(screen, family) + [visit_column(self.measure, 2)]


class SetBWithout(SetB):
    """Ablation 2.3: set B without one visit two measurement."""

    def __init__(self, measure: str) -> None:
        self.measure = measure
        self.name = f"B_without_{measure}"
        self.description = f"Set B without the visit two {measure}"

    def columns(self, screen: ScreenResult, family: str) -> list[str]:
        return [c for c in super().columns(screen, family) if c != visit_column(self.measure, 2)]


class SetBExtras(SetB):
    """Experiment 2.10: set B plus the usable visit two extras of amendment 1."""

    name = "B_extras"
    description = "Set B plus the usable visit two extras"

    def columns(self, screen: ScreenResult, family: str) -> list[str]:
        from antenatal.features.extras import EXTRA_COLUMNS

        return super().columns(screen, family) + list(EXTRA_COLUMNS)


PRIMARY_SETS: tuple[FeatureSet, ...] = (SetA(), SetB(), SetC())
