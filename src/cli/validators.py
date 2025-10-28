"""Validation services for JSON exports and data integrity.

This module provides comprehensive validation for exported parts and compatibility data.
Validates against Pydantic models and enforces data quality standards.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog
from pydantic import ValidationError

from src.models.part import Part
from src.models.vehicle import VehicleCompatibility

logger = structlog.get_logger()


@dataclass
class ValidationIssue:
    """Represents a validation issue.

    Attributes:
        severity: Issue severity ('error' or 'warning')
        field: Field/location where issue occurred
        message: Human-readable issue description
        details: Additional context (optional)
    """

    severity: str
    field: str
    message: str
    details: str | None = None


@dataclass
class ValidationResult:
    """Validation result with all findings.

    Attributes:
        is_valid: Whether data passed validation (no errors)
        errors: List of error issues
        warnings: List of warning issues
        total_items: Total number of items validated
        valid_items: Number of items that passed validation
    """

    is_valid: bool
    errors: list[ValidationIssue]
    warnings: list[ValidationIssue]
    total_items: int
    valid_items: int

    @property
    def error_count(self) -> int:
        """Get total error count."""
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        """Get total warning count."""
        return len(self.warnings)


class DataValidator:
    """Validates exported JSON data against Pydantic models.

    Provides comprehensive validation with configurable strictness levels.
    """

    def __init__(self, strict: bool = False) -> None:
        """Initialize validator.

        Args:
            strict: If True, warnings are treated as errors
        """
        self.strict = strict
        logger.info("validator_initialized", strict=strict)

    def validate_json_file(self, filepath: Path) -> ValidationResult:
        """Validate a JSON export file.

        Detects file type (parts, compatibility, hierarchical) and validates accordingly.

        Args:
            filepath: Path to JSON file

        Returns:
            ValidationResult with all findings

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid or unknown
        """
        if not filepath.exists():
            msg = f"File not found: {filepath}"
            raise FileNotFoundError(msg)

        logger.info("validating_file", filepath=str(filepath))

        try:
            with filepath.open(encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            msg = f"Invalid JSON format: {e}"
            raise ValueError(msg) from e

        # Detect and validate based on structure
        if "parts" in data:
            return self._validate_parts_export(data, filepath)
        if "compatibility" in data:
            return self._validate_compatibility_export(data, filepath)
        if "data" in data and isinstance(data["data"], dict):
            return self._validate_hierarchical_export(data, filepath)
        msg = "Unknown export format: missing 'parts', 'compatibility', or 'data' key"
        raise ValueError(msg)

    def validate_directory(self, dirpath: Path) -> dict[str, ValidationResult]:
        """Validate all JSON files in a directory.

        Args:
            dirpath: Directory path

        Returns:
            Dict mapping filename to ValidationResult

        Raises:
            FileNotFoundError: If directory doesn't exist
        """
        if not dirpath.exists():
            msg = f"Directory not found: {dirpath}"
            raise FileNotFoundError(msg)

        if not dirpath.is_dir():
            msg = f"Not a directory: {dirpath}"
            raise ValueError(msg)

        results: dict[str, ValidationResult] = {}

        for json_file in dirpath.glob("*.json"):
            logger.info("validating_file_in_directory", file=json_file.name)
            try:
                results[json_file.name] = self.validate_json_file(json_file)
            except ValueError as e:
                logger.warning("file_validation_failed", file=json_file.name, error=str(e))
                # Create error result
                results[json_file.name] = ValidationResult(
                    is_valid=False,
                    errors=[
                        ValidationIssue(
                            severity="error",
                            field="file",
                            message=str(e),
                        )
                    ],
                    warnings=[],
                    total_items=0,
                    valid_items=0,
                )

        return results

    def _validate_parts_export(self, data: dict[str, Any], filepath: Path) -> ValidationResult:
        """Validate parts export format.

        Args:
            data: Parsed JSON data
            filepath: File path for logging

        Returns:
            ValidationResult
        """
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []

        # Validate structure
        structure_errors = self._validate_export_structure(data, ["metadata", "parts"])
        errors.extend(structure_errors)

        if errors:
            # Can't continue without valid structure
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                total_items=0,
                valid_items=0,
            )

        # Validate metadata
        metadata_issues = self._validate_metadata(data["metadata"], ["export_date", "total_parts"])
        errors.extend(metadata_issues["errors"])
        warnings.extend(metadata_issues["warnings"])

        # Validate parts
        parts_data = data["parts"]
        if not isinstance(parts_data, list):
            errors.append(
                ValidationIssue(
                    severity="error",
                    field="parts",
                    message="'parts' must be a list",
                )
            )
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                total_items=0,
                valid_items=0,
            )

        total_items = len(parts_data)
        valid_items = 0

        for idx, part_data in enumerate(parts_data):
            part_issues = self._validate_part_data(part_data, idx)
            errors.extend(part_issues["errors"])
            warnings.extend(part_issues["warnings"])

            if not part_issues["errors"]:
                valid_items += 1

        # Check metadata consistency
        declared_count = data["metadata"].get("total_parts", 0)
        if declared_count != total_items:
            warnings.append(
                ValidationIssue(
                    severity="warning",
                    field="metadata.total_parts",
                    message=f"Metadata declares {declared_count} parts but found {total_items}",
                )
            )

        is_valid = len(errors) == 0 and (not self.strict or len(warnings) == 0)

        logger.info(
            "parts_validation_complete",
            filepath=str(filepath),
            total=total_items,
            valid=valid_items,
            errors=len(errors),
            warnings=len(warnings),
        )

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            total_items=total_items,
            valid_items=valid_items,
        )

    def _validate_compatibility_export(
        self, data: dict[str, Any], filepath: Path
    ) -> ValidationResult:
        """Validate compatibility export format.

        Args:
            data: Parsed JSON data
            filepath: File path for logging

        Returns:
            ValidationResult
        """
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []

        # Validate structure
        structure_errors = self._validate_export_structure(data, ["metadata", "compatibility"])
        errors.extend(structure_errors)

        if errors:
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                total_items=0,
                valid_items=0,
            )

        # Validate metadata
        metadata_issues = self._validate_metadata(
            data["metadata"], ["export_date", "total_mappings"]
        )
        errors.extend(metadata_issues["errors"])
        warnings.extend(metadata_issues["warnings"])

        # Validate compatibility data
        compat_data = data["compatibility"]
        if not isinstance(compat_data, list):
            errors.append(
                ValidationIssue(
                    severity="error",
                    field="compatibility",
                    message="'compatibility' must be a list",
                )
            )
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                total_items=0,
                valid_items=0,
            )

        total_items = len(compat_data)
        valid_items = 0

        for idx, compat in enumerate(compat_data):
            compat_issues = self._validate_compatibility_data(compat, idx)
            errors.extend(compat_issues["errors"])
            warnings.extend(compat_issues["warnings"])

            if not compat_issues["errors"]:
                valid_items += 1

        # Check metadata consistency
        declared_count = data["metadata"].get("total_mappings", 0)
        if declared_count != total_items:
            warnings.append(
                ValidationIssue(
                    severity="warning",
                    field="metadata.total_mappings",
                    message=f"Metadata declares {declared_count} mappings but found {total_items}",
                )
            )

        is_valid = len(errors) == 0 and (not self.strict or len(warnings) == 0)

        logger.info(
            "compatibility_validation_complete",
            filepath=str(filepath),
            total=total_items,
            valid=valid_items,
            errors=len(errors),
            warnings=len(warnings),
        )

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            total_items=total_items,
            valid_items=valid_items,
        )

    def _validate_hierarchical_export(
        self, data: dict[str, Any], filepath: Path
    ) -> ValidationResult:
        """Validate hierarchical export format.

        Args:
            data: Parsed JSON data
            filepath: File path for logging

        Returns:
            ValidationResult
        """
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []

        # Validate structure
        structure_errors = self._validate_export_structure(data, ["metadata", "data"])
        errors.extend(structure_errors)

        if errors:
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                total_items=0,
                valid_items=0,
            )

        # Validate metadata
        metadata_issues = self._validate_metadata(
            data["metadata"], ["export_date", "structure", "total_years"]
        )
        errors.extend(metadata_issues["errors"])
        warnings.extend(metadata_issues["warnings"])

        # Validate hierarchical data
        hierarchy = data["data"]
        if not isinstance(hierarchy, dict):
            errors.append(
                ValidationIssue(
                    severity="error",
                    field="data",
                    message="'data' must be a dict (hierarchical structure)",
                )
            )
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                total_items=0,
                valid_items=0,
            )

        total_items = 0
        valid_items = 0

        # Traverse hierarchy: year -> make -> model -> parts
        for year, makes in hierarchy.items():
            # Validate year is numeric
            if not str(year).isdigit():
                warnings.append(
                    ValidationIssue(
                        severity="warning",
                        field=f"data.{year}",
                        message=f"Year '{year}' is not numeric",
                    )
                )

            if not isinstance(makes, dict):
                errors.append(
                    ValidationIssue(
                        severity="error",
                        field=f"data.{year}",
                        message=f"Make data for year {year} must be a dict",
                    )
                )
                continue

            for make, models in makes.items():
                if not isinstance(models, dict):
                    errors.append(
                        ValidationIssue(
                            severity="error",
                            field=f"data.{year}.{make}",
                            message=f"Model data for {year} {make} must be a dict",
                        )
                    )
                    continue

                for model, parts in models.items():
                    if not isinstance(parts, list):
                        errors.append(
                            ValidationIssue(
                                severity="error",
                                field=f"data.{year}.{make}.{model}",
                                message=f"Parts data for {year} {make} {model} must be a list",
                            )
                        )
                        continue

                    # Validate each part in this vehicle configuration
                    for idx, part_data in enumerate(parts):
                        total_items += 1
                        location = f"{year}.{make}.{model}[{idx}]"
                        part_issues = self._validate_part_data(part_data, location)
                        errors.extend(part_issues["errors"])
                        warnings.extend(part_issues["warnings"])

                        if not part_issues["errors"]:
                            valid_items += 1

        # Check year count consistency
        declared_years = data["metadata"].get("total_years", 0)
        actual_years = len(hierarchy)
        if declared_years != actual_years:
            warnings.append(
                ValidationIssue(
                    severity="warning",
                    field="metadata.total_years",
                    message=f"Metadata declares {declared_years} years but found {actual_years}",
                )
            )

        is_valid = len(errors) == 0 and (not self.strict or len(warnings) == 0)

        logger.info(
            "hierarchical_validation_complete",
            filepath=str(filepath),
            total_parts=total_items,
            valid_parts=valid_items,
            years=len(hierarchy),
            errors=len(errors),
            warnings=len(warnings),
        )

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            total_items=total_items,
            valid_items=valid_items,
        )

    def _validate_export_structure(
        self, data: dict[str, Any], required_keys: list[str]
    ) -> list[ValidationIssue]:
        """Validate export file has required top-level keys.

        Args:
            data: Parsed JSON data
            required_keys: List of required keys

        Returns:
            List of ValidationIssue objects
        """
        errors: list[ValidationIssue] = []

        for key in required_keys:
            if key not in data:
                errors.append(
                    ValidationIssue(
                        severity="error",
                        field="structure",
                        message=f"Missing required key: '{key}'",
                    )
                )

        return errors

    def _validate_metadata(
        self,
        metadata: Any,  # noqa: ANN401
        required_fields: list[str],
    ) -> dict[str, list[ValidationIssue]]:
        """Validate export metadata.

        Args:
            metadata: Metadata (should be dict, but needs validation)
            required_fields: Required metadata fields

        Returns:
            Dict with 'errors' and 'warnings' lists
        """
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []

        if not isinstance(metadata, dict):
            errors.append(
                ValidationIssue(
                    severity="error",
                    field="metadata",
                    message="Metadata must be a dict",
                )
            )
            return {"errors": errors, "warnings": warnings}

        # Check required fields
        for field in required_fields:
            if field not in metadata:
                errors.append(
                    ValidationIssue(
                        severity="error",
                        field=f"metadata.{field}",
                        message=f"Missing required metadata field: '{field}'",
                    )
                )

        # Validate version if present
        if "version" in metadata:
            version = metadata["version"]
            if not isinstance(version, str):
                warnings.append(
                    ValidationIssue(
                        severity="warning",
                        field="metadata.version",
                        message="Version should be a string",
                    )
                )

        return {"errors": errors, "warnings": warnings}

    def _validate_part_data(
        self, part_data: dict[str, Any], identifier: int | str
    ) -> dict[str, list[ValidationIssue]]:
        """Validate part data against Pydantic model.

        Args:
            part_data: Part data dict
            identifier: Part index or location identifier

        Returns:
            Dict with 'errors' and 'warnings' lists
        """
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []

        try:
            # Attempt to create Part instance
            part = Part(**part_data)

            # Additional validation checks
            if not part.images:
                warnings.append(
                    ValidationIssue(
                        severity="warning",
                        field=f"parts[{identifier}].images",
                        message=f"Part {part.sku} has no images",
                    )
                )

            if not part.description:
                warnings.append(
                    ValidationIssue(
                        severity="warning",
                        field=f"parts[{identifier}].description",
                        message=f"Part {part.sku} has no description",
                    )
                )

            if not part.specifications:
                warnings.append(
                    ValidationIssue(
                        severity="warning",
                        field=f"parts[{identifier}].specifications",
                        message=f"Part {part.sku} has no specifications",
                    )
                )

        except ValidationError as e:
            # Parse Pydantic validation errors
            for error in e.errors():
                field_path = ".".join(str(loc) for loc in error["loc"])
                errors.append(
                    ValidationIssue(
                        severity="error",
                        field=f"parts[{identifier}].{field_path}",
                        message=error["msg"],
                        details=error.get("type"),
                    )
                )
        except Exception as e:  # noqa: BLE001
            errors.append(
                ValidationIssue(
                    severity="error",
                    field=f"parts[{identifier}]",
                    message=f"Unexpected validation error: {e}",
                )
            )

        return {"errors": errors, "warnings": warnings}

    def _validate_compatibility_data(
        self, compat_data: dict[str, Any], index: int
    ) -> dict[str, list[ValidationIssue]]:
        """Validate compatibility data against Pydantic model.

        Args:
            compat_data: Compatibility data dict
            index: Compatibility entry index

        Returns:
            Dict with 'errors' and 'warnings' lists
        """
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []

        try:
            # Attempt to create VehicleCompatibility instance
            compat = VehicleCompatibility(**compat_data)

            # Additional validation checks
            if not compat.vehicles:
                errors.append(
                    ValidationIssue(
                        severity="error",
                        field=f"compatibility[{index}].vehicles",
                        message=f"Compatibility for {compat.part_sku} has no vehicles",
                    )
                )

        except ValidationError as e:
            # Parse Pydantic validation errors
            for error in e.errors():
                field_path = ".".join(str(loc) for loc in error["loc"])
                errors.append(
                    ValidationIssue(
                        severity="error",
                        field=f"compatibility[{index}].{field_path}",
                        message=error["msg"],
                        details=error.get("type"),
                    )
                )
        except Exception as e:  # noqa: BLE001
            errors.append(
                ValidationIssue(
                    severity="error",
                    field=f"compatibility[{index}]",
                    message=f"Unexpected validation error: {e}",
                )
            )

        return {"errors": errors, "warnings": warnings}
