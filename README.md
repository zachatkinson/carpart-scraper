# CSF MyCarParts Scraper

[![Python Version](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](http://mypy-lang.org/)
[![Tests](https://img.shields.io/badge/tests-950%20passing-brightgreen.svg)](#testing)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> A production-grade web scraper and WordPress plugin for extracting automotive parts data from csf.mycarparts.com, built with strict adherence to DRY, SOLID, and AAA principles.

## Overview

The **CSF MyCarParts Scraper** extracts complete automotive parts data and displays it through a WordPress catalog. The project consists of:

1. **Web Scraper** — Intelligent, respectful scraper that handles JavaScript-rendered pages via Playwright
2. **JSON Export** — Clean, Pydantic-validated data exported to structured JSON
3. **WordPress Plugin** — Full catalog with custom database table, Gutenberg blocks, REST API, and async search

## Features

### Web Scraper

- **1,728 parts** across 8,764 application pages and 32,500+ vehicle configurations
- **Two-phase pipeline** — Catalog scraping + detail enrichment run independently
- **Intelligent change detection** — MD5 fingerprinting skips unchanged catalogs
- **Incremental updates** — Content hashing detects changed parts without re-scraping everything
- **Checkpoint/resume** — Recover from interruptions without losing progress
- **Respectful scraping** — 1-3 second delays, descriptive user-agent, robots.txt compliance
- **Retry logic** — Exponential backoff on failures
- **Data validation** — Pydantic models ensure data quality
- **AVIF image conversion** — Gallery images downloaded and optimized

### WordPress Plugin

- **Custom database table** (`wp_csf_parts`) for fast queries
- **Gutenberg blocks** — Product catalog and single product blocks
- **REST API** — Full CRUD endpoints for parts data
- **Async search** — JavaScript-powered search with filters
- **Custom taxonomies** — Makes, models, years, categories
- **WP-CLI integration** — `wp csf-parts import`, `stats`, `clear`
- **Responsive design** — Mobile-friendly catalog and detail pages

## Architecture

```
┌─────────────────────────────────────┐
│       CSF MyCarParts Website        │
└──────────────┬──────────────────────┘
               │  Respectful scraping (1-3s delays)
               ▼
┌────────────────────────────────────────┐
│         Python Scraper                 │
│  ┌──────────┐  ┌─────────┐  ┌────────┐│
│  │ Fetcher  │→ │ Parser  │→ │Validate││
│  │(Playwright│  │(BS4)    │  │(Pydantic││
│  │+ httpx)  │  │         │  │)       ││
│  └──────────┘  └─────────┘  └───┬────┘│
└─────────────────────────────────┼─────┘
                                  │
         Phase 1                  ▼              Phase 2
  ┌──────────────────┐   ┌────────────────┐   ┌──────────────────┐
  │ scrape_catalog.py│   │  parts.json    │   │enrich_details.py │
  │ - Hierarchy      │──→│  compat.json   │──→│ - Descriptions   │
  │ - Applications   │   └────────────────┘   │ - Specs (22 flds)│
  │ - Basic parts    │                        │ - Tech notes     │
  └──────────────────┘                        │ - Interchange    │
                                              │ - Images → AVIF  │
                                              └────────┬─────────┘
                                                       │
                                                       ▼
                                              ┌────────────────────┐
                                              │parts_with_details  │
                                              │    .json           │
                                              └────────┬───────────┘
                                                       │  merge
                                                       ▼
         ┌────────────────────────────────────────────────────┐
         │              WordPress Site                         │
         │  ┌──────────────┐  ┌─────────────┐  ┌───────────┐ │
         │  │ wp_csf_parts │  │ Gutenberg   │  │ REST API  │ │
         │  │ (custom DB)  │  │ Blocks      │  │ /wp-json/ │ │
         │  └──────────────┘  └─────────────┘  └───────────┘ │
         └────────────────────────────────────────────────────┘
```

### Change Detection

The scraper uses a two-tier change detection system:

1. **Hierarchy fingerprint** — MD5 of the full vehicle hierarchy. If nothing changed, the entire scrape is skipped.
2. **Part content hashing** — MD5 of each part's content-relevant fields (excludes volatile fields like `scraped_at` and enrichment-only fields). Detects which specific parts changed between runs.

## Quick Start

### Prerequisites

- **Python 3.13+**
- **uv** — Fast Python package installer ([install](https://github.com/astral-sh/uv))
- **WordPress 6.0+** with DDEV (for the plugin)

### Setup

```bash
git clone https://github.com/zachatkinson/carpart-scraper.git
cd carpart-scraper

uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Install Playwright browser
playwright install chromium
```

### Run a Full Scrape

```bash
# Full pipeline (catalog + details + auto-merge)
python run_scrape.py --catalog --details

# Or run phases separately
python scrape_catalog.py --output-dir exports/
python enrich_details.py
```

See [WORKFLOW.md](WORKFLOW.md) for the complete guide.

## Project Structure

```
carpart-scraper/
├── src/
│   ├── scraper/                # Web scraping logic
│   │   ├── fetcher.py         # Playwright + httpx with retry/rate-limiting
│   │   ├── parser.py          # HTML parsing (application + detail pages)
│   │   ├── orchestrator.py    # Scrape coordination, dedup, checkpoints
│   │   ├── image_processor.py # Image download + AVIF conversion
│   │   ├── ajax_parser.py     # AJAX response parsing
│   │   ├── validator.py       # Part validation
│   │   └── protocols.py       # Protocol definitions
│   ├── models/                 # Pydantic models
│   │   ├── part.py            # Part model
│   │   ├── vehicle.py         # Vehicle model
│   │   └── validators.py      # Shared validators
│   ├── exporters/              # Data export
│   │   └── json_exporter.py   # JSON export with metadata
│   └── cli/                    # Click CLI application
│       ├── main.py
│       └── commands/           # CLI subcommands
├── carpart-scraper-wp/         # WordPress plugin
│   ├── csf-parts-catalog.php  # Main plugin file
│   ├── includes/              # Plugin classes (DB, REST, import, CLI)
│   ├── admin/                 # Admin interface
│   ├── blocks/                # Gutenberg blocks (catalog, single-product)
│   ├── public/                # Frontend assets (CSS, JS, images)
│   └── templates/             # PHP templates
├── tests/
│   ├── unit/                  # 950 unit tests (AAA pattern)
│   └── e2e/                   # End-to-end tests (Playwright)
├── run_scrape.py              # Unified orchestrator
├── scrape_catalog.py          # Phase 1: Catalog scraping
├── enrich_details.py          # Phase 2: Detail enrichment
├── merge_for_import.py        # Merge compatibility into enriched data
├── exports/                   # JSON output (gitignored)
├── checkpoints/               # Resume checkpoints (gitignored)
├── images/                    # Downloaded images (gitignored)
├── WORKFLOW.md                # End-to-end usage guide
├── ARCHITECTURE.md            # Technical architecture
├── PRODUCTION_UPDATE_STRATEGY.md  # Production maintenance guide
└── pyproject.toml             # Project config & dependencies
```

## Development

### Code Quality

```bash
ruff format src/           # Format
ruff check src/            # Lint
mypy src/                  # Type check
pytest                     # Test
```

All checks run in CI. See [CLAUDE.md](.claude/CLAUDE.md) for the complete coding standards (DRY, SOLID, AAA, WordPress conventions).

### Testing

All tests follow the **AAA (Arrange-Act-Assert)** pattern and are designed to be **flexible, not brittle**.

```bash
pytest                              # Run all tests
pytest tests/unit/ --no-cov -q      # Quick unit tests
pytest --cov=src --cov-report=html  # With coverage report
```

### Performance

- **Throughput**: ~1,200 parts/second (parse, validate, export)
- **Memory**: ~2 KB per part
- **Parser**: ~450 us per part extraction
- **Validator**: ~46 us per part (21,600 parts/sec)

See [docs/PERFORMANCE.md](docs/PERFORMANCE.md) for detailed benchmarks.

## Documentation

| Document | Purpose |
|----------|---------|
| [CLAUDE.md](.claude/CLAUDE.md) | Coding standards (DRY, SOLID, AAA, WordPress) |
| [WORKFLOW.md](WORKFLOW.md) | End-to-end usage guide |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Technical architecture and DRY principles |
| [PRODUCTION_UPDATE_STRATEGY.md](PRODUCTION_UPDATE_STRATEGY.md) | Production maintenance and scheduling |
| [docs/PERFORMANCE.md](docs/PERFORMANCE.md) | Performance benchmarks |

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

**Last Updated**: 2026-03-04
