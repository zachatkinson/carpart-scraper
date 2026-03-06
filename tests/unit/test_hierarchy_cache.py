"""Unit tests for HierarchyCache.

Tests cover:
- Load/save round-trip
- get/set for URL hashes and make hierarchy entries
- has_data detection
- Missing file creates empty cache
- clear() resets state
- Invalid file format handled gracefully
"""

import json
from pathlib import Path
from typing import Any

from src.scraper.hierarchy_cache import HierarchyCache


class TestHierarchyCacheLoadSave:
    """Test persistence (load/save) of hierarchy cache."""

    def test_save_and_load_round_trip(self, tmp_path: Path) -> None:
        """Test that saved data is restored on load."""
        # Arrange
        cache_path = tmp_path / "hierarchy_cache.json"
        cache = HierarchyCache(cache_path)
        cache.set_url_hash("https://example.com/get_year_by_make/3", "abc123")
        cache.set_make_hierarchy(3, [{"make": "Honda", "year": "2024", "model": "Civic"}])

        # Act
        cache.save()
        cache2 = HierarchyCache(cache_path)

        # Assert
        assert cache2.get_url_hash("https://example.com/get_year_by_make/3") == "abc123"
        entries = cache2.get_make_hierarchy(3)
        assert entries is not None
        assert len(entries) == 1
        assert entries[0]["make"] == "Honda"

    def test_save_creates_parent_directories(self, tmp_path: Path) -> None:
        """Test that save() creates parent directories if needed."""
        # Arrange
        cache_path = tmp_path / "nested" / "dir" / "cache.json"
        cache = HierarchyCache(cache_path)
        cache.set_url_hash("https://example.com", "hash1")

        # Act
        cache.save()

        # Assert
        assert cache_path.exists()

    def test_save_writes_valid_json(self, tmp_path: Path) -> None:
        """Test that save() writes parseable JSON with expected keys."""
        # Arrange
        cache_path = tmp_path / "cache.json"
        cache = HierarchyCache(cache_path)
        cache.set_url_hash("https://example.com", "hash1")
        cache.set_make_hierarchy(1, [{"make": "Ford"}])
        cache.save()

        # Act
        raw: dict[str, Any] = json.loads(cache_path.read_text())

        # Assert
        assert "url_hashes" in raw
        assert "make_entries" in raw
        assert raw["url_hashes"]["https://example.com"] == "hash1"


class TestHierarchyCacheGetSet:
    """Test get/set operations for URL hashes and make entries."""

    def test_get_url_hash_returns_none_for_unknown(self, tmp_path: Path) -> None:
        """Test get_url_hash() returns None for unstored URL."""
        # Arrange
        cache = HierarchyCache(tmp_path / "cache.json")

        # Act
        result = cache.get_url_hash("https://unknown.com")

        # Assert
        assert result is None

    def test_set_and_get_url_hash(self, tmp_path: Path) -> None:
        """Test set_url_hash() stores value retrievable by get_url_hash()."""
        # Arrange
        cache = HierarchyCache(tmp_path / "cache.json")

        # Act
        cache.set_url_hash("https://example.com/3", "deadbeef")

        # Assert
        assert cache.get_url_hash("https://example.com/3") == "deadbeef"

    def test_get_make_hierarchy_returns_none_for_unknown(self, tmp_path: Path) -> None:
        """Test get_make_hierarchy() returns None for uncached make."""
        # Arrange
        cache = HierarchyCache(tmp_path / "cache.json")

        # Act
        result = cache.get_make_hierarchy(99)

        # Assert
        assert result is None

    def test_set_and_get_make_hierarchy(self, tmp_path: Path) -> None:
        """Test set_make_hierarchy() stores entries retrievable by get_make_hierarchy()."""
        # Arrange
        cache = HierarchyCache(tmp_path / "cache.json")
        entries = [
            {"make_id": 3, "make": "Honda", "year": "2024", "model": "Civic"},
            {"make_id": 3, "make": "Honda", "year": "2024", "model": "Accord"},
        ]

        # Act
        cache.set_make_hierarchy(3, entries)

        # Assert
        result = cache.get_make_hierarchy(3)
        assert result is not None
        assert len(result) == 2

    def test_set_url_hash_overwrites_existing(self, tmp_path: Path) -> None:
        """Test that setting the same URL twice overwrites the hash."""
        # Arrange
        cache = HierarchyCache(tmp_path / "cache.json")
        cache.set_url_hash("https://example.com", "old_hash")

        # Act
        cache.set_url_hash("https://example.com", "new_hash")

        # Assert
        assert cache.get_url_hash("https://example.com") == "new_hash"


class TestHierarchyCacheHasData:
    """Test has_data() detection."""

    def test_empty_cache_has_no_data(self, tmp_path: Path) -> None:
        """Test has_data() returns False on empty cache."""
        # Arrange
        cache = HierarchyCache(tmp_path / "cache.json")

        # Act & Assert
        assert cache.has_data() is False

    def test_cache_with_hashes_has_data(self, tmp_path: Path) -> None:
        """Test has_data() returns True when URL hashes exist."""
        # Arrange
        cache = HierarchyCache(tmp_path / "cache.json")
        cache.set_url_hash("https://example.com", "hash1")

        # Act & Assert
        assert cache.has_data() is True


class TestHierarchyCacheClear:
    """Test clear() method."""

    def test_clear_resets_all_data(self, tmp_path: Path) -> None:
        """Test clear() removes all cached data."""
        # Arrange
        cache = HierarchyCache(tmp_path / "cache.json")
        cache.set_url_hash("https://example.com", "hash1")
        cache.set_make_hierarchy(3, [{"make": "Honda"}])

        # Act
        cache.clear()

        # Assert
        assert cache.has_data() is False
        assert cache.get_url_hash("https://example.com") is None
        assert cache.get_make_hierarchy(3) is None

    def test_clear_then_save_writes_empty(self, tmp_path: Path) -> None:
        """Test clear() + save() persists empty state."""
        # Arrange
        cache_path = tmp_path / "cache.json"
        cache = HierarchyCache(cache_path)
        cache.set_url_hash("https://example.com", "hash1")
        cache.save()

        # Act
        cache.clear()
        cache.save()

        # Assert
        cache2 = HierarchyCache(cache_path)
        assert cache2.has_data() is False


class TestHierarchyCacheMissingFile:
    """Test behavior when cache file doesn't exist."""

    def test_missing_file_creates_empty_cache(self, tmp_path: Path) -> None:
        """Test that a non-existent file produces an empty cache without error."""
        # Arrange & Act
        cache = HierarchyCache(tmp_path / "nonexistent.json")

        # Assert
        assert cache.has_data() is False
        assert cache.get_url_hash("anything") is None
        assert cache.get_make_hierarchy(1) is None


class TestHierarchyCacheInvalidFormat:
    """Test graceful handling of invalid cache files."""

    def test_non_dict_json_ignored(self, tmp_path: Path) -> None:
        """Test that a JSON file containing a non-dict is handled gracefully."""
        # Arrange
        cache_path = tmp_path / "cache.json"
        cache_path.write_text(json.dumps([1, 2, 3]))

        # Act
        cache = HierarchyCache(cache_path)

        # Assert
        assert cache.has_data() is False

    def test_dict_missing_keys_uses_defaults(self, tmp_path: Path) -> None:
        """Test that a dict without expected keys defaults to empty."""
        # Arrange
        cache_path = tmp_path / "cache.json"
        cache_path.write_text(json.dumps({"unexpected_key": "value"}))

        # Act
        cache = HierarchyCache(cache_path)

        # Assert
        assert cache.has_data() is False
        assert cache.get_make_hierarchy(1) is None
