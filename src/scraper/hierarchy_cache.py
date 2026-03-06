"""Persistent cache for hierarchy data (years → models) used in incremental runs.

Stores two mappings:
1. years URL → MD5 hash of the AJAX response body
2. make_id → list of hierarchy entry dicts

When the hash for a make's years URL matches the stored value, all model
enumeration for that make can be skipped and the cached hierarchy entries
reused directly.

Storage format (JSON):
    {
        "url_hashes": {"https://…/get_year_by_make/3": "a1b2c3…", …},
        "make_entries": {"3": [{…}, …], …}
    }
"""

import json
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


class HierarchyCache:
    """Caches hierarchy data for lightweight change detection at the years level.

    On each run we hash the ``get_year_by_make`` AJAX response for every make.
    If the hash matches the previous run, the full model enumeration for that
    make is skipped and previously cached hierarchy entries are returned instead.

    Attributes:
        cache_path: Path to the JSON persistence file
    """

    def __init__(self, cache_path: Path) -> None:
        """Initialize the cache.

        Args:
            cache_path: Path to the JSON file for persistence
        """
        self.cache_path = cache_path
        self._url_hashes: dict[str, str] = {}
        self._make_entries: dict[str, list[dict[str, Any]]] = {}
        self._load()

    def get_url_hash(self, url: str) -> str | None:
        """Get stored response hash for a years URL.

        Args:
            url: The ``get_year_by_make`` URL

        Returns:
            MD5 hex digest or None if not stored
        """
        return self._url_hashes.get(url)

    def set_url_hash(self, url: str, hash_value: str) -> None:
        """Store response hash for a years URL.

        Args:
            url: The ``get_year_by_make`` URL
            hash_value: MD5 hex digest of the response body
        """
        self._url_hashes[url] = hash_value

    def get_make_hierarchy(self, make_id: int) -> list[dict[str, Any]] | None:
        """Get cached hierarchy entries for a make.

        Args:
            make_id: Make ID (e.g. 3 for Honda)

        Returns:
            List of hierarchy entry dicts or None if not cached
        """
        entries = self._make_entries.get(str(make_id))
        if entries is None:
            return None
        return entries

    def set_make_hierarchy(self, make_id: int, entries: list[dict[str, Any]]) -> None:
        """Store hierarchy entries for a make.

        Args:
            make_id: Make ID
            entries: List of hierarchy entry dicts for this make
        """
        self._make_entries[str(make_id)] = entries

    def has_data(self) -> bool:
        """Check if the cache has any entries.

        Returns:
            True if at least one URL hash is stored
        """
        return len(self._url_hashes) > 0

    def save(self) -> None:
        """Persist current data to disk."""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with self.cache_path.open("w") as f:
            json.dump(
                {
                    "url_hashes": self._url_hashes,
                    "make_entries": self._make_entries,
                },
                f,
                indent=2,
            )

        logger.debug(
            "hierarchy_cache_saved",
            path=str(self.cache_path),
            url_hashes=len(self._url_hashes),
            make_entries=len(self._make_entries),
        )

    def clear(self) -> None:
        """Clear all cached data (in-memory only; call save() to persist)."""
        self._url_hashes.clear()
        self._make_entries.clear()

    def _load(self) -> None:
        """Load data from disk if the file exists."""
        if not self.cache_path.exists():
            logger.debug("hierarchy_cache_not_found", path=str(self.cache_path))
            return

        with self.cache_path.open() as f:
            loaded = json.load(f)

        if not isinstance(loaded, dict):
            logger.warning(
                "hierarchy_cache_invalid_format",
                path=str(self.cache_path),
                got_type=type(loaded).__name__,
            )
            return

        self._url_hashes = loaded.get("url_hashes", {})
        self._make_entries = loaded.get("make_entries", {})

        logger.debug(
            "hierarchy_cache_loaded",
            path=str(self.cache_path),
            url_hashes=len(self._url_hashes),
            make_entries=len(self._make_entries),
        )
