"""Memory profiling tests for carpart-scraper.

Run with:
    pytest tests/performance/test_memory_profiling.py -v -s
    python -m memory_profiler tests/performance/test_memory_profiling.py

Note: These tests are marked as 'slow' and are skipped by default.
Run with: pytest tests/performance/ -v -m slow
"""

from decimal import Decimal
from pathlib import Path

import pytest

from src.exporters.json_exporter import JSONExporter
from src.models.part import Part
from src.models.vehicle import Vehicle, VehicleCompatibility
from src.scraper.parser import CSFParser


@pytest.mark.slow
@pytest.mark.memory
def test_memory_large_part_collection():
    """Test memory usage with 10,000 parts in memory."""
    import tracemalloc

    tracemalloc.start()

    # Create 10,000 parts
    parts = []
    for i in range(10000):
        part = Part(
            sku=f"CSF-{i:05d}",
            name=f"High Performance Part {i}",
            price=Decimal("299.99"),
            description=f"Premium part with enhanced features - Part #{i}",
            category="Radiators" if i % 2 == 0 else "Condensers",
            specifications={
                "core_width": f"{20 + (i % 10)} in",
                "core_height": f"{15 + (i % 5)} in",
                "rows": str(2 + (i % 2)),
                "material": "Aluminum",
            },
            images=[],
            manufacturer="CSF",
            in_stock=True,
            tech_notes=f"Tech note for part {i}",
        )
        parts.append(part)

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Convert to MB
    current_mb = current / 1024 / 1024
    peak_mb = peak / 1024 / 1024

    print("\n10,000 Parts Memory Usage:")
    print(f"  Current: {current_mb:.2f} MB")
    print(f"  Peak: {peak_mb:.2f} MB")
    print(f"  Per part: {(peak_mb / 10000) * 1024:.2f} KB")

    # Assertions (reasonable limits for 10k parts)
    assert len(parts) == 10000
    assert peak_mb < 500  # Should be well under 500MB for 10k parts
    assert current_mb < 300  # Current should be under 300MB


@pytest.mark.slow
@pytest.mark.memory
def test_memory_large_export(tmp_path: Path):
    """Test memory usage during large JSON export."""
    import tracemalloc

    # Create parts
    parts = [
        Part(
            sku=f"CSF-{i:05d}",
            name=f"Part {i}",
            price=Decimal("99.99"),
            category="Radiators",
            specifications={"spec1": f"value{i}"},
            images=[],
        )
        for i in range(5000)
    ]

    exporter = JSONExporter(output_dir=tmp_path)

    tracemalloc.start()

    # Export
    filepath = exporter.export_parts(parts, "large_export.json")

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Convert to MB
    current_mb = current / 1024 / 1024
    peak_mb = peak / 1024 / 1024

    print("\n5,000 Parts Export Memory Usage:")
    print(f"  Current: {current_mb:.2f} MB")
    print(f"  Peak: {peak_mb:.2f} MB")
    print(f"  File size: {filepath.stat().st_size / 1024 / 1024:.2f} MB")

    # Assertions
    assert filepath.exists()
    assert peak_mb < 200  # Should be under 200MB for 5k parts export


@pytest.mark.slow
@pytest.mark.memory
def test_memory_incremental_export(tmp_path: Path):
    """Test memory usage with incremental export (append mode)."""
    import tracemalloc

    exporter = JSONExporter(output_dir=tmp_path)
    filename = "incremental.json"

    # Create initial export
    initial_parts = [
        Part(
            sku=f"CSF-{i:05d}", name=f"Part {i}", category="Radiators", specifications={}, images=[]
        )
        for i in range(1000)
    ]
    exporter.export_parts_incremental(initial_parts, filename, append=False)

    tracemalloc.start()

    # Append 9 more batches (10,000 parts total)
    for batch in range(9):
        batch_parts = [
            Part(
                sku=f"CSF-{1000 + batch * 1000 + i:05d}",
                name=f"Part {1000 + batch * 1000 + i}",
                category="Radiators",
                specifications={},
                images=[],
            )
            for i in range(1000)
        ]
        exporter.export_parts_incremental(batch_parts, filename, append=True)

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Convert to MB
    current_mb = current / 1024 / 1024
    peak_mb = peak / 1024 / 1024

    filepath = tmp_path / filename

    print("\n10,000 Parts Incremental Export Memory Usage:")
    print(f"  Current: {current_mb:.2f} MB")
    print(f"  Peak: {peak_mb:.2f} MB")
    print(f"  File size: {filepath.stat().st_size / 1024 / 1024:.2f} MB")

    # Assertions
    assert filepath.exists()
    # Note: Incremental export loads the entire file each time,
    # so memory usage will be higher than single export
    assert peak_mb < 500  # Reasonable limit


@pytest.mark.slow
@pytest.mark.memory
def test_memory_parser_operations():
    """Test memory usage during parsing operations."""
    import tracemalloc

    # Create large HTML document
    html_parts = []
    for i in range(100):
        html_parts.append(f"""
            <div class="row app" id="app_{i}">
                <h4><a href="/items/{i}">{i}</a> - Part {i}</h4>
                <table class="table">
                    <tbody>
                        <tr>
                            <td>Spec {i * 1}: Value {i * 1}</td>
                            <td>Spec {i * 2}: Value {i * 2}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        """)

    large_html = f"""
    <html>
        <body>
            <div class="applications">
                {"".join(html_parts)}
            </div>
        </body>
    </html>
    """

    parser = CSFParser()

    tracemalloc.start()

    # Parse
    soup = parser.parse(large_html)

    # Extract from all app divs
    apps = soup.select(".row.app")

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Convert to MB
    current_mb = current / 1024 / 1024
    peak_mb = peak / 1024 / 1024

    print("\n100 Parts HTML Parsing Memory Usage:")
    print(f"  Current: {current_mb:.2f} MB")
    print(f"  Peak: {peak_mb:.2f} MB")
    print(f"  HTML size: {len(large_html) / 1024:.2f} KB")
    print(f"  Parts found: {len(apps)}")

    # Assertions
    assert len(apps) == 100
    assert peak_mb < 50  # Should be under 50MB for 100 parts


@pytest.mark.slow
@pytest.mark.memory
def test_memory_vehicle_compatibility():
    """Test memory usage with large vehicle compatibility data."""
    import tracemalloc

    tracemalloc.start()

    # Create 1000 compatibility entries with 10 vehicles each
    compatibilities = []
    for part_num in range(1000):
        vehicles = [
            Vehicle(year=2010 + (i % 15), make=f"Make{i % 10}", model=f"Model{i % 20}")
            for i in range(10)
        ]
        compat = VehicleCompatibility(part_sku=f"CSF-{part_num:05d}", vehicles=vehicles)
        compatibilities.append(compat)

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Convert to MB
    current_mb = current / 1024 / 1024
    peak_mb = peak / 1024 / 1024

    print("\n1,000 Compatibility Entries (10 vehicles each) Memory Usage:")
    print(f"  Current: {current_mb:.2f} MB")
    print(f"  Peak: {peak_mb:.2f} MB")
    print(f"  Total vehicles: {sum(len(c.vehicles) for c in compatibilities)}")

    # Assertions
    assert len(compatibilities) == 1000
    assert sum(len(c.vehicles) for c in compatibilities) == 10000
    assert peak_mb < 100  # Should be under 100MB


# ===========================
# Helper functions
# ===========================


def print_memory_summary():
    """Print current memory usage summary."""
    import os

    import psutil

    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()

    print("\nProcess Memory Summary:")
    print(f"  RSS (Resident Set Size): {mem_info.rss / 1024 / 1024:.2f} MB")
    print(f"  VMS (Virtual Memory Size): {mem_info.vms / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    # Can be run directly for profiling
    print("Running memory profiling tests...")
    test_memory_large_part_collection()
    test_memory_parser_operations()
    test_memory_vehicle_compatibility()
    print("\nMemory profiling complete!")
