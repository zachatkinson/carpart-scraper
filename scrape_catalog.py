"""Scrape CSF MyCarParts catalog data (hierarchy + applications).

This script builds the vehicle hierarchy and fetches application pages to create
the base catalog without images. This is the first step in a modular scraping pipeline.

Outputs:
- exports/parts.json - All parts with basic info (no images)
- exports/compatibility.json - Vehicle compatibility data

Exit codes:
- 0: Success (all pages scraped or acceptable failure rate)
- 1: Hard failure (exception, Ctrl-C)
- 2: Excessive failure rate (>5% of pages failed)

Usage:
    python scrape_catalog.py
    python scrape_catalog.py --make Nissan
    python scrape_catalog.py --year 2023
    python scrape_catalog.py --output-dir my_exports/
"""

import sys
from pathlib import Path
from typing import Any

import click
import structlog

from src.scraper.orchestrator import ScraperOrchestrator

logger = structlog.get_logger()

# Exit codes
EXIT_SUCCESS = 0
EXIT_HARD_FAILURE = 1
EXIT_EXCESSIVE_FAILURES = 2

# Maximum acceptable failure rate (5%)
MAX_FAILURE_RATE = 0.05


def _print_failure_summary(stats: dict[str, Any]) -> None:
    """Print human-readable failure summary to stdout.

    Args:
        stats: Statistics dict from scrape_all()
    """
    failure_summary = stats.get("failure_summary", {})
    total_failures = failure_summary.get("total_failures", 0)

    if total_failures == 0:
        print("  Failures:        0 (clean run)")
        return

    by_phase = failure_summary.get("by_phase", {})
    retryable = failure_summary.get("retryable", 0)
    permanent = failure_summary.get("permanent", 0)

    print(f"  Total Failures:  {total_failures}")
    for phase, count in sorted(by_phase.items()):
        print(f"    - {phase}: {count}")
    print(f"    Retryable:     {retryable}")
    print(f"    Permanent:     {permanent}")


def _determine_exit_code(stats: dict[str, Any]) -> int:
    """Determine CI exit code based on failure rate.

    Args:
        stats: Statistics dict from scrape_all()

    Returns:
        Exit code (0 = success, 2 = excessive failures)
    """
    total_applications = stats.get("total_applications", 0)
    applications_failed = stats.get("applications_failed", 0)

    if total_applications == 0:
        return EXIT_SUCCESS

    failure_rate = applications_failed / total_applications

    if failure_rate > MAX_FAILURE_RATE:
        logger.warning(
            "excessive_failure_rate",
            failure_rate=f"{failure_rate:.1%}",
            threshold=f"{MAX_FAILURE_RATE:.0%}",
            applications_failed=applications_failed,
            total_applications=total_applications,
        )
        return EXIT_EXCESSIVE_FAILURES

    return EXIT_SUCCESS


def _run_scrape(  # noqa: PLR0913
    make: str | None,
    year: int | None,
    output_dir: str,
    output_path: Path,
    incremental: bool = False,
    check_changes: bool = False,
    resume: bool = False,
    fetch_details: bool = False,
) -> None:
    """Run the scraping workflow within a context manager.

    Args:
        make: Make filter
        year: Year filter
        output_dir: Output directory string
        output_path: Output directory Path
        incremental: Load previous export as baseline, only process changes
        check_changes: Check hierarchy fingerprint before scraping
        resume: Resume from latest checkpoint
        fetch_details: Fetch detail pages for parts
    """
    with ScraperOrchestrator(
        output_dir=output_path,
        checkpoint_dir=Path("checkpoints"),
        delay_override=None,
        incremental=incremental,
    ) as orchestrator:
        logger.info("catalog_scrape_started", make=make, year=year, output_dir=output_dir)

        stats = orchestrator.scrape_all(
            make_filter=make,
            year_filter=year,
            resume=resume,
            check_changes=check_changes,
            fetch_details=fetch_details,
            fetch_details_new_only=True,
        )

        orchestrator.export_data()
        orchestrator.generate_completeness_report()

        logger.info("catalog_scrape_completed", output_dir=output_dir, **stats)

        _print_results(stats, output_path)

        exit_code = _determine_exit_code(stats)
        if exit_code == EXIT_EXCESSIVE_FAILURES:
            failed = stats["applications_failed"]
            total = stats["total_applications"]
            print(
                f"\nWARNING: Excessive failure rate ({failed}/{total} apps failed). "
                f"Exit code: {EXIT_EXCESSIVE_FAILURES}"
            )
        sys.exit(exit_code)


def _print_results(stats: dict[str, Any], output_path: Path) -> None:
    """Print scrape results summary.

    Args:
        stats: Statistics dict from scrape_all()
        output_path: Output directory Path
    """
    print("\n" + "=" * 60)
    print("Catalog Scrape Complete!")
    print("=" * 60)
    print(f"  Unique Parts:    {stats['unique_parts']}")
    print(f"  New Parts:       {stats.get('new_parts', 0)}")
    print(f"  Changed Parts:   {stats.get('changed_parts', 0)}")
    print(f"  Apps Processed:  {stats['applications_processed']}")
    print(f"  Apps Failed:     {stats['applications_failed']}")
    _print_failure_summary(stats)
    print("  Output files:")
    print(f"    {output_path / 'parts.json'}")
    print(f"    {output_path / 'compatibility.json'}")
    print()
    print("Next step:")
    print("  python enrich_images.py  # Add images to parts.json")
    print("=" * 60 + "\n")


@click.command()
@click.option(
    "--make",
    type=str,
    default=None,
    help="Filter by specific make (e.g., 'Nissan')",
)
@click.option(
    "--year",
    type=int,
    default=None,
    help="Filter by specific year (e.g., 2023)",
)
@click.option(
    "--output-dir",
    type=click.Path(),
    default="exports",
    help="Output directory for JSON files (default: exports/)",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Enable verbose logging",
)
@click.option(
    "--incremental",
    is_flag=True,
    help="Load previous export as baseline, only process changes",
)
@click.option(
    "--check-changes",
    is_flag=True,
    help="Check hierarchy fingerprint before scraping",
)
@click.option(
    "--resume",
    is_flag=True,
    help="Resume from latest checkpoint",
)
@click.option(
    "--fetch-details",
    is_flag=True,
    help="Fetch detail pages for parts",
)
def main(  # noqa: PLR0913
    make: str | None,
    year: int | None,
    output_dir: str,
    verbose: bool,  # noqa: ARG001
    incremental: bool,
    check_changes: bool,
    resume: bool,
    fetch_details: bool,
) -> None:
    """Scrape CSF MyCarParts catalog (hierarchy + applications only).

    This builds the vehicle hierarchy and fetches application pages to create
    parts.json and compatibility.json WITHOUT images. Images can be added later
    using enrich_images.py.

    Examples:
        python scrape_catalog.py
        python scrape_catalog.py --make Nissan
        python scrape_catalog.py --year 2023
        python scrape_catalog.py --output-dir my_exports/
        python scrape_catalog.py --make Tesla --incremental
    """
    print("\n" + "=" * 60)
    print("CSF MyCarParts Catalog Scraper")
    print("Building vehicle hierarchy + fetching applications")
    print("=" * 60 + "\n")

    if make:
        print(f"  Make Filter:     {make}")
    else:
        print("  Make Filter:     All makes")

    if year:
        print(f"  Year Filter:     {year}")
    else:
        print("  Year Filter:     All years")

    print(f"  Output Dir:      {output_dir}")
    print(f"  Incremental:     {'Yes' if incremental else 'No'}")
    print(f"  Fetch Details:   {'Yes' if fetch_details else 'No'}")
    print(f"  Resume:          {'Yes' if resume else 'No'}")
    print()

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        _run_scrape(
            make,
            year,
            output_dir,
            output_path,
            incremental=incremental,
            check_changes=check_changes,
            resume=resume,
            fetch_details=fetch_details,
        )

    except KeyboardInterrupt:
        logger.warning("catalog_scrape_interrupted")
        print("\nScrape interrupted by user")
        sys.exit(EXIT_HARD_FAILURE)
    except SystemExit:
        raise
    except Exception as e:
        logger.exception("catalog_scrape_failed", error=str(e))
        print(f"\nError: {e}")
        sys.exit(EXIT_HARD_FAILURE)


if __name__ == "__main__":
    main()
