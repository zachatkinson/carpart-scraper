# CSF MyCarParts Scraper - Development Guidelines

## Table of Contents

- [Overview](#overview)
- [Core Principles](#core-principles)
  - [DRY (Don't Repeat Yourself)](#dry-dont-repeat-yourself)
  - [SOLID Principles](#solid-principles)
  - [AAA Testing Pattern](#aaa-testing-pattern)
- [Python Coding Standards](#python-coding-standards)
- [Type Safety](#type-safety)
- [API Design Guidelines](#api-design-guidelines)
- [Testing Standards](#testing-standards)
- [Error Handling](#error-handling)
- [Documentation Requirements](#documentation-requirements)
- [Anti-Patterns to Avoid](#anti-patterns-to-avoid)

## Overview

This document defines the coding standards and architectural principles for the CSF MyCarParts Scraper project. Every line of code, test, and documentation must adhere to these guidelines to ensure maintainability, scalability, and excellence.

**Guiding Philosophy**: Write code that is self-documenting, testable, and maintainable by anyone on the team within their first day.

## Core Principles

### DRY (Don't Repeat Yourself)

**Definition**: Every piece of knowledge must have a single, unambiguous, authoritative representation within the system.

#### Rules

1. **No Code Duplication**: If you write the same logic twice, extract it into a function/class
2. **Configuration Over Code**: Use config files instead of hardcoded values
3. **Shared Utilities**: Common operations belong in utility modules
4. **Template Methods**: Use base classes with template methods for shared workflows

#### Examples

**❌ BAD - Repetitive Code**:
```python
def scrape_radiators():
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception("Failed")
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup.find_all('div', class_='part')

def scrape_condensers():
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception("Failed")
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup.find_all('div', class_='part')
```

**✅ GOOD - DRY Implementation**:
```python
class BaseScraper:
    """Base scraper with shared functionality."""

    def fetch_and_parse(self, url: str) -> BeautifulSoup:
        """Fetch URL and return parsed HTML."""
        response = self._fetch_with_retry(url)
        return BeautifulSoup(response.text, 'html.parser')

    def _fetch_with_retry(self, url: str) -> requests.Response:
        """Fetch URL with error handling."""
        response = requests.get(url)
        if response.status_code != 200:
            raise HTTPException(f"Failed to fetch {url}")
        return response

class RadiatorScraper(BaseScraper):
    def scrape(self) -> list[Part]:
        soup = self.fetch_and_parse(self.url)
        return self._parse_parts(soup)

class CondenserScraper(BaseScraper):
    def scrape(self) -> list[Part]:
        soup = self.fetch_and_parse(self.url)
        return self._parse_parts(soup)
```

#### Configuration Management

**❌ BAD - Hardcoded Values**:
```python
def connect_to_db():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="carparts",
        user="admin"
    )
```

**✅ GOOD - Configuration-Driven**:
```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_host: str
    db_port: int = 5432
    db_name: str
    db_user: str

    class Config:
        env_file = ".env"

# database.py
def connect_to_db(settings: Settings):
    return psycopg2.connect(
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
        user=settings.db_user
    )
```

### SOLID Principles

#### S - Single Responsibility Principle (SRP)

**Rule**: A class should have only one reason to change.

**❌ BAD - Multiple Responsibilities**:
```python
class PartManager:
    def scrape_part(self, url: str) -> Part:
        """Scrapes, validates, saves, and sends notifications."""
        html = requests.get(url).text
        part = self.parse_html(html)
        if not self.validate_part(part):
            raise ValueError("Invalid part")
        self.save_to_database(part)
        self.send_notification(f"Scraped {part.name}")
        return part
```

**✅ GOOD - Single Responsibility**:
```python
class PartScraper:
    """Responsible only for scraping."""
    def scrape(self, url: str) -> dict:
        html = requests.get(url).text
        return self.parse_html(html)

class PartValidator:
    """Responsible only for validation."""
    def validate(self, part_data: dict) -> Part:
        if not part_data.get('sku'):
            raise ValidationError("SKU required")
        return Part(**part_data)

class PartRepository:
    """Responsible only for persistence."""
    def save(self, part: Part) -> None:
        self.db.add(part)
        self.db.commit()

class NotificationService:
    """Responsible only for notifications."""
    def notify_scraped(self, part: Part) -> None:
        self.send(f"Scraped {part.name}")
```

#### O - Open/Closed Principle (OCP)

**Rule**: Software entities should be open for extension but closed for modification.

**❌ BAD - Modification Required**:
```python
class DataExporter:
    def export(self, data: list[Part], format: str) -> None:
        if format == "json":
            self._export_json(data)
        elif format == "csv":
            self._export_csv(data)
        elif format == "xml":  # Need to modify class for new format
            self._export_xml(data)
```

**✅ GOOD - Extension Without Modification**:
```python
from abc import ABC, abstractmethod

class Exporter(ABC):
    """Abstract exporter interface."""
    @abstractmethod
    def export(self, data: list[Part], path: Path) -> None:
        pass

class JSONExporter(Exporter):
    def export(self, data: list[Part], path: Path) -> None:
        with open(path, 'w') as f:
            json.dump([p.model_dump() for p in data], f)

class CSVExporter(Exporter):
    def export(self, data: list[Part], path: Path) -> None:
        # CSV export logic
        pass

class XMLExporter(Exporter):  # New format without modifying existing code
    def export(self, data: list[Part], path: Path) -> None:
        # XML export logic
        pass

class DataExporter:
    def __init__(self, exporter: Exporter):
        self.exporter = exporter

    def export(self, data: list[Part], path: Path) -> None:
        self.exporter.export(data, path)
```

#### L - Liskov Substitution Principle (LSP)

**Rule**: Subtypes must be substitutable for their base types without altering correctness.

**❌ BAD - Violates LSP**:
```python
class Scraper:
    def scrape(self, url: str) -> list[Part]:
        return [Part(...)]

class BrokenScraper(Scraper):
    def scrape(self, url: str) -> None:  # Returns None instead of list!
        print("Scraping...")
        # Doesn't return anything
```

**✅ GOOD - Honors LSP**:
```python
class Scraper(ABC):
    @abstractmethod
    def scrape(self, url: str) -> list[Part]:
        """Scrape parts from URL."""
        pass

class RadiatorScraper(Scraper):
    def scrape(self, url: str) -> list[Part]:
        # Always returns list[Part] as promised
        return [self._parse_radiator(html)]

class CondenserScraper(Scraper):
    def scrape(self, url: str) -> list[Part]:
        # Always returns list[Part] as promised
        return [self._parse_condenser(html)]

def scrape_all(scrapers: list[Scraper]) -> list[Part]:
    """Works with any Scraper subtype."""
    parts = []
    for scraper in scrapers:
        parts.extend(scraper.scrape(url))  # LSP: all scrapers work the same way
    return parts
```

#### I - Interface Segregation Principle (ISP)

**Rule**: Clients should not depend on interfaces they don't use.

**❌ BAD - Fat Interface**:
```python
class DataProcessor(ABC):
    @abstractmethod
    def fetch(self) -> dict: pass

    @abstractmethod
    def parse(self, data: dict) -> Part: pass

    @abstractmethod
    def validate(self, part: Part) -> bool: pass

    @abstractmethod
    def save(self, part: Part) -> None: pass

    @abstractmethod
    def notify(self, part: Part) -> None: pass

# Client only needs parsing, but must implement everything
class SimpleParser(DataProcessor):
    def parse(self, data: dict) -> Part:
        return Part(**data)

    def fetch(self) -> dict:
        raise NotImplementedError  # Don't need this!

    def validate(self, part: Part) -> bool:
        raise NotImplementedError  # Don't need this!

    # ... etc
```

**✅ GOOD - Segregated Interfaces**:
```python
class Fetcher(Protocol):
    def fetch(self) -> dict: ...

class Parser(Protocol):
    def parse(self, data: dict) -> Part: ...

class Validator(Protocol):
    def validate(self, part: Part) -> bool: ...

class Repository(Protocol):
    def save(self, part: Part) -> None: ...

class Notifier(Protocol):
    def notify(self, part: Part) -> None: ...

# Client implements only what it needs
class SimpleParser:
    def parse(self, data: dict) -> Part:
        return Part(**data)

class ComprehensiveValidator:
    def validate(self, part: Part) -> bool:
        return all([part.sku, part.name, part.price > 0])
```

#### D - Dependency Inversion Principle (DIP)

**Rule**: Depend on abstractions, not concretions.

**❌ BAD - Tight Coupling**:
```python
class PostgresRepository:
    def save(self, part: Part) -> None:
        # PostgreSQL specific code
        pass

class PartService:
    def __init__(self):
        self.repo = PostgresRepository()  # Tightly coupled to Postgres!

    def add_part(self, part: Part) -> None:
        self.repo.save(part)
```

**✅ GOOD - Dependency Inversion**:
```python
class PartRepository(ABC):
    """Abstract repository interface."""
    @abstractmethod
    def save(self, part: Part) -> None:
        pass

class PostgresRepository(PartRepository):
    def save(self, part: Part) -> None:
        # PostgreSQL implementation
        pass

class SQLiteRepository(PartRepository):
    def save(self, part: Part) -> None:
        # SQLite implementation
        pass

class PartService:
    def __init__(self, repository: PartRepository):  # Depends on abstraction
        self.repo = repository

    def add_part(self, part: Part) -> None:
        self.repo.save(part)

# Easy to swap implementations
service_postgres = PartService(PostgresRepository())
service_sqlite = PartService(SQLiteRepository())
```

### AAA Testing Pattern

**Rule**: All tests must follow the Arrange-Act-Assert pattern for clarity and consistency.

#### Structure

1. **Arrange**: Set up test data, mocks, and preconditions
2. **Act**: Execute the single operation under test
3. **Assert**: Verify expected outcome(s)

#### Examples

**✅ GOOD - Clear AAA Structure**:
```python
def test_part_validator_accepts_valid_part():
    # Arrange
    valid_part = Part(
        sku="CSF-12345",
        name="High Performance Radiator",
        price=299.99,
        category="Radiators"
    )
    validator = PartValidator()

    # Act
    result = validator.validate(valid_part)

    # Assert
    assert result.is_valid is True
    assert result.errors == []

def test_part_validator_rejects_missing_sku():
    # Arrange
    invalid_part = Part(
        sku="",
        name="Radiator",
        price=100.00
    )
    validator = PartValidator()

    # Act
    result = validator.validate(invalid_part)

    # Assert
    assert result.is_valid is False
    assert "sku" in result.errors
    assert "required" in result.errors["sku"].lower()
```

#### Test Naming Convention

**Format**: `test_<unit>_<scenario>_<expected_result>`

**Examples**:
- `test_scraper_with_valid_html_returns_parts`
- `test_validator_with_negative_price_raises_error`
- `test_api_with_invalid_token_returns_401`

#### Test Data Factories

**✅ Use Factories for Complex Data**:
```python
# conftest.py
import factory

class PartFactory(factory.Factory):
    class Meta:
        model = Part

    sku = factory.Sequence(lambda n: f"CSF-{n:05d}")
    name = "Test Part"
    price = 99.99
    category = "Radiators"

# test_validator.py
def test_validator_with_factory():
    # Arrange
    part = PartFactory(price=-10.00)  # Override specific field
    validator = PartValidator()

    # Act
    result = validator.validate(part)

    # Assert
    assert result.is_valid is False
```

#### Flexible vs Brittle Tests

**Rule**: Write tests that verify behavior, not implementation details. Tests should be resilient to refactoring.

**Characteristics of Flexible (Good) Tests**:
- Test public interfaces, not private methods
- Assert on outcomes, not internal state
- Independent of implementation details
- Survive refactoring without changes
- Focus on "what" not "how"

**Characteristics of Brittle (Bad) Tests**:
- Tightly coupled to implementation
- Break when refactoring without behavior changes
- Test internal private methods directly
- Over-specify assertions
- Hard-coded test data

**❌ BRITTLE - Tests Implementation Details**:
```python
def test_scraper_uses_specific_parser():
    # Arrange
    scraper = PartScraper()

    # Act
    scraper.scrape("https://example.com")

    # Assert - Testing HOW it works, not WHAT it does
    assert scraper._parser is not None
    assert isinstance(scraper._parser, BeautifulSoup)
    assert scraper._parser.features == "html.parser"
    assert scraper._internal_cache == {}
```

**✅ FLEXIBLE - Tests Behavior**:
```python
def test_scraper_extracts_parts_from_page():
    # Arrange
    scraper = PartScraper()
    test_url = "https://example.com/parts"

    # Act
    parts = scraper.scrape(test_url)

    # Assert - Testing WHAT it does, not HOW
    assert len(parts) > 0
    assert all(isinstance(p, Part) for p in parts)
    assert all(p.sku.startswith("CSF-") for p in parts)
```

**❌ BRITTLE - Over-Specification**:
```python
def test_api_returns_parts():
    # Act
    response = client.get("/api/v1/parts")

    # Assert - Too specific about structure
    assert response.json() == {
        "data": [
            {
                "id": 1,
                "sku": "CSF-12345",
                "name": "Radiator",
                "price": "299.99",
                "category": "Radiators",
                "created_at": "2025-01-15T10:30:00Z",
                "updated_at": "2025-01-15T10:30:00Z",
                "metadata": {}
            }
        ],
        "count": 1,
        "page": 1
    }
```

**✅ FLEXIBLE - Tests Contract**:
```python
def test_api_returns_parts():
    # Act
    response = client.get("/api/v1/parts")
    data = response.json()

    # Assert - Tests essential contract, not exact structure
    assert response.status_code == 200
    assert "data" in data
    assert len(data["data"]) > 0

    first_part = data["data"][0]
    assert "sku" in first_part
    assert "name" in first_part
    assert "price" in first_part
    assert first_part["sku"].startswith("CSF-")
```

**❌ BRITTLE - Testing Private Methods**:
```python
def test_validator_internal_sku_check():
    # Arrange
    validator = PartValidator()

    # Act & Assert - Testing private implementation
    assert validator._is_valid_sku_format("CSF-12345") is True
    assert validator._is_valid_sku_format("INVALID") is False
```

**✅ FLEXIBLE - Testing Public Interface**:
```python
def test_validator_accepts_valid_sku():
    # Arrange
    part = Part(sku="CSF-12345", name="Radiator", price=99.99)
    validator = PartValidator()

    # Act
    result = validator.validate(part)

    # Assert - Testing public behavior
    assert result.is_valid is True

def test_validator_rejects_invalid_sku():
    # Arrange
    part = Part(sku="INVALID", name="Radiator", price=99.99)
    validator = PartValidator()

    # Act
    result = validator.validate(part)

    # Assert - Testing public behavior
    assert result.is_valid is False
    assert "sku" in result.errors
```

**Best Practices for Flexible Tests**:

1. **Use Test Builders/Factories**: Avoid hard-coded test data
   ```python
   # Flexible: Tests only care about the field being tested
   part = PartFactory(price=-10.00)  # Price is what matters
   ```

2. **Assert on Behavior, Not Structure**:
   ```python
   # Good: Behavior-focused
   assert len(parts) == expected_count
   assert all(p.price > 0 for p in parts)

   # Bad: Structure-focused
   assert parts[0].id == 1
   assert parts[0].created_at == "2025-01-15T10:30:00Z"
   ```

3. **Test Through Public APIs**:
   ```python
   # Good: Through public interface
   service.add_part(part)
   retrieved = service.get_part(part.sku)
   assert retrieved == part

   # Bad: Accessing internals
   service._repository._cache[part.sku] = part
   assert service._repository._cache[part.sku] == part
   ```

4. **Use Appropriate Assertion Granularity**:
   ```python
   # Good: Specific to test purpose
   assert part.price > 0  # For price validation test
   assert part.sku.startswith("CSF-")  # For SKU format test

   # Bad: Over-asserting
   assert part.price == Decimal("299.99")
   assert part.created_at.year == 2025
   assert part.created_at.month == 1
   # ... when these details don't matter to the test
   ```

5. **Mock External Dependencies, Not Internal Logic**:
   ```python
   # Good: Mock external API
   mock_http_client.get.return_value = mock_response

   # Bad: Mock internal methods
   mocker.patch.object(scraper, '_parse_html')
   ```

## Python Coding Standards

### Code Style

- **Formatter**: Use `ruff format` (replaces Black)
- **Linter**: Use `ruff check` (replaces Flake8, isort, etc.)
- **Line Length**: 100 characters maximum
- **Quotes**: Double quotes for strings
- **Imports**: Absolute imports preferred, grouped (stdlib, third-party, local)

### Import Organization

```python
# Standard library
import os
from pathlib import Path
from typing import Protocol

# Third-party
import httpx
from pydantic import BaseModel

# Local application
from src.models.part import Part
from src.services.validator import PartValidator
```

### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Variables | `snake_case` | `part_count`, `is_valid` |
| Functions | `snake_case` | `fetch_parts()`, `validate_sku()` |
| Classes | `PascalCase` | `PartScraper`, `HTTPClient` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_RETRIES`, `API_BASE_URL` |
| Private | `_leading_underscore` | `_parse_html()`, `_cache` |
| Protocols | `IPascalCase` or `PascalCase` | `IRepository`, `Fetcher` |

### Function Design

**Rules**:
1. Functions should do ONE thing
2. Maximum 20 lines per function (guideline, not hard rule)
3. Maximum 4 parameters (use config objects for more)
4. Return early to avoid deep nesting

**✅ GOOD Example**:
```python
def fetch_part_by_sku(sku: str, client: HTTPClient) -> Part | None:
    """Fetch part by SKU from API.

    Args:
        sku: Part SKU to fetch
        client: HTTP client instance

    Returns:
        Part if found, None otherwise

    Raises:
        ValidationError: If SKU format is invalid
    """
    if not sku:
        raise ValidationError("SKU cannot be empty")

    response = client.get(f"/parts/{sku}")

    if response.status_code == 404:
        return None

    response.raise_for_status()
    return Part(**response.json())
```

## Type Safety

### Type Hints

**Rule**: ALL functions, methods, and classes must have complete type hints.

**✅ Required**:
```python
def calculate_total(parts: list[Part], tax_rate: float = 0.08) -> Decimal:
    """Calculate total price including tax."""
    subtotal = sum(part.price for part in parts)
    return Decimal(subtotal * (1 + tax_rate))

class PartService:
    def __init__(self, repository: PartRepository, cache: Cache) -> None:
        self.repository = repository
        self.cache = cache

    def get_part(self, sku: str) -> Part | None:
        """Retrieve part by SKU."""
        return self.repository.find_by_sku(sku)
```

### Pydantic Models

**Rule**: Use Pydantic for all data validation and serialization.

```python
from pydantic import BaseModel, Field, field_validator
from decimal import Decimal

class Part(BaseModel):
    """Automotive part model."""
    sku: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    price: Decimal = Field(..., gt=0, decimal_places=2)
    category: str
    description: str | None = None

    @field_validator('sku')
    @classmethod
    def validate_sku(cls, v: str) -> str:
        if not v.startswith('CSF-'):
            raise ValueError('SKU must start with CSF-')
        return v.upper()

    model_config = {
        'frozen': True,  # Immutable
        'str_strip_whitespace': True
    }
```

### MyPy Configuration

**Rule**: MyPy must pass in strict mode with zero errors.

```toml
# pyproject.toml
[tool.mypy]
python_version = "3.13"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_any_generics = true
```

## API Design Guidelines

### RESTful Principles

**Rules**:
1. Use nouns for resources, not verbs
2. Use HTTP methods correctly (GET, POST, PUT, PATCH, DELETE)
3. Use proper status codes
4. Version your API (`/api/v1/`)

### Endpoint Structure

```python
from fastapi import APIRouter, HTTPException, Query
from typing import Annotated

router = APIRouter(prefix="/api/v1")

@router.get("/parts", response_model=list[PartResponse])
async def list_parts(
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    category: str | None = None
) -> list[PartResponse]:
    """List parts with pagination and filtering.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        category: Filter by category (optional)

    Returns:
        List of parts matching criteria
    """
    # Implementation
    pass

@router.get("/parts/{sku}", response_model=PartResponse)
async def get_part(sku: str) -> PartResponse:
    """Get part by SKU.

    Args:
        sku: Part SKU

    Returns:
        Part details

    Raises:
        HTTPException: 404 if part not found
    """
    part = await part_service.get_by_sku(sku)
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
    return PartResponse.from_orm(part)
```

### HTTP Status Codes

| Code | Meaning | Use Case |
|------|---------|----------|
| 200 | OK | Successful GET, PUT, PATCH |
| 201 | Created | Successful POST |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Validation error |
| 401 | Unauthorized | Missing/invalid auth |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 422 | Unprocessable Entity | Pydantic validation error |
| 500 | Internal Server Error | Unexpected error |

## Respectful Web Scraping

**Rule**: All web scraping must be conducted ethically and respectfully, minimizing impact on target servers.

### Core Principles

1. **Respect robots.txt**: Always check and honor robots.txt directives
2. **Rate Limiting**: Implement delays between requests to avoid overwhelming servers
3. **Identify Yourself**: Use descriptive user-agents with contact information
4. **Handle Errors Gracefully**: Implement exponential backoff on failures
5. **Off-Peak Scraping**: Schedule intensive scraping during low-traffic periods when possible

### Required Implementation

**✅ REQUIRED Components**:

```python
from typing import Protocol
import time
import random
from tenacity import retry, wait_exponential, stop_after_attempt

class RespectfulFetcher(Protocol):
    """Protocol for respectful HTTP fetching."""

    # Required configuration
    MIN_DELAY_SECONDS: float = 1.0
    MAX_DELAY_SECONDS: float = 3.0
    USER_AGENT: str = "CSF-Parts-Scraper/1.0 (contact@example.com)"
    MAX_RETRIES: int = 3
    TIMEOUT_SECONDS: int = 30

    def fetch_with_delay(self, url: str) -> Response:
        """Fetch URL with mandatory delay."""
        # Random delay between MIN and MAX
        delay = random.uniform(self.MIN_DELAY_SECONDS, self.MAX_DELAY_SECONDS)
        time.sleep(delay)

        headers = {"User-Agent": self.USER_AGENT}
        response = httpx.get(url, headers=headers, timeout=self.TIMEOUT_SECONDS)

        return response

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(MAX_RETRIES)
    )
    def fetch_with_retry(self, url: str) -> Response:
        """Fetch with exponential backoff on failures."""
        return self.fetch_with_delay(url)
```

### Rate Limiting Guidelines

| Scraping Intensity | Min Delay | Max Delay | Use Case |
|-------------------|-----------|-----------|----------|
| **Gentle** | 2s | 5s | Initial testing, small datasets |
| **Standard** | 1s | 3s | Production scraping (default) |
| **Aggressive** | 0.5s | 1.5s | Only with explicit permission |

**Default**: Always use **Standard** (1-3 seconds) unless you have specific permission from the site owner.

### User-Agent Best Practices

**✅ GOOD - Descriptive and Contactable**:
```python
USER_AGENT = "CSF-Parts-Scraper/1.0 (+https://yoursite.com/bot; contact@example.com)"
```

**❌ BAD - Deceptive or Generic**:
```python
USER_AGENT = "Mozilla/5.0..."  # Pretending to be a browser
USER_AGENT = "Python/3.13"     # Too generic, no contact info
```

### Robots.txt Compliance

**Check Before Scraping**:

```python
import urllib.robotparser

def check_robots_txt(base_url: str, path: str) -> bool:
    """Check if path is allowed by robots.txt."""
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(f"{base_url}/robots.txt")
    rp.read()

    user_agent = "CSF-Parts-Scraper"
    return rp.can_fetch(user_agent, path)

# Usage
if not check_robots_txt("https://example.com", "/parts/radiators"):
    logger.warning("Path disallowed by robots.txt, skipping")
    return
```

### Error Handling and Backoff

**Respect Server Signals**:

```python
def handle_rate_limiting(response: Response) -> None:
    """Handle HTTP 429 and Retry-After headers."""
    if response.status_code == 429:
        # Check for Retry-After header
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            wait_seconds = int(retry_after)
            logger.info(f"Rate limited, waiting {wait_seconds}s")
            time.sleep(wait_seconds)
        else:
            # Default backoff
            time.sleep(60)
        raise RetryableError("Rate limited")

    if response.status_code >= 500:
        # Server error, back off
        logger.warning(f"Server error {response.status_code}, backing off")
        raise RetryableError("Server error")
```

### Monitoring and Logging

**Track Your Impact**:

```python
import structlog

logger = structlog.get_logger()

class ScraperMetrics:
    """Track scraping metrics for respectful behavior."""

    def __init__(self):
        self.requests_made = 0
        self.bytes_downloaded = 0
        self.errors_encountered = 0
        self.start_time = time.time()

    def log_request(self, url: str, response: Response) -> None:
        """Log request details."""
        self.requests_made += 1
        self.bytes_downloaded += len(response.content)

        logger.info(
            "request_completed",
            url=url,
            status_code=response.status_code,
            response_size=len(response.content),
            total_requests=self.requests_made
        )

    def get_rate(self) -> float:
        """Get requests per second (should be <1 for respectful scraping)."""
        elapsed = time.time() - self.start_time
        return self.requests_made / elapsed if elapsed > 0 else 0
```

### Scheduling and Timing

**Off-Peak Recommendations**:

```python
from datetime import datetime

def is_off_peak_time() -> bool:
    """Check if current time is off-peak (2 AM - 6 AM local)."""
    current_hour = datetime.now().hour
    return 2 <= current_hour < 6

def should_scrape_now(force: bool = False) -> bool:
    """Determine if scraping should proceed."""
    if force:
        logger.warning("Forced scraping during peak hours")
        return True

    if is_off_peak_time():
        logger.info("Off-peak time, proceeding with scraping")
        return True

    logger.info("Peak hours, consider rescheduling for 2-6 AM")
    return False
```

### Anti-Patterns to Avoid

**❌ NEVER DO THIS**:

1. **Parallel Requests Without Rate Limiting**:
   ```python
   # BAD: Hammering server with concurrent requests
   async def scrape_all(urls):
       tasks = [fetch(url) for url in urls]  # No rate limiting!
       return await asyncio.gather(*tasks)
   ```

2. **Ignoring HTTP Error Codes**:
   ```python
   # BAD: Ignoring 429 rate limit responses
   try:
       response = requests.get(url)
   except Exception:
       pass  # Silently failing and retrying immediately
   ```

3. **No Request Delays**:
   ```python
   # BAD: No delays between requests
   for url in urls:
       response = requests.get(url)  # Instant next request!
   ```

4. **Fake User-Agents**:
   ```python
   # BAD: Pretending to be a real browser
   headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)..."}
   ```

### Checklist for Respectful Scraping

Before deploying any scraper, verify:

- [ ] Rate limiting implemented (1-3 second delays minimum)
- [ ] Descriptive user-agent with contact information
- [ ] robots.txt checked and honored
- [ ] Exponential backoff on errors
- [ ] HTTP 429 handling with Retry-After support
- [ ] Request timeout configured (max 30 seconds)
- [ ] Logging and monitoring in place
- [ ] Off-peak scheduling considered
- [ ] No parallel requests without rate limiting
- [ ] Error handling prevents runaway retries

## Code Quality and Linting

### Philosophy

**Code quality enforcement is non-negotiable**. All code must pass linting, type checking, and formatting checks before being committed. Ignoring or disabling linting rules should be an **absolute last resort** and only used when it is the legitimate best practice solution.

**We fix issues properly to best practices - we never rely on ignoring or disabling as a crutch.**

### The Three-Step Quality Process

Every code change must go through this process in order:

#### 1. Format (`ruff format`)

```bash
ruff format src/
```

Automatically formats code to consistent style. This should **never** produce errors - it just applies formatting.

#### 2. Lint (`ruff check`)

```bash
ruff check --fix src/
```

Catches code quality issues, unused imports, style violations, and potential bugs. Auto-fixes safe issues.

**For remaining issues**:
- ✅ **PREFERRED**: Fix the issue properly following best practices
- ❌ **AVOID**: Using `# noqa: RULE` to suppress warnings
- ⚠️ **ONLY IF**: Suppression is the documented best practice (see Legitimate Suppressions below)

#### 3. Type Check (`mypy`)

```bash
mypy src/
```

Ensures type safety. This is the **most critical** check.

**For type errors**:
- ✅ **ALWAYS**: Fix with proper type annotations
- ❌ **NEVER**: Use `# type: ignore` unless dealing with untyped third-party libraries

### Legitimate Use of Suppressions

There are rare cases where suppressing a warning is the correct solution:

#### ARG002 - Unused method argument

**Legitimate**: Template methods or interface implementations
```python
class HTMLParser:
    def extract_part_data(self, soup: BeautifulSoup) -> dict[str, Any]:  # noqa: ARG002
        """Template method - soup is used by subclasses."""
        return {}

class CSFParser(HTMLParser):
    def extract_part_data(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Now soup is used."""
        return {"sku": soup.select_one(".sku").text}
```

**Why legitimate**: The parent class defines the interface; subclasses use the parameter.

#### S311 - Standard pseudo-random generators

**Legitimate**: Non-cryptographic random use (delays, sampling, etc.)
```python
delay = random.uniform(1.0, 3.0)  # noqa: S311
```

**Why legitimate**: This is for mimicking human behavior, not security. Using `secrets` module would be overkill.

**NOT legitimate**: Password generation, tokens, cryptographic keys (use `secrets` module)

### When Suppression is a Crutch (Anti-Patterns)

❌ **BAD - Suppressing instead of fixing**:
```python
def parse_price(price: Any) -> Decimal:  # noqa: ANN401
    # Should use: str | float | Decimal instead of Any
```

❌ **BAD - Suppressing exception best practices**:
```python
except Exception as e:
    logger.error(...)  # noqa: TRY400
    # Should use: logger.exception(...)
```

❌ **BAD - Suppressing import organization**:
```python
def validate():
    import datetime  # noqa: PLC0415
    # Should move import to top of file
```

### Pre-Commit Checklist

Before committing any code:

- [ ] `ruff format src/` - All files formatted
- [ ] `ruff check src/` - **Zero errors, zero warnings**
- [ ] `mypy src/` - **Zero type errors**
- [ ] Reviewed any suppressions added - are they truly legitimate?
- [ ] Tests pass (`pytest`)
- [ ] Documentation updated

### CI/CD Integration

All three checks run in CI. **Pull requests cannot merge if any check fails.**

```yaml
# .github/workflows/quality.yml
- name: Format check
  run: ruff format --check src/

- name: Lint
  run: ruff check src/

- name: Type check
  run: mypy src/
```

### Summary

| Check | Tool | Failures Allowed | Fix Strategy |
|-------|------|------------------|--------------|
| Formatting | `ruff format` | **ZERO** | Auto-fix only |
| Linting | `ruff check` | **ZERO** | Fix properly, suppress only if legitimate |
| Type Safety | `mypy` | **ZERO** | Add proper types, never ignore |

**Remember**: Clean code is maintainable code. Suppressions are technical debt.

## Testing Standards

### Coverage Requirements

- **Minimum**: 90% code coverage
- **Target**: 95%+ code coverage
- **Critical Paths**: 100% coverage (payment, auth, data integrity)

### Test Organization

```
tests/
├── unit/
│   ├── test_validators.py
│   ├── test_models.py
│   └── test_services.py
├── integration/
│   ├── test_api.py
│   ├── test_database.py
│   └── test_scraper.py
├── e2e/
│   └── test_workflows.py
└── conftest.py
```

### Pytest Configuration

```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--strict-markers",
    "--cov=src",
    "--cov-report=html",
    "--cov-report=term-missing",
    "--cov-fail-under=90",
]
```

### Mocking Guidelines

**Rules**:
1. Mock external dependencies (APIs, databases, file systems)
2. Don't mock the unit under test
3. Use `pytest-mock` for mocking
4. Verify mock interactions when behavior matters

```python
def test_scraper_retries_on_failure(mocker):
    # Arrange
    mock_client = mocker.Mock(spec=HTTPClient)
    mock_client.get.side_effect = [
        HTTPException("Timeout"),
        HTTPException("Timeout"),
        mocker.Mock(status_code=200, text="<html>...</html>")
    ]
    scraper = PartScraper(client=mock_client)

    # Act
    result = scraper.scrape("https://example.com")

    # Assert
    assert mock_client.get.call_count == 3
    assert len(result) > 0
```

## Error Handling

### Exception Hierarchy

```python
class CarPartScraperError(Exception):
    """Base exception for all application errors."""
    pass

class ValidationError(CarPartScraperError):
    """Data validation failed."""
    pass

class ScrapingError(CarPartScraperError):
    """Web scraping failed."""
    pass

class HTTPError(ScrapingError):
    """HTTP request failed."""
    pass

class ParsingError(ScrapingError):
    """HTML parsing failed."""
    pass
```

### Error Handling Pattern

**✅ GOOD**:
```python
from typing import TypeVar, Callable
from functools import wraps

T = TypeVar('T')

def retry_on_error(max_attempts: int = 3):
    """Decorator to retry function on failure."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except HTTPError as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
            raise last_exception
        return wrapper
    return decorator

@retry_on_error(max_attempts=3)
def fetch_part(sku: str) -> Part:
    """Fetch part with automatic retry."""
    response = httpx.get(f"{BASE_URL}/parts/{sku}")
    response.raise_for_status()
    return Part(**response.json())
```

### Logging

**Rules**:
1. Use structured logging (JSON format)
2. Include context (request ID, user ID, etc.)
3. Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

```python
import structlog

logger = structlog.get_logger()

def scrape_part(url: str) -> Part:
    """Scrape part from URL."""
    logger.info("scraping_started", url=url)

    try:
        response = fetch_url(url)
        part = parse_response(response)
        logger.info("scraping_completed", sku=part.sku, url=url)
        return part
    except ScrapingError as e:
        logger.error("scraping_failed", url=url, error=str(e))
        raise
```

## Documentation Requirements

### Docstrings

**Rule**: All public functions, classes, and modules must have docstrings in Google style.

```python
def calculate_shipping(parts: list[Part], destination: str, expedited: bool = False) -> Decimal:
    """Calculate shipping cost for parts order.

    Calculates total shipping cost based on combined weight, destination,
    and shipping speed. Uses carrier API for real-time rates.

    Args:
        parts: List of parts to ship
        destination: Destination ZIP code
        expedited: Whether to use expedited shipping (default: False)

    Returns:
        Total shipping cost in USD

    Raises:
        ValidationError: If destination ZIP is invalid
        CarrierAPIError: If carrier API is unavailable

    Examples:
        >>> parts = [PartFactory(), PartFactory()]
        >>> calculate_shipping(parts, "90210")
        Decimal("15.99")

        >>> calculate_shipping(parts, "90210", expedited=True)
        Decimal("29.99")
    """
    pass
```

### Inline Comments

**Rules**:
1. Explain WHY, not WHAT
2. Use comments for complex algorithms or business logic
3. Avoid obvious comments

**❌ BAD**:
```python
# Increment counter by 1
counter += 1
```

**✅ GOOD**:
```python
# Skip cached items to avoid re-processing already validated parts
if part.sku in validated_cache:
    continue
```

## Anti-Patterns to Avoid

### 1. God Objects

**❌ AVOID**: Classes that know/do too much

```python
class PartManager:
    def scrape_parts(self): pass
    def validate_parts(self): pass
    def save_parts(self): pass
    def export_parts(self): pass
    def send_notifications(self): pass
    def generate_reports(self): pass
    # ... 20 more methods
```

### 2. Magic Numbers/Strings

**❌ AVOID**: Hardcoded values without context

```python
if response.status_code == 429:  # What does 429 mean?
    time.sleep(60)  # Why 60?
```

**✅ PREFER**: Named constants

```python
HTTP_TOO_MANY_REQUESTS = 429
RATE_LIMIT_COOLDOWN_SECONDS = 60

if response.status_code == HTTP_TOO_MANY_REQUESTS:
    time.sleep(RATE_LIMIT_COOLDOWN_SECONDS)
```

### 3. Primitive Obsession

**❌ AVOID**: Using primitives instead of domain objects

```python
def create_part(sku: str, name: str, price: float, category: str) -> bool:
    pass
```

**✅ PREFER**: Rich domain models

```python
def create_part(part: Part) -> Part:
    pass
```

### 4. Shotgun Surgery

**❌ AVOID**: Requiring changes across many files for one feature

**✅ PREFER**: Cohesive modules where related changes are localized

### 5. Copy-Paste Programming

**❌ AVOID**: Duplicating code instead of abstracting

**✅ PREFER**: Extract shared logic into utilities/base classes

### 6. Silent Failures

**❌ AVOID**: Swallowing exceptions

```python
try:
    risky_operation()
except Exception:
    pass  # Silent failure!
```

**✅ PREFER**: Explicit error handling

```python
try:
    risky_operation()
except KnownError as e:
    logger.error("operation_failed", error=str(e))
    raise
except Exception as e:
    logger.critical("unexpected_error", error=str(e))
    raise
```

## Enforcement

### Pre-Commit Hooks

All code must pass these checks before commit:

1. **ruff format**: Code formatting
2. **ruff check**: Linting rules
3. **mypy**: Type checking
4. **pytest**: All tests pass
5. **Coverage**: Minimum 90% coverage

### Code Review Checklist

- [ ] Follows DRY principles (no duplication)
- [ ] Adheres to SOLID principles
- [ ] Tests follow AAA pattern
- [ ] Full type hints present
- [ ] Docstrings for all public APIs
- [ ] No magic numbers/strings
- [ ] Error handling present
- [ ] Logging added where appropriate
- [ ] No anti-patterns present
- [ ] Test coverage ≥90%

---

**Last Updated**: 2025-10-27
**Version**: 1.0.0
**Maintainer**: Development Team

This is a living document. Propose changes via pull request with rationale.
