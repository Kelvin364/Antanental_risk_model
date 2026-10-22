"""Command line entry point: ``python -m antenatal <command>``.

Commands run in this order: ``derive-cohort``, ``seal-partition``,
``run-analysis``, ``run-extensions``, ``freeze-artefact``,
``freeze-secondary-artefact``, ``summarise-results``. ``run-all`` runs them in
sequence. The single held out evaluation is never part of ``run-all``.
Every path is relative to the repository root, which defaults to the current
directory and can be changed with ``--root``.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable

import pandas as pd

from antenatal.cohort.builder import CohortBuilder
from antenatal.cohort.partition import PartitionWriter
from antenatal.config import PRIMARY, sensitivity_specs
from antenatal.data.loader import DataLoader
from antenatal.paths import ProjectPaths


def derive_cohort(paths: ProjectPaths) -> None:
    """Build the cohort, write the per record manifest, the flow table and sensitivity counts."""
    raw = DataLoader(PRIMARY, paths.root).load()
    cohort = CohortBuilder(PRIMARY).build(raw)
    cohort.manifest().to_csv(paths.outputs / "cohort_manifest.csv", index=False)
    cohort.flow_table().to_csv(paths.tables / "cohort_flow.csv", index=False)
    rows = [{"analysis": "Primary", "cohort": len(cohort.analysis), "events": cohort.events}]
    for name, spec in sensitivity_specs().items():
        variant = CohortBuilder(spec).build(raw)
        rows.append({"analysis": name, "cohort": len(variant.analysis), "events": variant.events})
    table = pd.DataFrame(rows)
    table["prevalence_percent"] = (100 * table["events"] / table["cohort"]).round(2)
    table.to_csv(paths.tables / "sensitivity_cohorts.csv", index=False)
    print(cohort.flow_table().to_string(index=False))


def seal_partition(paths: ProjectPaths) -> None:
    """Seal the held out partition, then write the outer folds on development records."""
    raw = DataLoader(PRIMARY, paths.root).load()
    cohort = CohortBuilder(PRIMARY).build(raw)
    writer = PartitionWriter(paths.partitions, PRIMARY)
    partition = writer.load() if writer.holdout_path.exists() else writer.seal_holdout(cohort)
    development = partition.development(cohort)
    writer.write_folds(writer.outer_folds(development))
    print(
        f"Development {len(development)} records, {int(development['lbw'].sum())} events; "
        f"held out {partition.holdout_size} records sealed with SHA 256 {partition.sha256}"
    )


def run_analysis(paths: ProjectPaths) -> None:
    """Nested cross validation and every development table and figure."""
    from antenatal.analysis import run_analysis as run

    run(paths, PRIMARY)


def run_extensions(paths: ProjectPaths) -> None:
    """Stage 5 analyses on development records."""
    from antenatal.extensions import run_extensions as run

    run(paths, PRIMARY)


def freeze_artefact(paths: ProjectPaths) -> None:
    """Fit the served configuration on development records and save the artefact."""
    from antenatal.study import freeze_artefact as freeze

    artefact = freeze(paths, PRIMARY)
    print(
        f"Artefact {artefact.version}: {artefact.family} on set {artefact.feature_set}, "
        f"{len(artefact.feature_names)} features, saved to {paths.model}"
    )


def freeze_secondary_artefact(paths: ProjectPaths) -> None:
    """Fit the pre specified secondary configuration (set B) and save it beside the primary."""
    from antenatal.study import SECONDARY_PLAN
    from antenatal.study import freeze_artefact as freeze

    artefact = freeze(paths, PRIMARY, SECONDARY_PLAN)
    print(
        f"Secondary artefact {artefact.version}: set {artefact.feature_set}, not served by default"
    )


def summarise_results(paths: ProjectPaths) -> None:
    """Collect every headline number, with its source file, into results_summary.csv."""
    from antenatal.reporting.results_summary import build_results_summary

    print(build_results_summary(paths).to_string(index=False))


def meeting_evidence(paths: ProjectPaths) -> None:
    """Write docs/meeting_evidence.md from the output tables."""
    from antenatal.reporting.meeting_evidence import write_meeting_evidence

    write_meeting_evidence(paths)
    print("Wrote docs/meeting_evidence.md")


def update_readme(paths: ProjectPaths) -> None:
    """Refresh the generated results and structure blocks of README.md."""
    from antenatal.reporting.readme import update_readme as update

    update(paths)
    print("Updated README.md")


def technical_report(paths: ProjectPaths) -> None:
    """Write docs/Technical-Report.md from the outputs and the evidence files."""
    from antenatal.reporting.technical_report import write_technical_report

    print(f"Wrote {write_technical_report(paths)}")


def draw_figures(paths: ProjectPaths) -> None:
    """Redraw every figure from the saved tables, with the limitation footer."""
    from antenatal.reporting.redraw import redraw_all

    print(f"Redrew {len(redraw_all(paths))} figures")


def _commands() -> dict[str, Callable[[ProjectPaths], None]]:
    return {
        "derive-cohort": derive_cohort,
        "seal-partition": seal_partition,
        "run-analysis": run_analysis,
        "run-extensions": run_extensions,
        "freeze-artefact": freeze_artefact,
        "freeze-secondary-artefact": freeze_secondary_artefact,
        "summarise-results": summarise_results,
        "draw-figures": draw_figures,
        "meeting-evidence": meeting_evidence,
        "update-readme": update_readme,
        "technical-report": technical_report,
    }


def main(argv: list[str] | None = None) -> None:
    """Parse arguments and run one command."""
    commands = _commands()
    parser = argparse.ArgumentParser(prog="antenatal", description=__doc__)
    parser.add_argument("command", choices=[*commands, "run-all"])
    parser.add_argument("--root", default=None, help="repository root (default: current directory)")
    args = parser.parse_args(argv)
    paths = ProjectPaths.from_root(args.root).ensure()
    selected = list(commands) if args.command == "run-all" else [args.command]
    for name in selected:
        commands[name](paths)


if __name__ == "__main__":
    main()
