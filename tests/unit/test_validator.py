"""Unit tests for data validators.

Tests both the scraper DataValidator (src.scraper.validator) and
CLI DataValidator (src.cli.validators) following AAA pattern.
"""

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from src.cli.validators import (
    DataValidator as CLIDataValidator,
)
from src.cli.validators import ValidationIssue, ValidationResult
from src.models.part import Part, PartImage
from src.models.vehicle import VehicleCompatibility
from src.scraper.validator import DataValidator as ScraperDataValidator


class TestScraperDataValidator:
    """Tests for src.scraper.validator.DataValidator."""

    def test_validate_part_with_valid_data(self) -> None:
        """Test validate_part accepts valid part data."""
        # Arrange
        validator = ScraperDataValidator()
        valid_data = {
            "sku": "CSF-12345",
            "name": "High Performance Radiator",
            "price": "299.99",
            "category": "Radiators",
            "description": "Premium radiator for high performance applications",
        }

        # Act
        result = validator.validate_part(valid_data)

        # Assert
        assert isinstance(result, Part)
        assert result.sku == "CSF-12345"
        assert result.name == "High Performance Radiator"
        assert result.price == Decimal("299.99")
        assert result.category == "Radiators"

    def test_validate_part_with_missing_sku(self) -> None:
        """Test validate_part rejects data with missing SKU."""
        # Arrange
        validator = ScraperDataValidator()
        invalid_data = {
            "name": "Radiator",
            "price": "100.00",
            "category": "Radiators",
        }

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_part(invalid_data)

        # Assert error details
        assert "sku" in str(exc_info.value)

    def test_validate_part_with_empty_name(self) -> None:
        """Test validate_part rejects data with empty name."""
        # Arrange
        validator = ScraperDataValidator()
        invalid_data = {
            "sku": "CSF-12345",
            "name": "",
            "price": "100.00",
            "category": "Radiators",
        }

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_part(invalid_data)

        # Assert error contains name field
        assert "name" in str(exc_info.value)

    def test_validate_part_with_negative_price(self) -> None:
        """Test validate_part rejects data with negative price."""
        # Arrange
        validator = ScraperDataValidator()
        invalid_data = {
            "sku": "CSF-12345",
            "name": "Radiator",
            "price": "-50.00",
            "category": "Radiators",
        }

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_part(invalid_data)

        # Assert error relates to price
        assert "price" in str(exc_info.value).lower()

    def test_validate_part_preprocesses_features_list(self) -> None:
        """Test validate_part correctly preprocesses features list."""
        # Arrange
        validator = ScraperDataValidator()
        data = {
            "sku": "CSF-12345",
            "name": "Radiator",
            "category": "Radiators",
            "features": ["Feature 1", "Feature 2", "", "Feature 3", None],
        }

        # Act
        result = validator.validate_part(data)

        # Assert - empty strings and None should be filtered out
        assert result.features == ["Feature 1", "Feature 2", "Feature 3"]

    def test_validate_part_preprocesses_tech_notes_to_string(self) -> None:
        """Test validate_part converts tech_notes to string."""
        # Arrange
        validator = ScraperDataValidator()
        data = {
            "sku": "CSF-12345",
            "name": "Radiator",
            "category": "Radiators",
            "tech_notes": 12345,  # Non-string value
        }

        # Act
        result = validator.validate_part(data)

        # Assert
        assert result.tech_notes == "12345"
        assert isinstance(result.tech_notes, str)

    def test_validate_part_converts_empty_tech_notes_to_none(self) -> None:
        """Test validate_part converts empty tech_notes to None."""
        # Arrange
        validator = ScraperDataValidator()
        data = {
            "sku": "CSF-12345",
            "name": "Radiator",
            "category": "Radiators",
            "tech_notes": "   ",  # Whitespace only
        }

        # Act
        result = validator.validate_part(data)

        # Assert
        assert result.tech_notes is None

    def test_validate_part_preprocesses_position_to_string(self) -> None:
        """Test validate_part converts position to string."""
        # Arrange
        validator = ScraperDataValidator()
        data = {
            "sku": "CSF-12345",
            "name": "Radiator",
            "category": "Radiators",
            "position": 123,  # Non-string value
        }

        # Act
        result = validator.validate_part(data)

        # Assert
        assert result.position == "123"
        assert isinstance(result.position, str)

    def test_validate_part_converts_empty_position_to_none(self) -> None:
        """Test validate_part converts empty position to None."""
        # Arrange
        validator = ScraperDataValidator()
        data = {
            "sku": "CSF-12345",
            "name": "Radiator",
            "category": "Radiators",
            "position": "",
        }

        # Act
        result = validator.validate_part(data)

        # Assert
        assert result.position is None

    def test_validate_vehicle_compatibility_with_valid_data(self) -> None:
        """Test validate_compatibility accepts valid compatibility data."""
        # Arrange
        validator = ScraperDataValidator()
        valid_data = {
            "part_sku": "CSF-12345",
            "vehicles": [
                {"make": "Audi", "model": "A4", "year": 2020},
                {"make": "Audi", "model": "A4", "year": 2021},
            ],
        }

        # Act
        result = validator.validate_compatibility(valid_data)

        # Assert
        assert isinstance(result, VehicleCompatibility)
        assert result.part_sku == "CSF-12345"
        assert len(result.vehicles) == 2
        assert result.get_year_range() == (2020, 2021)

    def test_validate_vehicle_compatibility_with_invalid_data(self) -> None:
        """Test validate_compatibility rejects invalid compatibility data."""
        # Arrange
        validator = ScraperDataValidator()
        invalid_data = {
            "part_sku": "CSF-12345",
            "vehicles": [],  # Empty list - violates min_length=1
        }

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_compatibility(invalid_data)

        # Assert error relates to vehicles
        assert "vehicles" in str(exc_info.value)

    def test_preprocess_part_data_handles_all_field_types(self) -> None:
        """Test _preprocess_part_data handles various field types."""
        # Arrange
        validator = ScraperDataValidator()
        data: dict[str, Any] = {
            "sku": "CSF-12345",
            "name": "Radiator",
            "category": "Radiators",
            "price": "299.99",
            "specifications": None,  # Should become {}
            "features": None,  # Should become []
            "images": [{"url": "https://example.com/img.jpg"}],
        }

        # Act
        result = validator._preprocess_part_data(data)  # noqa: SLF001

        # Assert
        assert isinstance(result["price"], Decimal)
        assert result["specifications"] == {}
        assert result["features"] == []
        assert isinstance(result["images"][0], PartImage)
        assert result["manufacturer"] == "CSF"
        assert result["in_stock"] is True

    def test_parse_price_converts_string_to_decimal(self) -> None:
        """Test _parse_price converts string prices to Decimal."""
        # Arrange
        validator = ScraperDataValidator()

        # Act
        result = validator._parse_price("299.99")  # noqa: SLF001

        # Assert
        assert result == Decimal("299.99")
        assert isinstance(result, Decimal)

    def test_parse_price_converts_float_to_decimal(self) -> None:
        """Test _parse_price converts float prices to Decimal."""
        # Arrange
        validator = ScraperDataValidator()

        # Act
        result = validator._parse_price(299.99)  # noqa: SLF001

        # Assert
        assert result == Decimal("299.99")
        assert isinstance(result, Decimal)

    def test_parse_price_handles_price_with_dollar_sign(self) -> None:
        """Test _parse_price handles price strings with dollar signs."""
        # Arrange
        validator = ScraperDataValidator()

        # Act
        result = validator._parse_price("$299.99")  # noqa: SLF001

        # Assert
        assert result == Decimal("299.99")

    def test_parse_price_handles_price_with_commas(self) -> None:
        """Test _parse_price handles price strings with thousand separators."""
        # Arrange
        validator = ScraperDataValidator()

        # Act
        result = validator._parse_price("1,299.99")  # noqa: SLF001

        # Assert
        assert result == Decimal("1299.99")

    def test_parse_price_handles_decimal_input(self) -> None:
        """Test _parse_price returns Decimal unchanged when input is Decimal."""
        # Arrange
        validator = ScraperDataValidator()
        price = Decimal("299.99")

        # Act
        result = validator._parse_price(price)  # noqa: SLF001

        # Assert
        assert result == price
        assert result is price

    def test_parse_price_raises_on_empty_string(self) -> None:
        """Test _parse_price raises ValueError for empty string."""
        # Arrange
        validator = ScraperDataValidator()

        # Act & Assert
        with pytest.raises(ValueError, match="empty") as exc_info:
            validator._parse_price("")  # noqa: SLF001

        # Assert error message
        assert "empty" in str(exc_info.value).lower()

    def test_parse_price_raises_on_invalid_format(self) -> None:
        """Test _parse_price raises ValueError for invalid format."""
        # Arrange
        validator = ScraperDataValidator()

        # Act & Assert
        with pytest.raises(ValueError, match="parse") as exc_info:
            validator._parse_price("not-a-price")  # noqa: SLF001

        # Assert error message
        assert "parse" in str(exc_info.value).lower()

    def test_preprocess_part_data_does_not_call_parse_price_for_none(self) -> None:
        """Test _preprocess_part_data handles None price correctly."""
        # Arrange
        validator = ScraperDataValidator()
        data = {
            "sku": "CSF-12345",
            "name": "Radiator",
            "category": "Radiators",
            "price": None,
        }

        # Act
        result = validator._preprocess_part_data(data)  # noqa: SLF001

        # Assert - None should remain None
        assert result["price"] is None


class TestCLIDataValidator:
    """Tests for src.cli.validators.DataValidator."""

    def test_validate_json_file_detects_parts_export(self, tmp_path: Path) -> None:
        """Test validate_json_file correctly detects parts export format."""
        # Arrange
        validator = CLIDataValidator()
        parts_data = {
            "metadata": {"export_date": "2025-10-28", "total_parts": 1, "version": "1.0"},
            "parts": [
                {
                    "sku": "CSF-12345",
                    "name": "Radiator",
                    "price": 299.99,
                    "category": "Radiators",
                }
            ],
        }
        test_file = tmp_path / "parts.json"
        test_file.write_text(json.dumps(parts_data))

        # Act
        result = validator.validate_json_file(test_file)

        # Assert
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert result.total_items == 1

    def test_validate_json_file_detects_compatibility_export(self, tmp_path: Path) -> None:
        """Test validate_json_file correctly detects compatibility export format."""
        # Arrange
        validator = CLIDataValidator()
        compat_data = {
            "metadata": {"export_date": "2025-10-28", "total_mappings": 1},
            "compatibility": [
                {
                    "part_sku": "CSF-12345",
                    "vehicles": [{"make": "Audi", "model": "A4", "year": 2020}],
                }
            ],
        }
        test_file = tmp_path / "compatibility.json"
        test_file.write_text(json.dumps(compat_data))

        # Act
        result = validator.validate_json_file(test_file)

        # Assert
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert result.total_items == 1

    def test_validate_json_file_detects_hierarchical_export(self, tmp_path: Path) -> None:
        """Test validate_json_file correctly detects hierarchical export format."""
        # Arrange
        validator = CLIDataValidator()
        hierarchical_data = {
            "metadata": {
                "export_date": "2025-10-28",
                "structure": "year>make>model",
                "total_years": 1,
            },
            "data": {
                "2020": {
                    "Audi": {
                        "A4": [
                            {
                                "sku": "CSF-12345",
                                "name": "Radiator",
                                "category": "Radiators",
                            }
                        ]
                    }
                }
            },
        }
        test_file = tmp_path / "hierarchical.json"
        test_file.write_text(json.dumps(hierarchical_data))

        # Act
        result = validator.validate_json_file(test_file)

        # Assert
        assert isinstance(result, ValidationResult)
        assert result.total_items == 1

    def test_validate_directory_validates_multiple_files(self, tmp_path: Path) -> None:
        """Test validate_directory processes all JSON files in directory."""
        # Arrange
        validator = CLIDataValidator()

        # Create multiple valid files
        parts_data = {
            "metadata": {"export_date": "2025-10-28", "total_parts": 1},
            "parts": [{"sku": "CSF-12345", "name": "Radiator", "category": "Radiators"}],
        }
        (tmp_path / "parts1.json").write_text(json.dumps(parts_data))
        (tmp_path / "parts2.json").write_text(json.dumps(parts_data))

        # Create a non-JSON file that should be ignored
        (tmp_path / "readme.txt").write_text("This is not JSON")

        # Act
        results = validator.validate_directory(tmp_path)

        # Assert
        assert len(results) == 2
        assert "parts1.json" in results
        assert "parts2.json" in results
        assert "readme.txt" not in results

    def test_validate_parts_export_checks_structure(self, tmp_path: Path) -> None:
        """Test _validate_parts_export validates export structure."""
        # Arrange
        validator = CLIDataValidator()
        invalid_data: dict[str, Any] = {
            "parts": []
            # Missing 'metadata' key
        }
        test_file = tmp_path / "invalid.json"
        test_file.write_text(json.dumps(invalid_data))

        # Act
        result = validator.validate_json_file(test_file)

        # Assert
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert any("metadata" in err.message.lower() for err in result.errors)

    def test_validate_compatibility_export_checks_structure(self, tmp_path: Path) -> None:
        """Test _validate_compatibility_export validates export structure."""
        # Arrange
        validator = CLIDataValidator()
        invalid_data: dict[str, Any] = {
            "compatibility": []
            # Missing 'metadata' key
        }
        test_file = tmp_path / "invalid.json"
        test_file.write_text(json.dumps(invalid_data))

        # Act
        result = validator.validate_json_file(test_file)

        # Assert
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert any("metadata" in err.message.lower() for err in result.errors)

    def test_validate_part_data_validates_against_part_model(self, tmp_path: Path) -> None:
        """Test _validate_part_data validates part data against Part model."""
        # Arrange
        validator = CLIDataValidator()
        invalid_parts = {
            "metadata": {"export_date": "2025-10-28", "total_parts": 1},
            "parts": [
                {
                    "sku": "INVALID",  # Wrong SKU format (doesn't start with CSF-)
                    "name": "Radiator",
                    "category": "Radiators",
                }
            ],
        }
        test_file = tmp_path / "invalid_parts.json"
        test_file.write_text(json.dumps(invalid_parts))

        # Act
        result = validator.validate_json_file(test_file)

        # Assert
        assert result.is_valid is False
        assert result.valid_items == 0
        assert len(result.errors) > 0

    def test_validation_result_aggregates_errors_correctly(self, tmp_path: Path) -> None:
        """Test ValidationResult correctly aggregates multiple errors."""
        # Arrange
        validator = CLIDataValidator()
        data_with_errors = {
            "metadata": {"export_date": "2025-10-28", "total_parts": 2},
            "parts": [
                # First part: missing SKU
                {"name": "Radiator 1", "category": "Radiators"},
                # Second part: invalid SKU format
                {"sku": "INVALID", "name": "Radiator 2", "category": "Radiators"},
            ],
        }
        test_file = tmp_path / "errors.json"
        test_file.write_text(json.dumps(data_with_errors))

        # Act
        result = validator.validate_json_file(test_file)

        # Assert
        assert result.is_valid is False
        assert result.total_items == 2
        assert result.valid_items == 0
        assert result.error_count >= 2  # At least 2 errors

    def test_validation_result_aggregates_warnings_correctly(self, tmp_path: Path) -> None:
        """Test ValidationResult correctly aggregates warnings."""
        # Arrange
        validator = CLIDataValidator()
        data_with_warnings = {
            "metadata": {"export_date": "2025-10-28", "total_parts": 1},
            "parts": [
                {
                    "sku": "CSF-12345",
                    "name": "Radiator",
                    "category": "Radiators",
                    # Missing optional fields like description, images, specs
                }
            ],
        }
        test_file = tmp_path / "warnings.json"
        test_file.write_text(json.dumps(data_with_warnings))

        # Act
        result = validator.validate_json_file(test_file)

        # Assert
        assert result.is_valid is True  # Warnings don't invalidate
        assert result.warning_count > 0

    def test_validation_result_error_count_property(self) -> None:
        """Test ValidationResult.error_count property."""
        # Arrange
        errors = [
            ValidationIssue("error", "field1", "Error 1"),
            ValidationIssue("error", "field2", "Error 2"),
        ]
        result = ValidationResult(
            is_valid=False,
            errors=errors,
            warnings=[],
            total_items=1,
            valid_items=0,
        )

        # Act
        error_count = result.error_count

        # Assert
        assert error_count == 2

    def test_validation_result_warning_count_property(self) -> None:
        """Test ValidationResult.warning_count property."""
        # Arrange
        warnings = [
            ValidationIssue("warning", "field1", "Warning 1"),
            ValidationIssue("warning", "field2", "Warning 2"),
            ValidationIssue("warning", "field3", "Warning 3"),
        ]
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=warnings,
            total_items=1,
            valid_items=1,
        )

        # Act
        warning_count = result.warning_count

        # Assert
        assert warning_count == 3

    def test_strict_mode_treats_warnings_as_errors(self, tmp_path: Path) -> None:
        """Test strict mode causes warnings to invalidate results."""
        # Arrange
        validator = CLIDataValidator(strict=True)
        data_with_warnings = {
            "metadata": {"export_date": "2025-10-28", "total_parts": 1},
            "parts": [
                {
                    "sku": "CSF-12345",
                    "name": "Radiator",
                    "category": "Radiators",
                    # Missing optional fields will generate warnings
                }
            ],
        }
        test_file = tmp_path / "warnings.json"
        test_file.write_text(json.dumps(data_with_warnings))

        # Act
        result = validator.validate_json_file(test_file)

        # Assert
        # In strict mode, warnings should cause is_valid to be False
        if result.warning_count > 0:
            assert result.is_valid is False

    def test_validate_json_file_raises_on_missing_file(self) -> None:
        """Test validate_json_file raises FileNotFoundError for missing file."""
        # Arrange
        validator = CLIDataValidator()
        nonexistent_file = Path("/nonexistent/path/file.json")

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            validator.validate_json_file(nonexistent_file)

    def test_validate_json_file_raises_on_invalid_json(self, tmp_path: Path) -> None:
        """Test validate_json_file raises ValueError for invalid JSON."""
        # Arrange
        validator = CLIDataValidator()
        test_file = tmp_path / "invalid.json"
        test_file.write_text("{invalid json content")

        # Act & Assert
        with pytest.raises(ValueError, match="JSON") as exc_info:
            validator.validate_json_file(test_file)

        # Assert error message mentions JSON
        assert "json" in str(exc_info.value).lower()

    def test_validate_json_file_raises_on_unknown_format(self, tmp_path: Path) -> None:
        """Test validate_json_file raises ValueError for unknown format."""
        # Arrange
        validator = CLIDataValidator()
        unknown_format = {"unknown_key": "value"}
        test_file = tmp_path / "unknown.json"
        test_file.write_text(json.dumps(unknown_format))

        # Act & Assert
        with pytest.raises(ValueError, match="format") as exc_info:
            validator.validate_json_file(test_file)

        # Assert error mentions format
        assert "format" in str(exc_info.value).lower()

    def test_validate_directory_raises_on_missing_directory(self) -> None:
        """Test validate_directory raises FileNotFoundError for missing directory."""
        # Arrange
        validator = CLIDataValidator()
        nonexistent_dir = Path("/nonexistent/directory")

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            validator.validate_directory(nonexistent_dir)

    def test_validate_directory_raises_on_file_instead_of_directory(self, tmp_path: Path) -> None:
        """Test validate_directory raises ValueError when given a file."""
        # Arrange
        validator = CLIDataValidator()
        test_file = tmp_path / "file.json"
        test_file.write_text("{}")

        # Act & Assert
        with pytest.raises(ValueError, match="directory") as exc_info:
            validator.validate_directory(test_file)

        # Assert error mentions directory
        assert "directory" in str(exc_info.value).lower()

    def test_metadata_count_mismatch_generates_warning(self, tmp_path: Path) -> None:
        """Test metadata count mismatch generates warning."""
        # Arrange
        validator = CLIDataValidator()
        data_with_mismatch = {
            "metadata": {"export_date": "2025-10-28", "total_parts": 5},  # Claims 5
            "parts": [  # But only has 1
                {"sku": "CSF-12345", "name": "Radiator", "category": "Radiators"}
            ],
        }
        test_file = tmp_path / "mismatch.json"
        test_file.write_text(json.dumps(data_with_mismatch))

        # Act
        result = validator.validate_json_file(test_file)

        # Assert
        assert result.warning_count > 0
        assert any("total_parts" in warning.field for warning in result.warnings)

    def test_hierarchical_validation_counts_all_parts(self, tmp_path: Path) -> None:
        """Test hierarchical validation counts parts across all vehicles."""
        # Arrange
        validator = CLIDataValidator()
        hierarchical_data = {
            "metadata": {
                "export_date": "2025-10-28",
                "structure": "year>make>model",
                "total_years": 2,
            },
            "data": {
                "2020": {
                    "Audi": {
                        "A4": [
                            {"sku": "CSF-12345", "name": "Part 1", "category": "Cat1"},
                            {"sku": "CSF-12346", "name": "Part 2", "category": "Cat2"},
                        ]
                    }
                },
                "2021": {
                    "BMW": {
                        "3 Series": [{"sku": "CSF-12347", "name": "Part 3", "category": "Cat1"}]
                    }
                },
            },
        }
        test_file = tmp_path / "hierarchical.json"
        test_file.write_text(json.dumps(hierarchical_data))

        # Act
        result = validator.validate_json_file(test_file)

        # Assert
        assert result.total_items == 3  # Should count all 3 parts


class TestValidationIssue:
    """Tests for ValidationIssue dataclass."""

    def test_validation_issue_creation(self) -> None:
        """Test ValidationIssue can be created with required fields."""
        # Arrange & Act
        issue = ValidationIssue(
            severity="error",
            field="parts[0].sku",
            message="SKU is required",
        )

        # Assert
        assert issue.severity == "error"
        assert issue.field == "parts[0].sku"
        assert issue.message == "SKU is required"
        assert issue.details is None

    def test_validation_issue_with_details(self) -> None:
        """Test ValidationIssue can include optional details."""
        # Arrange & Act
        issue = ValidationIssue(
            severity="warning",
            field="parts[0].price",
            message="Price is missing",
            details="missing_field",
        )

        # Assert
        assert issue.details == "missing_field"


class TestScraperValidatorBatch:
    """Tests for batch validation in scraper validator."""

    def test_validate_batch_processes_multiple_parts(self) -> None:
        """Test validate_batch processes multiple valid parts."""
        # Arrange
        validator = ScraperDataValidator()
        parts_data = [
            {"sku": "CSF-1", "name": "Part 1", "price": "99.99", "category": "Cat1"},
            {"sku": "CSF-2", "name": "Part 2", "price": "199.99", "category": "Cat2"},
            {"sku": "CSF-3", "name": "Part 3", "price": "299.99", "category": "Cat3"},
        ]

        # Act
        results = validator.validate_batch(parts_data)

        # Assert
        assert len(results) == 3
        assert all(isinstance(part, Part) for part in results)

    def test_validate_batch_continues_on_error(self) -> None:
        """Test validate_batch continues processing after validation errors."""
        # Arrange
        validator = ScraperDataValidator()
        parts_data = [
            {"sku": "CSF-1", "name": "Part 1", "category": "Cat1"},  # Valid
            {"name": "Part 2", "category": "Cat2"},  # Missing SKU - invalid
            {"sku": "CSF-3", "name": "Part 3", "category": "Cat3"},  # Valid
        ]

        # Act
        results = validator.validate_batch(parts_data)

        # Assert
        assert len(results) == 2  # Only valid parts
        assert results[0].sku == "CSF-1"
        assert results[1].sku == "CSF-3"

    def test_validate_batch_returns_empty_for_all_invalid(self) -> None:
        """Test validate_batch returns empty list when all parts are invalid."""
        # Arrange
        validator = ScraperDataValidator()
        invalid_parts = [
            {"name": "Part 1"},  # Missing SKU
            {"sku": "CSF-2"},  # Missing name
            {"sku": "CSF-3", "name": ""},  # Empty name
        ]

        # Act
        results = validator.validate_batch(invalid_parts)

        # Assert
        assert len(results) == 0
