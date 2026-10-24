"""The single held out evaluation (guideline version 2, Stage 4.3; docs/holdout_protocol.md).

Usage, only after the supervisor has approved:
``python scripts/run_holdout.py --approval "supervisor approved on 23 October, run the holdout on
artefact 1.0.0" --operator NAME``

The approval must be the exact sentence. The script loads the locked candidate (set C,
artefact 1.0.0), the frozen comparators (set B and set A) and the classification
threshold, verifies every checksum, and calls ``HoldoutEvaluator.evaluate_once`` once.
Results go to ``outputs/tables/holdout_result.csv``, ``holdout_comparisons.csv`` and
``holdout_classification.csv`` and
``holdout_net_benefit.csv``; the access log records the operator, purpose, commit,
checksums and result path. A second run is refused.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPROVAL = "supervisor approved on 23 October, run the holdout on artefact 1.0.0"
PURPOSE = "single confirmatory check of the locked candidate and the prespecified comparisons"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--approval", required=True, help="the exact approval sentence")
    parser.add_argument("--operator", required=True, help="who runs the evaluation")
    args = parser.parse_args(argv)
    if args.approval.strip() != APPROVAL:
        print(f"Refused: the approval must read exactly: {APPROVAL}")
        return 2
    sys.path.insert(0, str(ROOT / "src"))
    from antenatal.artefact.artefact import CHECKSUM_FILE, FittedPipelineArtefact
    from antenatal.artefact.classification import ClassificationRule
    from antenatal.evaluation.holdout import HoldoutEvaluator, LockedModel
    from antenatal.paths import ProjectPaths
    from antenatal.study import load_context

    paths = ProjectPaths.from_root(ROOT)
    models = []
    for name, directory in (
        ("C", paths.model),
        ("B", paths.model / "secondary_set_b"),
        ("A", paths.model / "comparator_set_a"),
    ):
        sha = (directory / CHECKSUM_FILE).read_text().split()[0]
        models.append(LockedModel(name, FittedPipelineArtefact.load(directory, verify=True), sha))
    rule = ClassificationRule.load(paths.model, models[0].sha256)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True
    ).stdout.strip()
    provenance = f"operator {args.operator}; purpose {PURPOSE}; commit {commit}"
    tables = HoldoutEvaluator(paths.partitions).evaluate_once(
        models,
        load_context(paths).cohort,
        paths.tables,
        confirm_supervisor_reviewed=True,
        rule=rule,
        provenance=provenance,
    )
    for name, table in tables.items():
        print(f"\n{name}\n{table.to_string(index=False)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
