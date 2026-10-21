"""Reading the released file read only, with its SHA 256 verified first."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from antenatal.config import PRIMARY, StudySpec


class ChecksumMismatch(RuntimeError):
    """Raised when a file does not match the SHA 256 the study was frozen on."""


def sha256_of(path: Path) -> str:
    """Return the SHA 256 hex digest of a file, read in one megabyte chunks."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class DataLoader:
    """Loads the Maternal Health Risks Stratification file (Mwifunyi et al., 2025).

    The file is opened for reading only and is never written to. ``load`` checks
    the SHA 256 before parsing so that every result is tied to one exact file.
    """

    def __init__(self, spec: StudySpec = PRIMARY, root: Path | None = None) -> None:
        self._spec = spec
        self._path = (root or Path.cwd()) / spec.data_path

    @property
    def path(self) -> Path:
        """Absolute path of the data file."""
        return self._path

    def verify_checksum(self) -> str:
        """Return the file digest; raise ``ChecksumMismatch`` if it is not the frozen one."""
        if not self._path.exists():
            raise FileNotFoundError(f"Data file not found: {self._path}. See data/README.md.")
        digest = sha256_of(self._path)
        if digest != self._spec.data_sha256:
            raise ChecksumMismatch(
                f"{self._path.name} has SHA 256 {digest}, expected {self._spec.data_sha256}"
            )
        return digest

    def load(self) -> pd.DataFrame:
        """Verify the checksum, then return the file as a data frame of raw values."""
        self.verify_checksum()
        frame = pd.read_csv(self._path, low_memory=False)
        if frame.shape != self._spec.data_shape:
            raise ValueError(f"Expected shape {self._spec.data_shape}, found {frame.shape}")
        return frame

    def provenance(self) -> dict[str, object]:
        """Return source, licence, size and checksum of the file for the manifest."""
        return {
            "dataset": "Dataset for Maternal Health Risks Stratification (MHRS) in Tanzania",
            "version": "1",
            "doi": self._spec.data_doi,
            "licence": self._spec.data_licence,
            "file": str(self._spec.data_path),
            "bytes": self._path.stat().st_size,
            "sha256": self.verify_checksum(),
            "rows": self._spec.data_shape[0],
            "columns": self._spec.data_shape[1],
        }
