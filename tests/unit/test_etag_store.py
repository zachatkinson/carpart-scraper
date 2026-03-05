"""Unit tests for ETagStore.

Tests cover:
- Initialization (empty store, loading from disk)
- Get/set operations
- Persistence (save/load roundtrip)
- has_data() and stats() queries
- Edge cases (missing file, empty store)
"""

import json
from pathlib import Path

from src.scraper.etag_store import ETagStore


class TestETagStoreInit:
    """Test ETagStore initialization."""

    def test_init_creates_empty_store_when_file_missing(self, tmp_path: Path) -> None:
        """Test __init__() creates empty store when no file exists."""
        # Arrange
        store_path = tmp_path / "etags.json"

        # Act
        store = ETagStore(store_path)

        # Assert
        assert not store.has_data()
        assert store.stats() == {"total_entries": 0}

    def test_init_loads_existing_data_from_disk(self, tmp_path: Path) -> None:
        """Test __init__() loads data from existing JSON file."""
        # Arrange
        store_path = tmp_path / "etags.json"
        existing_data = {
            "https://example.com/applications/1": "abc123",
            "https://example.com/applications/2": "def456",
        }
        store_path.write_text(json.dumps(existing_data))

        # Act
        store = ETagStore(store_path)

        # Assert
        assert store.has_data()
        assert store.get("https://example.com/applications/1") == "abc123"
        assert store.get("https://example.com/applications/2") == "def456"


class TestETagStoreGetSet:
    """Test ETagStore get/set operations."""

    def test_get_returns_none_for_unknown_url(self, tmp_path: Path) -> None:
        """Test get() returns None for URLs not in the store."""
        # Arrange
        store = ETagStore(tmp_path / "etags.json")

        # Act
        result = store.get("https://example.com/unknown")

        # Assert
        assert result is None

    def test_set_stores_hash_retrievable_by_get(self, tmp_path: Path) -> None:
        """Test set() stores a hash that get() can retrieve."""
        # Arrange
        store = ETagStore(tmp_path / "etags.json")
        url = "https://csf.mycarparts.com/applications/8430"
        content_hash = "a1b2c3d4e5f6"

        # Act
        store.set(url, content_hash)

        # Assert
        assert store.get(url) == content_hash

    def test_set_overwrites_existing_hash(self, tmp_path: Path) -> None:
        """Test set() overwrites previously stored hash."""
        # Arrange
        store = ETagStore(tmp_path / "etags.json")
        url = "https://csf.mycarparts.com/applications/8430"
        store.set(url, "old_hash")

        # Act
        store.set(url, "new_hash")

        # Assert
        assert store.get(url) == "new_hash"


class TestETagStorePersistence:
    """Test ETagStore save/load roundtrip."""

    def test_save_creates_json_file(self, tmp_path: Path) -> None:
        """Test save() creates a JSON file on disk."""
        # Arrange
        store_path = tmp_path / "etags.json"
        store = ETagStore(store_path)
        store.set("https://example.com/1", "hash1")

        # Act
        store.save()

        # Assert
        assert store_path.exists()
        data = json.loads(store_path.read_text())
        assert data == {"https://example.com/1": "hash1"}

    def test_save_load_roundtrip_preserves_data(self, tmp_path: Path) -> None:
        """Test that data survives a save/load cycle."""
        # Arrange
        store_path = tmp_path / "etags.json"
        store1 = ETagStore(store_path)
        store1.set("https://example.com/1", "hash1")
        store1.set("https://example.com/2", "hash2")
        store1.save()

        # Act
        store2 = ETagStore(store_path)

        # Assert
        assert store2.get("https://example.com/1") == "hash1"
        assert store2.get("https://example.com/2") == "hash2"
        assert store2.stats() == {"total_entries": 2}

    def test_save_creates_parent_directories(self, tmp_path: Path) -> None:
        """Test save() creates parent directories if they don't exist."""
        # Arrange
        store_path = tmp_path / "nested" / "dir" / "etags.json"
        store = ETagStore(store_path)
        store.set("https://example.com/1", "hash1")

        # Act
        store.save()

        # Assert
        assert store_path.exists()


class TestETagStoreQueries:
    """Test ETagStore query methods."""

    def test_has_data_returns_false_for_empty_store(self, tmp_path: Path) -> None:
        """Test has_data() returns False when store is empty."""
        # Arrange
        store = ETagStore(tmp_path / "etags.json")

        # Act & Assert
        assert store.has_data() is False

    def test_has_data_returns_true_after_set(self, tmp_path: Path) -> None:
        """Test has_data() returns True after storing an entry."""
        # Arrange
        store = ETagStore(tmp_path / "etags.json")
        store.set("https://example.com/1", "hash1")

        # Act & Assert
        assert store.has_data() is True

    def test_stats_returns_correct_count(self, tmp_path: Path) -> None:
        """Test stats() returns accurate entry count."""
        # Arrange
        store = ETagStore(tmp_path / "etags.json")
        store.set("https://example.com/1", "hash1")
        store.set("https://example.com/2", "hash2")
        store.set("https://example.com/3", "hash3")

        # Act
        result = store.stats()

        # Assert
        assert result == {"total_entries": 3}
