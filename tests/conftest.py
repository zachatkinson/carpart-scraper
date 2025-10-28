"""Test fixtures and configuration.

This module provides reusable test fixtures following the AAA (Arrange-Act-Assert) pattern.
All fixtures are designed for flexibility and can be easily customized per test.
"""

import json
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import httpx
import pytest
from bs4 import BeautifulSoup
from playwright.sync_api import Page
from pytest_mock import MockerFixture

from src.models.part import Part, PartImage
from src.models.vehicle import Vehicle, VehicleCompatibility
from src.scraper.fetcher import RespectfulFetcher
from src.scraper.parser import CSFParser

# ============================================================================
# Pydantic Model Fixtures
# ============================================================================


@pytest.fixture
def sample_part_image() -> PartImage:
    """Valid PartImage instance for testing.

    Returns:
        PartImage with primary image from S3
    """
    return PartImage(
        url="https://illumaware-digital-assets.s3.us-east-2.amazonaws.com/catalog196/applications/6087/large/large_3951_1_wm.jpg",
        alt_text="CSF Radiator 3951",
        is_primary=True,
    )


@pytest.fixture
def sample_part(sample_part_image: PartImage) -> Part:
    """Valid Part instance for testing.

    Args:
        sample_part_image: Primary image fixture

    Returns:
        Part with complete data
    """
    return Part(
        sku="CSF-3951",
        name="Radiator",
        price=Decimal("299.99"),
        description="High Performance Radiator with upgraded heavy duty core",
        category="Radiator",
        specifications={
            "Eng. Base": "1.5L L4 1497cc",
            "Aspiration": "Turbocharged",
            "Core Thickness": "30mm",
            "Tech Note": "O.E.M. style Plastic tank & Aluminum core",
        },
        images=[sample_part_image],
        manufacturer="CSF",
        in_stock=True,
        features=["Upgraded Heavy Duty Core. 7% Thicker 30mm vs OEM 27mm"],
        tech_notes="O.E.M. style Plastic tank & Aluminum core",
        position="Not Applicable",
    )


@pytest.fixture
def sample_vehicle() -> Vehicle:
    """Valid Vehicle instance for testing.

    Returns:
        Vehicle representing 2025 Honda Accord
    """
    return Vehicle(
        make="Honda",
        model="Accord",
        year=2025,
        submodel="Sport",
        engine="1.5L L4 1497cc",
        fuel_type="Gasoline",
        aspiration="Turbocharged",
    )


@pytest.fixture
def sample_vehicle_compatibility(sample_vehicle: Vehicle) -> VehicleCompatibility:
    """Valid VehicleCompatibility instance for testing.

    Args:
        sample_vehicle: Vehicle fixture

    Returns:
        VehicleCompatibility with multiple vehicles
    """
    return VehicleCompatibility(
        part_sku="CSF-3951",
        vehicles=[
            sample_vehicle,
            Vehicle(
                make="Honda",
                model="Accord",
                year=2024,
                engine="1.5L L4 1497cc",
                fuel_type="Gasoline",
                aspiration="Turbocharged",
            ),
            Vehicle(
                make="Honda",
                model="Accord",
                year=2023,
                engine="1.5L L4 1497cc",
                fuel_type="Gasoline",
                aspiration="Turbocharged",
            ),
        ],
        notes="Direct fit replacement",
    )


# ============================================================================
# HTML Test Data Fixtures
# ============================================================================


@pytest.fixture
def sample_html_application_page() -> str:
    """HTML string for application page with parts.

    Returns:
        HTML containing part listings with images, specs, and links
    """
    return """<!DOCTYPE html>
<html>
<head><title>Csf MyCarParts</title></head>
<body>
<div class="applications">
  <div class="panel result" id="radiator">
    <div class="panel-header">
      <div class="row">
        <div class="col">
          <h4 class="font-weight-bold">Radiator</h4>
        </div>
      </div>
    </div>
    <div class="panel-body">
      <div class="row app" id="test_app_1">
        <div class="col-2 pl-0 image_3951">
          <img class="img-thumbnail primary-image" alt="3951"
               src="https://illumaware-digital-assets.s3.us-east-2.amazonaws.com/catalog196/applications/6087/large/large_3951_1_wm.jpg">
        </div>
        <div class="col-8 p-0">
          <h4><a href="/items/3951">3951</a> - Radiator</h4>
          Position: <b>Not Applicable</b><br>
          <table class="table table-borderless table-ssm">
            <tbody>
              <tr>
                <td width="50%">Eng. Base: 1.5L L4 1497cc</td>
                <td width="50%">Aspiration: Turbocharged</td>
              </tr>
            </tbody>
          </table>
          <ul class="no-padding">
            <li>Upgraded Heavy Duty Core. 7% Thicker 30mm vs OEM 27mm</li>
          </ul>
        </div>
        <div class="col pr-0">
          <p><a class="btn btn-secondary col" href="/items/3951">Item Detail</a></p>
        </div>
      </div>
    </div>
  </div>
</div>
</body>
</html>"""


@pytest.fixture
def sample_html_detail_page() -> str:
    """HTML string for detail page with complete specifications.

    Returns:
        HTML containing full part details, specs, tech notes, and interchange data
    """
    return """<!DOCTYPE html>
<html>
<head><title>Csf MyCarParts</title></head>
<body>
<div class="panel">
  <div class="panel-header">
    <table class="float-left">
      <tr>
        <td class="selling-part">3883</td>
        <td class="item-type">Radiator</td>
      </tr>
    </table>
  </div>
  <div class="panel-body">
    <div class="row">
      <div class="col-6">
        <h5>High Performance Aluminum Radiator for Maximum Cooling</h5>
        <p>Radiator</p>
      </div>
    </div>
    <div class="row">
      <div class="col-12">
        <div class="item_attributes">
          <table class="table">
            <tr>
              <td>
                <table class="table table-borderless col-6">
                  <tr>
                    <td>Bottom Hose Fitting (in):</td>
                    <th class="text-left">1 1/4 Left (in)</th>
                  </tr>
                </table>
              </td>
              <td>
                <table class="table table-borderless col-6">
                  <tr>
                    <td>Box Height (in):</td>
                    <th class="text-left">5 1/4</th>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td>
                <table class="table table-borderless col-6">
                  <tr>
                    <td>Core Thickness (mm):</td>
                    <th class="text-left">30</th>
                  </tr>
                </table>
              </td>
              <td>
                <table class="table table-borderless col-6">
                  <tr>
                    <td>Tech Note:</td>
                    <th class="text-left">O.E.M. style Plastic tank & Aluminum core</th>
                  </tr>
                </table>
              </td>
            </tr>
          </table>
        </div>
      </div>
    </div>
    <div class="row">
      <div class="col-12">
        <h5>Interchange Information</h5>
        <table class="table">
          <thead>
            <tr>
              <th>Reference Number</th>
              <th>Reference Name</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>19010-5AA-A01</td>
              <td>OEM</td>
            </tr>
            <tr>
              <td>HO3010177</td>
              <td>Partslink</td>
            </tr>
            <tr>
              <td>13408</td>
              <td>DPI</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</div>
</body>
</html>"""


@pytest.fixture
def sample_ajax_response() -> dict[str, Any]:
    """JQuery AJAX response for vehicle selection.

    Returns:
        Dict representing AJAX response with years/models data
    """
    return {
        "years": [2025, 2024, 2023, 2022, 2021],
        "models": [
            {"id": "1", "name": "Accord"},
            {"id": "2", "name": "Civic"},
            {"id": "3", "name": "CR-V"},
        ],
    }


# ============================================================================
# File and Directory Fixtures
# ============================================================================


@pytest.fixture
def temp_json_file(sample_part: Part, tmp_path: Path) -> Path:
    """Temporary JSON file with parts data.

    Args:
        sample_part: Part fixture
        tmp_path: Pytest's temporary directory fixture

    Returns:
        Path to temporary JSON file

    Note:
        File is automatically cleaned up after test
    """
    temp_file = tmp_path / "test_parts.json"
    data = {
        "metadata": {
            "export_date": "2025-01-15T10:00:00Z",
            "total_parts": 1,
            "version": "1.0",
        },
        "parts": [sample_part.model_dump(mode="json")],
    }
    temp_file.write_text(json.dumps(data, indent=2))
    return temp_file


@pytest.fixture
def temp_export_dir(tmp_path: Path) -> Path:
    """Temporary directory for export operations.

    Args:
        tmp_path: Pytest's temporary directory fixture

    Returns:
        Path to temporary directory

    Note:
        Directory and contents are automatically cleaned up after test
    """
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    return export_dir


# ============================================================================
# Mock Object Fixtures
# ============================================================================


@pytest.fixture
def mock_fetcher(mocker: MockerFixture) -> Mock:
    """Mocked RespectfulFetcher for testing without network calls.

    Args:
        mocker: pytest-mock fixture

    Returns:
        Mock fetcher with pre-configured responses

    Example:
        >>> def test_scraper(mock_fetcher):
        ...     mock_fetcher.fetch.return_value.text = "<html>...</html>"
        ...     # Test code here
    """
    mock = mocker.Mock(spec=RespectfulFetcher)

    # Configure default successful response
    mock_response = mocker.Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.text = "<html><body>Test</body></html>"
    mock_response.content = b"<html><body>Test</body></html>"
    mock.fetch.return_value = mock_response

    # Configure browser fetch
    mock.fetch_with_browser.return_value = "<html><body>Test</body></html>"

    return mock


@pytest.fixture
def mock_parser(mocker: MockerFixture) -> Mock:
    """Mocked CSFParser for testing without HTML parsing.

    Args:
        mocker: pytest-mock fixture

    Returns:
        Mock parser with pre-configured extraction methods

    Example:
        >>> def test_validator(mock_parser):
        ...     mock_parser.extract_part_data.return_value = {"sku": "CSF-123"}
        ...     # Test code here
    """
    mock = mocker.Mock(spec=CSFParser)

    # Configure default parse response
    mock.parse.return_value = BeautifulSoup("<html></html>", "lxml")

    # Configure default extraction
    mock.extract_part_data.return_value = {
        "sku": "CSF-3951",
        "name": "Radiator",
        "price": None,
        "description": None,
        "category": "Radiator",
        "specifications": {"Eng. Base": "1.5L L4"},
        "images": [],
        "manufacturer": "CSF",
        "in_stock": True,
    }

    return mock


@pytest.fixture
def mock_playwright_page(mocker: MockerFixture) -> Mock:
    """Mocked Playwright Page for browser automation testing.

    Args:
        mocker: pytest-mock fixture

    Returns:
        Mock Playwright page with pre-configured methods

    Example:
        >>> def test_browser_scraper(mock_playwright_page):
        ...     mock_playwright_page.goto.return_value = None
        ...     mock_playwright_page.content.return_value = "<html>...</html>"
        ...     # Test code here
    """
    mock = mocker.Mock(spec=Page)

    # Configure navigation
    mock.goto.return_value = None

    # Configure content retrieval
    mock.content.return_value = "<html><body>Test Content</body></html>"

    # Configure element selection
    mock.query_selector.return_value = mocker.Mock()
    mock.query_selector_all.return_value = []

    # Configure waiting
    mock.wait_for_selector.return_value = None
    mock.wait_for_load_state.return_value = None

    return mock


# ============================================================================
# Factory Fixtures (for parameterized test data)
# ============================================================================


@pytest.fixture
def part_factory() -> Callable[..., Part]:
    """Factory for creating Part instances with custom attributes.

    Returns:
        Part factory function that can be called with custom kwargs

    Example:
        >>> def test_with_custom_part(part_factory):
        ...     part = part_factory(sku="CSF-999", price=Decimal("99.99"))
        ...     assert part.sku == "CSF-999"
    """

    def create_part(**overrides: Any) -> Part:  # noqa: ANN401
        """Create Part with optional overrides.

        Args:
            **overrides: Fields to override in default Part

        Returns:
            Part instance
        """
        defaults: dict[str, Any] = {
            "sku": "CSF-9999",
            "name": "Test Part",
            "price": Decimal("99.99"),
            "description": "Test description",
            "category": "Radiators",
            "specifications": {"test": "value"},
            "images": [],
            "manufacturer": "CSF",
            "in_stock": True,
            "features": ["Test feature"],
            "tech_notes": "Test notes",
            "position": "Front",
        }
        defaults.update(overrides)
        return Part(**defaults)

    return create_part


@pytest.fixture
def vehicle_factory() -> Callable[..., Vehicle]:
    """Factory for creating Vehicle instances with custom attributes.

    Returns:
        Vehicle factory function

    Example:
        >>> def test_with_custom_vehicle(vehicle_factory):
        ...     vehicle = vehicle_factory(make="Toyota", year=2023)
        ...     assert vehicle.make == "Toyota"
    """

    def create_vehicle(**overrides: Any) -> Vehicle:  # noqa: ANN401
        """Create Vehicle with optional overrides.

        Args:
            **overrides: Fields to override in default Vehicle

        Returns:
            Vehicle instance
        """
        defaults: dict[str, Any] = {
            "make": "Honda",
            "model": "Accord",
            "year": 2024,
            "submodel": None,
            "engine": "2.0L L4",
            "fuel_type": "Gasoline",
            "aspiration": "Naturally Aspirated",
        }
        defaults.update(overrides)
        return Vehicle(**defaults)

    return create_vehicle


# ============================================================================
# Pytest Configuration
# ============================================================================


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with custom markers and settings.

    Args:
        config: Pytest config object
    """
    config.addinivalue_line(
        "markers",
        "parser: Tests for HTML parsing functionality",
    )
    config.addinivalue_line(
        "markers",
        "fetcher: Tests for HTTP fetching functionality",
    )
    config.addinivalue_line(
        "markers",
        "models: Tests for Pydantic models",
    )
