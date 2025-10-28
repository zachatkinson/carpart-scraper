"""Example tests demonstrating fixture usage.

This module shows how to use the fixtures defined in conftest.py
following the AAA (Arrange-Act-Assert) pattern.
"""

from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock

import pytest

from src.models.part import Part, PartImage
from src.models.vehicle import Vehicle, VehicleCompatibility


@pytest.mark.models
class TestPartFixtures:
    """Tests demonstrating Part-related fixtures."""

    def test_sample_part_image_fixture(self, sample_part_image: PartImage) -> None:
        """Test that sample_part_image provides valid PartImage.

        Demonstrates: Basic fixture usage

        Args:
            sample_part_image: PartImage fixture
        """
        # Arrange - fixture provides the data

        # Act - inspect the fixture
        url = sample_part_image.url
        is_primary = sample_part_image.is_primary

        # Assert - verify fixture is correctly configured
        assert url.startswith("https://")
        assert is_primary is True
        assert sample_part_image.alt_text is not None

    def test_sample_part_fixture(self, sample_part: Part) -> None:
        """Test that sample_part provides complete Part.

        Demonstrates: Fixture with dependencies

        Args:
            sample_part: Part fixture
        """
        # Arrange - fixture provides the data

        # Act - inspect the fixture
        sku = sample_part.sku
        category = sample_part.category

        # Assert - verify fixture is correctly configured
        assert sku.startswith("CSF-")
        assert category == "Radiator"
        assert sample_part.price is not None
        assert sample_part.price > Decimal("0")
        assert len(sample_part.images) > 0

    def test_part_factory_with_defaults(self, part_factory: Callable[..., Part]) -> None:
        """Test part_factory creates Part with defaults.

        Demonstrates: Factory fixture usage

        Args:
            part_factory: Part factory fixture
        """
        # Arrange
        # (No arrangement needed)

        # Act
        part = part_factory()

        # Assert
        assert part.sku == "CSF-9999"
        assert part.name == "Test Part"
        assert part.price == Decimal("99.99")

    def test_part_factory_with_overrides(self, part_factory: Callable[..., Part]) -> None:
        """Test part_factory creates Part with custom values.

        Demonstrates: Factory fixture with overrides

        Args:
            part_factory: Part factory fixture
        """
        # Arrange
        custom_sku = "CSF-CUSTOM"
        custom_price = Decimal("199.99")

        # Act
        part = part_factory(sku=custom_sku, price=custom_price)

        # Assert
        assert part.sku == custom_sku
        assert part.price == custom_price
        # Other fields use defaults
        assert part.manufacturer == "CSF"


@pytest.mark.models
class TestVehicleFixtures:
    """Tests demonstrating Vehicle-related fixtures."""

    def test_sample_vehicle_fixture(self, sample_vehicle: Vehicle) -> None:
        """Test that sample_vehicle provides valid Vehicle.

        Demonstrates: Basic vehicle fixture

        Args:
            sample_vehicle: Vehicle fixture
        """
        # Arrange - fixture provides the data

        # Act - inspect the fixture
        year = sample_vehicle.year
        make = sample_vehicle.make

        # Assert - verify fixture is correctly configured
        assert year == 2025
        assert make == "Honda"
        assert sample_vehicle.model == "Accord"

    def test_sample_vehicle_compatibility_fixture(
        self, sample_vehicle_compatibility: VehicleCompatibility
    ) -> None:
        """Test that sample_vehicle_compatibility provides valid compatibility data.

        Demonstrates: Complex fixture with relationships

        Args:
            sample_vehicle_compatibility: VehicleCompatibility fixture
        """
        # Arrange - fixture provides the data

        # Act - inspect the fixture
        year_range = sample_vehicle_compatibility.get_year_range()
        vehicle_count = len(sample_vehicle_compatibility.vehicles)

        # Assert - verify fixture is correctly configured
        assert year_range is not None
        assert vehicle_count == 3
        assert sample_vehicle_compatibility.part_sku.startswith("CSF-")

    def test_vehicle_factory_with_defaults(self, vehicle_factory: Callable[..., Vehicle]) -> None:
        """Test vehicle_factory creates Vehicle with defaults.

        Demonstrates: Vehicle factory usage

        Args:
            vehicle_factory: Vehicle factory fixture
        """
        # Arrange
        # (No arrangement needed)

        # Act
        vehicle = vehicle_factory()

        # Assert
        assert vehicle.make == "Honda"
        assert vehicle.model == "Accord"
        assert vehicle.year == 2024

    def test_vehicle_factory_with_overrides(self, vehicle_factory: Callable[..., Vehicle]) -> None:
        """Test vehicle_factory creates Vehicle with custom values.

        Demonstrates: Vehicle factory with overrides

        Args:
            vehicle_factory: Vehicle factory fixture
        """
        # Arrange
        custom_make = "Toyota"
        custom_year = 2023

        # Act
        vehicle = vehicle_factory(make=custom_make, year=custom_year)

        # Assert
        assert vehicle.make == custom_make
        assert vehicle.year == custom_year
        # Other fields use defaults
        assert vehicle.fuel_type == "Gasoline"


@pytest.mark.parser
class TestHtmlFixtures:
    """Tests demonstrating HTML fixture usage."""

    def test_sample_html_application_page(self, sample_html_application_page: str) -> None:
        """Test that sample_html_application_page provides valid HTML.

        Demonstrates: HTML string fixture

        Args:
            sample_html_application_page: HTML fixture
        """
        # Arrange - fixture provides the HTML

        # Act - inspect the HTML
        has_doctype = sample_html_application_page.startswith("<!DOCTYPE html>")
        has_part_data = "3951" in sample_html_application_page

        # Assert - verify fixture has expected content
        assert has_doctype
        assert has_part_data
        assert "Radiator" in sample_html_application_page

    def test_sample_html_detail_page(self, sample_html_detail_page: str) -> None:
        """Test that sample_html_detail_page provides valid HTML.

        Demonstrates: Detail page HTML fixture

        Args:
            sample_html_detail_page: HTML fixture
        """
        # Arrange - fixture provides the HTML

        # Act - inspect the HTML
        has_specs = "Core Thickness" in sample_html_detail_page
        has_interchange = "Interchange Information" in sample_html_detail_page

        # Assert - verify fixture has expected content
        assert has_specs
        assert has_interchange
        assert "Tech Note" in sample_html_detail_page


class TestFileFixtures:
    """Tests demonstrating file and directory fixtures."""

    def test_temp_json_file(self, temp_json_file: Path) -> None:
        """Test that temp_json_file provides valid JSON file.

        Demonstrates: Temporary file fixture

        Args:
            temp_json_file: Path to temporary JSON file
        """
        # Arrange - fixture provides the file

        # Act - read the file
        file_exists = temp_json_file.exists()
        is_json = temp_json_file.suffix == ".json"

        # Assert - verify fixture provides valid file
        assert file_exists
        assert is_json
        assert temp_json_file.stat().st_size > 0

    def test_temp_export_dir(self, temp_export_dir: Path) -> None:
        """Test that temp_export_dir provides valid directory.

        Demonstrates: Temporary directory fixture

        Args:
            temp_export_dir: Path to temporary directory
        """
        # Arrange - fixture provides the directory

        # Act - inspect the directory
        dir_exists = temp_export_dir.exists()
        is_directory = temp_export_dir.is_dir()

        # Assert - verify fixture provides valid directory
        assert dir_exists
        assert is_directory

    def test_temp_export_dir_can_write_files(self, temp_export_dir: Path) -> None:
        """Test that files can be written to temp_export_dir.

        Demonstrates: Using temporary directory for file operations

        Args:
            temp_export_dir: Path to temporary directory
        """
        # Arrange
        test_file = temp_export_dir / "test.json"

        # Act - write file to temporary directory
        test_file.write_text('{"test": "data"}')

        # Assert - verify file was written
        assert test_file.exists()
        assert "test" in test_file.read_text()


@pytest.mark.fetcher
class TestMockFixtures:
    """Tests demonstrating mock fixture usage."""

    def test_mock_fetcher_default_response(self, mock_fetcher: Mock) -> None:
        """Test that mock_fetcher provides configured response.

        Demonstrates: Mock fetcher fixture

        Args:
            mock_fetcher: Mocked RespectfulFetcher
        """
        # Arrange - fixture provides configured mock

        # Act - use the mock fetcher
        response = mock_fetcher.fetch("https://example.com")

        # Assert - verify mock behavior
        assert response.status_code == 200
        assert "Test" in response.text
        mock_fetcher.fetch.assert_called_once_with("https://example.com")

    def test_mock_parser_default_extraction(self, mock_parser: Mock) -> None:
        """Test that mock_parser provides configured extraction.

        Demonstrates: Mock parser fixture

        Args:
            mock_parser: Mocked CSFParser
        """
        # Arrange - fixture provides configured mock

        # Act - use the mock parser
        soup = mock_parser.parse("<html></html>")
        data = mock_parser.extract_part_data(soup)

        # Assert - verify mock behavior
        assert data["sku"].startswith("CSF-")
        assert data["manufacturer"] == "CSF"
        mock_parser.parse.assert_called_once()
        mock_parser.extract_part_data.assert_called_once()

    def test_mock_playwright_page_navigation(self, mock_playwright_page: Mock) -> None:
        """Test that mock_playwright_page provides configured page.

        Demonstrates: Mock Playwright page fixture

        Args:
            mock_playwright_page: Mocked Playwright page
        """
        # Arrange - fixture provides configured mock

        # Act - use the mock page
        mock_playwright_page.goto("https://example.com")
        content = mock_playwright_page.content()

        # Assert - verify mock behavior
        assert "Test Content" in content
        mock_playwright_page.goto.assert_called_once_with("https://example.com")
        mock_playwright_page.content.assert_called_once()
