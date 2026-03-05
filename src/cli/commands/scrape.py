"""Scrape command for CLI.

This module implements the main 'scrape' command for extracting parts data
from CSF MyCarParts website. It invokes the ScraperOrchestrator directly
for a single-command, cron-ready pipeline.
"""

import sys
from pathlib import Path

import click
import structlog
from rich.console import Console

from src.scraper.image_processor import ImageProcessor
from src.scraper.image_syncer import (
    ImageSyncer,
    ImageSyncStrategy,
    LocalFileSyncer,
    RemoteAPISyncer,
    SyncResult,
)
from src.scraper.orchestrator import ScraperOrchestrator
from src.scraper.state_syncer import StateSyncer

logger = structlog.get_logger()
console = Console()

# Exit codes
EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_HIGH_FAILURE_RATE = 2
FAILURE_RATE_THRESHOLD = 0.05


@click.command()
@click.option(
    "--make",
    type=str,
    default=None,
    help="Filter by vehicle make (e.g., 'Honda', 'Toyota')",
)
@click.option(
    "--year",
    type=int,
    default=None,
    help="Filter by model year (e.g., 2025, 2024)",
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, dir_okay=True, writable=True, path_type=Path),
    default="exports",
    help="Export directory path (default: exports/)",
)
@click.option(
    "--catalog-only",
    is_flag=True,
    default=False,
    help="Only scrape catalog data (skip detail pages and merged export)",
)
@click.option(
    "--incremental",
    is_flag=True,
    default=False,
    help="Use incremental mode — skip unchanged pages via content hashing",
)
@click.option(
    "--force-full",
    is_flag=True,
    default=False,
    help="Force full scrape, ignoring cached ETags and previous exports",
)
@click.option(
    "--resume",
    is_flag=True,
    default=False,
    help="Resume from the latest checkpoint",
)
@click.option(
    "--sync-images",
    is_flag=True,
    default=False,
    help="Sync AVIF images to WordPress after scraping",
)
@click.option(
    "--wp-url",
    type=str,
    default=None,
    envvar="CSF_WP_URL",
    help="WordPress URL or local uploads path (env: CSF_WP_URL)",
)
@click.option(
    "--wp-api-key",
    type=str,
    default=None,
    envvar="CSF_WP_API_KEY",
    help="WordPress API key for remote sync (env: CSF_WP_API_KEY)",
)
def scrape(  # noqa: PLR0913
    make: str | None,
    year: int | None,
    output_dir: Path,
    catalog_only: bool,
    incremental: bool,
    force_full: bool,
    resume: bool,
    sync_images: bool,
    wp_url: str | None,
    wp_api_key: str | None,
) -> None:
    r"""Scrape automotive parts data from CSF MyCarParts.

    Runs the full scraping pipeline: hierarchy enumeration, application
    scraping, detail enrichment, and JSON export — all in one command.

    Examples:
        \b
        # Full scrape (catalog + details + merged export)
        $ carpart scrape

        \b
        # Catalog only (no detail pages, no merged export)
        $ carpart scrape --catalog-only

        \b
        # Incremental — only re-scrape changed pages
        $ carpart scrape --incremental

        \b
        # Resume from checkpoint after interruption
        $ carpart scrape --resume

        \b
        # Scrape only Honda 2025 vehicles
        $ carpart scrape --make Honda --year 2025

        \b
        # Scrape and sync images to local WordPress (DDEV)
        $ carpart scrape --sync-images --wp-url /path/to/wp-content/uploads

        \b
        # Scrape and sync images to remote WordPress
        $ carpart scrape --sync-images --wp-url https://site.com --wp-api-key KEY
    """
    fetch_details = not catalog_only
    is_remote = _is_remote_wp(wp_url)
    state_syncer: StateSyncer | None = None

    try:
        # Pull state from WordPress for remote mode (ephemeral CI runners)
        if is_remote and wp_api_key:
            state_syncer = StateSyncer(wp_url=wp_url, api_key=wp_api_key)  # type: ignore[arg-type]
            state_syncer.pull("etags", Path("checkpoints/etags.json"))
            state_syncer.pull("manifest", Path("images/manifest.json"))

        with ScraperOrchestrator(
            output_dir=output_dir,
            incremental=incremental,
            checkpoint_dir="checkpoints",
        ) as orchestrator:
            # Set up streaming image sync before scraping
            sync_result: SyncResult | None = None
            if sync_images and not catalog_only:
                syncer = _create_image_syncer(wp_url, wp_api_key, orchestrator.image_processor)
                orchestrator.image_syncer = syncer

            # Run the full scraping pipeline
            stats = orchestrator.scrape_all(
                make_filter=make,
                year_filter=year,
                fetch_details=fetch_details,
                resume=resume,
                force_full=force_full,
            )

            # Export parts.json + compatibility.json
            export_paths = orchestrator.export_data()

            # Produce merged parts_complete.json when details were fetched
            if fetch_details:
                complete_path = orchestrator.export_complete()
                export_paths["complete"] = complete_path

            # Collect cumulative sync result from streaming sync
            if orchestrator.image_syncer is not None:
                sync_result = orchestrator.image_syncer.cumulative_result

        # Print summary
        _print_summary(stats, export_paths, sync_result)

        # Determine exit code
        exit_code = _compute_exit_code(stats)
        sys.exit(exit_code)

    except KeyboardInterrupt:
        console.print("\n[yellow]Scraping interrupted by user.[/yellow]")
        sys.exit(EXIT_FAILURE)
    except click.UsageError:
        raise
    except Exception as e:
        logger.exception("scraping_error", error=str(e))
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(EXIT_FAILURE)
    finally:
        # Push state to WordPress for remote mode — always attempt,
        # even after partial runs or crashes
        if state_syncer is not None:
            state_syncer.push("etags", Path("checkpoints/etags.json"))
            state_syncer.push("manifest", Path("images/manifest.json"))
            state_syncer.close()


def _create_image_syncer(
    wp_url: str | None,
    wp_api_key: str | None,
    image_processor: ImageProcessor,
) -> ImageSyncer:
    """Create an ImageSyncer with the appropriate strategy.

    Args:
        wp_url: WordPress URL or local directory path
        wp_api_key: API key for remote WordPress
        image_processor: ImageProcessor instance

    Returns:
        Configured ImageSyncer

    Raises:
        click.UsageError: If wp_url is missing or configuration is invalid
    """
    if not wp_url:
        msg = "--wp-url is required when using --sync-images"
        raise click.UsageError(msg)

    # Determine strategy: local path or remote URL
    strategy: ImageSyncStrategy
    wp_path = Path(wp_url)
    if wp_path.is_dir() or (not wp_url.startswith(("http://", "https://")) and "/" in wp_url):
        strategy = LocalFileSyncer(wp_uploads_dir=wp_path)
    elif wp_url.startswith(("http://", "https://")):
        if not wp_api_key:
            msg = "--wp-api-key is required for remote WordPress sync"
            raise click.UsageError(msg)
        strategy = RemoteAPISyncer(wp_url=wp_url, api_key=wp_api_key)
    else:
        msg = f"--wp-url must be a local directory path or HTTP(S) URL, got: {wp_url}"
        raise click.UsageError(msg)

    return ImageSyncer(strategy=strategy, image_processor=image_processor)


def _is_remote_wp(wp_url: str | None) -> bool:
    """Check if wp_url points to a remote WordPress site.

    Args:
        wp_url: WordPress URL or local path (may be None)

    Returns:
        True if wp_url is an HTTP(S) URL
    """
    return wp_url is not None and wp_url.startswith(("http://", "https://"))


def _print_summary(
    stats: dict[str, object],
    export_paths: dict[str, Path],
    sync_result: SyncResult | None = None,
) -> None:
    """Print scraping summary to console.

    Args:
        stats: Statistics from scrape_all()
        export_paths: Dict mapping export type to file path
        sync_result: Optional SyncResult from streaming image sync
    """
    console.print()
    console.print("[bold green]Scraping complete![/bold green]")
    console.print(f"  Unique parts:    {stats['unique_parts']}")
    console.print(f"  Vehicles tracked: {stats['vehicles_tracked']}")
    console.print(f"  Applications:    {stats['applications_processed']} processed")

    failure_summary = stats.get("failure_summary", {})
    total_failures = (
        failure_summary.get("total_failures", 0) if isinstance(failure_summary, dict) else 0
    )
    if total_failures > 0:
        console.print(f"  [yellow]Failures:       {total_failures}[/yellow]")

    console.print()
    console.print("[bold]Exports:[/bold]")
    for name, path in export_paths.items():
        console.print(f"  {name}: {path}")

    if sync_result is not None:
        console.print()
        console.print("[bold]Image Sync (streaming):[/bold]")
        console.print(f"  Uploaded:  {sync_result.uploaded}")
        console.print(f"  Skipped:   {sync_result.skipped}")
        console.print(f"  Failed:    {sync_result.failed}")


def _compute_exit_code(stats: dict[str, object]) -> int:
    """Compute exit code from scraping statistics.

    Args:
        stats: Statistics from scrape_all()

    Returns:
        0 for success, 1 for hard failure, 2 for high failure rate
    """
    total_apps = stats.get("total_applications", 0)
    if not isinstance(total_apps, int):
        total_apps = 0

    failure_summary = stats.get("failure_summary", {})
    total_failures = (
        failure_summary.get("total_failures", 0) if isinstance(failure_summary, dict) else 0
    )

    if total_apps == 0:
        return EXIT_SUCCESS

    failure_rate = total_failures / total_apps
    if failure_rate > FAILURE_RATE_THRESHOLD:
        return EXIT_HIGH_FAILURE_RATE

    return EXIT_SUCCESS
