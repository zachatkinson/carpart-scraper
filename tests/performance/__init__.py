"""Performance tests for carpart-scraper.

This module contains performance benchmarks and profiling tests for:
- Scraper throughput (parts per minute)
- Memory usage during large scrapes
- Parsing performance
- Validation performance
- Export performance
- Concurrent request handling

Run with: pytest tests/performance/ -v --benchmark-only
"""
