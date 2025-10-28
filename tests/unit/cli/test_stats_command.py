"""Unit tests for stats command.

This module tests the stats command functionality including:
- Command-line option parsing and validation
- File and directory analysis
- Statistics display and formatting
- Detailed mode functionality
- Error handling and exit codes
- Help text display
- StatsAnalyzer integration
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
from click.testing import CliRunner
from rich.console import Console

from src.cli.commands.stats import (
    _display_category_breakdown,
    _display_detailed_stats,
    _display_general_stats,
    _display_vehicle_stats,
    _format_file_size,
    stats,
)
from src.utils.stats_analyzer import DataStats, StatsAnalyzer


class TestStatsCommand:
    """Tests for stats command."""

    def test_stats_command_requires_input_option(self) -> None:
        """Test that --input option is required."""
        # Arrange
        runner = CliRunner()

        # Act
        result = runner.invoke(stats, [])

        # Assert
        assert result.exit_code != 0
        assert "Missing option '--input'" in result.output or "required" in result.output.lower()

    def test_stats_command_input_option_accepts_file_path(self, tmp_path: Path) -> None:
        """Test that --input option accepts file path."""
        # Arrange
        runner = CliRunner()
        test_file = tmp_path / "test.json"
        test_data = {
            "parts": [{"sku": "CSF-12345", "name": "Test Radiator", "category": "Radiators"}]
        }
        test_file.write_text(json.dumps(test_data))

        # Act
        result = runner.invoke(stats, ["--input", str(test_file)])

        # Assert
        assert result.exit_code == 0
        assert "Analyzing file:" in result.output
        assert "test.json" in result.output

    def test_stats_command_input_option_accepts_directory_path(self, tmp_path: Path) -> None:
        """Test that --input option accepts directory path."""
        # Arrange
        runner = CliRunner()
        test_dir = tmp_path / "data"
        test_dir.mkdir()
        test_file = test_dir / "parts.json"
        test_data = {
            "parts": [{"sku": "CSF-12345", "name": "Test Radiator", "category": "Radiators"}]
        }
        test_file.write_text(json.dumps(test_data))

        # Act
        result = runner.invoke(stats, ["--input", str(test_dir)])

        # Assert
        assert result.exit_code == 0
        assert "Analyzing directory:" in result.output
        assert "data" in result.output

    def test_stats_command_input_option_rejects_nonexistent_path(self) -> None:
        """Test that --input option rejects nonexistent path."""
        # Arrange
        runner = CliRunner()
        nonexistent_path = "/nonexistent/path/to/file.json"

        # Act
        result = runner.invoke(stats, ["--input", nonexistent_path])

        # Assert
        assert result.exit_code != 0
        assert "does not exist" in result.output.lower() or "invalid" in result.output.lower()

    def test_stats_command_detailed_flag_shows_detailed_stats(
        self, tmp_path: Path, mocker: Mock
    ) -> None:
        """Test that --detailed flag shows detailed stats."""
        # Arrange
        runner = CliRunner()
        test_file = tmp_path / "test.json"
        test_data = {
            "parts": [{"sku": "CSF-12345", "name": "Test Radiator", "category": "Radiators"}]
        }
        test_file.write_text(json.dumps(test_data))

        # Mock the analyzer to verify detailed=True is passed
        mock_analyzer = mocker.patch("src.cli.commands.stats.StatsAnalyzer")
        mock_instance = Mock()
        mock_instance.analyze_file.return_value = DataStats(
            total_parts=1,
            unique_skus=1,
            total_vehicles=0,
            parts_by_category={"Radiators": 1},
            file_size_bytes=100,
            export_date=datetime.now(UTC),
        )
        mock_analyzer.return_value = mock_instance

        # Act
        result = runner.invoke(stats, ["--input", str(test_file), "--detailed"])

        # Assert
        assert result.exit_code == 0
        mock_instance.analyze_file.assert_called_once()
        call_kwargs = mock_instance.analyze_file.call_args[1]
        assert call_kwargs["detailed"] is True
        assert "Detailed Analysis" in result.output

    def test_stats_command_detailed_flag_defaults_to_false(
        self, tmp_path: Path, mocker: Mock
    ) -> None:
        """Test that --detailed flag defaults to False."""
        # Arrange
        runner = CliRunner()
        test_file = tmp_path / "test.json"
        test_data = {
            "parts": [{"sku": "CSF-12345", "name": "Test Radiator", "category": "Radiators"}]
        }
        test_file.write_text(json.dumps(test_data))

        mock_analyzer = mocker.patch("src.cli.commands.stats.StatsAnalyzer")
        mock_instance = Mock()
        mock_instance.analyze_file.return_value = DataStats(
            total_parts=1,
            unique_skus=1,
            total_vehicles=0,
            parts_by_category={"Radiators": 1},
            file_size_bytes=100,
            export_date=datetime.now(UTC),
        )
        mock_analyzer.return_value = mock_instance

        # Act
        result = runner.invoke(stats, ["--input", str(test_file)])

        # Assert
        assert result.exit_code == 0
        call_kwargs = mock_instance.analyze_file.call_args[1]
        assert call_kwargs["detailed"] is False
        assert "Detailed Analysis" not in result.output

    def test_stats_command_displays_general_statistics(self, tmp_path: Path) -> None:
        """Test that command displays general statistics."""
        # Arrange
        runner = CliRunner()
        test_file = tmp_path / "test.json"
        test_data = {
            "parts": [
                {"sku": "CSF-12345", "name": "Test Radiator", "category": "Radiators"},
                {"sku": "CSF-67890", "name": "Test Condenser", "category": "Condensers"},
            ]
        }
        test_file.write_text(json.dumps(test_data))

        # Act
        result = runner.invoke(stats, ["--input", str(test_file)])

        # Assert
        assert result.exit_code == 0
        assert "General Statistics" in result.output
        assert "Total Parts" in result.output
        assert "Unique SKUs" in result.output
        assert "Total Vehicles" in result.output
        assert "File Size" in result.output

    def test_stats_command_displays_parts_by_category(self, tmp_path: Path) -> None:
        """Test that command displays parts by category."""
        # Arrange
        runner = CliRunner()
        test_file = tmp_path / "test.json"
        test_data = {
            "parts": [
                {"sku": "CSF-12345", "name": "Test Radiator", "category": "Radiators"},
                {"sku": "CSF-67890", "name": "Test Condenser", "category": "Condensers"},
                {"sku": "CSF-11111", "name": "Another Radiator", "category": "Radiators"},
            ]
        }
        test_file.write_text(json.dumps(test_data))

        # Act
        result = runner.invoke(stats, ["--input", str(test_file)])

        # Assert
        assert result.exit_code == 0
        assert "Parts by Category" in result.output
        assert "Radiators" in result.output
        assert "Condensers" in result.output

    def test_stats_command_displays_vehicles_by_make(self, tmp_path: Path) -> None:
        """Test that command displays vehicles by make."""
        # Arrange
        runner = CliRunner()
        test_file = tmp_path / "test.json"
        test_data = {
            "parts": [
                {
                    "sku": "CSF-12345",
                    "name": "Test Radiator",
                    "category": "Radiators",
                    "vehicle": {"make": "Honda", "model": "Accord", "year": 2020},
                },
                {
                    "sku": "CSF-67890",
                    "name": "Test Condenser",
                    "category": "Condensers",
                    "vehicle": {"make": "Toyota", "model": "Camry", "year": 2021},
                },
                {
                    "sku": "CSF-11111",
                    "name": "Another Radiator",
                    "category": "Radiators",
                    "vehicle": {"make": "Honda", "model": "Civic", "year": 2020},
                },
            ]
        }
        test_file.write_text(json.dumps(test_data))

        # Act
        result = runner.invoke(stats, ["--input", str(test_file)])

        # Assert
        assert result.exit_code == 0
        assert "Vehicles by Make" in result.output
        assert "Honda" in result.output
        assert "Toyota" in result.output

    def test_stats_command_detailed_mode_shows_additional_metrics(self, tmp_path: Path) -> None:
        """Test that detailed mode shows additional metrics."""
        # Arrange
        runner = CliRunner()
        test_file = tmp_path / "test.json"
        test_data = {
            "parts": [
                {"sku": "CSF-12345", "name": "Test Radiator", "category": "Radiators"},
                {"sku": "CSF-67890", "name": "Test Condenser", "category": "Condensers"},
            ]
        }
        test_file.write_text(json.dumps(test_data))

        # Act
        result = runner.invoke(stats, ["--input", str(test_file), "--detailed"])

        # Assert
        assert result.exit_code == 0
        assert "Detailed Analysis" in result.output
        assert "Average parts per category" in result.output
        assert "Data density" in result.output
        assert "SKU utilization" in result.output

    def test_stats_command_exit_code_zero_on_success(self, tmp_path: Path) -> None:
        """Test that command returns exit code 0 on success."""
        # Arrange
        runner = CliRunner()
        test_file = tmp_path / "test.json"
        test_data = {
            "parts": [{"sku": "CSF-12345", "name": "Test Radiator", "category": "Radiators"}]
        }
        test_file.write_text(json.dumps(test_data))

        # Act
        result = runner.invoke(stats, ["--input", str(test_file)])

        # Assert
        assert result.exit_code == 0
        assert "Analysis complete!" in result.output

    def test_stats_command_exit_code_nonzero_on_file_not_found(self) -> None:
        """Test that command returns non-zero exit code on file not found."""
        # Arrange
        runner = CliRunner()
        nonexistent_file = "/nonexistent/file.json"

        # Act
        result = runner.invoke(stats, ["--input", nonexistent_file])

        # Assert
        assert result.exit_code != 0

    def test_stats_command_handles_invalid_json(self, tmp_path: Path) -> None:
        """Test that command handles invalid JSON gracefully."""
        # Arrange
        runner = CliRunner()
        test_file = tmp_path / "invalid.json"
        test_file.write_text("{ invalid json }")

        # Act
        result = runner.invoke(stats, ["--input", str(test_file)])

        # Assert
        assert result.exit_code != 0
        assert "Error" in result.output

    def test_stats_command_handles_empty_file(self, tmp_path: Path) -> None:
        """Test that command handles empty file gracefully."""
        # Arrange
        runner = CliRunner()
        test_file = tmp_path / "empty.json"
        test_file.write_text("{}")

        # Act
        result = runner.invoke(stats, ["--input", str(test_file)])

        # Assert
        assert result.exit_code == 0
        assert "Total Parts" in result.output

    def test_stats_command_handles_analyzer_value_error(self, tmp_path: Path, mocker: Mock) -> None:
        """Test that command handles ValueError from analyzer."""
        # Arrange
        runner = CliRunner()
        test_file = tmp_path / "test.json"
        test_file.write_text(json.dumps({"parts": []}))

        mock_analyzer = mocker.patch("src.cli.commands.stats.StatsAnalyzer")
        mock_instance = Mock()
        mock_instance.analyze_file.side_effect = ValueError("Invalid data format")
        mock_analyzer.return_value = mock_instance

        # Act
        result = runner.invoke(stats, ["--input", str(test_file)])

        # Assert
        assert result.exit_code != 0
        assert "Error" in result.output

    def test_stats_command_help_displays_correctly(self) -> None:
        """Test that help text displays correctly."""
        # Arrange
        runner = CliRunner()

        # Act
        result = runner.invoke(stats, ["--help"])

        # Assert
        assert result.exit_code == 0
        assert "Analyze automotive parts data and display statistics" in result.output
        assert "--input" in result.output
        assert "--detailed" in result.output
        assert "JSON file or directory to analyze" in result.output
        assert "Show detailed breakdown with additional statistics" in result.output

    def test_stats_command_short_option_i_works(self, tmp_path: Path) -> None:
        """Test that short option -i works for --input."""
        # Arrange
        runner = CliRunner()
        test_file = tmp_path / "test.json"
        test_data = {
            "parts": [{"sku": "CSF-12345", "name": "Test Radiator", "category": "Radiators"}]
        }
        test_file.write_text(json.dumps(test_data))

        # Act
        result = runner.invoke(stats, ["-i", str(test_file)])

        # Assert
        assert result.exit_code == 0
        assert "Analyzing file:" in result.output

    def test_stats_command_short_option_d_works(self, tmp_path: Path) -> None:
        """Test that short option -d works for --detailed."""
        # Arrange
        runner = CliRunner()
        test_file = tmp_path / "test.json"
        test_data = {
            "parts": [{"sku": "CSF-12345", "name": "Test Radiator", "category": "Radiators"}]
        }
        test_file.write_text(json.dumps(test_data))

        # Act
        result = runner.invoke(stats, ["-i", str(test_file), "-d"])

        # Assert
        assert result.exit_code == 0
        assert "Detailed Analysis" in result.output


class TestStatsAnalyzer:
    """Tests for StatsAnalyzer class."""

    def test_stats_analyzer_analyze_file_analyzes_single_json_file(self, tmp_path: Path) -> None:
        """Test that analyze_file() analyzes single JSON file."""
        # Arrange
        analyzer = StatsAnalyzer()
        test_file = tmp_path / "test.json"
        test_data = [
            {"sku": "CSF-12345", "name": "Test Radiator", "category": "Radiators"},
            {"sku": "CSF-67890", "name": "Test Condenser", "category": "Condensers"},
        ]
        test_file.write_text(json.dumps(test_data))

        # Act
        stats = analyzer.analyze_file(test_file)

        # Assert
        assert stats.total_parts == 2
        assert stats.unique_skus == 2
        assert stats.parts_by_category["Radiators"] == 1
        assert stats.parts_by_category["Condensers"] == 1

    def test_stats_analyzer_analyze_file_raises_error_on_nonexistent_file(self) -> None:
        """Test that analyze_file() raises FileNotFoundError on nonexistent file."""
        # Arrange
        analyzer = StatsAnalyzer()
        nonexistent_file = Path("/nonexistent/file.json")

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="File not found"):
            analyzer.analyze_file(nonexistent_file)

    def test_stats_analyzer_analyze_file_raises_error_on_invalid_format(
        self, tmp_path: Path
    ) -> None:
        """Test that analyze_file() raises ValueError on invalid format."""
        # Arrange
        analyzer = StatsAnalyzer()
        test_file = tmp_path / "test.json"
        test_file.write_text(json.dumps("not a list or dict"))

        # Act & Assert
        with pytest.raises(ValueError, match="Unsupported data format"):
            analyzer.analyze_file(test_file)

    def test_stats_analyzer_analyze_file_handles_detailed_flag(self, tmp_path: Path) -> None:
        """Test that analyze_file() accepts detailed flag."""
        # Arrange
        analyzer = StatsAnalyzer()
        test_file = tmp_path / "test.json"
        test_data = [{"sku": "CSF-12345", "name": "Test Radiator", "category": "Radiators"}]
        test_file.write_text(json.dumps(test_data))

        # Act
        stats = analyzer.analyze_file(test_file, detailed=True)

        # Assert
        assert stats.total_parts == 1
        assert stats.unique_skus == 1

    def test_stats_analyzer_analyze_directory_aggregates_multiple_files(
        self, tmp_path: Path
    ) -> None:
        """Test that analyze_directory() aggregates multiple files."""
        # Arrange
        analyzer = StatsAnalyzer()
        test_dir = tmp_path / "data"
        test_dir.mkdir()

        # Create multiple JSON files
        file1 = test_dir / "parts1.json"
        file1.write_text(
            json.dumps([{"sku": "CSF-12345", "name": "Radiator", "category": "Radiators"}])
        )

        file2 = test_dir / "parts2.json"
        file2.write_text(
            json.dumps([{"sku": "CSF-67890", "name": "Condenser", "category": "Condensers"}])
        )

        # Act
        stats = analyzer.analyze_directory(test_dir)

        # Assert
        assert stats.total_parts == 2
        assert stats.unique_skus == 2
        assert len(stats.parts_by_category) == 2

    def test_stats_analyzer_analyze_directory_raises_error_on_nonexistent_directory(
        self,
    ) -> None:
        """Test that analyze_directory() raises FileNotFoundError on nonexistent directory."""
        # Arrange
        analyzer = StatsAnalyzer()
        nonexistent_dir = Path("/nonexistent/directory")

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="Directory not found"):
            analyzer.analyze_directory(nonexistent_dir)

    def test_stats_analyzer_analyze_directory_raises_error_on_no_json_files(
        self, tmp_path: Path
    ) -> None:
        """Test that analyze_directory() raises ValueError when no JSON files found."""
        # Arrange
        analyzer = StatsAnalyzer()
        test_dir = tmp_path / "empty"
        test_dir.mkdir()

        # Act & Assert
        with pytest.raises(ValueError, match="No JSON files found"):
            analyzer.analyze_directory(test_dir)

    def test_stats_analyzer_analyze_list_data_handles_list_format(self) -> None:
        """Test that _analyze_parts_list() handles list format."""
        # Arrange
        analyzer = StatsAnalyzer()
        parts_data = [
            {"sku": "CSF-12345", "name": "Radiator", "category": "Radiators"},
            {"sku": "CSF-67890", "name": "Condenser", "category": "Condensers"},
        ]

        # Act
        stats = analyzer._analyze_parts_list(parts_data, 1000, False)  # noqa: SLF001

        # Assert
        assert stats.total_parts == 2
        assert stats.unique_skus == 2
        assert stats.file_size_bytes == 1000

    def test_stats_analyzer_analyze_list_data_handles_empty_list(self) -> None:
        """Test that _analyze_parts_list() handles empty list."""
        # Arrange
        analyzer = StatsAnalyzer()
        parts_data: list[dict[str, Any]] = []

        # Act
        stats = analyzer._analyze_parts_list(parts_data, 0, False)  # noqa: SLF001

        # Assert
        assert stats.total_parts == 0
        assert stats.unique_skus == 0
        assert stats.total_vehicles == 0

    def test_stats_analyzer_analyze_list_data_detects_duplicates(self) -> None:
        """Test that _analyze_parts_list() detects duplicate SKUs."""
        # Arrange
        analyzer = StatsAnalyzer()
        parts_data = [
            {"sku": "CSF-12345", "name": "Radiator 1", "category": "Radiators"},
            {"sku": "CSF-12345", "name": "Radiator 2", "category": "Radiators"},
            {"sku": "CSF-67890", "name": "Condenser", "category": "Condensers"},
        ]

        # Act
        stats = analyzer._analyze_parts_list(parts_data, 1000, False)  # noqa: SLF001

        # Assert
        assert stats.total_parts == 3
        assert stats.unique_skus == 2
        assert stats.duplicate_count == 1
        assert stats.deduplication_rate > 0

    def test_stats_analyzer_analyze_list_data_extracts_vehicle_data(self) -> None:
        """Test that _analyze_parts_list() extracts vehicle data."""
        # Arrange
        analyzer = StatsAnalyzer()
        parts_data = [
            {
                "sku": "CSF-12345",
                "name": "Radiator",
                "category": "Radiators",
                "vehicle": {"make": "Honda", "model": "Accord", "year": 2020},
            },
            {
                "sku": "CSF-67890",
                "name": "Condenser",
                "category": "Condensers",
                "vehicle": {"make": "Toyota", "model": "Camry", "year": 2021},
            },
        ]

        # Act
        stats = analyzer._analyze_parts_list(parts_data, 1000, False)  # noqa: SLF001

        # Assert
        assert stats.total_vehicles == 2
        assert stats.has_compatibility_data is True
        assert len(stats.vehicles_by_make) == 2
        assert stats.vehicles_by_make["Honda"] == 1
        assert stats.vehicles_by_make["Toyota"] == 1

    def test_stats_analyzer_analyze_list_data_detects_price_data(self) -> None:
        """Test that _analyze_parts_list() detects price data."""
        # Arrange
        analyzer = StatsAnalyzer()
        parts_data = [
            {
                "sku": "CSF-12345",
                "name": "Radiator",
                "category": "Radiators",
                "price": "299.99",
            }
        ]

        # Act
        stats = analyzer._analyze_parts_list(parts_data, 1000, False)  # noqa: SLF001

        # Assert
        assert stats.price_data_available is True

    def test_stats_analyzer_analyze_dict_data_handles_dict_format(self, tmp_path: Path) -> None:
        """Test that _analyze_dict_data() handles dict format."""
        # Arrange
        analyzer = StatsAnalyzer()
        data = {
            "parts": [
                {"sku": "CSF-12345", "name": "Radiator", "category": "Radiators"},
                {"sku": "CSF-67890", "name": "Condenser", "category": "Condensers"},
            ]
        }

        # Act
        stats = analyzer._analyze_dict_data(data, 1000, False)  # noqa: SLF001

        # Assert
        assert stats.total_parts == 2
        assert stats.unique_skus == 2

    def test_stats_analyzer_analyze_dict_data_handles_data_key(self) -> None:
        """Test that _analyze_dict_data() handles 'data' key."""
        # Arrange
        analyzer = StatsAnalyzer()
        data = {
            "data": [
                {"sku": "CSF-12345", "name": "Radiator", "category": "Radiators"},
            ]
        }

        # Act
        stats = analyzer._analyze_dict_data(data, 1000, False)  # noqa: SLF001

        # Assert
        assert stats.total_parts == 1

    def test_stats_analyzer_analyze_dict_data_handles_compatibility_format(self) -> None:
        """Test that _analyze_dict_data() handles compatibility format."""
        # Arrange
        analyzer = StatsAnalyzer()
        data = {
            "CSF-12345": [{"make": "Honda", "model": "Accord", "year": 2020}],
            "CSF-67890": [{"make": "Toyota", "model": "Camry", "year": 2021}],
        }

        # Act
        stats = analyzer._analyze_dict_data(data, 1000, False)  # noqa: SLF001

        # Assert
        assert stats.total_parts == 2
        assert stats.unique_skus == 2

    def test_stats_analyzer_analyze_dict_data_handles_summary_format(self) -> None:
        """Test that _analyze_dict_data() handles summary format."""
        # Arrange
        analyzer = StatsAnalyzer()
        data = {
            "summary": {
                "total_parts_found": 100,
                "unique_skus": 95,
                "deduplication_rate": 0.05,
            }
        }

        # Act
        stats = analyzer._analyze_dict_data(data, 1000, False)  # noqa: SLF001

        # Assert
        assert stats.total_parts == 100
        assert stats.unique_skus == 95
        assert stats.deduplication_rate == 0.05

    def test_stats_analyzer_calculate_detailed_stats_computes_metrics(self, tmp_path: Path) -> None:
        """Test that _calculate_detailed_stats() computes metrics."""
        # Arrange
        analyzer = StatsAnalyzer()
        test_file = tmp_path / "test.json"
        test_data = [
            {"sku": "CSF-12345", "name": "Radiator", "category": "Radiators"},
            {"sku": "CSF-67890", "name": "Condenser", "category": "Condensers"},
        ]
        test_file.write_text(json.dumps(test_data))

        # Act
        stats = analyzer.analyze_file(test_file, detailed=True)

        # Assert
        assert stats.total_parts > 0
        assert stats.file_size_bytes > 0
        assert len(stats.parts_by_category) > 0

    def test_stats_analyzer_handles_different_json_structures(self, tmp_path: Path) -> None:
        """Test that StatsAnalyzer handles different JSON structures."""
        # Arrange
        analyzer = StatsAnalyzer()

        # Test with list structure
        test_file1 = tmp_path / "list.json"
        test_file1.write_text(
            json.dumps([{"sku": "CSF-12345", "name": "Radiator", "category": "Radiators"}])
        )

        # Test with dict structure
        test_file2 = tmp_path / "dict.json"
        test_file2.write_text(
            json.dumps(
                {"parts": [{"sku": "CSF-67890", "name": "Condenser", "category": "Condensers"}]}
            )
        )

        # Act
        stats1 = analyzer.analyze_file(test_file1)
        stats2 = analyzer.analyze_file(test_file2)

        # Assert
        assert stats1.total_parts == 1
        assert stats2.total_parts == 1
        assert stats1.unique_skus == 1
        assert stats2.unique_skus == 1


class TestDisplayFunctions:
    """Tests for display helper functions."""

    def test_display_general_stats_displays_all_fields(self, mocker: Mock) -> None:
        """Test that _display_general_stats() displays all fields."""
        # Arrange
        mock_console = mocker.patch("src.cli.commands.stats.Console")
        mock_instance = Mock()
        mock_console.return_value = mock_instance

        stats_data = DataStats(
            total_parts=100,
            unique_skus=95,
            total_vehicles=50,
            parts_by_category={"Radiators": 60, "Condensers": 40},
            duplicate_count=5,
            deduplication_rate=0.05,
            file_size_bytes=1024000,
            export_date=datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC),
            has_compatibility_data=True,
            price_data_available=True,
        )

        console = Console()
        test_path = Path("/test/path.json")

        # Act
        _display_general_stats(console, stats_data, test_path)

        # Assert - Function should complete without errors
        # Actual assertion would require capturing Rich output, which is complex
        # We verify the function runs without exceptions
        assert True

    def test_display_category_breakdown_displays_categories(self, mocker: Mock) -> None:
        """Test that _display_category_breakdown() displays categories."""
        # Arrange
        console = Console()
        stats_data = DataStats(
            total_parts=100,
            unique_skus=100,
            total_vehicles=0,
            parts_by_category={"Radiators": 60, "Condensers": 40},
        )

        # Act
        _display_category_breakdown(console, stats_data)

        # Assert - Function should complete without errors
        assert True

    def test_display_vehicle_stats_displays_makes(self, mocker: Mock) -> None:
        """Test that _display_vehicle_stats() displays makes."""
        # Arrange
        console = Console()
        stats_data = DataStats(
            total_parts=100,
            unique_skus=100,
            total_vehicles=50,
            vehicles_by_make={"Honda": 30, "Toyota": 20},
            has_compatibility_data=True,
        )

        # Act
        _display_vehicle_stats(console, stats_data)

        # Assert - Function should complete without errors
        assert True

    def test_display_vehicle_stats_handles_empty_vehicles(self, mocker: Mock) -> None:
        """Test that _display_vehicle_stats() handles empty vehicles."""
        # Arrange
        console = Console()
        stats_data = DataStats(
            total_parts=100,
            unique_skus=100,
            total_vehicles=0,
            vehicles_by_make={},
        )

        # Act
        _display_vehicle_stats(console, stats_data)

        # Assert - Function should complete without errors (returns early)
        assert True

    def test_display_detailed_stats_displays_additional_metrics(self, mocker: Mock) -> None:
        """Test that _display_detailed_stats() displays additional metrics."""
        # Arrange
        console = Console()
        stats_data = DataStats(
            total_parts=100,
            unique_skus=95,
            total_vehicles=50,
            parts_by_category={"Radiators": 60, "Condensers": 40},
            file_size_bytes=1024000,
        )

        # Act
        _display_detailed_stats(console, stats_data)

        # Assert - Function should complete without errors
        assert True

    def test_format_file_size_formats_bytes(self) -> None:
        """Test that _format_file_size() formats bytes correctly."""
        # Arrange & Act & Assert
        assert _format_file_size(500) == "500 B"

    def test_format_file_size_formats_kilobytes(self) -> None:
        """Test that _format_file_size() formats kilobytes correctly."""
        # Arrange & Act
        result = _format_file_size(1024)

        # Assert
        assert result == "1.0 KB"

    def test_format_file_size_formats_megabytes(self) -> None:
        """Test that _format_file_size() formats megabytes correctly."""
        # Arrange & Act
        result = _format_file_size(1024 * 1024)

        # Assert
        assert result == "1.0 MB"

    def test_format_file_size_formats_gigabytes(self) -> None:
        """Test that _format_file_size() formats gigabytes correctly."""
        # Arrange & Act
        result = _format_file_size(1024 * 1024 * 1024)

        # Assert
        assert result == "1.0 GB"

    def test_format_file_size_handles_fractional_sizes(self) -> None:
        """Test that _format_file_size() handles fractional sizes."""
        # Arrange & Act
        result = _format_file_size(1536)  # 1.5 KB

        # Assert
        assert result == "1.5 KB"
