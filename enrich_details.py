"""Enrich existing parts.json with complete detail page data.

This script:
1. Loads existing parts.json
2. For each part (or specific SKUs if provided)
3. Fetches detail page (https://csf.autocaredata.com/items/{sku_number})
4. Extracts comprehensive data:
   - Full description
   - Detailed specifications (~22 fields)
   - Technical notes
   - Interchange data (competitor part numbers)
   - Gallery images (large images only)
5. Downloads and converts images to AVIF
6. Updates part data with all enriched fields
7. Saves enriched parts.json

This provides complete product data in one pass, avoiding multiple detail page fetches.

Supports targeted updates:
    # Re-scrape specific SKUs
    python enrich_details.py --skus CSF-3680,CSF-3981,CSF-10535

    # Re-scrape SKUs from file
    python enrich_details.py --skus-file changed_skus.txt
"""

import json
import logging
import time
from pathlib import Path
from typing import Any

import click
import structlog
from bs4 import BeautifulSoup
from tqdm import tqdm

from src.scraper.fetcher import RespectfulFetcher
from src.scraper.image_processor import ImageProcessor
from src.scraper.parser import CSFParser

logger = structlog.get_logger()

# Configuration
PARTS_JSON = Path("exports/parts.json")
OUTPUT_JSON = Path("exports/parts_with_details.json")
IMAGES_DIR = Path("images")
DETAIL_PAGE_DELAY = 2.0  # Seconds between detail page fetches


def load_parts(parts_file: Path) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Load parts from JSON file.

    Args:
        parts_file: Path to parts.json

    Returns:
        Tuple of (parts list, metadata dict or None)
    """
    with parts_file.open() as f:
        data = json.load(f)

    # Handle wrapped format with metadata
    if isinstance(data, dict) and "parts" in data:
        parts = data["parts"]
        metadata = data.get("metadata")
        logger.info("loaded_wrapped_format", parts_count=len(parts), has_metadata=bool(metadata))
    else:
        parts = data
        metadata = None
        logger.info("loaded_parts_array", parts_count=len(parts))

    return parts, metadata


def save_parts(
    parts: list[dict[str, Any]], output_file: Path, metadata: dict[str, Any] | None = None
) -> None:
    """Save parts to JSON file.

    Args:
        parts: List of part dicts
        output_file: Path to save JSON
        metadata: Optional metadata dict
    """
    output_data = {"metadata": metadata, "parts": parts} if metadata else parts

    with output_file.open("w") as f:
        json.dump(output_data, f, indent=2)

    logger.info("parts_saved", path=str(output_file), count=len(parts))


def construct_detail_url(sku: str) -> str:
    """Construct detail page URL from SKU.

    Args:
        sku: Part SKU (e.g., "CSF-3680")

    Returns:
        Detail page URL

    Example:
        >>> construct_detail_url("CSF-3680")
        'https://csf.autocaredata.com/items/3680'
    """
    # Extract numeric part from SKU (CSF-3680 → 3680)
    sku_number = sku.replace("CSF-", "").replace("csf-", "")
    return f"https://csf.autocaredata.com/items/{sku_number}"


def enrich_part_with_details(
    part: dict[str, Any],
    fetcher: RespectfulFetcher,
    parser: CSFParser,
    image_processor: ImageProcessor,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Fetch detail page and enrich part with complete data.

    Args:
        part: Part dict
        fetcher: HTTP fetcher
        parser: HTML parser
        image_processor: Image processor
        force_refresh: Re-fetch even if part already has detail data

    Returns:
        Updated part dict with:
        - full_description: str | None
        - specifications: dict (merged from application + detail pages)
        - tech_notes: str | None
        - interchange_data: list[dict]
        - images: list[dict] (processed AVIF images)
    """
    sku = part.get("sku", "")

    # Skip if already enriched (unless force_refresh)
    if not force_refresh and part.get("full_description") is not None and part.get("images"):
        logger.debug("part_already_enriched_skipping", sku=sku)
        return part

    # Construct detail page URL
    url = construct_detail_url(sku)

    try:
        # Fetch detail page with browser (for JavaScript content)
        logger.debug("fetching_detail_page", sku=sku, url=url)
        html = fetcher.fetch_with_browser(url)

        # Parse complete detail page data
        soup = BeautifulSoup(html, "html.parser")
        detail_data = parser.extract_detail_page_data(soup, sku)

        # Extract and process images
        images = detail_data.get("additional_images", [])
        if images:
            logger.info("images_extracted", sku=sku, count=len(images))
            processed_images = image_processor.process_images(sku, images)

            if processed_images:
                part["images"] = processed_images
            else:
                logger.warning("image_processing_failed", sku=sku)
        else:
            logger.warning("no_images_found", sku=sku, url=url)

        # Merge detail page data into part
        # Preserve existing basic info from application pages
        part["full_description"] = detail_data.get("full_description")
        part["tech_notes"] = detail_data.get("tech_notes")
        part["interchange_data"] = detail_data.get("interchange_data", [])

        # Merge specifications (detail page specs are more comprehensive)
        existing_specs = part.get("specifications", {})
        detail_specs = detail_data.get("specifications", {})
        # Detail page specs take precedence, but keep application page specs as fallback
        part["specifications"] = {**existing_specs, **detail_specs}

        logger.info(
            "part_enriched",
            sku=sku,
            has_description=bool(part.get("full_description")),
            spec_count=len(part.get("specifications", {})),
            has_tech_notes=bool(part.get("tech_notes")),
            interchange_count=len(part.get("interchange_data", [])),
            image_count=len(part.get("images", [])),
        )

    except Exception as e:
        logger.exception("enrichment_failed", sku=sku, url=url, error=str(e))
        return part
    else:
        return part


def load_sku_filters(skus: str | None, skus_file: Path | None) -> set[str] | None:
    """Load target SKU filters from CLI arguments.

    Args:
        skus: Comma-separated list of SKUs
        skus_file: Path to file containing SKUs (one per line)

    Returns:
        Set of target SKUs, or None if no filter specified
    """
    if skus:
        target_skus = {sku.strip() for sku in skus.split(",")}
        logger.info("sku_filter_from_args", count=len(target_skus))
        return target_skus

    if skus_file:
        with skus_file.open() as f:
            target_skus = {line.strip() for line in f if line.strip()}
        logger.info("sku_filter_from_file", file=str(skus_file), count=len(target_skus))
        return target_skus

    return None


def filter_parts_to_process(
    parts: list[dict[str, Any]],
    target_skus: set[str] | None,
    force: bool,
) -> list[dict[str, Any]]:
    """Filter parts list to those needing enrichment.

    Args:
        parts: All parts
        target_skus: Specific SKUs to target, or None for all
        force: Whether to force re-enrichment

    Returns:
        List of parts to process
    """
    if target_skus:
        parts_to_process = [p for p in parts if p.get("sku") in target_skus]
        logger.info(
            "targeting_specific_skus",
            total=len(parts),
            targeted=len(parts_to_process),
            not_found=len(target_skus) - len(parts_to_process),
        )
        return parts_to_process

    if force:
        logger.info("force_refresh_all_parts", count=len(parts))
        return parts

    parts_to_process = [
        p for p in parts if p.get("full_description") is None or not p.get("images")
    ]
    logger.info(
        "parts_analysis",
        total=len(parts),
        already_enriched=len(parts) - len(parts_to_process),
        needs_enrichment=len(parts_to_process),
    )
    return parts_to_process


def run_enrichment_loop(
    parts_to_process: list[dict[str, Any]],
    fetcher: RespectfulFetcher,
    parser: CSFParser,
    image_processor: ImageProcessor,
    force: bool,
) -> tuple[int, int]:
    """Run the enrichment loop over parts with progress tracking.

    Args:
        parts_to_process: Parts that need enrichment
        fetcher: HTTP fetcher
        parser: HTML parser
        image_processor: Image processor
        force: Whether to force re-enrichment

    Returns:
        Tuple of (enriched_count, failed_count)
    """
    enriched_count = 0
    failed_count = 0

    with tqdm(
        total=len(parts_to_process), desc="Enriching parts with detail data", unit="part"
    ) as pbar:
        for part in parts_to_process:
            time.sleep(DETAIL_PAGE_DELAY)

            had_description = bool(part.get("full_description"))
            had_images = bool(part.get("images"))

            enriched_part = enrich_part_with_details(
                part, fetcher, parser, image_processor, force_refresh=force
            )

            has_description = bool(enriched_part.get("full_description"))
            has_images = bool(enriched_part.get("images"))

            if (has_description and not had_description) or (has_images and not had_images):
                enriched_count += 1
            else:
                failed_count += 1

            pbar.update(1)
            pbar.set_postfix({"enriched": enriched_count, "failed": failed_count})

    return enriched_count, failed_count


def print_summary(
    total: int, already_enriched: int, needed: int, enriched: int, failed: int
) -> None:
    """Print enrichment summary to stdout.

    Args:
        total: Total parts count
        already_enriched: Parts that were already enriched
        needed: Parts that needed enrichment
        enriched: Successfully enriched count
        failed: Failed enrichment count
    """
    print("\n" + "=" * 60)
    print("Detail Page Enrichment Complete!")
    print("=" * 60)
    print(f"Total parts:          {total}")
    print(f"Already enriched:     {already_enriched}")
    print(f"Needed enrichment:    {needed}")
    print(f"Successfully enriched: {enriched}")
    print(f"Failed:               {failed}")
    print(f"\nOutput:               {OUTPUT_JSON}")
    print("=" * 60)


@click.command()
@click.option(
    "--skus",
    type=str,
    default=None,
    help="Comma-separated list of SKUs to enrich (e.g., 'CSF-3680,CSF-3981')",
)
@click.option(
    "--skus-file",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="File containing SKUs to enrich (one per line)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force re-enrichment even if part already has detail data",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Enable verbose logging",
)
def main(skus: str | None, skus_file: Path | None, force: bool, verbose: bool) -> None:
    """Main enrichment workflow with optional SKU filtering."""
    if verbose:
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
        )

    logger.info("enrichment_started", input=str(PARTS_JSON), output=str(OUTPUT_JSON))

    parts, metadata = load_parts(PARTS_JSON)
    target_skus = load_sku_filters(skus, skus_file)
    parts_to_process = filter_parts_to_process(parts, target_skus, force)

    if not parts_to_process:
        if target_skus:
            logger.warning("no_matching_skus_found")
            print("No matching SKUs found in parts.json")
        else:
            logger.info("all_parts_enriched_nothing_to_do")
            print("All parts already enriched")
        return

    fetcher = RespectfulFetcher()
    parser = CSFParser()
    image_processor = ImageProcessor(images_dir=IMAGES_DIR, avif_quality=85)

    try:
        enriched_count, failed_count = run_enrichment_loop(
            parts_to_process, fetcher, parser, image_processor, force
        )

        save_parts(parts, OUTPUT_JSON, metadata)
        print_summary(
            total=len(parts),
            already_enriched=len(parts) - len(parts_to_process),
            needed=len(parts_to_process),
            enriched=enriched_count,
            failed=failed_count,
        )

        logger.info(
            "enrichment_complete",
            total=len(parts),
            enriched=enriched_count,
            failed=failed_count,
        )

    finally:
        fetcher.close()
        image_processor.close()


if __name__ == "__main__":
    main()
