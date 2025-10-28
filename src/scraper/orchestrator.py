"""Scraper orchestrator for coordinating the full scraping workflow.

This module implements the main scraping orchestration logic that coordinates
fetching, parsing, deduplication, and export of automotive parts data.
"""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

from src.exporters.json_exporter import JSONExporter
from src.models.part import Part
from src.models.vehicle import Vehicle, VehicleCompatibility
from src.scraper.ajax_parser import AJAXResponseParser
from src.scraper.fetcher import RespectfulFetcher
from src.scraper.parser import CSFParser
from src.scraper.validator import DataValidator

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


class ScraperOrchestrator:
    """Orchestrates the full scraping workflow.

    Coordinates all phases of scraping:
    1. Hierarchy enumeration (makes → years → models → applications)
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
    """

    def __init__(
        self,
        output_dir: Path | str = "exports",
        incremental: bool = False,
        delay_override: float | None = None,
        checkpoint_dir: Path | str = "checkpoints",
    ) -> None:
        """Initialize orchestrator.

        Args:
            output_dir: Directory for exports (default: "exports")
            incremental: Use incremental export mode (default: False)
            delay_override: Override default delay between requests (default: None)
            checkpoint_dir: Directory for checkpoint files (default: "checkpoints")

        Note:
            The delay_override parameter is currently ignored as RespectfulFetcher
            uses Final constants. A future enhancement could modify the fetcher
            to accept delay parameters in its constructor.
        """
        self.fetcher = RespectfulFetcher()
        # Note: delay_override is reserved for future use when fetcher supports it
        self.delay_override = delay_override

        self.ajax_parser = AJAXResponseParser()
        self.html_parser = CSFParser()
        self.validator = DataValidator()
        self.exporter = JSONExporter(output_dir=output_dir)
        self.output_dir = Path(output_dir)
        self.checkpoint_dir = Path(checkpoint_dir)
        self.incremental = incremental

        # Ensure checkpoint directory exists
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # State tracking
        self.unique_parts: dict[str, Part] = {}
        self.vehicle_compat: dict[str, list[Vehicle]] = {}
        self.parts_scraped = 0
        self.processed_application_ids: set[int] = set()

        logger.info(
            "orchestrator_initialized",
            output_dir=str(self.output_dir),
            checkpoint_dir=str(self.checkpoint_dir),
            incremental=incremental,
            delay_override=delay_override,
        )

    def _enumerate_years(self, make_id: int, make_name: str) -> dict[int, str]:
        """Enumerate all years for a given make.

        Args:
            make_id: Make ID (e.g., 3 for Honda)
            make_name: Make name (e.g., "Honda")

        Returns:
            Dict mapping year_id to year string

        Example:
            >>> years = orchestrator._enumerate_years(3, "Honda")
            >>> 192 in years  # 2025
            True
        """
        url = f"https://csf.mycarparts.com/get_year_by_make/{make_id}"
        logger.debug("enumerating_years", make=make_name, make_id=make_id, url=url)

        response = self.fetcher.fetch(url)
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

    def _build_hierarchy(
        self, make_filter: str | None = None, year_filter: int | None = None
    ) -> list[dict[str, Any]]:
        """Build complete vehicle hierarchy.

        Args:
            make_filter: Filter by make name (e.g., "Honda")
            year_filter: Filter by year (e.g., 2025)

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
        hierarchy = []

        # Filter makes if requested
        makes_to_process: list[tuple[int, str]] = list(MAKES.items())
        if make_filter:
            makes_to_process = [
                (mid, mname) for mid, mname in MAKES.items() if mname.lower() == make_filter.lower()
            ]

        logger.info(
            "building_hierarchy",
            total_makes=len(makes_to_process),
            make_filter=make_filter,
            year_filter=year_filter,
        )

        for make_id, make_name in makes_to_process:
            # Enumerate years for this make
            years = self._enumerate_years(make_id, make_name)

            # Filter years if requested
            if year_filter:
                years = {yid: yr for yid, yr in years.items() if int(yr) == year_filter}

            for year_id, year in years.items():
                # Enumerate models for this year/make
                models = self._enumerate_models(year_id, year, make_name)

                for application_id, model in models.items():
                    hierarchy.append(
                        {
                            "make_id": make_id,
                            "make": make_name,
                            "year_id": year_id,
                            "year": year,
                            "application_id": application_id,
                            "model": model,
                        }
                    )

        logger.info("hierarchy_built", total_vehicles=len(hierarchy))
        return hierarchy

    def _scrape_application_page(
        self, application_id: int, vehicle_config: dict[str, Any]
    ) -> list[Part]:
        """Scrape parts from a vehicle application page.

        Args:
            application_id: Application ID for the vehicle
            vehicle_config: Vehicle configuration dict with make, model, year

        Returns:
            List of Part objects found on the page

        Example:
            >>> config = {"make": "Honda", "model": "Accord", "year": "2020"}
            >>> parts = orchestrator._scrape_application_page(8430, config)
            >>> len(parts) > 0
            True
        """
        url = f"https://csf.mycarparts.com/applications/{application_id}"
        logger.info(
            "scraping_application_page",
            application_id=application_id,
            vehicle=f"{vehicle_config['year']} {vehicle_config['make']} {vehicle_config['model']}",
            url=url,
        )

        # Fetch page with JavaScript rendering
        html = self.fetcher.fetch_with_browser(url)

        # Parse parts from application page (returns list of dicts)
        soup = self.html_parser.parse(html)
        parts_data = self.html_parser.extract_parts_from_application_page(soup)

        # Validate and convert to Part objects
        parts: list[Part] = self.validator.validate_batch(parts_data)

        logger.info(
            "application_page_scraped",
            application_id=application_id,
            parts_found=len(parts),
        )

        return parts

    def _deduplicate_and_track(self, parts: list[Part], vehicle: Vehicle) -> set[str]:
        """Deduplicate parts by SKU and track vehicle compatibility.

        Uses last-write-wins strategy: always updates part data with latest
        information when re-scraping. Prevents duplicate vehicles in compatibility.

        Args:
            parts: List of parts from application page
            vehicle: Vehicle configuration for compatibility tracking

        Returns:
            Set of new SKUs (parts not seen before in this session)

        Note:
            This method updates self.unique_parts and self.vehicle_compat
            in place for memory efficiency.
        """
        new_skus: set[str] = set()

        for part in parts:
            sku = part.sku

            # Track new parts (first time seeing this SKU)
            if sku not in self.unique_parts:
                new_skus.add(sku)
                logger.debug("new_part_found", sku=sku, name=part.name)

            # Always update with latest data (last-write-wins)
            self.unique_parts[sku] = part

            # Track vehicle compatibility (prevent duplicates)
            if sku not in self.vehicle_compat:
                self.vehicle_compat[sku] = []

            # Check if this exact vehicle is already tracked
            vehicle_exists = any(
                v.make == vehicle.make and v.model == vehicle.model and v.year == vehicle.year
                for v in self.vehicle_compat[sku]
            )

            if not vehicle_exists:
                self.vehicle_compat[sku].append(vehicle)
                logger.debug(
                    "vehicle_compatibility_added",
                    sku=sku,
                    vehicle=f"{vehicle.year} {vehicle.make} {vehicle.model}",
                )

        logger.info(
            "deduplication_complete",
            parts_processed=len(parts),
            new_parts=len(new_skus),
            total_unique=len(self.unique_parts),
        )

        return new_skus

    def _fetch_detail_page(self, sku: str) -> dict[str, Any]:
        """Fetch and parse detail page for a part.

        Args:
            sku: Part SKU

        Returns:
            Dict with detailed part information from detail page

        Example:
            >>> detail = orchestrator._fetch_detail_page("7016")
            >>> "specifications" in detail
            True
        """
        url = f"https://csf.mycarparts.com/items/{sku}"
        logger.info("fetching_detail_page", sku=sku, url=url)

        # Fetch page with JavaScript rendering
        html = self.fetcher.fetch_with_browser(url)

        # Parse detail page
        soup = self.html_parser.parse(html)
        detail_data = self.html_parser.extract_detail_page_data(soup, sku)

        logger.info(
            "detail_page_fetched",
            sku=sku,
            has_description=bool(detail_data.get("full_description")),
            spec_count=len(detail_data.get("specifications", {})),
        )

        return detail_data

    def _enrich_part_with_details(self, sku: str, detail_data: dict[str, Any]) -> None:
        """Enrich a part with data from its detail page.

        Args:
            sku: Part SKU
            detail_data: Detail page data from _fetch_detail_page

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

        # Create new Part with enriched data
        enriched_part = Part(**updated_data)
        self.unique_parts[sku] = enriched_part

        logger.debug("part_enriched", sku=sku)

    def _create_vehicle_from_config(self, config: dict[str, Any]) -> Vehicle:
        """Create Vehicle object from configuration dict.

        Args:
            config: Vehicle configuration with make, model, year

        Returns:
            Vehicle object

        Example:
            >>> config = {"make": "Honda", "model": "Accord", "year": "2020"}
            >>> vehicle = orchestrator._create_vehicle_from_config(config)
            >>> vehicle.make
            'Honda'
        """
        return Vehicle(
            make=config["make"],
            model=config["model"],
            year=int(config["year"]),
        )

    def _get_hierarchy_fingerprint(self, hierarchy: list[dict[str, Any]]) -> str:
        """Generate fingerprint hash of vehicle hierarchy.

        Args:
            hierarchy: Vehicle hierarchy from _build_hierarchy

        Returns:
            MD5 hash of hierarchy structure

        Note:
            Only includes structural data (makes, years, models, application_ids).
            Changes to part details don't affect this fingerprint.
        """
        # Create canonical JSON representation
        hierarchy_json = json.dumps(hierarchy, sort_keys=True)
        # MD5 is fine for non-cryptographic fingerprinting
        fingerprint = hashlib.md5(hierarchy_json.encode()).hexdigest()  # noqa: S324

        logger.debug("hierarchy_fingerprint_generated", fingerprint=fingerprint)
        return fingerprint

    def _load_last_fingerprint(
        self, make_filter: str | None = None, year_filter: int | None = None
    ) -> str | None:
        """Load last saved hierarchy fingerprint.

        Args:
            make_filter: Make filter to match
            year_filter: Year filter to match

        Returns:
            Previous fingerprint hash or None if no previous run
        """
        filters = []
        if make_filter:
            filters.append(make_filter.lower())
        if year_filter:
            filters.append(str(year_filter))
        filter_str = "_".join(filters) if filters else "all"

        fingerprint_file = self.checkpoint_dir / f"hierarchy_fingerprint_{filter_str}.txt"

        if fingerprint_file.exists():
            fingerprint = fingerprint_file.read_text().strip()
            logger.info("loaded_previous_fingerprint", fingerprint=fingerprint)
            return fingerprint

        logger.info("no_previous_fingerprint_found")
        return None

    def _save_fingerprint(
        self, fingerprint: str, make_filter: str | None = None, year_filter: int | None = None
    ) -> None:
        """Save hierarchy fingerprint for future comparison.

        Args:
            fingerprint: Fingerprint hash to save
            make_filter: Make filter used
            year_filter: Year filter used
        """
        filters = []
        if make_filter:
            filters.append(make_filter.lower())
        if year_filter:
            filters.append(str(year_filter))
        filter_str = "_".join(filters) if filters else "all"

        fingerprint_file = self.checkpoint_dir / f"hierarchy_fingerprint_{filter_str}.txt"
        fingerprint_file.write_text(fingerprint)

        logger.info("fingerprint_saved", fingerprint=fingerprint, file=str(fingerprint_file))

    def detect_catalog_changes(
        self, make_filter: str | None = None, year_filter: int | None = None
    ) -> dict[str, Any]:
        """Detect if catalog hierarchy has changed since last run.

        This is a lightweight check that only enumerates the hierarchy
        (AJAX calls) without fetching any application pages. Takes ~5 minutes
        vs ~9 hours for full scrape.

        Args:
            make_filter: Filter by make name
            year_filter: Filter by year

        Returns:
            Dict with change detection results:
            - changed: bool (True if hierarchy changed)
            - current_fingerprint: str (hash of current hierarchy)
            - previous_fingerprint: str | None (hash of previous hierarchy)
            - total_vehicles: int (count of vehicle configurations)
            - new_vehicles: int (if changed, count of new configurations)

        Example:
            >>> changes = orchestrator.detect_catalog_changes(make_filter="Honda")
            >>> if changes['changed']:
            >>>     orchestrator.scrape_all(make_filter="Honda")
        """
        logger.info(
            "detecting_catalog_changes",
            make_filter=make_filter,
            year_filter=year_filter,
        )

        # Build hierarchy (only AJAX calls, no page fetching)
        hierarchy = self._build_hierarchy(make_filter=make_filter, year_filter=year_filter)

        # Generate fingerprint
        current_fingerprint = self._get_hierarchy_fingerprint(hierarchy)

        # Compare to previous fingerprint
        previous_fingerprint = self._load_last_fingerprint(make_filter, year_filter)

        changed = current_fingerprint != previous_fingerprint

        result = {
            "changed": changed,
            "current_fingerprint": current_fingerprint,
            "previous_fingerprint": previous_fingerprint,
            "total_vehicles": len(hierarchy),
        }

        if changed:
            # Save new fingerprint
            self._save_fingerprint(current_fingerprint, make_filter, year_filter)

            if previous_fingerprint:
                logger.info(
                    "catalog_changed",
                    total_vehicles=len(hierarchy),
                    fingerprint_changed=True,
                )
            else:
                logger.info(
                    "first_catalog_scan",
                    total_vehicles=len(hierarchy),
                )
        else:
            logger.info(
                "catalog_unchanged",
                total_vehicles=len(hierarchy),
                fingerprint=current_fingerprint,
            )

        return result

    def _save_checkpoint(self, make_filter: str | None, year_filter: int | None) -> Path:
        """Save current scraping state to checkpoint file.

        Args:
            make_filter: Make filter used in scraping
            year_filter: Year filter used in scraping

        Returns:
            Path to checkpoint file

        Note:
            Checkpoint includes processed application IDs and current statistics.
            Parts and compatibility data are saved separately via export.
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

        checkpoint_data = {
            "timestamp": timestamp,
            "make_filter": make_filter,
            "year_filter": year_filter,
            "processed_application_ids": list(self.processed_application_ids),
            "unique_parts_count": len(self.unique_parts),
            "parts_scraped": self.parts_scraped,
            "vehicles_tracked": sum(len(v) for v in self.vehicle_compat.values()),
        }

        with checkpoint_path.open("w") as f:
            json.dump(checkpoint_data, f, indent=2)

        logger.info("checkpoint_saved", path=str(checkpoint_path), **checkpoint_data)
        return checkpoint_path

    def _load_checkpoint(self, checkpoint_path: Path | str) -> dict[str, Any]:
        """Load scraping state from checkpoint file.

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
        check_changes: bool = False,
        fetch_details_new_only: bool = True,
    ) -> dict[str, Any]:
        """Execute full scraping workflow with intelligent change detection.

        Workflow:
        1. [Optional] Check for catalog changes (if check_changes=True)
        2. Build vehicle hierarchy (makes → years → models → applications)
        3. For each application:
           a. Scrape application page for parts list
           b. Deduplicate by SKU and track vehicle compatibility (last-write-wins)
           c. Save checkpoint every N applications
        4. For each SKU:
           a. Fetch detail page for new SKUs (if fetch_details_new_only=True)
           b. OR fetch details for all SKUs (if fetch_details=True and fetch_details_new_only=False)
           c. Enrich part with detailed specifications

        Args:
            make_filter: Filter by make name (e.g., "Honda")
            year_filter: Filter by year (e.g., 2025)
            fetch_details: Whether to fetch detail pages (default: True)
            resume: Resume from latest checkpoint if available (default: False)
            checkpoint_interval: Save checkpoint every N applications (default: 10)
            check_changes: Check for hierarchy changes before scraping (default: False)
            fetch_details_new_only: Only fetch details for new SKUs (default: True)

        Returns:
            Dict with scraping statistics including:
            - unique_parts: Total unique parts tracked
            - new_parts: Parts added in this run
            - catalog_changed: Whether hierarchy changed (if check_changes=True)
            - details_fetched_count: Number of detail pages fetched

        Example:
            >>> # Daily intelligent scrape
            >>> orchestrator = ScraperOrchestrator()
            >>> stats = orchestrator.scrape_all(
            ...     make_filter="Honda",
            ...     check_changes=True,
            ...     fetch_details_new_only=True
            ... )
            >>> if not stats['catalog_changed']:
            ...     print("No changes detected, scrape skipped")
        """
        logger.info(
            "scraping_started",
            make_filter=make_filter,
            year_filter=year_filter,
            fetch_details=fetch_details,
            resume=resume,
            check_changes=check_changes,
            fetch_details_new_only=fetch_details_new_only,
        )

        # Phase 0: Check for catalog changes (optional)
        catalog_changed = True  # Assume changed unless check_changes=True
        if check_changes:
            change_result = self.detect_catalog_changes(make_filter, year_filter)
            catalog_changed = change_result["changed"]

            if not catalog_changed:
                logger.info("no_catalog_changes_detected_skipping_scrape")
                return {
                    "unique_parts": len(self.unique_parts),
                    "total_applications": change_result["total_vehicles"],
                    "applications_processed": 0,
                    "parts_scraped": self.parts_scraped,
                    "new_parts": 0,
                    "vehicles_tracked": sum(len(v) for v in self.vehicle_compat.values()),
                    "make_filter": make_filter,
                    "year_filter": year_filter,
                    "details_fetched": False,
                    "details_fetched_count": 0,
                    "catalog_changed": False,
                    "resumed": resume,
                }

        # Resume from checkpoint if requested
        if resume:
            checkpoint = self._get_latest_checkpoint(make_filter, year_filter)
            if checkpoint:
                self._load_checkpoint(checkpoint)
                # Also load previously exported data if incremental mode
                if self.incremental:
                    logger.info("incremental_mode_resume", checkpoint=str(checkpoint))

        # Phase 1: Build vehicle hierarchy
        hierarchy = self._build_hierarchy(make_filter=make_filter, year_filter=year_filter)
        total_applications = len(hierarchy)

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

        # Phase 2: Scrape application pages and deduplicate
        new_skus_found: set[str] = set()
        applications_processed = 0

        for idx, config in enumerate(hierarchy, 1):
            application_id = config["application_id"]

            logger.info(
                "processing_application",
                progress=f"{idx}/{len(hierarchy)}",
                vehicle=f"{config['year']} {config['make']} {config['model']}",
                application_id=application_id,
            )

            try:
                # Scrape application page
                parts = self._scrape_application_page(application_id, config)
                self.parts_scraped += len(parts)

                # Create vehicle for compatibility tracking
                vehicle = self._create_vehicle_from_config(config)

                # Deduplicate and track compatibility (last-write-wins)
                new_skus = self._deduplicate_and_track(parts, vehicle)
                new_skus_found.update(new_skus)

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

            except Exception as e:
                logger.exception(
                    "application_scrape_failed",
                    application_id=application_id,
                    error=str(e),
                )
                continue

        logger.info(
            "workflow_phase_2_complete",
            applications_processed=applications_processed,
            unique_parts=len(self.unique_parts),
            new_skus=len(new_skus_found),
        )

        # Save final checkpoint
        self._save_checkpoint(make_filter, year_filter)

        # Phase 3: Fetch detail pages for parts
        details_fetched_count = 0
        if fetch_details:
            # Determine which SKUs to fetch details for
            if fetch_details_new_only:
                skus_to_fetch = new_skus_found
                logger.info(
                    "workflow_phase_3_started_new_only",
                    new_skus_to_enrich=len(skus_to_fetch),
                )
            else:
                skus_to_fetch = set(self.unique_parts.keys())
                logger.info(
                    "workflow_phase_3_started_all",
                    total_skus_to_enrich=len(skus_to_fetch),
                )

            if skus_to_fetch:
                for idx, sku in enumerate(skus_to_fetch, 1):
                    logger.info(
                        "fetching_details",
                        progress=f"{idx}/{len(skus_to_fetch)}",
                        sku=sku,
                    )

                    try:
                        detail_data = self._fetch_detail_page(sku)
                        self._enrich_part_with_details(sku, detail_data)
                        details_fetched_count += 1
                    except Exception as e:
                        logger.exception("detail_fetch_failed", sku=sku, error=str(e))
                        continue

                logger.info(
                    "workflow_phase_3_complete",
                    parts_enriched=details_fetched_count,
                    new_only=fetch_details_new_only,
                )

        # Compile statistics
        stats = {
            "unique_parts": len(self.unique_parts),
            "total_applications": total_applications,
            "applications_processed": applications_processed,
            "parts_scraped": self.parts_scraped,
            "new_parts": len(new_skus_found),
            "vehicles_tracked": sum(len(v) for v in self.vehicle_compat.values()),
            "make_filter": make_filter,
            "year_filter": year_filter,
            "details_fetched": fetch_details,
            "details_fetched_count": details_fetched_count,
            "details_new_only": fetch_details_new_only,
            "catalog_changed": catalog_changed,
            "resumed": resume,
        }

        logger.info("scraping_completed", **stats)
        return stats

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
            if self.incremental:
                paths["parts"] = self.exporter.export_parts_incremental(parts_list, append=True)
            else:
                paths["parts"] = self.exporter.export_parts(parts_list)

        # Export compatibility
        if self.vehicle_compat:
            compat_list = [
                VehicleCompatibility(part_sku=sku, vehicles=vehicles, notes=None)
                for sku, vehicles in self.vehicle_compat.items()
            ]
            if self.incremental:
                paths["compatibility"] = self.exporter.export_compatibility_incremental(
                    compat_list, append=True
                )
            else:
                paths["compatibility"] = self.exporter.export_compatibility(compat_list)

        logger.info("export_completed", files=list(paths.keys()))
        return paths

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
        self.fetcher.close()
        logger.info("orchestrator_closed")

    def __enter__(self) -> "ScraperOrchestrator":
        """Context manager entry."""
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager exit."""
        self.close()
