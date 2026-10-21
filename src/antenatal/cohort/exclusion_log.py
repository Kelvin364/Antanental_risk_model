"""The ordered record of eligibility steps behind Table 3.5."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

import pandas as pd


@dataclass(frozen=True)
class Step:
    """One eligibility rule and its effect on the remaining records."""

    number: int
    criterion: str
    excluded: int
    remaining: int
    events_remaining: int


@dataclass
class ExclusionLog:
    """Steps in the order they were applied, starting from the full file."""

    steps: list[Step] = field(default_factory=list)

    def append(self, step: Step) -> None:
        """Add the next step; numbers must increase by one."""
        expected = len(self.steps)
        if step.number != expected:
            raise ValueError(f"Step {step.number} recorded out of order, expected {expected}")
        self.steps.append(step)

    def counts(self) -> list[int]:
        """Records remaining after each step, starting with the file size."""
        return [s.remaining for s in self.steps]

    def to_frame(self) -> pd.DataFrame:
        """Return the log as a table with one row per step."""
        return pd.DataFrame([asdict(s) for s in self.steps])
