# Performance Benchmarks and Baselines

This document contains performance benchmarks and memory profiling results for the carpart-scraper project. These baselines were established on 2025-10-28 using Python 3.13.7 on macOS (Darwin 25.0.0).

## Table of Contents

- [Overview](#overview)
- [Benchmark Results](#benchmark-results)
  - [Parser Benchmarks](#parser-benchmarks)
  - [Validator Benchmarks](#validator-benchmarks)
  - [Export Benchmarks](#export-benchmarks)
  - [Model Benchmarks](#model-benchmarks)
  - [Workflow Benchmarks](#workflow-benchmarks)
  - [Memory Benchmarks](#memory-benchmarks)
- [Memory Profiling Results](#memory-profiling-results)
  - [Large Part Collections](#large-part-collections)
  - [Export Operations](#export-operations)
  - [Parser Operations](#parser-operations)
  - [Vehicle Compatibility](#vehicle-compatibility)
- [Performance Guidelines](#performance-guidelines)
- [Running Performance Tests](#running-performance-tests)

## Overview

Performance testing is critical for ensuring the scraper can handle large-scale data extraction efficiently. We use:

- **pytest-benchmark**: For precise performance benchmarking
- **tracemalloc**: For detailed memory profiling
- **pytest markers**: `@pytest.mark.slow` and `@pytest.mark.memory` for long-running tests

All benchmarks use the AAA (Arrange-Act-Assert) pattern and are designed to be reproducible.

## Benchmark Results

### Parser Benchmarks

| Operation | Min (μs) | Mean (μs) | Median (μs) | OPS (K/s) | Notes |
|-----------|----------|-----------|-------------|-----------|-------|
| **Text Extraction** | 55.5 | 68.3 | 63.0 | 14.6 | CSS selector-based extraction |
| **HTML Parse** | 248.4 | 307.8 | 262.2 | 3.2 | BeautifulSoup parsing |
| **CSF Part Extraction** | 367.6 | 447.3 | 410.3 | 2.2 | Complete part data extraction |

**Key Insights:**
- Text extraction is the fastest operation (14.6K ops/sec)
- HTML parsing with BeautifulSoup averages 308 μs
- Complete part extraction takes ~450 μs per part

### Validator Benchmarks

| Operation | Min (μs) | Mean (μs) | Median (μs) | OPS | Notes |
|-----------|----------|-----------|-------------|-----|-------|
| **Single Part Validation** | 38.2 | 46.2 | 42.3 | 21,633/s | Pydantic validation |
| **Batch Validation (100 parts)** | 3,442 | 3,742 | 3,726 | 267/s | 100 parts validated |

**Key Insights:**
- Single part validation is very fast: ~46 μs
- Batch validation scales linearly: ~37 μs per part
- Can validate ~21,600 parts per second (single) or ~26,700 parts per second (batched)

### Export Benchmarks

| Operation | Min (μs) | Mean (μs) | Median (μs) | OPS | Notes |
|-----------|----------|-----------|-------------|-----|-------|
| **JSON Serialization** | 157.7 | 174.3 | 170.0 | 5,738/s | Model to dict conversion |
| **JSON Export** | 992.0 | 1,126.6 | 1,100.8 | 888/s | 100 parts to file |
| **Incremental Export** | 1,734.7 | 166,529.6 | 169,421.9 | 6.0/s | Append mode (load + append + write) |

**Key Insights:**
- JSON serialization: ~174 μs per 100 parts
- Full export to file: ~1.1 ms per 100 parts
- Incremental export is slower due to file reloading (use for large datasets to manage memory)

### Model Benchmarks

| Operation | Min (μs) | Mean (μs) | Median (μs) | OPS (K/s) | Notes |
|-----------|----------|-----------|-------------|-----------|-------|
| **Vehicle Creation** | 1.3 | 1.5 | 1.5 | 650.0 | Instantiate Vehicle model |
| **Part Creation** | 1.4 | 1.6 | 1.5 | 608.6 | Instantiate Part model |
| **Compatibility Creation** | 12.7 | 13.5 | 13.3 | 73.9 | VehicleCompatibility with 10 vehicles |

**Key Insights:**
- Model instantiation is extremely fast: 1-2 μs for simple models
- VehicleCompatibility with 10 vehicles: ~13.5 μs
- Can create ~650,000 Vehicle objects per second

### Workflow Benchmarks

| Workflow | Min (μs) | Mean (μs) | Median (μs) | OPS | Notes |
|----------|----------|-----------|-------------|-----|-------|
| **Parse → Validate** | 677.8 | 792.9 | 714.9 | 1,261/s | Complete parse and validation |
| **Validate → Export** | 1,002.2 | 1,029.0 | 1,017.0 | 972/s | Validation and file export |

**Key Insights:**
- Full parse → validate workflow: ~793 μs
- Validate → export workflow: ~1,029 μs
- Can process ~1,200 parts per second end-to-end

### Memory Benchmarks

| Operation | Parts Count | Min (ms) | Mean (ms) | Median (ms) | Notes |
|-----------|-------------|----------|-----------|-------------|-------|
| **JSON Load** | 1,000 | 1.43 | 1.61 | 1.47 | Load large JSON file |
| **Large Part List** | 1,000 | 1.81 | 2.12 | 1.87 | Create 1,000 parts in memory |

## Memory Profiling Results

### Large Part Collections

**10,000 Parts in Memory:**
- **Current Memory**: 20.62 MB
- **Peak Memory**: 20.62 MB
- **Per Part**: 2.11 KB
- **Assertion**: Peak < 500 MB ✅

**Key Insights:**
- Very memory efficient: ~2 KB per part
- 10,000 parts consume only ~20 MB
- Can easily handle 100,000+ parts in memory

### Export Operations

**5,000 Parts Export:**
- **Peak Memory**: 4.16 MB
- **File Size**: 1.70 MB
- **Assertion**: Peak < 200 MB ✅

**10,000 Parts Incremental Export:**
- **Peak Memory**: 12.21 MB
- **File Size**: 3.04 MB
- **Batches**: 10 batches of 1,000 parts
- **Assertion**: Peak < 500 MB ✅

**Key Insights:**
- Single export is more memory efficient: 4.16 MB for 5,000 parts
- Incremental export trades memory for flexibility: 12.21 MB for 10,000 parts
- Both approaches are well under memory limits
- JSON compression ratio: ~2:1 (in-memory vs file)

### Parser Operations

**100 Parts HTML Parsing:**
- **Peak Memory**: 1.13 MB
- **HTML Size**: 41.66 KB
- **Parts Found**: 100
- **Assertion**: Peak < 50 MB ✅

**Key Insights:**
- BeautifulSoup creates ~27x memory overhead (41 KB → 1.13 MB)
- Still very reasonable for typical scraping operations

### Vehicle Compatibility

**1,000 Compatibility Entries (10 vehicles each):**
- **Peak Memory**: 7.18 MB
- **Total Vehicles**: 10,000
- **Per Entry**: ~7.18 KB
- **Assertion**: Peak < 100 MB ✅

**Key Insights:**
- Vehicle compatibility data is compact: ~7 KB per entry
- Can store 10,000+ compatibility mappings in <10 MB

## Performance Guidelines

### Recommended Limits

Based on our benchmarks, the following limits are safe for production use:

| Operation | Recommended Limit | Safety Margin |
|-----------|------------------|---------------|
| Parts in memory | 50,000 | 10x safety margin (500 MB) |
| Export batch size | 10,000 | Optimal for incremental export |
| Concurrent parsers | 10 | Depends on available CPU cores |
| HTML parse size | 1 MB | Keep under 50 MB parsed |

### Optimization Tips

1. **For Large Scrapes (>10,000 parts)**:
   - Use incremental export: `export_parts_incremental(parts, filename, append=True)`
   - Process in batches of 1,000-5,000 parts
   - Current memory usage: ~12 MB for 10,000 parts

2. **For Fast Scraping**:
   - Batch validate parts: ~267 batches/sec (100 parts each)
   - Use concurrent parsers with rate limiting
   - Parse → validate → export: ~1,200 parts/sec

3. **For Memory Efficiency**:
   - Clear part lists after export: `parts.clear()`
   - Use incremental export for continuous scraping
   - Monitor with `tracemalloc` in production

### Expected Throughput

Based on workflow benchmarks:

- **Parse → Validate**: ~1,261 parts/second
- **Validate → Export**: ~972 parts/second
- **Full Pipeline**: ~800-1,000 parts/second (with rate limiting)

With 1-3 second delays between requests (respectful scraping):
- **Conservative (3s delay)**: ~1,200 parts/hour
- **Moderate (2s delay)**: ~1,800 parts/hour
- **Aggressive (1s delay)**: ~3,600 parts/hour

## Running Performance Tests

### Run All Benchmarks

```bash
# Run all performance benchmarks
pytest tests/performance/test_benchmarks.py --benchmark-only -v

# Save baseline for comparison
pytest tests/performance/test_benchmarks.py --benchmark-only --benchmark-save=baseline

# Compare against baseline
pytest tests/performance/test_benchmarks.py --benchmark-only --benchmark-compare=baseline
```

### Run Memory Profiling Tests

```bash
# Run memory profiling tests (marked as slow)
pytest tests/performance/test_memory_profiling.py -v -m slow --tb=short -s

# Run specific memory test
pytest tests/performance/test_memory_profiling.py::test_memory_large_part_collection -v -s
```

### Run All Performance Tests

```bash
# Run all performance tests (benchmarks + memory profiling)
pytest tests/performance/ -v -m slow
```

### Benchmark Options

```bash
# Show detailed statistics
pytest tests/performance/test_benchmarks.py --benchmark-only --benchmark-verbose

# Only run specific benchmark group
pytest tests/performance/test_benchmarks.py --benchmark-only -k "parser"

# Generate histogram
pytest tests/performance/test_benchmarks.py --benchmark-only --benchmark-histogram=histogram
```

## Monitoring in Production

For production monitoring, consider:

1. **Memory Monitoring**:
   ```python
   import tracemalloc
   tracemalloc.start()
   # ... scraping operations ...
   current, peak = tracemalloc.get_traced_memory()
   print(f"Peak memory: {peak / 1024 / 1024:.2f} MB")
   ```

2. **Performance Logging**:
   ```python
   import time
   start = time.perf_counter()
   # ... operation ...
   elapsed = time.perf_counter() - start
   logger.info("operation_complete", duration_ms=elapsed * 1000)
   ```

3. **Throughput Tracking**:
   ```python
   from src.utils.stats_analyzer import StatsAnalyzer
   analyzer = StatsAnalyzer()
   # Track parts per minute, memory usage, errors
   ```

---

**Last Updated**: 2025-10-28
**Python Version**: 3.13.7
**Platform**: macOS (Darwin 25.0.0)
**Test Suite**: 15 benchmarks + 5 memory profiling tests
