"""HTTP fetcher with respectful scraping practices.

This module implements respectful web scraping with:
- Rate limiting (0.3-0.8s for HTTP, 1-3s for browser fetches)
- Polite user-agent
- Exponential backoff on errors
- Request timeout
- Persistent browser for efficiency (with resource blocking)
- Smart retry (skip non-retryable HTTP errors like 404)
- Lightweight content-hash checks for change detection
"""

import asyncio
import hashlib
import random
import re
import time
from typing import Final

import httpx
import structlog
from playwright.sync_api import Browser, BrowserContext, Playwright, sync_playwright
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

logger = structlog.get_logger()

# Browser retry constants
BROWSER_MAX_RETRIES: Final[int] = 3
BROWSER_BACKOFF_BASE: Final[int] = 2


def _is_retryable_http_error(exception: BaseException) -> bool:
    """Determine if an HTTP error should be retried.

    Returns False for client errors (4xx except 429), True for everything else.
    This prevents wasting retries on permanent failures like 404 Not Found.

    Args:
        exception: The exception to check

    Returns:
        True if the request should be retried, False otherwise
    """
    if isinstance(exception, httpx.HTTPStatusError):
        status = exception.response.status_code
        http_too_many_requests = 429
        min_client_error = 400
        max_client_error = 499
        # Don't retry 4xx errors (client errors) except 429 (rate limit)
        if min_client_error <= status <= max_client_error and status != http_too_many_requests:
            return False
    # Retry everything else (5xx, network errors, timeouts, etc.)
    return True


def _is_retryable_browser_error(error: BaseException) -> bool:
    """Classify whether a browser error is retryable.

    Checks error message for known transient patterns like timeouts
    and network failures vs permanent errors.

    Args:
        error: The exception to classify

    Returns:
        True if the error is likely transient and worth retrying
    """
    error_str = str(error).lower()
    retryable_patterns = [
        "timeout",
        "net::err_",
        "navigation failed",
        "navigating frame was detached",
        "page crashed",
        "browser has been closed",
        "connection refused",
        "connection reset",
        "target closed",
    ]
    return any(pattern in error_str for pattern in retryable_patterns)


class RespectfulFetcher:
    """HTTP fetcher with built-in respectful scraping practices.

    Implements rate limiting, retries, and error handling to ensure
    we don't overwhelm the target server. Uses a persistent browser
    instance for efficiency across multiple fetch_with_browser calls.

    Attributes:
        MIN_DELAY_SECONDS: Minimum delay between requests
        MAX_DELAY_SECONDS: Maximum delay between requests
        USER_AGENT: Descriptive user-agent string
        MAX_RETRIES: Maximum number of retry attempts
        TIMEOUT_SECONDS: Request timeout
    """

    MIN_DELAY_SECONDS: Final[float] = 0.3
    MAX_DELAY_SECONDS: Final[float] = 0.8
    BROWSER_MIN_DELAY_SECONDS: Final[float] = 1.0
    BROWSER_MAX_DELAY_SECONDS: Final[float] = 3.0
    USER_AGENT: Final[str] = "CSF-Parts-Scraper/1.0 (contact@example.com)"
    MAX_RETRIES: Final[int] = 3
    TIMEOUT_SECONDS: Final[int] = 30

    def __init__(self) -> None:
        """Initialize fetcher with HTTP client and lazy browser fields."""
        self.client = httpx.Client(
            headers={"User-Agent": self.USER_AGENT},
            timeout=self.TIMEOUT_SECONDS,
            follow_redirects=True,
        )
        self._last_request_time: float = 0

        # Persistent browser lifecycle (lazy-initialized)
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._browser_context: BrowserContext | None = None

    def _ensure_browser(self) -> tuple[Browser, BrowserContext]:
        """Lazily initialize persistent Playwright browser on first use.

        Blocks images, stylesheets, fonts, and other non-HTML resources
        via route interception since the parser only needs HTML structure.

        Returns:
            Tuple of (browser, browser_context) objects

        Note:
            Uses sync_playwright().start() instead of context manager
            so the browser persists across multiple calls.
        """
        if self._browser is None:
            pw = sync_playwright().start()
            self._playwright = pw
            self._browser = pw.chromium.launch(headless=True)
            self._browser_context = self._browser.new_context(user_agent=self.USER_AGENT)
            self._browser_context.route(
                "**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,ttf,eot,css}",
                lambda route: route.abort(),
            )
            logger.info("browser_initialized")

        assert self._browser is not None  # noqa: S101
        assert self._browser_context is not None  # noqa: S101
        return self._browser, self._browser_context

    def _apply_rate_limit(self, *, browser: bool = False) -> None:
        """Apply rate limiting delay between requests.

        Uses shorter delays for lightweight HTTP requests and longer
        delays for browser-driven fetches that put more load on the server.

        Args:
            browser: If True, use longer browser-appropriate delays (1-3s).
                     If False (default), use shorter HTTP delays (0.3-0.8s).
        """
        min_delay = self.BROWSER_MIN_DELAY_SECONDS if browser else self.MIN_DELAY_SECONDS
        max_delay = self.BROWSER_MAX_DELAY_SECONDS if browser else self.MAX_DELAY_SECONDS

        if self._last_request_time > 0:
            elapsed = time.time() - self._last_request_time

            if elapsed < min_delay:
                delay = random.uniform(min_delay - elapsed, max_delay)  # noqa: S311
                logger.debug(
                    "rate_limit_delay",
                    delay=round(delay, 2),
                    elapsed_since_last=round(elapsed, 2),
                    mode="browser" if browser else "http",
                )
                time.sleep(delay)

        self._last_request_time = time.time()

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(MAX_RETRIES),
        retry=retry_if_exception(_is_retryable_http_error),
        reraise=True,
    )
    def fetch(self, url: str) -> httpx.Response:
        """Fetch URL with rate limiting and retries.

        Skips retries for non-retryable errors (4xx except 429).

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

    @staticmethod
    def _normalize_html(html: str) -> str:
        """Strip volatile tokens from HTML for stable content hashing.

        The target server embeds per-request CSRF tokens and authenticity
        tokens that change on every response. This method removes them so
        that content hashes are stable across requests when actual page
        content hasn't changed.

        Args:
            html: Raw HTML response text

        Returns:
            HTML with volatile tokens replaced by empty strings
        """
        # Remove CSRF meta tag content
        normalized = re.sub(r'content="[A-Za-z0-9+/=]+"', 'content=""', html)
        # Remove form authenticity token values
        return re.sub(r'value="[A-Za-z0-9+/=]+"', 'value=""', normalized)

    def check_etag(self, url: str, previous_hash: str | None) -> tuple[bool, str]:
        """Check if a page has changed using lightweight HTTP content hashing.

        Performs a plain HTTP GET (no browser) and computes a content hash
        of the normalized HTML. Compares against the previous hash to detect
        changes without needing Playwright.

        The server's native ETags change on every request (due to CSRF tokens),
        so we compute our own stable hashes from the normalized HTML content.

        Args:
            url: Application page URL to check
            previous_hash: Previously stored content hash, or None for first check

        Returns:
            Tuple of (changed: bool, current_hash: str)
            - (True, hash) if content changed or no previous hash exists
            - (False, hash) if content is unchanged
        """
        self._apply_rate_limit()

        logger.debug("checking_content_hash", url=url)

        try:
            response = self.client.get(
                url,
                headers={"Accept": "text/html,application/xhtml+xml"},
            )
            response.raise_for_status()
        except httpx.HTTPError:
            logger.warning("content_hash_check_failed", url=url)
            # On error, assume changed so we don't skip it
            return True, previous_hash or ""

        normalized = self._normalize_html(response.text)
        current_hash = hashlib.md5(normalized.encode()).hexdigest()  # noqa: S324

        if previous_hash is None:
            logger.debug("content_hash_first_check", url=url, hash=current_hash)
            return True, current_hash

        changed = current_hash != previous_hash

        if changed:
            logger.debug("content_hash_changed", url=url)
        else:
            logger.debug("content_hash_unchanged", url=url)

        return changed, current_hash

    async def async_check_etags(
        self,
        urls_and_hashes: list[tuple[str, str | None]],
        concurrency: int = 10,
        progress_every: int = 500,
    ) -> list[tuple[bool, str]]:
        """Check multiple pages for changes concurrently using async HTTP.

        Runs up to ``concurrency`` lightweight GET requests in parallel,
        each with a random 0.3-0.8s delay to stay respectful. Results
        are returned in the same order as the input list.

        Args:
            urls_and_hashes: List of (url, previous_hash_or_None) pairs
            concurrency: Maximum number of simultaneous requests
            progress_every: Log progress every N completions

        Returns:
            List of (changed, current_hash) tuples, one per input pair
        """
        semaphore = asyncio.Semaphore(concurrency)
        completed_count = 0
        total = len(urls_and_hashes)
        count_lock = asyncio.Lock()

        async with httpx.AsyncClient(
            headers={"User-Agent": self.USER_AGENT},
            timeout=self.TIMEOUT_SECONDS,
            follow_redirects=True,
        ) as async_client:

            async def _check_one(url: str, previous_hash: str | None) -> tuple[bool, str]:
                nonlocal completed_count

                async with semaphore:
                    delay = random.uniform(  # noqa: S311
                        self.MIN_DELAY_SECONDS, self.MAX_DELAY_SECONDS
                    )
                    await asyncio.sleep(delay)

                    try:
                        response = await async_client.get(
                            url,
                            headers={"Accept": "text/html,application/xhtml+xml"},
                        )
                        response.raise_for_status()
                    except httpx.HTTPError:
                        logger.warning("async_content_hash_check_failed", url=url)
                        changed = True
                        current_hash = previous_hash or ""
                    else:
                        normalized = self._normalize_html(response.text)
                        current_hash = hashlib.md5(  # noqa: S324
                            normalized.encode()
                        ).hexdigest()
                        changed = previous_hash is None or current_hash != previous_hash

                async with count_lock:
                    completed_count += 1
                    if completed_count % progress_every == 0 or completed_count == total:
                        logger.info(
                            "etag_check_progress",
                            completed=completed_count,
                            total=total,
                        )

                return changed, current_hash

            tasks = [_check_one(url, prev_hash) for url, prev_hash in urls_and_hashes]
            return list(await asyncio.gather(*tasks))

    def fetch_with_browser(self, url: str) -> str:
        """Fetch URL using persistent headless browser for JavaScript content.

        Uses a persistent browser instance (created on first call) and creates
        a fresh page per request. Includes retry logic with exponential backoff
        for transient errors. Uses ``domcontentloaded`` wait strategy since
        only the HTML DOM is needed, not images or analytics scripts.

        Args:
            url: URL to fetch

        Returns:
            Rendered HTML content

        Raises:
            Exception: If browser fetch fails after all retries

        Example:
            >>> fetcher = RespectfulFetcher()
            >>> html = fetcher.fetch_with_browser("https://example.com")
            >>> "<!DOCTYPE html>" in html
            True
        """
        self._apply_rate_limit(browser=True)

        logger.info("fetching_url_with_browser", url=url)

        _browser, browser_context = self._ensure_browser()

        last_error: BaseException | None = None

        for attempt in range(BROWSER_MAX_RETRIES):
            page = browser_context.new_page()
            try:
                page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=self.TIMEOUT_SECONDS * 1000,
                )

                content: str = page.content()

                logger.info(
                    "browser_fetch_success",
                    url=url,
                    content_length=len(content),
                    attempt=attempt + 1,
                )

            except Exception as e:
                last_error = e
                logger.warning(
                    "browser_fetch_attempt_failed",
                    url=url,
                    attempt=attempt + 1,
                    max_attempts=BROWSER_MAX_RETRIES,
                    error=str(e),
                    error_type=type(e).__name__,
                )

                if not _is_retryable_browser_error(e):
                    logger.exception(
                        "browser_fetch_non_retryable",
                        url=url,
                        error=str(e),
                    )
                    raise

                if attempt < BROWSER_MAX_RETRIES - 1:
                    backoff = BROWSER_BACKOFF_BASE ** (attempt + 1)
                    logger.info("browser_fetch_retrying", backoff_seconds=backoff)
                    time.sleep(backoff)

            else:
                return content

            finally:
                page.close()

        # All retries exhausted
        msg = f"Browser fetch failed after {BROWSER_MAX_RETRIES} attempts: {last_error}"
        raise RuntimeError(msg) from last_error

    def close(self) -> None:
        """Close HTTP client, browser, and release all resources."""
        # Clean up browser resources in order: context → browser → playwright
        if self._browser_context is not None:
            self._browser_context.close()
            self._browser_context = None

        if self._browser is not None:
            self._browser.close()
            self._browser = None

        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None

        self.client.close()
        logger.debug("fetcher_closed")

    def __enter__(self) -> "RespectfulFetcher":
        """Context manager entry."""
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager exit."""
        self.close()
