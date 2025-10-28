"""Performance benchmarks using pytest-benchmark.

Run with:
    pytest tests/performance/test_benchmarks.py --benchmark-only -v
    pytest tests/performance/test_benchmarks.py --benchmark-compare
    pytest tests/performance/test_benchmarks.py --benchmark-save=baseline
"""

import json
from decimal import Decimal

import pytest
from bs4 import BeautifulSoup

from src.exporters.json_exporter import JSONExporter
from src.models.part import Part
from src.models.vehicle import Vehicle, VehicleCompatibility
from src.scraper.parser import CSFParser, HTMLParser
from src.scraper.validator import DataValidator


@pytest.fixture
def sample_html() -> str:
    """Provide sample HTML for parsing benchmarks."""
    return """
    <html>
        <body>
            <div class="applications">
                <div class="panel result" id="radiator">
                    <div class="panel-header">
                        <div class="row">
                            <div class="col">
                                <h4 class="font-weight-bold">Radiator</h4>
                            </div>
                        </div>
                    </div>
                    <div class="panel-body">
                        <div class="row app" id="test_app_1">
                            <div class="col-2 pl-0 image_3951">
                                <img class="img-thumbnail primary-image" alt="3951"
                                     src="https://example.com/image.jpg">
                            </div>
                            <div class="col-8 p-0">
                                <h4><a href="/items/3951">3951</a> - Radiator</h4>
                                Position: <b>Not Applicable</b><br>
                                <table class="table table-borderless table-ssm">
                                    <tbody>
                                        <tr>
                                            <td>Core Width: 24.5 in</td>
                                            <td>Core Height: 16.25 in</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </body>
    </html>
    """


@pytest.fixture
def sample_part_data() -> dict:
    """Provide sample part data for validation benchmarks."""
    return {
        "sku": "CSF-12345",
        "name": "High Performance Radiator",
        "price": "299.99",
        "description": "Premium aluminum radiator with enhanced cooling",
        "category": "Radiators",
        "specifications": {"core_size": "32x19", "rows": "2", "material": "Aluminum"},
        "images": [
            {"url": "https://example.com/img1.jpg", "alt_text": "Front view", "is_primary": True}
        ],
        "manufacturer": "CSF",
        "in_stock": True,
        "tech_notes": "Direct fit replacement",
        "position": "Front",
    }


@pytest.fixture
def sample_parts(sample_part_data) -> list[Part]:
    """Generate list of sample parts for export benchmarks."""
    parts = []
    for i in range(100):
        part = Part(
            sku=f"CSF-{10000 + i}",
            name=f"Part {i}",
            price=Decimal("99.99"),
            description=f"Description for part {i}",
            category="Radiators",
            specifications={"spec1": f"value{i}", "spec2": f"value{i}"},
            images=[],
            manufacturer="CSF",
            in_stock=True,
        )
        parts.append(part)
    return parts


# ===========================
# Parser Benchmarks
# ===========================


@pytest.mark.benchmark(group="parser")
def test_benchmark_html_parse(benchmark, sample_html):
    """Benchmark HTML parsing with BeautifulSoup."""
    parser = HTMLParser()

    result = benchmark(parser.parse, sample_html)

    assert result is not None
    assert isinstance(result, BeautifulSoup)


@pytest.mark.benchmark(group="parser")
def test_benchmark_csf_part_extraction(benchmark, sample_html):
    """Benchmark CSF part data extraction from HTML."""
    parser = CSFParser()
    soup = parser.parse(sample_html)

    result = benchmark(parser.extract_part_data, soup)

    assert result["sku"] == "3951"


@pytest.mark.benchmark(group="parser")
def test_benchmark_text_extraction(benchmark, sample_html):
    """Benchmark text extraction from parsed HTML."""
    parser = HTMLParser()
    soup = parser.parse(sample_html)

    result = benchmark(parser.extract_text, soup, ".row.app h4")

    assert result is not None


# ===========================
# Validator Benchmarks
# ===========================


@pytest.mark.benchmark(group="validator")
def test_benchmark_part_validation(benchmark, sample_part_data):
    """Benchmark Part validation with Pydantic."""
    validator = DataValidator()

    result = benchmark(validator.validate_part, sample_part_data)

    assert result.sku == "CSF-12345"


@pytest.mark.benchmark(group="validator")
def test_benchmark_batch_validation(benchmark):
    """Benchmark batch validation of 100 parts."""
    validator = DataValidator()
    parts_data = [
        {
            "sku": f"CSF-{10000 + i}",
            "name": f"Part {i}",
            "category": "Radiators",
            "specifications": {},
            "images": [],
        }
        for i in range(100)
    ]

    def validate_batch():
        return [validator.validate_part(data) for data in parts_data]

    results = benchmark(validate_batch)

    assert len(results) == 100


# ===========================
# Export Benchmarks
# ===========================


@pytest.mark.benchmark(group="export")
def test_benchmark_json_export(benchmark, sample_parts, tmp_path):
    """Benchmark JSON export of 100 parts."""
    exporter = JSONExporter(output_dir=tmp_path)

    result = benchmark(exporter.export_parts, sample_parts, "benchmark.json")

    assert result.exists()


@pytest.mark.benchmark(group="export")
def test_benchmark_json_serialization(benchmark, sample_parts):
    """Benchmark JSON serialization without file I/O."""

    def serialize_parts():
        return [part.model_dump(mode="json") for part in sample_parts]

    results = benchmark(serialize_parts)

    assert len(results) == 100


@pytest.mark.benchmark(group="export")
def test_benchmark_incremental_export(benchmark, sample_parts, tmp_path):
    """Benchmark incremental JSON export (append mode)."""
    exporter = JSONExporter(output_dir=tmp_path)
    filename = "incremental.json"

    # Create initial file
    exporter.export_parts_incremental(sample_parts[:50], filename, append=False)

    # Benchmark appending
    result = benchmark(exporter.export_parts_incremental, sample_parts[50:], filename, append=True)

    assert result.exists()


# ===========================
# Model Benchmarks
# ===========================


@pytest.mark.benchmark(group="models")
def test_benchmark_part_creation(benchmark):
    """Benchmark Part model instantiation."""

    def create_part():
        return Part(
            sku="CSF-12345",
            name="Test Part",
            category="Radiators",
            specifications={},
            images=[],
        )

    result = benchmark(create_part)

    assert result.sku == "CSF-12345"


@pytest.mark.benchmark(group="models")
def test_benchmark_vehicle_creation(benchmark):
    """Benchmark Vehicle model instantiation."""

    def create_vehicle():
        return Vehicle(year=2020, make="Honda", model="Civic")

    result = benchmark(create_vehicle)

    assert result.year == 2020


@pytest.mark.benchmark(group="models")
def test_benchmark_compatibility_creation(benchmark):
    """Benchmark VehicleCompatibility model with multiple vehicles."""

    def create_compatibility():
        vehicles = [Vehicle(year=2015 + i, make="Honda", model="Civic") for i in range(10)]
        return VehicleCompatibility(part_sku="CSF-12345", vehicles=vehicles)

    result = benchmark(create_compatibility)

    assert len(result.vehicles) == 10


# ===========================
# Complex Workflow Benchmarks
# ===========================


@pytest.mark.benchmark(group="workflow")
def test_benchmark_parse_validate_workflow(benchmark, sample_html, sample_part_data):
    """Benchmark complete parse → validate workflow."""

    def parse_and_validate():
        parser = CSFParser()
        validator = DataValidator()
        soup = parser.parse(sample_html)
        part_data = parser.extract_part_data(soup)
        # Add required fields for validation
        part_data.update(sample_part_data)
        return validator.validate_part(part_data)

    result = benchmark(parse_and_validate)

    assert result.sku == "CSF-12345"


@pytest.mark.benchmark(group="workflow")
def test_benchmark_validate_export_workflow(benchmark, sample_parts, tmp_path):
    """Benchmark complete validate → export workflow."""
    exporter = JSONExporter(output_dir=tmp_path)

    def validate_and_export():
        # Parts are already validated, just export
        return exporter.export_parts(sample_parts, "workflow.json")

    result = benchmark(validate_and_export)

    assert result.exists()


# ===========================
# Memory-Intensive Benchmarks
# ===========================


@pytest.mark.benchmark(group="memory")
def test_benchmark_large_part_list(benchmark):
    """Benchmark handling of 1000 parts in memory."""

    def create_large_list():
        return [
            Part(
                sku=f"CSF-{i:05d}",
                name=f"Part {i}",
                category="Radiators",
                specifications={"spec1": f"val{i}"},
                images=[],
            )
            for i in range(1000)
        ]

    results = benchmark(create_large_list)

    assert len(results) == 1000


@pytest.mark.benchmark(group="memory")
def test_benchmark_json_load(benchmark, sample_parts, tmp_path):
    """Benchmark loading large JSON file."""
    exporter = JSONExporter(output_dir=tmp_path)
    filepath = exporter.export_parts(sample_parts * 10, "large.json")  # 1000 parts

    def load_json():
        with filepath.open() as f:
            return json.load(f)

    result = benchmark(load_json)

    assert result["metadata"]["total_parts"] == 1000
