"""Persistent store for application page content hashes.

Maps application URLs to content hashes so that subsequent scraping runs can
detect which pages have changed. Originally designed for HTTP ETags, but the
target server generates per-request ETags (due to CSRF tokens), so we compute
our own hashes from the normalized HTML content instead.

Storage format (JSON):
    {"https://csf.mycarparts.com/applications/8430": "a1b2c3...", ...}
"""

import json
from pathlib import Path

import structlog

logger = structlog.get_logger()


class ETagStore:
    """Persists content hashes for lightweight change detection.

    Stores a mapping of application URL -> content hash in a JSON file.
    On subsequent runs, we can compare the stored hash against a fresh
    HTTP response to determine if the page content has changed, avoiding
    expensive Playwright browser scrapes for unchanged pages.

    Attributes:
        store_path: Path to the JSON persistence file
    """

    def __init__(self, store_path: Path) -> None:
        """Initialize the store.

        Args:
            store_path: Path to the JSON file for persistence
        """
        self.store_path = store_path
        self._data: dict[str, str] = {}
        self.load()

    def get(self, url: str) -> str | None:
        """Get stored content hash for a URL.

        Args:
            url: Application page URL

        Returns:
            Content hash string or None if not stored
        """
        return self._data.get(url)

    def set(self, url: str, content_hash: str) -> None:
        """Store content hash for a URL.

        Args:
            url: Application page URL
            content_hash: MD5 hex digest of normalized page content
        """
        self._data[url] = content_hash

    def has_data(self) -> bool:
        """Check if the store has any entries.

        Returns:
            True if at least one URL->hash mapping exists
        """
        return len(self._data) > 0

    def save(self) -> None:
        """Persist current data to disk."""
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        with self.store_path.open("w") as f:
            json.dump(self._data, f, indent=2)

        logger.debug(
            "etag_store_saved",
            path=str(self.store_path),
            entries=len(self._data),
        )

    def load(self) -> None:
        """Load data from disk if the file exists."""
        if not self.store_path.exists():
            logger.debug("etag_store_not_found", path=str(self.store_path))
            return

        with self.store_path.open() as f:
            loaded = json.load(f)

        if not isinstance(loaded, dict):
            logger.warning(
                "etag_store_invalid_format",
                path=str(self.store_path),
                got_type=type(loaded).__name__,
            )
            return

        self._data = loaded

        logger.debug(
            "etag_store_loaded",
            path=str(self.store_path),
            entries=len(self._data),
        )

    def stats(self) -> dict[str, int]:
        """Get store statistics.

        Returns:
            Dict with total entry count
        """
        return {"total_entries": len(self._data)}
