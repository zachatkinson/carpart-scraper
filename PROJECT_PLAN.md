# CSF MyCarParts Scraper & WordPress Integration - Project Plan

## Table of Contents

- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Development Phases](#development-phases)
  - [Phase 1: Project Foundation & Documentation](#phase-1-project-foundation--documentation)
  - [Phase 2: Web Scraper Development](#phase-2-web-scraper-development)
  - [Phase 3: Testing & Quality Assurance](#phase-3-testing--quality-assurance)
  - [Phase 4: WordPress Plugin](#phase-4-wordpress-plugin)
- [Success Criteria](#success-criteria)
- [Code Quality Principles](#code-quality-principles)
- [Risk Mitigation](#risk-mitigation)

## Project Overview

This project consists of two main components:

1. **Python Web Scraper**: Extracts all automotive parts data from csf.mycarparts.com
2. **WordPress Plugin**: Displays scraped parts data natively in a WordPress installation

The scraper will be developed first with CLI tools for testing and validation. Once data extraction is stable and normalized, it will export to JSON format. The WordPress plugin will then import this data into WordPress's native MySQL database using Custom Post Types and Taxonomies.

### Goals

- Extract complete product information (names, SKUs, prices, descriptions, images, specs, categories, vehicle compatibility)
- Provide clean, normalized data through JSON exports
- Enable WordPress integration for seamless parts catalog display using native WP features
- Demonstrate industry-leading adherence to DRY, SOLID, and AAA principles
- Practice respectful web scraping with appropriate rate limiting and delays

## Architecture

### Simplified, WordPress-Focused Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CSF MyCarParts Website                    │
│              (JavaScript-heavy, AJAX endpoints)              │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          │ Respectful scraping (1-3s delays)
                          │ Runs on schedule (daily/weekly)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  Python Scraper (Scheduled)                  │
│  ┌────────────┐  ┌──────────┐  ┌─────────────────────┐     │
│  │  Fetcher   │─▶│  Parser  │─▶│  Data Validator     │     │
│  │ (httpx +   │  │(BS4/lxml)│  │   (Pydantic)        │     │
│  │ Playwright)│  │          │  │                     │     │
│  └────────────┘  └──────────┘  └──────────┬──────────┘     │
│                                           │                  │
│                                           ▼                  │
│                                  ┌─────────────────┐        │
│                                  │ JSON Exporter   │        │
│                                  └────────┬────────┘        │
└───────────────────────────────────────────┼─────────────────┘
                                            │
                                            ▼
                                   ┌────────────────┐
                                   │  parts.json    │
                                   │  images.json   │
                                   │  vehicles.json │
                                   └────────┬───────┘
                                            │
                                            │ Import via WP-Cron
                                            │ or manual trigger
                                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      WordPress Site                          │
│  ┌──────────────┐  ┌───────────────┐  ┌────────────────┐   │
│  │ JSON Importer│  │  Custom Post  │  │   Taxonomies   │   │
│  │              │─▶│  Type: Parts  │  │  (Categories,  │   │
│  │              │  │               │  │  Makes, Models)│   │
│  └──────────────┘  └───────┬───────┘  └────────┬───────┘   │
│                            │                    │            │
│                            ▼                    ▼            │
│                    ┌──────────────────────────────┐         │
│                    │   WordPress MySQL Database   │         │
│                    └──────────────┬───────────────┘         │
│                                   │                          │
│                                   ▼                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Frontend Display                                    │   │
│  │  • WP Templates/Shortcodes                          │   │
│  │  • Native WP Search                                 │   │
│  │  • Category/Taxonomy Filtering                      │   │
│  │  • Part Detail Pages                                │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Workflow

1. **Scraper runs on schedule** (cron job - daily/weekly)
2. **Fetches parts data** from CSF with respectful delays (1-3 seconds between requests)
3. **Validates and normalizes** data using Pydantic models
4. **Exports to JSON files** (parts.json, images.json, vehicles.json)
5. **WordPress plugin imports** JSON via WP-Cron or manual trigger
6. **Data stored in WP** as Custom Post Types with taxonomies
7. **Users browse parts** using native WordPress search and filtering

## Technology Stack

### Python Scraper

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Language** | Python 3.13+ | Core development language |
| **Scraping** | Playwright, BeautifulSoup4, httpx | Handle JS-heavy site, parse HTML, HTTP client |
| **Data Validation** | Pydantic v2 | Type-safe data models and validation |
| **Data Export** | JSON (built-in) | Export validated data for WordPress import |
| **Testing** | pytest, pytest-cov, pytest-mock, pytest-asyncio | Test framework and plugins |
| **Code Quality** | ruff, mypy | Linting, formatting, type checking |
| **CLI** | Click, Rich | Command-line interface with beautiful output |
| **Package Management** | uv | Fast Python package installer |
| **Rate Limiting** | tenacity | Retry logic and respectful delays |
| **Logging** | structlog | Structured logging for monitoring |

### WordPress Plugin (Phase 3)

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend** | PHP 8.1+ | WordPress plugin core |
| **Frontend** | JavaScript (Vanilla or React) | Interactive UI components |
| **Data Storage** | WordPress MySQL (native) | Custom Post Types and taxonomies |
| **Import** | WP-Cron | Scheduled JSON imports |
| **Testing** | PHPUnit, Jest | PHP and JS testing |
| **Search** | WordPress native search | Built-in WP search with custom fields |

## Development Phases

### Phase 1: Project Foundation & Documentation

**Status**: ✅ Complete

#### Tasks

- ✅ Create project structure
- ✅ Initialize git repository
- ✅ Create `.claude/CLAUDE.md` with comprehensive DRY/SOLID/AAA rules
- ✅ Create `PROJECT_PLAN.md` (this file)
- ✅ Create `README.md` with badges and TOC
- ✅ Create `.gitignore`
- ✅ Configure `pyproject.toml` with all dependencies
- ✅ Set up development environment (install dependencies)

#### Deliverables

- ✅ Industry-leading CLAUDE.md ruleset with flexible testing guidelines
- ✅ Complete project documentation
- ✅ Comprehensive gitignore
- ✅ Development environment ready with all dependencies installed

### Phase 2: Web Scraper Development

**Status**: ✅ Complete with Intelligent Scraping (2025-10-28)

#### 2.1 Reconnaissance & Respectful Scraping Strategy

**Status**: ✅ Complete

**Tasks**:
- ✅ Analyze csf.mycarparts.com structure
- ✅ Reverse-engineer AJAX endpoints (`remote:/get_year_by_make/[ID]`)
- ✅ Map vehicle hierarchy:
  - Website navigation: Make → Year → Model (how user selects)
  - Data organization: Year → Make → Model → Part (logical hierarchy, general to specific)
- ✅ Document part data structure and fields
- ✅ Verify robots.txt compliance (no restrictions found)
- ✅ Design respectful scraping implementation:
  - ✅ 1-3 second random delays between requests
  - ✅ Polite user-agent with contact information
  - ✅ Exponential backoff on errors
  - ✅ Respect rate limiting headers
  - ✅ Off-peak scheduling recommendations
- ✅ Create scraper architecture diagram

**Deliverables**:
- ✅ `RECONNAISSANCE.md` - Complete site analysis with URL patterns, selectors, data structures
- ✅ `SCRAPING_STRATEGY.md` - Comprehensive strategy with request estimates, timeline, deduplication approach
- ✅ `prototype_scraper.py` - Validated prototype (Honda only, 12 parts, 50% dedup rate)

**Key Findings**:
- Application pages return JavaScript, **MUST use Playwright** (not httpx)
- AJAX endpoints return jQuery code (not JSON) - need custom parser
- 51 makes → ~1,530 year/make combos → ~3,861 total requests estimated
- Part naming: `category` field = `{part_type}` for WordPress display titles

#### 2.2 Core Scraper Implementation (DRY/SOLID)

**Status**: ✅ Complete (2025-10-28)

**Tasks**:
- ✅ Create abstract base classes for scrapers (protocols in `protocols.py`)
- ✅ Implement HTTP client with retry logic and rate limiting (`RespectfulFetcher`)
- ✅ Build Playwright integration for JS-rendered content (in `fetcher.py`)
- ✅ Create parser classes for different data types (HTMLParser and CSFParser in `parser.py`)
- ✅ Implement data extraction (refactored with real selectors):
  - ✅ Vehicle makes/models/years (validated in prototype)
  - ✅ Part categories (validated in prototype)
  - ✅ Part details - SKU, category, images, features (validated in prototype)
  - ✅ Part specifications (detail pages: 25+ tables with 7-step normalization strategy)
  - ✅ Full part description (detail pages: h5 element - "1 Row Plastic Tank Aluminum Core")
  - ✅ Tech notes (detail pages: embedded in specification tables as "Tech Note" key)
  - ✅ Interchange data (detail pages: OEM/Partslink/DPI reference numbers table)
  - ✅ Vehicle compatibility data (deduplication validated in prototype)
- ✅ Build validator classes for data quality (DataValidator in `validator.py`)
- ✅ Implement error handling and logging (structlog in `fetcher.py`)

**Refactoring Completed** ✅ (2025-10-28):
- ✅ Create `AJAXResponseParser` class to parse jQuery responses (`src/scraper/ajax_parser.py`)
- ✅ Update `CSFParser` with actual selectors from reconnaissance (all TODO selectors replaced)
- ✅ Add Playwright support for application page rendering (validated in prototype)
- ✅ Update models to match discovered data structure (see Model Updates below)
- ✅ Create detail page prototype (`detail_page_prototype.py`) and validate extraction on 5 parts
- ✅ Implement detail page extraction methods in `CSFParser`:
  - ✅ `extract_detail_page_data()` - main entry point
  - ✅ `_extract_detail_specifications()` - table normalization (handles 4 table formats)
  - ✅ `_extract_spec_from_row()` - helper for row-by-row processing
  - ✅ `_extract_full_description()` - extract optional h5 descriptions
  - ✅ `_extract_tech_notes()` - extract from specification dict
  - ✅ `_extract_interchange_data()` - extract OEM/Partslink references
- ✅ Document findings in `RECONNAISSANCE.md` with comprehensive table format analysis

**SOLID Principles Applied**:
- **Single Responsibility**: Separate classes for HTTP, parsing, validation
- **Open/Closed**: Plugin architecture for new part categories
- **Liskov Substitution**: Abstract base scrapers with interchangeable implementations
- **Interface Segregation**: Focused interfaces (IFetcher, IParser, IValidator)
- **Dependency Inversion**: Constructor injection of dependencies

#### 2.3 Data Models & Validation

**Status**: ✅ Complete (Minor updates needed)

**Tasks**:
- ✅ Create Pydantic models for:
  - ✅ Vehicle (Make, Model, Year) in `models/vehicle.py`
  - ✅ Part (SKU, Name, Price, Description, Specs) in `models/part.py`
  - ✅ PartImage in `models/part.py`
  - ✅ VehicleCompatibility in `models/vehicle.py`
- ✅ Implement data normalization utilities (built into Pydantic validators)
- ✅ Create JSON export functionality (JSONExporter in `exporters/json_exporter.py`):
  - ✅ JSON exporter with pretty printing
  - ✅ Incremental export support - `export_parts_incremental()` and `export_compatibility_incremental()`
  - ✅ Append mode for memory-efficient large-scale scraping
  - ✅ Export validation (ensure JSON is valid for WP import)
- ✅ Add data validation and cleaning pipelines (Pydantic field validators)

**Model Updates Completed** ✅ (2025-10-27):
- ✅ `Part` model: Make `price` optional (not displayed on site) - `price: Decimal | None`
- ✅ `Part` model: Add `features: list[str]` field - for product highlights
- ✅ `Part` model: Add `tech_notes: str | None` field - for technical notes
- ✅ `Part` model: Add `position: str | None` field - for part location (e.g., 'Front', 'Rear')
- ✅ `Vehicle` model: Add `engine: str | None` field - engine specification
- ✅ `Vehicle` model: Add `fuel_type: str | None` field - fuel type
- ✅ `Vehicle` model: Add `aspiration: str | None` field - engine aspiration
- ✅ `DataValidator`: Updated to handle all new optional fields with proper preprocessing

#### 2.4 CLI Tool

**Status**: ✅ Complete (2025-10-28)

**Tasks Completed**:
- ✅ Create Click-based CLI application with Rich output
- ✅ Implement commands:
  - ✅ `scrape` - Run scraper with filtering options (make, year, incremental mode, delay override)
  - ✅ `validate` - Validate scraped data with beautiful error reports
  - ✅ `export` - Export data to JSON (flat or hierarchical formats)
  - ✅ `stats` - Show comprehensive statistics with category/vehicle breakdowns
  - ✅ `test-endpoint` - Test application/detail/AJAX endpoints with response details
- ✅ Add Rich progress bars with ETA, spinners, and status messages
- ✅ Implement YAML configuration file support with Pydantic validation

**Implementation Details**:
- **Files Created**: 12 total (5 commands, 4 utilities, 3 supporting modules)
  - `src/cli/main.py` - Main CLI entry point with Click groups
  - `src/cli/config.py` - YAML configuration with Pydantic validation
  - `src/cli/progress.py` - Reusable Rich progress components
  - `src/cli/validators.py` - Data validation service
  - `src/cli/commands/scrape.py` - Scraping command with ScraperOrchestrator
  - `src/cli/commands/validate.py` - Validation command with rich tables
  - `src/cli/commands/export.py` - Export command with format options
  - `src/cli/commands/stats.py` - Statistics command with breakdowns
  - `src/cli/commands/test_endpoint.py` - Endpoint testing command
  - `src/scraper/orchestrator.py` - Scraping workflow coordinator
  - `src/utils/stats_analyzer.py` - Statistics analysis utility
  - `config.example.yaml` - Complete configuration template

- **Quality Metrics**: All files pass with **0 errors, 0 warnings**
  - ✅ ruff format: All files properly formatted
  - ✅ ruff check: Zero linting errors or warnings
  - ✅ mypy: Full type safety in strict mode

- **Key Features**:
  - Beautiful Rich terminal UI with tables, progress bars, spinners
  - Context managers for clean resource management
  - Comprehensive error handling with helpful messages
  - SOLID principles (SRP, OCP, DIP) throughout
  - DRY - No code duplication, reusable components
  - Full type safety with 100% type hint coverage
  - Google-style docstrings on all public APIs
  - Configuration file support with CLI overrides

#### 2.5 Full Orchestration & Intelligent Scraping

**Status**: ✅ Complete (2025-10-28)

**Tasks**:
- ✅ Implement complete scraping orchestration workflow:
  - ✅ Hierarchy enumeration (makes → years → models → application IDs)
  - ✅ Application page scraping with Playwright
  - ✅ SKU-based deduplication with last-write-wins strategy
  - ✅ Detail page fetching for unique parts
  - ✅ Vehicle compatibility mapping with duplicate prevention
  - ✅ Checkpoint/resume functionality for long-running scrapes
  - ✅ Incremental export support
- ✅ Implement intelligent scraping features:
  - ✅ Hierarchy change detection (MD5 fingerprinting)
  - ✅ Conditional detail fetching (new SKUs only vs all SKUs)
  - ✅ Skip scraping when catalog unchanged
  - ✅ Timestamp tracking on parts and compatibility
- ✅ Add parser method `extract_parts_from_application_page()`
- ✅ Create test script `test_hierarchy.py` (validated Honda: 333 configs, 38 years)

**Intelligent Scraping Impact**:
- **Before**: 119,000 requests/week, 63 hours/week, no intelligence
- **After**: ~90,000 requests/week, ~22 hours/week, skip when no changes
- **Reduction**: 65% less scraping time, 24% fewer requests
- **Strategy**: Daily quick checks + weekly deep scrapes

**Workflow Example**:
```python
# Daily intelligent scrape (Mon-Sat)
stats = orchestrator.scrape_all(
    check_changes=True,           # 5-min hierarchy check
    fetch_details_new_only=True,  # Only fetch new SKU details
    checkpoint_interval=50
)
# Takes 5 min if unchanged, ~4 hours if changed

# Weekly deep scrape (Sunday)
stats = orchestrator.scrape_all(
    check_changes=False,           # Force full scrape
    fetch_details_new_only=False,  # Re-fetch all details
)
# Takes ~9 hours, refreshes all data
```

**Key Features**:
- Last-write-wins: Always updates parts with latest data
- Vehicle deduplication: Prevents duplicate compatibility entries
- Fingerprinting: MD5 hash of hierarchy to detect changes
- Timestamps: `scraped_at` field on parts and compatibility
- Smart fetching: Fetch details only for new SKUs (daily) or all (weekly)
- Respectful: 65% reduction in server load

### Phase 3: Testing & Quality Assurance

**Status**: ✅ Complete (2025-10-28)

#### 3.1 Comprehensive Test Suite (AAA Pattern)

**Status**: ✅ Complete (2025-10-28)

**Results**:
- ✅ **806 tests created** (100% passing)
- ✅ **85.40% overall coverage** (14 modules with >90% coverage)
- ✅ **Zero quality issues** (ruff, mypy clean)
- ✅ **Fast execution** (12-19 seconds for full suite)

**Tasks**:
- ✅ Create test data factories/fixtures (570+ lines in conftest.py)
- ✅ Write unit tests (target: >90% coverage):
  - ✅ Scraper components (fetcher: 94.87%, parser: 94.85%, validator: 90.48%)
  - ✅ Data validators and normalizers (90.48% coverage)
  - ✅ Pydantic models (100% coverage)
  - ✅ JSON exporters (84% coverage)
  - ✅ CLI commands (90-100% coverage on all 5 commands)
- ✅ Write integration tests:
  - ✅ End-to-end scraping workflow (27 integration tests)
  - ✅ JSON export/import cycle
  - ✅ Error handling and retry logic
- ⚪ Write performance tests (deferred to Phase 3.3):
  - ⚪ Scraper throughput (parts per minute)
  - ⚪ Memory usage during large scrapes
- ✅ All tests follow AAA pattern:
  - **Arrange**: Set up test data and dependencies
  - **Act**: Execute single action under test
  - **Assert**: Verify expected outcomes
- ✅ Tests are flexible, not brittle (test behavior, not implementation)

**Coverage Details**:
- 🏆 Perfect coverage (100%): Models, AJAX parser, scrape command
- 📊 Excellent coverage (>95%): Validate command (99.36%), orchestrator (96.61%), progress (96.24%)
- ✨ High coverage (90-95%): Parser, fetcher, config, stats, validator, export command
- ⚠️ Below target (<90%): JSON exporter (84%), CLI validators (83.55%), main entry (35.14%)

#### 3.2 Code Quality Gates

**Status**: ✅ Complete (2025-10-28)

**Results**:
- ✅ **Pre-commit hooks** installed and tested (all passing)
- ✅ **GitHub Actions CI/CD** workflow created with matrix testing
- ✅ **README badges** updated with actual coverage and test metrics

**Tasks**:
- ✅ Configure ruff for linting and formatting (pyproject.toml)
- ✅ Set up mypy for strict type checking (pyproject.toml)
- ✅ Generate coverage reports (HTML + XML + terminal)
- ✅ Create pre-commit hooks (.pre-commit-config.yaml):
  - ✅ Run ruff format/check
  - ✅ Run mypy
  - ✅ Run pytest (fast on commit, full coverage on push)
  - ✅ Check for large files (>1MB)
  - ✅ Detect private keys and secrets
  - ✅ File hygiene (trailing whitespace, EOF, line endings)
- ✅ Set up GitHub Actions CI/CD (.github/workflows/ci.yml):
  - ✅ Matrix testing (Python 3.11, 3.12, 3.13)
  - ✅ Lint and type check jobs
  - ✅ Security checks (safety, bandit)
  - ✅ Codecov integration
- ✅ Add badges to README:
  - ✅ CI status badge
  - ✅ Codecov coverage badge
  - ✅ Pre-commit badge
  - ✅ Updated test count (806 passing)
  - ✅ Updated coverage (85.40%)

#### 3.3 Performance Testing (Optional)

**Status**: ✅ Complete (2025-10-28)

**Results**:
- ✅ **15 performance benchmarks** created using pytest-benchmark
- ✅ **5 memory profiling tests** with tracemalloc
- ✅ **Comprehensive baseline documentation** (docs/PERFORMANCE.md)
- ✅ **Performance highlights**:
  - Throughput: ~1,200 parts/second (full pipeline)
  - Memory: 2.11 KB per part (20 MB for 10,000 parts)
  - Parser: 447 μs per part extraction
  - Validator: 46 μs per part (21,600 parts/sec)

**Tasks**:
- ✅ Benchmark scraper throughput (parts per minute)
  - ✅ Parser benchmarks (HTML parse, CSF extraction, text extraction)
  - ✅ Validator benchmarks (single + batch validation)
  - ✅ Model instantiation benchmarks (Part, Vehicle, Compatibility)
  - ✅ Workflow benchmarks (parse→validate, validate→export)
- ✅ Memory profiling during large scrapes
  - ✅ 10,000 parts in memory (20.62 MB peak)
  - ✅ 5,000 parts export (4.16 MB peak)
  - ✅ 10,000 parts incremental export (12.21 MB peak)
  - ✅ Parser operations (1.13 MB peak for 100 parts)
  - ✅ Vehicle compatibility (7.18 MB for 10,000 vehicles)
- ✅ Document baseline performance metrics (docs/PERFORMANCE.md)
- ✅ Add performance testing to README with highlights

### Phase 4: WordPress Plugin

**Status**: ⚪ Not Started

#### 4.1 Plugin Foundation

**Tasks**:
- [ ] Create WordPress plugin structure (following WP coding standards)
- [ ] Register custom post types for "Parts"
- [ ] Create taxonomies:
  - [ ] Part categories (Radiators, Condensers, etc.)
  - [ ] Vehicle makes
  - [ ] Vehicle models
  - [ ] Vehicle years
- [ ] Set up plugin settings/admin page

#### 4.2 JSON Import System

**Tasks**:
- [ ] Implement JSON file uploader (via admin interface)
- [ ] Create JSON parser and validator
- [ ] Build import mechanism:
  - [ ] Parse JSON and create WP posts
  - [ ] Assign taxonomies (categories, makes, models, years)
  - [ ] Handle custom fields/meta data
  - [ ] Import and attach images
  - [ ] Track import history (avoid duplicates)
- [ ] Add WP-Cron scheduled import (optional automation)
- [ ] Implement progress tracking and error logging
- [ ] Add rollback functionality (undo imports)

#### 4.3 Frontend Features

**Tasks**:
- [ ] Create part archive/catalog template
- [ ] Build single part detail page template
- [ ] Implement search functionality (leverage WP native search)
- [ ] Add filtering by:
  - [ ] Category
  - [ ] Make/Model/Year
  - [ ] Price range
  - [ ] Keyword search
- [ ] Create shortcodes for embedding parts
- [ ] Add vehicle compatibility checker widget
- [ ] Implement image galleries for parts
- [ ] Build responsive design (mobile-friendly)

#### 4.4 WordPress Testing

**Tasks**:
- [ ] Write PHPUnit tests for import logic
- [ ] Write Jest tests for JavaScript components
- [ ] Test WordPress compatibility (WP 6.0+)
- [ ] Test with common themes (Astra, GeneratePress, etc.)
- [ ] Performance testing with hundreds of parts
- [ ] Test multisite compatibility (if needed)

## Success Criteria

### Technical Excellence

- [ ] **Code Coverage**: >90% test coverage across all modules
- [ ] **Type Safety**: 100% type hints, passing mypy strict mode
- [ ] **Code Quality**: Ruff linting score 10/10, zero warnings
- [ ] **Documentation**: Every public function/class has docstrings
- [ ] **DRY Compliance**: No code duplication (max 3% similarity)
- [ ] **Respectful Scraping**: 1-3 second delays, polite user-agent

### Functional Requirements

- [ ] **Complete Data Extraction**: All parts from csf.mycarparts.com scraped successfully
- [ ] **Data Accuracy**: >99% accuracy in scraped vs source data
- [ ] **Clean JSON Export**: Valid, well-structured JSON for WordPress import
- [ ] **WordPress Integration**: Seamless display of parts in WP using Custom Post Types
- [ ] **Search Performance**: WordPress search returns results <200ms
- [ ] **Import Reliability**: JSON import completes without errors, handles duplicates

### Non-Functional Requirements

- [ ] **Scalability**: Handle hundreds to thousands of parts without performance issues
- [ ] **Maintainability**: New developers can contribute within 1 day (thanks to CLAUDE.md)
- [ ] **Observability**: Comprehensive logging and monitoring during scraping
- [ ] **Security**: No exposed credentials in code or config files

## Code Quality Principles

### DRY (Don't Repeat Yourself)

- Extract repeated logic into shared utilities
- Use configuration files instead of hardcoded values
- Create reusable components and mixins
- Leverage inheritance and composition appropriately

### SOLID Principles

#### Single Responsibility Principle
- Each class/function does one thing well
- Separation of concerns across modules

#### Open/Closed Principle
- Classes open for extension, closed for modification
- Use abstract base classes and protocols
- Plugin architecture for extensibility

#### Liskov Substitution Principle
- Subtypes must be substitutable for base types
- Consistent interfaces across implementations

#### Interface Segregation Principle
- Small, focused interfaces over large, monolithic ones
- Clients depend only on methods they use

#### Dependency Inversion Principle
- Depend on abstractions, not concrete implementations
- Use dependency injection throughout

### AAA Testing Pattern

All tests must follow:

1. **Arrange**: Set up test data, mocks, and preconditions
2. **Act**: Execute the single operation under test
3. **Assert**: Verify the expected outcome(s)

### Code Quality Enforcement (Added 2025-10-27)

**Three-Step Quality Process** - ALL code changes must pass:

1. **Format** (`ruff format src/`) - Auto-formats code to consistent style
2. **Lint** (`ruff check src/`) - Must have **ZERO errors, ZERO warnings**
3. **Type Check** (`mypy src/`) - Must have **ZERO type errors**

**Philosophy**: Suppressions (`# noqa`, `# type: ignore`) are technical debt and should be an **absolute last resort**. We fix issues properly to best practices - we never rely on ignoring or disabling as a crutch.

**Legitimate Suppressions** (documented in CLAUDE.md):
- `ARG002`: Unused method arguments in template methods/interface implementations
- `S311`: Non-cryptographic random use (delays, sampling - NOT for security)

See `.claude/CLAUDE.md` "Code Quality and Linting" section for full guidelines.

Example:
```python
def test_part_validator_rejects_invalid_sku():
    # Arrange
    invalid_part = Part(sku="", name="Test Part", price=10.00)
    validator = PartValidator()

    # Act
    result = validator.validate(invalid_part)

    # Assert
    assert result.is_valid is False
    assert "sku" in result.errors
```

## Risk Mitigation

| Risk | Impact | Mitigation Strategy |
|------|--------|---------------------|
| Website structure changes | High | Abstract scraping logic, comprehensive tests, version tracking |
| Rate limiting/blocking | Medium | Respectful delays (1-3s), retry logic, polite user-agent |
| Data quality issues | Medium | Comprehensive Pydantic validation, manual spot-checks |
| WordPress import failures | Medium | Validation before import, rollback functionality, logging |
| WordPress compatibility | Low | Test against multiple WP versions, follow WP coding standards |
| Scope creep | Medium | Clear phase boundaries, focus on core functionality first |
| Scraper performance | Low | Async operations where possible, progress monitoring |

## Timeline & Milestones

| Milestone | Target | Status |
|-----------|--------|--------|
| **M1**: Documentation Complete | Week 1 | ✅ Complete |
| **M1.5**: Reconnaissance & Prototype | Week 2 | ✅ Complete |
| **M2**: Scraper MVP (basic data extraction) | Week 2-3 | ✅ Complete |
| **M3**: Complete Scraper (all data + JSON export) | Week 4-5 | ✅ Complete |
| **M4**: Testing & Quality Gates | Week 6 | ✅ Complete |
| **M5**: WordPress Plugin MVP | Week 7-8 | ⚪ Not Started |
| **M6**: WordPress Plugin Complete | Week 9-10 | ⚪ Not Started |
| **M7**: Production Ready | Week 11 | ⚪ Not Started |

---

**Last Updated**: 2025-10-28
**Status**: Phase 3 Complete ✅ - Testing & Quality Assurance (806 tests, 85.40% coverage, performance benchmarked)

**Completed in Session 1** (Detail Pages):
1. ✅ Detail page prototype created and validated on 5 parts
2. ✅ Complex table normalization implemented (4 formats, 7-step strategy, 33% improvement)
3. ✅ CSFParser updated with 6 new detail page extraction methods
4. ✅ Incremental export support added to JSONExporter
5. ✅ All code passes quality checks: 0 errors, 0 warnings, 0 type issues

**Completed in Session 2** (CLI Tool):
1. ✅ Complete CLI application with 5 commands (scrape, validate, export, stats, test-endpoint)
2. ✅ Rich progress bars, spinners, tables, and status messages
3. ✅ YAML configuration file support with Pydantic validation
4. ✅ ScraperOrchestrator for workflow coordination
5. ✅ Statistics analyzer with category/vehicle breakdowns

**Completed in Session 3** (Comprehensive Test Suite):
1. ✅ 806 comprehensive tests created (100% passing)
2. ✅ 85.40% overall code coverage (14 modules with >90% coverage)
3. ✅ Perfect coverage (100%) on models, AJAX parser, scrape command
4. ✅ Integration tests for end-to-end workflows (27 tests)
5. ✅ All tests follow AAA pattern with zero quality issues
6. ✅ Pytest configuration with HTML/XML/terminal coverage reports
7. ✅ Fast test execution (12-19 seconds for full suite)

**Completed in Session 4** (Code Quality Gates):
1. ✅ Pre-commit hooks configured and tested (14 hooks, all passing)
2. ✅ GitHub Actions CI/CD with matrix testing (Python 3.11-3.13)
3. ✅ README badges updated (CI, coverage, pre-commit, tests)
4. ✅ Security checks integrated (private key detection, large file checks)
5. ✅ Automated quality gates (ruff, mypy, pytest on every commit)

**Completed in Session 5** (Performance Testing):
1. ✅ 15 performance benchmarks created using pytest-benchmark
2. ✅ 5 memory profiling tests with tracemalloc
3. ✅ Comprehensive baseline documentation (docs/PERFORMANCE.md)
4. ✅ Performance highlights documented (~1,200 parts/sec throughput, 2.11 KB/part memory)
5. ✅ README updated with performance testing section
6. ✅ pytest.ini updated with memory marker
7. ✅ Phase 3.3 marked complete (all Phase 3 tasks now complete)

**Completed in Session 6** (Full Orchestration & Intelligent Scraping):
1. ✅ Complete scraper orchestration workflow implemented
2. ✅ Hierarchy enumeration tested (Honda: 333 configs, 38 years)
3. ✅ Intelligent change detection with MD5 fingerprinting
4. ✅ Vehicle deduplication and last-write-wins strategy
5. ✅ Timestamp tracking on parts and compatibility
6. ✅ Conditional detail fetching (new SKUs only vs all)
7. ✅ 65% reduction in scraping time (63 → 22 hours/week)
8. ✅ 24% reduction in requests (119K → 90K requests/week)

**Next Steps**:
1. ⚪ Test full workflow with small dataset (Honda 2020)
2. ⚪ Test checkpoint/resume with interruption
3. ⚪ Begin Phase 4: WordPress Plugin development
