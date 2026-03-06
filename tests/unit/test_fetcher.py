"""Unit tests for RespectfulFetcher.

Tests cover:
- Initialization with correct settings
- HTTP requests with delays
- User-agent headers
- Successful responses
- HTTP error handling
- Retry logic (including smart 404 skip)
- Rate limiting timing
- Browser fetching (persistent browser, scroll, retries)
- Context manager cleanup
- Content hash change detection (check_etag)
- HTML normalization for stable hashing
- Async batch ETag checking (async_check_etags)
"""

import asyncio
import hashlib
import time
from unittest.mock import Mock

import httpx
import pytest
from playwright.sync_api import Browser, Page, Playwright
from pytest_mock import MockerFixture

from src.scraper.fetcher import (
    BROWSER_MAX_RETRIES,
    RespectfulFetcher,
    _is_retryable_browser_error,
    _is_retryable_http_error,
)


class TestRespectfulFetcherInit:
    """Test RespectfulFetcher initialization."""

    def test_init_creates_instance_with_correct_settings(self) -> None:
        """Test __init__() creates instance with correct settings."""
        # Arrange & Act
        fetcher = RespectfulFetcher()

        # Assert
        assert fetcher.MIN_DELAY_SECONDS == 0.3
        assert fetcher.MAX_DELAY_SECONDS == 0.8
        assert fetcher.BROWSER_MIN_DELAY_SECONDS == 1.0
        assert fetcher.BROWSER_MAX_DELAY_SECONDS == 3.0
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
        # Verify delays are reasonable (HTTP mode: 0.3-0.8s range)
        assert all(0.1 <= delay <= 1.0 for delay in sleep_calls)

        # Cleanup
        fetcher.close()

    def test_fetch_skips_delay_when_enough_time_passed(self, mocker: MockerFixture) -> None:
        """Test fetch() skips delay when elapsed time exceeds min delay."""
        # Arrange
        mock_sleep = mocker.patch("src.scraper.fetcher.time.sleep")
        mock_time = mocker.patch("src.scraper.fetcher.time.time")
        # First request: time() sets _last_request_time = 1.0
        # Second request: time() returns 2.0, elapsed = 1.0s > MIN_DELAY 0.3s
        # Third call: time() updates _last_request_time = 2.0
        mock_time.side_effect = [1.0, 2.0, 2.0]

        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.content = b"<html>test</html>"
        mock_response.raise_for_status = Mock()

        fetcher = RespectfulFetcher()
        mocker.patch.object(fetcher.client, "get", return_value=mock_response)

        # Act
        fetcher.fetch("https://example.com/first")
        fetcher.fetch("https://example.com/second")

        # Assert — no rate-limit sleep since elapsed (1.0s) > MIN_DELAY (0.3s)
        mock_sleep.assert_not_called()

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
        mock_page.evaluate = Mock()
        mock_page.wait_for_load_state = Mock()
        mock_page.close = Mock()

        mock_context = Mock()
        mock_context.new_page.return_value = mock_page

        mock_browser = Mock(spec=Browser)
        mock_browser.new_context.return_value = mock_context

        mock_playwright = Mock(spec=Playwright)
        mock_playwright.chromium.launch.return_value = mock_browser

        mock_sync_playwright = mocker.patch("src.scraper.fetcher.sync_playwright")
        mock_sync_playwright.return_value.start.return_value = mock_playwright

        fetcher = RespectfulFetcher()

        # Act
        html = fetcher.fetch_with_browser("https://example.com")

        # Assert
        assert html == "<html><body>Browser content</body></html>"
        mock_playwright.chromium.launch.assert_called_once_with(headless=True)
        mock_browser.new_context.assert_called_once_with(
            user_agent="CSF-Parts-Scraper/1.0 (contact@example.com)"
        )
        mock_page.goto.assert_called_once_with(
            "https://example.com", wait_until="networkidle", timeout=30000
        )
        mock_page.content.assert_called_once()
        mock_page.close.assert_called_once()

        # Cleanup
        fetcher.close()

    def test_fetch_with_browser_handles_navigation_error(self, mocker: MockerFixture) -> None:
        """Test fetch_with_browser() raises immediately for non-retryable errors."""
        # Arrange
        mocker.patch("src.scraper.fetcher.time.sleep")

        mock_page = Mock(spec=Page)
        mock_page.goto = Mock(side_effect=Exception("Protocol error: permission denied"))
        mock_page.close = Mock()

        mock_context = Mock()
        mock_context.new_page.return_value = mock_page

        mock_browser = Mock(spec=Browser)
        mock_browser.new_context.return_value = mock_context

        mock_playwright = Mock(spec=Playwright)
        mock_playwright.chromium.launch.return_value = mock_browser

        mock_sync_playwright = mocker.patch("src.scraper.fetcher.sync_playwright")
        mock_sync_playwright.return_value.start.return_value = mock_playwright

        fetcher = RespectfulFetcher()

        # Act & Assert - Non-retryable error raises immediately
        with pytest.raises(Exception, match="Protocol error: permission denied"):
            fetcher.fetch_with_browser("https://example.com")

        # Page should still be closed via finally block
        mock_page.close.assert_called_once()

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
        # Second request checks: elapsed = 1.5 - 1.0 = 0.5s < BROWSER_MIN_DELAY 1.0s
        fetcher.fetch_with_browser("https://example.com/second")

        # Assert
        # Should apply delay on second request (elapsed 0.5s < BROWSER_MIN_DELAY 1.0s)
        assert mock_sleep.call_count >= 1
        # Verify the delay is in the expected range (browser mode: 1-3s)
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
        # First request: time() to set _last_request_time = 1.0
        # Second request: time() to check elapsed (returns 1.1, so elapsed = 0.1s < 0.3s)
        # Third call: time() to update _last_request_time = 1.1
        mock_time.side_effect = [1.0, 1.1, 1.1]  # 0.1s elapsed

        mock_random = mocker.patch("src.scraper.fetcher.random.uniform")
        mock_random.return_value = 0.5  # Fixed delay for testing

        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.content = b"<html>test</html>"
        mock_response.raise_for_status = Mock()

        fetcher = RespectfulFetcher()
        mocker.patch.object(fetcher.client, "get", return_value=mock_response)

        # Act
        fetcher.fetch("https://example.com/first")
        # After first request, _last_request_time = 1.0
        # Second request: elapsed = 1.1 - 1.0 = 0.1s < MIN_DELAY 0.3s → delay applied
        fetcher.fetch("https://example.com/second")

        # Assert
        # Should call uniform with (min_delay - elapsed, max_delay)
        # = (0.3 - 0.1, 0.8) = (0.2, 0.8)
        assert mock_random.call_count >= 1, "random.uniform should be called for rate limiting"
        call_args = [call[0] for call in mock_random.call_args_list]
        assert any(abs(args[0] - 0.2) < 0.01 and abs(args[1] - 0.8) < 0.01 for args in call_args), (
            f"Expected uniform(0.2, 0.8), got {call_args}"
        )
        mock_sleep.assert_called_with(0.5)

        # Cleanup
        fetcher.close()


class TestSmartHTTPRetry:
    """Test smart HTTP retry logic that skips non-retryable errors."""

    def test_is_retryable_http_error_returns_false_for_404(self) -> None:
        """Test _is_retryable_http_error returns False for 404."""
        # Arrange
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 404
        error = httpx.HTTPStatusError(
            "Not Found",
            request=Mock(spec=httpx.Request),
            response=mock_response,
        )

        # Act
        result = _is_retryable_http_error(error)

        # Assert
        assert result is False

    def test_is_retryable_http_error_returns_false_for_403(self) -> None:
        """Test _is_retryable_http_error returns False for 403."""
        # Arrange
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 403
        error = httpx.HTTPStatusError(
            "Forbidden",
            request=Mock(spec=httpx.Request),
            response=mock_response,
        )

        # Act
        result = _is_retryable_http_error(error)

        # Assert
        assert result is False

    def test_is_retryable_http_error_returns_true_for_429(self) -> None:
        """Test _is_retryable_http_error returns True for 429 (rate limit)."""
        # Arrange
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 429
        error = httpx.HTTPStatusError(
            "Too Many Requests",
            request=Mock(spec=httpx.Request),
            response=mock_response,
        )

        # Act
        result = _is_retryable_http_error(error)

        # Assert
        assert result is True

    def test_is_retryable_http_error_returns_true_for_500(self) -> None:
        """Test _is_retryable_http_error returns True for 500."""
        # Arrange
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 500
        error = httpx.HTTPStatusError(
            "Internal Server Error",
            request=Mock(spec=httpx.Request),
            response=mock_response,
        )

        # Act
        result = _is_retryable_http_error(error)

        # Assert
        assert result is True

    def test_is_retryable_http_error_returns_true_for_non_http_error(self) -> None:
        """Test _is_retryable_http_error returns True for network errors."""
        # Arrange
        error = httpx.ConnectError("Connection refused")

        # Act
        result = _is_retryable_http_error(error)

        # Assert
        assert result is True

    def test_fetch_does_not_retry_on_404(self, mocker: MockerFixture) -> None:
        """Test fetch() does not retry on 404 errors."""
        # Arrange
        mocker.patch("src.scraper.fetcher.time.sleep")
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 404
        mock_response.headers = {}

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
            fetcher.fetch("https://example.com/missing")

        # Should only try once (no retry for 404)
        assert fetcher.client.get.call_count == 1
        assert exc_info.value.response.status_code == 404

        # Cleanup
        fetcher.close()


class TestBrowserErrorClassification:
    """Test _is_retryable_browser_error classification."""

    def test_timeout_error_is_retryable(self) -> None:
        """Test timeout errors are classified as retryable."""
        assert _is_retryable_browser_error(Exception("Navigation timeout exceeded"))

    def test_net_err_is_retryable(self) -> None:
        """Test net::err_ errors are classified as retryable."""
        assert _is_retryable_browser_error(Exception("net::err_connection_reset"))

    def test_navigation_failed_is_retryable(self) -> None:
        """Test navigation failed errors are classified as retryable."""
        assert _is_retryable_browser_error(Exception("navigation failed"))

    def test_page_crashed_is_retryable(self) -> None:
        """Test page crashed errors are classified as retryable."""
        assert _is_retryable_browser_error(Exception("page crashed"))

    def test_unknown_error_is_not_retryable(self) -> None:
        """Test unknown errors are classified as non-retryable."""
        assert not _is_retryable_browser_error(Exception("Something completely different"))

    def test_value_error_is_not_retryable(self) -> None:
        """Test ValueError is classified as non-retryable."""
        assert not _is_retryable_browser_error(ValueError("invalid argument"))


class TestPersistentBrowser:
    """Test persistent browser lifecycle management."""

    def test_browser_reuse_across_calls(self, mocker: MockerFixture) -> None:
        """Test browser is reused across multiple fetch_with_browser calls."""
        # Arrange
        mocker.patch("src.scraper.fetcher.time.sleep")

        mock_page = Mock(spec=Page)
        mock_page.content.return_value = "<html>test</html>"
        mock_page.goto = Mock()
        mock_page.evaluate = Mock()
        mock_page.wait_for_load_state = Mock()
        mock_page.close = Mock()

        mock_context = Mock()
        mock_context.new_page.return_value = mock_page

        mock_browser = Mock(spec=Browser)
        mock_browser.new_context.return_value = mock_context

        mock_playwright = Mock(spec=Playwright)
        mock_playwright.chromium.launch.return_value = mock_browser

        mock_sync_playwright = mocker.patch("src.scraper.fetcher.sync_playwright")
        mock_sync_playwright.return_value.start.return_value = mock_playwright

        fetcher = RespectfulFetcher()

        # Act - Make two calls
        fetcher.fetch_with_browser("https://example.com/first")
        fetcher.fetch_with_browser("https://example.com/second")

        # Assert - Browser launched only once
        mock_playwright.chromium.launch.assert_called_once()
        # But two pages were created
        assert mock_context.new_page.call_count == 2
        # And both pages were closed
        assert mock_page.close.call_count == 2

        # Cleanup
        fetcher.close()

    def test_close_cleans_up_browser(self, mocker: MockerFixture) -> None:
        """Test close() properly cleans up browser context, browser, and playwright."""
        # Arrange
        mocker.patch("src.scraper.fetcher.time.sleep")

        mock_page = Mock(spec=Page)
        mock_page.content.return_value = "<html>test</html>"
        mock_page.goto = Mock()
        mock_page.evaluate = Mock()
        mock_page.wait_for_load_state = Mock()
        mock_page.close = Mock()

        mock_context = Mock()
        mock_context.new_page.return_value = mock_page

        mock_browser = Mock(spec=Browser)
        mock_browser.new_context.return_value = mock_context

        mock_playwright = Mock(spec=Playwright)
        mock_playwright.chromium.launch.return_value = mock_browser

        mock_sync_playwright = mocker.patch("src.scraper.fetcher.sync_playwright")
        mock_sync_playwright.return_value.start.return_value = mock_playwright

        fetcher = RespectfulFetcher()

        # Initialize browser by making a call
        fetcher.fetch_with_browser("https://example.com")

        # Act
        fetcher.close()

        # Assert - All resources cleaned up in order
        mock_context.close.assert_called_once()
        mock_browser.close.assert_called_once()
        mock_playwright.stop.assert_called_once()

    def test_fetch_with_browser_retries_on_timeout(self, mocker: MockerFixture) -> None:
        """Test fetch_with_browser retries on timeout error."""
        # Arrange
        mocker.patch("src.scraper.fetcher.time.sleep")

        mock_page_fail = Mock(spec=Page)
        mock_page_fail.goto = Mock(side_effect=Exception("Navigation timeout exceeded"))
        mock_page_fail.close = Mock()

        mock_page_success = Mock(spec=Page)
        mock_page_success.content.return_value = "<html>success</html>"
        mock_page_success.goto = Mock()
        mock_page_success.evaluate = Mock()
        mock_page_success.wait_for_load_state = Mock()
        mock_page_success.close = Mock()

        mock_context = Mock()
        mock_context.new_page.side_effect = [mock_page_fail, mock_page_success]

        mock_browser = Mock(spec=Browser)
        mock_browser.new_context.return_value = mock_context

        mock_playwright = Mock(spec=Playwright)
        mock_playwright.chromium.launch.return_value = mock_browser

        mock_sync_playwright = mocker.patch("src.scraper.fetcher.sync_playwright")
        mock_sync_playwright.return_value.start.return_value = mock_playwright

        fetcher = RespectfulFetcher()

        # Act
        html = fetcher.fetch_with_browser("https://example.com")

        # Assert
        assert html == "<html>success</html>"
        # Two pages created (one failed, one succeeded)
        assert mock_context.new_page.call_count == 2
        # Both pages closed
        mock_page_fail.close.assert_called_once()
        mock_page_success.close.assert_called_once()

        # Cleanup
        fetcher.close()

    def test_fetch_with_browser_scrolls_to_bottom(self, mocker: MockerFixture) -> None:
        """Test fetch_with_browser calls scroll-to-bottom."""
        # Arrange
        mocker.patch("src.scraper.fetcher.time.sleep")

        mock_page = Mock(spec=Page)
        mock_page.content.return_value = "<html>test</html>"
        mock_page.goto = Mock()
        mock_page.evaluate = Mock()
        mock_page.wait_for_load_state = Mock()
        mock_page.close = Mock()

        mock_context = Mock()
        mock_context.new_page.return_value = mock_page

        mock_browser = Mock(spec=Browser)
        mock_browser.new_context.return_value = mock_context

        mock_playwright = Mock(spec=Playwright)
        mock_playwright.chromium.launch.return_value = mock_browser

        mock_sync_playwright = mocker.patch("src.scraper.fetcher.sync_playwright")
        mock_sync_playwright.return_value.start.return_value = mock_playwright

        fetcher = RespectfulFetcher()

        # Act
        fetcher.fetch_with_browser("https://example.com")

        # Assert - scroll was called
        mock_page.evaluate.assert_called_once_with("window.scrollTo(0, document.body.scrollHeight)")
        # networkidle waited after scroll
        mock_page.wait_for_load_state.assert_called_once_with("networkidle")

        # Cleanup
        fetcher.close()

    def test_fetch_with_browser_raises_on_non_retryable_error(self, mocker: MockerFixture) -> None:
        """Test fetch_with_browser raises immediately on non-retryable error."""
        # Arrange
        mocker.patch("src.scraper.fetcher.time.sleep")

        mock_page = Mock(spec=Page)
        mock_page.goto = Mock(side_effect=ValueError("non-retryable error"))
        mock_page.close = Mock()

        mock_context = Mock()
        mock_context.new_page.return_value = mock_page

        mock_browser = Mock(spec=Browser)
        mock_browser.new_context.return_value = mock_context

        mock_playwright = Mock(spec=Playwright)
        mock_playwright.chromium.launch.return_value = mock_browser

        mock_sync_playwright = mocker.patch("src.scraper.fetcher.sync_playwright")
        mock_sync_playwright.return_value.start.return_value = mock_playwright

        fetcher = RespectfulFetcher()

        # Act & Assert
        with pytest.raises(ValueError, match="non-retryable error"):
            fetcher.fetch_with_browser("https://example.com")

        # Only one attempt (no retry)
        assert mock_context.new_page.call_count == 1
        mock_page.close.assert_called_once()

        # Cleanup
        fetcher.close()

    def test_fetch_with_browser_raises_after_all_retries_exhausted(
        self, mocker: MockerFixture
    ) -> None:
        """Test fetch_with_browser raises RuntimeError after all retries exhausted."""
        # Arrange
        mocker.patch("src.scraper.fetcher.time.sleep")

        mock_page = Mock(spec=Page)
        mock_page.goto = Mock(side_effect=Exception("Navigation timeout exceeded"))
        mock_page.close = Mock()

        mock_context = Mock()
        mock_context.new_page.return_value = mock_page

        mock_browser = Mock(spec=Browser)
        mock_browser.new_context.return_value = mock_context

        mock_playwright = Mock(spec=Playwright)
        mock_playwright.chromium.launch.return_value = mock_browser

        mock_sync_playwright = mocker.patch("src.scraper.fetcher.sync_playwright")
        mock_sync_playwright.return_value.start.return_value = mock_playwright

        fetcher = RespectfulFetcher()

        # Act & Assert
        with pytest.raises(RuntimeError, match=f"Browser fetch failed after {BROWSER_MAX_RETRIES}"):
            fetcher.fetch_with_browser("https://example.com")

        # All retries were attempted
        assert mock_context.new_page.call_count == BROWSER_MAX_RETRIES
        assert mock_page.close.call_count == BROWSER_MAX_RETRIES

        # Cleanup
        fetcher.close()


class TestNormalizeHtml:
    """Test RespectfulFetcher._normalize_html() static method."""

    def test_normalize_html_strips_csrf_tokens(self) -> None:
        """Test _normalize_html removes CSRF meta tag content."""
        # Arrange
        html = '<meta name="csrf-token" content="abc123XYZ+/=" />'

        # Act
        result = RespectfulFetcher._normalize_html(html)  # noqa: SLF001

        # Assert
        assert 'content=""' in result
        assert "abc123XYZ+/=" not in result

    def test_normalize_html_strips_authenticity_tokens(self) -> None:
        """Test _normalize_html removes form authenticity token values."""
        # Arrange
        html = '<input type="hidden" name="authenticity_token" value="secretToken123+/=" />'

        # Act
        result = RespectfulFetcher._normalize_html(html)  # noqa: SLF001

        # Assert
        assert 'value=""' in result
        assert "secretToken123+/=" not in result

    def test_normalize_html_preserves_other_content(self) -> None:
        """Test _normalize_html preserves non-token HTML content."""
        # Arrange
        html = '<div class="product"><h1>Radiator CSF-3951</h1></div>'

        # Act
        result = RespectfulFetcher._normalize_html(html)  # noqa: SLF001

        # Assert
        assert result == html


class TestCheckEtag:
    """Test RespectfulFetcher.check_etag() content change detection."""

    def test_check_etag_returns_changed_true_for_first_check(self, mocker: MockerFixture) -> None:
        """Test check_etag returns (True, hash) when no previous hash exists."""
        # Arrange
        mocker.patch("src.scraper.fetcher.time.sleep")
        mocker.patch("src.scraper.fetcher.time.time", return_value=0.0)

        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = "<html><body>Content</body></html>"
        mock_response.raise_for_status = Mock()

        fetcher = RespectfulFetcher()
        mocker.patch.object(fetcher.client, "get", return_value=mock_response)

        # Act
        changed, current_hash = fetcher.check_etag("https://example.com", None)

        # Assert
        assert changed is True
        assert isinstance(current_hash, str)
        assert len(current_hash) == 32  # MD5 hex digest length

        # Cleanup
        fetcher.close()

    def test_check_etag_returns_changed_false_for_same_content(self, mocker: MockerFixture) -> None:
        """Test check_etag returns (False, hash) when content is unchanged."""
        # Arrange
        mocker.patch("src.scraper.fetcher.time.sleep")
        mocker.patch("src.scraper.fetcher.time.time", return_value=0.0)

        html = "<html><body>Same Content</body></html>"
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = html
        mock_response.raise_for_status = Mock()

        fetcher = RespectfulFetcher()
        mocker.patch.object(fetcher.client, "get", return_value=mock_response)

        # First check to get the hash
        _, first_hash = fetcher.check_etag("https://example.com", None)

        # Act - check again with same content
        changed, second_hash = fetcher.check_etag("https://example.com", first_hash)

        # Assert
        assert changed is False
        assert second_hash == first_hash

        # Cleanup
        fetcher.close()

    def test_check_etag_returns_changed_true_for_different_content(
        self, mocker: MockerFixture
    ) -> None:
        """Test check_etag returns (True, new_hash) when content has changed."""
        # Arrange
        mocker.patch("src.scraper.fetcher.time.sleep")
        mocker.patch("src.scraper.fetcher.time.time", return_value=0.0)

        mock_response_1 = Mock(spec=httpx.Response)
        mock_response_1.status_code = 200
        mock_response_1.text = "<html><body>Original</body></html>"
        mock_response_1.raise_for_status = Mock()

        mock_response_2 = Mock(spec=httpx.Response)
        mock_response_2.status_code = 200
        mock_response_2.text = "<html><body>Updated</body></html>"
        mock_response_2.raise_for_status = Mock()

        fetcher = RespectfulFetcher()
        mocker.patch.object(fetcher.client, "get", side_effect=[mock_response_1, mock_response_2])

        # First check
        _, first_hash = fetcher.check_etag("https://example.com", None)

        # Act - check with different content
        changed, second_hash = fetcher.check_etag("https://example.com", first_hash)

        # Assert
        assert changed is True
        assert second_hash != first_hash

        # Cleanup
        fetcher.close()

    def test_check_etag_returns_changed_true_on_http_error(self, mocker: MockerFixture) -> None:
        """Test check_etag returns (True, previous_hash) on HTTP error."""
        # Arrange
        mocker.patch("src.scraper.fetcher.time.sleep")
        mocker.patch("src.scraper.fetcher.time.time", return_value=0.0)

        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 500
        mock_response.raise_for_status = Mock(
            side_effect=httpx.HTTPStatusError(
                "Server Error",
                request=Mock(spec=httpx.Request),
                response=mock_response,
            )
        )

        fetcher = RespectfulFetcher()
        mocker.patch.object(fetcher.client, "get", return_value=mock_response)

        previous_hash = "abc123"

        # Act
        changed, returned_hash = fetcher.check_etag("https://example.com", previous_hash)

        # Assert - on error, assume changed and return previous hash
        assert changed is True
        assert returned_hash == previous_hash

        # Cleanup
        fetcher.close()


class TestAsyncCheckEtags:
    """Test RespectfulFetcher.async_check_etags() concurrent batch checking."""

    async def test_async_check_etags_returns_results_for_all_urls(
        self, mocker: MockerFixture
    ) -> None:
        """Test async_check_etags returns correct (changed, hash) for each URL."""
        # Arrange
        mocker.patch("src.scraper.fetcher.asyncio.sleep", return_value=None)

        html_a = "<html><body>Page A</body></html>"
        html_b = "<html><body>Page B</body></html>"
        hash_a = hashlib.md5(html_a.encode()).hexdigest()  # noqa: S324

        mock_response_a = httpx.Response(200, text=html_a, request=httpx.Request("GET", "http://a"))
        mock_response_b = httpx.Response(200, text=html_b, request=httpx.Request("GET", "http://b"))

        async def mock_get(url: str, **kwargs: object) -> httpx.Response:
            if "a" in url:
                return mock_response_a
            return mock_response_b

        mock_client = mocker.AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = mocker.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mocker.AsyncMock(return_value=False)
        mocker.patch("src.scraper.fetcher.httpx.AsyncClient", return_value=mock_client)

        fetcher = RespectfulFetcher()

        urls_and_hashes: list[tuple[str, str | None]] = [
            ("https://example.com/a", hash_a),  # unchanged
            ("https://example.com/b", None),  # first check → changed
            ("https://example.com/a2", "stale_hash"),  # changed (hash mismatch)
        ]

        # Act
        results = await fetcher.async_check_etags(urls_and_hashes, progress_every=100)

        # Assert
        assert len(results) == 3
        # URL a: same hash → unchanged
        assert results[0] == (False, hash_a)
        # URL b: no previous hash → changed
        assert results[1][0] is True
        assert isinstance(results[1][1], str)
        # URL a2: different previous hash → changed
        assert results[2][0] is True

        # Cleanup
        fetcher.close()

    async def test_async_check_etags_respects_concurrency_limit(
        self, mocker: MockerFixture
    ) -> None:
        """Test that semaphore limits in-flight requests to concurrency."""
        # Arrange
        mocker.patch("src.scraper.fetcher.asyncio.sleep", return_value=None)

        peak_concurrent = 0
        current_concurrent = 0
        concurrency_lock = asyncio.Lock()

        async def mock_get(url: str, **kwargs: object) -> httpx.Response:
            nonlocal peak_concurrent, current_concurrent
            async with concurrency_lock:
                current_concurrent += 1
                peak_concurrent = max(peak_concurrent, current_concurrent)
            # Simulate work
            await asyncio.sleep(0)
            async with concurrency_lock:
                current_concurrent -= 1
            return httpx.Response(
                200,
                text="<html>ok</html>",
                request=httpx.Request("GET", url),
            )

        mock_client = mocker.AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = mocker.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mocker.AsyncMock(return_value=False)
        mocker.patch("src.scraper.fetcher.httpx.AsyncClient", return_value=mock_client)

        fetcher = RespectfulFetcher()

        # 20 URLs but concurrency=3
        urls_and_hashes: list[tuple[str, str | None]] = [
            (f"https://example.com/{i}", None) for i in range(20)
        ]

        # Act
        results = await fetcher.async_check_etags(
            urls_and_hashes, concurrency=3, progress_every=100
        )

        # Assert
        assert len(results) == 20
        assert peak_concurrent <= 3

        # Cleanup
        fetcher.close()

    async def test_async_check_etags_handles_http_errors(self, mocker: MockerFixture) -> None:
        """Test that HTTP errors return (True, previous_hash) gracefully."""
        # Arrange
        mocker.patch("src.scraper.fetcher.asyncio.sleep", return_value=None)

        async def mock_get(url: str, **kwargs: object) -> httpx.Response:
            msg = "Connection refused"
            raise httpx.ConnectError(msg)

        mock_client = mocker.AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = mocker.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mocker.AsyncMock(return_value=False)
        mocker.patch("src.scraper.fetcher.httpx.AsyncClient", return_value=mock_client)

        fetcher = RespectfulFetcher()

        urls_and_hashes: list[tuple[str, str | None]] = [
            ("https://example.com/1", "prev_hash_1"),
            ("https://example.com/2", None),
        ]

        # Act
        results = await fetcher.async_check_etags(urls_and_hashes, progress_every=100)

        # Assert — on error, assume changed and return previous hash (or "")
        assert results[0] == (True, "prev_hash_1")
        assert results[1] == (True, "")

        # Cleanup
        fetcher.close()

    async def test_async_check_etags_logs_progress(self, mocker: MockerFixture) -> None:
        """Test that progress logging fires at correct intervals."""
        # Arrange
        mocker.patch("src.scraper.fetcher.asyncio.sleep", return_value=None)

        async def mock_get(url: str, **kwargs: object) -> httpx.Response:
            return httpx.Response(
                200,
                text="<html>ok</html>",
                request=httpx.Request("GET", url),
            )

        mock_client = mocker.AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = mocker.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mocker.AsyncMock(return_value=False)
        mocker.patch("src.scraper.fetcher.httpx.AsyncClient", return_value=mock_client)

        mock_logger = mocker.patch("src.scraper.fetcher.logger")

        fetcher = RespectfulFetcher()

        # 5 URLs with progress_every=2
        urls_and_hashes: list[tuple[str, str | None]] = [
            (f"https://example.com/{i}", None) for i in range(5)
        ]

        # Act
        await fetcher.async_check_etags(urls_and_hashes, progress_every=2)

        # Assert — progress logged at 2, 4, and 5 (final)
        progress_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call.args and call.args[0] == "etag_check_progress"
        ]
        completed_values = [call.kwargs["completed"] for call in progress_calls]
        assert 2 in completed_values
        assert 4 in completed_values
        assert 5 in completed_values

        # Cleanup
        fetcher.close()
