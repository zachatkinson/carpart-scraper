"""Test endpoint command for CLI.

This module provides the 'test-endpoint' command for testing different types
of CSF MyCarParts endpoints (application pages, detail pages, AJAX endpoints)
and displaying response details and extracted data previews.
"""

import json
import time
from enum import Enum
from pathlib import Path
from typing import Any

import click
import structlog
from bs4 import BeautifulSoup
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from src.scraper.ajax_parser import AJAXParsingError, AJAXResponseParser
from src.scraper.fetcher import RespectfulFetcher
from src.scraper.parser import CSFParser

logger = structlog.get_logger()
console = Console()


class EndpointType(str, Enum):
    """Supported endpoint types for testing.

    Attributes:
        APPLICATION: Application pages (JavaScript-rendered, requires browser)
        DETAIL: Detail pages (static HTML, can use httpx)
        AJAX: AJAX endpoints (JavaScript responses)
    """

    APPLICATION = "application"
    DETAIL = "detail"
    AJAX = "ajax"


class EndpointTestResult:
    """Result of endpoint testing.

    Attributes:
        url: URL that was tested
        endpoint_type: Type of endpoint tested
        status_code: HTTP status code (or 200 for browser)
        response_time: Time taken for request in seconds
        content_length: Size of response in bytes
        content: Raw response content
        extracted_data: Extracted/parsed data preview
        success: Whether the test was successful
        error_message: Error message if test failed
    """

    def __init__(
        self,
        url: str,
        endpoint_type: EndpointType,
    ) -> None:
        """Initialize test result.

        Args:
            url: URL being tested
            endpoint_type: Type of endpoint
        """
        self.url = url
        self.endpoint_type = endpoint_type
        self.status_code: int | None = None
        self.response_time: float = 0.0
        self.content_length: int = 0
        self.content: str = ""
        self.extracted_data: dict[str, Any] | None = None
        self.success: bool = False
        self.error_message: str | None = None


class EndpointTester:
    """Tests various types of CSF MyCarParts endpoints.

    Follows Single Responsibility Principle - only concerned with testing endpoints.
    Uses dependency injection for fetcher and parsers.
    """

    def __init__(
        self,
        fetcher: RespectfulFetcher,
        ajax_parser: AJAXResponseParser,
        html_parser: CSFParser,
    ) -> None:
        """Initialize endpoint tester.

        Args:
            fetcher: HTTP/Browser fetcher instance
            ajax_parser: AJAX response parser
            html_parser: HTML parser for CSF pages
        """
        self.fetcher = fetcher
        self.ajax_parser = ajax_parser
        self.html_parser = html_parser

    def test_endpoint(
        self,
        url: str,
        endpoint_type: EndpointType,
    ) -> EndpointTestResult:
        """Test an endpoint and collect results.

        Args:
            url: URL to test
            endpoint_type: Type of endpoint to test

        Returns:
            Test result with response details and extracted data
        """
        result = EndpointTestResult(url, endpoint_type)

        logger.info("testing_endpoint", url=url, endpoint_type=endpoint_type.value)

        try:
            if endpoint_type == EndpointType.APPLICATION:
                self._test_application_page(result)
            elif endpoint_type == EndpointType.DETAIL:
                self._test_detail_page(result)
            elif endpoint_type == EndpointType.AJAX:
                self._test_ajax_endpoint(result)

            result.success = True
            logger.info("test_successful", url=url, endpoint_type=endpoint_type.value)

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            logger.exception("test_failed", url=url, error=str(e))

        return result

    def _test_application_page(self, result: EndpointTestResult) -> None:
        """Test application page with Playwright.

        Args:
            result: Test result to populate
        """
        start_time = time.time()
        html = self.fetcher.fetch_with_browser(result.url)
        result.response_time = time.time() - start_time

        result.status_code = 200  # Browser always returns 200 for successful load
        result.content_length = len(html)
        result.content = html

        # Extract data preview
        soup = BeautifulSoup(html, "lxml")
        try:
            result.extracted_data = self.html_parser.extract_part_data(soup)
        except ValueError as e:
            logger.warning("data_extraction_failed", error=str(e))
            result.extracted_data = {"error": str(e)}

    def _test_detail_page(self, result: EndpointTestResult) -> None:
        """Test detail page with httpx.

        Args:
            result: Test result to populate
        """
        start_time = time.time()
        response = self.fetcher.fetch(result.url)
        result.response_time = time.time() - start_time

        result.status_code = response.status_code
        result.content_length = len(response.content)
        result.content = response.text

        # Extract SKU from URL (e.g., /items/3951 -> 3951)
        sku = result.url.rstrip("/").split("/")[-1]

        # Extract data preview
        soup = self.html_parser.parse(result.content)
        try:
            result.extracted_data = self.html_parser.extract_detail_page_data(soup, sku)
        except (ValueError, AttributeError, KeyError) as e:
            logger.warning("data_extraction_failed", error=str(e))
            result.extracted_data = {"error": str(e)}

    def _test_ajax_endpoint(self, result: EndpointTestResult) -> None:
        """Test AJAX endpoint with httpx.

        Args:
            result: Test result to populate
        """
        start_time = time.time()
        response = self.fetcher.fetch(result.url)
        result.response_time = time.time() - start_time

        result.status_code = response.status_code
        result.content_length = len(response.content)
        result.content = response.text

        # Parse AJAX response
        try:
            html = self.ajax_parser.parse(result.content)
            result.extracted_data = {
                "parsed_html": html[:500],  # First 500 chars
                "html_length": len(html),
            }
        except AJAXParsingError as e:
            logger.warning("ajax_parsing_failed", error=str(e))
            result.extracted_data = {"error": str(e)}


class ResultFormatter:
    """Formats test results using Rich for beautiful terminal output.

    Follows Single Responsibility Principle - only concerned with formatting output.
    """

    def __init__(self, console: Console) -> None:
        """Initialize formatter.

        Args:
            console: Rich console instance
        """
        self.console = console

    def display_result(self, result: EndpointTestResult) -> None:
        """Display test result with Rich formatting.

        Args:
            result: Test result to display
        """
        if result.success:
            self._display_success(result)
        else:
            self._display_error(result)

    def _display_success(self, result: EndpointTestResult) -> None:
        """Display successful test result.

        Args:
            result: Successful test result
        """
        # Header
        header = Text()
        header.append("Endpoint Test Result", style="bold green")
        header.append(f" ({result.endpoint_type.value})", style="dim")
        self.console.print()
        self.console.print(Panel(header, expand=False))

        # Response details table
        table = Table(title="Response Details", show_header=True)
        table.add_column("Property", style="cyan", no_wrap=True)
        table.add_column("Value", style="white")

        table.add_row("URL", result.url)
        table.add_row("Type", result.endpoint_type.value)
        table.add_row("Status Code", str(result.status_code))
        table.add_row("Response Time", f"{result.response_time:.3f}s")
        table.add_row("Content Length", f"{result.content_length:,} bytes")

        self.console.print(table)

        # Extracted data preview
        if result.extracted_data:
            self.console.print()
            self.console.print(Panel("Extracted Data Preview", style="bold blue"))

            # Format as pretty-printed dict
            data_json = json.dumps(result.extracted_data, indent=2, default=str)
            syntax = Syntax(data_json, "json", theme="monokai", line_numbers=True)
            self.console.print(syntax)

    def _display_error(self, result: EndpointTestResult) -> None:
        """Display failed test result.

        Args:
            result: Failed test result
        """
        header = Text()
        header.append("Endpoint Test Failed", style="bold red")
        header.append(f" ({result.endpoint_type.value})", style="dim")
        self.console.print()
        self.console.print(Panel(header, expand=False))

        # Error details
        table = Table(show_header=True)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("URL", result.url)
        table.add_row("Type", result.endpoint_type.value)
        table.add_row("Error", result.error_message or "Unknown error")

        self.console.print(table)

    def save_content(self, result: EndpointTestResult, output_path: Path) -> None:
        """Save response content to file.

        Args:
            result: Test result with content
            output_path: Path to save content
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(result.content, encoding="utf-8")
            self.console.print(
                f"\n[green]Content saved to:[/green] {output_path}",
            )
        except OSError as e:
            self.console.print(
                f"\n[red]Failed to save content:[/red] {e}",
            )


@click.command(name="test-endpoint")
@click.option(
    "--url",
    required=True,
    help="URL to test (full URL including https://)",
)
@click.option(
    "--type",
    "endpoint_type",
    type=click.Choice([t.value for t in EndpointType], case_sensitive=False),
    required=True,
    help="Type of endpoint to test",
)
@click.option(
    "--save",
    type=click.Path(path_type=Path),
    help="Save HTML/response content to specified file",
)
def test_endpoint(
    url: str,
    endpoint_type: str,
    save: Path | None,
) -> None:
    r"""Test a CSF MyCarParts endpoint and display response details.

    This command allows you to test different types of endpoints:

    \b
    - application: Test application pages (requires Playwright browser)
    - detail: Test detail/item pages (uses httpx)
    - ajax: Test AJAX endpoints (uses httpx + AJAX parser)

    The command will display:
    - HTTP status code
    - Response time
    - Content length
    - Extracted/parsed data preview

    Examples:
    \b
    # Test an application page
    carpart test-endpoint \\
        --url https://csfmycarparts.com/applications/8430 \\
        --type application

    \b
    # Test a detail page
    carpart test-endpoint \\
        --url https://csfmycarparts.com/items/3951 \\
        --type detail \\
        --save detail_3951.html

    \b
    # Test an AJAX endpoint
    carpart test-endpoint \\
        --url "https://csfmycarparts.com/get/years?make=Honda" \\
        --type ajax
    """
    # Convert string to enum
    endpoint_type_enum = EndpointType(endpoint_type.lower())

    # Initialize components with dependency injection
    fetcher = RespectfulFetcher()
    ajax_parser = AJAXResponseParser()
    html_parser = CSFParser()

    tester = EndpointTester(fetcher, ajax_parser, html_parser)
    formatter = ResultFormatter(console)

    try:
        # Run test
        result = tester.test_endpoint(url, endpoint_type_enum)

        # Display result
        formatter.display_result(result)

        # Save content if requested
        if save and result.success:
            formatter.save_content(result, save)

    finally:
        # Clean up resources
        fetcher.close()
