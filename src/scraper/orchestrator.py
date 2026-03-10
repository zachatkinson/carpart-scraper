"""Scraper orchestrator for coordinating the full scraping workflow.

This module implements the main scraping orchestration logic that coordinates
fetching, parsing, deduplication, and export of automotive parts data.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple, Self

import structlog
from bs4 import BeautifulSoup

from src.exporters.json_exporter import JSONExporter
from src.models.part import Part
from src.models.vehicle import Vehicle, VehicleCompatibility
from src.scraper.ajax_parser import AJAXResponseParser
from src.scraper.etag_store import ETagStore
from src.scraper.fetcher import RespectfulFetcher
from src.scraper.hierarchy_cache import HierarchyCache
from src.scraper.image_processor import ImageProcessor
from src.scraper.parser import CSFParser
from src.scraper.validator import DataValidator

if TYPE_CHECKING:
    import httpx

    from src.scraper.image_syncer import ImageSyncer

logger = structlog.get_logger()

# All 51 vehicle makes with their IDs (from reconnaissance)
MAKES = {
    1: "Nissan",
    2: "Ford",
    3: "Honda",
    4: "Toyota",
    5: "Scion",
    6: "Mazda",
    7: "Lexus",
    8: "Kia",
    9: "Hyundai",
    10: "Dodge",
    11: "Chevrolet",
    12: "GMC",
    13: "Buick",
    14: "Peterbilt",
    15: "Kenworth",
    16: "International",
    17: "Freightliner",
    18: "Lincoln",
    19: "Ram",
    20: "Mercury",
    21: "Volvo",
    22: "Subaru",
    23: "Jeep",
    24: "Volkswagen",
    25: "Mercedes-Benz",
    26: "Mitsubishi",
    27: "INFINITI",
    28: "Land Rover",
    29: "Chrysler",
    30: "Pontiac",
    31: "Saturn",
    32: "BMW",
    33: "Audi",
    34: "Cadillac",
    35: "Fiat",
    36: "Acura",
    37: "Hummer",
    38: "Isuzu",
    39: "Mack",
    40: "Sterling Truck",
    41: "Suzuki",
    42: "Porsche",
    43: "Jaguar",
    44: "Mini",
    45: "Oldsmobile",
    46: "Plymouth",
    47: "Saab",
    48: "Geo",
    49: "Daewoo",
    50: "Eagle",
    51: "Tesla",
}


@dataclass
class FailureRecord:
    """Record of a single scraping failure.

    Attributes:
        phase: Which phase failed (hierarchy, application, detail)
        identifier: What failed (make name, application ID, SKU)
        error_type: Exception class name
        error_message: Error description
        is_retryable: Whether the error is likely transient
    """

    phase: str
    identifier: str
    error_type: str
    error_message: str
    is_retryable: bool


@dataclass
class FailureTracker:
    """Tracks all failures during a scraping run.

    Provides recording, summarization, and querying of failures
    for post-run reporting and completeness analysis.
    """

    failures: list[FailureRecord] = field(default_factory=list)

    def record(
        self,
        phase: str,
        identifier: str,
        error_type: str,
        error_message: str,
        is_retryable: bool = True,
    ) -> None:
        """Record a failure.

        Args:
            phase: Phase where failure occurred
            identifier: What failed
            error_type: Exception class name
            error_message: Error description
            is_retryable: Whether the error is transient
        """
        self.failures.append(
            FailureRecord(
                phase=phase,
                identifier=identifier,
                error_type=error_type,
                error_message=error_message,
                is_retryable=is_retryable,
            )
        )

    def get_summary(self) -> dict[str, Any]:
        """Get failure summary grouped by phase.

        Returns:
            Dict with total_failures, by_phase counts, retryable/permanent counts
        """
        by_phase: dict[str, int] = {}
        retryable_count = 0
        permanent_count = 0

        for failure in self.failures:
            by_phase[failure.phase] = by_phase.get(failure.phase, 0) + 1
            if failure.is_retryable:
                retryable_count += 1
            else:
                permanent_count += 1

        return {
            "total_failures": len(self.failures),
            "by_phase": by_phase,
            "retryable": retryable_count,
            "permanent": permanent_count,
        }

    def get_failed_identifiers(self, phase: str) -> list[str]:
        """Get all failed identifiers for a given phase.

        Args:
            phase: Phase to filter by

        Returns:
            List of identifier strings that failed in this phase
        """
        return [f.identifier for f in self.failures if f.phase == phase]

    def to_dicts(self) -> list[dict[str, Any]]:
        """Serialize all failure records to dicts.

        Returns:
            List of serialized failure records
        """
        return [
            {
                "phase": f.phase,
                "identifier": f.identifier,
                "error_type": f.error_type,
                "error_message": f.error_message,
                "is_retryable": f.is_retryable,
            }
            for f in self.failures
        ]


class TimeBudgetError(Exception):
    """Raised when the scraper's time budget has been exhausted.

    This is a graceful exit — checkpoints have been saved and the next
    ``--resume`` run will continue where this one left off.
    """


# Public alias used by CLI
TimeBudgetExpired = TimeBudgetError


class TimeBudget:
    """Tracks elapsed time against a fixed budget.

    Args:
        budget_minutes: Total minutes allowed, or None for unlimited.
    """

    def __init__(self, budget_minutes: float | None) -> None:
        """Initialize time budget.

        Args:
            budget_minutes: Total minutes allowed, or None for unlimited.
        """
        self._start = time.monotonic()
        self._budget_seconds: float | None = (
            budget_minutes * 60.0 if budget_minutes is not None else None
        )

    @property
    def remaining_seconds(self) -> float | None:
        """Seconds remaining, or None if unlimited."""
        if self._budget_seconds is None:
            return None
        elapsed = time.monotonic() - self._start
        return max(0.0, self._budget_seconds - elapsed)

    @property
    def is_expired(self) -> bool:
        """True when the budget has been exhausted."""
        if self._budget_seconds is None:
            return False
        return (time.monotonic() - self._start) >= self._budget_seconds

    @property
    def elapsed_minutes(self) -> float:
        """Minutes elapsed since the budget started."""
        return (time.monotonic() - self._start) / 60.0


class DeduplicationResult(NamedTuple):
    """Result of deduplication with change detection.

    Attributes:
        new_skus: SKUs seen for the first time in this session
        changed_skus: SKUs whose content hash differs from previous export
    """

    new_skus: set[str]
    changed_skus: set[str]


class ScraperOrchestrator:
    """Orchestrates the full scraping workflow.

    Coordinates all phases of scraping:
    1. Hierarchy enumeration (makes -> years -> models -> applications)
    2. Deduplication by SKU
    3. Detail page fetching
    4. Export to JSON

    Attributes:
        fetcher: HTTP fetcher with rate limiting
        ajax_parser: Parser for jQuery AJAX responses
        html_parser: Parser for HTML content
        exporter: JSON data exporter
        output_dir: Directory for exports
        incremental: Whether to use incremental export mode
        failure_tracker: Tracks all failures during scraping
    """

    def __init__(  # noqa: PLR0913
        self,
        output_dir: Path | str = "exports",
        incremental: bool = False,
        delay_override: float | None = None,
        checkpoint_dir: Path | str = "checkpoints",
        fetcher: RespectfulFetcher | None = None,
        ajax_parser: AJAXResponseParser | None = None,
        html_parser: CSFParser | None = None,
        validator: DataValidator | None = None,
        exporter: JSONExporter | None = None,
        image_processor: ImageProcessor | None = None,
        etag_store: ETagStore | None = None,
        hierarchy_cache: HierarchyCache | None = None,
    ) -> None:
        """Initialize orchestrator with dependency injection.

        Args:
            output_dir: Directory for exports (default: "exports")
            incremental: Use incremental export mode (default: False)
            delay_override: Override default delay between requests (default: None)
            checkpoint_dir: Directory for checkpoint files (default: "checkpoints")
            fetcher: HTTP fetcher instance (default: creates RespectfulFetcher)
            ajax_parser: AJAX response parser (default: creates AJAXResponseParser)
            html_parser: HTML parser (default: creates CSFParser)
            validator: Data validator (default: creates DataValidator)
            exporter: JSON exporter (default: creates JSONExporter)
            image_processor: Image processor for AVIF conversion (default: creates ImageProcessor)
            etag_store: Content hash store for change detection (default: creates ETagStore)
            hierarchy_cache: Hierarchy cache for skipping unchanged makes
                (default: creates HierarchyCache)

        Note:
            Dependencies are injected via constructor for testability and flexibility.
            If not provided, default implementations are created automatically.
        """
        # Inject dependencies (create defaults if not provided)
        self.fetcher = fetcher or RespectfulFetcher()
        self.ajax_parser = ajax_parser or AJAXResponseParser()
        self.html_parser = html_parser or CSFParser()
        self.validator = validator or DataValidator()
        self.exporter = exporter or JSONExporter(output_dir=output_dir)
        self.image_processor = image_processor or ImageProcessor()
        self.image_syncer: ImageSyncer | None = None

        # Note: delay_override is reserved for future use when fetcher supports it
        self.delay_override = delay_override

        self.output_dir = Path(output_dir)
        self.checkpoint_dir = Path(checkpoint_dir)
        self.incremental = incremental

        # ETag store for content-hash-based change detection
        self.etag_store = etag_store or ETagStore(self.checkpoint_dir / "etags.json")

        # Hierarchy cache for skipping unchanged makes
        self.hierarchy_cache = hierarchy_cache or HierarchyCache(
            self.checkpoint_dir / "hierarchy_cache.json"
        )

        # Ensure checkpoint directory exists
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # State tracking
        self.unique_parts: dict[str, Part] = {}
        self.vehicle_compat: dict[str, list[Vehicle]] = {}
        self.parts_scraped = 0
        self.processed_application_ids: set[int] = set()

        # Failure tracking
        self.failure_tracker = FailureTracker()

        logger.info(
            "orchestrator_initialized",
            output_dir=str(self.output_dir),
            checkpoint_dir=str(self.checkpoint_dir),
            incremental=incremental,
            delay_override=delay_override,
        )

    def _enumerate_makes(self) -> dict[int, str]:
        """Discover all vehicle makes from the CSF homepage dropdown.

        Fetches the homepage and parses the makes dropdown to find all
        ``<a data-remote>`` links whose ``href`` contains ``get_year_by_make``.
        Falls back to the static ``MAKES`` constant if the homepage fetch
        or parsing fails.

        Returns:
            Dict mapping make_id to make name (same shape as ``MAKES``)
        """
        homepage_url = "https://csf.mycarparts.com/"
        try:
            response = self.fetcher.fetch(homepage_url)
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "make_discovery_failed_using_fallback",
                error_type=type(e).__name__,
                error=str(e),
            )
            return dict(MAKES)

        soup = BeautifulSoup(response.text, "html.parser")

        discovered: dict[int, str] = {}
        for link in soup.find_all("a", attrs={"data-remote": True}):
            href = link.get("href", "")
            if "get_year_by_make" not in href:
                continue

            # Extract make_id from last path segment (e.g. "/get_year_by_make/3" -> 3)
            match = re.search(r"/get_year_by_make/(\d+)", href)
            if not match:
                continue

            make_id = int(match.group(1))
            make_name = link.get_text(strip=True)
            if make_name:
                discovered[make_id] = make_name

        if not discovered:
            logger.warning("no_makes_discovered_from_homepage", url=homepage_url)
            return dict(MAKES)

        # Log any newly discovered makes not in the fallback constant
        known_ids = set(MAKES.keys())
        for mid, mname in discovered.items():
            if mid not in known_ids:
                logger.info("new_make_discovered", make_id=mid, make_name=mname)

        logger.info(
            "makes_discovered",
            count=len(discovered),
            new_count=len(set(discovered.keys()) - known_ids),
        )
        return discovered

    def _enumerate_years(
        self,
        make_id: int,
        make_name: str,
        *,
        prefetched_response: httpx.Response | None = None,
    ) -> dict[int, str]:
        """Enumerate all years for a given make.

        Args:
            make_id: Make ID (e.g., 3 for Honda)
            make_name: Make name (e.g., "Honda")
            prefetched_response: Already-fetched HTTP response to avoid double-fetching

        Returns:
            Dict mapping year_id to year string

        Example:
            >>> years = orchestrator._enumerate_years(3, "Honda")
            >>> 192 in years  # 2025
            True
        """
        url = f"https://csf.mycarparts.com/get_year_by_make/{make_id}"
        logger.debug("enumerating_years", make=make_name, make_id=make_id, url=url)

        response = prefetched_response or self.fetcher.fetch(url)
        years = self.ajax_parser.parse_year_response(response.text)

        logger.info("years_enumerated", make=make_name, year_count=len(years))
        return years

    def _enumerate_models(self, year_id: int, year: str, make_name: str) -> dict[int, str]:
        """Enumerate all models for a given year/make combination.

        Args:
            year_id: Year ID from year enumeration
            year: Year string (e.g., "2025")
            make_name: Make name (e.g., "Honda")

        Returns:
            Dict mapping application_id to model name

        Example:
            >>> models = orchestrator._enumerate_models(192, "2025", "Honda")
            >>> "Accord" in models.values()
            True
        """
        url = f"https://csf.mycarparts.com/get_model_by_make_year/{year_id}"
        logger.debug("enumerating_models", make=make_name, year=year, year_id=year_id, url=url)

        response = self.fetcher.fetch(url)
        models = self.ajax_parser.parse_model_response(response.text)

        logger.info("models_enumerated", make=make_name, year=year, model_count=len(models))
        return models

    def _build_hierarchy(  # noqa: PLR0915
        self,
        make_filter: str | None = None,
        year_filter: int | None = None,
        *,
        use_cache: bool = True,
    ) -> list[dict[str, Any]]:
        """Build complete vehicle hierarchy with error handling.

        Individual make or year failures are recorded and skipped,
        allowing the rest of the hierarchy to be built successfully.

        When ``use_cache`` is True and a previous hierarchy cache exists,
        the years AJAX response for each make is hashed and compared to
        the stored hash. On a match the cached hierarchy entries are reused,
        skipping all model enumeration requests for that make.

        Args:
            make_filter: Filter by make name (e.g., "Honda")
            year_filter: Filter by year (e.g., 2025)
            use_cache: Whether to use hierarchy cache (default: True)

        Returns:
            List of vehicle configurations with application IDs

        Format:
            [
                {
                    "make_id": 3,
                    "make": "Honda",
                    "year_id": 192,
                    "year": "2025",
                    "application_id": 8430,
                    "model": "Accord"
                },
                ...
            ]
        """
        hierarchy: list[dict[str, Any]] = []
        cache_hits = 0
        cache_misses = 0

        # Dynamically discover makes from homepage (falls back to MAKES constant)
        discovered_makes = self._enumerate_makes()

        # Filter makes if requested
        makes_to_process: list[tuple[int, str]] = list(discovered_makes.items())
        if make_filter:
            makes_to_process = [
                (mid, mname)
                for mid, mname in discovered_makes.items()
                if mname.lower() == make_filter.lower()
            ]

        logger.info(
            "building_hierarchy",
            total_makes=len(makes_to_process),
            make_filter=make_filter,
            year_filter=year_filter,
            use_cache=use_cache,
        )

        for make_id, make_name in makes_to_process:
            years_url = f"https://csf.mycarparts.com/get_year_by_make/{make_id}"

            try:
                # Fetch years response (we need it for both cache check and parsing)
                response = self.fetcher.fetch(years_url)
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "hierarchy_years_failed",
                    make=make_name,
                    make_id=make_id,
                    error_type=type(e).__name__,
                    error=str(e),
                )
                self.failure_tracker.record(
                    phase="hierarchy",
                    identifier=f"make:{make_name}",
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
                continue

            # Hash the years response for cache comparison
            response_hash = hashlib.md5(  # noqa: S324
                response.text.encode()
            ).hexdigest()

            # Check hierarchy cache
            if use_cache and self.hierarchy_cache.has_data():
                stored_hash = self.hierarchy_cache.get_url_hash(years_url)
                cached_entries = self.hierarchy_cache.get_make_hierarchy(make_id)

                if stored_hash == response_hash and cached_entries is not None:
                    # Cache hit — reuse cached hierarchy entries
                    make_entries = cached_entries
                    if year_filter:
                        make_entries = [e for e in make_entries if int(e["year"]) == year_filter]
                    hierarchy.extend(make_entries)
                    cache_hits += 1
                    logger.info(
                        "hierarchy_cache_hit",
                        make=make_name,
                        cached_entries=len(cached_entries),
                        after_filter=len(make_entries),
                    )
                    # Update hash in case it needs to be persisted
                    self.hierarchy_cache.set_url_hash(years_url, response_hash)
                    continue

            # Cache miss (or cache disabled) — enumerate years and models
            cache_misses += 1
            try:
                years = self._enumerate_years(make_id, make_name, prefetched_response=response)
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "hierarchy_years_parse_failed",
                    make=make_name,
                    make_id=make_id,
                    error_type=type(e).__name__,
                    error=str(e),
                )
                self.failure_tracker.record(
                    phase="hierarchy",
                    identifier=f"make:{make_name}",
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
                continue

            # Filter years if requested
            if year_filter:
                years = {yid: yr for yid, yr in years.items() if int(yr) == year_filter}

            make_entries = []
            for year_id, year in years.items():
                try:
                    # Enumerate models for this year/make
                    models = self._enumerate_models(year_id, year, make_name)
                except Exception as e:  # noqa: BLE001
                    logger.warning(
                        "hierarchy_models_failed",
                        make=make_name,
                        year=year,
                        year_id=year_id,
                        error_type=type(e).__name__,
                        error=str(e),
                    )
                    self.failure_tracker.record(
                        phase="hierarchy",
                        identifier=f"year:{make_name}/{year}",
                        error_type=type(e).__name__,
                        error_message=str(e),
                    )
                    continue

                for application_id, model in models.items():
                    make_entries.append(
                        {
                            "make_id": make_id,
                            "make": make_name,
                            "year_id": year_id,
                            "year": year,
                            "application_id": application_id,
                            "model": model,
                        }
                    )

            hierarchy.extend(make_entries)

            # Update cache with fresh data (store unfiltered entries)
            self.hierarchy_cache.set_url_hash(years_url, response_hash)
            # For cache storage, we need the full (unfiltered) entries for this make.
            # If year_filter was applied, we need to re-enumerate without filter
            # for the cache. But since we already enumerated with the filter,
            # we store what we have — the cache will be rebuilt on next full run.
            self.hierarchy_cache.set_make_hierarchy(make_id, make_entries)

        # Persist cache
        self.hierarchy_cache.save()

        logger.info(
            "hierarchy_built",
            total_vehicles=len(hierarchy),
            cache_hits=cache_hits,
            cache_misses=cache_misses,
        )
        return hierarchy

    def _deduplicate_and_track(
        self,
        parts: list[Part],
        vehicle: Vehicle,
        previous_hashes: dict[str, str] | None = None,
    ) -> DeduplicationResult:
        """Deduplicate parts by SKU and track vehicle compatibility.

        Uses last-write-wins strategy: always updates part data with latest
        information when re-scraping. Prevents duplicate vehicles in compatibility.
        When previous_hashes is provided, also detects changed parts by comparing
        content hashes.

        Args:
            parts: List of parts from application page
            vehicle: Vehicle configuration for compatibility tracking
            previous_hashes: Optional dict of SKU -> content hash from previous export.
                When provided, parts whose hash differs are tracked as changed.

        Returns:
            DeduplicationResult with new_skus and changed_skus sets

        Note:
            This method updates self.unique_parts and self.vehicle_compat
            in place for memory efficiency.
        """
        new_skus: set[str] = set()
        changed_skus: set[str] = set()

        for part in parts:
            sku = part.sku

            # Track new parts (first time seeing this SKU)
            if sku not in self.unique_parts:
                new_skus.add(sku)
                logger.debug("new_part_found", sku=sku, name=part.name)
            elif previous_hashes and sku in previous_hashes:
                # Check if content changed compared to previous export
                current_hash = self._content_hash(part)
                if current_hash != previous_hashes[sku]:
                    changed_skus.add(sku)
                    logger.debug("part_changed", sku=sku, name=part.name)

            # Always update with latest data (last-write-wins)
            self.unique_parts[sku] = part

            # Track vehicle compatibility (prevent duplicates)
            if sku not in self.vehicle_compat:
                self.vehicle_compat[sku] = []

            # Check if this exact vehicle (including engine) is already tracked
            vehicle_exists = any(
                v.make == vehicle.make
                and v.model == vehicle.model
                and v.year == vehicle.year
                and v.engine == vehicle.engine
                for v in self.vehicle_compat[sku]
            )

            if not vehicle_exists:
                self.vehicle_compat[sku].append(vehicle)
                engine_info = f" ({vehicle.engine})" if vehicle.engine else ""
                logger.debug(
                    "vehicle_compatibility_added",
                    sku=sku,
                    vehicle=f"{vehicle.year} {vehicle.make} {vehicle.model}{engine_info}",
                )

        logger.info(
            "deduplication_complete",
            parts_processed=len(parts),
            new_parts=len(new_skus),
            changed_parts=len(changed_skus),
            total_unique=len(self.unique_parts),
        )

        return DeduplicationResult(new_skus=new_skus, changed_skus=changed_skus)

    def _enrich_part_with_details(self, sku: str, detail_data: dict[str, Any]) -> None:
        """Enrich a part with data from its detail page.

        Args:
            sku: Part SKU
            detail_data: Detail page data extracted from detail page HTML

        Note:
            Creates a new Part object with enriched data since Parts are immutable.
            Updates self.unique_parts[sku] with the new object.
        """
        if sku not in self.unique_parts:
            logger.warning("part_not_found_for_enrichment", sku=sku)
            return

        part = self.unique_parts[sku]

        # Build updated data dict
        updated_data = part.model_dump()

        # Update with detail page data
        if detail_data.get("full_description"):
            updated_data["description"] = detail_data["full_description"]

        if detail_data.get("specifications"):
            # Merge specifications (detail page has more complete data)
            updated_data["specifications"] = {
                **updated_data["specifications"],
                **detail_data["specifications"],
            }

        if detail_data.get("tech_notes"):
            updated_data["tech_notes"] = detail_data["tech_notes"]

        if detail_data.get("interchange_data"):
            # Add interchange numbers (convert dict to ReferenceNumber objects)
            updated_data["interchange_numbers"] = detail_data["interchange_data"]

        # Process gallery images (parser already filters for large images only)
        if detail_data.get("additional_images"):
            processed_images = self.image_processor.process_images(
                sku, detail_data["additional_images"]
            )
            updated_data["images"] = processed_images

        # Create new Part with enriched data
        enriched_part = Part(**updated_data)
        self.unique_parts[sku] = enriched_part

        logger.debug("part_enriched", sku=sku, gallery_images=len(updated_data.get("images", [])))

    def _create_vehicle_from_config(
        self, config: dict[str, Any], vehicle_qualifiers: dict[str, Any] | None = None
    ) -> Vehicle:
        """Create Vehicle object from configuration dict.

        Args:
            config: Vehicle configuration with make, model, year
            vehicle_qualifiers: Optional dict with 'engine', 'aspiration', 'qualifiers' keys

        Returns:
            Vehicle object

        Example:
            >>> config = {"make": "Honda", "model": "Accord", "year": "2020"}
            >>> quals = {
            ...     "engine": "2.0L L4 1993cc",
            ...     "aspiration": "Turbocharged",
            ...     "qualifiers": ["Manual"]
            ... }
            >>> vehicle = orchestrator._create_vehicle_from_config(config, quals)
            >>> vehicle.make
            'Honda'
            >>> vehicle.engine
            '2.0L L4 1993cc'
            >>> vehicle.aspiration
            'Turbocharged'
        """
        if vehicle_qualifiers is None:
            vehicle_qualifiers = {}

        return Vehicle(
            make=config["make"],
            model=config["model"],
            year=int(config["year"]),
            engine=vehicle_qualifiers.get("engine"),
            aspiration=vehicle_qualifiers.get("aspiration"),
            qualifiers=vehicle_qualifiers.get("qualifiers", []),
        )

    @staticmethod
    def _content_hash(part: Part) -> str:
        """MD5 hash of content-relevant Part fields for change detection.

        Excludes volatile fields (scraped_at) and fields enriched separately
        (description, tech_notes, interchange_numbers) so that a re-scrape of the
        application page produces the same hash even if detail enrichment hasn't run yet.

        Args:
            part: Part to hash

        Returns:
            MD5 hex digest of content-relevant fields
        """
        content = {
            "sku": part.sku,
            "name": part.name,
            "price": str(part.price) if part.price else None,
            "category": part.category,
            "specifications": part.specifications,
            "images": [img.model_dump() for img in part.images],
            "manufacturer": part.manufacturer,
            "in_stock": part.in_stock,
            "features": part.features,
            "position": part.position,
        }
        return hashlib.md5(  # noqa: S324
            json.dumps(content, sort_keys=True).encode()
        ).hexdigest()

    def load_previous_export(self, export_path: Path | None = None) -> dict[str, str]:
        """Load previous parts.json and compute content hashes as baseline.

        Pre-populates self.unique_parts so un-scraped parts are preserved in output.
        Also loads previous compatibility.json to preserve vehicle compatibility data.
        Returns hash map for change detection during deduplication.

        Args:
            export_path: Path to previous parts.json (default: self.output_dir / "parts.json")

        Returns:
            Dict mapping SKU -> content hash from previous export
        """
        path = export_path or (self.output_dir / "parts.json")

        if not path.exists():
            logger.info("no_previous_export_found", path=str(path))
            return {}

        raw = json.loads(path.read_text())
        previous_hashes: dict[str, str] = {}

        # Handle both wrapped format {"metadata": ..., "parts": [...]} and flat list [...]
        data: list[dict[str, Any]] = raw.get("parts", raw) if isinstance(raw, dict) else raw

        for item in data:
            try:
                part = Part(**item)
                self.unique_parts[part.sku] = part
                previous_hashes[part.sku] = self._content_hash(part)
            except (ValueError, TypeError, KeyError, AttributeError) as e:
                sku = item.get("sku", "unknown") if isinstance(item, dict) else str(item)[:20]
                logger.warning("previous_part_load_failed", sku=sku, error=str(e))
                continue

        logger.info(
            "previous_export_loaded",
            parts_loaded=len(previous_hashes),
            path=str(path),
        )

        # Load previous compatibility.json too
        compat_path = path.parent / "compatibility.json"
        if compat_path.exists():
            compat_raw = json.loads(compat_path.read_text())
            # Handle wrapped format {"metadata": ..., "compatibility": [...]}
            compat_data: list[dict[str, Any]] = (
                compat_raw.get("compatibility", compat_raw)
                if isinstance(compat_raw, dict)
                else compat_raw
            )
            for entry in compat_data:
                sku = entry.get("sku", "")
                vehicles = entry.get("vehicles", [])
                if sku and sku not in self.vehicle_compat:
                    self.vehicle_compat[sku] = [Vehicle(**v) for v in vehicles]
            logger.info("previous_compatibility_loaded", entries=len(compat_data))

        return previous_hashes

    def _has_previous_export(self) -> bool:
        """Check if a previous export exists.

        Returns:
            True if parts.json exists in the output directory
        """
        return (self.output_dir / "parts.json").exists()

    def _filter_by_etags(self, hierarchy: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filter hierarchy to only applications whose pages have changed.

        Runs concurrent HTTP GET requests (capped by fetcher semaphore) for
        each application URL and computes content hashes. Pages whose hash
        matches the previously stored value are skipped.

        Args:
            hierarchy: Full vehicle hierarchy from _build_hierarchy

        Returns:
            Filtered hierarchy containing only changed/new applications
        """
        has_data = self.etag_store.has_data()

        if not has_data:
            logger.info("etag_store_empty_first_run")

        # Build batch of (url, previous_hash) pairs
        urls_and_hashes: list[tuple[str, str | None]] = []
        for config in hierarchy:
            application_id = config["application_id"]
            url = f"https://csf.mycarparts.com/applications/{application_id}"
            prev = self.etag_store.get(url) if has_data else None
            urls_and_hashes.append((url, prev))

        # Run concurrent checks
        results = asyncio.run(self.fetcher.async_check_etags(urls_and_hashes))

        # Process results sequentially
        changed: list[dict[str, Any]] = []
        skipped = 0

        for config, (is_changed, current_hash) in zip(hierarchy, results, strict=True):
            application_id = config["application_id"]
            url = f"https://csf.mycarparts.com/applications/{application_id}"
            self.etag_store.set(url, current_hash)

            if is_changed:
                changed.append(config)
            else:
                skipped += 1

        self.etag_store.save()

        logger.info(
            "etag_filtering_results",
            total=len(hierarchy),
            changed=len(changed),
            skipped=skipped,
        )

        # First run: return all (all are "new")
        if not has_data:
            return hierarchy

        return changed

    def _save_checkpoint(self, make_filter: str | None, year_filter: int | None) -> Path:
        """Save current scraping state to checkpoint file.

        Includes actual parts data and vehicle compatibility so resume
        does not need to re-fetch already scraped pages.

        Args:
            make_filter: Make filter used in scraping
            year_filter: Year filter used in scraping

        Returns:
            Path to checkpoint file
        """
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        filters = []
        if make_filter:
            filters.append(make_filter.lower())
        if year_filter:
            filters.append(str(year_filter))
        filter_str = "_".join(filters) if filters else "all"

        checkpoint_name = f"checkpoint_{filter_str}_{timestamp}.json"
        checkpoint_path = self.checkpoint_dir / checkpoint_name

        # Serialize parts data for checkpoint
        parts_data = {sku: part.model_dump(mode="json") for sku, part in self.unique_parts.items()}

        # Serialize vehicle compatibility
        compat_data = {
            sku: [v.model_dump(mode="json") for v in vehicles]
            for sku, vehicles in self.vehicle_compat.items()
        }

        checkpoint_data = {
            "timestamp": timestamp,
            "make_filter": make_filter,
            "year_filter": year_filter,
            "processed_application_ids": list(self.processed_application_ids),
            "unique_parts_count": len(self.unique_parts),
            "parts_scraped": self.parts_scraped,
            "vehicles_tracked": sum(len(v) for v in self.vehicle_compat.values()),
            "parts_data": parts_data,
            "vehicle_compat": compat_data,
            "failure_records": self.failure_tracker.to_dicts(),
        }

        with checkpoint_path.open("w") as f:
            json.dump(checkpoint_data, f, indent=2, default=str)

        logger.info(
            "checkpoint_saved",
            path=str(checkpoint_path),
            unique_parts_count=len(self.unique_parts),
            parts_scraped=self.parts_scraped,
        )
        return checkpoint_path

    @staticmethod
    def _raise_time_budget(
        budget: TimeBudget,
        phase: str,
        applications_processed: int,
        remaining: int | None = None,
    ) -> None:
        """Log and raise TimeBudgetError after checkpoint has been saved.

        Args:
            budget: The active time budget
            phase: Current scraping phase name
            applications_processed: Number of applications completed
            remaining: Applications still to process (if known)
        """
        logger.info(
            "time_budget_expired",
            phase=phase,
            elapsed_minutes=round(budget.elapsed_minutes, 1),
            applications_processed=applications_processed,
            remaining=remaining,
        )
        msg = (
            f"Time budget exhausted after {budget.elapsed_minutes:.1f} min "
            f"in phase '{phase}' ({applications_processed} apps processed"
        )
        if remaining is not None:
            msg += f", {remaining} remaining"
        msg += ")"
        raise TimeBudgetError(msg)

    def _load_checkpoint(self, checkpoint_path: Path | str) -> dict[str, Any]:
        """Load scraping state from checkpoint file.

        Restores parts data and vehicle compatibility if present in checkpoint
        (backward-compatible with old checkpoints that lack these fields).

        Args:
            checkpoint_path: Path to checkpoint file

        Returns:
            Checkpoint data dict

        Raises:
            FileNotFoundError: If checkpoint file doesn't exist
            ValueError: If checkpoint file is invalid
        """
        checkpoint_path = Path(checkpoint_path)

        if not checkpoint_path.exists():
            msg = f"Checkpoint file not found: {checkpoint_path}"
            raise FileNotFoundError(msg)

        with checkpoint_path.open() as f:
            checkpoint_data: dict[str, Any] = json.load(f)

        # Restore state
        try:
            self.processed_application_ids = set(checkpoint_data["processed_application_ids"])
            self.parts_scraped = checkpoint_data["parts_scraped"]
        except KeyError as e:
            msg = f"Invalid checkpoint file: {e}"
            raise ValueError(msg) from e

        # Restore parts data if present (backward-compatible)
        if "parts_data" in checkpoint_data:
            for sku, part_dict in checkpoint_data["parts_data"].items():
                self.unique_parts[sku] = Part(**part_dict)
            logger.info(
                "checkpoint_parts_restored",
                count=len(checkpoint_data["parts_data"]),
            )

        # Restore vehicle compatibility if present (backward-compatible)
        if "vehicle_compat" in checkpoint_data:
            for sku, vehicles_list in checkpoint_data["vehicle_compat"].items():
                self.vehicle_compat[sku] = [Vehicle(**v) for v in vehicles_list]
            logger.info(
                "checkpoint_compat_restored",
                count=len(checkpoint_data["vehicle_compat"]),
            )

        logger.info(
            "checkpoint_loaded",
            path=str(checkpoint_path),
            processed_apps=len(self.processed_application_ids),
        )

        return checkpoint_data

    def _get_latest_checkpoint(
        self, make_filter: str | None = None, year_filter: int | None = None
    ) -> Path | None:
        """Find the most recent checkpoint file matching filters.

        Args:
            make_filter: Make filter to match
            year_filter: Year filter to match

        Returns:
            Path to latest checkpoint or None if no matching checkpoint exists
        """
        filters = []
        if make_filter:
            filters.append(make_filter.lower())
        if year_filter:
            filters.append(str(year_filter))
        filter_str = "_".join(filters) if filters else "all"

        pattern = f"checkpoint_{filter_str}_*.json"
        checkpoints = sorted(self.checkpoint_dir.glob(pattern), reverse=True)

        if checkpoints:
            logger.info("found_checkpoint", path=str(checkpoints[0]))
            return checkpoints[0]

        logger.info("no_checkpoint_found", filter=filter_str)
        return None

    def scrape_all(  # noqa: PLR0913, PLR0912, PLR0915
        self,
        make_filter: str | None = None,
        year_filter: int | None = None,
        fetch_details: bool = True,
        resume: bool = False,
        checkpoint_interval: int = 10,
        fetch_details_new_only: bool = True,
        force_full: bool = False,
        time_budget_minutes: float | None = None,
    ) -> dict[str, Any]:
        """Execute full scraping workflow with intelligent change detection.

        Workflow:
        1. Build vehicle hierarchy (makes -> years -> models -> applications)
        1.5. [Auto] Filter unchanged pages via content hashing (if incremental)
        2. For each application:
           a. Scrape application page for parts list
           b. Deduplicate by SKU and track vehicle compatibility (last-write-wins)
           c. Save checkpoint every N applications
        3. For each SKU:
           a. Fetch detail page for new SKUs (if fetch_details_new_only=True)
           b. OR fetch details for all SKUs (if fetch_details=True and
              fetch_details_new_only=False)
           c. Enrich part with detailed specifications

        Args:
            make_filter: Filter by make name (e.g., "Honda")
            year_filter: Filter by year (e.g., 2025)
            fetch_details: Whether to fetch detail pages (default: True)
            resume: Resume from latest checkpoint if available (default: False)
            checkpoint_interval: Save checkpoint every N applications (default: 10)
            fetch_details_new_only: Only fetch details for new SKUs (default: True)
            force_full: Force full scrape, ignoring previous data (default: False)
            time_budget_minutes: Maximum minutes to run before saving checkpoint
                and exiting gracefully (default: None = unlimited).  Set this to
                a value *less* than your CI job timeout so that post-scrape steps
                (cache save, artifact upload) have time to execute.

        Returns:
            Dict with scraping statistics including failure tracking info

        Raises:
            TimeBudgetExpired: When the time budget is exhausted (checkpoint saved)
        """
        budget = TimeBudget(time_budget_minutes)
        # Auto-detect incremental mode: use it if previous data exists
        if not force_full and not self.incremental:
            etags_exist = self.etag_store.has_data()
            exports_exist = self._has_previous_export()
            if etags_exist or exports_exist:
                self.incremental = True
                logger.info(
                    "auto_incremental_detected",
                    etags_exist=etags_exist,
                    exports_exist=exports_exist,
                )

        # Force-full: reset manifest synced flags and hierarchy cache
        if force_full:
            self.image_processor.reset_synced_flags()
            self.hierarchy_cache.clear()
            self.hierarchy_cache.save()

        logger.info(
            "scraping_started",
            make_filter=make_filter,
            year_filter=year_filter,
            fetch_details=fetch_details,
            resume=resume,
            fetch_details_new_only=fetch_details_new_only,
            force_full=force_full,
            incremental=self.incremental,
        )

        # Resume from checkpoint if requested
        if resume:
            checkpoint = self._get_latest_checkpoint(make_filter, year_filter)
            if checkpoint:
                self._load_checkpoint(checkpoint)
                # Also load previously exported data if incremental mode
                if self.incremental:
                    logger.info("incremental_mode_resume", checkpoint=str(checkpoint))

        # Load previous export as baseline (if incremental)
        previous_hashes: dict[str, str] = {}
        if self.incremental:
            previous_hashes = self.load_previous_export()

        # Phase 1: Build vehicle hierarchy
        hierarchy = self._build_hierarchy(
            make_filter=make_filter,
            year_filter=year_filter,
            use_cache=not force_full,
        )
        total_applications = len(hierarchy)

        # Phase 1.5: ETag-based filtering (skip unchanged application pages)
        etag_skipped = 0
        if self.incremental and not force_full:
            pre_filter_count = len(hierarchy)
            hierarchy = self._filter_by_etags(hierarchy)
            etag_skipped = pre_filter_count - len(hierarchy)
            logger.info(
                "etag_filtering_complete",
                remaining=len(hierarchy),
                skipped=etag_skipped,
            )

        # Filter out already processed applications
        if resume and self.processed_application_ids:
            hierarchy = [
                config
                for config in hierarchy
                if config["application_id"] not in self.processed_application_ids
            ]
            logger.info(
                "resuming_from_checkpoint",
                total_applications=total_applications,
                already_processed=len(self.processed_application_ids),
                remaining=len(hierarchy),
            )

        logger.info("workflow_phase_1_complete", applications_to_process=len(hierarchy))

        # Phase 2: Batch-fetch application pages concurrently, then process sequentially
        new_skus_found: set[str] = set()
        changed_skus_found: set[str] = set()
        applications_processed = 0
        applications_failed = 0
        browser_fallback_count = 0

        # Step A: Async batch fetch all application pages (HTTP fast path)
        urls = [f"https://csf.mycarparts.com/applications/{c['application_id']}" for c in hierarchy]
        html_results: list[str | None] = []
        if urls:
            html_results = asyncio.run(self.fetcher.async_scrape_application_pages(urls))

        # Step B: Sequential processing (dedup, qualifier grouping, checkpoints)
        for idx, (config, fetched_html) in enumerate(zip(hierarchy, html_results, strict=True), 1):
            application_id = config["application_id"]
            url = f"https://csf.mycarparts.com/applications/{application_id}"

            logger.info(
                "processing_application",
                progress=f"{idx}/{len(hierarchy)}",
                vehicle=f"{config['year']} {config['make']} {config['model']}",
                application_id=application_id,
            )

            try:
                # Browser fallback for pages where HTTP fast path returned no content
                page_html: str
                if fetched_html is None:
                    logger.info("browser_fallback", application_id=application_id)
                    page_html = self.fetcher.fetch_with_browser(url)
                    browser_fallback_count += 1
                else:
                    page_html = fetched_html

                # Parse parts from application page
                soup = self.html_parser.parse(page_html)
                parts_data = self.html_parser.extract_parts_from_application_page(soup)
                parts: list[Part] = self.validator.validate_batch(parts_data)
                self.parts_scraped += len(parts)

                # Group parts by vehicle qualifiers (engine + aspiration + qualifiers)
                # Create separate Vehicle objects for each unique qualifier combination
                qualifier_groups: dict[str, tuple[dict[str, Any], list[Part]]] = {}
                for part, part_dict in zip(parts, parts_data, strict=True):
                    vehicle_qualifiers = part_dict.get("vehicle_qualifiers", {})

                    # Create unique key from qualifiers
                    engine = vehicle_qualifiers.get("engine") or ""
                    aspiration = vehicle_qualifiers.get("aspiration") or ""
                    quals = "|".join(vehicle_qualifiers.get("qualifiers", []))
                    qualifier_key = f"{engine}::{aspiration}::{quals}"

                    if qualifier_key not in qualifier_groups:
                        qualifier_groups[qualifier_key] = (vehicle_qualifiers, [])
                    qualifier_groups[qualifier_key][1].append(part)

                # Track compatibility for each qualifier variant
                for _qualifier_key, (
                    vehicle_qualifiers,
                    qualifier_parts,
                ) in qualifier_groups.items():
                    # Create vehicle with specific qualifiers
                    vehicle = self._create_vehicle_from_config(config, vehicle_qualifiers)

                    # Deduplicate and track compatibility (last-write-wins)
                    result = self._deduplicate_and_track(
                        qualifier_parts, vehicle, previous_hashes or None
                    )
                    new_skus_found.update(result.new_skus)
                    changed_skus_found.update(result.changed_skus)

                # Mark as processed
                self.processed_application_ids.add(application_id)
                applications_processed += 1

                # Save checkpoint periodically
                if applications_processed % checkpoint_interval == 0:
                    self._save_checkpoint(make_filter, year_filter)

                    # Export incrementally if configured
                    if self.incremental:
                        logger.info("exporting_incrementally")
                        self.export_data()

                    # Check time budget after checkpoint save
                    if budget.is_expired:
                        remaining = len(hierarchy) - idx
                        self._raise_time_budget(
                            budget, "application", applications_processed, remaining
                        )

            except TimeBudgetExpired:
                raise
            except Exception as e:
                applications_failed += 1
                self.failure_tracker.record(
                    phase="application",
                    identifier=str(application_id),
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
                logger.exception(
                    "application_scrape_failed",
                    application_id=application_id,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                continue

        logger.info(
            "workflow_phase_2_complete",
            applications_processed=applications_processed,
            applications_failed=applications_failed,
            browser_fallback_count=browser_fallback_count,
            unique_parts=len(self.unique_parts),
            new_skus=len(new_skus_found),
            changed_skus=len(changed_skus_found),
        )

        # Log incremental summary if we loaded a previous export
        if previous_hashes:
            preserved_skus = set(previous_hashes.keys()) - new_skus_found - changed_skus_found
            logger.info(
                "incremental_summary",
                new=len(new_skus_found),
                changed=len(changed_skus_found),
                preserved=len(preserved_skus),
            )

        # Save final checkpoint
        self._save_checkpoint(make_filter, year_filter)

        # Check time budget before starting Phase 3
        if budget.is_expired:
            self._raise_time_budget(budget, "before_phase_3", applications_processed)

        # Phase 3: Batch-fetch detail pages concurrently, then enrich sequentially
        details_fetched_count = 0
        details_failed = 0
        detail_browser_fallback_count = 0
        if fetch_details:
            # Determine which SKUs to fetch details for
            if fetch_details_new_only:
                skus_to_fetch = new_skus_found | changed_skus_found
                logger.info(
                    "workflow_phase_3_started_new_only",
                    new_skus_to_enrich=len(new_skus_found),
                    changed_skus_to_enrich=len(changed_skus_found),
                    total_to_enrich=len(skus_to_fetch),
                )
            else:
                skus_to_fetch = set(self.unique_parts.keys())
                logger.info(
                    "workflow_phase_3_started_all",
                    total_skus_to_enrich=len(skus_to_fetch),
                )

            if skus_to_fetch:
                # Step A: Build URLs and async batch fetch
                sku_list = sorted(skus_to_fetch)
                detail_urls = [
                    "https://csf.autocaredata.com/items/"
                    + sku.replace("CSF-", "").replace("csf-", "")
                    for sku in sku_list
                ]
                detail_html_results = asyncio.run(
                    self.fetcher.async_fetch_detail_pages(detail_urls)
                )

                # Step B: Sequential enrichment
                for sku, detail_url, fetched_html in zip(
                    sku_list, detail_urls, detail_html_results, strict=True
                ):
                    try:
                        # Browser fallback for pages where HTTP returned no content
                        detail_html: str
                        if fetched_html is None:
                            logger.info("detail_browser_fallback", sku=sku)
                            detail_html = self.fetcher.fetch_with_browser(detail_url)
                            detail_browser_fallback_count += 1
                        else:
                            detail_html = fetched_html

                        # Parse and enrich
                        soup = self.html_parser.parse(detail_html)
                        detail_data = self.html_parser.extract_detail_page_data(soup, sku)
                        self._enrich_part_with_details(sku, detail_data)
                        details_fetched_count += 1

                        # Stream-sync images for this SKU if syncer is configured
                        image_syncer = getattr(self, "image_syncer", None)
                        if image_syncer is not None:
                            image_syncer.sync_and_cleanup_for_sku(sku)
                    except Exception as e:
                        details_failed += 1
                        self.failure_tracker.record(
                            phase="detail",
                            identifier=sku,
                            error_type=type(e).__name__,
                            error_message=str(e),
                        )
                        logger.exception(
                            "detail_fetch_failed",
                            sku=sku,
                            error=str(e),
                            error_type=type(e).__name__,
                        )
                        continue

                logger.info(
                    "workflow_phase_3_complete",
                    parts_enriched=details_fetched_count,
                    details_failed=details_failed,
                    detail_browser_fallback_count=detail_browser_fallback_count,
                    new_only=fetch_details_new_only,
                )

        # Compile statistics
        stats: dict[str, Any] = {
            "unique_parts": len(self.unique_parts),
            "total_applications": total_applications,
            "applications_processed": applications_processed,
            "applications_skipped_unchanged": etag_skipped,
            "parts_scraped": self.parts_scraped,
            "new_parts": len(new_skus_found),
            "changed_parts": len(changed_skus_found),
            "vehicles_tracked": sum(len(v) for v in self.vehicle_compat.values()),
            "make_filter": make_filter,
            "year_filter": year_filter,
            "details_fetched": fetch_details,
            "details_fetched_count": details_fetched_count,
            "details_new_only": fetch_details_new_only,
            "resumed": resume,
            "applications_failed": applications_failed,
            "browser_fallback_count": browser_fallback_count,
            "details_failed": details_failed,
            "failure_summary": self.failure_tracker.get_summary(),
        }

        logger.info("scraping_completed", **stats)
        return stats

    def generate_completeness_report(
        self, previous_export_path: Path | str | None = None
    ) -> dict[str, Any]:
        """Generate a report on scraping completeness.

        Compares current scrape results against a previous export to detect
        missing or new parts, and summarizes all failures.

        Args:
            previous_export_path: Path to previous parts.json for comparison

        Returns:
            Dict with completeness metrics:
            - current_parts_count: int
            - failed_makes: list of make names that failed
            - failed_applications: list of application IDs that failed
            - failed_details: list of SKUs that failed detail fetch
            - failure_summary: dict with counts by phase
            - missing_skus: list of SKUs in previous but not current (if compared)
            - new_skus: list of SKUs in current but not previous (if compared)
        """
        report: dict[str, Any] = {
            "current_parts_count": len(self.unique_parts),
            "failed_makes": self.failure_tracker.get_failed_identifiers("hierarchy"),
            "failed_applications": self.failure_tracker.get_failed_identifiers("application"),
            "failed_details": self.failure_tracker.get_failed_identifiers("detail"),
            "failure_summary": self.failure_tracker.get_summary(),
        }

        # Compare with previous export if provided
        if previous_export_path is not None:
            previous_path = Path(previous_export_path)
            if previous_path.exists():
                with previous_path.open() as f:
                    previous_data = json.load(f)

                previous_skus = set()
                if isinstance(previous_data, list):
                    previous_skus = {p.get("sku", "") for p in previous_data}
                elif isinstance(previous_data, dict) and "parts" in previous_data:
                    previous_skus = {p.get("sku", "") for p in previous_data["parts"]}

                current_skus = set(self.unique_parts.keys())

                missing = previous_skus - current_skus
                new = current_skus - previous_skus

                report["missing_skus"] = sorted(missing)
                report["new_skus"] = sorted(new)
                report["missing_count"] = len(missing)
                report["new_count"] = len(new)

                if missing:
                    logger.warning(
                        "completeness_missing_parts",
                        missing_count=len(missing),
                        missing_skus=sorted(missing)[:10],
                    )
            else:
                logger.info(
                    "previous_export_not_found",
                    path=str(previous_path),
                )

        logger.info("completeness_report_generated", **report)
        return report

    def export_data(self) -> dict[str, Path]:
        """Export scraped data to JSON files.

        Returns:
            Dict mapping export type to file path

        Example:
            >>> orchestrator = ScraperOrchestrator()
            >>> paths = orchestrator.export_data()
            >>> paths["parts"].exists()
            True
        """
        logger.info("exporting_data", unique_parts=len(self.unique_parts))

        paths = {}

        # Export parts
        if self.unique_parts:
            parts_list = list(self.unique_parts.values())
            if self.incremental and self._has_previous_export():
                paths["parts"] = self.exporter.export_parts_incremental(parts_list, append=True)
            else:
                paths["parts"] = self.exporter.export_parts(parts_list)

        # Export compatibility
        if self.vehicle_compat:
            compat_list = [
                VehicleCompatibility(part_sku=sku, vehicles=vehicles, notes=None)
                for sku, vehicles in self.vehicle_compat.items()
            ]
            if self.incremental and (self.exporter.output_dir / "compatibility.json").exists():
                paths["compatibility"] = self.exporter.export_compatibility_incremental(
                    compat_list, append=True
                )
            else:
                paths["compatibility"] = self.exporter.export_compatibility(compat_list)

        logger.info("export_completed", files=list(paths.keys()))
        return paths

    def export_complete(self) -> Path:
        """Export merged parts with inline vehicle compatibility.

        Builds compatibility map from internal state and delegates to
        the JSON exporter to produce a single parts_complete.json file.

        Returns:
            Path to the merged export file
        """
        parts_list = list(self.unique_parts.values())
        return self.exporter.export_complete(parts_list, self.vehicle_compat)

    def get_stats(self) -> dict[str, Any]:
        """Get current scraping statistics.

        Returns:
            Dict of statistics

        Example:
            >>> orchestrator = ScraperOrchestrator()
            >>> stats = orchestrator.get_stats()
            >>> stats["unique_parts"]
            0
        """
        return {
            "unique_parts": len(self.unique_parts),
            "parts_scraped": self.parts_scraped,
            "vehicles_tracked": sum(len(v) for v in self.vehicle_compat.values()),
        }

    def close(self) -> None:
        """Clean up resources."""
        self.image_processor.close()
        self.fetcher.close()
        logger.info("orchestrator_closed")

    def __enter__(self) -> Self:
        """Context manager entry."""
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager exit."""
        self.close()
