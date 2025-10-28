"""Integration tests for end-to-end workflows.

This module tests complete workflows following the AAA (Arrange-Act-Assert) pattern:
- Scraping workflow: fetch → parse → validate → export
- CLI workflow: command → orchestrator → scraper → exporter
- Data validation pipeline: scraped data → validator → models
- Export workflows: parts → JSON export
- Error recovery in workflows: failures → retries → success

All tests use mocked external dependencies (network, browser) to ensure
predictable, fast, and reliable test execution.
"""

import json
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import httpx
import pytest
from playwright.sync_api import Browser, Page
from pytest_mock import MockerFixture

from src.exporters.json_exporter import JSONExporter
from src.models.part import Part
from src.models.vehicle import Vehicle, VehicleCompatibility
from src.scraper.fetcher import RespectfulFetcher
from src.scraper.orchestrator import ScraperOrchestrator
from src.scraper.parser import CSFParser
from src.scraper.validator import DataValidator

# ============================================================================
# Pytest Markers
# ============================================================================


@pytest.mark.integration
class TestScrapingWorkflow:
    """Test complete scraping workflow: fetch → parse → validate → export."""

    def test_workflow_fetch_parse_validate_succeeds_with_valid_html(
        self,
        mocker: MockerFixture,
        sample_html_application_page: str,
        tmp_path: Path,
    ) -> None:
        """Test complete scraping workflow with valid HTML data.

        Arrange: Mock fetcher, create parser and validator, prepare output dir
        Act: Fetch HTML → parse data → validate → create Part model
        Assert: Valid Part instance created with expected data
        """
        # Arrange
        mock_response = mocker.Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = sample_html_application_page
        mock_response.content = sample_html_application_page.encode()
        mock_response.raise_for_status = Mock()

        mocker.patch("src.scraper.fetcher.time.sleep")
        mocker.patch("src.scraper.fetcher.time.time", return_value=0.0)

        fetcher = RespectfulFetcher()
        mocker.patch.object(fetcher.client, "get", return_value=mock_response)

        parser = CSFParser()
        validator = DataValidator()

        # Act
        # Step 1: Fetch HTML
        response = fetcher.fetch("https://example.com/parts")
        html = response.text

        # Step 2: Parse HTML
        soup = parser.parse(html)
        part_data = parser.extract_part_data(soup)

        # Step 3: Add CSF- prefix if missing (workflow preprocessing)
        if "sku" in part_data and not part_data["sku"].startswith("CSF-"):
            part_data["sku"] = f"CSF-{part_data['sku']}"

        # Step 4: Validate and create model
        part = validator.validate_part(part_data)

        # Assert
        assert isinstance(part, Part)
        assert part.sku == "CSF-3951"  # Workflow added CSF- prefix
        assert "Radiator" in part.name  # Parser includes SKU in name
        assert part.category == "Radiator"
        assert part.manufacturer == "CSF"
        assert part.in_stock is True
        assert len(part.images) == 1
        assert part.images[0].is_primary is True

        # Cleanup
        fetcher.close()

    def test_workflow_fetch_parse_validate_export_creates_json_file(
        self,
        mocker: MockerFixture,
        sample_html_application_page: str,
        tmp_path: Path,
    ) -> None:
        """Test workflow from fetch to JSON export creates valid file.

        Arrange: Mock fetcher, setup parser/validator/exporter
        Act: Fetch → parse → validate → export to JSON
        Assert: JSON file created with valid structure
        """
        # Arrange
        mock_response = mocker.Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = sample_html_application_page
        mock_response.content = sample_html_application_page.encode()
        mock_response.raise_for_status = Mock()

        mocker.patch("src.scraper.fetcher.time.sleep")
        mocker.patch("src.scraper.fetcher.time.time", return_value=0.0)

        fetcher = RespectfulFetcher()
        mocker.patch.object(fetcher.client, "get", return_value=mock_response)

        parser = CSFParser()
        validator = DataValidator()
        exporter = JSONExporter(output_dir=tmp_path)

        # Act
        # Step 1: Fetch
        response = fetcher.fetch("https://example.com/parts")

        # Step 2: Parse
        soup = parser.parse(response.text)
        part_data = parser.extract_part_data(soup)

        # Step 3: Add CSF- prefix if missing (workflow preprocessing)
        if "sku" in part_data and not part_data["sku"].startswith("CSF-"):
            part_data["sku"] = f"CSF-{part_data['sku']}"

        # Step 4: Validate
        part = validator.validate_part(part_data)

        # Step 5: Export
        output_path = exporter.export_parts([part], filename="workflow_test.json")

        # Assert
        assert output_path.exists()
        with output_path.open(encoding="utf-8") as f:
            data = json.load(f)

        assert "metadata" in data
        assert "parts" in data
        assert data["metadata"]["total_parts"] == 1
        assert len(data["parts"]) == 1
        assert data["parts"][0]["sku"] == "CSF-3951"  # Validator adds CSF- prefix

        # Cleanup
        fetcher.close()

    def test_workflow_handles_network_error_gracefully(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
    ) -> None:
        """Test workflow handles network errors with proper exceptions.

        Arrange: Mock fetcher to raise network error
        Act: Attempt fetch → parse workflow
        Assert: Network error raised and propagated correctly
        """
        # Arrange
        mocker.patch("src.scraper.fetcher.time.sleep")
        request_error = httpx.RequestError("Connection failed")

        fetcher = RespectfulFetcher()
        mocker.patch.object(fetcher.client, "get", side_effect=request_error)

        # Act & Assert
        with pytest.raises(httpx.RequestError, match="Connection failed"):
            fetcher.fetch("https://example.com/parts")

        # Cleanup
        fetcher.close()

    def test_workflow_handles_http_error_gracefully(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
    ) -> None:
        """Test workflow handles HTTP errors (404, 500) gracefully.

        Arrange: Mock fetcher to return 404 error
        Act: Attempt fetch
        Assert: HTTPStatusError raised with correct status code
        """
        # Arrange
        mocker.patch("src.scraper.fetcher.time.sleep")
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 404

        http_error = httpx.HTTPStatusError(
            "Not Found",
            request=Mock(spec=httpx.Request),
            response=mock_response,
        )
        mock_response.raise_for_status = Mock(side_effect=http_error)

        fetcher = RespectfulFetcher()
        mocker.patch.object(fetcher.client, "get", return_value=mock_response)

        # Act & Assert
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            fetcher.fetch("https://example.com/notfound")

        assert exc_info.value.response.status_code == 404

        # Cleanup
        fetcher.close()

    def test_workflow_retries_on_failure_and_succeeds(
        self,
        mocker: MockerFixture,
        sample_html_application_page: str,
    ) -> None:
        """Test workflow retries on failure and eventually succeeds.

        Arrange: Mock fetcher to fail twice then succeed
        Act: Fetch with retries
        Assert: Request succeeds after retries
        """
        # Arrange
        mocker.patch("src.scraper.fetcher.time.sleep")

        mock_response_fail = Mock(spec=httpx.Response)
        mock_response_fail.status_code = 500
        http_error = httpx.HTTPStatusError(
            "Internal Server Error",
            request=Mock(spec=httpx.Request),
            response=mock_response_fail,
        )
        mock_response_fail.raise_for_status = Mock(side_effect=http_error)

        mock_response_success = Mock(spec=httpx.Response)
        mock_response_success.status_code = 200
        mock_response_success.text = sample_html_application_page
        mock_response_success.content = sample_html_application_page.encode()
        mock_response_success.raise_for_status = Mock()

        fetcher = RespectfulFetcher()
        mocker.patch.object(
            fetcher.client,
            "get",
            side_effect=[mock_response_fail, mock_response_fail, mock_response_success],
        )

        # Act
        response = fetcher.fetch("https://example.com/parts")

        # Assert
        assert response.status_code == 200
        assert fetcher.client.get.call_count == 3  # type: ignore[attr-defined]

        # Cleanup
        fetcher.close()


@pytest.mark.integration
class TestOrchestratorWorkflow:
    """Test orchestrator coordination of scraping components."""

    def test_orchestrator_initializes_all_components(self, tmp_path: Path) -> None:
        """Test orchestrator initializes all required components.

        Arrange: Create output directory
        Act: Initialize orchestrator
        Assert: All components (fetcher, parser, exporter) initialized
        """
        # Arrange & Act
        with ScraperOrchestrator(output_dir=tmp_path) as orchestrator:
            # Assert
            assert orchestrator.fetcher is not None
            assert isinstance(orchestrator.fetcher, RespectfulFetcher)
            assert orchestrator.html_parser is not None
            assert isinstance(orchestrator.html_parser, CSFParser)
            assert orchestrator.ajax_parser is not None
            assert orchestrator.exporter is not None
            assert isinstance(orchestrator.exporter, JSONExporter)
            assert orchestrator.output_dir == tmp_path
            assert orchestrator.incremental is False

    def test_orchestrator_tracks_unique_parts(self, tmp_path: Path) -> None:
        """Test orchestrator deduplicates parts by SKU.

        Arrange: Create orchestrator, prepare duplicate parts
        Act: Add parts to orchestrator state
        Assert: Only unique parts tracked
        """
        # Arrange
        with ScraperOrchestrator(output_dir=tmp_path) as orchestrator:
            part1 = Part(
                sku="CSF-12345",
                name="Radiator",
                category="Radiators",
            )
            part2 = Part(
                sku="CSF-12345",  # Duplicate SKU
                name="Radiator Updated",
                category="Radiators",
            )
            part3 = Part(
                sku="CSF-67890",
                name="Condenser",
                category="Condensers",
            )

            # Act
            orchestrator.unique_parts[part1.sku] = part1
            orchestrator.unique_parts[part2.sku] = part2  # Should overwrite
            orchestrator.unique_parts[part3.sku] = part3

            # Assert
            assert len(orchestrator.unique_parts) == 2
            assert orchestrator.unique_parts["CSF-12345"].name == "Radiator Updated"
            assert orchestrator.unique_parts["CSF-67890"].name == "Condenser"

    def test_orchestrator_exports_parts_successfully(
        self,
        tmp_path: Path,
        sample_part: Part,
    ) -> None:
        """Test orchestrator exports parts to JSON.

        Arrange: Create orchestrator with parts
        Act: Call export_data()
        Assert: JSON file created with parts
        """
        # Arrange
        with ScraperOrchestrator(output_dir=tmp_path) as orchestrator:
            orchestrator.unique_parts[sample_part.sku] = sample_part

            # Act
            paths = orchestrator.export_data()

            # Assert
            assert "parts" in paths
            assert paths["parts"].exists()

            with paths["parts"].open(encoding="utf-8") as f:
                data = json.load(f)

            assert data["metadata"]["total_parts"] == 1
            assert data["parts"][0]["sku"] == sample_part.sku

    def test_orchestrator_exports_compatibility_successfully(
        self,
        tmp_path: Path,
    ) -> None:
        """Test orchestrator exports compatibility data.

        Arrange: Create orchestrator with vehicle compatibility
        Act: Call export_data()
        Assert: Compatibility JSON created
        """
        # Arrange
        with ScraperOrchestrator(output_dir=tmp_path) as orchestrator:
            vehicles = [
                Vehicle(make="Honda", model="Accord", year=2025),
                Vehicle(make="Honda", model="Accord", year=2024),
            ]
            orchestrator.vehicle_compat["CSF-12345"] = vehicles

            # Act
            paths = orchestrator.export_data()

            # Assert
            assert "compatibility" in paths
            assert paths["compatibility"].exists()

            with paths["compatibility"].open(encoding="utf-8") as f:
                data = json.load(f)

            assert data["metadata"]["total_mappings"] == 1
            assert len(data["compatibility"]) == 1
            assert data["compatibility"][0]["part_sku"] == "CSF-12345"
            assert len(data["compatibility"][0]["vehicles"]) == 2

    def test_orchestrator_context_manager_cleans_up(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
    ) -> None:
        """Test orchestrator context manager properly cleans up resources.

        Arrange: Create orchestrator in context manager
        Act: Exit context
        Assert: close() called, resources cleaned up
        """
        # Arrange
        orchestrator = ScraperOrchestrator(output_dir=tmp_path)
        mock_close = mocker.patch.object(orchestrator, "close")

        # Act
        with orchestrator:
            pass

        # Assert
        mock_close.assert_called_once()

    def test_orchestrator_get_stats_returns_correct_counts(
        self,
        tmp_path: Path,
        sample_part: Part,
    ) -> None:
        """Test orchestrator get_stats returns accurate statistics.

        Arrange: Create orchestrator with parts and vehicles
        Act: Call get_stats()
        Assert: Correct counts returned
        """
        # Arrange
        with ScraperOrchestrator(output_dir=tmp_path) as orchestrator:
            orchestrator.unique_parts[sample_part.sku] = sample_part
            orchestrator.vehicle_compat[sample_part.sku] = [
                Vehicle(make="Honda", model="Accord", year=2025),
                Vehicle(make="Honda", model="Accord", year=2024),
            ]
            orchestrator.parts_scraped = 5

            # Act
            stats = orchestrator.get_stats()

            # Assert
            assert stats["unique_parts"] == 1
            assert stats["parts_scraped"] == 5
            assert stats["vehicles_tracked"] == 2


@pytest.mark.integration
class TestDataValidationPipeline:
    """Test data validation pipeline: scraped data → validator → models."""

    def test_pipeline_validates_complete_part_data(self) -> None:
        """Test validation pipeline with complete part data.

        Arrange: Create validator, prepare complete part data
        Act: Validate data
        Assert: Valid Part model created with all fields
        """
        # Arrange
        validator = DataValidator()
        complete_data: dict[str, Any] = {
            "sku": "CSF-12345",
            "name": "High Performance Radiator",
            "price": "299.99",
            "description": "Premium cooling solution",
            "category": "Radiators",
            "specifications": {
                "core_thickness": "30mm",
                "material": "Aluminum",
            },
            "images": [
                {
                    "url": "https://example.com/image.jpg",
                    "alt_text": "Front view",
                    "is_primary": True,
                }
            ],
            "features": ["High efficiency", "Direct fit"],
            "tech_notes": "Professional installation recommended",
            "position": "Front",
        }

        # Act
        part = validator.validate_part(complete_data)

        # Assert
        assert isinstance(part, Part)
        assert part.sku == "CSF-12345"
        assert part.name == "High Performance Radiator"
        assert part.price == Decimal("299.99")
        assert part.description == "Premium cooling solution"
        assert part.category == "Radiators"
        assert len(part.specifications) == 2
        assert len(part.images) == 1
        assert len(part.features) == 2
        assert part.tech_notes == "Professional installation recommended"
        assert part.position == "Front"

    def test_pipeline_validates_minimal_part_data(self) -> None:
        """Test validation pipeline with minimal required data.

        Arrange: Create validator, prepare minimal part data
        Act: Validate data
        Assert: Valid Part created with defaults for optional fields
        """
        # Arrange
        validator = DataValidator()
        minimal_data = {
            "sku": "CSF-67890",
            "name": "Condenser",
            "category": "Condensers",
        }

        # Act
        part = validator.validate_part(minimal_data)

        # Assert
        assert isinstance(part, Part)
        assert part.sku == "CSF-67890"
        assert part.name == "Condenser"
        assert part.category == "Condensers"
        assert part.price is None
        assert part.description is None
        assert part.manufacturer == "CSF"
        assert part.in_stock is True

    def test_pipeline_validates_batch_of_parts(self) -> None:
        """Test validation pipeline processes multiple parts.

        Arrange: Create validator, prepare batch of parts
        Act: Validate batch
        Assert: All valid parts returned
        """
        # Arrange
        validator = DataValidator()
        parts_data = [
            {"sku": "CSF-1", "name": "Part 1", "category": "Cat1"},
            {"sku": "CSF-2", "name": "Part 2", "category": "Cat2"},
            {"sku": "CSF-3", "name": "Part 3", "category": "Cat3"},
        ]

        # Act
        parts = validator.validate_batch(parts_data)

        # Assert
        assert len(parts) == 3
        assert all(isinstance(p, Part) for p in parts)
        assert [p.sku for p in parts] == ["CSF-1", "CSF-2", "CSF-3"]

    def test_pipeline_skips_invalid_parts_in_batch(self) -> None:
        """Test validation pipeline skips invalid parts in batch.

        Arrange: Create validator, prepare batch with invalid parts
        Act: Validate batch
        Assert: Only valid parts returned, invalid skipped
        """
        # Arrange
        validator = DataValidator()
        mixed_data = [
            {"sku": "CSF-1", "name": "Part 1", "category": "Cat1"},  # Valid
            {"name": "Part 2", "category": "Cat2"},  # Invalid: missing SKU
            {"sku": "CSF-3", "name": "Part 3", "category": "Cat3"},  # Valid
            {"sku": "CSF-4", "name": "", "category": "Cat4"},  # Invalid: empty name
        ]

        # Act
        parts = validator.validate_batch(mixed_data)

        # Assert
        assert len(parts) == 2
        assert parts[0].sku == "CSF-1"
        assert parts[1].sku == "CSF-3"

    def test_pipeline_validates_vehicle_compatibility(self) -> None:
        """Test validation pipeline for vehicle compatibility data.

        Arrange: Create validator, prepare compatibility data
        Act: Validate compatibility
        Assert: Valid VehicleCompatibility created
        """
        # Arrange
        validator = DataValidator()
        compat_data = {
            "part_sku": "CSF-12345",
            "vehicles": [
                {"make": "Honda", "model": "Accord", "year": 2025},
                {"make": "Honda", "model": "Civic", "year": 2024},
            ],
            "notes": "Direct fit replacement",
        }

        # Act
        compatibility = validator.validate_compatibility(compat_data)

        # Assert
        assert isinstance(compatibility, VehicleCompatibility)
        assert compatibility.part_sku == "CSF-12345"
        assert len(compatibility.vehicles) == 2
        assert compatibility.vehicles[0].make == "Honda"
        assert compatibility.notes == "Direct fit replacement"


@pytest.mark.integration
class TestExportWorkflow:
    """Test export workflows: parts → JSON export."""

    def test_export_workflow_creates_valid_json_structure(
        self,
        tmp_path: Path,
        sample_part: Part,
    ) -> None:
        """Test export workflow creates valid JSON with metadata.

        Arrange: Create exporter and parts
        Act: Export parts
        Assert: JSON has correct structure and metadata
        """
        # Arrange
        exporter = JSONExporter(output_dir=tmp_path)
        parts = [sample_part]

        # Act
        output_path = exporter.export_parts(parts, filename="export_test.json")

        # Assert
        assert output_path.exists()

        with output_path.open(encoding="utf-8") as f:
            data = json.load(f)

        assert "metadata" in data
        assert "parts" in data
        assert data["metadata"]["version"] == "1.0"
        assert data["metadata"]["total_parts"] == 1
        assert "export_date" in data["metadata"]
        assert isinstance(data["parts"], list)

    def test_export_workflow_handles_multiple_parts(
        self,
        tmp_path: Path,
        part_factory: Callable[..., Part],
    ) -> None:
        """Test export workflow with multiple parts.

        Arrange: Create exporter and multiple parts
        Act: Export all parts
        Assert: All parts included in export
        """
        # Arrange
        exporter = JSONExporter(output_dir=tmp_path)
        parts = [
            part_factory(sku="CSF-1", name="Part 1"),
            part_factory(sku="CSF-2", name="Part 2"),
            part_factory(sku="CSF-3", name="Part 3"),
        ]

        # Act
        output_path = exporter.export_parts(parts)

        # Assert
        with output_path.open(encoding="utf-8") as f:
            data = json.load(f)

        assert data["metadata"]["total_parts"] == 3
        assert len(data["parts"]) == 3
        assert [p["sku"] for p in data["parts"]] == ["CSF-1", "CSF-2", "CSF-3"]

    def test_export_workflow_creates_compatibility_export(
        self,
        tmp_path: Path,
        sample_vehicle_compatibility: VehicleCompatibility,
    ) -> None:
        """Test export workflow for compatibility data.

        Arrange: Create exporter and compatibility data
        Act: Export compatibility
        Assert: Valid compatibility JSON created
        """
        # Arrange
        exporter = JSONExporter(output_dir=tmp_path)
        compatibility = [sample_vehicle_compatibility]

        # Act
        output_path = exporter.export_compatibility(compatibility)

        # Assert
        assert output_path.exists()

        with output_path.open(encoding="utf-8") as f:
            data = json.load(f)

        assert "metadata" in data
        assert "compatibility" in data
        assert data["metadata"]["total_mappings"] == 1
        assert len(data["compatibility"]) == 1

    def test_export_workflow_creates_hierarchical_structure(
        self,
        tmp_path: Path,
        sample_part: Part,
        sample_vehicle_compatibility: VehicleCompatibility,
    ) -> None:
        """Test export workflow creates hierarchical year→make→model structure.

        Arrange: Create exporter, parts, and compatibility
        Act: Export hierarchical
        Assert: Correct nested structure created
        """
        # Arrange
        exporter = JSONExporter(output_dir=tmp_path)
        parts_by_sku = {sample_part.sku: sample_part}
        compatibility = [sample_vehicle_compatibility]

        # Act
        output_path = exporter.export_hierarchical(
            compatibility,
            parts_by_sku,
            filename="hierarchical_test.json",
        )

        # Assert
        assert output_path.exists()

        with output_path.open(encoding="utf-8") as f:
            data = json.load(f)

        assert "metadata" in data
        assert "data" in data
        assert data["metadata"]["structure"] == "year > make > model > parts"

        # Verify hierarchical structure
        hierarchy = data["data"]
        assert isinstance(hierarchy, dict)
        # Should have year as top level
        assert any(str(year).isdigit() for year in hierarchy)

    def test_export_workflow_validates_exported_file(
        self,
        tmp_path: Path,
        sample_part: Part,
    ) -> None:
        """Test export workflow includes validation step.

        Arrange: Create exporter and export parts
        Act: Validate exported file
        Assert: Validation returns True for valid export
        """
        # Arrange
        exporter = JSONExporter(output_dir=tmp_path)
        output_path = exporter.export_parts([sample_part])

        # Act
        is_valid = exporter.validate_export(output_path)

        # Assert
        assert is_valid is True

    def test_export_workflow_incremental_export_appends_data(
        self,
        tmp_path: Path,
        part_factory: Callable[..., Part],
    ) -> None:
        """Test incremental export workflow appends to existing file.

        Arrange: Create exporter, export initial batch, prepare second batch
        Act: Export second batch with append=True
        Assert: Both batches in final export
        """
        # Arrange
        exporter = JSONExporter(output_dir=tmp_path)
        filename = "incremental_test.json"

        part1 = part_factory(sku="CSF-1", name="Part 1")
        part2 = part_factory(sku="CSF-2", name="Part 2")

        # Export first batch
        exporter.export_parts_incremental([part1], filename=filename, append=False)

        # Act
        # Export second batch with append
        output_path = exporter.export_parts_incremental(
            [part2],
            filename=filename,
            append=True,
        )

        # Assert
        with output_path.open(encoding="utf-8") as f:
            data = json.load(f)

        assert data["metadata"]["total_parts"] == 2
        assert len(data["parts"]) == 2
        assert data["parts"][0]["sku"] == "CSF-1"
        assert data["parts"][1]["sku"] == "CSF-2"


@pytest.mark.integration
class TestErrorRecoveryWorkflow:
    """Test error recovery in workflows: failures → retries → success."""

    def test_recovery_workflow_retries_on_network_timeout(
        self,
        mocker: MockerFixture,
        sample_html_application_page: str,
    ) -> None:
        """Test workflow recovers from network timeout with retry.

        Arrange: Mock fetcher to timeout once then succeed
        Act: Fetch with automatic retry
        Assert: Request succeeds after retry
        """
        # Arrange
        mocker.patch("src.scraper.fetcher.time.sleep")

        mock_response_timeout = Mock(spec=httpx.Response)
        mock_response_timeout.status_code = 500
        timeout_error = httpx.HTTPStatusError(
            "Timeout",
            request=Mock(spec=httpx.Request),
            response=mock_response_timeout,
        )
        mock_response_timeout.raise_for_status = Mock(side_effect=timeout_error)

        mock_response_success = Mock(spec=httpx.Response)
        mock_response_success.status_code = 200
        mock_response_success.text = sample_html_application_page
        mock_response_success.content = sample_html_application_page.encode()
        mock_response_success.raise_for_status = Mock()

        fetcher = RespectfulFetcher()
        mocker.patch.object(
            fetcher.client,
            "get",
            side_effect=[mock_response_timeout, mock_response_success],
        )

        # Act
        response = fetcher.fetch("https://example.com/parts")

        # Assert
        assert response.status_code == 200
        assert fetcher.client.get.call_count == 2  # type: ignore[attr-defined]

        # Cleanup
        fetcher.close()

    def test_recovery_workflow_handles_invalid_html_gracefully(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Test workflow handles invalid HTML without crashing.

        Arrange: Mock fetcher with invalid HTML
        Act: Fetch and parse invalid HTML
        Assert: Parser raises appropriate error
        """
        # Arrange
        invalid_html = "<html><unclosed-tag>"
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = invalid_html
        mock_response.content = invalid_html.encode()
        mock_response.raise_for_status = Mock()

        mocker.patch("src.scraper.fetcher.time.sleep")
        mocker.patch("src.scraper.fetcher.time.time", return_value=0.0)

        fetcher = RespectfulFetcher()
        mocker.patch.object(fetcher.client, "get", return_value=mock_response)
        parser = CSFParser()

        # Act
        response = fetcher.fetch("https://example.com/parts")
        soup = parser.parse(response.text)

        # Parsing invalid HTML should work (BeautifulSoup is forgiving)
        # But extraction should fail gracefully
        with pytest.raises(ValueError, match="Missing required fields"):
            parser.extract_part_data(soup)

        # Cleanup
        fetcher.close()

    def test_recovery_workflow_continues_after_validation_error(self) -> None:
        """Test workflow continues processing after validation error.

        Arrange: Create validator, prepare batch with invalid data
        Act: Validate batch with mixed valid/invalid data
        Assert: Valid parts processed, invalid skipped
        """
        # Arrange
        validator = DataValidator()
        mixed_data = [
            {"sku": "CSF-1", "name": "Part 1", "category": "Cat1"},  # Valid
            {"name": "Part 2"},  # Invalid: missing SKU
            {"sku": "CSF-3", "name": "Part 3", "category": "Cat3"},  # Valid
        ]

        # Act
        parts = validator.validate_batch(mixed_data)

        # Assert
        assert len(parts) == 2  # Only valid parts
        assert parts[0].sku == "CSF-1"
        assert parts[1].sku == "CSF-3"

    def test_recovery_workflow_handles_export_failure_gracefully(
        self,
        tmp_path: Path,
        sample_part: Part,
        mocker: MockerFixture,
    ) -> None:
        """Test workflow handles export failure gracefully.

        Arrange: Create exporter, mock file write to fail
        Act: Attempt export
        Assert: Appropriate error raised
        """
        # Arrange
        exporter = JSONExporter(output_dir=tmp_path)

        # Make the directory read-only to cause write failure
        tmp_path.chmod(0o444)  # Read-only

        # Act & Assert
        try:
            with pytest.raises((PermissionError, OSError)):
                exporter.export_parts([sample_part], filename="readonly.json")
        finally:
            # Cleanup: restore permissions
            tmp_path.chmod(0o755)

    def test_recovery_workflow_browser_fallback_on_ajax_failure(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Test workflow can fallback to browser fetch when AJAX fails.

        Arrange: Mock fetcher with browser support
        Act: Use fetch_with_browser as fallback
        Assert: Browser fetch succeeds
        """
        # Arrange
        mocker.patch("src.scraper.fetcher.time.sleep")

        mock_page = Mock(spec=Page)
        mock_page.content.return_value = "<html><body>Browser content</body></html>"
        mock_page.goto = Mock()

        mock_browser = Mock(spec=Browser)
        mock_browser.new_page.return_value = mock_page
        mock_browser.close = Mock()

        mock_playwright = Mock()
        mock_playwright.chromium.launch.return_value = mock_browser

        mock_sync_playwright = mocker.patch("src.scraper.fetcher.sync_playwright")
        mock_sync_playwright.return_value.__enter__.return_value = mock_playwright

        fetcher = RespectfulFetcher()

        # Act
        html = fetcher.fetch_with_browser("https://example.com/ajax-page")

        # Assert
        assert html == "<html><body>Browser content</body></html>"
        mock_browser.close.assert_called_once()

        # Cleanup
        fetcher.close()
