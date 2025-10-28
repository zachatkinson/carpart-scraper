"""Scraper protocols (interfaces).

This module defines protocols (interfaces) for scraper components,
following the Interface Segregation Principle. Clients depend only
on the methods they actually use.
"""

from typing import Any, Protocol

import httpx
from bs4 import BeautifulSoup

from src.models.part import Part
from src.models.vehicle import Vehicle, VehicleCompatibility


class IFetcher(Protocol):
    """Protocol for HTTP fetching with respectful scraping."""

    def fetch(self, url: str) -> httpx.Response:
        """Fetch URL with rate limiting and retries.

        Args:
            url: URL to fetch

        Returns:
            HTTP response

        Raises:
            httpx.HTTPError: If request fails after retries
        """
        ...

    def fetch_with_browser(self, url: str) -> str:
        """Fetch URL using headless browser for JavaScript content.

        Args:
            url: URL to fetch

        Returns:
            Rendered HTML content

        Raises:
            Exception: If browser fetch fails
        """
        ...


class IParser(Protocol):
    """Protocol for HTML parsing."""

    def parse(self, html: str) -> BeautifulSoup:
        """Parse HTML into BeautifulSoup object.

        Args:
            html: Raw HTML string

        Returns:
            Parsed BeautifulSoup object
        """
        ...

    def extract_part_data(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Extract part data from parsed HTML.

        Args:
            soup: Parsed HTML

        Returns:
            Dict of part data

        Raises:
            ValueError: If required data cannot be extracted
        """
        ...


class IValidator(Protocol):
    """Protocol for data validation."""

    def validate_part(self, data: dict[str, Any]) -> Part:
        """Validate and construct Part from raw data.

        Args:
            data: Raw part data dict

        Returns:
            Validated Part instance

        Raises:
            ValidationError: If data is invalid
        """
        ...

    def validate_vehicle(self, data: dict[str, Any]) -> Vehicle:
        """Validate and construct Vehicle from raw data.

        Args:
            data: Raw vehicle data dict

        Returns:
            Validated Vehicle instance

        Raises:
            ValidationError: If data is invalid
        """
        ...


class IExporter(Protocol):
    """Protocol for data export."""

    def export_parts(self, parts: list[Part], output_path: str) -> None:
        """Export parts to file.

        Args:
            parts: List of parts to export
            output_path: Path to output file

        Raises:
            IOError: If export fails
        """
        ...

    def export_compatibility(
        self, compatibility: list[VehicleCompatibility], output_path: str
    ) -> None:
        """Export compatibility data to file.

        Args:
            compatibility: List of compatibility mappings
            output_path: Path to output file

        Raises:
            IOError: If export fails
        """
        ...
