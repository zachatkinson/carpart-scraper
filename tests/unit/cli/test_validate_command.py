"""Unit tests for validate command.

Tests the validate CLI command using Click's CliRunner for comprehensive
command-line interface testing. Follows AAA (Arrange-Act-Assert) pattern.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from src.cli.commands.validate import validate

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI runner for testing commands.

    Returns:
        CliRunner instance for invoking CLI commands
    """
    return CliRunner()


@pytest.fixture
def valid_parts_data() -> dict[str, Any]:
    """Create valid parts export data.

    Returns:
        Dict containing valid parts export structure
    """
    return {
        "metadata": {
            "export_date": "2025-01-15T10:30:00Z",
            "version": "1.0.0",
            "total_parts": 2,
        },
        "parts": [
            {
                "sku": "CSF-12345",
                "name": "High Performance Radiator",
                "price": "299.99",
                "description": "Premium aluminum radiator",
                "category": "Radiators",
                "specifications": {"material": "aluminum", "rows": "2"},
                "images": [{"url": "https://example.com/img1.jpg", "is_primary": True}],
                "manufacturer": "CSF",
                "in_stock": True,
                "features": ["High efficiency"],
                "tech_notes": "Direct fit replacement",
                "position": "Front",
            },
            {
                "sku": "CSF-67890",
                "name": "Performance Condenser",
                "price": "199.99",
                "description": "High-flow condenser",
                "category": "Condensers",
                "specifications": {"material": "aluminum"},
                "images": [{"url": "https://example.com/img2.jpg", "is_primary": True}],
                "manufacturer": "CSF",
                "in_stock": True,
                "features": ["Enhanced cooling"],
                "tech_notes": "OEM replacement",
                "position": "Front",
            },
        ],
    }


@pytest.fixture
def invalid_parts_data() -> dict[str, Any]:
    """Create invalid parts export data (missing required fields).

    Returns:
        Dict containing invalid parts export structure
    """
    return {
        "metadata": {
            "export_date": "2025-01-15T10:30:00Z",
            "total_parts": 1,
        },
        "parts": [
            {
                "sku": "INVALID",  # Should start with CSF-
                "name": "",  # Empty name
                # Missing required fields: price, description, category, etc.
            }
        ],
    }


@pytest.fixture
def parts_with_warnings_data() -> dict[str, Any]:
    """Create parts export data with warnings (missing optional fields).

    Returns:
        Dict containing parts with warning-level issues
    """
    return {
        "metadata": {
            "export_date": "2025-01-15T10:30:00Z",
            "total_parts": 1,
        },
        "parts": [
            {
                "sku": "CSF-12345",
                "name": "Test Part",
                "price": "99.99",
                "description": "Test description",
                "category": "Radiators",
                "specifications": {},
                "images": [],  # No images - warning
                "manufacturer": "CSF",
                "in_stock": True,
                "features": [],
                "tech_notes": "",
                "position": "Front",
            }
        ],
    }


# ============================================================================
# Test: Command Options and Arguments
# ============================================================================


def test_validate_command_accepts_file_input(
    cli_runner: CliRunner, tmp_path: Path, valid_parts_data: dict[str, Any]
) -> None:
    """Test that --input option accepts a file path.

    Verifies the validate command can process a single JSON file
    when provided via the --input option.
    """
    # Arrange
    json_file = tmp_path / "parts.json"
    json_file.write_text(json.dumps(valid_parts_data), encoding="utf-8")

    # Act
    result = cli_runner.invoke(validate, ["--input", str(json_file)])

    # Assert
    assert result.exit_code == 0
    assert "Validating:" in result.output
    assert "parts.json" in result.output
    assert "Validation PASSED" in result.output


def test_validate_command_accepts_directory_input(
    cli_runner: CliRunner, tmp_path: Path, valid_parts_data: dict[str, Any]
) -> None:
    """Test that --input option accepts a directory path.

    Verifies the validate command can process all JSON files
    in a directory when provided via the --input option.
    """
    # Arrange
    export_dir = tmp_path / "exports"
    export_dir.mkdir()

    file1 = export_dir / "parts1.json"
    file1.write_text(json.dumps(valid_parts_data), encoding="utf-8")

    file2 = export_dir / "parts2.json"
    file2.write_text(json.dumps(valid_parts_data), encoding="utf-8")

    # Act
    result = cli_runner.invoke(validate, ["--input", str(export_dir)])

    # Assert
    assert result.exit_code == 0
    assert "Validating:" in result.output
    assert "parts1.json" in result.output
    assert "parts2.json" in result.output
    assert "Validation PASSED" in result.output


def test_validate_command_requires_input_option(cli_runner: CliRunner) -> None:
    """Test that --input option is required.

    Verifies the command fails with an error when --input is not provided.
    """
    # Arrange - No input provided

    # Act
    result = cli_runner.invoke(validate, [])

    # Assert
    assert result.exit_code != 0
    assert "Missing option '--input'" in result.output or "required" in result.output.lower()


def test_validate_command_strict_flag_default_false(
    cli_runner: CliRunner, tmp_path: Path, parts_with_warnings_data: dict[str, Any]
) -> None:
    """Test that --strict flag defaults to False.

    Verifies warnings don't cause validation failure when strict mode
    is not enabled.
    """
    # Arrange
    json_file = tmp_path / "parts_warnings.json"
    json_file.write_text(json.dumps(parts_with_warnings_data), encoding="utf-8")

    # Act
    result = cli_runner.invoke(validate, ["--input", str(json_file)])

    # Assert
    assert result.exit_code == 0  # Should pass with warnings
    assert "Validation PASSED" in result.output


def test_validate_command_strict_flag_treats_warnings_as_errors(
    cli_runner: CliRunner, tmp_path: Path, parts_with_warnings_data: dict[str, Any]
) -> None:
    """Test that --strict flag treats warnings as errors.

    Verifies that when strict mode is enabled, files with warnings
    fail validation and exit with code 1.
    """
    # Arrange
    json_file = tmp_path / "parts_warnings.json"
    json_file.write_text(json.dumps(parts_with_warnings_data), encoding="utf-8")

    # Act
    result = cli_runner.invoke(validate, ["--input", str(json_file), "--strict"])

    # Assert
    assert result.exit_code == 1  # Should fail in strict mode
    assert "Validation FAILED" in result.output


def test_validate_command_report_option_generates_text_report(
    cli_runner: CliRunner, tmp_path: Path, valid_parts_data: dict[str, Any]
) -> None:
    """Test that --report option generates a text report file.

    Verifies a validation report is created at the specified path
    when the --report option is used.
    """
    # Arrange
    json_file = tmp_path / "parts.json"
    json_file.write_text(json.dumps(valid_parts_data), encoding="utf-8")

    report_file = tmp_path / "validation_report.txt"

    # Act
    result = cli_runner.invoke(validate, ["--input", str(json_file), "--report", str(report_file)])

    # Assert
    assert result.exit_code == 0
    assert report_file.exists()
    assert "Report saved to:" in result.output

    # Verify report content
    report_content = report_file.read_text(encoding="utf-8")
    assert "VALIDATION REPORT" in report_content
    assert "Total Files:" in report_content
    assert "Passed:" in report_content


# ============================================================================
# Test: Exit Codes
# ============================================================================


def test_validate_command_exit_code_0_for_valid_data(
    cli_runner: CliRunner, tmp_path: Path, valid_parts_data: dict[str, Any]
) -> None:
    """Test exit code 0 when validating valid data.

    Verifies the command exits with code 0 when all files
    pass validation without errors.
    """
    # Arrange
    json_file = tmp_path / "valid_parts.json"
    json_file.write_text(json.dumps(valid_parts_data), encoding="utf-8")

    # Act
    result = cli_runner.invoke(validate, ["--input", str(json_file)])

    # Assert
    assert result.exit_code == 0
    assert "Validation PASSED" in result.output


def test_validate_command_exit_code_1_for_invalid_data(
    cli_runner: CliRunner, tmp_path: Path, invalid_parts_data: dict[str, Any]
) -> None:
    """Test exit code 1 when validating invalid data.

    Verifies the command exits with code 1 when validation
    fails due to errors in the data.
    """
    # Arrange
    json_file = tmp_path / "invalid_parts.json"
    json_file.write_text(json.dumps(invalid_parts_data), encoding="utf-8")

    # Act
    result = cli_runner.invoke(validate, ["--input", str(json_file)])

    # Assert
    assert result.exit_code == 1
    assert "Validation FAILED" in result.output


def test_validate_command_exit_code_1_for_missing_file(cli_runner: CliRunner) -> None:
    """Test exit code 1 when input file doesn't exist.

    Verifies the command exits with code 1 when the specified
    input file cannot be found.
    """
    # Arrange
    nonexistent_file = "/nonexistent/path/to/file.json"

    # Act
    result = cli_runner.invoke(validate, ["--input", nonexistent_file])

    # Assert
    assert result.exit_code != 0


# ============================================================================
# Test: Help Text
# ============================================================================


def test_validate_command_help_displays_correctly(cli_runner: CliRunner) -> None:
    """Test that help text displays correctly.

    Verifies the --help option shows comprehensive usage information
    including all options and examples.
    """
    # Arrange - No setup needed

    # Act
    result = cli_runner.invoke(validate, ["--help"])

    # Assert
    assert result.exit_code == 0
    assert "Validate JSON export files against Pydantic models" in result.output
    assert "--input" in result.output
    assert "--strict" in result.output
    assert "--report" in result.output
    assert "Exit Codes:" in result.output
    assert "Examples:" in result.output


# ============================================================================
# Test: File Validation with CliRunner
# ============================================================================


def test_validate_valid_json_file_succeeds(
    cli_runner: CliRunner, tmp_path: Path, valid_parts_data: dict[str, Any]
) -> None:
    """Test that validating a valid JSON file succeeds.

    Verifies the complete validation flow for a properly formatted
    JSON file with valid part data.
    """
    # Arrange
    json_file = tmp_path / "valid_parts.json"
    json_file.write_text(json.dumps(valid_parts_data), encoding="utf-8")

    # Act
    result = cli_runner.invoke(validate, ["--input", str(json_file)])

    # Assert
    assert result.exit_code == 0
    assert "Validation PASSED" in result.output
    assert "PASS" in result.output  # Status indicator
    assert "2" in result.output  # Total items


def test_validate_invalid_json_file_fails(
    cli_runner: CliRunner, tmp_path: Path, invalid_parts_data: dict[str, Any]
) -> None:
    """Test that validating an invalid JSON file fails.

    Verifies the validation correctly identifies and reports errors
    in malformed or incomplete part data.
    """
    # Arrange
    json_file = tmp_path / "invalid_parts.json"
    json_file.write_text(json.dumps(invalid_parts_data), encoding="utf-8")

    # Act
    result = cli_runner.invoke(validate, ["--input", str(json_file)])

    # Assert
    assert result.exit_code == 1
    assert "Validation FAILED" in result.output
    assert "FAIL" in result.output  # Status indicator
    assert "Error" in result.output or "error" in result.output


def test_validate_malformed_json_file_fails(cli_runner: CliRunner, tmp_path: Path) -> None:
    """Test that validating a malformed JSON file fails.

    Verifies the command handles JSON parsing errors gracefully
    and reports them to the user.
    """
    # Arrange
    json_file = tmp_path / "malformed.json"
    json_file.write_text("{ invalid json syntax", encoding="utf-8")

    # Act
    result = cli_runner.invoke(validate, ["--input", str(json_file)])

    # Assert
    assert result.exit_code == 1
    assert "Error:" in result.output or "error" in result.output.lower()


# ============================================================================
# Test: Directory Validation
# ============================================================================


def test_validate_directory_validates_all_files(
    cli_runner: CliRunner,
    tmp_path: Path,
    valid_parts_data: dict[str, Any],
    invalid_parts_data: dict[str, Any],
) -> None:
    """Test that directory validation processes all JSON files.

    Verifies the command discovers and validates all JSON files
    in the specified directory.
    """
    # Arrange
    export_dir = tmp_path / "exports"
    export_dir.mkdir()

    valid_file = export_dir / "valid.json"
    valid_file.write_text(json.dumps(valid_parts_data), encoding="utf-8")

    invalid_file = export_dir / "invalid.json"
    invalid_file.write_text(json.dumps(invalid_parts_data), encoding="utf-8")

    # Act
    result = cli_runner.invoke(validate, ["--input", str(export_dir)])

    # Assert
    assert result.exit_code == 1  # Should fail due to invalid file
    assert "valid.json" in result.output
    assert "invalid.json" in result.output
    assert "Validation FAILED" in result.output


def test_validate_empty_directory_succeeds(cli_runner: CliRunner, tmp_path: Path) -> None:
    """Test that validating an empty directory succeeds.

    Verifies the command handles empty directories gracefully
    without errors.
    """
    # Arrange
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    # Act
    result = cli_runner.invoke(validate, ["--input", str(empty_dir)])

    # Assert
    assert result.exit_code == 0
    assert "Validation PASSED" in result.output


# ============================================================================
# Test: Report Generation
# ============================================================================


def test_validate_report_created_when_specified(
    cli_runner: CliRunner, tmp_path: Path, valid_parts_data: dict[str, Any]
) -> None:
    """Test that report file is created when --report is specified.

    Verifies the report file is created with proper content structure
    when the --report option is used.
    """
    # Arrange
    json_file = tmp_path / "parts.json"
    json_file.write_text(json.dumps(valid_parts_data), encoding="utf-8")

    report_file = tmp_path / "report.txt"

    # Act
    result = cli_runner.invoke(validate, ["--input", str(json_file), "--report", str(report_file)])

    # Assert
    assert result.exit_code == 0
    assert report_file.exists()

    report_content = report_file.read_text(encoding="utf-8")
    assert "VALIDATION REPORT" in report_content
    assert "File: parts.json" in report_content
    assert "Status: PASS" in report_content


def test_validate_report_contains_error_details(
    cli_runner: CliRunner, tmp_path: Path, invalid_parts_data: dict[str, Any]
) -> None:
    """Test that report contains detailed error information.

    Verifies the generated report includes comprehensive error
    details for failed validations.
    """
    # Arrange
    json_file = tmp_path / "invalid.json"
    json_file.write_text(json.dumps(invalid_parts_data), encoding="utf-8")

    report_file = tmp_path / "error_report.txt"

    # Act
    result = cli_runner.invoke(validate, ["--input", str(json_file), "--report", str(report_file)])

    # Assert
    assert result.exit_code == 1
    assert report_file.exists()

    report_content = report_file.read_text(encoding="utf-8")
    assert "VALIDATION REPORT" in report_content
    assert "Status: FAIL" in report_content
    assert "ERRORS:" in report_content


def test_validate_report_includes_warnings_in_strict_mode(
    cli_runner: CliRunner, tmp_path: Path, parts_with_warnings_data: dict[str, Any]
) -> None:
    """Test that report includes warnings when in strict mode.

    Verifies warnings are properly documented in the report
    when strict mode is enabled.
    """
    # Arrange
    json_file = tmp_path / "warnings.json"
    json_file.write_text(json.dumps(parts_with_warnings_data), encoding="utf-8")

    report_file = tmp_path / "warnings_report.txt"

    # Act
    cli_runner.invoke(
        validate, ["--input", str(json_file), "--strict", "--report", str(report_file)]
    )

    # Assert
    assert report_file.exists()

    report_content = report_file.read_text(encoding="utf-8")
    assert "VALIDATION REPORT" in report_content
    assert "Strict Mode: Enabled" in report_content
    assert "WARNINGS:" in report_content or "Total Warnings:" in report_content


# ============================================================================
# Test: Strict Mode Behavior
# ============================================================================


def test_validate_strict_mode_converts_warnings_to_errors(
    cli_runner: CliRunner, tmp_path: Path, parts_with_warnings_data: dict[str, Any]
) -> None:
    """Test that strict mode treats warnings as validation failures.

    Verifies that files with only warnings pass in normal mode
    but fail in strict mode.
    """
    # Arrange
    json_file = tmp_path / "parts_warnings.json"
    json_file.write_text(json.dumps(parts_with_warnings_data), encoding="utf-8")

    # Act - Normal mode
    result_normal = cli_runner.invoke(validate, ["--input", str(json_file)])

    # Act - Strict mode
    result_strict = cli_runner.invoke(validate, ["--input", str(json_file), "--strict"])

    # Assert - Normal mode passes
    assert result_normal.exit_code == 0
    assert "Validation PASSED" in result_normal.output

    # Assert - Strict mode fails
    assert result_strict.exit_code == 1
    assert "Validation FAILED" in result_strict.output


def test_validate_strict_mode_shows_warning_details(
    cli_runner: CliRunner, tmp_path: Path, parts_with_warnings_data: dict[str, Any]
) -> None:
    """Test that strict mode displays warning details in output.

    Verifies warning messages are shown in the console output
    when strict mode is enabled.
    """
    # Arrange
    json_file = tmp_path / "parts_warnings.json"
    json_file.write_text(json.dumps(parts_with_warnings_data), encoding="utf-8")

    # Act
    result = cli_runner.invoke(validate, ["--input", str(json_file), "--strict"])

    # Assert
    assert result.exit_code == 1
    assert "Warning" in result.output or "warning" in result.output


# ============================================================================
# Test: Edge Cases
# ============================================================================


def test_validate_handles_unknown_export_format(cli_runner: CliRunner, tmp_path: Path) -> None:
    """Test that unknown export formats are handled gracefully.

    Verifies the command reports an error for JSON files that don't
    match any known export format.
    """
    # Arrange
    unknown_format = {"unknown_key": "unknown_value"}
    json_file = tmp_path / "unknown.json"
    json_file.write_text(json.dumps(unknown_format), encoding="utf-8")

    # Act
    result = cli_runner.invoke(validate, ["--input", str(json_file)])

    # Assert
    assert result.exit_code == 1
    assert "Error:" in result.output or "error" in result.output.lower()


def test_validate_handles_large_directory(
    cli_runner: CliRunner, tmp_path: Path, valid_parts_data: dict[str, Any]
) -> None:
    """Test that validation handles directories with many files.

    Verifies the command can process multiple files efficiently
    without errors.
    """
    # Arrange
    export_dir = tmp_path / "large_export"
    export_dir.mkdir()

    # Create 10 valid JSON files
    for i in range(10):
        file = export_dir / f"parts_{i}.json"
        file.write_text(json.dumps(valid_parts_data), encoding="utf-8")

    # Act
    result = cli_runner.invoke(validate, ["--input", str(export_dir)])

    # Assert
    assert result.exit_code == 0
    assert "Validation PASSED" in result.output


def test_validate_option_short_forms_work(
    cli_runner: CliRunner, tmp_path: Path, valid_parts_data: dict[str, Any]
) -> None:
    """Test that short option forms work correctly.

    Verifies -i and -r short options function identically
    to their long-form equivalents.
    """
    # Arrange
    json_file = tmp_path / "parts.json"
    json_file.write_text(json.dumps(valid_parts_data), encoding="utf-8")

    report_file = tmp_path / "report.txt"

    # Act - Use short option forms
    result = cli_runner.invoke(validate, ["-i", str(json_file), "-r", str(report_file)])

    # Assert
    assert result.exit_code == 0
    assert report_file.exists()
    assert "Validation PASSED" in result.output
