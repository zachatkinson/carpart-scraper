"""Unit tests for RespectfulFetcher.

Tests cover:
- Initialization with correct settings
- HTTP requests with delays
- User-agent headers
- Successful responses
- HTTP error handling
- Retry logic
- Rate limiting timing
- Browser fetching
- Context manager cleanup
"""

import time
from unittest.mock import Mock

import httpx
import pytest
from playwright.sync_api import Browser, Page, Playwright
from pytest_mock import MockerFixture

from src.scraper.fetcher import RespectfulFetcher


class TestRespectfulFetcherInit:
    """Test RespectfulFetcher initialization."""

    def test_init_creates_instance_with_correct_settings(self) -> None:
        """Test __init__() creates instance with correct settings."""
        # Arrange & Act
        fetcher = RespectfulFetcher()

        # Assert
        assert fetcher.MIN_DELAY_SECONDS == 1.0
        assert fetcher.MAX_DELAY_SECONDS == 3.0
        assert fetcher.USER_AGENT == "CSF-Parts-Scraper/1.0 (contact@example.com)"
        assert fetcher.MAX_RETRIES == 3
        assert fetcher.TIMEOUT_SECONDS == 30
        assert isinstance(fetcher.client, httpx.Client)
        assert fetcher._last_request_time == 0  # noqa: SLF001

        # Cleanup
        fetcher.close()

    def test_init_configures_http_client_with_user_agent(self) -> None:
        """Test __init__() configures HTTP client with user agent."""
        # Arrange & Act
        fetcher = RespectfulFetcher()

        # Assert
        assert fetcher.client.headers["User-Agent"] == "CSF-Parts-Scraper/1.0 (contact@example.com)"

        # Cleanup
        fetcher.close()

    def test_init_configures_http_client_with_timeout(self) -> None:
        """Test __init__() configures HTTP client with timeout."""
        # Arrange & Act
        fetcher = RespectfulFetcher()

        # Assert
        assert fetcher.client.timeout.read == 30.0

        # Cleanup
        fetcher.close()

    def test_init_configures_http_client_with_redirects(self) -> None:
        """Test __init__() configures HTTP client to follow redirects."""
        # Arrange & Act
        fetcher = RespectfulFetcher()

        # Assert
        assert fetcher.client.follow_redirects is True

        # Cleanup
        fetcher.close()


class TestRespectfulFetcherFetch:
    """Test RespectfulFetcher.fetch() method."""

    def test_fetch_makes_http_request_with_delay(self, mocker: MockerFixture) -> None:
        """Test fetch() makes HTTP request with delay."""
        # Arrange
        mock_sleep = mocker.patch("src.scraper.fetcher.time.sleep")
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.content = b"<html>test</html>"
        mock_response.raise_for_status = Mock()

        fetcher = RespectfulFetcher()
        mocker.patch.object(fetcher.client, "get", return_value=mock_response)

        # Act
        response = fetcher.fetch("https://example.com")

        # Assert
        fetcher.client.get.assert_called_once_with("https://example.com")  # type: ignore[attr-defined]
        assert response == mock_response
        # First request should not sleep (no previous request)
        mock_sleep.assert_not_called()

        # Cleanup
        fetcher.close()

    def test_fetch_includes_user_agent_header(self, mocker: MockerFixture) -> None:
        """Test fetch() includes user-agent header."""
        # Arrange
        mocker.patch("src.scraper.fetcher.time.sleep")
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.content = b"<html>test</html>"
        mock_response.raise_for_status = Mock()

        fetcher = RespectfulFetcher()
        mocker.patch.object(fetcher.client, "get", return_value=mock_response)

        # Act
        fetcher.fetch("https://example.com")

        # Assert
        assert fetcher.client.headers["User-Agent"] == "CSF-Parts-Scraper/1.0 (contact@example.com)"

        # Cleanup
        fetcher.close()

    def test_fetch_handles_successful_response_200(self, mocker: MockerFixture) -> None:
        """Test fetch() handles successful responses (200)."""
        # Arrange
        mocker.patch("src.scraper.fetcher.time.sleep")
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.content = b"<html>Success!</html>"
        mock_response.raise_for_status = Mock()

        fetcher = RespectfulFetcher()
        mocker.patch.object(fetcher.client, "get", return_value=mock_response)

        # Act
        response = fetcher.fetch("https://example.com")

        # Assert
        assert response.status_code == 200
        assert response.content == b"<html>Success!</html>"
        mock_response.raise_for_status.assert_called_once()

        # Cleanup
        fetcher.close()

    def test_fetch_handles_http_error_404(self, mocker: MockerFixture) -> None:
        """Test fetch() handles HTTP errors (404)."""
        # Arrange
        mocker.patch("src.scraper.fetcher.time.sleep")
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 404

        http_error = httpx.HTTPStatusError(
            "Not Found",
            request=Mock(spec=httpx.Request),
            response=mock_response,
        )
        mock_response.raise_for_status = Mock(side_effect=http_error)

        fetcher = RespectfulFetcher()
        mocker.patch.object(fetcher.client, "get", return_value=mock_response)

        # Act & Assert
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            fetcher.fetch("https://example.com/notfound")

        assert exc_info.value.response.status_code == 404

        # Cleanup
        fetcher.close()

    def test_fetch_handles_http_error_500(self, mocker: MockerFixture) -> None:
        """Test fetch() handles HTTP errors (500)."""
        # Arrange
        mocker.patch("src.scraper.fetcher.time.sleep")
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 500

        http_error = httpx.HTTPStatusError(
            "Internal Server Error",
            request=Mock(spec=httpx.Request),
            response=mock_response,
        )
        mock_response.raise_for_status = Mock(side_effect=http_error)

        fetcher = RespectfulFetcher()
        mocker.patch.object(fetcher.client, "get", return_value=mock_response)

        # Act & Assert
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            fetcher.fetch("https://example.com/error")

        assert exc_info.value.response.status_code == 500

        # Cleanup
        fetcher.close()

    def test_fetch_handles_rate_limit_429_with_retry_after(self, mocker: MockerFixture) -> None:
        """Test fetch() handles HTTP 429 with Retry-After header."""
        # Arrange
        mock_sleep = mocker.patch("src.scraper.fetcher.time.sleep")
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "5"}

        http_error = httpx.HTTPStatusError(
            "Too Many Requests",
            request=Mock(spec=httpx.Request),
            response=mock_response,
        )
        mock_response.raise_for_status = Mock(side_effect=http_error)

        fetcher = RespectfulFetcher()
        mocker.patch.object(fetcher.client, "get", return_value=mock_response)

        # Act & Assert
        with pytest.raises(httpx.HTTPStatusError):
            fetcher.fetch("https://example.com")

        # Assert sleep was called with retry-after value
        assert any(call[0][0] == 5 for call in mock_sleep.call_args_list)

        # Cleanup
        fetcher.close()

    def test_fetch_handles_rate_limit_429_without_retry_after(self, mocker: MockerFixture) -> None:
        """Test fetch() handles HTTP 429 without Retry-After header."""
        # Arrange
        mocker.patch("src.scraper.fetcher.time.sleep")
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 429
        mock_response.headers = {}  # No Retry-After header

        http_error = httpx.HTTPStatusError(
            "Too Many Requests",
            request=Mock(spec=httpx.Request),
            response=mock_response,
        )
        mock_response.raise_for_status = Mock(side_effect=http_error)

        fetcher = RespectfulFetcher()
        mocker.patch.object(fetcher.client, "get", return_value=mock_response)

        # Act & Assert
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            fetcher.fetch("https://example.com")

        assert exc_info.value.response.status_code == 429

        # Cleanup
        fetcher.close()

    def test_fetch_retries_on_failure_with_max_retries_3(self, mocker: MockerFixture) -> None:
        """Test fetch() retries on failure (test with max_retries=3)."""
        # Arrange
        mocker.patch("src.scraper.fetcher.time.sleep")
        mock_response_fail = Mock(spec=httpx.Response)
        mock_response_fail.status_code = 500

        http_error = httpx.HTTPStatusError(
            "Internal Server Error",
            request=Mock(spec=httpx.Request),
            response=mock_response_fail,
        )
        mock_response_fail.raise_for_status = Mock(side_effect=http_error)

        mock_response_success = Mock(spec=httpx.Response)
        mock_response_success.status_code = 200
        mock_response_success.content = b"<html>Success on retry!</html>"
        mock_response_success.raise_for_status = Mock()

        fetcher = RespectfulFetcher()
        # Fail twice, succeed on third attempt
        mocker.patch.object(
            fetcher.client,
            "get",
            side_effect=[mock_response_fail, mock_response_fail, mock_response_success],
        )

        # Act
        response = fetcher.fetch("https://example.com")

        # Assert
        assert fetcher.client.get.call_count == 3  # type: ignore[attr-defined]
        assert response.status_code == 200
        assert response.content == b"<html>Success on retry!</html>"

        # Cleanup
        fetcher.close()

    def test_fetch_raises_after_max_retries_exceeded(self, mocker: MockerFixture) -> None:
        """Test fetch() raises exception after max retries exceeded."""
        # Arrange
        mocker.patch("src.scraper.fetcher.time.sleep")
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 500

        http_error = httpx.HTTPStatusError(
            "Internal Server Error",
            request=Mock(spec=httpx.Request),
            response=mock_response,
        )
        mock_response.raise_for_status = Mock(side_effect=http_error)

        fetcher = RespectfulFetcher()
        mocker.patch.object(fetcher.client, "get", return_value=mock_response)

        # Act & Assert
        with pytest.raises(httpx.HTTPStatusError):
            fetcher.fetch("https://example.com")

        # Should try 3 times (MAX_RETRIES)
        assert fetcher.client.get.call_count == 3  # type: ignore[attr-defined]

        # Cleanup
        fetcher.close()

    def test_fetch_respects_delay_between_requests(self, mocker: MockerFixture) -> None:
        """Test fetch() respects delay between requests (test timing)."""
        # Arrange
        mock_sleep = mocker.patch("src.scraper.fetcher.time.sleep")
        # Don't mock time - let it run naturally to trigger the rate limiting logic

        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.content = b"<html>test</html>"
        mock_response.raise_for_status = Mock()

        fetcher = RespectfulFetcher()
        mocker.patch.object(fetcher.client, "get", return_value=mock_response)

        # Act
        start = time.time()
        fetcher.fetch("https://example.com/first")
        # Make second request immediately - should trigger rate limiting
        fetcher.fetch("https://example.com/second")
        _elapsed = time.time() - start

        # Assert
        # Second request should have been rate limited
        # We expect at least one sleep call for rate limiting
        assert mock_sleep.call_count >= 1
        # Total elapsed time should be at least the minimum delay (accounting for mocked sleep)
        # Since sleep is mocked, elapsed should be minimal but sleep was called
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        # Verify delays are reasonable (0.5-3.0s range based on implementation)
        assert all(0.4 <= delay <= 3.5 for delay in sleep_calls)

        # Cleanup
        fetcher.close()

    def test_fetch_applies_human_behavior_delay_when_enough_time_passed(
        self, mocker: MockerFixture
    ) -> None:
        """Test fetch() applies small delay even when enough time has passed."""
        # Arrange
        mock_sleep = mocker.patch("src.scraper.fetcher.time.sleep")
        # Allow real time to pass so we can test the human behavior delay

        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.content = b"<html>test</html>"
        mock_response.raise_for_status = Mock()

        fetcher = RespectfulFetcher()
        mocker.patch.object(fetcher.client, "get", return_value=mock_response)

        # Act
        fetcher.fetch("https://example.com/first")
        # Wait long enough that MIN_DELAY passes (simulating real delay with mock)
        time.sleep(1.1)  # Sleep for 1.1s (longer than MIN_DELAY of 1.0s)
        fetcher.fetch("https://example.com/second")

        # Assert
        # Should still apply human behavior delay (0.5-1.5s) even though enough time passed
        assert mock_sleep.call_count >= 1
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        # Human behavior delay is 0.5-1.5s
        assert any(0.4 <= delay <= 1.6 for delay in sleep_calls)

        # Cleanup
        fetcher.close()

    def test_fetch_handles_request_error(self, mocker: MockerFixture) -> None:
        """Test fetch() handles network request errors."""
        # Arrange
        mocker.patch("src.scraper.fetcher.time.sleep")
        request_error = httpx.RequestError("Connection failed")

        fetcher = RespectfulFetcher()
        mocker.patch.object(fetcher.client, "get", side_effect=request_error)

        # Act & Assert
        with pytest.raises(httpx.RequestError):
            fetcher.fetch("https://example.com")

        # Cleanup
        fetcher.close()

    def test_fetch_handles_timeout_error(self, mocker: MockerFixture) -> None:
        """Test fetch() handles timeout errors."""
        # Arrange
        mocker.patch("src.scraper.fetcher.time.sleep")
        timeout_error = httpx.TimeoutException("Request timeout")

        fetcher = RespectfulFetcher()
        mocker.patch.object(fetcher.client, "get", side_effect=timeout_error)

        # Act & Assert
        with pytest.raises(httpx.TimeoutException):
            fetcher.fetch("https://example.com")

        # Cleanup
        fetcher.close()

    def test_fetch_handles_connect_error(self, mocker: MockerFixture) -> None:
        """Test fetch() handles connection errors."""
        # Arrange
        mocker.patch("src.scraper.fetcher.time.sleep")
        connect_error = httpx.ConnectError("Failed to connect")

        fetcher = RespectfulFetcher()
        mocker.patch.object(fetcher.client, "get", side_effect=connect_error)

        # Act & Assert
        with pytest.raises(httpx.ConnectError):
            fetcher.fetch("https://example.com")

        # Cleanup
        fetcher.close()


class TestRespectfulFetcherBrowser:
    """Test RespectfulFetcher.fetch_with_browser() method."""

    def test_fetch_with_browser_returns_html(self, mocker: MockerFixture) -> None:
        """Test fetch_with_browser() returns HTML."""
        # Arrange
        mocker.patch("src.scraper.fetcher.time.sleep")

        mock_page = Mock(spec=Page)
        mock_page.content.return_value = "<html><body>Browser content</body></html>"
        mock_page.goto = Mock()

        mock_browser = Mock(spec=Browser)
        mock_browser.new_page.return_value = mock_page
        mock_browser.close = Mock()

        mock_playwright = Mock(spec=Playwright)
        mock_playwright.chromium.launch.return_value = mock_browser

        mock_sync_playwright = mocker.patch("src.scraper.fetcher.sync_playwright")
        mock_sync_playwright.return_value.__enter__.return_value = mock_playwright

        fetcher = RespectfulFetcher()

        # Act
        html = fetcher.fetch_with_browser("https://example.com")

        # Assert
        assert html == "<html><body>Browser content</body></html>"
        mock_playwright.chromium.launch.assert_called_once_with(headless=True)
        mock_browser.new_page.assert_called_once_with(
            user_agent="CSF-Parts-Scraper/1.0 (contact@example.com)"
        )
        mock_page.goto.assert_called_once_with(
            "https://example.com", wait_until="networkidle", timeout=30000
        )
        mock_page.content.assert_called_once()
        mock_browser.close.assert_called_once()

        # Cleanup
        fetcher.close()

    def test_fetch_with_browser_handles_navigation_error(self, mocker: MockerFixture) -> None:
        """Test fetch_with_browser() handles navigation errors."""
        # Arrange
        mocker.patch("src.scraper.fetcher.time.sleep")

        mock_page = Mock(spec=Page)
        mock_page.goto = Mock(side_effect=Exception("Navigation timeout"))

        mock_browser = Mock(spec=Browser)
        mock_browser.new_page.return_value = mock_page
        mock_browser.close = Mock()

        mock_playwright = Mock(spec=Playwright)
        mock_playwright.chromium.launch.return_value = mock_browser

        mock_sync_playwright = mocker.patch("src.scraper.fetcher.sync_playwright")
        mock_sync_playwright.return_value.__enter__.return_value = mock_playwright

        fetcher = RespectfulFetcher()

        # Act & Assert
        with pytest.raises(Exception, match="Navigation timeout"):
            fetcher.fetch_with_browser("https://example.com")

        # Browser should still be closed
        mock_browser.close.assert_called_once()

        # Cleanup
        fetcher.close()

    def test_fetch_with_browser_applies_rate_limit(self, mocker: MockerFixture) -> None:
        """Test fetch_with_browser() applies rate limiting."""
        # Arrange
        mock_sleep = mocker.patch("src.scraper.fetcher.time.sleep")
        mock_time = mocker.patch("src.scraper.fetcher.time.time")
        # Simulate time progression
        # First call: time() to set _last_request_time = 1.0 (non-zero!)
        # Second call: time() to check elapsed (returns 1.5, elapsed = 0.5s)
        # Third call: time() to update _last_request_time = 1.5
        mock_time.side_effect = [1.0, 1.5, 1.5]

        mock_page = Mock(spec=Page)
        mock_page.content.return_value = "<html>test</html>"
        mock_page.goto = Mock()

        mock_browser = Mock(spec=Browser)
        mock_browser.new_page.return_value = mock_page
        mock_browser.close = Mock()

        mock_playwright = Mock(spec=Playwright)
        mock_playwright.chromium.launch.return_value = mock_browser

        mock_sync_playwright = mocker.patch("src.scraper.fetcher.sync_playwright")
        mock_sync_playwright.return_value.__enter__.return_value = mock_playwright

        fetcher = RespectfulFetcher()

        # Act
        fetcher.fetch_with_browser("https://example.com/first")
        # After first request, _last_request_time = 1.0
        # Second request checks: elapsed = 1.5 - 1.0 = 0.5s < MIN_DELAY 1.0s
        fetcher.fetch_with_browser("https://example.com/second")

        # Assert
        # Should apply delay on second request (elapsed 0.5s < MIN_DELAY 1.0s)
        assert mock_sleep.call_count >= 1
        # Verify the delay is in the expected range (min_delay - elapsed to max_delay)
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        # Should delay between (1.0 - 0.5) = 0.5 and 3.0 seconds
        assert any(0.4 <= delay <= 3.5 for delay in sleep_calls)

        # Cleanup
        fetcher.close()


class TestRespectfulFetcherContextManager:
    """Test RespectfulFetcher context manager functionality."""

    def test_context_manager_properly_cleans_up(self, mocker: MockerFixture) -> None:
        """Test context manager properly cleans up Playwright."""
        # Arrange
        mocker.patch("src.scraper.fetcher.time.sleep")
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.content = b"<html>test</html>"
        mock_response.raise_for_status = Mock()

        # Act
        with RespectfulFetcher() as fetcher:
            mock_client_close = mocker.patch.object(fetcher.client, "close")
            mocker.patch.object(fetcher.client, "get", return_value=mock_response)
            fetcher.fetch("https://example.com")

        # Assert
        # Client should be closed on context manager exit
        mock_client_close.assert_called_once()

    def test_context_manager_enter_returns_fetcher(self) -> None:
        """Test context manager __enter__ returns fetcher instance."""
        # Arrange & Act
        with RespectfulFetcher() as fetcher:
            # Assert
            assert isinstance(fetcher, RespectfulFetcher)
            assert hasattr(fetcher, "fetch")
            assert hasattr(fetcher, "fetch_with_browser")

    def test_context_manager_exit_closes_client(self, mocker: MockerFixture) -> None:
        """Test context manager __exit__ closes HTTP client."""
        # Arrange
        fetcher = RespectfulFetcher()
        mock_close = mocker.patch.object(fetcher, "close")

        # Act
        fetcher.__enter__()
        fetcher.__exit__(None, None, None)

        # Assert
        mock_close.assert_called_once()

    def test_close_method_closes_http_client(self, mocker: MockerFixture) -> None:
        """Test close() method closes HTTP client."""
        # Arrange
        fetcher = RespectfulFetcher()
        mock_client_close = mocker.patch.object(fetcher.client, "close")

        # Act
        fetcher.close()

        # Assert
        mock_client_close.assert_called_once()


class TestRespectfulFetcherRateLimiting:
    """Test RespectfulFetcher rate limiting internals."""

    def test_first_request_has_no_previous_request_time(self, mocker: MockerFixture) -> None:
        """Test first request initializes last_request_time."""
        # Arrange
        mocker.patch("src.scraper.fetcher.time.sleep")
        mock_time = mocker.patch("src.scraper.fetcher.time.time")
        mock_time.return_value = 100.0

        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.content = b"<html>test</html>"
        mock_response.raise_for_status = Mock()

        fetcher = RespectfulFetcher()
        mocker.patch.object(fetcher.client, "get", return_value=mock_response)

        # Act
        assert fetcher._last_request_time == 0  # noqa: SLF001
        fetcher.fetch("https://example.com")

        # Assert
        assert fetcher._last_request_time == 100.0  # noqa: SLF001

        # Cleanup
        fetcher.close()

    def test_rate_limit_uses_random_delay(self, mocker: MockerFixture) -> None:
        """Test rate limiting uses random delay between MIN and MAX."""
        # Arrange
        mock_sleep = mocker.patch("src.scraper.fetcher.time.sleep")
        mock_time = mocker.patch("src.scraper.fetcher.time.time")
        # First request: time() to set _last_request_time = 1.0 (non-zero!)
        # Second request: time() to check elapsed (returns 1.5, so elapsed = 0.5s)
        # Third call: time() to update _last_request_time = 1.5
        mock_time.side_effect = [1.0, 1.5, 1.5]  # 0.5s elapsed

        mock_random = mocker.patch("src.scraper.fetcher.random.uniform")
        mock_random.return_value = 2.0  # Fixed delay for testing

        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.content = b"<html>test</html>"
        mock_response.raise_for_status = Mock()

        fetcher = RespectfulFetcher()
        mocker.patch.object(fetcher.client, "get", return_value=mock_response)

        # Act
        fetcher.fetch("https://example.com/first")
        # After first request, _last_request_time = 1.0
        # Second request checks elapsed time (1.5 - 1.0 = 0.5s < MIN_DELAY 1.0s)
        fetcher.fetch("https://example.com/second")

        # Assert
        # Should call uniform with (min_delay - elapsed, max_delay)
        # = (1.0 - 0.5, 3.0) = (0.5, 3.0)
        assert mock_random.call_count >= 1, "random.uniform should be called for rate limiting"
        # Check if any call matches our expected arguments
        call_args = [call[0] for call in mock_random.call_args_list]
        assert any(args == (0.5, 3.0) for args in call_args), (
            f"Expected uniform(0.5, 3.0), got {call_args}"
        )
        mock_sleep.assert_called_with(2.0)

        # Cleanup
        fetcher.close()
