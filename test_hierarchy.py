#!/usr/bin/env python3
"""Manual integration test for hierarchy enumeration.

This script provides a quick way to manually test hierarchy building
without running the full test suite. Useful for development and debugging.

Tests:
- AJAX endpoints work correctly
- Year enumeration for a specific make
- Model enumeration for a specific year
- Complete hierarchy building with filters
"""

from __future__ import annotations

import sys
import traceback

from src.scraper.orchestrator import ScraperOrchestrator


def print_section(title: str, width: int = 80) -> None:
    """Print a formatted section header."""
    print("=" * width)
    print(title)
    print("=" * width)
    print()


def print_subsection(title: str, width: int = 80) -> None:
    """Print a formatted subsection header."""
    print(title)
    print("-" * width)


def main() -> int:
    """Test hierarchy building with Honda examples.

    Returns:
        0 for success, 1 for failure
    """
    print_section("Testing Hierarchy Enumeration")

    # Create orchestrator
    print("Creating orchestrator...")
    orchestrator = ScraperOrchestrator()
    print("✓ Orchestrator created")
    print()

    try:
        # Test 1: Build hierarchy for Honda only (all years)
        print_subsection("Test 1: Building hierarchy for Honda (all years)...")
        # Using private method for testing purposes  # noqa: SLF001
        honda_hierarchy = orchestrator._build_hierarchy(make_filter="Honda")
        print(f"✓ Found {len(honda_hierarchy)} Honda vehicle configurations")
        print()

        # Show first 3 configurations
        print("Sample configurations:")
        for i, config in enumerate(honda_hierarchy[:3], 1):
            print(f"  {i}. {config['year']} {config['make']} {config['model']}")
            print(f"     Application ID: {config['application_id']}")
        print()

        # Test 2: Build hierarchy for Honda 2020 only
        print_subsection("Test 2: Building hierarchy for Honda 2020...")
        # Using private method for testing purposes  # noqa: SLF001
        honda_2020 = orchestrator._build_hierarchy(make_filter="Honda", year_filter=2020)
        print(f"✓ Found {len(honda_2020)} Honda 2020 models")
        print()

        # Show all 2020 models
        print("2020 Honda models:")
        for i, config in enumerate(honda_2020, 1):
            print(f"  {i}. {config['model']} (App ID: {config['application_id']})")
        print()

        # Test 3: Verify year enumeration directly
        print_subsection("Test 3: Testing year enumeration for Honda...")
        honda_id = 3  # Honda ID from MAKES constant
        # Using private method for testing purposes  # noqa: SLF001
        years = orchestrator._enumerate_years(honda_id, "Honda")
        print(f"✓ Found {len(years)} years for Honda")
        print(f"  Sample years: {list(years.values())[:5]}")
        print()

        # Test 4: Verify model enumeration for a specific year
        if years:
            # Get first year_id
            first_year_id = list(years.keys())[0]
            first_year = years[first_year_id]
            print_subsection(f"Test 4: Testing model enumeration for Honda {first_year}...")
            # Using private method for testing purposes  # noqa: SLF001
            models = orchestrator._enumerate_models(first_year_id, first_year, "Honda")
            print(f"✓ Found {len(models)} Honda {first_year} models")
            print(f"  Models: {', '.join(list(models.values())[:5])}")
            print()

        print_section("All tests passed! ✓")
        return 0

    except Exception as e:  # noqa: BLE001
        # Broad exception is acceptable for a test script
        print(f"\n❌ Error: {e}")
        traceback.print_exc()
        return 1

    finally:
        # Clean up
        orchestrator.close()
        print("\n✓ Orchestrator closed")


if __name__ == "__main__":
    sys.exit(main())
