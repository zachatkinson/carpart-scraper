"""Unit tests for test-endpoint command.

This module contains comprehensive tests for the CLI test-endpoint command,
EndpointTester, and ResultFormatter classes, following AAA (Arrange-Act-Assert) pattern.
"""

from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest
from click.testing import CliRunner
from pytest_mock import MockerFixture

from src.cli.commands.test_endpoint import (
    EndpointTester,
    EndpointTestResult,
    EndpointType,
    ResultFormatter,
)
from src.cli.commands.test_endpoint import test_endpoint as cmd_test_endpoint
from src.scraper.ajax_parser import AJAXParsingError, AJAXResponseParser
from src.scraper.fetcher import RespectfulFetcher
from src.scraper.parser import CSFParser

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide Click CLI test runner.

    Returns:
        CliRunner instance for testing Click commands
    """
    return CliRunner()


@pytest.fixture
def mock_fetcher(mocker: MockerFixture) -> Mock:
    """Provide mocked RespectfulFetcher.

    Args:
        mocker: pytest-mock fixture

    Returns:
        Mock fetcher instance
    """
    mock: Mock = mocker.Mock(spec=RespectfulFetcher)

    # Configure default httpx response
    mock_response = mocker.Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.text = "<html><body>Test</body></html>"
    mock_response.content = b"<html><body>Test</body></html>"
    mock.fetch.return_value = mock_response

    # Configure browser fetch
    mock.fetch_with_browser.return_value = "<html><body>Test</body></html>"

    return mock


@pytest.fixture
def mock_ajax_parser(mocker: MockerFixture) -> Mock:
    """Provide mocked AJAXResponseParser.

    Args:
        mocker: pytest-mock fixture

    Returns:
        Mock AJAX parser instance
    """
    mock: Mock = mocker.Mock(spec=AJAXResponseParser)
    mock.parse.return_value = "<html><body>Parsed HTML</body></html>"
    return mock


@pytest.fixture
def mock_html_parser(mocker: MockerFixture) -> Mock:
    """Provide mocked CSFParser.

    Args:
        mocker: pytest-mock fixture

    Returns:
        Mock HTML parser instance
    """
    mock: Mock = mocker.Mock(spec=CSFParser)
    mock.extract_part_data.return_value = {
        "sku": "CSF-3951",
        "name": "Radiator",
        "price": "299.99",
    }
    mock.extract_detail_page_data.return_value = {
        "sku": "CSF-3951",
        "name": "Radiator",
        "price": "299.99",
        "description": "Test description",
    }
    return mock


@pytest.fixture
def patch_dependencies(
    mocker: MockerFixture,
    mock_fetcher: Mock,
    mock_ajax_parser: Mock,
    mock_html_parser: Mock,
) -> tuple[Mock, Mock, Mock]:
    """Patch all test-endpoint command dependencies.

    Args:
        mocker: pytest-mock fixture
        mock_fetcher: Mock fetcher instance
        mock_ajax_parser: Mock AJAX parser instance
        mock_html_parser: Mock HTML parser instance

    Returns:
        Tuple of patched constructors (fetcher, ajax_parser, html_parser)
    """
    patched_fetcher = mocker.patch(
        "src.cli.commands.test_endpoint.RespectfulFetcher",
        return_value=mock_fetcher,
    )
    patched_ajax = mocker.patch(
        "src.cli.commands.test_endpoint.AJAXResponseParser",
        return_value=mock_ajax_parser,
    )
    patched_html = mocker.patch(
        "src.cli.commands.test_endpoint.CSFParser",
        return_value=mock_html_parser,
    )
    return patched_fetcher, patched_ajax, patched_html


# ============================================================================
# Click Command Tests
# ============================================================================


class TestTestEndpointCommandRegistration:
    """Test that test-endpoint command is registered correctly."""

    def test_test_endpoint_is_click_command(self) -> None:
        """Test test-endpoint command is a Click command."""
        # Arrange & Act & Assert
        assert hasattr(cmd_test_endpoint, "callback")
        assert hasattr(cmd_test_endpoint, "params")

    def test_test_endpoint_has_url_option(self) -> None:
        """Test test-endpoint command has --url option."""
        # Arrange
        param_names = [param.name for param in cmd_test_endpoint.params]

        # Act & Assert
        assert "url" in param_names

    def test_test_endpoint_has_type_option(self) -> None:
        """Test test-endpoint command has --type option."""
        # Arrange
        param_names = [param.name for param in cmd_test_endpoint.params]

        # Act & Assert
        assert "endpoint_type" in param_names

    def test_test_endpoint_has_save_option(self) -> None:
        """Test test-endpoint command has --save option."""
        # Arrange
        param_names = [param.name for param in cmd_test_endpoint.params]

        # Act & Assert
        assert "save" in param_names


class TestTestEndpointCommandOptions:
    """Test test-endpoint command option handling."""

    def test_url_option_is_required(self, cli_runner: CliRunner) -> None:
        """Test --url option is required."""
        # Arrange & Act
        result = cli_runner.invoke(cmd_test_endpoint, ["--type", "detail"])

        # Assert
        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_type_option_is_required(self, cli_runner: CliRunner) -> None:
        """Test --type option is required."""
        # Arrange & Act
        result = cli_runner.invoke(cmd_test_endpoint, ["--url", "https://example.com/items/3951"])

        # Assert
        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_type_option_accepts_application(
        self, cli_runner: CliRunner, patch_dependencies: tuple[Mock, Mock, Mock]
    ) -> None:
        """Test --type option accepts 'application' value."""
        # Arrange
        url = "https://example.com/applications/8430"

        # Act
        result = cli_runner.invoke(cmd_test_endpoint, ["--url", url, "--type", "application"])

        # Assert
        assert result.exit_code == 0

    def test_type_option_accepts_detail(
        self, cli_runner: CliRunner, patch_dependencies: tuple[Mock, Mock, Mock]
    ) -> None:
        """Test --type option accepts 'detail' value."""
        # Arrange
        url = "https://example.com/items/3951"

        # Act
        result = cli_runner.invoke(cmd_test_endpoint, ["--url", url, "--type", "detail"])

        # Assert
        assert result.exit_code == 0

    def test_type_option_accepts_ajax(
        self, cli_runner: CliRunner, patch_dependencies: tuple[Mock, Mock, Mock]
    ) -> None:
        """Test --type option accepts 'ajax' value."""
        # Arrange
        url = "https://example.com/get/years?make=Honda"

        # Act
        result = cli_runner.invoke(cmd_test_endpoint, ["--url", url, "--type", "ajax"])

        # Assert
        assert result.exit_code == 0

    def test_type_option_rejects_invalid_value(self, cli_runner: CliRunner) -> None:
        """Test --type option rejects invalid values."""
        # Arrange
        url = "https://example.com/items/3951"

        # Act
        result = cli_runner.invoke(cmd_test_endpoint, ["--url", url, "--type", "invalid"])

        # Assert
        assert result.exit_code != 0
        assert "Invalid value" in result.output or "invalid choice" in result.output.lower()

    def test_save_option_accepts_file_path(
        self,
        cli_runner: CliRunner,
        patch_dependencies: tuple[Mock, Mock, Mock],
        tmp_path: Path,
    ) -> None:
        """Test --save option accepts file path."""
        # Arrange
        url = "https://example.com/items/3951"
        save_path = tmp_path / "response.html"

        # Act
        result = cli_runner.invoke(
            cmd_test_endpoint,
            ["--url", url, "--type", "detail", "--save", str(save_path)],
        )

        # Assert
        assert result.exit_code == 0
        assert save_path.exists()


class TestTestEndpointCommandHelp:
    """Test test-endpoint command help text."""

    def test_help_text_displays_correctly(self, cli_runner: CliRunner) -> None:
        """Test help text displays correctly."""
        # Arrange & Act
        result = cli_runner.invoke(cmd_test_endpoint, ["--help"])

        # Assert
        assert result.exit_code == 0
        assert "Test a CSF MyCarParts endpoint" in result.output
        assert "--url" in result.output
        assert "--type" in result.output
        assert "--save" in result.output
        assert "application" in result.output
        assert "detail" in result.output
        assert "ajax" in result.output


class TestTestEndpointCommandWorkflow:
    """Test test-endpoint command full workflow."""

    def test_application_endpoint_workflow(
        self,
        cli_runner: CliRunner,
        patch_dependencies: tuple[Mock, Mock, Mock],
        mock_fetcher: Mock,
    ) -> None:
        """Test complete workflow for application endpoint."""
        # Arrange
        url = "https://example.com/applications/8430"
        _, _, _ = patch_dependencies

        # Act
        result = cli_runner.invoke(cmd_test_endpoint, ["--url", url, "--type", "application"])

        # Assert
        assert result.exit_code == 0
        mock_fetcher.fetch_with_browser.assert_called_once_with(url)
        assert "Endpoint Test Result" in result.output

    def test_detail_endpoint_workflow(
        self,
        cli_runner: CliRunner,
        patch_dependencies: tuple[Mock, Mock, Mock],
        mock_fetcher: Mock,
    ) -> None:
        """Test complete workflow for detail endpoint."""
        # Arrange
        url = "https://example.com/items/3951"
        _, _, _ = patch_dependencies

        # Act
        result = cli_runner.invoke(cmd_test_endpoint, ["--url", url, "--type", "detail"])

        # Assert
        assert result.exit_code == 0
        mock_fetcher.fetch.assert_called_once_with(url)
        assert "Endpoint Test Result" in result.output

    def test_ajax_endpoint_workflow(
        self,
        cli_runner: CliRunner,
        patch_dependencies: tuple[Mock, Mock, Mock],
        mock_fetcher: Mock,
        mock_ajax_parser: Mock,
    ) -> None:
        """Test complete workflow for AJAX endpoint."""
        # Arrange
        url = "https://example.com/get/years?make=Honda"
        _, _, _ = patch_dependencies

        # Act
        result = cli_runner.invoke(cmd_test_endpoint, ["--url", url, "--type", "ajax"])

        # Assert
        assert result.exit_code == 0
        mock_fetcher.fetch.assert_called_once_with(url)
        mock_ajax_parser.parse.assert_called_once()
        assert "Endpoint Test Result" in result.output

    def test_fetcher_cleanup_called(
        self,
        cli_runner: CliRunner,
        patch_dependencies: tuple[Mock, Mock, Mock],
        mock_fetcher: Mock,
    ) -> None:
        """Test fetcher cleanup is called after command execution."""
        # Arrange
        url = "https://example.com/items/3951"
        _, _, _ = patch_dependencies

        # Act
        result = cli_runner.invoke(cmd_test_endpoint, ["--url", url, "--type", "detail"])

        # Assert
        assert result.exit_code == 0
        mock_fetcher.close.assert_called_once()

    def test_save_content_creates_file(
        self,
        cli_runner: CliRunner,
        patch_dependencies: tuple[Mock, Mock, Mock],
        tmp_path: Path,
    ) -> None:
        """Test --save option creates file with response content."""
        # Arrange
        url = "https://example.com/items/3951"
        save_path = tmp_path / "response.html"
        _, _, _ = patch_dependencies

        # Act
        result = cli_runner.invoke(
            cmd_test_endpoint,
            ["--url", url, "--type", "detail", "--save", str(save_path)],
        )

        # Assert
        assert result.exit_code == 0
        assert save_path.exists()
        content = save_path.read_text(encoding="utf-8")
        assert "<html>" in content


# ============================================================================
# EndpointType Tests
# ============================================================================


class TestEndpointType:
    """Test EndpointType enum."""

    def test_endpoint_type_has_application(self) -> None:
        """Test EndpointType has APPLICATION value."""
        # Arrange & Act & Assert
        assert EndpointType.APPLICATION.value == "application"

    def test_endpoint_type_has_detail(self) -> None:
        """Test EndpointType has DETAIL value."""
        # Arrange & Act & Assert
        assert EndpointType.DETAIL.value == "detail"

    def test_endpoint_type_has_ajax(self) -> None:
        """Test EndpointType has AJAX value."""
        # Arrange & Act & Assert
        assert EndpointType.AJAX.value == "ajax"

    def test_endpoint_type_can_be_converted_from_string(self) -> None:
        """Test EndpointType can be converted from string."""
        # Arrange & Act
        endpoint_type = EndpointType("application")

        # Assert
        assert endpoint_type == EndpointType.APPLICATION


# ============================================================================
# EndpointTestResult Tests
# ============================================================================


class TestEndpointTestResult:
    """Test EndpointTestResult class."""

    def test_init_sets_url_and_type(self) -> None:
        """Test __init__ sets URL and endpoint type."""
        # Arrange
        url = "https://example.com/items/3951"
        endpoint_type = EndpointType.DETAIL

        # Act
        result = EndpointTestResult(url, endpoint_type)

        # Assert
        assert result.url == url
        assert result.endpoint_type == endpoint_type

    def test_init_sets_default_values(self) -> None:
        """Test __init__ sets default values for result fields."""
        # Arrange
        url = "https://example.com/items/3951"
        endpoint_type = EndpointType.DETAIL

        # Act
        result = EndpointTestResult(url, endpoint_type)

        # Assert
        assert result.status_code is None
        assert result.response_time == 0.0
        assert result.content_length == 0
        assert result.content == ""
        assert result.extracted_data is None
        assert result.success is False
        assert result.error_message is None


# ============================================================================
# EndpointTester Tests
# ============================================================================


class TestEndpointTesterInit:
    """Test EndpointTester initialization."""

    def test_init_sets_dependencies(
        self,
        mock_fetcher: Mock,
        mock_ajax_parser: Mock,
        mock_html_parser: Mock,
    ) -> None:
        """Test __init__ sets all dependencies."""
        # Arrange & Act
        tester = EndpointTester(mock_fetcher, mock_ajax_parser, mock_html_parser)

        # Assert
        assert tester.fetcher is mock_fetcher
        assert tester.ajax_parser is mock_ajax_parser
        assert tester.html_parser is mock_html_parser


class TestEndpointTesterApplicationPage:
    """Test EndpointTester application page testing."""

    def test_test_application_page_uses_browser(
        self,
        mock_fetcher: Mock,
        mock_ajax_parser: Mock,
        mock_html_parser: Mock,
    ) -> None:
        """Test testing application page uses browser fetcher."""
        # Arrange
        url = "https://example.com/applications/8430"
        tester = EndpointTester(mock_fetcher, mock_ajax_parser, mock_html_parser)

        # Act
        result = tester.test_endpoint(url, EndpointType.APPLICATION)

        # Assert
        mock_fetcher.fetch_with_browser.assert_called_once_with(url)
        assert result.success is True

    def test_test_application_page_sets_status_code_200(
        self,
        mock_fetcher: Mock,
        mock_ajax_parser: Mock,
        mock_html_parser: Mock,
    ) -> None:
        """Test testing application page sets status code to 200."""
        # Arrange
        url = "https://example.com/applications/8430"
        tester = EndpointTester(mock_fetcher, mock_ajax_parser, mock_html_parser)

        # Act
        result = tester.test_endpoint(url, EndpointType.APPLICATION)

        # Assert
        assert result.status_code == 200

    def test_test_application_page_measures_response_time(
        self,
        mock_fetcher: Mock,
        mock_ajax_parser: Mock,
        mock_html_parser: Mock,
    ) -> None:
        """Test testing application page measures response time."""
        # Arrange
        url = "https://example.com/applications/8430"
        tester = EndpointTester(mock_fetcher, mock_ajax_parser, mock_html_parser)

        # Act
        result = tester.test_endpoint(url, EndpointType.APPLICATION)

        # Assert
        assert result.response_time > 0

    def test_test_application_page_extracts_data(
        self,
        mock_fetcher: Mock,
        mock_ajax_parser: Mock,
        mock_html_parser: Mock,
    ) -> None:
        """Test testing application page extracts data."""
        # Arrange
        url = "https://example.com/applications/8430"
        tester = EndpointTester(mock_fetcher, mock_ajax_parser, mock_html_parser)

        # Act
        result = tester.test_endpoint(url, EndpointType.APPLICATION)

        # Assert
        assert result.extracted_data is not None
        mock_html_parser.extract_part_data.assert_called_once()

    def test_test_application_page_handles_extraction_error(
        self,
        mock_fetcher: Mock,
        mock_ajax_parser: Mock,
        mock_html_parser: Mock,
    ) -> None:
        """Test testing application page handles extraction errors gracefully."""
        # Arrange
        url = "https://example.com/applications/8430"
        mock_html_parser.extract_part_data.side_effect = ValueError("Extraction failed")
        tester = EndpointTester(mock_fetcher, mock_ajax_parser, mock_html_parser)

        # Act
        result = tester.test_endpoint(url, EndpointType.APPLICATION)

        # Assert
        assert result.success is True
        assert result.extracted_data is not None
        assert "error" in result.extracted_data


class TestEndpointTesterDetailPage:
    """Test EndpointTester detail page testing."""

    def test_test_detail_page_uses_httpx(
        self,
        mock_fetcher: Mock,
        mock_ajax_parser: Mock,
        mock_html_parser: Mock,
    ) -> None:
        """Test testing detail page uses httpx fetcher."""
        # Arrange
        url = "https://example.com/items/3951"
        tester = EndpointTester(mock_fetcher, mock_ajax_parser, mock_html_parser)

        # Act
        result = tester.test_endpoint(url, EndpointType.DETAIL)

        # Assert
        mock_fetcher.fetch.assert_called_once_with(url)
        assert result.success is True

    def test_test_detail_page_sets_status_code(
        self,
        mock_fetcher: Mock,
        mock_ajax_parser: Mock,
        mock_html_parser: Mock,
        mocker: MockerFixture,
    ) -> None:
        """Test testing detail page sets status code from response."""
        # Arrange
        url = "https://example.com/items/3951"
        mock_response = mocker.Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = "<html></html>"
        mock_response.content = b"<html></html>"
        mock_fetcher.fetch.return_value = mock_response
        tester = EndpointTester(mock_fetcher, mock_ajax_parser, mock_html_parser)

        # Act
        result = tester.test_endpoint(url, EndpointType.DETAIL)

        # Assert
        assert result.status_code == 200

    def test_test_detail_page_extracts_sku_from_url(
        self,
        mock_fetcher: Mock,
        mock_ajax_parser: Mock,
        mock_html_parser: Mock,
    ) -> None:
        """Test testing detail page extracts SKU from URL."""
        # Arrange
        url = "https://example.com/items/3951"
        tester = EndpointTester(mock_fetcher, mock_ajax_parser, mock_html_parser)

        # Act
        result = tester.test_endpoint(url, EndpointType.DETAIL)

        # Assert
        assert result.success is True
        mock_html_parser.extract_detail_page_data.assert_called_once()
        call_args = mock_html_parser.extract_detail_page_data.call_args
        assert call_args[0][1] == "3951"

    def test_test_detail_page_handles_trailing_slash(
        self,
        mock_fetcher: Mock,
        mock_ajax_parser: Mock,
        mock_html_parser: Mock,
    ) -> None:
        """Test testing detail page handles URLs with trailing slash."""
        # Arrange
        url = "https://example.com/items/3951/"
        tester = EndpointTester(mock_fetcher, mock_ajax_parser, mock_html_parser)

        # Act
        result = tester.test_endpoint(url, EndpointType.DETAIL)

        # Assert
        assert result.success is True
        call_args = mock_html_parser.extract_detail_page_data.call_args
        assert call_args[0][1] == "3951"

    def test_test_detail_page_handles_extraction_errors(
        self,
        mock_fetcher: Mock,
        mock_ajax_parser: Mock,
        mock_html_parser: Mock,
    ) -> None:
        """Test testing detail page handles extraction errors gracefully."""
        # Arrange
        url = "https://example.com/items/3951"
        mock_html_parser.extract_detail_page_data.side_effect = KeyError("Missing field")
        tester = EndpointTester(mock_fetcher, mock_ajax_parser, mock_html_parser)

        # Act
        result = tester.test_endpoint(url, EndpointType.DETAIL)

        # Assert
        assert result.success is True
        assert result.extracted_data is not None
        assert "error" in result.extracted_data


class TestEndpointTesterAjaxEndpoint:
    """Test EndpointTester AJAX endpoint testing."""

    def test_test_ajax_endpoint_uses_httpx(
        self,
        mock_fetcher: Mock,
        mock_ajax_parser: Mock,
        mock_html_parser: Mock,
    ) -> None:
        """Test testing AJAX endpoint uses httpx fetcher."""
        # Arrange
        url = "https://example.com/get/years?make=Honda"
        tester = EndpointTester(mock_fetcher, mock_ajax_parser, mock_html_parser)

        # Act
        result = tester.test_endpoint(url, EndpointType.AJAX)

        # Assert
        mock_fetcher.fetch.assert_called_once_with(url)
        assert result.success is True

    def test_test_ajax_endpoint_parses_response(
        self,
        mock_fetcher: Mock,
        mock_ajax_parser: Mock,
        mock_html_parser: Mock,
    ) -> None:
        """Test testing AJAX endpoint parses response."""
        # Arrange
        url = "https://example.com/get/years?make=Honda"
        tester = EndpointTester(mock_fetcher, mock_ajax_parser, mock_html_parser)

        # Act
        result = tester.test_endpoint(url, EndpointType.AJAX)

        # Assert
        mock_ajax_parser.parse.assert_called_once()
        assert result.success is True

    def test_test_ajax_endpoint_extracts_parsed_html_preview(
        self,
        mock_fetcher: Mock,
        mock_ajax_parser: Mock,
        mock_html_parser: Mock,
    ) -> None:
        """Test testing AJAX endpoint extracts parsed HTML preview."""
        # Arrange
        url = "https://example.com/get/years?make=Honda"
        parsed_html = "A" * 1000
        mock_ajax_parser.parse.return_value = parsed_html
        tester = EndpointTester(mock_fetcher, mock_ajax_parser, mock_html_parser)

        # Act
        result = tester.test_endpoint(url, EndpointType.AJAX)

        # Assert
        assert result.success is True
        assert result.extracted_data is not None
        assert "parsed_html" in result.extracted_data
        assert len(result.extracted_data["parsed_html"]) == 500
        assert "html_length" in result.extracted_data
        assert result.extracted_data["html_length"] == 1000

    def test_test_ajax_endpoint_handles_parsing_error(
        self,
        mock_fetcher: Mock,
        mock_ajax_parser: Mock,
        mock_html_parser: Mock,
    ) -> None:
        """Test testing AJAX endpoint handles parsing errors gracefully."""
        # Arrange
        url = "https://example.com/get/years?make=Honda"
        mock_ajax_parser.parse.side_effect = AJAXParsingError("Parse failed")
        tester = EndpointTester(mock_fetcher, mock_ajax_parser, mock_html_parser)

        # Act
        result = tester.test_endpoint(url, EndpointType.AJAX)

        # Assert
        assert result.success is True
        assert result.extracted_data is not None
        assert "error" in result.extracted_data


class TestEndpointTesterErrorHandling:
    """Test EndpointTester error handling."""

    def test_test_endpoint_handles_network_error(
        self,
        mock_fetcher: Mock,
        mock_ajax_parser: Mock,
        mock_html_parser: Mock,
    ) -> None:
        """Test test_endpoint handles network errors."""
        # Arrange
        url = "https://example.com/items/3951"
        mock_fetcher.fetch.side_effect = httpx.RequestError("Network error")
        tester = EndpointTester(mock_fetcher, mock_ajax_parser, mock_html_parser)

        # Act
        result = tester.test_endpoint(url, EndpointType.DETAIL)

        # Assert
        assert result.success is False
        assert result.error_message is not None
        assert "Network error" in result.error_message

    def test_test_endpoint_handles_http_error(
        self,
        mock_fetcher: Mock,
        mock_ajax_parser: Mock,
        mock_html_parser: Mock,
    ) -> None:
        """Test test_endpoint handles HTTP errors."""
        # Arrange
        url = "https://example.com/items/3951"
        mock_fetcher.fetch.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=Mock(),
            response=Mock(status_code=404),
        )
        tester = EndpointTester(mock_fetcher, mock_ajax_parser, mock_html_parser)

        # Act
        result = tester.test_endpoint(url, EndpointType.DETAIL)

        # Assert
        assert result.success is False
        assert result.error_message is not None

    def test_test_endpoint_handles_timeout_error(
        self,
        mock_fetcher: Mock,
        mock_ajax_parser: Mock,
        mock_html_parser: Mock,
    ) -> None:
        """Test test_endpoint handles timeout errors."""
        # Arrange
        url = "https://example.com/items/3951"
        mock_fetcher.fetch.side_effect = httpx.TimeoutException("Timeout")
        tester = EndpointTester(mock_fetcher, mock_ajax_parser, mock_html_parser)

        # Act
        result = tester.test_endpoint(url, EndpointType.DETAIL)

        # Assert
        assert result.success is False
        assert result.error_message is not None
        assert "Timeout" in result.error_message


# ============================================================================
# ResultFormatter Tests
# ============================================================================


class TestResultFormatterInit:
    """Test ResultFormatter initialization."""

    def test_init_sets_console(self, mocker: MockerFixture) -> None:
        """Test __init__ sets console instance."""
        # Arrange
        mock_console = mocker.Mock()

        # Act
        formatter = ResultFormatter(mock_console)

        # Assert
        assert formatter.console is mock_console


class TestResultFormatterDisplaySuccess:
    """Test ResultFormatter success display."""

    def test_display_result_shows_success_for_successful_test(self, mocker: MockerFixture) -> None:
        """Test display_result shows success output for successful test."""
        # Arrange
        mock_console = mocker.Mock()
        formatter = ResultFormatter(mock_console)
        result = EndpointTestResult("https://example.com/items/3951", EndpointType.DETAIL)
        result.success = True
        result.status_code = 200
        result.response_time = 1.234
        result.content_length = 5000
        result.extracted_data = {"sku": "CSF-3951"}

        # Act
        formatter.display_result(result)

        # Assert
        assert mock_console.print.call_count >= 2
        assert mock_console.print.called

    def test_display_success_includes_response_details(self, mocker: MockerFixture) -> None:
        """Test _display_success includes response details in output."""
        # Arrange
        mock_console = mocker.Mock()
        formatter = ResultFormatter(mock_console)
        result = EndpointTestResult("https://example.com/items/3951", EndpointType.DETAIL)
        result.success = True
        result.status_code = 200
        result.response_time = 1.234
        result.content_length = 5000

        # Act
        formatter.display_result(result)

        # Assert
        mock_console.print.assert_called()


class TestResultFormatterDisplayError:
    """Test ResultFormatter error display."""

    def test_display_result_shows_error_for_failed_test(self, mocker: MockerFixture) -> None:
        """Test display_result shows error output for failed test."""
        # Arrange
        mock_console = mocker.Mock()
        formatter = ResultFormatter(mock_console)
        result = EndpointTestResult("https://example.com/items/3951", EndpointType.DETAIL)
        result.success = False
        result.error_message = "Network error"

        # Act
        formatter.display_result(result)

        # Assert
        assert mock_console.print.call_count >= 2
        assert mock_console.print.called


class TestResultFormatterSaveContent:
    """Test ResultFormatter save content functionality."""

    def test_save_content_creates_file(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test save_content creates file with response content."""
        # Arrange
        mock_console = mocker.Mock()
        formatter = ResultFormatter(mock_console)
        result = EndpointTestResult("https://example.com/items/3951", EndpointType.DETAIL)
        result.content = "<html><body>Test Content</body></html>"
        output_path = tmp_path / "response.html"

        # Act
        formatter.save_content(result, output_path)

        # Assert
        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert content == result.content

    def test_save_content_creates_parent_directories(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Test save_content creates parent directories if needed."""
        # Arrange
        mock_console = mocker.Mock()
        formatter = ResultFormatter(mock_console)
        result = EndpointTestResult("https://example.com/items/3951", EndpointType.DETAIL)
        result.content = "<html><body>Test</body></html>"
        output_path = tmp_path / "nested" / "dir" / "response.html"

        # Act
        formatter.save_content(result, output_path)

        # Assert
        assert output_path.exists()
        assert output_path.parent.exists()

    def test_save_content_displays_success_message(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Test save_content displays success message."""
        # Arrange
        mock_console = mocker.Mock()
        formatter = ResultFormatter(mock_console)
        result = EndpointTestResult("https://example.com/items/3951", EndpointType.DETAIL)
        result.content = "<html><body>Test</body></html>"
        output_path = tmp_path / "response.html"

        # Act
        formatter.save_content(result, output_path)

        # Assert
        mock_console.print.assert_called()
        call_args = mock_console.print.call_args[0][0]
        assert "Content saved to:" in call_args

    def test_save_content_handles_os_error(self, mocker: MockerFixture) -> None:
        """Test save_content handles OS errors gracefully."""
        # Arrange
        mock_console = mocker.Mock()
        formatter = ResultFormatter(mock_console)
        result = EndpointTestResult("https://example.com/items/3951", EndpointType.DETAIL)
        result.content = "<html><body>Test</body></html>"
        invalid_path = Path("/invalid/path/that/does/not/exist/file.html")

        # Act
        formatter.save_content(result, invalid_path)

        # Assert
        mock_console.print.assert_called()
        call_args = mock_console.print.call_args[0][0]
        assert "Failed to save content:" in call_args
