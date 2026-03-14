"""
CLI entry point for the Linear project creator.

Usage:
    python main.py <yaml_file> [--dry-run] [--verbose] [--output <path>] [--lint-mode <mode>]

Arguments:
    yaml_file           Path to the YAML project definition file.

Options:
    --dry-run           Log what would be created without calling the Linear API.
    --verbose           Set log level to DEBUG (default: INFO).
    --output <path>     Path for the output mapping JSON file.
                        Default: linear_mapping.json in the current directory.
    --lint-mode <mode>  Work item lint behavior: enforce (default) or warn.

Exit codes:
    0  All objects created successfully (or dry-run completed successfully).
    1  Configuration error, YAML validation error, or API error.

Environment variables required (unless --dry-run):
    LINEAR_API_KEY   Linear personal or application API key.
    LINEAR_TEAM_ID   Linear team identifier (UUID).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from config import load_config
from linear_client import LinearAPIError, LinearClient
from models import ProjectModel
from project_builder import BuildStats, build_project
from work_item_linter import LintViolation, lint_project
from yaml_parser import parse_yaml


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        level=level,
        stream=sys.stderr,
    )


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CLI definition
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="linear_project_creator",
        description="Create a Linear project hierarchy from a YAML definition file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "yaml_file",
        metavar="YAML_FILE",
        help="Path to the project definition YAML file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Log what would be created without calling the Linear API.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Enable DEBUG-level logging.",
    )
    parser.add_argument(
        "--output",
        metavar="PATH",
        default="linear_mapping.json",
        help="Output path for the Linear ID mapping file (default: linear_mapping.json).",
    )
    parser.add_argument(
        "--lint-mode",
        choices=("enforce", "warn"),
        default="enforce",
        help=(
            "Work item quality lint mode: "
            "'enforce' (default) blocks execution on violations, "
            "'warn' logs violations and continues."
        ),
    )
    return parser


# ---------------------------------------------------------------------------
# Summary helpers
# ---------------------------------------------------------------------------


def _print_summary(mapping: dict, dry_run: bool) -> None:
    mode_label = " [DRY-RUN]" if dry_run else ""
    print(f"\n=== Linear Project Creator — Summary{mode_label} ===")
    print(f"  Project ID  : {mapping['project']}")
    print(f"  Milestones  : {len(mapping.get('milestones', {}))}")
    print(f"  Epics       : {len(mapping['epics'])}")
    print(f"  Stories     : {len(mapping['stories'])}")
    print(f"  Tasks       : {len(mapping['tasks'])}")

    if mapping.get("milestones"):
        print("\n  Milestones created:")
        for name, ms_id in mapping["milestones"].items():
            print(f"    {ms_id}  {name}")

    if mapping["epics"]:
        print("\n  Epics created:")
        for name, issue_id in mapping["epics"].items():
            print(f"    {issue_id}  {name}")

    print()


def _report_lint_violations(violations: list[LintViolation], lint_mode: str) -> None:
    is_warn_mode = lint_mode == "warn"
    level_fn = logger.warning if is_warn_mode else logger.error
    level_fn(
        "Work item quality check failed: %d violation(s) detected.", len(violations)
    )
    for v in violations:
        level_fn("  [%s] %s — %s", v.rule_id, v.context, v.message)
    if is_warn_mode:
        logger.warning(
            "Proceeding despite lint violations because --lint-mode=warn was specified. "
            "Revise these work items before submitting to the DevOS planning pipeline."
        )
    else:
        logger.error(
            "Revise the YAML file to satisfy the work item contract before running again. "
            "Contract reference: contracts/work_item_contract.md  "
            "Linter rules: contracts/work_item_linter_rules.md"
        )


def _write_mapping(mapping: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = output_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(mapping, indent=2), encoding="utf-8")
    tmp.replace(output_path)
    logger.info("Mapping written to %s", output_path)


def _write_run_report(
    mapping: dict,
    stats: BuildStats,
    lint_violations: list[LintViolation],
    lint_mode: str,
    yaml_source: str,
    dry_run: bool,
    output_path: Path,
) -> None:
    """
    Write a machine-readable run report JSON alongside the mapping file.

    The report captures: timestamp, input, lint results, build counts, and
    any unresolved blocks references — in a fixed, deterministic structure
    suitable for automated post-processing by DevOS agents or CI pipelines.

    The report file is written atomically (tmp → replace) like the mapping.
    Failure to write the report is logged as a warning but never aborts the run.
    """
    report = {
        "schema_version": "1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "yaml_source": yaml_source,
        "dry_run": dry_run,
        "lint": {
            "mode": lint_mode,
            "violation_count": len(lint_violations),
            "violations": [
                {"context": v.context, "rule_id": v.rule_id, "message": v.message}
                for v in lint_violations
            ],
        },
        "build": {
            "project_id": mapping.get("project", ""),
            "milestones_created": stats.milestones_created,
            "epics_created": stats.epics_created,
            "stories_created": stats.stories_created,
            "tasks_created": stats.tasks_created,
            "relations_created": stats.relations_created,
            "unresolved_blocks_count": len(stats.unresolved_blocks),
            "unresolved_blocks": stats.unresolved_blocks,
        },
    }
    report_path = output_path.with_name(output_path.stem + "_report.json")
    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = report_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(report, indent=2), encoding="utf-8")
        tmp.replace(report_path)
        logger.info("Run report written to %s", report_path)
    except OSError as exc:
        logger.warning("Could not write run report to %s: %s", report_path, exc)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    _configure_logging(args.verbose)

    output_path = Path(args.output).resolve()

    # ------------------------------------------------------------------
    # Step 1: Parse YAML input — fail fast, no API calls yet.
    # ------------------------------------------------------------------
    logger.info("Parsing input file: %s", args.yaml_file)
    try:
        project: ProjectModel = parse_yaml(args.yaml_file)
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 1
    except (ValueError, Exception) as exc:
        logger.error("YAML parse error: %s", exc)
        return 1

    logger.info(
        "Parsed: project='%s', %d epic(s).",
        project.name,
        len(project.epics),
    )

    # ------------------------------------------------------------------
    # Step 1.5: Work item quality lint — semantic validation against the
    # work item contract (contracts/work_item_linter_rules.md).
    # Runs before any API call; violations block execution in enforce mode.
    # ------------------------------------------------------------------
    logger.info("Running work item quality lint.")
    lint_violations = lint_project(project)
    if lint_violations:
        _report_lint_violations(lint_violations, lint_mode=args.lint_mode)
        if args.lint_mode == "enforce":
            return 1
    else:
        logger.info("Work item quality lint passed — no violations.")

    # ------------------------------------------------------------------
    # Step 2: Load config — required even in dry-run so the user sees
    # config errors early rather than at the end of a dry-run.
    # In dry-run, we catch the error and proceed with a None client.
    # ------------------------------------------------------------------
    client: LinearClient | None = None
    if not args.dry_run:
        try:
            config = load_config()
        except ValueError as exc:
            logger.error("Configuration error: %s", exc)
            return 1
        client = LinearClient(config)
        logger.info("Linear client initialised (team_id=%s).", config.team_id)
        team_id = config.team_id
    else:
        # Attempt to load config; if it's missing, warn but continue for dry-run.
        try:
            config = load_config()
            client = LinearClient(config)
            team_id = config.team_id
        except ValueError as exc:
            logger.warning(
                "Config incomplete (%s) — proceeding in dry-run mode without a real client.",
                exc,
            )
            team_id = "dry-run-team"
            client = None  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # Step 3: Build the project hierarchy.
    # ------------------------------------------------------------------
    logger.info("Starting project build (dry_run=%s).", args.dry_run)

    # Pass flush_path so progress is persisted after each epic even on failure.
    try:
        mapping, build_stats = build_project(
            project=project,
            client=client,  # type: ignore[arg-type]  # safe: dry_run guards API calls
            team_id=team_id,
            dry_run=args.dry_run,
            flush_path=output_path,
        )
    except LinearAPIError as exc:
        logger.error("Linear API error: %s", exc)
        logger.info(
            "Partial mapping (if any) was flushed to %s before the error.", output_path
        )
        return 1

    # ------------------------------------------------------------------
    # Step 4: Write final mapping + run report and print summary.
    # ------------------------------------------------------------------
    try:
        _write_mapping(mapping, output_path)
    except OSError as exc:
        logger.error("Could not write mapping file: %s", exc)
        return 1

    _write_run_report(
        mapping=mapping,
        stats=build_stats,
        lint_violations=lint_violations,
        lint_mode=args.lint_mode,
        yaml_source=str(Path(args.yaml_file).resolve()),
        dry_run=args.dry_run,
        output_path=output_path,
    )

    _print_summary(mapping, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
