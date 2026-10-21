"""Locations of inputs and outputs, all relative to the repository root."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    """Every directory the pipeline reads from or writes to."""

    root: Path

    @classmethod
    def from_root(cls, root: Path | str | None = None) -> ProjectPaths:
        """Use ``root`` when given, otherwise the current working directory."""
        return cls(Path(root).resolve() if root else Path.cwd())

    @property
    def outputs(self) -> Path:
        """Directory of every generated result."""
        return self.root / "outputs"

    @property
    def tables(self) -> Path:
        """Directory of generated CSV tables."""
        return self.outputs / "tables"

    @property
    def figures(self) -> Path:
        """Directory of generated PNG figures."""
        return self.outputs / "figures"

    @property
    def partitions(self) -> Path:
        """Directory of the sealed held out partition and the fold assignment."""
        return self.root / "partitions"

    @property
    def model(self) -> Path:
        """Directory the application loads the frozen artefact from."""
        return self.root / "webapp" / "model"

    def ensure(self) -> ProjectPaths:
        """Create the output directories when they are missing and return self."""
        for directory in (self.tables, self.figures, self.partitions):
            directory.mkdir(parents=True, exist_ok=True)
        return self
