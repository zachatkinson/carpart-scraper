"""Unified CSF MyCarParts scraper orchestrator.

This script orchestrates the modular scraping pipeline,
allowing you to run:
1. Catalog scraping (hierarchy + applications)
   -> parts.json, compatibility.json
2. Detail enrichment (full descriptions, specs, tech notes,
   interchange, images) -> parts_with_details.json

You can run either phase independently or both sequentially.

Examples:
    # Full scrape (catalog + details)
    python run_scrape.py --catalog --details

    # Catalog only
    python run_scrape.py --catalog

    # Details only (requires existing parts.json)
    python run_scrape.py --details

    # Catalog with filters
    python run_scrape.py --catalog --make Nissan --year 2023

    # Full scrape with custom output directory
    python run_scrape.py --catalog --details --output-dir my_exports/

    # Target specific SKUs for detail enrichment
    python run_scrape.py --details --skus CSF-3680,CSF-3981,CSF-10535

    # Target SKUs from file for detail enrichment
    python run_scrape.py --details --skus-file changed_skus.txt

    # Force re-enrichment of all parts (even if already enriched)
    python run_scrape.py --details --force
"""

import json
import subprocess
import sys
from pathlib import Path

import click
import httpx
import structlog

logger = structlog.get_logger()

SEPARATOR_WIDTH = 60
HTTP_OK = 200


def _print_config(
    catalog: bool,
    details: bool,
    make: str | None,
    year: int | None,
    output_dir: str,
) -> None:
    """Print configuration summary at start of run."""
    if catalog and details:
        phases = "Catalog + Details"
    elif catalog:
        phases = "Catalog"
    else:
        phases = "Details"

    print("\n" + "=" * SEPARATOR_WIDTH)
    print("CSF MyCarParts Unified Scraper")
    print("=" * SEPARATOR_WIDTH)
    print(f"  Phases:          {phases}")
    if make:
        print(f"  Make Filter:     {make}")
    if year:
        print(f"  Year Filter:     {year}")
    print(f"  Output Dir:      {output_dir}")
    print("=" * SEPARATOR_WIDTH + "\n")


def _run_catalog_phase(
    output_dir: str,
    output_path: Path,
    make: str | None,
    year: int | None,
    verbose: bool,
) -> None:
    """Run Phase 1: Catalog scraping."""
    logger.info("phase_catalog_starting")
    print("\n" + "=" * SEPARATOR_WIDTH)
    print("PHASE 1: CATALOG SCRAPING")
    print("Building vehicle hierarchy + fetching applications")
    print("=" * SEPARATOR_WIDTH + "\n")

    cmd = [
        sys.executable,
        "scrape_catalog.py",
        "--output-dir",
        output_dir,
    ]
    if make:
        cmd.extend(["--make", make])
    if year:
        cmd.extend(["--year", str(year)])
    if verbose:
        cmd.append("--verbose")

    try:
        # Commands built from trusted CLI inputs
        subprocess.run(cmd, check=True)  # noqa: S603
        logger.info("phase_catalog_completed")
    except subprocess.CalledProcessError as e:
        logger.exception("phase_catalog_failed", error=str(e))
        print(f"\nCatalog scraping failed with exit code {e.returncode}")
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        logger.warning("phase_catalog_interrupted")
        print("\nCatalog scraping interrupted by user")
        sys.exit(1)

    parts_file = output_path / "parts.json"
    compatibility_file = output_path / "compatibility.json"

    if not parts_file.exists():
        logger.exception("catalog_output_missing", file=str(parts_file))
        print(f"\nExpected output file not found: {parts_file}")
        sys.exit(1)

    print("\nCatalog scraping completed:")
    print(f"   {parts_file}")
    print(f"   {compatibility_file}")


def _run_details_phase(
    output_path: Path,
    verbose: bool,
    skus: str | None,
    skus_file: str | None,
    force: bool,
) -> None:
    """Run Phase 2: Detail enrichment."""
    logger.info("phase_details_starting")
    print("\n" + "=" * SEPARATOR_WIDTH)
    print("PHASE 2: DETAIL PAGE ENRICHMENT")
    print("Fetching detail pages for complete product data")
    print("(descriptions, specs, tech notes, interchange, images)")
    print("=" * SEPARATOR_WIDTH + "\n")

    parts_file = output_path / "parts.json"
    if not parts_file.exists():
        logger.exception("parts_json_missing", file=str(parts_file))
        print(f"\nRequired input file not found: {parts_file}")
        print("   Run with --catalog first to generate parts.json")
        sys.exit(1)

    cmd = [sys.executable, "enrich_details.py"]
    if verbose:
        cmd.append("--verbose")
    if skus:
        cmd.extend(["--skus", skus])
    if skus_file:
        cmd.extend(["--skus-file", skus_file])
    if force:
        cmd.append("--force")

    try:
        # Commands built from trusted CLI inputs
        subprocess.run(cmd, check=True)  # noqa: S603
        logger.info("phase_details_completed")
    except subprocess.CalledProcessError as e:
        logger.exception("phase_details_failed", error=str(e))
        print(f"\nDetail enrichment failed with exit code {e.returncode}")
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        logger.warning("phase_details_interrupted")
        print("\nDetail enrichment interrupted by user")
        sys.exit(1)

    enriched_file = output_path / "parts_with_details.json"
    if not enriched_file.exists():
        logger.exception("enriched_output_missing", file=str(enriched_file))
        print(f"\nExpected output file not found: {enriched_file}")
        sys.exit(1)

    print("\nDetail enrichment completed:")
    print(f"   {enriched_file}")


def _run_merge_phase(output_path: Path) -> None:
    """Run Phase 3: Auto-merge compatibility data."""
    logger.info("phase_merge_starting")
    print("\n" + "=" * SEPARATOR_WIDTH)
    print("PHASE 3: AUTO-MERGE COMPATIBILITY DATA")
    print("Merging parts_with_details.json + compatibility.json")
    print("=" * SEPARATOR_WIDTH + "\n")

    parts_with_details_file = output_path / "parts_with_details.json"
    compatibility_file = output_path / "compatibility.json"
    complete_file = output_path / "parts_complete.json"

    try:
        with parts_with_details_file.open() as f:
            parts_data = json.load(f)

        with compatibility_file.open() as f:
            compat_data = json.load(f)

        compat_map = {
            record["part_sku"]: record["vehicles"] for record in compat_data["compatibility"]
        }

        merged_count = 0
        for part in parts_data["parts"]:
            sku = part["sku"]
            if sku in compat_map:
                part["compatibility"] = compat_map[sku]
                merged_count += 1

        with complete_file.open("w") as f:
            json.dump(parts_data, f, indent=2)

        print(f"Merged compatibility data for {merged_count} parts")
        print(f"   Output: {complete_file}")

        logger.info("phase_merge_completed", merged_count=merged_count)

    except Exception as e:
        logger.exception("phase_merge_failed", error=str(e))
        print(f"\nAuto-merge failed: {e}")
        print("   You can manually merge using compatibility.json")


def _run_push_phase(
    output_path: Path,
    wp_url: str | None,
    wp_api_key: str | None,
) -> None:
    """Run Phase 4: Push to WordPress."""
    logger.info("phase_push_starting")
    print("\n" + "=" * SEPARATOR_WIDTH)
    print("PHASE 4: PUSH TO WORDPRESS")
    print("Sending data to WordPress via Push API")
    print("=" * SEPARATOR_WIDTH + "\n")

    if not wp_url or not wp_api_key:
        print(
            "--push requires --wp-url and --wp-api-key (or CSF_WP_URL and CSF_WP_API_KEY env vars)"
        )
        sys.exit(1)

    push_file = None
    for candidate in [
        output_path / "parts_complete.json",
        output_path / "parts_with_details.json",
        output_path / "parts.json",
    ]:
        if candidate.exists():
            push_file = candidate
            break

    if not push_file:
        print("No JSON file found to push")
        sys.exit(1)

    print(f"  Pushing: {push_file}")
    print(f"  To:      {wp_url}")

    try:
        endpoint = wp_url.rstrip("/") + "/wp-json/csf/v1/import"

        with push_file.open() as f:
            json_data = json.load(f)

        response = httpx.post(
            endpoint,
            json=json_data,
            headers={
                "X-CSF-API-Key": wp_api_key,
                "Content-Type": "application/json",
            },
            timeout=300.0,
        )

        if response.status_code == HTTP_OK:
            result_data = response.json()
            results = result_data.get("results", {})
            print("\nPush successful!")
            print(f"   Created: {results.get('created', 0)}")
            print(f"   Updated: {results.get('updated', 0)}")
            print(f"   Skipped: {results.get('skipped', 0)}")
            logger.info("phase_push_completed", **results)
        else:
            print(f"\nPush failed: HTTP {response.status_code}")
            print(f"   {response.text}")
            logger.exception(
                "phase_push_failed",
                status=response.status_code,
                body=response.text,
            )

    except Exception as e:
        logger.exception("phase_push_error", error=str(e))
        print(f"\nPush failed: {e}")


def _print_summary(
    catalog: bool,
    details: bool,
    push: bool,
    output_path: Path,
) -> None:
    """Print final pipeline summary."""
    print("\n" + "=" * SEPARATOR_WIDTH)
    print("SCRAPING PIPELINE COMPLETED")
    print("=" * SEPARATOR_WIDTH)

    if catalog and details:
        _print_full_summary(push, output_path)
    elif catalog:
        _print_catalog_summary(output_path)
    else:
        _print_details_summary(push, output_path)

    print("=" * SEPARATOR_WIDTH + "\n")


def _print_full_summary(push: bool, output_path: Path) -> None:
    """Print summary when both catalog and details ran."""
    print("All phases completed successfully:")
    print(f"  1. Catalog:  {output_path / 'parts.json'}")
    print(f"  2. Compat:   {output_path / 'compatibility.json'}")
    enriched = output_path / "parts_with_details.json"
    print(f"  3. Enriched: {enriched}")
    print(f"  4. Complete: {output_path / 'parts_complete.json'}")
    if push:
        print("  5. Pushed to WordPress")
    print()
    if not push:
        print("Next step:")
        print("  Add --push --wp-url <url> --wp-api-key <key> to auto-push to WordPress")


def _print_catalog_summary(output_path: Path) -> None:
    """Print summary when only catalog ran."""
    print("Catalog scraping completed:")
    print(f"  {output_path / 'parts.json'}")
    print(f"  {output_path / 'compatibility.json'}")
    print()
    print("Next step:")
    print("  python run_scrape.py --details  # Add complete product details")


def _print_details_summary(push: bool, output_path: Path) -> None:
    """Print summary when only details ran."""
    print("Detail enrichment completed:")
    print(f"  {output_path / 'parts_with_details.json'}")
    print()
    if not push:
        print("Next step:")
        print("  Manually merge with compatibility.json, then import")


@click.command()
@click.option(
    "--catalog",
    is_flag=True,
    help="Run catalog scraping (hierarchy + applications)",
)
@click.option(
    "--details",
    is_flag=True,
    help=("Run detail enrichment (full descriptions, specs, tech notes, interchange, images)"),
)
@click.option(
    "--images",
    is_flag=True,
    help="DEPRECATED: Use --details instead. Runs detail enrichment.",
)
@click.option(
    "--make",
    type=str,
    default=None,
    help="Filter by specific make (e.g., 'Nissan') - catalog only",
)
@click.option(
    "--year",
    type=int,
    default=None,
    help="Filter by specific year (e.g., 2023) - catalog only",
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
    "--skus",
    type=str,
    default=None,
    help=("Comma-separated SKUs to target (e.g., 'CSF-3680,CSF-3981') - images only"),
)
@click.option(
    "--skus-file",
    type=click.Path(exists=True),
    default=None,
    help="File containing SKUs to target (one per line) - details only",
)
@click.option(
    "--force",
    is_flag=True,
    help=("Force re-enrichment even if parts already have detail data - details only"),
)
@click.option(
    "--push",
    is_flag=True,
    help="Push final JSON to WordPress via REST API after scraping",
)
@click.option(
    "--wp-url",
    type=str,
    envvar="CSF_WP_URL",
    default=None,
    help="WordPress site URL (or set CSF_WP_URL env var)",
)
@click.option(
    "--wp-api-key",
    type=str,
    envvar="CSF_WP_API_KEY",
    default=None,
    help="WordPress Push API key (or set CSF_WP_API_KEY env var)",
)
def main(  # noqa: PLR0913 - Click command requires many options
    catalog: bool,
    details: bool,
    images: bool,
    make: str | None,
    year: int | None,
    output_dir: str,
    verbose: bool,
    skus: str | None,
    skus_file: str | None,
    force: bool,
    push: bool,
    wp_url: str | None,
    wp_api_key: str | None,
) -> None:
    """Orchestrator for CSF MyCarParts scraping pipeline.

    Run different phases of the scraping process independently
    or together:
    - Catalog: Build vehicle hierarchy and fetch application pages
    - Details: Fetch detail pages for complete product data
      (descriptions, specs, tech notes, interchange, images)

    At least one of --catalog or --details must be specified.
    """
    if images:
        print("--images is deprecated. Use --details instead for complete enrichment.")
        details = True

    if not catalog and not details:
        print("Error: At least one of --catalog or --details must be specified.")
        print()
        print("Examples:")
        print("  python run_scrape.py --catalog --details  # Full scrape")
        print("  python run_scrape.py --catalog            # Catalog only")
        print("  python run_scrape.py --details            # Details only")
        sys.exit(1)

    output_path = Path(output_dir)

    _print_config(catalog, details, make, year, output_dir)

    if catalog:
        _run_catalog_phase(output_dir, output_path, make, year, verbose)

    if details:
        _run_details_phase(output_path, verbose, skus, skus_file, force)

    if catalog and details:
        _run_merge_phase(output_path)

    if push:
        _run_push_phase(output_path, wp_url, wp_api_key)

    _print_summary(catalog, details, push, output_path)

    logger.info(
        "pipeline_completed",
        catalog=catalog,
        details=details,
        output_dir=output_dir,
    )


if __name__ == "__main__":
    main()
