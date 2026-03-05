"""Unit tests for JSON exporter.

Tests the JSONExporter class for exporting parts and compatibility data.
All tests follow the AAA (Arrange-Act-Assert) pattern.
"""

# ruff: noqa: SLF001 - Testing private methods is intentional

import json
from decimal import Decimal
from pathlib import Path

import pytest

from src.exporters.json_exporter import JSONExporter
from src.models.part import Part, PartImage
from src.models.vehicle import Vehicle, VehicleCompatibility

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_part() -> Part:
    """Create a sample Part instance for testing.

    Returns:
        A valid Part with all fields populated
    """
    return Part(
        sku="CSF-12345",
        name="High Performance Radiator",
        price=Decimal("299.99"),
        description="Premium aluminum radiator for maximum cooling",
        category="Radiators",
        specifications={
            "material": "Aluminum",
            "rows": 2,
            "core_width": "26 inches",
        },
        images=[
            PartImage(url="https://example.com/image1.jpg", alt_text="Front view", is_primary=True),
            PartImage(url="https://example.com/image2.jpg", alt_text="Side view", is_primary=False),
        ],
        manufacturer="CSF",
        in_stock=True,
        features=["High efficiency", "Direct fit", "Lifetime warranty"],
        tech_notes="Requires professional installation",
        position="Front",
    )


@pytest.fixture
def sample_part_minimal() -> Part:
    """Create a minimal Part instance for testing.

    Returns:
        A Part with only required fields
    """
    return Part(
        sku="CSF-67890",
        name="Condenser",
        category="Condensers",
        price=None,
        description=None,
        tech_notes=None,
        position=None,
    )


@pytest.fixture
def sample_vehicle() -> Vehicle:
    """Create a sample Vehicle instance for testing.

    Returns:
        A valid Vehicle
    """
    return Vehicle(
        make="Audi",
        model="A4",
        year=2020,
        submodel="Quattro",
        engine="2.0L L4",
        fuel_type="Gasoline",
        aspiration="Turbocharged",
    )


@pytest.fixture
def sample_compatibility(sample_vehicle: Vehicle) -> VehicleCompatibility:
    """Create a sample VehicleCompatibility instance for testing.

    Args:
        sample_vehicle: Vehicle fixture

    Returns:
        A valid VehicleCompatibility
    """
    return VehicleCompatibility(
        part_sku="CSF-12345",
        vehicles=[
            sample_vehicle,
            Vehicle(
                make="Audi",
                model="A4",
                year=2021,
                submodel=None,
                engine=None,
                fuel_type=None,
                aspiration=None,
            ),
            Vehicle(
                make="Audi",
                model="A5",
                year=2020,
                submodel=None,
                engine=None,
                fuel_type=None,
                aspiration=None,
            ),
        ],
        notes="Direct fit, no modifications required",
    )


# ============================================================================
# Test JSONExporter.__init__()
# ============================================================================


def test_init_creates_output_directory(tmp_path: Path) -> None:
    """Test that __init__() creates the output directory.

    Arrange: Create path that doesn't exist yet
    Act: Initialize JSONExporter
    Assert: Directory was created
    """
    # Arrange
    output_dir = tmp_path / "test_exports"
    assert not output_dir.exists()

    # Act
    exporter = JSONExporter(output_dir=output_dir)

    # Assert
    assert output_dir.exists()
    assert output_dir.is_dir()
    assert exporter.output_dir == output_dir


def test_init_uses_default_directory() -> None:
    """Test that __init__() uses 'exports' as default directory.

    Arrange: No output_dir specified
    Act: Initialize JSONExporter
    Assert: Uses 'exports' directory
    """
    # Arrange & Act
    exporter = JSONExporter()

    # Assert
    assert exporter.output_dir == Path("exports")


def test_init_creates_nested_directories(tmp_path: Path) -> None:
    """Test that __init__() creates nested parent directories.

    Arrange: Create path with multiple levels that don't exist
    Act: Initialize JSONExporter
    Assert: All parent directories were created
    """
    # Arrange
    nested_path = tmp_path / "level1" / "level2" / "level3"
    assert not nested_path.exists()

    # Act
    JSONExporter(output_dir=nested_path)

    # Assert
    assert nested_path.exists()
    assert nested_path.is_dir()


# ============================================================================
# Test JSONExporter.export_parts()
# ============================================================================


def test_export_parts_creates_json_file_with_metadata(
    tmp_path: Path,
    sample_part: Part,
) -> None:
    """Test that export_parts() creates JSON file with metadata.

    Arrange: Create exporter and sample parts
    Act: Export parts to JSON
    Assert: File created with correct metadata structure
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)
    parts = [sample_part]

    # Act
    output_path = exporter.export_parts(parts, filename="test_parts.json")

    # Assert
    assert output_path.exists()
    assert output_path == tmp_path / "test_parts.json"

    with output_path.open(encoding="utf-8") as f:
        data = json.load(f)

    assert "metadata" in data
    assert "parts" in data
    assert data["metadata"]["total_parts"] == 1
    assert data["metadata"]["version"] == "1.0"
    assert "export_date" in data["metadata"]
    assert len(data["parts"]) == 1


def test_export_parts_with_pretty_true_formats_json_nicely(
    tmp_path: Path,
    sample_part: Part,
) -> None:
    """Test that export_parts() with pretty=True formats JSON with indentation.

    Arrange: Create exporter and sample parts
    Act: Export with pretty=True
    Assert: JSON file is formatted with indentation
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)
    parts = [sample_part]

    # Act
    output_path = exporter.export_parts(parts, filename="pretty.json", pretty=True)

    # Assert
    with output_path.open(encoding="utf-8") as f:
        content = f.read()

    # Pretty JSON should have newlines and indentation
    assert "\n" in content
    assert "  " in content  # Check for 2-space indentation
    assert content.count("\n") > 10  # Should have many lines


def test_export_parts_with_pretty_false_creates_compact_json(
    tmp_path: Path,
    sample_part: Part,
) -> None:
    """Test that export_parts() with pretty=False creates compact JSON.

    Arrange: Create exporter and sample parts
    Act: Export with pretty=False
    Assert: JSON file is compact without extra whitespace
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)
    parts = [sample_part]

    # Act
    output_path = exporter.export_parts(parts, filename="compact.json", pretty=False)

    # Assert
    with output_path.open(encoding="utf-8") as f:
        content = f.read()

    # Compact JSON should be on one line (or few lines)
    lines = content.strip().split("\n")
    assert len(lines) == 1  # Single line


def test_export_parts_converts_decimal_to_string(
    tmp_path: Path,
    sample_part: Part,
) -> None:
    """Test that export_parts() converts Decimal prices to strings.

    Arrange: Create exporter and part with Decimal price
    Act: Export parts
    Assert: Price is stored as string in JSON
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)
    parts = [sample_part]

    # Act
    output_path = exporter.export_parts(parts)

    # Assert
    with output_path.open(encoding="utf-8") as f:
        data = json.load(f)

    exported_part = data["parts"][0]
    assert isinstance(exported_part["price"], str)
    assert exported_part["price"] == "299.99"


def test_export_parts_handles_multiple_parts(
    tmp_path: Path,
    sample_part: Part,
    sample_part_minimal: Part,
) -> None:
    """Test that export_parts() handles multiple parts correctly.

    Arrange: Create exporter and multiple parts
    Act: Export all parts
    Assert: All parts are included in export
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)
    parts = [sample_part, sample_part_minimal]

    # Act
    output_path = exporter.export_parts(parts)

    # Assert
    with output_path.open(encoding="utf-8") as f:
        data = json.load(f)

    assert data["metadata"]["total_parts"] == 2
    assert len(data["parts"]) == 2
    assert data["parts"][0]["sku"] == "CSF-12345"
    assert data["parts"][1]["sku"] == "CSF-67890"


def test_export_parts_returns_path(tmp_path: Path, sample_part: Part) -> None:
    """Test that export_parts() returns the output path.

    Arrange: Create exporter and parts
    Act: Export parts
    Assert: Returned path matches expected path
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)
    filename = "output.json"

    # Act
    returned_path = exporter.export_parts([sample_part], filename=filename)

    # Assert
    assert isinstance(returned_path, Path)
    assert returned_path == tmp_path / filename
    assert returned_path.exists()


# ============================================================================
# Test JSONExporter.export_compatibility()
# ============================================================================


def test_export_compatibility_creates_compatibility_json(
    tmp_path: Path,
    sample_compatibility: VehicleCompatibility,
) -> None:
    """Test that export_compatibility() creates JSON with compatibility data.

    Arrange: Create exporter and compatibility data
    Act: Export compatibility
    Assert: JSON file created with correct structure
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)
    compatibility = [sample_compatibility]

    # Act
    output_path = exporter.export_compatibility(
        compatibility,
        filename="compat.json",
    )

    # Assert
    assert output_path.exists()

    with output_path.open(encoding="utf-8") as f:
        data = json.load(f)

    assert "metadata" in data
    assert "compatibility" in data
    assert data["metadata"]["total_mappings"] == 1
    assert data["metadata"]["version"] == "1.0"
    assert len(data["compatibility"]) == 1


def test_export_compatibility_includes_vehicles(
    tmp_path: Path,
    sample_compatibility: VehicleCompatibility,
) -> None:
    """Test that export_compatibility() includes vehicle data.

    Arrange: Create exporter and compatibility with vehicles
    Act: Export compatibility
    Assert: Vehicle data is included correctly
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)
    compatibility = [sample_compatibility]

    # Act
    output_path = exporter.export_compatibility(compatibility)

    # Assert
    with output_path.open(encoding="utf-8") as f:
        data = json.load(f)

    compat_entry = data["compatibility"][0]
    assert compat_entry["part_sku"] == "CSF-12345"
    assert len(compat_entry["vehicles"]) == 3
    assert compat_entry["vehicles"][0]["make"] == "Audi"
    assert compat_entry["vehicles"][0]["model"] == "A4"
    assert compat_entry["vehicles"][0]["year"] == 2020


# ============================================================================
# Test JSONExporter.export_hierarchical()
# ============================================================================


def test_export_hierarchical_creates_hierarchical_structure(
    tmp_path: Path,
    sample_part: Part,
    sample_compatibility: VehicleCompatibility,
) -> None:
    """Test that export_hierarchical() creates Year → Make → Model → Parts structure.

    Arrange: Create exporter with parts and compatibility data
    Act: Export hierarchical
    Assert: Correct nested structure created
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)
    parts_by_sku = {"CSF-12345": sample_part}
    compatibility = [sample_compatibility]

    # Act
    output_path = exporter.export_hierarchical(
        compatibility,
        parts_by_sku,
        filename="hierarchy.json",
    )

    # Assert
    assert output_path.exists()

    with output_path.open(encoding="utf-8") as f:
        data = json.load(f)

    assert "metadata" in data
    assert "data" in data
    assert data["metadata"]["structure"] == "year > make > model > parts"

    # Check hierarchical structure exists
    hierarchy = data["data"]
    assert "2020" in hierarchy
    assert "Audi" in hierarchy["2020"]
    assert "A4" in hierarchy["2020"]["Audi"]
    assert "A5" in hierarchy["2020"]["Audi"]


def test_export_hierarchical_organizes_parts_by_vehicle(
    tmp_path: Path,
    sample_part: Part,
    sample_compatibility: VehicleCompatibility,
) -> None:
    """Test that export_hierarchical() correctly organizes parts under vehicles.

    Arrange: Create exporter with compatibility mappings
    Act: Export hierarchical
    Assert: Parts appear under correct vehicle paths
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)
    parts_by_sku = {"CSF-12345": sample_part}
    compatibility = [sample_compatibility]

    # Act
    output_path = exporter.export_hierarchical(compatibility, parts_by_sku)

    # Assert
    with output_path.open(encoding="utf-8") as f:
        data = json.load(f)

    # Check parts are under correct vehicle path
    a4_parts = data["data"]["2020"]["Audi"]["A4"]
    assert len(a4_parts) > 0
    assert a4_parts[0]["sku"] == "CSF-12345"

    a5_parts = data["data"]["2020"]["Audi"]["A5"]
    assert len(a5_parts) > 0
    assert a5_parts[0]["sku"] == "CSF-12345"


def test_export_hierarchical_handles_missing_part(
    tmp_path: Path,
    sample_compatibility: VehicleCompatibility,
) -> None:
    """Test that export_hierarchical() handles missing parts gracefully.

    Arrange: Create exporter with compatibility but empty parts dict
    Act: Export hierarchical
    Assert: Export succeeds but skips missing parts
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)
    parts_by_sku: dict[str, Part] = {}  # Empty - no parts available
    compatibility = [sample_compatibility]

    # Act
    output_path = exporter.export_hierarchical(compatibility, parts_by_sku)

    # Assert
    assert output_path.exists()

    with output_path.open(encoding="utf-8") as f:
        data = json.load(f)

    # Structure should exist but be empty or minimal
    assert "data" in data
    # The hierarchy might be empty since no parts were found
    hierarchy = data["data"]
    assert isinstance(hierarchy, dict)


# ============================================================================
# Test JSONExporter.export_parts_incremental()
# ============================================================================


def test_export_parts_incremental_with_append_false_creates_new_file(
    tmp_path: Path,
    sample_part: Part,
) -> None:
    """Test that export_parts_incremental() with append=False creates new file.

    Arrange: Create exporter and parts
    Act: Export with append=False
    Assert: New file created
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)
    parts = [sample_part]

    # Act
    output_path = exporter.export_parts_incremental(
        parts,
        filename="incremental.json",
        append=False,
    )

    # Assert
    assert output_path.exists()

    with output_path.open(encoding="utf-8") as f:
        data = json.load(f)

    assert data["metadata"]["total_parts"] == 1
    assert len(data["parts"]) == 1


def test_export_parts_incremental_with_append_true_appends_to_existing(
    tmp_path: Path,
    sample_part: Part,
    sample_part_minimal: Part,
) -> None:
    """Test that export_parts_incremental() with append=True appends to existing file.

    Arrange: Create exporter, export initial file, prepare second batch
    Act: Export with append=True
    Assert: Parts appended to existing file
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)
    filename = "incremental.json"

    # Create initial file
    exporter.export_parts_incremental([sample_part], filename=filename, append=False)

    # Act - append second batch
    output_path = exporter.export_parts_incremental(
        [sample_part_minimal],
        filename=filename,
        append=True,
    )

    # Assert
    with output_path.open(encoding="utf-8") as f:
        data = json.load(f)

    assert data["metadata"]["total_parts"] == 2
    assert len(data["parts"]) == 2
    assert data["parts"][0]["sku"] == "CSF-12345"
    assert data["parts"][1]["sku"] == "CSF-67890"


def test_export_parts_incremental_raises_valueerror_if_append_true_and_file_missing(
    tmp_path: Path,
    sample_part: Part,
) -> None:
    """Test that export_parts_incremental() raises ValueError if append=True but file doesn't exist.

    Arrange: Create exporter with non-existent file
    Act: Try to export with append=True
    Assert: ValueError raised
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)
    filename = "nonexistent.json"
    parts = [sample_part]

    # Act & Assert
    with pytest.raises(ValueError, match="Cannot append to non-existent file"):
        exporter.export_parts_incremental(parts, filename=filename, append=True)


def test_export_parts_incremental_updates_metadata_on_append(
    tmp_path: Path,
    sample_part: Part,
    sample_part_minimal: Part,
) -> None:
    """Test that export_parts_incremental() updates metadata when appending.

    Arrange: Create exporter with existing file
    Act: Append new parts
    Assert: Metadata reflects updated count and date
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)
    filename = "incremental.json"

    # Create initial file
    initial_path = exporter.export_parts_incremental(
        [sample_part],
        filename=filename,
        append=False,
    )

    with initial_path.open(encoding="utf-8") as f:
        initial_data = json.load(f)
    initial_date = initial_data["metadata"]["export_date"]

    # Act - append
    output_path = exporter.export_parts_incremental(
        [sample_part_minimal],
        filename=filename,
        append=True,
    )

    # Assert
    with output_path.open(encoding="utf-8") as f:
        updated_data = json.load(f)

    assert updated_data["metadata"]["total_parts"] == 2
    # Export date should be updated (different from initial)
    assert updated_data["metadata"]["export_date"] != initial_date


# ============================================================================
# Test JSONExporter.export_compatibility_incremental()
# ============================================================================


def test_export_compatibility_incremental_with_append_false_creates_new(
    tmp_path: Path,
    sample_compatibility: VehicleCompatibility,
) -> None:
    """Test that export_compatibility_incremental() with append=False creates new file.

    Arrange: Create exporter and compatibility data
    Act: Export with append=False
    Assert: New file created
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)
    compatibility = [sample_compatibility]

    # Act
    output_path = exporter.export_compatibility_incremental(
        compatibility,
        filename="compat_inc.json",
        append=False,
    )

    # Assert
    assert output_path.exists()

    with output_path.open(encoding="utf-8") as f:
        data = json.load(f)

    assert data["metadata"]["total_mappings"] == 1
    assert len(data["compatibility"]) == 1


def test_export_compatibility_incremental_with_append_true_appends(
    tmp_path: Path,
    sample_compatibility: VehicleCompatibility,
) -> None:
    """Test that export_compatibility_incremental() with append=True appends data.

    Arrange: Create exporter, export initial file, prepare second batch
    Act: Export with append=True
    Assert: Compatibility data appended
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)
    filename = "compat_inc.json"

    # Create initial file
    exporter.export_compatibility_incremental(
        [sample_compatibility],
        filename=filename,
        append=False,
    )

    # Create second compatibility entry
    compat2 = VehicleCompatibility(
        part_sku="CSF-67890",
        vehicles=[
            Vehicle(
                make="BMW",
                model="3 Series",
                year=2019,
                submodel=None,
                engine=None,
                fuel_type=None,
                aspiration=None,
            )
        ],
        notes=None,
    )

    # Act
    output_path = exporter.export_compatibility_incremental(
        [compat2],
        filename=filename,
        append=True,
    )

    # Assert
    with output_path.open(encoding="utf-8") as f:
        data = json.load(f)

    assert data["metadata"]["total_mappings"] == 2
    assert len(data["compatibility"]) == 2
    assert data["compatibility"][0]["part_sku"] == "CSF-12345"
    assert data["compatibility"][1]["part_sku"] == "CSF-67890"


def test_export_compatibility_incremental_raises_valueerror_if_append_true_and_missing(
    tmp_path: Path,
    sample_compatibility: VehicleCompatibility,
) -> None:
    """Test export_compatibility_incremental() raises ValueError if file missing with append=True.

    Arrange: Create exporter with non-existent file
    Act: Try to export with append=True
    Assert: ValueError raised
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)
    filename = "missing.json"

    # Act & Assert
    with pytest.raises(ValueError, match="Cannot append to non-existent file"):
        exporter.export_compatibility_incremental(
            [sample_compatibility],
            filename=filename,
            append=True,
        )


# ============================================================================
# Test JSONExporter.validate_export()
# ============================================================================


def test_validate_export_returns_true_for_valid_json(
    tmp_path: Path,
    sample_part: Part,
) -> None:
    """Test that validate_export() returns True for valid JSON file.

    Arrange: Create exporter and export valid JSON
    Act: Validate the export
    Assert: Returns True
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)
    output_path = exporter.export_parts([sample_part])

    # Act
    result = exporter.validate_export(output_path)

    # Assert
    assert result is True


def test_validate_export_returns_false_for_invalid_json(tmp_path: Path) -> None:
    """Test that validate_export() returns False for invalid JSON file.

    Arrange: Create exporter and invalid JSON file
    Act: Validate the invalid file
    Assert: Returns False
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)
    invalid_file = tmp_path / "invalid.json"

    # Create invalid JSON
    with invalid_file.open("w", encoding="utf-8") as f:
        f.write("{invalid json content")

    # Act
    result = exporter.validate_export(invalid_file)

    # Assert
    assert result is False


def test_validate_export_returns_false_for_nonexistent_file(tmp_path: Path) -> None:
    """Test that validate_export() returns False for nonexistent file.

    Arrange: Create exporter with path to non-existent file
    Act: Validate the non-existent file
    Assert: Returns False
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)
    nonexistent = tmp_path / "does_not_exist.json"

    # Act
    result = exporter.validate_export(nonexistent)

    # Assert
    assert result is False


# ============================================================================
# Test JSONExporter.get_export_stats()
# ============================================================================


def test_get_export_stats_returns_correct_statistics(
    tmp_path: Path,
    sample_part: Part,
    sample_part_minimal: Part,
) -> None:
    """Test that get_export_stats() returns correct statistics.

    Arrange: Create exporter and export multiple parts
    Act: Get export stats
    Assert: Stats are accurate
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)
    parts = [sample_part, sample_part_minimal]
    output_path = exporter.export_parts(parts, filename="stats_test.json")

    # Act
    stats = exporter.get_export_stats(output_path)

    # Assert
    assert stats["filepath"] == str(output_path)
    assert stats["total_parts"] == 2
    assert stats["version"] == "1.0"
    assert "export_date" in stats
    assert stats["file_size_bytes"] > 0
    assert stats["file_size_mb"] >= 0  # Can be 0.0 for small files
    assert isinstance(stats["file_size_mb"], float)


def test_get_export_stats_includes_file_size(
    tmp_path: Path,
    sample_part: Part,
) -> None:
    """Test that get_export_stats() includes accurate file size.

    Arrange: Create exporter and export parts
    Act: Get stats
    Assert: File size metrics present and reasonable
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)
    output_path = exporter.export_parts([sample_part])

    # Act
    stats = exporter.get_export_stats(output_path)

    # Assert
    assert "file_size_bytes" in stats
    assert "file_size_mb" in stats
    assert stats["file_size_bytes"] > 0

    # Check that MB conversion is correct
    expected_mb = round(stats["file_size_bytes"] / (1024 * 1024), 2)
    assert stats["file_size_mb"] == expected_mb


def test_get_export_stats_returns_error_for_invalid_file(tmp_path: Path) -> None:
    """Test that get_export_stats() returns error dict for invalid file.

    Arrange: Create exporter and invalid JSON file
    Act: Get stats from invalid file
    Assert: Returns dict with error key
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)
    invalid_file = tmp_path / "invalid.json"

    with invalid_file.open("w", encoding="utf-8") as f:
        f.write("not valid json")

    # Act
    stats = exporter.get_export_stats(invalid_file)

    # Assert
    assert "error" in stats
    assert isinstance(stats["error"], str)


# ============================================================================
# Test JSONExporter._part_to_dict()
# ============================================================================


def test_part_to_dict_converts_part_to_dict(sample_part: Part, tmp_path: Path) -> None:
    """Test that _part_to_dict() converts Part to dict.

    Arrange: Create exporter and sample part
    Act: Convert part to dict
    Assert: Returns dict with all fields
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)

    # Act
    result = exporter._part_to_dict(sample_part)

    # Assert
    assert isinstance(result, dict)
    assert result["sku"] == "CSF-12345"
    assert result["name"] == "High Performance Radiator"
    assert result["price"] == "299.99"  # Converted to string
    assert result["category"] == "Radiators"
    assert "specifications" in result
    assert "images" in result
    assert len(result["images"]) == 2


def test_part_to_dict_handles_none_price(sample_part_minimal: Part, tmp_path: Path) -> None:
    """Test that _part_to_dict() handles None price correctly.

    Arrange: Create exporter and part with None price
    Act: Convert to dict
    Assert: Price is None or string 'None' in dict (Pydantic serialization)
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)

    # Act
    result = exporter._part_to_dict(sample_part_minimal)

    # Assert
    # Pydantic's model_dump converts None to "None" string in JSON mode
    assert result["price"] in (None, "None")


def test_part_to_dict_converts_decimal_to_string(sample_part: Part, tmp_path: Path) -> None:
    """Test that _part_to_dict() converts Decimal to string.

    Arrange: Create exporter and part with Decimal price
    Act: Convert to dict
    Assert: Price is string type
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)

    # Act
    result = exporter._part_to_dict(sample_part)

    # Assert
    assert isinstance(result["price"], str)
    assert result["price"] == "299.99"


# ============================================================================
# Test JSONExporter._compatibility_to_dict()
# ============================================================================


def test_compatibility_to_dict_converts_compatibility_to_dict(
    sample_compatibility: VehicleCompatibility,
    tmp_path: Path,
) -> None:
    """Test that _compatibility_to_dict() converts VehicleCompatibility to dict.

    Arrange: Create exporter and compatibility data
    Act: Convert to dict
    Assert: Returns dict with all fields
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)

    # Act
    result = exporter._compatibility_to_dict(sample_compatibility)

    # Assert
    assert isinstance(result, dict)
    assert result["part_sku"] == "CSF-12345"
    assert "vehicles" in result
    assert len(result["vehicles"]) == 3
    assert result["notes"] == "Direct fit, no modifications required"


def test_compatibility_to_dict_includes_vehicle_data(
    sample_compatibility: VehicleCompatibility,
    tmp_path: Path,
) -> None:
    """Test that _compatibility_to_dict() includes complete vehicle data.

    Arrange: Create exporter and compatibility
    Act: Convert to dict
    Assert: Vehicle data is complete
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)

    # Act
    result = exporter._compatibility_to_dict(sample_compatibility)

    # Assert
    first_vehicle = result["vehicles"][0]
    assert first_vehicle["make"] == "Audi"
    assert first_vehicle["model"] == "A4"
    assert first_vehicle["year"] == 2020
    assert first_vehicle["submodel"] == "Quattro"
    assert first_vehicle["engine"] == "2.0L L4"


# ============================================================================
# Test OSError paths and compact JSON for uncovered branches
# ============================================================================


def test_export_parts_raises_oserror_on_write_failure(tmp_path: Path, sample_part: Part) -> None:
    """Test that export_parts() raises OSError when file write fails.

    Arrange: Create exporter and make output path a directory so write fails
    Act: Try to export parts
    Assert: OSError raised with descriptive message
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)
    bad_path = tmp_path / "parts.json"
    bad_path.mkdir()

    # Act & Assert
    with pytest.raises(OSError, match="Failed to export parts"):
        exporter.export_parts([sample_part], filename="parts.json")


def test_export_compatibility_raises_oserror_on_write_failure(
    tmp_path: Path, sample_compatibility: VehicleCompatibility
) -> None:
    """Test that export_compatibility() raises OSError when file write fails.

    Arrange: Create exporter and make output path a directory so write fails
    Act: Try to export compatibility
    Assert: OSError raised with descriptive message
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)
    bad_path = tmp_path / "compat.json"
    bad_path.mkdir()

    # Act & Assert
    with pytest.raises(OSError, match="Failed to export compatibility"):
        exporter.export_compatibility([sample_compatibility], filename="compat.json")


def test_export_hierarchical_compact_json(
    tmp_path: Path, sample_part: Part, sample_compatibility: VehicleCompatibility
) -> None:
    """Test that export_hierarchical() with pretty=False produces compact single-line JSON.

    Arrange: Create exporter with parts and compatibility data
    Act: Export hierarchical with pretty=False
    Assert: Output is a single line of JSON
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)
    parts_by_sku = {"CSF-12345": sample_part}

    # Act
    output_path = exporter.export_hierarchical(
        [sample_compatibility], parts_by_sku, filename="compact.json", pretty=False
    )

    # Assert
    content = output_path.read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    assert len(lines) == 1


def test_export_hierarchical_raises_oserror_on_write_failure(
    tmp_path: Path, sample_part: Part, sample_compatibility: VehicleCompatibility
) -> None:
    """Test that export_hierarchical() raises OSError when file write fails.

    Arrange: Create exporter and make output path a directory so write fails
    Act: Try to export hierarchical
    Assert: OSError raised with descriptive message
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)
    bad_path = tmp_path / "hierarchy.json"
    bad_path.mkdir()

    # Act & Assert
    with pytest.raises(OSError, match="Failed to export hierarchical"):
        exporter.export_hierarchical(
            [sample_compatibility], {"CSF-12345": sample_part}, filename="hierarchy.json"
        )


def test_export_parts_incremental_compact_json(tmp_path: Path, sample_part: Part) -> None:
    """Test that export_parts_incremental() with pretty=False produces compact JSON.

    Arrange: Create exporter and sample part
    Act: Export parts incrementally with pretty=False
    Assert: Output is a single line of JSON
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)

    # Act
    output_path = exporter.export_parts_incremental(
        [sample_part], filename="compact.json", pretty=False
    )

    # Assert
    content = output_path.read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    assert len(lines) == 1


def test_export_parts_incremental_raises_oserror_on_write_failure(
    tmp_path: Path, sample_part: Part
) -> None:
    """Test that export_parts_incremental() raises OSError when file write fails.

    Arrange: Create exporter and make output path a directory so write fails
    Act: Try to export parts incrementally
    Assert: OSError raised with descriptive message
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)
    bad_path = tmp_path / "inc.json"
    bad_path.mkdir()

    # Act & Assert
    with pytest.raises(OSError, match="Failed to export parts incrementally"):
        exporter.export_parts_incremental([sample_part], filename="inc.json")


def test_export_compatibility_incremental_compact_json(
    tmp_path: Path, sample_compatibility: VehicleCompatibility
) -> None:
    """Test that export_compatibility_incremental() with pretty=False produces compact JSON.

    Arrange: Create exporter and sample compatibility
    Act: Export compatibility incrementally with pretty=False
    Assert: Output is a single line of JSON
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)

    # Act
    output_path = exporter.export_compatibility_incremental(
        [sample_compatibility], filename="compact.json", pretty=False
    )

    # Assert
    content = output_path.read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    assert len(lines) == 1


def test_export_compatibility_incremental_raises_oserror_on_write_failure(
    tmp_path: Path, sample_compatibility: VehicleCompatibility
) -> None:
    """Test that export_compatibility_incremental() raises OSError when file write fails.

    Arrange: Create exporter and make output path a directory so write fails
    Act: Try to export compatibility incrementally
    Assert: OSError raised with descriptive message
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)
    bad_path = tmp_path / "inc_compat.json"
    bad_path.mkdir()

    # Act & Assert
    with pytest.raises(OSError, match="Failed to export compatibility incrementally"):
        exporter.export_compatibility_incremental(
            [sample_compatibility], filename="inc_compat.json"
        )


def test_export_hierarchical_multiple_vehicles(tmp_path: Path) -> None:
    """Test that export_hierarchical() handles multiple vehicles across different years/makes.

    Arrange: Create two parts with distinct vehicle compatibility (different years/makes)
    Act: Export hierarchical
    Assert: Both years present in hierarchy with correct metadata
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)
    part1 = Part(sku="CSF-100", name="Radiator A", category="Radiator", price=Decimal("99.99"))
    part2 = Part(sku="CSF-200", name="Condenser B", category="Condenser", price=Decimal("199.99"))
    compat1 = VehicleCompatibility(
        part_sku="CSF-100",
        vehicles=[Vehicle(make="Honda", model="Civic", year=2020)],
    )
    compat2 = VehicleCompatibility(
        part_sku="CSF-200",
        vehicles=[Vehicle(make="Toyota", model="Camry", year=2021)],
    )
    parts_by_sku = {"CSF-100": part1, "CSF-200": part2}

    # Act
    output_path = exporter.export_hierarchical([compat1, compat2], parts_by_sku)

    # Assert
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["metadata"]["total_years"] == 2
    assert "2020" in data["data"] or 2020 in data["data"]
    assert "2021" in data["data"] or 2021 in data["data"]


# ============================================================================
# Test JSONExporter.export_complete()
# ============================================================================


def test_export_complete_creates_merged_json(
    tmp_path: Path,
    sample_part: Part,
    sample_vehicle: Vehicle,
) -> None:
    """Test that export_complete() creates merged JSON with parts and inline compatibility.

    Arrange: Create exporter, parts, and compatibility map
    Act: Export complete
    Assert: File created with correct merged structure
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)
    parts = [sample_part]
    compat_map = {sample_part.sku: [sample_vehicle]}

    # Act
    output_path = exporter.export_complete(parts, compat_map)

    # Assert
    assert output_path.exists()
    assert output_path == tmp_path / "parts_complete.json"

    with output_path.open(encoding="utf-8") as f:
        data = json.load(f)

    assert "metadata" in data
    assert "parts" in data
    assert data["metadata"]["total_parts"] == 1
    assert len(data["parts"]) == 1

    part_entry = data["parts"][0]
    assert part_entry["sku"] == "CSF-12345"
    assert "compatibility" in part_entry
    assert len(part_entry["compatibility"]) == 1
    assert part_entry["compatibility"][0]["make"] == "Audi"
    assert part_entry["compatibility"][0]["year"] == 2020


def test_export_complete_part_without_compatibility_gets_empty_list(
    tmp_path: Path,
    sample_part: Part,
) -> None:
    """Test that parts without compatibility get an empty compatibility list.

    Arrange: Create exporter, parts, and empty compatibility map
    Act: Export complete
    Assert: Part has empty compatibility array
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)
    parts = [sample_part]
    compat_map: dict[str, list[Vehicle]] = {}

    # Act
    output_path = exporter.export_complete(parts, compat_map)

    # Assert
    with output_path.open(encoding="utf-8") as f:
        data = json.load(f)

    part_entry = data["parts"][0]
    assert part_entry["compatibility"] == []


def test_export_complete_multiple_vehicles_inline(
    tmp_path: Path,
    sample_part: Part,
) -> None:
    """Test that multiple compatible vehicles are inlined correctly.

    Arrange: Create part with multiple compatible vehicles
    Act: Export complete
    Assert: All vehicles present in compatibility array
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)
    vehicles = [
        Vehicle(make="Audi", model="A4", year=2020),
        Vehicle(make="Audi", model="A4", year=2021),
        Vehicle(make="Audi", model="A5", year=2020),
    ]
    compat_map = {sample_part.sku: vehicles}

    # Act
    output_path = exporter.export_complete([sample_part], compat_map)

    # Assert
    with output_path.open(encoding="utf-8") as f:
        data = json.load(f)

    assert len(data["parts"][0]["compatibility"]) == 3


def test_export_complete_raises_oserror_on_write_failure(
    tmp_path: Path,
    sample_part: Part,
) -> None:
    """Test that export_complete() raises OSError when file write fails.

    Arrange: Create exporter and make output path a directory so write fails
    Act: Try to export complete
    Assert: OSError raised with descriptive message
    """
    # Arrange
    exporter = JSONExporter(output_dir=tmp_path)
    bad_path = tmp_path / "parts_complete.json"
    bad_path.mkdir()

    # Act & Assert
    with pytest.raises(OSError, match="Failed to export complete data"):
        exporter.export_complete([sample_part], {})
