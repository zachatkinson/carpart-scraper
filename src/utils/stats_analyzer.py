"""Statistics analyzer for scraped data and exports.

This module provides utilities for analyzing automotive parts data,
generating statistics, and detecting patterns in the data.
"""

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class DataStats(BaseModel):
    """Statistics for automotive parts data.

    Attributes:
        total_parts: Total number of parts
        unique_skus: Number of unique SKUs
        parts_by_category: Count of parts per category
        total_vehicles: Total number of unique vehicles
        vehicles_by_make: Count of vehicles per make
        duplicate_count: Number of duplicate parts detected
        deduplication_rate: Percentage of duplicates (0-1)
        file_size_bytes: Size of the data file in bytes
        export_date: Date the export was created
        has_compatibility_data: Whether compatibility data is present
        price_data_available: Whether price data is available
    """

    total_parts: int = Field(..., ge=0, description="Total number of parts")
    unique_skus: int = Field(..., ge=0, description="Number of unique SKUs")
    parts_by_category: dict[str, int] = Field(
        default_factory=dict, description="Parts count per category"
    )
    total_vehicles: int = Field(..., ge=0, description="Total unique vehicles")
    vehicles_by_make: dict[str, int] = Field(
        default_factory=dict, description="Vehicles count per make"
    )
    duplicate_count: int = Field(default=0, ge=0, description="Number of duplicates")
    deduplication_rate: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Duplicate percentage"
    )
    file_size_bytes: int = Field(default=0, ge=0, description="File size in bytes")
    export_date: datetime | None = Field(None, description="Export creation date")
    has_compatibility_data: bool = Field(default=False, description="Has compatibility data")
    price_data_available: bool = Field(default=False, description="Has price data")

    model_config = {
        "frozen": True,
    }


class StatsAnalyzer:
    """Analyzer for automotive parts data statistics.

    Provides methods to analyze scraped data, exported files, and
    generate comprehensive statistics.
    """

    def __init__(self) -> None:
        """Initialize the stats analyzer."""

    def analyze_file(self, file_path: Path, detailed: bool = False) -> DataStats:
        """Analyze a JSON file and generate statistics.

        Args:
            file_path: Path to JSON file to analyze
            detailed: Whether to include detailed analysis

        Returns:
            Statistics for the file

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
        """
        if not file_path.exists():
            msg = f"File not found: {file_path}"
            raise FileNotFoundError(msg)

        # Load JSON data
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # Get file size
        file_size = file_path.stat().st_size

        # Determine data format and analyze
        if isinstance(data, list):
            return self._analyze_parts_list(data, file_size, detailed)
        if isinstance(data, dict):
            return self._analyze_dict_data(data, file_size, detailed)
        msg = f"Unsupported data format in {file_path}"
        raise ValueError(msg)

    def analyze_directory(self, dir_path: Path, detailed: bool = False) -> DataStats:
        """Analyze all JSON files in a directory.

        Args:
            dir_path: Path to directory containing JSON files
            detailed: Whether to include detailed analysis

        Returns:
            Combined statistics for all files

        Raises:
            FileNotFoundError: If directory doesn't exist
            ValueError: If no JSON files found
        """
        if not dir_path.exists() or not dir_path.is_dir():
            msg = f"Directory not found: {dir_path}"
            raise FileNotFoundError(msg)

        json_files = list(dir_path.glob("*.json"))
        if not json_files:
            msg = f"No JSON files found in {dir_path}"
            raise ValueError(msg)

        # Combine stats from all files
        combined_parts: list[dict[str, Any]] = []
        combined_vehicles: list[dict[str, Any]] = []
        total_size = 0

        for json_file in json_files:
            with json_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                total_size += json_file.stat().st_size

                if isinstance(data, list):
                    combined_parts.extend(data)
                elif isinstance(data, dict):
                    # Handle different dict formats
                    if "parts" in data:
                        parts = data.get("parts", [])
                        if isinstance(parts, list):
                            combined_parts.extend(parts)
                    if "compatibility" in data or "vehicles" in data:
                        vehicles = data.get("vehicles", data.get("compatibility", []))
                        if isinstance(vehicles, list):
                            combined_vehicles.extend(vehicles)

        return self._analyze_parts_list(combined_parts, total_size, detailed)

    def _analyze_parts_list(
        self,
        parts_data: list[dict[str, Any]],
        file_size: int,
        detailed: bool,  # noqa: ARG002
    ) -> DataStats:
        """Analyze a list of parts data.

        Args:
            parts_data: List of part dictionaries
            file_size: Size of the source file
            detailed: Whether to include detailed analysis (reserved for future use)

        Returns:
            Statistics for the parts data
        """
        if not parts_data:
            return DataStats(
                total_parts=0,
                unique_skus=0,
                total_vehicles=0,
                file_size_bytes=file_size,
                export_date=datetime.now(UTC),
            )

        # Extract SKUs and detect duplicates
        skus = [part.get("sku", "") for part in parts_data if part.get("sku")]
        sku_counts = Counter(skus)
        unique_skus = len(sku_counts)
        duplicate_count = sum(1 for count in sku_counts.values() if count > 1)
        dedup_rate = duplicate_count / unique_skus if unique_skus > 0 else 0.0

        # Category breakdown
        categories = [part.get("category", "Unknown") for part in parts_data]
        category_counts = dict(Counter(categories))

        # Vehicle analysis
        vehicles_set: set[tuple[str, str, int]] = set()
        make_counts: Counter[str] = Counter()

        for part in parts_data:
            # Check for vehicle data in part
            if part.get("vehicle"):
                vehicle = part["vehicle"]
                make = vehicle.get("make", "")
                model = vehicle.get("model", "")
                year = vehicle.get("year", 0)
                if make and model and year:
                    vehicles_set.add((make, model, year))
                    make_counts[make] += 1

        # Check for price data
        has_prices = any(part.get("price") is not None for part in parts_data)

        return DataStats(
            total_parts=len(parts_data),
            unique_skus=unique_skus,
            parts_by_category=category_counts,
            total_vehicles=len(vehicles_set),
            vehicles_by_make=dict(make_counts),
            duplicate_count=duplicate_count,
            deduplication_rate=dedup_rate,
            file_size_bytes=file_size,
            export_date=datetime.now(UTC),
            has_compatibility_data=bool(vehicles_set),
            price_data_available=has_prices,
        )

    def _analyze_dict_data(self, data: dict[str, Any], file_size: int, detailed: bool) -> DataStats:
        """Analyze dictionary-formatted data.

        Handles various dict formats like:
        - {"parts": [...], "metadata": {...}}
        - {"sku": [vehicles...], ...} (compatibility format)
        - {"summary": {...}, "data": [...]}

        Args:
            data: Dictionary of data
            file_size: Size of the source file
            detailed: Whether to include detailed analysis

        Returns:
            Statistics for the data
        """
        # Try to extract parts list from various formats
        parts_data: list[dict[str, Any]] = []

        # Format 1: {"parts": [...]}
        if "parts" in data:
            parts_data = data["parts"]

        # Format 2: {"data": [...]}
        elif "data" in data:
            parts_data = data["data"]

        # Format 3: Compatibility format {"sku": [vehicles...]}
        elif all(isinstance(v, list) for v in data.values()):
            # This is likely a compatibility mapping
            # Convert to parts format for analysis
            parts_data = [
                {"sku": sku, "category": "Unknown", "vehicles": vehicles}
                for sku, vehicles in data.items()
            ]

        # Format 4: Summary format
        elif "summary" in data:
            # Extract summary data
            summary = data["summary"]
            return DataStats(
                total_parts=summary.get("total_parts_found", 0),
                unique_skus=summary.get("unique_skus", 0),
                parts_by_category={},
                total_vehicles=0,
                vehicles_by_make={},
                duplicate_count=0,
                deduplication_rate=summary.get("deduplication_rate", 0.0),
                file_size_bytes=file_size,
                export_date=datetime.now(UTC),
                has_compatibility_data=False,
                price_data_available=False,
            )

        return self._analyze_parts_list(parts_data, file_size, detailed)
