"""Unit tests for ImageSyncer and sync strategies.

Tests cover:
- LocalFileSyncer: copies files, skips existing same-size, handles errors
- RemoteAPISyncer: uploads via REST API, handles batch failures
- ImageSyncer: orchestrates sync + cleanup, marks manifest entries
- SyncResult aggregation
"""

import json
from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest
from pytest_mock import MockerFixture

from src.scraper.image_processor import ImageProcessor
from src.scraper.image_syncer import ImageSyncer, LocalFileSyncer, RemoteAPISyncer

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def images_dir(tmp_path: Path) -> Path:
    """Provide a temporary images directory."""
    return tmp_path / "images"


@pytest.fixture
def wp_uploads_dir(tmp_path: Path) -> Path:
    """Provide a temporary WordPress uploads directory."""
    return tmp_path / "wp-content" / "uploads"


@pytest.fixture
def processor(images_dir: Path, mocker: MockerFixture) -> ImageProcessor:
    """Provide an ImageProcessor with a mock HTTP client."""
    proc = ImageProcessor(images_dir=images_dir)
    proc.client.close()
    proc.client = mocker.Mock(spec=httpx.Client)
    return proc


def _create_avif_file(avif_dir: Path, filename: str, content: bytes = b"fake-avif") -> Path:
    """Create a fake AVIF file in the avif directory."""
    avif_dir.mkdir(parents=True, exist_ok=True)
    path = avif_dir / filename
    path.write_bytes(content)
    return path


# ---------------------------------------------------------------------------
# LocalFileSyncer Tests
# ---------------------------------------------------------------------------


class TestLocalFileSyncer:
    """Test LocalFileSyncer copies files to WordPress uploads."""

    def test_copies_files_to_target_directory(self, tmp_path: Path, wp_uploads_dir: Path) -> None:
        """Files are copied to the correct WordPress target directory."""
        # Arrange
        syncer = LocalFileSyncer(wp_uploads_dir=wp_uploads_dir)
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        src_file = src_dir / "CSF-100_0.avif"
        src_file.write_bytes(b"avif-data")

        # Act
        result = syncer.sync_batch([src_file])

        # Assert
        assert result.uploaded == 1
        assert result.skipped == 0
        assert result.failed == 0
        dest = wp_uploads_dir / "csf-parts" / "images" / "avif" / "CSF-100_0.avif"
        assert dest.exists()
        assert dest.read_bytes() == b"avif-data"

    def test_skips_existing_file_with_same_size(self, tmp_path: Path, wp_uploads_dir: Path) -> None:
        """Files already at destination with same size are skipped."""
        # Arrange
        syncer = LocalFileSyncer(wp_uploads_dir=wp_uploads_dir)
        src_file = tmp_path / "CSF-100_0.avif"
        src_file.write_bytes(b"avif-data")

        # Pre-create destination with same content/size
        dest_dir = wp_uploads_dir / "csf-parts" / "images" / "avif"
        dest_dir.mkdir(parents=True)
        dest_file = dest_dir / "CSF-100_0.avif"
        dest_file.write_bytes(b"avif-data")

        # Act
        result = syncer.sync_batch([src_file])

        # Assert
        assert result.uploaded == 0
        assert result.skipped == 1

    def test_overwrites_existing_file_with_different_size(
        self, tmp_path: Path, wp_uploads_dir: Path
    ) -> None:
        """Files at destination with different size are overwritten."""
        # Arrange
        syncer = LocalFileSyncer(wp_uploads_dir=wp_uploads_dir)
        src_file = tmp_path / "CSF-100_0.avif"
        src_file.write_bytes(b"new-avif-data-longer")

        dest_dir = wp_uploads_dir / "csf-parts" / "images" / "avif"
        dest_dir.mkdir(parents=True)
        dest_file = dest_dir / "CSF-100_0.avif"
        dest_file.write_bytes(b"old-data")

        # Act
        result = syncer.sync_batch([src_file])

        # Assert
        assert result.uploaded == 1
        assert dest_file.read_bytes() == b"new-avif-data-longer"

    def test_verify_connection_creates_directory(self, wp_uploads_dir: Path) -> None:
        """verify_connection() creates target directory and returns True."""
        # Arrange
        syncer = LocalFileSyncer(wp_uploads_dir=wp_uploads_dir)

        # Act
        connected = syncer.verify_connection()

        # Assert
        assert connected is True
        assert syncer.target_dir.is_dir()

    def test_handles_multiple_files(self, tmp_path: Path, wp_uploads_dir: Path) -> None:
        """Multiple files are copied in a single batch."""
        # Arrange
        syncer = LocalFileSyncer(wp_uploads_dir=wp_uploads_dir)
        files = []
        for i in range(3):
            f = tmp_path / f"CSF-{i}_0.avif"
            f.write_bytes(f"data-{i}".encode())
            files.append(f)

        # Act
        result = syncer.sync_batch(files)

        # Assert
        assert result.uploaded == 3
        assert result.skipped == 0
        assert result.failed == 0


# ---------------------------------------------------------------------------
# RemoteAPISyncer Tests
# ---------------------------------------------------------------------------


class TestRemoteAPISyncer:
    """Test RemoteAPISyncer uploads via REST API."""

    def test_uploads_files_via_rest_api(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Files are uploaded as multipart POST to REST endpoint."""
        # Arrange
        syncer = RemoteAPISyncer(wp_url="https://example.com", api_key="test-key")
        mock_response = mocker.Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "results": {"uploaded": 1, "skipped": 0, "errors": []},
        }
        mock_response.raise_for_status = mocker.Mock()
        syncer.client = mocker.Mock(spec=httpx.Client)
        syncer.client.post.return_value = mock_response

        src_file = tmp_path / "CSF-100_0.avif"
        src_file.write_bytes(b"avif-data")

        # Act
        result = syncer.sync_batch([src_file])

        # Assert
        assert result.uploaded == 1
        syncer.client.post.assert_called_once()
        call_kwargs = syncer.client.post.call_args
        assert call_kwargs.kwargs["headers"]["X-CSF-API-Key"] == "test-key"

    def test_handles_batch_upload_failure(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """HTTP errors during upload are captured as failures."""
        # Arrange
        syncer = RemoteAPISyncer(wp_url="https://example.com", api_key="test-key")
        syncer.client = mocker.Mock(spec=httpx.Client)
        syncer.client.post.side_effect = httpx.HTTPError("Connection refused")

        src_file = tmp_path / "CSF-100_0.avif"
        src_file.write_bytes(b"avif-data")

        # Act
        result = syncer.sync_batch([src_file])

        # Assert
        assert result.failed == 1
        assert len(result.errors) == 1
        assert "Batch upload failed" in result.errors[0]

    def test_verify_connection_returns_true_on_success(self, mocker: MockerFixture) -> None:
        """verify_connection() returns True when endpoint responds."""
        # Arrange
        syncer = RemoteAPISyncer(wp_url="https://example.com", api_key="test-key")
        mock_response = mocker.Mock(spec=httpx.Response)
        mock_response.status_code = 200
        syncer.client = mocker.Mock(spec=httpx.Client)
        syncer.client.head.return_value = mock_response

        # Act
        result = syncer.verify_connection()

        # Assert
        assert result is True

    def test_verify_connection_returns_false_on_error(self, mocker: MockerFixture) -> None:
        """verify_connection() returns False when endpoint is unreachable."""
        # Arrange
        syncer = RemoteAPISyncer(wp_url="https://example.com", api_key="test-key")
        syncer.client = mocker.Mock(spec=httpx.Client)
        syncer.client.head.side_effect = httpx.HTTPError("Connection refused")

        # Act
        result = syncer.verify_connection()

        # Assert
        assert result is False

    def test_endpoint_url_constructed_correctly(self) -> None:
        """Endpoint URL is correctly constructed from wp_url."""
        # Arrange & Act
        syncer = RemoteAPISyncer(wp_url="https://example.com/", api_key="key")

        # Assert — trailing slash removed, endpoint appended
        assert syncer.endpoint == "https://example.com/wp-json/csf/v1/images/upload"


# ---------------------------------------------------------------------------
# ImageSyncer Orchestrator Tests
# ---------------------------------------------------------------------------


class TestImageSyncer:
    """Test ImageSyncer orchestration of sync + cleanup."""

    def test_sync_copies_unsynced_files(
        self, images_dir: Path, wp_uploads_dir: Path, processor: ImageProcessor
    ) -> None:
        """sync() delivers unsynced files via strategy and marks them synced."""
        # Arrange
        _create_avif_file(processor.avif_dir, "CSF-100_0.avif")
        processor._manifest["CSF-100_0.avif"] = {  # noqa: SLF001
            "source_hash": "abc",
            "etag": None,
            "synced": False,
        }
        strategy = LocalFileSyncer(wp_uploads_dir=wp_uploads_dir)
        syncer = ImageSyncer(strategy=strategy, image_processor=processor)

        # Act
        result = syncer.sync()

        # Assert
        assert result.uploaded == 1
        entry = processor._manifest["CSF-100_0.avif"]  # noqa: SLF001
        assert entry["synced"] is True

    def test_sync_skips_when_nothing_to_sync(self, processor: ImageProcessor) -> None:
        """sync() returns empty result when all images are already synced."""
        # Arrange — no unsynced files
        strategy = Mock(spec=LocalFileSyncer)
        syncer = ImageSyncer(strategy=strategy, image_processor=processor)

        # Act
        result = syncer.sync()

        # Assert
        assert result.uploaded == 0
        assert result.skipped == 0
        strategy.sync_batch.assert_not_called()

    def test_sync_skips_missing_files(
        self, images_dir: Path, wp_uploads_dir: Path, processor: ImageProcessor
    ) -> None:
        """sync() skips manifest entries where the AVIF file is missing from disk."""
        # Arrange — manifest entry but no file on disk
        processor._manifest["CSF-MISSING_0.avif"] = {  # noqa: SLF001
            "source_hash": "abc",
            "etag": None,
            "synced": False,
        }
        strategy = LocalFileSyncer(wp_uploads_dir=wp_uploads_dir)
        syncer = ImageSyncer(strategy=strategy, image_processor=processor)

        # Act
        result = syncer.sync()

        # Assert — nothing uploaded because file is missing
        assert result.uploaded == 0

    def test_cleanup_deletes_synced_files(
        self, images_dir: Path, processor: ImageProcessor
    ) -> None:
        """cleanup() deletes AVIF files that are marked as synced."""
        # Arrange
        avif_path = _create_avif_file(processor.avif_dir, "CSF-100_0.avif")
        processor._manifest["CSF-100_0.avif"] = {  # noqa: SLF001
            "source_hash": "abc",
            "etag": None,
            "synced": True,
        }
        strategy = Mock(spec=LocalFileSyncer)
        syncer = ImageSyncer(strategy=strategy, image_processor=processor)

        # Act
        deleted = syncer.cleanup()

        # Assert
        assert deleted == 1
        assert not avif_path.exists()

    def test_cleanup_preserves_unsynced_files(
        self, images_dir: Path, processor: ImageProcessor
    ) -> None:
        """cleanup() does not delete files that haven't been synced."""
        # Arrange
        avif_path = _create_avif_file(processor.avif_dir, "CSF-100_0.avif")
        processor._manifest["CSF-100_0.avif"] = {  # noqa: SLF001
            "source_hash": "abc",
            "etag": None,
            "synced": False,
        }
        strategy = Mock(spec=LocalFileSyncer)
        syncer = ImageSyncer(strategy=strategy, image_processor=processor)

        # Act
        deleted = syncer.cleanup()

        # Assert
        assert deleted == 0
        assert avif_path.exists()

    def test_full_sync_and_cleanup_workflow(
        self, images_dir: Path, wp_uploads_dir: Path, processor: ImageProcessor
    ) -> None:
        """Full workflow: sync unsynced files, then cleanup synced files."""
        # Arrange
        avif_path = _create_avif_file(processor.avif_dir, "CSF-100_0.avif", b"test-data")
        processor._manifest["CSF-100_0.avif"] = {  # noqa: SLF001
            "source_hash": "abc",
            "etag": None,
            "synced": False,
        }
        strategy = LocalFileSyncer(wp_uploads_dir=wp_uploads_dir)
        syncer = ImageSyncer(strategy=strategy, image_processor=processor)

        # Act — sync then cleanup
        sync_result = syncer.sync()
        cleanup_count = syncer.cleanup()

        # Assert
        assert sync_result.uploaded == 1
        assert cleanup_count == 1
        assert not avif_path.exists()
        # Destination file should exist
        dest = wp_uploads_dir / "csf-parts" / "images" / "avif" / "CSF-100_0.avif"
        assert dest.exists()
        assert dest.read_bytes() == b"test-data"

    def test_manifest_persisted_after_sync(
        self, images_dir: Path, wp_uploads_dir: Path, processor: ImageProcessor
    ) -> None:
        """Manifest is saved to disk after sync with updated synced flags."""
        # Arrange
        _create_avif_file(processor.avif_dir, "CSF-100_0.avif")
        processor._manifest["CSF-100_0.avif"] = {  # noqa: SLF001
            "source_hash": "abc",
            "etag": None,
            "synced": False,
        }
        strategy = LocalFileSyncer(wp_uploads_dir=wp_uploads_dir)
        syncer = ImageSyncer(strategy=strategy, image_processor=processor)

        # Act
        syncer.sync()

        # Assert — manifest on disk has synced=True
        manifest_data = json.loads((images_dir / "manifest.json").read_text())
        assert manifest_data["CSF-100_0.avif"]["synced"] is True


# ---------------------------------------------------------------------------
# Streaming Sync Tests (sync_and_cleanup_for_sku)
# ---------------------------------------------------------------------------


class TestImageSyncerStreaming:
    """Test ImageSyncer streaming sync (per-SKU sync during scraping)."""

    def test_sync_and_cleanup_syncs_sku_files(
        self, images_dir: Path, wp_uploads_dir: Path, processor: ImageProcessor
    ) -> None:
        """sync_and_cleanup_for_sku() syncs and deletes matching files."""
        # Arrange
        avif_path = _create_avif_file(processor.avif_dir, "CSF-100_0.avif", b"image-data")
        processor._manifest["CSF-100_0.avif"] = {  # noqa: SLF001
            "source_hash": "abc",
            "etag": None,
            "synced": False,
        }
        strategy = LocalFileSyncer(wp_uploads_dir=wp_uploads_dir)
        syncer = ImageSyncer(strategy=strategy, image_processor=processor)

        # Act
        result = syncer.sync_and_cleanup_for_sku("CSF-100")

        # Assert — uploaded and local file deleted
        assert result.uploaded == 1
        assert not avif_path.exists()
        # Destination exists
        dest = wp_uploads_dir / "csf-parts" / "images" / "avif" / "CSF-100_0.avif"
        assert dest.exists()

    def test_sync_and_cleanup_ignores_other_skus(
        self, images_dir: Path, wp_uploads_dir: Path, processor: ImageProcessor
    ) -> None:
        """sync_and_cleanup_for_sku() does not touch other SKUs' files."""
        # Arrange
        _create_avif_file(processor.avif_dir, "CSF-100_0.avif")
        other_path = _create_avif_file(processor.avif_dir, "CSF-200_0.avif")
        processor._manifest["CSF-100_0.avif"] = {  # noqa: SLF001
            "source_hash": "abc",
            "etag": None,
            "synced": False,
        }
        processor._manifest["CSF-200_0.avif"] = {  # noqa: SLF001
            "source_hash": "def",
            "etag": None,
            "synced": False,
        }
        strategy = LocalFileSyncer(wp_uploads_dir=wp_uploads_dir)
        syncer = ImageSyncer(strategy=strategy, image_processor=processor)

        # Act
        syncer.sync_and_cleanup_for_sku("CSF-100")

        # Assert — other SKU's file is untouched
        assert other_path.exists()

    def test_sync_and_cleanup_returns_empty_for_no_match(self, processor: ImageProcessor) -> None:
        """sync_and_cleanup_for_sku() returns empty result when no files match."""
        # Arrange
        strategy = Mock(spec=LocalFileSyncer)
        syncer = ImageSyncer(strategy=strategy, image_processor=processor)

        # Act
        result = syncer.sync_and_cleanup_for_sku("CSF-NONEXISTENT")

        # Assert
        assert result.uploaded == 0
        assert result.skipped == 0
        strategy.sync_batch.assert_not_called()

    def test_cumulative_result_accumulates_across_calls(
        self, images_dir: Path, wp_uploads_dir: Path, processor: ImageProcessor
    ) -> None:
        """cumulative_result tracks totals across multiple streaming calls."""
        # Arrange
        _create_avif_file(processor.avif_dir, "CSF-100_0.avif")
        _create_avif_file(processor.avif_dir, "CSF-200_0.avif")
        processor._manifest["CSF-100_0.avif"] = {  # noqa: SLF001
            "source_hash": "abc",
            "etag": None,
            "synced": False,
        }
        processor._manifest["CSF-200_0.avif"] = {  # noqa: SLF001
            "source_hash": "def",
            "etag": None,
            "synced": False,
        }
        strategy = LocalFileSyncer(wp_uploads_dir=wp_uploads_dir)
        syncer = ImageSyncer(strategy=strategy, image_processor=processor)

        # Act
        syncer.sync_and_cleanup_for_sku("CSF-100")
        syncer.sync_and_cleanup_for_sku("CSF-200")

        # Assert
        assert syncer.cumulative_result.uploaded == 2

    def test_manifest_persisted_after_streaming_sync(
        self, images_dir: Path, wp_uploads_dir: Path, processor: ImageProcessor
    ) -> None:
        """Manifest is saved to disk after each streaming sync call."""
        # Arrange
        _create_avif_file(processor.avif_dir, "CSF-100_0.avif")
        processor._manifest["CSF-100_0.avif"] = {  # noqa: SLF001
            "source_hash": "abc",
            "etag": None,
            "synced": False,
        }
        strategy = LocalFileSyncer(wp_uploads_dir=wp_uploads_dir)
        syncer = ImageSyncer(strategy=strategy, image_processor=processor)

        # Act
        syncer.sync_and_cleanup_for_sku("CSF-100")

        # Assert — manifest on disk has synced=True
        manifest_data = json.loads((images_dir / "manifest.json").read_text())
        assert manifest_data["CSF-100_0.avif"]["synced"] is True
