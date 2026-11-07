"""Seal the new test set: a seeded draw over registration groups, reading no outcome.

The old held out partition is found by subtraction (analysis cohort minus development
records), so ``partitions/holdout_ids.csv`` is never opened. Run once; it refuses to rerun.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SEALED = Path(__file__).resolve().parent / "sealed"
SEED = 20261107
MANIFEST_COLUMNS = ["record_id", "group_key_hash", "eligible", "in_analysis_cohort"]


def main() -> None:
    target = SEALED / "test_ids.csv"
    if target.exists():
        raise SystemExit("The test set is already sealed.")
    manifest = pd.read_csv(ROOT / "outputs/cohort_manifest.csv", usecols=MANIFEST_COLUMNS)
    predictions = pd.read_parquet(ROOT / "outputs/oof_predictions.parquet", columns=["record_id"])
    study_development = set(predictions["record_id"].unique())
    in_development = manifest["record_id"].isin(study_development)
    old_held_out = manifest["in_analysis_cohort"] & ~in_development
    blocked_groups = set(manifest.loc[old_held_out, "group_key_hash"])
    quarantine = manifest["group_key_hash"].isin(blocked_groups)
    development_groups = set(manifest.loc[in_development, "group_key_hash"])

    remaining = manifest[manifest["eligible"] & ~in_development & ~quarantine]
    free = remaining[~remaining["group_key_hash"].isin(development_groups)]
    groups = np.sort(free["group_key_hash"].unique())
    drawn = np.random.default_rng(SEED).permutation(groups)[: len(groups) // 2]
    test = free[free["group_key_hash"].isin(set(drawn))]["record_id"].sort_values()
    pool = sorted(study_development | (set(remaining["record_id"]) - set(test)))

    test.to_csv(target, index=False)
    pd.Series(pool, name="record_id").to_csv(SEALED / "development_ids.csv", index=False)
    quarantined = manifest.loc[quarantine, "record_id"].sort_values()
    quarantined.to_csv(SEALED / "quarantine_ids.csv", index=False)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    (SEALED / "test_ids.sha256").write_text(digest + "\n")
    print(f"test {len(test)}, development pool {len(pool)}, quarantine {len(quarantined)}")
    print(f"sha256 {digest}")


if __name__ == "__main__":
    main()
