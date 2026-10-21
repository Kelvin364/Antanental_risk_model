"""The run manifest: inputs, environment, seed and a checksum for every output (R4, R13)."""

from __future__ import annotations

import json
import platform
import subprocess
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

from antenatal.cohort.partition import HOLDOUT_CHECKSUM
from antenatal.config import StudySpec
from antenatal.data.loader import sha256_of
from antenatal.paths import ProjectPaths

LIBRARIES = ("numpy", "pandas", "scipy", "scikit-learn", "joblib", "matplotlib", "pyarrow")


def library_versions() -> dict[str, str]:
    """Python and library versions of the running environment."""
    versions = {"python": platform.python_version()}
    versions.update({name: version(name) for name in LIBRARIES})
    return versions


def git_commit(root: Path) -> str | None:
    """Commit hash of the repository, or None outside a git checkout."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def write_manifest(paths: ProjectPaths, spec: StudySpec, extra: dict[str, object]) -> Path:
    """Write outputs/manifest.json describing the inputs and every file under outputs."""
    outputs = sorted(
        p for p in paths.outputs.rglob("*") if p.is_file() and p.name != "manifest.json"
    )
    manifest = {
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_commit": git_commit(paths.root),
        "seed": spec.seed,
        "environment": library_versions(),
        "inputs": {
            "data": {"path": str(spec.data_path), "sha256": sha256_of(paths.root / spec.data_path)},
            "holdout_sha256_record": (paths.partitions / HOLDOUT_CHECKSUM).read_text().split()[0],
            "folds": sha256_of(paths.partitions / "folds.parquet"),
        },
        "spec": spec.as_dict(),
        "outputs": {str(p.relative_to(paths.root)): sha256_of(p) for p in outputs},
        **extra,
    }
    path = paths.outputs / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2, default=str))
    return path
