"""Unit tests for ScraperOrchestrator resilience features.

Tests cover:
- FailureTracker recording and summarization
- _build_hierarchy error handling (continues on failed make/year)
- Checkpoint save/restore with parts data
- Completeness report with previous export comparison
- Failure stats in scrape_all return value
"""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest
from pytest_mock import MockerFixture

from src.models.part import Part
from src.models.vehicle import Vehicle
from src.scraper.ajax_parser import AJAXParsingError, AJAXResponseParser
from src.scraper.etag_store import ETagStore
from src.scraper.hierarchy_cache import HierarchyCache
from src.scraper.orchestrator import MAKES, DeduplicationResult, FailureTracker, ScraperOrchestrator


class TestFailureTracker:
    """Test FailureTracker dataclass."""

    def test_record_adds_failure(self) -> None:
        """Test record() adds a FailureRecord to the list."""
        # Arrange
        tracker = FailureTracker()

        # Act
        tracker.record(
            phase="hierarchy",
            identifier="make:Honda",
            error_type="AJAXParsingError",
            error_message="No .html() call found",
        )

        # Assert
        assert len(tracker.failures) == 1
        assert tracker.failures[0].phase == "hierarchy"
        assert tracker.failures[0].identifier == "make:Honda"

    def test_get_summary_counts_by_phase(self) -> None:
        """Test get_summary() returns counts grouped by phase."""
        # Arrange
        tracker = FailureTracker()
        tracker.record("hierarchy", "make:Honda", "Error", "msg")
        tracker.record("hierarchy", "make:Toyota", "Error", "msg")
        tracker.record("application", "1234", "Error", "msg")
        tracker.record("detail", "CSF-100", "Error", "msg", is_retryable=False)

        # Act
        summary = tracker.get_summary()

        # Assert
        assert summary["total_failures"] == 4
        assert summary["by_phase"]["hierarchy"] == 2
        assert summary["by_phase"]["application"] == 1
        assert summary["by_phase"]["detail"] == 1
        assert summary["retryable"] == 3
        assert summary["permanent"] == 1

    def test_get_failed_identifiers_filters_by_phase(self) -> None:
        """Test get_failed_identifiers() returns only identifiers for given phase."""
        # Arrange
        tracker = FailureTracker()
        tracker.record("hierarchy", "make:Honda", "Error", "msg")
        tracker.record("application", "1234", "Error", "msg")
        tracker.record("hierarchy", "make:Toyota", "Error", "msg")

        # Act
        hierarchy_ids = tracker.get_failed_identifiers("hierarchy")
        app_ids = tracker.get_failed_identifiers("application")

        # Assert
        assert hierarchy_ids == ["make:Honda", "make:Toyota"]
        assert app_ids == ["1234"]

    def test_to_dicts_serializes_all_records(self) -> None:
        """Test to_dicts() returns serializable dicts."""
        # Arrange
        tracker = FailureTracker()
        tracker.record("hierarchy", "make:Honda", "AJAXParsingError", "msg", is_retryable=True)

        # Act
        result = tracker.to_dicts()

        # Assert
        assert len(result) == 1
        assert result[0]["phase"] == "hierarchy"
        assert result[0]["identifier"] == "make:Honda"
        assert result[0]["is_retryable"] is True

    def test_empty_tracker_returns_zero_summary(self) -> None:
        """Test get_summary() with no failures returns zeros."""
        # Arrange
        tracker = FailureTracker()

        # Act
        summary = tracker.get_summary()

        # Assert
        assert summary["total_failures"] == 0
        assert summary["by_phase"] == {}
        assert summary["retryable"] == 0
        assert summary["permanent"] == 0


class TestEnumerateMakes:
    """Test _enumerate_makes() dynamic make discovery from homepage."""

    HOMEPAGE_HTML = """
    <html><body>
    <ul>
        <li><a data-remote="true" href="/get_year_by_make/3">Honda</a></li>
        <li><a data-remote="true" href="/get_year_by_make/4">Toyota</a></li>
        <li><a data-remote="true" href="/get_year_by_make/99">NewBrand</a></li>
    </ul>
    </body></html>
    """

    def test_enumerate_makes_parses_homepage(self) -> None:
        """Test _enumerate_makes() extracts makes from homepage HTML."""
        # Arrange
        mock_fetcher = Mock()
        mock_response = Mock(spec=httpx.Response)
        mock_response.text = self.HOMEPAGE_HTML
        mock_fetcher.fetch.return_value = mock_response

        orchestrator = ScraperOrchestrator.__new__(ScraperOrchestrator)
        orchestrator.fetcher = mock_fetcher

        # Act
        makes = orchestrator._enumerate_makes()  # noqa: SLF001

        # Assert
        assert makes == {3: "Honda", 4: "Toyota", 99: "NewBrand"}
        mock_fetcher.fetch.assert_called_once_with("https://csf.mycarparts.com/")

    def test_enumerate_makes_falls_back_on_fetch_error(self) -> None:
        """Test _enumerate_makes() returns MAKES constant when homepage fetch fails."""
        # Arrange
        mock_fetcher = Mock()
        mock_fetcher.fetch.side_effect = httpx.ConnectError("Connection refused")

        orchestrator = ScraperOrchestrator.__new__(ScraperOrchestrator)
        orchestrator.fetcher = mock_fetcher

        # Act
        makes = orchestrator._enumerate_makes()  # noqa: SLF001

        # Assert — falls back to static MAKES
        assert makes == MAKES

    def test_enumerate_makes_falls_back_on_empty_html(self) -> None:
        """Test _enumerate_makes() returns MAKES when no links found."""
        # Arrange
        mock_fetcher = Mock()
        mock_response = Mock(spec=httpx.Response)
        mock_response.text = "<html><body><p>No dropdown</p></body></html>"
        mock_fetcher.fetch.return_value = mock_response

        orchestrator = ScraperOrchestrator.__new__(ScraperOrchestrator)
        orchestrator.fetcher = mock_fetcher

        # Act
        makes = orchestrator._enumerate_makes()  # noqa: SLF001

        # Assert — falls back to static MAKES
        assert makes == MAKES

    def test_enumerate_makes_logs_new_makes(self, mocker: MockerFixture) -> None:
        """Test _enumerate_makes() logs makes not in the MAKES fallback."""
        # Arrange
        mock_fetcher = Mock()
        mock_response = Mock(spec=httpx.Response)
        mock_response.text = self.HOMEPAGE_HTML
        mock_fetcher.fetch.return_value = mock_response

        orchestrator = ScraperOrchestrator.__new__(ScraperOrchestrator)
        orchestrator.fetcher = mock_fetcher

        mock_logger = mocker.patch("src.scraper.orchestrator.logger")

        # Act
        makes = orchestrator._enumerate_makes()  # noqa: SLF001

        # Assert — make 99 "NewBrand" is not in MAKES, should be logged
        mock_logger.info.assert_any_call("new_make_discovered", make_id=99, make_name="NewBrand")
        assert 99 in makes

    def test_build_hierarchy_uses_discovered_makes(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Test _build_hierarchy() calls _enumerate_makes() for make list."""
        # Arrange
        mock_fetcher = Mock()
        mock_ajax = Mock(spec=AJAXResponseParser)

        mock_response_years = Mock(spec=httpx.Response)
        mock_response_years.text = "years_js"
        mock_response_models = Mock(spec=httpx.Response)
        mock_response_models.text = "models_js"

        mock_fetcher.fetch.side_effect = [mock_response_years, mock_response_models]

        mock_ajax.parse_year_response.return_value = {100: "2024"}
        mock_ajax.parse_model_response.return_value = {8000: "Camry"}

        orchestrator = ScraperOrchestrator.__new__(ScraperOrchestrator)
        orchestrator.fetcher = mock_fetcher
        orchestrator.ajax_parser = mock_ajax
        orchestrator.failure_tracker = FailureTracker()
        orchestrator.hierarchy_cache = HierarchyCache(tmp_path / "hc.json")

        # Mock _enumerate_makes to return a single make
        mocker.patch.object(orchestrator, "_enumerate_makes", return_value={4: "Toyota"})

        # Act
        hierarchy = orchestrator._build_hierarchy()  # noqa: SLF001

        # Assert
        orchestrator._enumerate_makes.assert_called_once()  # noqa: SLF001
        assert len(hierarchy) == 1
        assert hierarchy[0]["make"] == "Toyota"


class TestBuildHierarchyErrorHandling:
    """Test _build_hierarchy continues on individual make/year failures."""

    def test_build_hierarchy_continues_on_failed_make(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Test _build_hierarchy skips failed make and continues with others."""
        # Arrange
        mock_fetcher = Mock()
        mock_ajax = Mock(spec=AJAXResponseParser)

        # Honda fails, Toyota succeeds
        honda_error = AJAXParsingError("No .html() call found")

        mock_response_toyota_years = Mock(spec=httpx.Response)
        mock_response_toyota_years.text = "years_js"

        mock_response_toyota_models = Mock(spec=httpx.Response)
        mock_response_toyota_models.text = "models_js"

        # fetch() calls: Honda years fails, Toyota years succeeds, Toyota models succeeds
        mock_fetcher.fetch = Mock(
            side_effect=[
                honda_error,  # Honda years
                mock_response_toyota_years,  # Toyota years
                mock_response_toyota_models,  # Toyota 2024 models
            ]
        )

        mock_ajax.parse_year_response.return_value = {100: "2024"}
        mock_ajax.parse_model_response.return_value = {8000: "Camry"}

        orchestrator = ScraperOrchestrator.__new__(ScraperOrchestrator)
        orchestrator.fetcher = mock_fetcher
        orchestrator.ajax_parser = mock_ajax
        orchestrator.failure_tracker = FailureTracker()
        orchestrator.hierarchy_cache = HierarchyCache(tmp_path / "hc.json")

        # Mock _enumerate_makes to return Honda and Toyota
        mocker.patch.object(
            orchestrator, "_enumerate_makes", return_value={3: "Honda", 4: "Toyota"}
        )

        # Act
        hierarchy = orchestrator._build_hierarchy()  # noqa: SLF001

        # Assert - Toyota came through, Honda was skipped
        assert len(hierarchy) == 1
        assert hierarchy[0]["make"] == "Toyota"
        assert hierarchy[0]["model"] == "Camry"

        # Failure was recorded
        failures = orchestrator.failure_tracker.get_failed_identifiers("hierarchy")
        assert "make:Honda" in failures

    def test_build_hierarchy_continues_on_failed_year(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Test _build_hierarchy skips failed year and continues with others."""
        # Arrange
        mock_fetcher = Mock()
        mock_ajax = Mock(spec=AJAXResponseParser)

        mock_response_years = Mock(spec=httpx.Response)
        mock_response_years.text = "years_js"

        mock_response_models_fail = AJAXParsingError("No .html() call found")
        mock_response_models_ok = Mock(spec=httpx.Response)
        mock_response_models_ok.text = "models_js"

        mock_fetcher.fetch = Mock(
            side_effect=[
                mock_response_years,  # Honda years (succeeds)
                mock_response_models_fail,  # 2024 models (fails)
                mock_response_models_ok,  # 2023 models (succeeds)
            ]
        )

        mock_ajax.parse_year_response.return_value = {100: "2024", 101: "2023"}
        mock_ajax.parse_model_response.return_value = {8000: "Accord"}

        orchestrator = ScraperOrchestrator.__new__(ScraperOrchestrator)
        orchestrator.fetcher = mock_fetcher
        orchestrator.ajax_parser = mock_ajax
        orchestrator.failure_tracker = FailureTracker()
        orchestrator.hierarchy_cache = HierarchyCache(tmp_path / "hc.json")

        mocker.patch.object(orchestrator, "_enumerate_makes", return_value={3: "Honda"})

        # Act
        hierarchy = orchestrator._build_hierarchy()  # noqa: SLF001

        # Assert - 2023 came through, 2024 was skipped
        assert len(hierarchy) == 1
        assert hierarchy[0]["year"] == "2023"

        # Failure was recorded
        failures = orchestrator.failure_tracker.get_failed_identifiers("hierarchy")
        assert any("2024" in f for f in failures)


class TestCheckpointWithPartsData:
    """Test checkpoint save/restore with actual parts and compatibility data."""

    def test_checkpoint_saves_and_restores_parts(self, tmp_path: Path) -> None:
        """Test checkpoint saves parts data and restores it on load."""
        # Arrange
        orchestrator = ScraperOrchestrator(
            output_dir=tmp_path / "exports",
            checkpoint_dir=tmp_path / "checkpoints",
        )

        # Add some parts
        part1 = Part(
            sku="CSF-1001",
            name="Radiator A",
            category="Radiator",
        )
        part2 = Part(
            sku="CSF-1002",
            name="Condenser B",
            category="Condenser",
        )
        orchestrator.unique_parts = {"CSF-1001": part1, "CSF-1002": part2}

        vehicle = Vehicle(make="Honda", model="Accord", year=2024)
        orchestrator.vehicle_compat = {"CSF-1001": [vehicle]}
        orchestrator.processed_application_ids = {100, 200}
        orchestrator.parts_scraped = 5

        # Act - Save checkpoint
        checkpoint_path = orchestrator._save_checkpoint(  # noqa: SLF001
            make_filter=None,
            year_filter=None,
        )

        # Create a new orchestrator and restore
        orchestrator2 = ScraperOrchestrator(
            output_dir=tmp_path / "exports",
            checkpoint_dir=tmp_path / "checkpoints",
        )
        orchestrator2._load_checkpoint(checkpoint_path)  # noqa: SLF001

        # Assert - Parts restored
        assert len(orchestrator2.unique_parts) == 2
        assert "CSF-1001" in orchestrator2.unique_parts
        assert "CSF-1002" in orchestrator2.unique_parts
        assert orchestrator2.unique_parts["CSF-1001"].name == "Radiator A"

        # Vehicle compat restored
        assert "CSF-1001" in orchestrator2.vehicle_compat
        assert len(orchestrator2.vehicle_compat["CSF-1001"]) == 1
        assert orchestrator2.vehicle_compat["CSF-1001"][0].make == "Honda"

        # Other state restored
        assert orchestrator2.processed_application_ids == {100, 200}
        assert orchestrator2.parts_scraped == 5

        # Cleanup
        orchestrator.close()
        orchestrator2.close()

    def test_checkpoint_backward_compatible_with_old_format(self, tmp_path: Path) -> None:
        """Test loading old checkpoint without parts_data still works."""
        # Arrange
        checkpoint_dir = tmp_path / "checkpoints"
        checkpoint_dir.mkdir()

        old_checkpoint = {
            "timestamp": "20250101_000000",
            "make_filter": None,
            "year_filter": None,
            "processed_application_ids": [100, 200],
            "unique_parts_count": 5,
            "parts_scraped": 10,
            "vehicles_tracked": 3,
            # No parts_data or vehicle_compat fields
        }
        checkpoint_path = checkpoint_dir / "checkpoint_all_20250101_000000.json"
        checkpoint_path.write_text(json.dumps(old_checkpoint))

        orchestrator = ScraperOrchestrator(
            output_dir=tmp_path / "exports",
            checkpoint_dir=checkpoint_dir,
        )

        # Act
        orchestrator._load_checkpoint(checkpoint_path)  # noqa: SLF001

        # Assert - Basic state restored
        assert orchestrator.processed_application_ids == {100, 200}
        assert orchestrator.parts_scraped == 10
        # No parts data (old format)
        assert len(orchestrator.unique_parts) == 0
        assert len(orchestrator.vehicle_compat) == 0

        # Cleanup
        orchestrator.close()


class TestCompletenessReport:
    """Test generate_completeness_report() method."""

    def test_completeness_report_detects_missing_parts(self, tmp_path: Path) -> None:
        """Test report detects parts missing compared to previous export."""
        # Arrange
        orchestrator = ScraperOrchestrator(
            output_dir=tmp_path / "exports",
            checkpoint_dir=tmp_path / "checkpoints",
        )

        # Current scrape has 2 parts
        orchestrator.unique_parts = {
            "CSF-1001": Part(sku="CSF-1001", name="Part A", category="Radiator"),
            "CSF-1003": Part(sku="CSF-1003", name="Part C", category="Radiator"),
        }

        # Previous export had 3 parts (CSF-1002 is now missing)
        previous_data = [
            {"sku": "CSF-1001", "name": "Part A"},
            {"sku": "CSF-1002", "name": "Part B"},
            {"sku": "CSF-1003", "name": "Part C"},
        ]
        previous_path = tmp_path / "previous_parts.json"
        previous_path.write_text(json.dumps(previous_data))

        # Act
        report = orchestrator.generate_completeness_report(
            previous_export_path=previous_path,
        )

        # Assert
        assert report["current_parts_count"] == 2
        assert "CSF-1002" in report["missing_skus"]
        assert report["missing_count"] == 1
        assert report["new_count"] == 0

        # Cleanup
        orchestrator.close()

    def test_completeness_report_detects_new_parts(self, tmp_path: Path) -> None:
        """Test report detects new parts not in previous export."""
        # Arrange
        orchestrator = ScraperOrchestrator(
            output_dir=tmp_path / "exports",
            checkpoint_dir=tmp_path / "checkpoints",
        )

        orchestrator.unique_parts = {
            "CSF-1001": Part(sku="CSF-1001", name="Part A", category="Radiator"),
            "CSF-1002": Part(sku="CSF-1002", name="Part B", category="Radiator"),
            "CSF-1004": Part(sku="CSF-1004", name="Part D", category="Radiator"),
        }

        previous_data = [
            {"sku": "CSF-1001", "name": "Part A"},
            {"sku": "CSF-1002", "name": "Part B"},
        ]
        previous_path = tmp_path / "previous_parts.json"
        previous_path.write_text(json.dumps(previous_data))

        # Act
        report = orchestrator.generate_completeness_report(
            previous_export_path=previous_path,
        )

        # Assert
        assert "CSF-1004" in report["new_skus"]
        assert report["new_count"] == 1
        assert report["missing_count"] == 0

        # Cleanup
        orchestrator.close()

    def test_completeness_report_without_previous_export(self, tmp_path: Path) -> None:
        """Test report works without previous export for comparison."""
        # Arrange
        orchestrator = ScraperOrchestrator(
            output_dir=tmp_path / "exports",
            checkpoint_dir=tmp_path / "checkpoints",
        )
        orchestrator.unique_parts = {
            "CSF-1001": Part(sku="CSF-1001", name="Part A", category="Radiator"),
        }

        # Act
        report = orchestrator.generate_completeness_report()

        # Assert
        assert report["current_parts_count"] == 1
        assert "missing_skus" not in report

        # Cleanup
        orchestrator.close()

    def test_completeness_report_includes_failure_info(self, tmp_path: Path) -> None:
        """Test report includes failure tracker information."""
        # Arrange
        orchestrator = ScraperOrchestrator(
            output_dir=tmp_path / "exports",
            checkpoint_dir=tmp_path / "checkpoints",
        )
        orchestrator.failure_tracker.record("application", "1234", "RuntimeError", "timeout")
        orchestrator.failure_tracker.record("detail", "CSF-5000", "HTTPError", "404")

        # Act
        report = orchestrator.generate_completeness_report()

        # Assert
        assert "1234" in report["failed_applications"]
        assert "CSF-5000" in report["failed_details"]
        assert report["failure_summary"]["total_failures"] == 2

        # Cleanup
        orchestrator.close()


class TestContentHash:
    """Test _content_hash() static method for change detection."""

    def test_content_hash_same_for_identical_parts(self) -> None:
        """Test two parts with same content fields produce the same hash."""
        # Arrange
        part_a = Part(sku="CSF-1001", name="Radiator A", category="Radiator")
        part_b = Part(sku="CSF-1001", name="Radiator A", category="Radiator")

        # Act
        hash_a = ScraperOrchestrator._content_hash(part_a)  # noqa: SLF001
        hash_b = ScraperOrchestrator._content_hash(part_b)  # noqa: SLF001

        # Assert
        assert hash_a == hash_b

    def test_content_hash_differs_for_changed_name(self) -> None:
        """Test changing a content field changes the hash."""
        # Arrange
        part_a = Part(sku="CSF-1001", name="Radiator A", category="Radiator")
        part_b = Part(sku="CSF-1001", name="Radiator B", category="Radiator")

        # Act
        hash_a = ScraperOrchestrator._content_hash(part_a)  # noqa: SLF001
        hash_b = ScraperOrchestrator._content_hash(part_b)  # noqa: SLF001

        # Assert
        assert hash_a != hash_b

    def test_content_hash_ignores_scraped_at(self) -> None:
        """Test that different scraped_at timestamps don't change the hash."""
        # Arrange
        part_a = Part(
            sku="CSF-1001",
            name="Radiator A",
            category="Radiator",
            scraped_at=datetime(2025, 1, 1, tzinfo=UTC),
        )
        part_b = Part(
            sku="CSF-1001",
            name="Radiator A",
            category="Radiator",
            scraped_at=datetime(2025, 6, 15, tzinfo=UTC),
        )

        # Act
        hash_a = ScraperOrchestrator._content_hash(part_a)  # noqa: SLF001
        hash_b = ScraperOrchestrator._content_hash(part_b)  # noqa: SLF001

        # Assert
        assert hash_a == hash_b

    def test_content_hash_ignores_description(self) -> None:
        """Test that description (detail-enriched field) doesn't change the hash."""
        # Arrange
        part_a = Part(sku="CSF-1001", name="Radiator A", category="Radiator")
        part_b = Part(
            sku="CSF-1001",
            name="Radiator A",
            category="Radiator",
            description="Enriched description from detail page",
        )

        # Act
        hash_a = ScraperOrchestrator._content_hash(part_a)  # noqa: SLF001
        hash_b = ScraperOrchestrator._content_hash(part_b)  # noqa: SLF001

        # Assert
        assert hash_a == hash_b


class TestLoadPreviousExport:
    """Test load_previous_export() method."""

    def test_load_previous_export_populates_unique_parts(self, tmp_path: Path) -> None:
        """Test that loading previous export pre-populates unique_parts."""
        # Arrange
        orchestrator = ScraperOrchestrator(
            output_dir=tmp_path / "exports",
            checkpoint_dir=tmp_path / "checkpoints",
        )
        exports_dir = tmp_path / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)

        parts_data = [
            {"sku": "CSF-1001", "name": "Radiator A", "category": "Radiator"},
            {"sku": "CSF-1002", "name": "Condenser B", "category": "Condenser"},
        ]
        (exports_dir / "parts.json").write_text(json.dumps(parts_data))

        # Act
        orchestrator.load_previous_export()

        # Assert
        assert len(orchestrator.unique_parts) == 2
        assert "CSF-1001" in orchestrator.unique_parts
        assert "CSF-1002" in orchestrator.unique_parts
        assert orchestrator.unique_parts["CSF-1001"].name == "Radiator A"

        # Cleanup
        orchestrator.close()

    def test_load_previous_export_returns_hashes(self, tmp_path: Path) -> None:
        """Test that loading previous export returns SKU -> hash mapping."""
        # Arrange
        orchestrator = ScraperOrchestrator(
            output_dir=tmp_path / "exports",
            checkpoint_dir=tmp_path / "checkpoints",
        )
        exports_dir = tmp_path / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)

        parts_data = [
            {"sku": "CSF-1001", "name": "Radiator A", "category": "Radiator"},
            {"sku": "CSF-1002", "name": "Condenser B", "category": "Condenser"},
        ]
        (exports_dir / "parts.json").write_text(json.dumps(parts_data))

        # Act
        hashes = orchestrator.load_previous_export()

        # Assert
        assert len(hashes) == 2
        assert "CSF-1001" in hashes
        assert "CSF-1002" in hashes
        # Hashes should be 32-char hex strings (MD5)
        assert len(hashes["CSF-1001"]) == 32
        assert all(c in "0123456789abcdef" for c in hashes["CSF-1001"])

        # Cleanup
        orchestrator.close()

    def test_load_previous_export_missing_file(self, tmp_path: Path) -> None:
        """Test that missing file returns empty dict without error."""
        # Arrange
        orchestrator = ScraperOrchestrator(
            output_dir=tmp_path / "exports",
            checkpoint_dir=tmp_path / "checkpoints",
        )

        # Act
        hashes = orchestrator.load_previous_export()

        # Assert
        assert hashes == {}
        assert len(orchestrator.unique_parts) == 0

        # Cleanup
        orchestrator.close()

    def test_load_previous_export_loads_compatibility(self, tmp_path: Path) -> None:
        """Test that loading previous export also loads compatibility.json."""
        # Arrange
        orchestrator = ScraperOrchestrator(
            output_dir=tmp_path / "exports",
            checkpoint_dir=tmp_path / "checkpoints",
        )
        exports_dir = tmp_path / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)

        parts_data = [
            {"sku": "CSF-1001", "name": "Radiator A", "category": "Radiator"},
        ]
        compat_data = [
            {
                "sku": "CSF-1001",
                "vehicles": [
                    {"make": "Honda", "model": "Accord", "year": 2024},
                ],
            },
        ]
        (exports_dir / "parts.json").write_text(json.dumps(parts_data))
        (exports_dir / "compatibility.json").write_text(json.dumps(compat_data))

        # Act
        orchestrator.load_previous_export()

        # Assert
        assert "CSF-1001" in orchestrator.vehicle_compat
        assert len(orchestrator.vehicle_compat["CSF-1001"]) == 1
        assert orchestrator.vehicle_compat["CSF-1001"][0].make == "Honda"

        # Cleanup
        orchestrator.close()


class TestDeduplicateWithChanges:
    """Test _deduplicate_and_track() with previous_hashes for change detection."""

    def test_deduplicate_detects_new_part(self, tmp_path: Path) -> None:
        """Test that a part not in previous hashes is flagged as new."""
        # Arrange
        orchestrator = ScraperOrchestrator(
            output_dir=tmp_path / "exports",
            checkpoint_dir=tmp_path / "checkpoints",
        )
        part = Part(sku="CSF-2001", name="New Radiator", category="Radiator")
        vehicle = Vehicle(make="Honda", model="Civic", year=2024)
        previous_hashes: dict[str, str] = {"CSF-1001": "abc123"}

        # Act
        result = orchestrator._deduplicate_and_track(  # noqa: SLF001
            [part], vehicle, previous_hashes
        )

        # Assert
        assert "CSF-2001" in result.new_skus
        assert len(result.changed_skus) == 0

        # Cleanup
        orchestrator.close()

    def test_deduplicate_detects_changed_part(self, tmp_path: Path) -> None:
        """Test that a part with different content hash is flagged as changed."""
        # Arrange
        orchestrator = ScraperOrchestrator(
            output_dir=tmp_path / "exports",
            checkpoint_dir=tmp_path / "checkpoints",
        )

        # Pre-populate with old version
        old_part = Part(sku="CSF-1001", name="Old Name", category="Radiator")
        orchestrator.unique_parts["CSF-1001"] = old_part
        old_hash = ScraperOrchestrator._content_hash(old_part)  # noqa: SLF001

        # New version with changed name
        new_part = Part(sku="CSF-1001", name="Updated Name", category="Radiator")
        vehicle = Vehicle(make="Honda", model="Civic", year=2024)
        previous_hashes = {"CSF-1001": old_hash}

        # Act
        result = orchestrator._deduplicate_and_track(  # noqa: SLF001
            [new_part], vehicle, previous_hashes
        )

        # Assert
        assert "CSF-1001" in result.changed_skus
        assert len(result.new_skus) == 0

        # Cleanup
        orchestrator.close()

    def test_deduplicate_unchanged_part_not_flagged(self, tmp_path: Path) -> None:
        """Test that an unchanged part is neither new nor changed."""
        # Arrange
        orchestrator = ScraperOrchestrator(
            output_dir=tmp_path / "exports",
            checkpoint_dir=tmp_path / "checkpoints",
        )

        part = Part(sku="CSF-1001", name="Radiator A", category="Radiator")
        # Pre-populate so it's not "new"
        orchestrator.unique_parts["CSF-1001"] = part
        content_hash = ScraperOrchestrator._content_hash(part)  # noqa: SLF001

        vehicle = Vehicle(make="Honda", model="Civic", year=2024)
        previous_hashes = {"CSF-1001": content_hash}

        # Act
        result = orchestrator._deduplicate_and_track(  # noqa: SLF001
            [part], vehicle, previous_hashes
        )

        # Assert
        assert len(result.new_skus) == 0
        assert len(result.changed_skus) == 0

        # Cleanup
        orchestrator.close()

    def test_deduplicate_returns_deduplication_result(self, tmp_path: Path) -> None:
        """Test that return type is DeduplicationResult NamedTuple."""
        # Arrange
        orchestrator = ScraperOrchestrator(
            output_dir=tmp_path / "exports",
            checkpoint_dir=tmp_path / "checkpoints",
        )
        part = Part(sku="CSF-1001", name="Radiator", category="Radiator")
        vehicle = Vehicle(make="Honda", model="Civic", year=2024)

        # Act
        result = orchestrator._deduplicate_and_track(  # noqa: SLF001
            [part], vehicle
        )

        # Assert
        assert isinstance(result, DeduplicationResult)
        assert hasattr(result, "new_skus")
        assert hasattr(result, "changed_skus")

        # Cleanup
        orchestrator.close()


class TestBuildHierarchyFilters:
    """Test _build_hierarchy with make_filter and year_filter."""

    def test_build_hierarchy_with_make_filter(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test _build_hierarchy only processes matching make when make_filter is set."""
        # Arrange
        mock_fetcher = Mock()
        mock_ajax = Mock(spec=AJAXResponseParser)

        mock_response_years = Mock(spec=httpx.Response)
        mock_response_years.text = "years_js"
        mock_response_models = Mock(spec=httpx.Response)
        mock_response_models.text = "models_js"

        mock_fetcher.fetch = Mock(
            side_effect=[
                mock_response_years,  # Honda years
                mock_response_models,  # Honda 2024 models
            ]
        )

        mock_ajax.parse_year_response.return_value = {100: "2024"}
        mock_ajax.parse_model_response.return_value = {8000: "Civic"}

        orchestrator = ScraperOrchestrator.__new__(ScraperOrchestrator)
        orchestrator.fetcher = mock_fetcher
        orchestrator.ajax_parser = mock_ajax
        orchestrator.failure_tracker = FailureTracker()
        orchestrator.hierarchy_cache = HierarchyCache(tmp_path / "hc.json")

        mocker.patch.object(
            orchestrator, "_enumerate_makes", return_value={3: "Honda", 4: "Toyota"}
        )

        # Act
        hierarchy = orchestrator._build_hierarchy(make_filter="Honda")  # noqa: SLF001

        # Assert - Only Honda is processed, Toyota is skipped entirely
        assert len(hierarchy) == 1
        assert hierarchy[0]["make"] == "Honda"
        assert hierarchy[0]["model"] == "Civic"
        # fetch() was called only twice (Honda years + Honda 2024 models)
        assert mock_fetcher.fetch.call_count == 2

    def test_build_hierarchy_with_year_filter(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test _build_hierarchy filters years when year_filter is set."""
        # Arrange
        mock_fetcher = Mock()
        mock_ajax = Mock(spec=AJAXResponseParser)

        mock_response_years = Mock(spec=httpx.Response)
        mock_response_years.text = "years_js"
        mock_response_models = Mock(spec=httpx.Response)
        mock_response_models.text = "models_js"

        # Only 1 model call needed (2024 is filtered out, only 2023 remains)
        mock_fetcher.fetch = Mock(
            side_effect=[
                mock_response_years,  # Honda years
                mock_response_models,  # Honda 2023 models
            ]
        )

        mock_ajax.parse_year_response.return_value = {100: "2024", 101: "2023"}
        mock_ajax.parse_model_response.return_value = {9000: "Accord"}

        orchestrator = ScraperOrchestrator.__new__(ScraperOrchestrator)
        orchestrator.fetcher = mock_fetcher
        orchestrator.ajax_parser = mock_ajax
        orchestrator.failure_tracker = FailureTracker()
        orchestrator.hierarchy_cache = HierarchyCache(tmp_path / "hc.json")

        mocker.patch.object(orchestrator, "_enumerate_makes", return_value={3: "Honda"})

        # Act
        hierarchy = orchestrator._build_hierarchy(year_filter=2023)  # noqa: SLF001

        # Assert - Only year 2023 is processed
        assert len(hierarchy) == 1
        assert hierarchy[0]["year"] == "2023"
        assert hierarchy[0]["model"] == "Accord"


class TestScrapeApplicationPage:
    """Test _scrape_application_page method."""

    def test_scrape_application_page_returns_parts(self) -> None:
        """Test _scrape_application_page fetches, parses, and validates parts."""
        # Arrange
        orchestrator = ScraperOrchestrator.__new__(ScraperOrchestrator)
        orchestrator.fetcher = Mock()
        orchestrator.html_parser = Mock()
        orchestrator.validator = Mock()

        orchestrator.fetcher.fetch_with_browser.return_value = "<html>parts page</html>"
        mock_soup = Mock()
        orchestrator.html_parser.parse.return_value = mock_soup

        raw_parts_data = [
            {"sku": "CSF-1001", "name": "Radiator", "vehicle_qualifiers": {}},
        ]
        orchestrator.html_parser.extract_parts_from_application_page.return_value = raw_parts_data

        validated_part = Part(sku="CSF-1001", name="Radiator", category="Radiator")
        orchestrator.validator.validate_batch.return_value = [validated_part]

        config = {"make": "Honda", "model": "Accord", "year": "2020"}

        # Act
        parts, parts_data = orchestrator._scrape_application_page(8430, config)  # noqa: SLF001

        # Assert
        assert len(parts) == 1
        assert parts[0].sku == "CSF-1001"
        assert parts_data == raw_parts_data
        orchestrator.fetcher.fetch_with_browser.assert_called_once_with(
            "https://csf.mycarparts.com/applications/8430"
        )
        orchestrator.html_parser.parse.assert_called_once_with("<html>parts page</html>")
        orchestrator.html_parser.extract_parts_from_application_page.assert_called_once_with(
            mock_soup
        )
        orchestrator.validator.validate_batch.assert_called_once_with(raw_parts_data)


class TestFetchDetailPage:
    """Test _fetch_detail_page method."""

    def test_fetch_detail_page_returns_detail_data(self) -> None:
        """Test _fetch_detail_page fetches and parses detail page."""
        # Arrange
        orchestrator = ScraperOrchestrator.__new__(ScraperOrchestrator)
        orchestrator.fetcher = Mock()
        orchestrator.html_parser = Mock()

        orchestrator.fetcher.fetch_with_browser.return_value = "<html>detail</html>"
        mock_soup = Mock()
        orchestrator.html_parser.parse.return_value = mock_soup

        detail_data = {
            "full_description": "High performance radiator",
            "specifications": {"Material": "Aluminum"},
        }
        orchestrator.html_parser.extract_detail_page_data.return_value = detail_data

        # Act
        result = orchestrator._fetch_detail_page("CSF-3562")  # noqa: SLF001

        # Assert
        assert result == detail_data
        orchestrator.fetcher.fetch_with_browser.assert_called_once_with(
            "https://csf.autocaredata.com/items/3562"
        )
        orchestrator.html_parser.parse.assert_called_once_with("<html>detail</html>")
        orchestrator.html_parser.extract_detail_page_data.assert_called_once_with(
            mock_soup, "CSF-3562"
        )


class TestEnrichPartWithDetails:
    """Test _enrich_part_with_details method."""

    def test_enrich_part_with_description_specs_and_images(self) -> None:
        """Test enrichment updates description, specifications, and filters large images."""
        # Arrange
        orchestrator = ScraperOrchestrator.__new__(ScraperOrchestrator)
        orchestrator.image_processor = Mock()

        original_part = Part(
            sku="CSF-1001",
            name="Radiator A",
            category="Radiator",
            specifications={"Weight": "10 lbs"},
        )
        orchestrator.unique_parts = {"CSF-1001": original_part}

        detail_data = {
            "full_description": "Premium high-flow radiator",
            "specifications": {"Material": "Aluminum", "Rows": "2"},
            "tech_notes": "Requires adapter bracket",
            "interchange_data": [
                {"reference_number": "30048", "reference_type": "OEM"},
            ],
            "additional_images": [
                {"url": "https://img.example.com/large.jpg", "size": "large"},
                {"url": "https://img.example.com/thumb.jpg", "size": "thumbnail"},
            ],
        }

        processed_images = [
            {"url": "https://cdn.example.com/1001.avif", "alt_text": None, "is_primary": False}
        ]
        orchestrator.image_processor.process_images.return_value = processed_images

        # Act
        orchestrator._enrich_part_with_details("CSF-1001", detail_data)  # noqa: SLF001

        # Assert
        enriched = orchestrator.unique_parts["CSF-1001"]
        assert enriched.description == "Premium high-flow radiator"
        # Specs merged: original Weight + new Material + Rows
        assert enriched.specifications["Weight"] == "10 lbs"
        assert enriched.specifications["Material"] == "Aluminum"
        assert enriched.specifications["Rows"] == "2"
        assert enriched.tech_notes == "Requires adapter bracket"
        assert len(enriched.interchange_numbers) == 1
        assert enriched.interchange_numbers[0].reference_number == "30048"
        # All images passed to image_processor (parser handles large-only filtering)
        orchestrator.image_processor.process_images.assert_called_once_with(
            "CSF-1001",
            [
                {"url": "https://img.example.com/large.jpg", "size": "large"},
                {"url": "https://img.example.com/thumb.jpg", "size": "thumbnail"},
            ],
        )

    def test_enrich_part_missing_sku_logs_warning(self) -> None:
        """Test enrichment with missing SKU does nothing."""
        # Arrange
        orchestrator = ScraperOrchestrator.__new__(ScraperOrchestrator)
        orchestrator.unique_parts = {}

        # Act
        orchestrator._enrich_part_with_details(  # noqa: SLF001
            "CSF-9999", {"full_description": "Nope"}
        )

        # Assert - No error raised, unique_parts still empty
        assert len(orchestrator.unique_parts) == 0


class TestCreateVehicleFromConfig:
    """Test _create_vehicle_from_config method."""

    def test_create_vehicle_with_qualifiers(self) -> None:
        """Test creating Vehicle with engine, aspiration, and qualifiers."""
        # Arrange
        orchestrator = ScraperOrchestrator.__new__(ScraperOrchestrator)
        config = {"make": "Honda", "model": "Accord", "year": "2020"}
        qualifiers = {
            "engine": "2.0L L4 1993cc",
            "aspiration": "Turbocharged",
            "qualifiers": ["Manual"],
        }

        # Act
        vehicle = orchestrator._create_vehicle_from_config(config, qualifiers)  # noqa: SLF001

        # Assert
        assert vehicle.make == "Honda"
        assert vehicle.model == "Accord"
        assert vehicle.year == 2020
        assert vehicle.engine == "2.0L L4 1993cc"
        assert vehicle.aspiration == "Turbocharged"
        assert vehicle.qualifiers == ["Manual"]

    def test_create_vehicle_without_qualifiers(self) -> None:
        """Test creating Vehicle with None qualifiers defaults to empty dict."""
        # Arrange
        orchestrator = ScraperOrchestrator.__new__(ScraperOrchestrator)
        config = {"make": "Toyota", "model": "Camry", "year": "2024"}

        # Act
        vehicle = orchestrator._create_vehicle_from_config(config, None)  # noqa: SLF001

        # Assert
        assert vehicle.make == "Toyota"
        assert vehicle.model == "Camry"
        assert vehicle.year == 2024
        assert vehicle.engine is None
        assert vehicle.aspiration is None
        assert vehicle.qualifiers == []


class TestLoadCheckpointErrors:
    """Test _load_checkpoint error conditions."""

    def test_missing_field_raises_value_error(self, tmp_path: Path) -> None:
        """Test checkpoint missing required field raises ValueError."""
        # Arrange
        checkpoint_dir = tmp_path / "checkpoints"
        checkpoint_dir.mkdir()
        checkpoint_path = checkpoint_dir / "checkpoint_all_20250101_000000.json"
        # Missing 'processed_application_ids' and 'parts_scraped'
        checkpoint_path.write_text(json.dumps({"timestamp": "20250101_000000"}))

        orchestrator = ScraperOrchestrator.__new__(ScraperOrchestrator)
        orchestrator.unique_parts = {}
        orchestrator.vehicle_compat = {}

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid checkpoint file"):
            orchestrator._load_checkpoint(checkpoint_path)  # noqa: SLF001

    def test_missing_file_raises_file_not_found_error(self, tmp_path: Path) -> None:
        """Test non-existent checkpoint path raises FileNotFoundError."""
        # Arrange
        orchestrator = ScraperOrchestrator.__new__(ScraperOrchestrator)
        non_existent = tmp_path / "does_not_exist.json"

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="Checkpoint file not found"):
            orchestrator._load_checkpoint(non_existent)  # noqa: SLF001


class TestGetLatestCheckpoint:
    """Test _get_latest_checkpoint method."""

    def test_returns_latest_checkpoint(self, tmp_path: Path) -> None:
        """Test returns the most recent checkpoint file."""
        # Arrange
        orchestrator = ScraperOrchestrator.__new__(ScraperOrchestrator)
        orchestrator.checkpoint_dir = tmp_path

        # Create checkpoint files with different timestamps
        (tmp_path / "checkpoint_all_20250101_100000.json").write_text("{}")
        (tmp_path / "checkpoint_all_20250102_100000.json").write_text("{}")
        (tmp_path / "checkpoint_all_20250101_120000.json").write_text("{}")

        # Act
        latest = orchestrator._get_latest_checkpoint()  # noqa: SLF001

        # Assert - Sorted reverse, so 20250102 is first
        assert latest is not None
        assert "20250102" in latest.name

    def test_returns_none_when_no_matches(self, tmp_path: Path) -> None:
        """Test returns None when no matching checkpoints exist."""
        # Arrange
        orchestrator = ScraperOrchestrator.__new__(ScraperOrchestrator)
        orchestrator.checkpoint_dir = tmp_path

        # Act
        latest = orchestrator._get_latest_checkpoint()  # noqa: SLF001

        # Assert
        assert latest is None


class TestScrapeAllPhase2:
    """Test scrape_all Phase 2 (application scraping loop)."""

    def _make_orchestrator(self, tmp_path: Path) -> ScraperOrchestrator:
        """Create a minimally configured orchestrator for scrape_all tests."""
        orchestrator = ScraperOrchestrator.__new__(ScraperOrchestrator)
        orchestrator.fetcher = Mock()
        orchestrator.ajax_parser = Mock(spec=AJAXResponseParser)
        orchestrator.html_parser = Mock()
        orchestrator.validator = Mock()
        orchestrator.exporter = Mock()
        orchestrator.image_processor = Mock()
        orchestrator.output_dir = tmp_path / "exports"
        orchestrator.checkpoint_dir = tmp_path / "checkpoints"
        orchestrator.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        orchestrator.incremental = False
        orchestrator.unique_parts = {}
        orchestrator.vehicle_compat = {}
        orchestrator.parts_scraped = 0
        orchestrator.processed_application_ids = set()
        orchestrator.failure_tracker = FailureTracker()
        orchestrator.delay_override = None
        orchestrator.etag_store = ETagStore(tmp_path / "etags.json")
        orchestrator.hierarchy_cache = HierarchyCache(tmp_path / "hc.json")
        return orchestrator

    def test_successful_scrape_loop(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test Phase 2 scrapes applications and deduplicates parts."""
        # Arrange
        orchestrator = self._make_orchestrator(tmp_path)

        hierarchy = [
            {
                "make_id": 3,
                "make": "Honda",
                "year_id": 100,
                "year": "2024",
                "application_id": 8000,
                "model": "Civic",
            },
        ]
        mocker.patch.object(orchestrator, "_build_hierarchy", return_value=hierarchy)
        mocker.patch.object(orchestrator, "_save_checkpoint", return_value=tmp_path / "cp.json")

        part = Part(sku="CSF-1001", name="Radiator", category="Radiator")
        parts_data = [{"sku": "CSF-1001", "name": "Radiator", "vehicle_qualifiers": {}}]
        mocker.patch.object(
            orchestrator, "_scrape_application_page", return_value=([part], parts_data)
        )

        # Act
        result = orchestrator.scrape_all(fetch_details=False)

        # Assert
        assert result["applications_processed"] == 1
        assert result["applications_failed"] == 0
        assert result["unique_parts"] == 1
        assert "CSF-1001" in orchestrator.unique_parts
        assert 8000 in orchestrator.processed_application_ids

    def test_failed_application_continues(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test Phase 2 records failure and continues to next application."""
        # Arrange
        orchestrator = self._make_orchestrator(tmp_path)

        hierarchy = [
            {
                "make_id": 3,
                "make": "Honda",
                "year_id": 100,
                "year": "2024",
                "application_id": 8000,
                "model": "Civic",
            },
            {
                "make_id": 4,
                "make": "Toyota",
                "year_id": 200,
                "year": "2024",
                "application_id": 9000,
                "model": "Camry",
            },
        ]
        mocker.patch.object(orchestrator, "_build_hierarchy", return_value=hierarchy)
        mocker.patch.object(orchestrator, "_save_checkpoint", return_value=tmp_path / "cp.json")

        part = Part(sku="CSF-2001", name="Condenser", category="Condenser")
        parts_data = [{"sku": "CSF-2001", "name": "Condenser", "vehicle_qualifiers": {}}]

        # First application fails, second succeeds
        mocker.patch.object(
            orchestrator,
            "_scrape_application_page",
            side_effect=[
                RuntimeError("Network timeout"),
                ([part], parts_data),
            ],
        )

        # Act
        result = orchestrator.scrape_all(fetch_details=False)

        # Assert
        assert result["applications_processed"] == 1
        assert result["applications_failed"] == 1
        assert result["unique_parts"] == 1
        assert orchestrator.failure_tracker.get_failed_identifiers("application") == ["8000"]


class TestScrapeAllPhase3:
    """Test scrape_all Phase 3 (detail page fetching)."""

    def _make_orchestrator(self, tmp_path: Path) -> ScraperOrchestrator:
        """Create a minimally configured orchestrator for scrape_all tests."""
        orchestrator = ScraperOrchestrator.__new__(ScraperOrchestrator)
        orchestrator.fetcher = Mock()
        orchestrator.ajax_parser = Mock(spec=AJAXResponseParser)
        orchestrator.html_parser = Mock()
        orchestrator.validator = Mock()
        orchestrator.exporter = Mock()
        orchestrator.image_processor = Mock()
        orchestrator.output_dir = tmp_path / "exports"
        orchestrator.checkpoint_dir = tmp_path / "checkpoints"
        orchestrator.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        orchestrator.incremental = False
        orchestrator.unique_parts = {}
        orchestrator.vehicle_compat = {}
        orchestrator.parts_scraped = 0
        orchestrator.processed_application_ids = set()
        orchestrator.failure_tracker = FailureTracker()
        orchestrator.delay_override = None
        orchestrator.etag_store = ETagStore(tmp_path / "etags.json")
        orchestrator.hierarchy_cache = HierarchyCache(tmp_path / "hc.json")
        return orchestrator

    def test_fetch_details_new_only(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test Phase 3 fetches details only for new/changed SKUs when new_only=True."""
        # Arrange
        orchestrator = self._make_orchestrator(tmp_path)

        hierarchy = [
            {
                "make_id": 3,
                "make": "Honda",
                "year_id": 100,
                "year": "2024",
                "application_id": 8000,
                "model": "Civic",
            },
        ]
        mocker.patch.object(orchestrator, "_build_hierarchy", return_value=hierarchy)
        mocker.patch.object(orchestrator, "_save_checkpoint", return_value=tmp_path / "cp.json")

        part = Part(sku="CSF-1001", name="Radiator", category="Radiator")
        parts_data = [{"sku": "CSF-1001", "name": "Radiator", "vehicle_qualifiers": {}}]
        mocker.patch.object(
            orchestrator, "_scrape_application_page", return_value=([part], parts_data)
        )

        detail_data = {"full_description": "Great radiator", "specifications": {}}
        mocker.patch.object(orchestrator, "_fetch_detail_page", return_value=detail_data)
        mocker.patch.object(orchestrator, "_enrich_part_with_details")

        # Act
        result = orchestrator.scrape_all(fetch_details=True, fetch_details_new_only=True)

        # Assert
        assert result["details_fetched_count"] == 1
        assert result["details_failed"] == 0
        orchestrator._fetch_detail_page.assert_called_once_with("CSF-1001")  # noqa: SLF001
        orchestrator._enrich_part_with_details.assert_called_once_with(  # noqa: SLF001
            "CSF-1001", detail_data
        )

    def test_fetch_details_all(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test Phase 3 fetches details for all SKUs when new_only=False."""
        # Arrange
        orchestrator = self._make_orchestrator(tmp_path)

        # Pre-populate with existing part that is NOT new
        existing_part = Part(sku="CSF-5000", name="Existing", category="Radiator")
        orchestrator.unique_parts["CSF-5000"] = existing_part

        hierarchy = [
            {
                "make_id": 3,
                "make": "Honda",
                "year_id": 100,
                "year": "2024",
                "application_id": 8000,
                "model": "Civic",
            },
        ]
        mocker.patch.object(orchestrator, "_build_hierarchy", return_value=hierarchy)
        mocker.patch.object(orchestrator, "_save_checkpoint", return_value=tmp_path / "cp.json")

        new_part = Part(sku="CSF-1001", name="Radiator", category="Radiator")
        parts_data = [{"sku": "CSF-1001", "name": "Radiator", "vehicle_qualifiers": {}}]
        mocker.patch.object(
            orchestrator, "_scrape_application_page", return_value=([new_part], parts_data)
        )

        detail_data = {"full_description": "Great", "specifications": {}}
        mocker.patch.object(orchestrator, "_fetch_detail_page", return_value=detail_data)
        mocker.patch.object(orchestrator, "_enrich_part_with_details")

        # Act
        result = orchestrator.scrape_all(fetch_details=True, fetch_details_new_only=False)

        # Assert - Both CSF-5000 (existing) and CSF-1001 (new) should have details fetched
        assert result["details_fetched_count"] == 2
        assert orchestrator._fetch_detail_page.call_count == 2  # noqa: SLF001


class TestScrapeAllResume:
    """Test scrape_all with resume=True."""

    def test_resume_loads_checkpoint_and_filters(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Test resume loads checkpoint and skips already-processed applications."""
        # Arrange
        orchestrator = ScraperOrchestrator.__new__(ScraperOrchestrator)
        orchestrator.fetcher = Mock()
        orchestrator.ajax_parser = Mock(spec=AJAXResponseParser)
        orchestrator.html_parser = Mock()
        orchestrator.validator = Mock()
        orchestrator.exporter = Mock()
        orchestrator.image_processor = Mock()
        orchestrator.output_dir = tmp_path / "exports"
        orchestrator.checkpoint_dir = tmp_path / "checkpoints"
        orchestrator.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        orchestrator.incremental = False
        orchestrator.unique_parts = {}
        orchestrator.vehicle_compat = {}
        orchestrator.parts_scraped = 0
        orchestrator.processed_application_ids = set()
        orchestrator.failure_tracker = FailureTracker()
        orchestrator.delay_override = None
        orchestrator.etag_store = ETagStore(tmp_path / "etags.json")
        orchestrator.hierarchy_cache = HierarchyCache(tmp_path / "hc.json")

        # Create a checkpoint file
        checkpoint_data = {
            "timestamp": "20250101_000000",
            "make_filter": None,
            "year_filter": None,
            "processed_application_ids": [8000],
            "unique_parts_count": 1,
            "parts_scraped": 1,
            "vehicles_tracked": 1,
            "parts_data": {
                "CSF-1001": {
                    "sku": "CSF-1001",
                    "name": "Radiator",
                    "category": "Radiator",
                },
            },
            "vehicle_compat": {},
        }
        checkpoint_path = orchestrator.checkpoint_dir / "checkpoint_all_20250101_000000.json"
        checkpoint_path.write_text(json.dumps(checkpoint_data))

        hierarchy = [
            {
                "make_id": 3,
                "make": "Honda",
                "year_id": 100,
                "year": "2024",
                "application_id": 8000,
                "model": "Civic",
            },  # Already processed
            {
                "make_id": 4,
                "make": "Toyota",
                "year_id": 200,
                "year": "2024",
                "application_id": 9000,
                "model": "Camry",
            },  # New
        ]
        mocker.patch.object(orchestrator, "_build_hierarchy", return_value=hierarchy)
        mocker.patch.object(orchestrator, "_save_checkpoint", return_value=tmp_path / "cp.json")

        part = Part(sku="CSF-2001", name="Condenser", category="Condenser")
        parts_data = [{"sku": "CSF-2001", "name": "Condenser", "vehicle_qualifiers": {}}]
        mocker.patch.object(
            orchestrator, "_scrape_application_page", return_value=([part], parts_data)
        )

        # Act
        result = orchestrator.scrape_all(resume=True, fetch_details=False)

        # Assert - Only application 9000 was processed (8000 skipped)
        assert result["applications_processed"] == 1
        assert result["total_applications"] == 2
        orchestrator._scrape_application_page.assert_called_once_with(  # noqa: SLF001
            9000, hierarchy[1]
        )


class TestScrapeAllIncremental:
    """Test scrape_all with incremental=True."""

    def test_incremental_loads_previous_export(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test incremental mode calls load_previous_export."""
        # Arrange
        orchestrator = ScraperOrchestrator.__new__(ScraperOrchestrator)
        orchestrator.fetcher = Mock()
        orchestrator.ajax_parser = Mock(spec=AJAXResponseParser)
        orchestrator.html_parser = Mock()
        orchestrator.validator = Mock()
        orchestrator.exporter = Mock()
        orchestrator.image_processor = Mock()
        orchestrator.output_dir = tmp_path / "exports"
        orchestrator.checkpoint_dir = tmp_path / "checkpoints"
        orchestrator.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        orchestrator.incremental = True
        orchestrator.unique_parts = {}
        orchestrator.vehicle_compat = {}
        orchestrator.parts_scraped = 0
        orchestrator.processed_application_ids = set()
        orchestrator.failure_tracker = FailureTracker()
        orchestrator.delay_override = None
        orchestrator.etag_store = ETagStore(tmp_path / "etags.json")
        orchestrator.hierarchy_cache = HierarchyCache(tmp_path / "hc.json")

        mocker.patch.object(orchestrator, "_build_hierarchy", return_value=[])
        mocker.patch.object(orchestrator, "_save_checkpoint", return_value=tmp_path / "cp.json")
        mocker.patch.object(
            orchestrator, "load_previous_export", return_value={"CSF-1001": "hash123"}
        )

        # Act
        orchestrator.scrape_all(fetch_details=False)

        # Assert
        orchestrator.load_previous_export.assert_called_once()


class TestCompletenessReportDictFormat:
    """Test generate_completeness_report with dict-format previous data."""

    def test_previous_data_dict_with_parts_key(self, tmp_path: Path) -> None:
        """Test completeness report handles previous data in dict format with 'parts' key."""
        # Arrange
        orchestrator = ScraperOrchestrator.__new__(ScraperOrchestrator)
        orchestrator.unique_parts = {
            "CSF-1001": Part(sku="CSF-1001", name="Part A", category="Radiator"),
        }
        orchestrator.failure_tracker = FailureTracker()

        previous_data = {
            "parts": [
                {"sku": "CSF-1001", "name": "Part A"},
                {"sku": "CSF-1002", "name": "Part B"},
            ]
        }
        previous_path = tmp_path / "previous_parts.json"
        previous_path.write_text(json.dumps(previous_data))

        # Act
        report = orchestrator.generate_completeness_report(
            previous_export_path=previous_path,
        )

        # Assert
        assert "CSF-1002" in report["missing_skus"]
        assert report["missing_count"] == 1
        assert report["new_count"] == 0


class TestCompletenessReportMissingFile:
    """Test generate_completeness_report when previous file doesn't exist."""

    def test_previous_path_does_not_exist(self, tmp_path: Path) -> None:
        """Test report handles non-existent previous export path gracefully."""
        # Arrange
        orchestrator = ScraperOrchestrator.__new__(ScraperOrchestrator)
        orchestrator.unique_parts = {
            "CSF-1001": Part(sku="CSF-1001", name="Part A", category="Radiator"),
        }
        orchestrator.failure_tracker = FailureTracker()

        non_existent_path = tmp_path / "does_not_exist.json"

        # Act
        report = orchestrator.generate_completeness_report(
            previous_export_path=non_existent_path,
        )

        # Assert - Report generated but no comparison data
        assert report["current_parts_count"] == 1
        assert "missing_skus" not in report
        assert "new_skus" not in report


class TestExportData:
    """Test export_data method."""

    def test_non_incremental_export(self, tmp_path: Path) -> None:
        """Test export_data uses non-incremental methods when incremental=False."""
        # Arrange
        orchestrator = ScraperOrchestrator.__new__(ScraperOrchestrator)
        orchestrator.exporter = Mock()
        orchestrator.incremental = False

        part = Part(sku="CSF-1001", name="Radiator", category="Radiator")
        vehicle = Vehicle(make="Honda", model="Civic", year=2024)
        orchestrator.unique_parts = {"CSF-1001": part}
        orchestrator.vehicle_compat = {"CSF-1001": [vehicle]}

        orchestrator.exporter.export_parts.return_value = tmp_path / "parts.json"
        orchestrator.exporter.export_compatibility.return_value = tmp_path / "compat.json"

        # Act
        paths = orchestrator.export_data()

        # Assert
        orchestrator.exporter.export_parts.assert_called_once()
        orchestrator.exporter.export_compatibility.assert_called_once()
        assert paths["parts"] == tmp_path / "parts.json"
        assert paths["compatibility"] == tmp_path / "compat.json"

    def test_incremental_export(self, tmp_path: Path) -> None:
        """Test export_data uses incremental methods when previous exports exist."""
        # Arrange — create previous export files so incremental append is used
        (tmp_path / "parts.json").write_text('{"parts": []}')
        (tmp_path / "compatibility.json").write_text('{"compatibility": []}')

        orchestrator = ScraperOrchestrator.__new__(ScraperOrchestrator)
        orchestrator.exporter = Mock()
        orchestrator.exporter.output_dir = tmp_path
        orchestrator.incremental = True
        orchestrator.output_dir = tmp_path

        part = Part(sku="CSF-1001", name="Radiator", category="Radiator")
        vehicle = Vehicle(make="Honda", model="Civic", year=2024)
        orchestrator.unique_parts = {"CSF-1001": part}
        orchestrator.vehicle_compat = {"CSF-1001": [vehicle]}

        orchestrator.exporter.export_parts_incremental.return_value = tmp_path / "parts.json"
        orchestrator.exporter.export_compatibility_incremental.return_value = (
            tmp_path / "compat.json"
        )

        # Act
        paths = orchestrator.export_data()

        # Assert
        orchestrator.exporter.export_parts_incremental.assert_called_once()
        orchestrator.exporter.export_compatibility_incremental.assert_called_once()
        assert paths["parts"] == tmp_path / "parts.json"
        assert paths["compatibility"] == tmp_path / "compat.json"


class TestHierarchyCaching:
    """Test hierarchy cache integration in _build_hierarchy."""

    def test_cache_hit_skips_model_enumeration(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test that a cache hit reuses cached entries and skips _enumerate_models."""
        # Arrange
        mock_fetcher = Mock()
        mock_ajax = Mock(spec=AJAXResponseParser)

        # The years response text that will be hashed
        years_response_text = "years_js_content"
        mock_response_years = Mock(spec=httpx.Response)
        mock_response_years.text = years_response_text
        mock_fetcher.fetch.return_value = mock_response_years

        orchestrator = ScraperOrchestrator.__new__(ScraperOrchestrator)
        orchestrator.fetcher = mock_fetcher
        orchestrator.ajax_parser = mock_ajax
        orchestrator.failure_tracker = FailureTracker()
        orchestrator.hierarchy_cache = HierarchyCache(tmp_path / "hc.json")

        # Pre-populate cache with matching hash and entries
        expected_hash = hashlib.md5(years_response_text.encode()).hexdigest()  # noqa: S324
        years_url = "https://csf.mycarparts.com/get_year_by_make/3"
        orchestrator.hierarchy_cache.set_url_hash(years_url, expected_hash)
        cached_entries = [
            {
                "make_id": 3,
                "make": "Honda",
                "year_id": 100,
                "year": "2024",
                "application_id": 8000,
                "model": "Civic",
            },
            {
                "make_id": 3,
                "make": "Honda",
                "year_id": 101,
                "year": "2023",
                "application_id": 8001,
                "model": "Accord",
            },
        ]
        orchestrator.hierarchy_cache.set_make_hierarchy(3, cached_entries)

        mocker.patch.object(orchestrator, "_enumerate_makes", return_value={3: "Honda"})

        # Act
        hierarchy = orchestrator._build_hierarchy()  # noqa: SLF001

        # Assert — cached entries used, models NOT enumerated
        assert len(hierarchy) == 2
        assert hierarchy[0]["model"] == "Civic"
        assert hierarchy[1]["model"] == "Accord"
        mock_ajax.parse_model_response.assert_not_called()
        # Only 1 fetch call (years URL), no model fetches
        assert mock_fetcher.fetch.call_count == 1

    def test_cache_miss_enumerates_normally_and_updates_cache(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Test that a cache miss proceeds with normal enumeration and updates cache."""
        # Arrange
        mock_fetcher = Mock()
        mock_ajax = Mock(spec=AJAXResponseParser)

        mock_response_years = Mock(spec=httpx.Response)
        mock_response_years.text = "new_years_content"
        mock_response_models = Mock(spec=httpx.Response)
        mock_response_models.text = "models_js"

        mock_fetcher.fetch = Mock(
            side_effect=[
                mock_response_years,  # Honda years
                mock_response_models,  # Honda 2024 models
            ]
        )

        mock_ajax.parse_year_response.return_value = {100: "2024"}
        mock_ajax.parse_model_response.return_value = {8000: "Civic"}

        orchestrator = ScraperOrchestrator.__new__(ScraperOrchestrator)
        orchestrator.fetcher = mock_fetcher
        orchestrator.ajax_parser = mock_ajax
        orchestrator.failure_tracker = FailureTracker()
        orchestrator.hierarchy_cache = HierarchyCache(tmp_path / "hc.json")

        # Pre-populate cache with DIFFERENT hash (causes miss)
        years_url = "https://csf.mycarparts.com/get_year_by_make/3"
        orchestrator.hierarchy_cache.set_url_hash(years_url, "old_stale_hash")
        orchestrator.hierarchy_cache.set_make_hierarchy(3, [{"make": "Honda", "model": "OLD"}])

        mocker.patch.object(orchestrator, "_enumerate_makes", return_value={3: "Honda"})

        # Act
        hierarchy = orchestrator._build_hierarchy()  # noqa: SLF001

        # Assert — normal enumeration happened
        assert len(hierarchy) == 1
        assert hierarchy[0]["model"] == "Civic"
        mock_ajax.parse_year_response.assert_called_once()
        mock_ajax.parse_model_response.assert_called_once()

        # Cache was updated
        expected_hash = hashlib.md5(b"new_years_content").hexdigest()  # noqa: S324
        assert orchestrator.hierarchy_cache.get_url_hash(years_url) == expected_hash
        cached = orchestrator.hierarchy_cache.get_make_hierarchy(3)
        assert cached is not None
        assert len(cached) == 1
        assert cached[0]["model"] == "Civic"

    def test_empty_cache_proceeds_normally(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test that an empty cache (first run) enumerates everything normally."""
        # Arrange
        mock_fetcher = Mock()
        mock_ajax = Mock(spec=AJAXResponseParser)

        mock_response_years = Mock(spec=httpx.Response)
        mock_response_years.text = "years_js"
        mock_response_models = Mock(spec=httpx.Response)
        mock_response_models.text = "models_js"

        mock_fetcher.fetch = Mock(
            side_effect=[
                mock_response_years,  # Honda years
                mock_response_models,  # Honda 2024 models
            ]
        )

        mock_ajax.parse_year_response.return_value = {100: "2024"}
        mock_ajax.parse_model_response.return_value = {8000: "Civic"}

        orchestrator = ScraperOrchestrator.__new__(ScraperOrchestrator)
        orchestrator.fetcher = mock_fetcher
        orchestrator.ajax_parser = mock_ajax
        orchestrator.failure_tracker = FailureTracker()
        orchestrator.hierarchy_cache = HierarchyCache(tmp_path / "hc.json")

        mocker.patch.object(orchestrator, "_enumerate_makes", return_value={3: "Honda"})

        # Act
        hierarchy = orchestrator._build_hierarchy()  # noqa: SLF001

        # Assert — full enumeration happened
        assert len(hierarchy) == 1
        assert hierarchy[0]["model"] == "Civic"
        mock_ajax.parse_year_response.assert_called_once()
        mock_ajax.parse_model_response.assert_called_once()

    def test_year_filter_applied_to_cached_entries(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Test that year_filter is applied to cached hierarchy entries."""
        # Arrange
        mock_fetcher = Mock()
        mock_ajax = Mock(spec=AJAXResponseParser)

        years_response_text = "years_js_content"
        mock_response_years = Mock(spec=httpx.Response)
        mock_response_years.text = years_response_text
        mock_fetcher.fetch.return_value = mock_response_years

        orchestrator = ScraperOrchestrator.__new__(ScraperOrchestrator)
        orchestrator.fetcher = mock_fetcher
        orchestrator.ajax_parser = mock_ajax
        orchestrator.failure_tracker = FailureTracker()
        orchestrator.hierarchy_cache = HierarchyCache(tmp_path / "hc.json")

        # Pre-populate cache with entries for multiple years
        expected_hash = hashlib.md5(years_response_text.encode()).hexdigest()  # noqa: S324
        years_url = "https://csf.mycarparts.com/get_year_by_make/3"
        orchestrator.hierarchy_cache.set_url_hash(years_url, expected_hash)
        cached_entries = [
            {
                "make_id": 3,
                "make": "Honda",
                "year_id": 100,
                "year": "2024",
                "application_id": 8000,
                "model": "Civic",
            },
            {
                "make_id": 3,
                "make": "Honda",
                "year_id": 101,
                "year": "2023",
                "application_id": 8001,
                "model": "Accord",
            },
        ]
        orchestrator.hierarchy_cache.set_make_hierarchy(3, cached_entries)

        mocker.patch.object(orchestrator, "_enumerate_makes", return_value={3: "Honda"})

        # Act — only want year 2023
        hierarchy = orchestrator._build_hierarchy(year_filter=2023)  # noqa: SLF001

        # Assert — only 2023 entry returned
        assert len(hierarchy) == 1
        assert hierarchy[0]["year"] == "2023"
        assert hierarchy[0]["model"] == "Accord"

    def test_use_cache_false_bypasses_cache(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test that use_cache=False ignores cached data and enumerates normally."""
        # Arrange
        mock_fetcher = Mock()
        mock_ajax = Mock(spec=AJAXResponseParser)

        years_response_text = "years_js_content"
        mock_response_years = Mock(spec=httpx.Response)
        mock_response_years.text = years_response_text
        mock_response_models = Mock(spec=httpx.Response)
        mock_response_models.text = "models_js"

        mock_fetcher.fetch = Mock(
            side_effect=[
                mock_response_years,  # Honda years
                mock_response_models,  # Honda 2024 models
            ]
        )

        mock_ajax.parse_year_response.return_value = {100: "2024"}
        mock_ajax.parse_model_response.return_value = {8000: "Civic"}

        orchestrator = ScraperOrchestrator.__new__(ScraperOrchestrator)
        orchestrator.fetcher = mock_fetcher
        orchestrator.ajax_parser = mock_ajax
        orchestrator.failure_tracker = FailureTracker()
        orchestrator.hierarchy_cache = HierarchyCache(tmp_path / "hc.json")

        # Pre-populate cache with matching hash (would normally be a hit)
        expected_hash = hashlib.md5(years_response_text.encode()).hexdigest()  # noqa: S324
        years_url = "https://csf.mycarparts.com/get_year_by_make/3"
        orchestrator.hierarchy_cache.set_url_hash(years_url, expected_hash)
        orchestrator.hierarchy_cache.set_make_hierarchy(
            3,
            [
                {
                    "make_id": 3,
                    "make": "Honda",
                    "year_id": 999,
                    "year": "2020",
                    "application_id": 9999,
                    "model": "CACHED_OLD",
                }
            ],
        )

        mocker.patch.object(orchestrator, "_enumerate_makes", return_value={3: "Honda"})

        # Act — bypass cache
        hierarchy = orchestrator._build_hierarchy(use_cache=False)  # noqa: SLF001

        # Assert — fresh enumeration, not cached data
        assert len(hierarchy) == 1
        assert hierarchy[0]["model"] == "Civic"
        mock_ajax.parse_year_response.assert_called_once()
        mock_ajax.parse_model_response.assert_called_once()
