"""Merge parts, compatibility, and detail data for WordPress import."""

import json
from pathlib import Path
from typing import Any


def _load_json_file(path: Path, key: str) -> list[dict[str, Any]]:
    """Load a JSON file and return the list under the given key.

    Args:
        path: Path to the JSON file.
        key: Top-level key containing the list data.

    Returns:
        List of dictionaries from the JSON file.
    """
    with path.open() as f:
        data = json.load(f)
    return data[key]


def _build_compatibility_lookup(
    compatibility: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Build a SKU-to-vehicles lookup from compatibility entries.

    Args:
        compatibility: Raw compatibility data with part_sku and vehicles.

    Returns:
        Dictionary mapping SKU to list of vehicle dicts.
    """
    lookup: dict[str, list[dict[str, Any]]] = {}
    for comp in compatibility:
        lookup[comp["part_sku"]] = comp["vehicles"]
    return lookup


def _enrich_part(
    part: dict[str, Any],
    details_by_sku: dict[str, dict[str, Any]],
) -> bool:
    """Merge enrichment details into a part dict in-place.

    Args:
        part: Part dictionary to enrich.
        details_by_sku: Lookup of enriched details keyed by SKU.

    Returns:
        True if enrichment data was found, False otherwise.
    """
    sku = part["sku"]
    if sku in details_by_sku:
        enriched = details_by_sku[sku]
        part["description"] = enriched.get("description") or enriched.get("full_description") or ""
        part["tech_notes"] = enriched.get("tech_notes")
        part["specifications"] = enriched.get("specifications", [])
        part["interchange"] = enriched.get("interchange", [])
        part["images"] = enriched.get("images", [])
        return True

    part["description"] = None
    part["tech_notes"] = None
    part["specifications"] = []
    part["interchange"] = []
    part["images"] = []
    return False


def _write_output(
    merged: list[dict[str, Any]],
    output_path: Path,
    enriched_count: int,
    compatibility_count: int,
) -> None:
    """Write merged data to JSON and print summary.

    Args:
        merged: List of fully merged part dictionaries.
        output_path: Destination file path.
        enriched_count: Number of parts with enrichment data.
        compatibility_count: Number of parts with compatibility data.
    """
    output_data = {"parts": merged}
    with output_path.open("w") as f:
        json.dump(output_data, f, indent=2)

    total = len(merged)
    enrich_pct = enriched_count / total * 100
    compat_pct = compatibility_count / total * 100
    size_mb = output_path.stat().st_size / 1024 / 1024

    print(f"\n{'=' * 60}")
    print("Merge Complete!")
    print(f"{'=' * 60}")
    print(f"Total parts:           {total}")
    print(f"With enrichment:       {enriched_count} ({enrich_pct:.1f}%)")
    print(f"With compatibility:    {compatibility_count} ({compat_pct:.1f}%)")
    print(f"\nOutput: {output_path}")
    print(f"Size:   {size_mb:.1f} MB")
    print(f"{'=' * 60}")


def merge_data() -> None:
    """Merge parts catalog, compatibility, and enrichment data."""
    print("Loading data files...")

    parts_path = Path("exports/parts.json")
    compatibility_path = Path("exports/compatibility.json")
    details_path = Path("exports/parts_with_details.json")

    parts = _load_json_file(parts_path, "parts")
    print(f"Loaded {len(parts)} parts from {parts_path}")

    compatibility = _load_json_file(compatibility_path, "compatibility")
    print(f"Loaded {len(compatibility)} compatibility entries")

    details = _load_json_file(details_path, "parts")
    print(f"Loaded {len(details)} enriched parts from {details_path}")

    # Build lookups
    print("\nMerging data...")
    details_by_sku = {part["sku"]: part for part in details}
    compatibility_by_sku = _build_compatibility_lookup(compatibility)

    # Merge into final structure
    merged = []
    enriched_count = 0
    compatibility_count = 0

    for part in parts:
        if _enrich_part(part, details_by_sku):
            enriched_count += 1

        if part["sku"] in compatibility_by_sku:
            part["compatibility"] = compatibility_by_sku[part["sku"]]
            compatibility_count += 1
        else:
            part["compatibility"] = []

        merged.append(part)

    output_path = Path("scraped_data_clean/parts_complete.json")
    _write_output(merged, output_path, enriched_count, compatibility_count)


if __name__ == "__main__":
    merge_data()
