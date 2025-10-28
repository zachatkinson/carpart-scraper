"""Unit tests for export command.

This module tests the export command functionality including:
- Command-line option parsing and validation
- Data loading from directories
- JSONExporter integration
- Error handling and exit codes
- Help text display
"""

import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock

import pytest
from click.testing import CliRunner

from src.cli.commands.export import (
    _display_export_stats,
    _load_compatibility_from_directory,
    _load_parts_from_directory,
    export,
)
from src.models.part import Part
from src.models.vehicle import VehicleCompatibility


class TestExportCommand:
    """Tests for export command."""

    def test_export_command_requires_input_option(self) -> None:
        """Test that --input option is required."""
        # Arrange
        runner = CliRunner()

        # Act
        result = runner.invoke(export, ["--output", "test.json"])

        # Assert
        assert result.exit_code != 0
        assert "Missing option '--input'" in result.output or "required" in result.output.lower()

    def test_export_command_requires_output_option(self) -> None:
        """Test that --output option is required."""
        # Arrange
        runner = CliRunner()

        # Act
        with runner.isolated_filesystem():
            Path("input").mkdir()
            result = runner.invoke(export, ["--input", "input"])

        # Assert
        assert result.exit_code != 0
        assert "Missing option '--output'" in result.output or "required" in result.output.lower()

    def test_export_command_with_valid_input_output(self, tmp_path: Path, mocker: Mock) -> None:
        """Test export command with valid input and output options."""
        # Arrange
        runner = CliRunner()
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        # Create test data file
        test_parts = [
            {
                "sku": "CSF-12345",
                "name": "Test Radiator",
                "price": "299.99",
                "category": "Radiators",
            }
        ]
        (input_dir / "parts.json").write_text(json.dumps({"parts": test_parts}))

        # Mock JSONExporter
        mock_exporter = mocker.patch("src.cli.commands.export.JSONExporter")
        mock_instance = Mock()
        mock_instance.export_parts.return_value = tmp_path / "exports" / "output.json"
        mock_instance.get_export_stats.return_value = {
            "total_parts": 1,
            "file_size_mb": 0.001,
            "export_date": "2025-01-15T10:00:00Z",
            "version": "1.0",
        }
        mock_exporter.return_value = mock_instance

        # Act
        result = runner.invoke(
            export,
            [
                "--input",
                str(input_dir),
                "--output",
                "output.json",
                "--output-dir",
                str(tmp_path / "exports"),
            ],
        )

        # Assert
        assert result.exit_code == 0
        assert "Export completed successfully" in result.output
        mock_exporter.assert_called_once()

    def test_export_command_format_option_accepts_json(self, tmp_path: Path, mocker: Mock) -> None:
        """Test that --format option accepts 'json'."""
        # Arrange
        runner = CliRunner()
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        test_parts = [{"sku": "CSF-12345", "name": "Test", "category": "Radiators"}]
        (input_dir / "parts.json").write_text(json.dumps({"parts": test_parts}))

        mock_exporter = mocker.patch("src.cli.commands.export.JSONExporter")
        mock_instance = Mock()
        mock_instance.export_parts.return_value = tmp_path / "output.json"
        mock_instance.get_export_stats.return_value = {"total_parts": 1}
        mock_exporter.return_value = mock_instance

        # Act
        result = runner.invoke(
            export,
            ["--input", str(input_dir), "--output", "test.json", "--format", "json"],
        )

        # Assert
        assert result.exit_code == 0
        mock_instance.export_parts.assert_called_once()

    def test_export_command_format_option_accepts_hierarchical(
        self, tmp_path: Path, mocker: Mock
    ) -> None:
        """Test that --format option accepts 'hierarchical'."""
        # Arrange
        runner = CliRunner()
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        # Create parts and compatibility files
        test_parts = [{"sku": "CSF-12345", "name": "Test", "category": "Radiators"}]
        (input_dir / "parts.json").write_text(json.dumps({"parts": test_parts}))

        test_compat = [
            {
                "part_sku": "CSF-12345",
                "vehicles": [{"make": "Audi", "model": "A4", "year": 2020}],
            }
        ]
        (input_dir / "compatibility.json").write_text(json.dumps({"compatibility": test_compat}))

        mock_exporter = mocker.patch("src.cli.commands.export.JSONExporter")
        mock_instance = Mock()
        mock_instance.export_hierarchical.return_value = tmp_path / "output.json"
        mock_instance.get_export_stats.return_value = {"total_parts": 1}
        mock_exporter.return_value = mock_instance

        # Act
        result = runner.invoke(
            export,
            ["--input", str(input_dir), "--output", "test.json", "--format", "hierarchical"],
        )

        # Assert
        assert result.exit_code == 0
        mock_instance.export_hierarchical.assert_called_once()

    def test_export_command_pretty_flag_enabled_by_default(
        self, tmp_path: Path, mocker: Mock
    ) -> None:
        """Test that --pretty flag is enabled by default."""
        # Arrange
        runner = CliRunner()
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        test_parts = [{"sku": "CSF-12345", "name": "Test", "category": "Radiators"}]
        (input_dir / "parts.json").write_text(json.dumps({"parts": test_parts}))

        mock_exporter = mocker.patch("src.cli.commands.export.JSONExporter")
        mock_instance = Mock()
        mock_instance.export_parts.return_value = tmp_path / "output.json"
        mock_instance.get_export_stats.return_value = {"total_parts": 1}
        mock_exporter.return_value = mock_instance

        # Act
        result = runner.invoke(
            export,
            ["--input", str(input_dir), "--output", "test.json"],
        )

        # Assert
        assert result.exit_code == 0
        # Verify pretty=True was passed
        call_kwargs = mock_instance.export_parts.call_args[1]
        assert call_kwargs["pretty"] is True

    def test_export_command_no_pretty_flag_disables_formatting(
        self, tmp_path: Path, mocker: Mock
    ) -> None:
        """Test that --no-pretty flag disables JSON formatting."""
        # Arrange
        runner = CliRunner()
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        test_parts = [{"sku": "CSF-12345", "name": "Test", "category": "Radiators"}]
        (input_dir / "parts.json").write_text(json.dumps({"parts": test_parts}))

        mock_exporter = mocker.patch("src.cli.commands.export.JSONExporter")
        mock_instance = Mock()
        mock_instance.export_parts.return_value = tmp_path / "output.json"
        mock_instance.get_export_stats.return_value = {"total_parts": 1}
        mock_exporter.return_value = mock_instance

        # Act
        result = runner.invoke(
            export,
            ["--input", str(input_dir), "--output", "test.json", "--no-pretty"],
        )

        # Assert
        assert result.exit_code == 0
        call_kwargs = mock_instance.export_parts.call_args[1]
        assert call_kwargs["pretty"] is False

    def test_export_command_output_dir_creates_directory(
        self, tmp_path: Path, mocker: Mock
    ) -> None:
        """Test that --output-dir creates the directory if it doesn't exist."""
        # Arrange
        runner = CliRunner()
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "new_exports"

        test_parts = [{"sku": "CSF-12345", "name": "Test", "category": "Radiators"}]
        (input_dir / "parts.json").write_text(json.dumps({"parts": test_parts}))

        # Mock JSONExporter - it will create the directory
        mock_exporter = mocker.patch("src.cli.commands.export.JSONExporter")
        mock_instance = Mock()
        mock_instance.export_parts.return_value = output_dir / "test.json"
        mock_instance.get_export_stats.return_value = {"total_parts": 1}
        mock_exporter.return_value = mock_instance

        # Act
        result = runner.invoke(
            export,
            [
                "--input",
                str(input_dir),
                "--output",
                "test.json",
                "--output-dir",
                str(output_dir),
            ],
        )

        # Assert
        assert result.exit_code == 0
        # Verify JSONExporter was initialized with correct output_dir
        mock_exporter.assert_called_once_with(output_dir=output_dir)

    def test_export_command_loads_parts_from_directory(self, tmp_path: Path, mocker: Mock) -> None:
        """Test that command loads parts from directory correctly."""
        # Arrange
        runner = CliRunner()
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        test_parts = [
            {"sku": "CSF-12345", "name": "Radiator 1", "category": "Radiators"},
            {"sku": "CSF-67890", "name": "Radiator 2", "category": "Radiators"},
        ]
        (input_dir / "parts.json").write_text(json.dumps({"parts": test_parts}))

        mock_exporter = mocker.patch("src.cli.commands.export.JSONExporter")
        mock_instance = Mock()
        mock_instance.export_parts.return_value = tmp_path / "output.json"
        mock_instance.get_export_stats.return_value = {"total_parts": 2}
        mock_exporter.return_value = mock_instance

        # Act
        result = runner.invoke(
            export,
            ["--input", str(input_dir), "--output", "test.json"],
        )

        # Assert
        assert result.exit_code == 0
        assert "Loaded 2 parts" in result.output
        # Verify export_parts was called with list of Part instances
        call_args = mock_instance.export_parts.call_args
        parts_arg = call_args[1]["parts"]
        assert len(parts_arg) == 2
        assert all(isinstance(p, Part) for p in parts_arg)

    def test_export_command_calls_json_exporter_with_correct_params(
        self, tmp_path: Path, mocker: Mock
    ) -> None:
        """Test that command calls JSONExporter with correct parameters."""
        # Arrange
        runner = CliRunner()
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        test_parts = [{"sku": "CSF-12345", "name": "Test", "category": "Radiators"}]
        (input_dir / "parts.json").write_text(json.dumps({"parts": test_parts}))

        mock_exporter = mocker.patch("src.cli.commands.export.JSONExporter")
        mock_instance = Mock()
        mock_instance.export_parts.return_value = tmp_path / "my_export.json"
        mock_instance.get_export_stats.return_value = {"total_parts": 1}
        mock_exporter.return_value = mock_instance

        # Act
        result = runner.invoke(
            export,
            ["--input", str(input_dir), "--output", "my_export.json", "--no-pretty"],
        )

        # Assert
        assert result.exit_code == 0
        mock_instance.export_parts.assert_called_once()
        call_kwargs = mock_instance.export_parts.call_args[1]
        assert call_kwargs["filename"] == "my_export.json"
        assert call_kwargs["pretty"] is False
        assert isinstance(call_kwargs["parts"], list)

    def test_export_command_exit_code_zero_on_success(self, tmp_path: Path, mocker: Mock) -> None:
        """Test that command returns exit code 0 on success."""
        # Arrange
        runner = CliRunner()
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        test_parts = [{"sku": "CSF-12345", "name": "Test", "category": "Radiators"}]
        (input_dir / "parts.json").write_text(json.dumps({"parts": test_parts}))

        mock_exporter = mocker.patch("src.cli.commands.export.JSONExporter")
        mock_instance = Mock()
        mock_instance.export_parts.return_value = tmp_path / "output.json"
        mock_instance.get_export_stats.return_value = {"total_parts": 1}
        mock_exporter.return_value = mock_instance

        # Act
        result = runner.invoke(
            export,
            ["--input", str(input_dir), "--output", "test.json"],
        )

        # Assert
        assert result.exit_code == 0

    def test_export_command_exit_code_nonzero_on_error(self, tmp_path: Path) -> None:
        """Test that command returns non-zero exit code on error."""
        # Arrange
        runner = CliRunner()
        input_dir = tmp_path / "nonexistent"

        # Act
        result = runner.invoke(
            export,
            ["--input", str(input_dir), "--output", "test.json"],
        )

        # Assert
        assert result.exit_code != 0

    def test_export_command_handles_exporter_errors(self, tmp_path: Path, mocker: Mock) -> None:
        """Test that command handles JSONExporter errors gracefully."""
        # Arrange
        runner = CliRunner()
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        test_parts = [{"sku": "CSF-12345", "name": "Test", "category": "Radiators"}]
        (input_dir / "parts.json").write_text(json.dumps({"parts": test_parts}))

        mock_exporter = mocker.patch("src.cli.commands.export.JSONExporter")
        mock_instance = Mock()
        mock_instance.export_parts.side_effect = OSError("Disk full")
        mock_exporter.return_value = mock_instance

        # Act
        result = runner.invoke(
            export,
            ["--input", str(input_dir), "--output", "test.json"],
        )

        # Assert
        assert result.exit_code != 0
        assert "Failed to process data" in result.output or "Disk full" in result.output

    def test_export_command_help_displays_correctly(self) -> None:
        """Test that help text displays correctly."""
        # Arrange
        runner = CliRunner()

        # Act
        result = runner.invoke(export, ["--help"])

        # Assert
        assert result.exit_code == 0
        assert "Export scraped data to JSON format" in result.output
        assert "--input" in result.output
        assert "--output" in result.output
        assert "--format" in result.output
        assert "--pretty" in result.output
        assert "--output-dir" in result.output

    def test_export_command_warns_when_no_parts_found(self, tmp_path: Path) -> None:
        """Test that command warns when no parts are found."""
        # Arrange
        runner = CliRunner()
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        # Act
        result = runner.invoke(
            export,
            ["--input", str(input_dir), "--output", "test.json"],
        )

        # Assert
        assert result.exit_code == 0
        assert "No parts found" in result.output

    def test_export_command_warns_when_no_compatibility_for_hierarchical(
        self, tmp_path: Path, mocker: Mock
    ) -> None:
        """Test warning when hierarchical export requested but no compatibility data found."""
        # Arrange
        runner = CliRunner()
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        test_parts = [{"sku": "CSF-12345", "name": "Test", "category": "Radiators"}]
        (input_dir / "parts.json").write_text(json.dumps({"parts": test_parts}))

        mocker.patch("src.cli.commands.export.JSONExporter")

        # Act
        result = runner.invoke(
            export,
            ["--input", str(input_dir), "--output", "test.json", "--format", "hierarchical"],
        )

        # Assert
        assert result.exit_code == 0
        assert "No compatibility data found" in result.output


class TestLoadPartsFromDirectory:
    """Tests for _load_parts_from_directory function."""

    def test_load_parts_finds_json_files(self, tmp_path: Path) -> None:
        """Test that function finds and loads JSON files."""
        # Arrange
        test_parts = [
            {"sku": "CSF-12345", "name": "Radiator 1", "category": "Radiators"},
            {"sku": "CSF-67890", "name": "Radiator 2", "category": "Radiators"},
        ]
        (tmp_path / "parts.json").write_text(json.dumps({"parts": test_parts}))

        # Act
        parts = _load_parts_from_directory(tmp_path)

        # Assert
        assert len(parts) == 2
        assert all(isinstance(p, Part) for p in parts)
        assert parts[0].sku == "CSF-12345"
        assert parts[1].sku == "CSF-67890"

    def test_load_parts_handles_dict_with_parts_key(self, tmp_path: Path) -> None:
        """Test loading from dict with 'parts' key."""
        # Arrange
        test_data = {
            "parts": [
                {"sku": "CSF-12345", "name": "Test", "category": "Radiators"},
            ]
        }
        (tmp_path / "data.json").write_text(json.dumps(test_data))

        # Act
        parts = _load_parts_from_directory(tmp_path)

        # Assert
        assert len(parts) == 1
        assert parts[0].sku == "CSF-12345"

    def test_load_parts_handles_dict_with_data_key(self, tmp_path: Path) -> None:
        """Test loading from dict with 'data' key."""
        # Arrange
        test_data = {
            "data": [
                {"sku": "CSF-12345", "name": "Test", "category": "Radiators"},
            ]
        }
        (tmp_path / "data.json").write_text(json.dumps(test_data))

        # Act
        parts = _load_parts_from_directory(tmp_path)

        # Assert
        assert len(parts) == 1
        assert parts[0].sku == "CSF-12345"

    def test_load_parts_handles_dict_as_single_part(self, tmp_path: Path) -> None:
        """Test loading single part from dict structure."""
        # Arrange
        test_data = {"sku": "CSF-12345", "name": "Test", "category": "Radiators"}
        (tmp_path / "single_part.json").write_text(json.dumps(test_data))

        # Act
        parts = _load_parts_from_directory(tmp_path)

        # Assert
        assert len(parts) == 1
        assert parts[0].sku == "CSF-12345"

    def test_load_parts_handles_list_structure(self, tmp_path: Path) -> None:
        """Test loading from list structure."""
        # Arrange
        test_data = [
            {"sku": "CSF-12345", "name": "Test 1", "category": "Radiators"},
            {"sku": "CSF-67890", "name": "Test 2", "category": "Condensers"},
        ]
        (tmp_path / "parts_list.json").write_text(json.dumps(test_data))

        # Act
        parts = _load_parts_from_directory(tmp_path)

        # Assert
        assert len(parts) == 2
        assert parts[0].sku == "CSF-12345"
        assert parts[1].sku == "CSF-67890"

    def test_load_parts_handles_multiple_files(self, tmp_path: Path) -> None:
        """Test loading parts from multiple JSON files."""
        # Arrange
        file1_data = {"parts": [{"sku": "CSF-12345", "name": "Test 1", "category": "Radiators"}]}
        file2_data = {"parts": [{"sku": "CSF-67890", "name": "Test 2", "category": "Condensers"}]}

        (tmp_path / "parts1.json").write_text(json.dumps(file1_data))
        (tmp_path / "parts2.json").write_text(json.dumps(file2_data))

        # Act
        parts = _load_parts_from_directory(tmp_path)

        # Assert
        assert len(parts) == 2

    def test_load_parts_skips_invalid_json(self, tmp_path: Path, mocker: Mock) -> None:
        """Test that function skips files with invalid JSON."""
        # Arrange
        (tmp_path / "invalid.json").write_text("{ invalid json }")
        (tmp_path / "valid.json").write_text(
            json.dumps({"parts": [{"sku": "CSF-12345", "name": "Test", "category": "Radiators"}]})
        )

        # Mock logger to verify warning
        mock_logger = mocker.patch("src.cli.commands.export.logger")

        # Act
        parts = _load_parts_from_directory(tmp_path)

        # Assert
        assert len(parts) == 1
        assert parts[0].sku == "CSF-12345"
        mock_logger.warning.assert_called()

    def test_load_parts_skips_invalid_part_data(self, tmp_path: Path, mocker: Mock) -> None:
        """Test that function skips parts with invalid data."""
        # Arrange
        test_data = {
            "parts": [
                {"sku": "CSF-12345", "name": "Valid", "category": "Radiators"},
                {"sku": "INVALID", "name": "Bad SKU", "category": "Radiators"},  # Invalid SKU
                {"name": "Missing SKU", "category": "Radiators"},  # Missing SKU
            ]
        }
        (tmp_path / "parts.json").write_text(json.dumps(test_data))

        mock_logger = mocker.patch("src.cli.commands.export.logger")

        # Act
        parts = _load_parts_from_directory(tmp_path)

        # Assert
        assert len(parts) == 1
        assert parts[0].sku == "CSF-12345"
        # Verify warnings were logged for invalid parts
        assert mock_logger.warning.call_count >= 2

    def test_load_parts_returns_empty_list_when_no_files(self, tmp_path: Path) -> None:
        """Test that function returns empty list when no JSON files found."""
        # Arrange
        # Empty directory

        # Act
        parts = _load_parts_from_directory(tmp_path)

        # Assert
        assert parts == []

    def test_load_parts_handles_parts_with_all_fields(self, tmp_path: Path) -> None:
        """Test loading parts with all optional fields populated."""
        # Arrange
        test_data = {
            "parts": [
                {
                    "sku": "CSF-12345",
                    "name": "High Performance Radiator",
                    "price": "299.99",
                    "description": "Premium cooling solution",
                    "category": "Radiators",
                    "specifications": {"rows": "2", "core_size": "26x19"},
                    "images": [
                        {"url": "http://example.com/img1.jpg", "is_primary": True},
                    ],
                    "manufacturer": "CSF",
                    "in_stock": True,
                    "features": ["High flow", "Lightweight"],
                    "tech_notes": "Requires modification",
                    "position": "Front",
                }
            ]
        }
        (tmp_path / "parts.json").write_text(json.dumps(test_data))

        # Act
        parts = _load_parts_from_directory(tmp_path)

        # Assert
        assert len(parts) == 1
        part = parts[0]
        assert part.sku == "CSF-12345"
        assert part.price == Decimal("299.99")
        assert part.description == "Premium cooling solution"
        assert len(part.images) == 1
        assert part.images[0].is_primary is True
        assert len(part.features) == 2


class TestLoadCompatibilityFromDirectory:
    """Tests for _load_compatibility_from_directory function."""

    def test_load_compatibility_finds_compatibility_files(self, tmp_path: Path) -> None:
        """Test that function finds compatibility JSON files."""
        # Arrange
        test_data = {
            "compatibility": [
                {
                    "part_sku": "CSF-12345",
                    "vehicles": [{"make": "Audi", "model": "A4", "year": 2020}],
                }
            ]
        }
        (tmp_path / "compatibility.json").write_text(json.dumps(test_data))

        # Act
        compatibility = _load_compatibility_from_directory(tmp_path)

        # Assert
        assert len(compatibility) == 1
        assert isinstance(compatibility[0], VehicleCompatibility)
        assert compatibility[0].part_sku == "CSF-12345"

    def test_load_compatibility_handles_dict_with_compatibility_key(self, tmp_path: Path) -> None:
        """Test loading from dict with 'compatibility' key."""
        # Arrange
        test_data = {
            "compatibility": [
                {
                    "part_sku": "CSF-12345",
                    "vehicles": [{"make": "BMW", "model": "3 Series", "year": 2021}],
                }
            ]
        }
        (tmp_path / "compat.json").write_text(json.dumps(test_data))

        # Act
        compatibility = _load_compatibility_from_directory(tmp_path)

        # Assert
        assert len(compatibility) == 1
        assert compatibility[0].vehicles[0].make == "Bmw"

    def test_load_compatibility_handles_dict_with_data_key(self, tmp_path: Path) -> None:
        """Test loading from dict with 'data' key."""
        # Arrange
        test_data = {
            "data": [
                {
                    "part_sku": "CSF-12345",
                    "vehicles": [{"make": "Mercedes", "model": "C-Class", "year": 2022}],
                }
            ]
        }
        (tmp_path / "compat.json").write_text(json.dumps(test_data))

        # Act
        compatibility = _load_compatibility_from_directory(tmp_path)

        # Assert
        assert len(compatibility) == 1
        assert compatibility[0].vehicles[0].make == "Mercedes"

    def test_load_compatibility_handles_list_structure(self, tmp_path: Path) -> None:
        """Test loading from list structure."""
        # Arrange
        test_data = [
            {
                "part_sku": "CSF-12345",
                "vehicles": [{"make": "Audi", "model": "A4", "year": 2020}],
            },
            {
                "part_sku": "CSF-67890",
                "vehicles": [{"make": "BMW", "model": "X5", "year": 2021}],
            },
        ]
        (tmp_path / "compat.json").write_text(json.dumps(test_data))

        # Act
        compatibility = _load_compatibility_from_directory(tmp_path)

        # Assert
        assert len(compatibility) == 2

    def test_load_compatibility_returns_empty_list_when_no_files(self, tmp_path: Path) -> None:
        """Test that function returns empty list when no compatibility files found."""
        # Arrange
        # Create a parts file but no compatibility file
        (tmp_path / "parts.json").write_text(json.dumps({"parts": []}))

        # Act
        compatibility = _load_compatibility_from_directory(tmp_path)

        # Assert
        assert compatibility == []

    def test_load_compatibility_skips_invalid_json(self, tmp_path: Path, mocker: Mock) -> None:
        """Test that function skips files with invalid JSON."""
        # Arrange
        (tmp_path / "compatibility_invalid.json").write_text("{ invalid }")
        (tmp_path / "compatibility_valid.json").write_text(
            json.dumps(
                {
                    "compatibility": [
                        {
                            "part_sku": "CSF-12345",
                            "vehicles": [{"make": "Audi", "model": "A4", "year": 2020}],
                        }
                    ]
                }
            )
        )

        mock_logger = mocker.patch("src.cli.commands.export.logger")

        # Act
        compatibility = _load_compatibility_from_directory(tmp_path)

        # Assert
        assert len(compatibility) == 1
        mock_logger.warning.assert_called()

    def test_load_compatibility_skips_invalid_data(self, tmp_path: Path, mocker: Mock) -> None:
        """Test that function skips compatibility with invalid data."""
        # Arrange
        test_data = {
            "compatibility": [
                {
                    "part_sku": "CSF-12345",
                    "vehicles": [{"make": "Audi", "model": "A4", "year": 2020}],
                },
                {
                    "part_sku": "INVALID",  # Invalid SKU format
                    "vehicles": [{"make": "BMW", "model": "X5", "year": 2021}],
                },
                {
                    # Missing part_sku
                    "vehicles": [{"make": "Mercedes", "model": "C-Class", "year": 2022}],
                },
            ]
        }
        (tmp_path / "compatibility.json").write_text(json.dumps(test_data))

        mock_logger = mocker.patch("src.cli.commands.export.logger")

        # Act
        compatibility = _load_compatibility_from_directory(tmp_path)

        # Assert
        assert len(compatibility) == 1
        assert compatibility[0].part_sku == "CSF-12345"
        assert mock_logger.warning.call_count >= 2

    def test_load_compatibility_handles_multiple_vehicles(self, tmp_path: Path) -> None:
        """Test loading compatibility with multiple vehicles."""
        # Arrange
        test_data = {
            "compatibility": [
                {
                    "part_sku": "CSF-12345",
                    "vehicles": [
                        {"make": "Audi", "model": "A4", "year": 2020},
                        {"make": "Audi", "model": "A4", "year": 2021},
                        {"make": "Audi", "model": "A4", "year": 2022},
                    ],
                }
            ]
        }
        (tmp_path / "compatibility.json").write_text(json.dumps(test_data))

        # Act
        compatibility = _load_compatibility_from_directory(tmp_path)

        # Assert
        assert len(compatibility) == 1
        assert len(compatibility[0].vehicles) == 3


class TestDisplayExportStats:
    """Tests for _display_export_stats function."""

    def test_display_export_stats_with_valid_stats(
        self, tmp_path: Path, mocker: Mock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test displaying statistics with valid data."""
        # Arrange
        mock_exporter = Mock()
        mock_exporter.get_export_stats.return_value = {
            "total_parts": 150,
            "file_size_mb": 2.5,
            "export_date": "2025-01-15T10:30:00Z",
            "version": "1.0",
        }
        output_path = tmp_path / "test.json"
        output_path.touch()

        # Mock console to avoid Rich table issues in tests
        mock_console = mocker.patch("src.cli.commands.export.console")

        # Act
        _display_export_stats(mock_exporter, output_path)

        # Assert
        mock_exporter.get_export_stats.assert_called_once_with(output_path)
        # Verify console.print was called with table
        assert mock_console.print.call_count >= 2

    def test_display_export_stats_handles_error_in_stats(
        self, tmp_path: Path, mocker: Mock
    ) -> None:
        """Test handling of error in statistics generation."""
        # Arrange
        mock_exporter = Mock()
        mock_exporter.get_export_stats.return_value = {"error": "File not found"}
        output_path = tmp_path / "nonexistent.json"

        mock_console = mocker.patch("src.cli.commands.export.console")

        # Act
        _display_export_stats(mock_exporter, output_path)

        # Assert
        mock_exporter.get_export_stats.assert_called_once_with(output_path)
        # Verify warning was printed
        print_calls = mock_console.print.call_args_list
        assert any("Could not generate statistics" in str(call) for call in print_calls)

    def test_display_export_stats_handles_missing_fields(
        self, tmp_path: Path, mocker: Mock
    ) -> None:
        """Test displaying stats with missing fields (uses defaults)."""
        # Arrange
        mock_exporter = Mock()
        mock_exporter.get_export_stats.return_value = {
            "total_parts": 50,
            # Missing other fields
        }
        output_path = tmp_path / "test.json"
        output_path.touch()

        mock_console = mocker.patch("src.cli.commands.export.console")

        # Act
        _display_export_stats(mock_exporter, output_path)

        # Assert
        mock_exporter.get_export_stats.assert_called_once()
        assert mock_console.print.call_count >= 2
