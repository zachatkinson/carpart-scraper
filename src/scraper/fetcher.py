"""HTTP fetcher with respectful scraping practices.

This module implements respectful web scraping with:
- Rate limiting (1-3 second delays)
- Polite user-agent
- Exponential backoff on errors
- Request timeout
"""

import random
import time
from typing import Final

import httpx
import structlog
from playwright.sync_api import sync_playwright
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


class RespectfulFetcher:
    """HTTP fetcher with built-in respectful scraping practices.

    Implements rate limiting, retries, and error handling to ensure
    we don't overwhelm the target server.

    Attributes:
        MIN_DELAY_SECONDS: Minimum delay between requests
        MAX_DELAY_SECONDS: Maximum delay between requests
        USER_AGENT: Descriptive user-agent string
        MAX_RETRIES: Maximum number of retry attempts
        TIMEOUT_SECONDS: Request timeout
    """

    MIN_DELAY_SECONDS: Final[float] = 1.0
    MAX_DELAY_SECONDS: Final[float] = 3.0
    USER_AGENT: Final[str] = "CSF-Parts-Scraper/1.0 (contact@example.com)"
    MAX_RETRIES: Final[int] = 3
    TIMEOUT_SECONDS: Final[int] = 30

    def __init__(self) -> None:
        """Initialize fetcher with HTTP client."""
        self.client = httpx.Client(
            headers={"User-Agent": self.USER_AGENT},
            timeout=self.TIMEOUT_SECONDS,
            follow_redirects=True,
        )
        self._last_request_time: float = 0

    def _apply_rate_limit(self) -> None:
        """Apply rate limiting delay between requests.

        Ensures we wait 1-3 seconds between requests to be respectful.
        Uses random delay to mimic human behavior.
        """
        if self._last_request_time > 0:
            elapsed = time.time() - self._last_request_time
            min_delay = self.MIN_DELAY_SECONDS

            if elapsed < min_delay:
                delay = random.uniform(min_delay - elapsed, self.MAX_DELAY_SECONDS)  # noqa: S311
                logger.debug(
                    "rate_limit_delay",
                    delay=delay,
                    elapsed_since_last=elapsed,
                )
                time.sleep(delay)
            else:
                # Even if enough time has passed, add small random delay
                delay = random.uniform(0.5, 1.5)  # noqa: S311
                logger.debug("human_behavior_delay", delay=delay)
                time.sleep(delay)

        self._last_request_time = time.time()

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(MAX_RETRIES),
        reraise=True,
    )
    def fetch(self, url: str) -> httpx.Response:
        """Fetch URL with rate limiting and retries.

        Args:
            url: URL to fetch

        Returns:
            HTTP response

        Raises:
            httpx.HTTPError: If request fails after retries

        Example:
            >>> fetcher = RespectfulFetcher()
            >>> response = fetcher.fetch("https://example.com")
            >>> response.status_code
            200
        """
        self._apply_rate_limit()

        logger.info("fetching_url", url=url)

        try:
            response = self.client.get(url)
            response.raise_for_status()

            logger.info(
                "fetch_success",
                url=url,
                status_code=response.status_code,
                content_length=len(response.content),
            )

        except httpx.HTTPStatusError as e:
            logger.exception(
                "fetch_http_error",
                url=url,
                status_code=e.response.status_code,
                error=str(e),
            )

            # Handle rate limiting
            http_too_many_requests = 429
            if e.response.status_code == http_too_many_requests:
                retry_after = e.response.headers.get("Retry-After")
                if retry_after:
                    wait_seconds = int(retry_after)
                    logger.warning(
                        "rate_limited",
                        retry_after=wait_seconds,
                    )
                    time.sleep(wait_seconds)

            raise

        except httpx.RequestError as e:
            logger.exception(
                "fetch_request_error",
                url=url,
                error=str(e),
            )
            raise
        else:
            return response

    def fetch_with_browser(self, url: str) -> str:
        """Fetch URL using headless browser for JavaScript content.

        Args:
            url: URL to fetch

        Returns:
            Rendered HTML content

        Raises:
            Exception: If browser fetch fails

        Example:
            >>> fetcher = RespectfulFetcher()
            >>> html = fetcher.fetch_with_browser("https://example.com")
            >>> "<!DOCTYPE html>" in html
            True
        """
        self._apply_rate_limit()

        logger.info("fetching_url_with_browser", url=url)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=self.USER_AGENT)

            try:
                page.goto(url, wait_until="networkidle", timeout=self.TIMEOUT_SECONDS * 1000)
                content = page.content()

                logger.info(
                    "browser_fetch_success",
                    url=url,
                    content_length=len(content),
                )

                return content

            finally:
                browser.close()

    def close(self) -> None:
        """Close HTTP client and release resources."""
        self.client.close()
        logger.debug("fetcher_closed")

    def __enter__(self) -> "RespectfulFetcher":
        """Context manager entry."""
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager exit."""
        self.close()
