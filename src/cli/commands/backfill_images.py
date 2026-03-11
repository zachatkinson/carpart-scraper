"""Backfill images command for CLI.

Fetches detail pages for parts missing images, downloads and converts
gallery images to AVIF, and syncs them to WordPress. The manifest
serves as the resume checkpoint — SKUs already present are skipped.
"""

import asyncio
import json
import sys
import time
from pathlib import Path

import click
import httpx
import structlog
from rich.console import Console

from src.scraper.fetcher import RespectfulFetcher
from src.scraper.image_processor import ImageProcessor
from src.scraper.image_syncer import (
    ImageSyncer,
    ImageSyncStrategy,
    LocalFileSyncer,
    RemoteAPISyncer,
)
from src.scraper.parser import CSFParser
from src.scraper.state_syncer import StateSyncer

logger = structlog.get_logger()
console = Console()

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_TIME_BUDGET = 3

WP_PAGE_SIZE = 100
DETAIL_BASE_URL = "https://csf.autocaredata.com/items/"


@click.command("backfill-images")
@click.option(
    "--wp-url",
    type=str,
    required=True,
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
@click.option(
    "--source",
    type=str,
    required=True,
    help="SKU source: 'wp' to paginate WP API, or path to local JSON export",
)
@click.option(
    "--time-budget",
    type=float,
    default=None,
    envvar="CSF_TIME_BUDGET",
    help="Max minutes to run before graceful exit (env: CSF_TIME_BUDGET)",
)
@click.option(
    "--batch-size",
    type=int,
    default=50,
    help="Detail pages to fetch concurrently per batch (default: 50)",
)
@click.option(
    "--images-dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default="images",
    help="Image storage directory (default: images/)",
)
def backfill_images(  # noqa: PLR0913
    wp_url: str,
    wp_api_key: str | None,
    source: str,
    time_budget: float | None,
    batch_size: int,
    images_dir: Path,
) -> None:
    r"""Backfill images for parts that are missing them.

    Fetches detail pages for SKUs not yet in the image manifest,
    downloads gallery images, converts to AVIF, and syncs to WordPress.
    Resumes automatically — SKUs already in the manifest are skipped.

    Examples:
        \b
        # Backfill from WordPress part list
        $ carpart backfill-images --source wp \
            --wp-url https://site.com --wp-api-key KEY

        \b
        # Backfill from local export file
        $ carpart backfill-images --source exports/parts_complete.json \
            --wp-url /path/to/uploads

        \b
        # With time budget for CI
        $ carpart backfill-images --source wp \
            --wp-url https://site.com --wp-api-key KEY --time-budget 60
    """
    is_remote = wp_url.startswith(("http://", "https://"))
    state_syncer: StateSyncer | None = None
    image_processor: ImageProcessor | None = None
    fetcher: RespectfulFetcher | None = None

    try:
        # Pull manifest from WordPress (remote mode)
        if is_remote and wp_api_key:
            state_syncer = StateSyncer(wp_url=wp_url, api_key=wp_api_key)
            state_syncer.pull("manifest", Path(f"{images_dir}/manifest.json"))

        # Collect all known SKUs
        all_skus = _collect_skus(source, wp_url, wp_api_key)

        # Determine which SKUs are missing images
        image_processor = ImageProcessor(images_dir=images_dir)
        skus_missing = _find_missing_skus(all_skus, image_processor)

        if not skus_missing:
            console.print("[green]All SKUs already have images![/green]")
            sys.exit(EXIT_SUCCESS)

        # Run the backfill pipeline
        syncer = _create_image_syncer(wp_url, wp_api_key, image_processor)
        fetcher = RespectfulFetcher()
        timed_out, processed, failed = _run_backfill(
            skus_missing, fetcher, image_processor, syncer, batch_size, time_budget
        )

        # Print summary
        _print_summary(syncer, processed, failed, len(skus_missing), timed_out)

        if timed_out:
            sys.exit(EXIT_TIME_BUDGET)
        sys.exit(EXIT_SUCCESS)

    except click.UsageError:
        raise
    except Exception as e:
        logger.exception("backfill_error", error=str(e))
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(EXIT_FAILURE)
    finally:
        if image_processor is not None:
            image_processor.close()
        if fetcher is not None:
            fetcher.close()
        if state_syncer is not None:
            state_syncer.push("manifest", Path(f"{images_dir}/manifest.json"))
            state_syncer.close()


def _collect_skus(source: str, wp_url: str, wp_api_key: str | None) -> list[str]:
    """Collect SKUs from the specified source.

    Args:
        source: 'wp' for WordPress API, or path to local JSON file
        wp_url: WordPress base URL (used when source is 'wp')
        wp_api_key: API key (required when source is 'wp')

    Returns:
        List of SKU strings
    """
    console.print("[bold]Collecting SKUs...[/bold]")
    if source == "wp":
        if not wp_api_key:
            msg = "--wp-api-key is required when --source is 'wp'"
            raise click.UsageError(msg)
        skus = _fetch_skus_from_wp(wp_url, wp_api_key)
    else:
        skus = _load_skus_from_json(Path(source))
    console.print(f"  Found {len(skus)} total SKUs")
    return skus


def _find_missing_skus(all_skus: list[str], image_processor: ImageProcessor) -> list[str]:
    """Find SKUs that don't have any images in the manifest.

    Args:
        all_skus: All known SKUs
        image_processor: ImageProcessor with loaded manifest

    Returns:
        List of SKUs missing images
    """
    skus_with_images = {
        filename.rsplit("_", 1)[0]
        for filename in image_processor._manifest  # noqa: SLF001
    }
    skus_missing = [s for s in all_skus if s not in skus_with_images]
    console.print(f"  Already have images: {len(skus_with_images)}")
    console.print(f"  Missing images:      {len(skus_missing)}")
    return skus_missing


def _run_backfill(  # noqa: PLR0913
    skus_missing: list[str],
    fetcher: RespectfulFetcher,
    image_processor: ImageProcessor,
    syncer: ImageSyncer,
    batch_size: int,
    time_budget: float | None,
) -> tuple[bool, int, int]:
    """Run the backfill pipeline in batches.

    Args:
        skus_missing: SKUs that need images
        fetcher: HTTP fetcher for detail pages
        image_processor: Image processor for AVIF conversion
        syncer: Image syncer for WordPress delivery
        batch_size: Concurrent detail page fetches per batch
        time_budget: Max minutes to run (None for unlimited)

    Returns:
        Tuple of (timed_out, processed_count, failed_count)
    """
    parser = CSFParser()
    deadline = time.monotonic() + (time_budget * 60) if time_budget else None
    processed = 0
    failed = 0
    timed_out = False

    console.print(
        f"\n[bold]Processing {len(skus_missing)} SKUs in batches of {batch_size}...[/bold]"
    )

    for batch_start in range(0, len(skus_missing), batch_size):
        if deadline and time.monotonic() >= deadline:
            timed_out = True
            console.print("[yellow]Time budget reached, saving progress...[/yellow]")
            break

        batch_skus = skus_missing[batch_start : batch_start + batch_size]
        batch_urls = [
            DETAIL_BASE_URL + sku.replace("CSF-", "").replace("csf-", "") for sku in batch_skus
        ]

        html_results = asyncio.run(
            fetcher.async_fetch_detail_pages(batch_urls, concurrency=batch_size)
        )

        batch_ok, batch_fail = _process_batch(
            batch_skus,
            batch_urls,
            html_results,
            fetcher,
            parser,
            image_processor,
            syncer,
        )
        processed += batch_ok
        failed += batch_fail

        logger.info(
            "backfill_batch_complete",
            processed=processed,
            failed=failed,
            remaining=len(skus_missing) - batch_start - len(batch_skus),
        )

    return timed_out, processed, failed


def _process_batch(  # noqa: PLR0913
    skus: list[str],
    urls: list[str],
    html_results: list[str | None],
    fetcher: RespectfulFetcher,
    parser: CSFParser,
    image_processor: ImageProcessor,
    syncer: ImageSyncer,
) -> tuple[int, int]:
    """Process a single batch of SKUs: parse, download images, sync.

    Args:
        skus: SKUs in this batch
        urls: Corresponding detail page URLs
        html_results: Fetched HTML (None means browser fallback needed)
        fetcher: Fetcher for browser fallback
        parser: HTML parser
        image_processor: AVIF image processor
        syncer: WordPress image syncer

    Returns:
        Tuple of (ok_count, fail_count)
    """
    ok = 0
    fail = 0

    for sku, url, fetched_html in zip(skus, urls, html_results, strict=True):
        try:
            html = fetched_html if fetched_html is not None else fetcher.fetch_with_browser(url)
            soup = parser.parse(html)
            detail_data = parser.extract_detail_page_data(soup, sku)

            images = detail_data.get("additional_images", [])
            if images:
                image_processor.process_images(sku, images)
                syncer.sync_and_cleanup_for_sku(sku)

            ok += 1
        except (httpx.HTTPError, OSError, ValueError, KeyError) as e:
            fail += 1
            logger.warning("backfill_sku_failed", sku=sku, error=str(e))

    return ok, fail


def _print_summary(
    syncer: ImageSyncer, processed: int, failed: int, total: int, timed_out: bool
) -> None:
    """Print backfill summary to console.

    Args:
        syncer: Image syncer with cumulative results
        processed: Number of SKUs successfully processed
        failed: Number of SKUs that failed
        total: Total SKUs that needed backfill
        timed_out: Whether time budget was reached
    """
    sync_result = syncer.cumulative_result
    console.print()
    status = (
        "[bold yellow]Backfill paused (time budget)[/bold yellow]"
        if timed_out
        else "[bold green]Backfill complete![/bold green]"
    )
    console.print(status)
    console.print(f"  Processed:   {processed}")
    console.print(f"  Failed:      {failed}")
    console.print(f"  Remaining:   {total - processed - failed}")
    console.print(f"  Uploaded:    {sync_result.uploaded}")
    console.print(f"  Skipped:     {sync_result.skipped}")


def _fetch_skus_from_wp(wp_url: str, api_key: str) -> list[str]:
    """Paginate WordPress REST API to collect all part SKUs.

    Args:
        wp_url: WordPress base URL
        api_key: API key for authentication

    Returns:
        List of all SKU strings from WordPress
    """
    skus: list[str] = []
    page = 1
    with httpx.Client(timeout=30) as client:
        while True:
            response = client.get(
                f"{wp_url.rstrip('/')}/wp-json/csf/v1/parts",
                params={"per_page": WP_PAGE_SIZE, "page": page},
                headers={"X-CSF-API-Key": api_key},
            )
            response.raise_for_status()
            data = response.json()

            parts = data.get("parts", [])
            if not parts:
                break

            skus.extend(part["sku"] for part in parts if part.get("sku"))

            total_pages = data.get("total_pages", page)
            if page >= total_pages:
                break
            page += 1

            logger.debug(
                "wp_sku_fetch_progress",
                page=page,
                total_pages=total_pages,
                skus=len(skus),
            )

    return skus


def _load_skus_from_json(path: Path) -> list[str]:
    """Load SKUs from a local JSON export file.

    Supports both flat list format (parts_complete.json) and
    nested formats with a 'sku' key per item.

    Args:
        path: Path to JSON file

    Returns:
        List of SKU strings

    Raises:
        click.UsageError: If file doesn't exist or has unexpected format
    """
    if not path.exists():
        msg = f"Source file not found: {path}"
        raise click.UsageError(msg)

    data = json.loads(path.read_text())

    if isinstance(data, list):
        return [item["sku"] for item in data if isinstance(item, dict) and item.get("sku")]

    if isinstance(data, dict) and "parts" in data:
        return [item["sku"] for item in data["parts"] if isinstance(item, dict) and item.get("sku")]

    msg = f"Unexpected JSON format in {path}"
    raise click.UsageError(msg)


def _create_image_syncer(
    wp_url: str,
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
        click.UsageError: If configuration is invalid
    """
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
        msg = f"--wp-url must be a local directory or HTTP(S) URL, got: {wp_url}"
        raise click.UsageError(msg)

    return ImageSyncer(strategy=strategy, image_processor=image_processor)
