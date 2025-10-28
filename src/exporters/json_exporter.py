"""JSON exporter for parts and compatibility data.

This module exports validated data to JSON files for WordPress import.
Supports hierarchical organization (Year → Make → Model → Parts).
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

from src.models.part import Part
from src.models.vehicle import VehicleCompatibility

logger = structlog.get_logger()


class JSONExporter:
    """Exporter for parts and compatibility data to JSON format.

    Creates clean, well-formatted JSON files suitable for WordPress import.
    Supports both flat and hierarchical organization.
    """

    def __init__(self, output_dir: Path | str = "exports") -> None:
        """Initialize exporter.

        Args:
            output_dir: Directory for JSON exports (default: "exports")
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("json_exporter_initialized", output_dir=str(self.output_dir))

    def export_parts(
        self,
        parts: list[Part],
        filename: str = "parts.json",
        pretty: bool = True,
    ) -> Path:
        """Export parts to JSON file.

        Args:
            parts: List of validated Part instances
            filename: Output filename (default: "parts.json")
            pretty: Whether to pretty-print JSON (default: True)

        Returns:
            Path to created JSON file

        Raises:
            IOError: If export fails

        Example:
            >>> exporter = JSONExporter()
            >>> parts = [part1, part2]
            >>> path = exporter.export_parts(parts)
            >>> path.exists()
            True
        """
        output_path = self.output_dir / filename

        try:
            # Convert Parts to dicts
            parts_data = [self._part_to_dict(part) for part in parts]

            # Create export structure with metadata
            export_data = {
                "metadata": {
                    "export_date": datetime.now(UTC).isoformat(),
                    "total_parts": len(parts),
                    "version": "1.0",
                },
                "parts": parts_data,
            }

            # Write to file
            with output_path.open("w", encoding="utf-8") as f:
                if pretty:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                else:
                    json.dump(export_data, f, ensure_ascii=False)

            logger.info(
                "parts_exported",
                filename=filename,
                count=len(parts),
                path=str(output_path),
            )

        except Exception as e:
            logger.exception("export_failed", filename=filename, error=str(e))
            msg = f"Failed to export parts: {e}"
            raise OSError(msg) from e
        else:
            return output_path

    def export_compatibility(
        self,
        compatibility: list[VehicleCompatibility],
        filename: str = "compatibility.json",
        pretty: bool = True,
    ) -> Path:
        """Export vehicle compatibility data to JSON file.

        Args:
            compatibility: List of VehicleCompatibility instances
            filename: Output filename (default: "compatibility.json")
            pretty: Whether to pretty-print JSON (default: True)

        Returns:
            Path to created JSON file

        Raises:
            IOError: If export fails
        """
        output_path = self.output_dir / filename

        try:
            # Convert to dicts
            compat_data = [self._compatibility_to_dict(comp) for comp in compatibility]

            # Create export structure
            export_data = {
                "metadata": {
                    "export_date": datetime.now(UTC).isoformat(),
                    "total_mappings": len(compatibility),
                    "version": "1.0",
                },
                "compatibility": compat_data,
            }

            # Write to file
            with output_path.open("w", encoding="utf-8") as f:
                if pretty:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                else:
                    json.dump(export_data, f, ensure_ascii=False)

            logger.info(
                "compatibility_exported",
                filename=filename,
                count=len(compatibility),
                path=str(output_path),
            )

        except Exception as e:
            logger.exception("export_failed", filename=filename, error=str(e))
            msg = f"Failed to export compatibility: {e}"
            raise OSError(msg) from e
        else:
            return output_path

    def export_hierarchical(
        self,
        compatibility: list[VehicleCompatibility],
        parts_by_sku: dict[str, Part],
        filename: str = "hierarchical.json",
        pretty: bool = True,
    ) -> Path:
        """Export data in hierarchical structure: Year → Make → Model → Parts.

        This format is optimized for WordPress import and navigation.

        Args:
            compatibility: List of VehicleCompatibility mappings
            parts_by_sku: Dict mapping SKU to Part
            filename: Output filename (default: "hierarchical.json")
            pretty: Whether to pretty-print JSON (default: True)

        Returns:
            Path to created JSON file

        Raises:
            IOError: If export fails

        Example:
            >>> exporter = JSONExporter()
            >>> parts_by_sku = {"CSF-123": part1, "CSF-456": part2}
            >>> path = exporter.export_hierarchical(compatibility, parts_by_sku)
        """
        output_path = self.output_dir / filename

        try:
            # Build hierarchical structure
            hierarchy: dict[int, dict[str, dict[str, list[dict[str, Any]]]]] = {}

            for compat in compatibility:
                part_sku = compat.part_sku
                part = parts_by_sku.get(part_sku)

                if not part:
                    logger.warning("part_not_found_for_compat", sku=part_sku)
                    continue

                part_dict = self._part_to_dict(part)

                # Organize by Year → Make → Model
                for vehicle in compat.vehicles:
                    year = vehicle.year
                    make = vehicle.make
                    model = vehicle.model

                    # Initialize nested structure
                    if year not in hierarchy:
                        hierarchy[year] = {}
                    if make not in hierarchy[year]:
                        hierarchy[year][make] = {}
                    if model not in hierarchy[year][make]:
                        hierarchy[year][make][model] = []

                    # Add part to this vehicle configuration
                    hierarchy[year][make][model].append(part_dict)

            # Create export structure
            export_data = {
                "metadata": {
                    "export_date": datetime.now(UTC).isoformat(),
                    "structure": "year > make > model > parts",
                    "total_years": len(hierarchy),
                    "version": "1.0",
                },
                "data": hierarchy,
            }

            # Write to file
            with output_path.open("w", encoding="utf-8") as f:
                if pretty:
                    json.dump(export_data, f, indent=2, ensure_ascii=False, sort_keys=True)
                else:
                    json.dump(export_data, f, ensure_ascii=False)

            logger.info(
                "hierarchical_exported",
                filename=filename,
                years=len(hierarchy),
                path=str(output_path),
            )

        except Exception as e:
            logger.exception("export_failed", filename=filename, error=str(e))
            msg = f"Failed to export hierarchical data: {e}"
            raise OSError(msg) from e
        else:
            return output_path

    def _part_to_dict(self, part: Part) -> dict[str, Any]:
        """Convert Part to dict for JSON serialization.

        Args:
            part: Part instance

        Returns:
            Dict representation suitable for JSON

        Note:
            Uses Pydantic's model_dump with specific serialization rules.
        """
        data = part.model_dump(mode="json")

        # Convert Decimal to string for better JSON compatibility
        if "price" in data:
            data["price"] = str(data["price"])

        return data

    def _compatibility_to_dict(self, compatibility: VehicleCompatibility) -> dict[str, Any]:
        """Convert VehicleCompatibility to dict for JSON serialization.

        Args:
            compatibility: VehicleCompatibility instance

        Returns:
            Dict representation suitable for JSON
        """
        return compatibility.model_dump(mode="json")

    def validate_export(self, filepath: Path) -> bool:
        """Validate that exported JSON file is valid.

        Args:
            filepath: Path to JSON file

        Returns:
            True if valid JSON, False otherwise

        Example:
            >>> exporter = JSONExporter()
            >>> path = exporter.export_parts([part1, part2])
            >>> exporter.validate_export(path)
            True
        """
        try:
            with filepath.open(encoding="utf-8") as f:
                json.load(f)
            logger.info("export_validated", filepath=str(filepath))

        except (OSError, json.JSONDecodeError) as e:
            logger.exception("export_validation_failed", filepath=str(filepath), error=str(e))
            return False
        else:
            return True

    def get_export_stats(self, filepath: Path) -> dict[str, Any]:
        """Get statistics about an exported JSON file.

        Args:
            filepath: Path to JSON file

        Returns:
            Dict of statistics (size, part count, etc.)

        Example:
            >>> exporter = JSONExporter()
            >>> path = exporter.export_parts([part1, part2])
            >>> stats = exporter.get_export_stats(path)
            >>> stats["total_parts"]
            2
        """
        try:
            with filepath.open(encoding="utf-8") as f:
                data = json.load(f)

            stats = {
                "filepath": str(filepath),
                "file_size_bytes": filepath.stat().st_size,
                "file_size_mb": round(filepath.stat().st_size / (1024 * 1024), 2),
                "export_date": data.get("metadata", {}).get("export_date"),
                "total_parts": data.get("metadata", {}).get("total_parts", 0),
                "version": data.get("metadata", {}).get("version"),
            }

            logger.info("export_stats_generated", **stats)

        except (OSError, json.JSONDecodeError) as e:
            logger.exception("stats_generation_failed", filepath=str(filepath), error=str(e))
            return {"error": str(e)}
        else:
            return stats

    def export_parts_incremental(
        self,
        parts: list[Part],
        filename: str = "parts.json",
        append: bool = False,
        pretty: bool = True,
    ) -> Path:
        """Export parts with support for incremental/append mode.

        This method supports both creating new exports and appending to existing
        ones, enabling memory-efficient large-scale scraping.

        Args:
            parts: List of Part instances to export
            filename: Output filename (default: "parts.json")
            append: If True, append to existing file; if False, create new (default: False)
            pretty: Whether to pretty-print JSON (default: True)

        Returns:
            Path to created/updated JSON file

        Raises:
            IOError: If export fails
            ValueError: If append=True but file doesn't exist or is invalid

        Example:
            >>> exporter = JSONExporter()
            >>> # First batch
            >>> exporter.export_parts_incremental(batch1, "parts.json", append=False)
            >>> # Subsequent batches
            >>> exporter.export_parts_incremental(batch2, "parts.json", append=True)
            >>> exporter.export_parts_incremental(batch3, "parts.json", append=True)
        """
        output_path = self.output_dir / filename

        if append and not output_path.exists():
            msg = f"Cannot append to non-existent file: {output_path}"
            raise ValueError(msg)

        try:
            if append:
                # Load existing data
                with output_path.open(encoding="utf-8") as f:
                    existing_data = json.load(f)

                # Validate existing structure
                if "parts" not in existing_data:
                    msg = f"Invalid export format in {filename}: missing 'parts' key"
                    raise ValueError(msg)

                # Append new parts
                new_parts_data = [self._part_to_dict(part) for part in parts]
                existing_data["parts"].extend(new_parts_data)

                # Update metadata
                existing_data["metadata"]["export_date"] = datetime.now(UTC).isoformat()
                existing_data["metadata"]["total_parts"] = len(existing_data["parts"])

                export_data = existing_data
                logger.info(
                    "appending_parts",
                    filename=filename,
                    new_count=len(parts),
                    total_count=export_data["metadata"]["total_parts"],
                )
            else:
                # Create new export
                parts_data = [self._part_to_dict(part) for part in parts]
                export_data = {
                    "metadata": {
                        "export_date": datetime.now(UTC).isoformat(),
                        "total_parts": len(parts),
                        "version": "1.0",
                    },
                    "parts": parts_data,
                }
                logger.info("creating_new_export", filename=filename, count=len(parts))

            # Write to file
            with output_path.open("w", encoding="utf-8") as f:
                if pretty:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                else:
                    json.dump(export_data, f, ensure_ascii=False)

            logger.info(
                "incremental_export_complete",
                filename=filename,
                total_parts=export_data["metadata"]["total_parts"],
                path=str(output_path),
            )

        except (OSError, json.JSONDecodeError) as e:
            logger.exception("incremental_export_failed", filename=filename, error=str(e))
            msg = f"Failed to export parts incrementally: {e}"
            raise OSError(msg) from e
        else:
            return output_path

    def export_compatibility_incremental(
        self,
        compatibility: list[VehicleCompatibility],
        filename: str = "compatibility.json",
        append: bool = False,
        pretty: bool = True,
    ) -> Path:
        """Export compatibility data with support for incremental/append mode.

        Args:
            compatibility: List of VehicleCompatibility instances
            filename: Output filename (default: "compatibility.json")
            append: If True, append to existing file (default: False)
            pretty: Whether to pretty-print JSON (default: True)

        Returns:
            Path to created/updated JSON file

        Raises:
            IOError: If export fails
            ValueError: If append=True but file doesn't exist or is invalid
        """
        output_path = self.output_dir / filename

        if append and not output_path.exists():
            msg = f"Cannot append to non-existent file: {output_path}"
            raise ValueError(msg)

        try:
            if append:
                # Load existing data
                with output_path.open(encoding="utf-8") as f:
                    existing_data = json.load(f)

                # Validate existing structure
                if "compatibility" not in existing_data:
                    msg = f"Invalid export format in {filename}: missing 'compatibility' key"
                    raise ValueError(msg)

                # Append new compatibility data
                new_compat_data = [self._compatibility_to_dict(comp) for comp in compatibility]
                existing_data["compatibility"].extend(new_compat_data)

                # Update metadata
                existing_data["metadata"]["export_date"] = datetime.now(UTC).isoformat()
                existing_data["metadata"]["total_mappings"] = len(existing_data["compatibility"])

                export_data = existing_data
                logger.info(
                    "appending_compatibility",
                    filename=filename,
                    new_count=len(compatibility),
                    total_count=export_data["metadata"]["total_mappings"],
                )
            else:
                # Create new export
                compat_data = [self._compatibility_to_dict(comp) for comp in compatibility]
                export_data = {
                    "metadata": {
                        "export_date": datetime.now(UTC).isoformat(),
                        "total_mappings": len(compatibility),
                        "version": "1.0",
                    },
                    "compatibility": compat_data,
                }
                logger.info(
                    "creating_new_compatibility_export", filename=filename, count=len(compatibility)
                )

            # Write to file
            with output_path.open("w", encoding="utf-8") as f:
                if pretty:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                else:
                    json.dump(export_data, f, ensure_ascii=False)

            logger.info(
                "incremental_compatibility_export_complete",
                filename=filename,
                total_mappings=export_data["metadata"]["total_mappings"],
                path=str(output_path),
            )

        except (OSError, json.JSONDecodeError) as e:
            logger.exception(
                "incremental_compatibility_export_failed", filename=filename, error=str(e)
            )
            msg = f"Failed to export compatibility incrementally: {e}"
            raise OSError(msg) from e
        else:
            return output_path
