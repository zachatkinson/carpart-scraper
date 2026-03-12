"""Unit tests for ImageProcessor.

Tests cover:
- ETag-based conditional downloads (304 Not Modified)
- Enhanced manifest schema with etag/synced fields
- Legacy manifest migration (flat string → rich dict)
- Manifest relocation from avif/ to images/
- Manifest-based staleness detection
- Re-encoding when source image changes
- Encoding when no manifest entry exists
- Manifest persistence across sessions
- Corrupted manifest recovery
- Sync helper methods (mark_synced, get_unsynced_files, get_synced_files)
"""

import hashlib
import json
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest
from PIL import Image
from pytest_mock import MockerFixture

from src.scraper.image_processor import ImageProcessor


def _make_jpeg_bytes(
    color: tuple[int, int, int] = (255, 0, 0),
    size: tuple[int, int] = (10, 10),
) -> bytes:
    """Create minimal JPEG bytes for testing."""
    buf = BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    return buf.getvalue()


def _make_png_bytes(mode: str, size: tuple[int, int] = (10, 10)) -> bytes:
    """Create PNG bytes in a specific image mode (RGBA, P, L, etc.)."""
    buf = BytesIO()
    img = Image.new(mode, size, 0)
    img.save(buf, format="PNG")
    return buf.getvalue()


RED_JPEG = _make_jpeg_bytes((255, 0, 0))
BLUE_JPEG = _make_jpeg_bytes((0, 0, 255))
RED_HASH = hashlib.md5(RED_JPEG).hexdigest()  # noqa: S324
BLUE_HASH = hashlib.md5(BLUE_JPEG).hexdigest()  # noqa: S324


@pytest.fixture
def images_dir(tmp_path: Path) -> Path:
    """Provide a temporary images directory."""
    return tmp_path / "images"


@pytest.fixture
def mock_client(mocker: MockerFixture) -> Mock:
    """Provide a mock httpx.Client that returns RED_JPEG by default."""
    client = mocker.Mock(spec=httpx.Client)
    response = mocker.Mock(spec=httpx.Response)
    response.content = RED_JPEG
    response.status_code = 200
    response.headers = {"etag": '"abc123"'}
    response.raise_for_status = mocker.Mock()
    client.get.return_value = response
    return client


def _make_processor(images_dir: Path, mock_client: Mock) -> ImageProcessor:
    """Create an ImageProcessor wired to the mock client."""
    processor = ImageProcessor(images_dir=images_dir)
    processor.client.close()
    processor.client = mock_client
    return processor


IMAGE_ENTRY = {
    "url": "https://s3.example.com/img.jpg",
    "alt_text": "Part photo",
    "is_primary": True,
}


class TestProcessImagesManifest:
    """Test manifest-based staleness detection in process_images."""

    def test_first_run_downloads_encodes_and_stores_entry(
        self, images_dir: Path, mock_client: Mock
    ) -> None:
        """First run with no AVIF on disk encodes and stores rich manifest entry."""
        # Arrange
        processor = _make_processor(images_dir, mock_client)

        # Act
        result = processor.process_images("CSF-100", [IMAGE_ENTRY])

        # Assert
        assert len(result) == 1
        assert result[0]["url"] == "images/avif/CSF-100_0.avif"
        assert (images_dir / "avif" / "CSF-100_0.avif").exists()
        entry = processor._manifest["CSF-100_0.avif"]  # noqa: SLF001
        assert entry["source_hash"] == RED_HASH
        assert entry["etag"] == '"abc123"'
        assert entry["synced"] is False

        processor.close()

    def test_skips_encoding_when_source_unchanged(
        self, images_dir: Path, mock_client: Mock
    ) -> None:
        """Existing AVIF + matching manifest hash skips re-encoding."""
        # Arrange — first run to populate AVIF and manifest
        processor = _make_processor(images_dir, mock_client)
        processor.process_images("CSF-100", [IMAGE_ENTRY])
        avif_path = images_dir / "avif" / "CSF-100_0.avif"
        original_mtime = avif_path.stat().st_mtime

        # Act — second run with same image content
        mock_client.get.return_value.content = RED_JPEG
        result = processor.process_images("CSF-100", [IMAGE_ENTRY])

        # Assert — AVIF file not rewritten
        assert len(result) == 1
        assert avif_path.stat().st_mtime == original_mtime

        processor.close()

    def test_reencodes_when_source_changed(self, images_dir: Path, mock_client: Mock) -> None:
        """Existing AVIF + different manifest hash triggers re-encoding."""
        # Arrange — first run with red image
        processor = _make_processor(images_dir, mock_client)
        processor.process_images("CSF-100", [IMAGE_ENTRY])

        # Act — second run with blue image (different content)
        response_mock = mock_client.get.return_value
        response_mock.content = BLUE_JPEG
        result = processor.process_images("CSF-100", [IMAGE_ENTRY])

        # Assert — AVIF was re-encoded, manifest updated
        assert len(result) == 1
        entry = processor._manifest["CSF-100_0.avif"]  # noqa: SLF001
        assert entry["source_hash"] == BLUE_HASH

        processor.close()

    def test_encodes_when_no_manifest_entry(
        self, images_dir: Path, mock_client: Mock, mocker: MockerFixture
    ) -> None:
        """Existing AVIF on disk but missing manifest entry triggers encoding."""
        # Arrange — create processor, write a dummy AVIF without going through process_images
        processor = _make_processor(images_dir, mock_client)
        avif_path = images_dir / "avif" / "CSF-100_0.avif"
        avif_path.write_bytes(b"dummy")
        # manifest has no entry for this file
        encode_spy = mocker.spy(processor, "_encode_avif")

        # Act
        result = processor.process_images("CSF-100", [IMAGE_ENTRY])

        # Assert — encoding was called, manifest now has the entry
        assert len(result) == 1
        encode_spy.assert_called_once()
        entry = processor._manifest["CSF-100_0.avif"]  # noqa: SLF001
        assert entry["source_hash"] == RED_HASH

        processor.close()


class TestETagConditionalDownloads:
    """Test ETag-based conditional request handling."""

    def test_304_not_modified_skips_download_and_encoding(
        self, images_dir: Path, mock_client: Mock, mocker: MockerFixture
    ) -> None:
        """When server returns 304, no download or AVIF encoding occurs."""
        # Arrange — first run to populate manifest with ETag
        processor = _make_processor(images_dir, mock_client)
        processor.process_images("CSF-100", [IMAGE_ENTRY])
        encode_spy = mocker.spy(processor, "_encode_avif")

        # Set up 304 response for second request
        response_304 = mocker.Mock(spec=httpx.Response)
        response_304.status_code = 304
        mock_client.get.return_value = response_304

        # Act
        result = processor.process_images("CSF-100", [IMAGE_ENTRY])

        # Assert — image reference returned, but no encoding
        assert len(result) == 1
        assert result[0]["url"] == "images/avif/CSF-100_0.avif"
        encode_spy.assert_not_called()

        processor.close()

    def test_sends_if_none_match_header_when_etag_stored(
        self, images_dir: Path, mock_client: Mock
    ) -> None:
        """Sends If-None-Match header when ETag exists in manifest."""
        # Arrange — first run populates manifest with ETag
        processor = _make_processor(images_dir, mock_client)
        processor.process_images("CSF-100", [IMAGE_ENTRY])

        # Act — second request
        processor.process_images("CSF-100", [IMAGE_ENTRY])

        # Assert — second call should include If-None-Match
        calls = mock_client.get.call_args_list
        assert len(calls) == 2
        second_call_headers = calls[1].kwargs.get("headers", {})
        assert second_call_headers.get("If-None-Match") == '"abc123"'

        processor.close()

    def test_no_if_none_match_when_no_etag_stored(
        self, images_dir: Path, mock_client: Mock
    ) -> None:
        """Does not send If-None-Match when no ETag is in manifest."""
        # Arrange — fresh processor, no manifest entries
        processor = _make_processor(images_dir, mock_client)

        # Act
        processor.process_images("CSF-100", [IMAGE_ENTRY])

        # Assert — first call should have empty headers
        call_headers = mock_client.get.call_args.kwargs.get("headers", {})
        assert "If-None-Match" not in call_headers

        processor.close()

    def test_no_if_none_match_when_avif_missing_from_disk(
        self, images_dir: Path, mock_client: Mock
    ) -> None:
        """Does not send If-None-Match if AVIF file is missing from disk."""
        # Arrange — populate manifest with ETag but don't create AVIF file
        processor = _make_processor(images_dir, mock_client)
        processor._manifest["CSF-100_0.avif"] = {  # noqa: SLF001
            "source_hash": RED_HASH,
            "etag": '"abc123"',
            "synced": False,
        }
        # No AVIF file on disk

        # Act
        processor.process_images("CSF-100", [IMAGE_ENTRY])

        # Assert — should NOT send If-None-Match since AVIF is missing
        call_headers = mock_client.get.call_args.kwargs.get("headers", {})
        assert "If-None-Match" not in call_headers

        processor.close()

    def test_stores_etag_from_response(self, images_dir: Path, mock_client: Mock) -> None:
        """ETag from HTTP response is stored in manifest."""
        # Arrange
        mock_client.get.return_value.headers = {"etag": '"new-etag-value"'}
        processor = _make_processor(images_dir, mock_client)

        # Act
        processor.process_images("CSF-100", [IMAGE_ENTRY])

        # Assert
        entry = processor._manifest["CSF-100_0.avif"]  # noqa: SLF001
        assert entry["etag"] == '"new-etag-value"'

        processor.close()


class TestManifestMigration:
    """Test manifest format and location migration."""

    def test_legacy_flat_manifest_migrated_to_rich_format(self, images_dir: Path) -> None:
        """Legacy manifest with flat string values is auto-migrated."""
        # Arrange — write legacy format manifest at new location
        images_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = images_dir / "manifest.json"
        legacy_data = {"CSF-100_0.avif": RED_HASH, "CSF-200_0.avif": BLUE_HASH}
        manifest_path.write_text(json.dumps(legacy_data))

        # Act
        processor = ImageProcessor(images_dir=images_dir)

        # Assert — all entries migrated to rich format
        for filename in ("CSF-100_0.avif", "CSF-200_0.avif"):
            entry = processor._manifest[filename]  # noqa: SLF001
            assert isinstance(entry, dict)
            assert "source_hash" in entry
            assert entry["etag"] is None
            assert entry["synced"] is False

        processor.close()

    def test_manifest_relocated_from_avif_dir(self, images_dir: Path) -> None:
        """Legacy manifest in avif/ directory is moved to images/."""
        # Arrange — write manifest at old location
        avif_dir = images_dir / "avif"
        avif_dir.mkdir(parents=True, exist_ok=True)
        old_path = avif_dir / "manifest.json"
        old_path.write_text(json.dumps({"CSF-100_0.avif": RED_HASH}))

        # Act
        processor = ImageProcessor(images_dir=images_dir)

        # Assert — file moved to new location
        new_path = images_dir / "manifest.json"
        assert new_path.exists()
        assert not old_path.exists()
        assert "CSF-100_0.avif" in processor._manifest  # noqa: SLF001

        processor.close()

    def test_new_location_preferred_over_legacy(self, images_dir: Path) -> None:
        """If both old and new manifest exist, new location is used (no move)."""
        # Arrange — both files exist
        images_dir.mkdir(parents=True, exist_ok=True)
        avif_dir = images_dir / "avif"
        avif_dir.mkdir(parents=True, exist_ok=True)

        old_path = avif_dir / "manifest.json"
        old_path.write_text(json.dumps({"OLD_0.avif": "oldhash"}))

        new_path = images_dir / "manifest.json"
        new_path.write_text(json.dumps({"NEW_0.avif": "newhash"}))

        # Act
        processor = ImageProcessor(images_dir=images_dir)

        # Assert — new location data is loaded, old file untouched
        assert "NEW_0.avif" in processor._manifest  # noqa: SLF001
        assert "OLD_0.avif" not in processor._manifest  # noqa: SLF001
        assert old_path.exists()  # old file not deleted

        processor.close()


class TestManifestPersistence:
    """Test manifest loading and saving across sessions."""

    def test_manifest_persists_across_sessions(self, images_dir: Path, mock_client: Mock) -> None:
        """Manifest written on close is loaded by a new ImageProcessor instance."""
        # Arrange — session 1: process an image then close
        processor1 = _make_processor(images_dir, mock_client)
        processor1.process_images("CSF-200", [IMAGE_ENTRY])
        processor1.close()

        # Act — session 2: create new processor, check manifest loaded
        processor2 = ImageProcessor(images_dir=images_dir)
        processor2.client.close()
        processor2.client = mock_client

        # Assert
        entry = processor2._manifest.get("CSF-200_0.avif")  # noqa: SLF001
        assert isinstance(entry, dict)
        assert entry["source_hash"] == RED_HASH

        # Verify manifest.json exists at new location (images/, not avif/)
        manifest_path = images_dir / "manifest.json"
        assert manifest_path.exists()

        processor2.close()

    def test_corrupted_manifest_resets_gracefully(self, images_dir: Path) -> None:
        """Corrupted manifest.json is handled without crashing."""
        # Arrange — write invalid JSON to manifest
        images_dir.mkdir(parents=True, exist_ok=True)
        (images_dir / "manifest.json").write_text("{invalid json!!!")

        # Act — creating processor should not raise
        processor = ImageProcessor(images_dir=images_dir)

        # Assert — manifest is reset to empty
        assert processor._manifest == {}  # noqa: SLF001

        processor.close()

    def test_context_manager_saves_manifest(self, images_dir: Path, mock_client: Mock) -> None:
        """Using ImageProcessor as context manager persists manifest on exit."""
        # Arrange & Act
        with ImageProcessor(images_dir=images_dir) as processor:
            processor.client.close()
            processor.client = mock_client
            processor.process_images("CSF-300", [IMAGE_ENTRY])

        # Assert — manifest was saved by __exit__
        manifest_path = images_dir / "manifest.json"
        assert manifest_path.exists()
        stored = json.loads(manifest_path.read_text())
        assert "CSF-300_0.avif" in stored


class TestSyncHelpers:
    """Test manifest sync helper methods."""

    def test_mark_synced_sets_flag(self, images_dir: Path, mock_client: Mock) -> None:
        """mark_synced() sets synced=True for a manifest entry."""
        # Arrange
        processor = _make_processor(images_dir, mock_client)
        processor.process_images("CSF-100", [IMAGE_ENTRY])

        # Act
        processor.mark_synced("CSF-100_0.avif")

        # Assert
        entry = processor._manifest["CSF-100_0.avif"]  # noqa: SLF001
        assert entry["synced"] is True

        processor.close()

    def test_get_unsynced_files_returns_unsynced(self, images_dir: Path, mock_client: Mock) -> None:
        """get_unsynced_files() returns files not yet synced."""
        # Arrange
        processor = _make_processor(images_dir, mock_client)
        processor.process_images("CSF-100", [IMAGE_ENTRY])
        processor.process_images("CSF-200", [IMAGE_ENTRY])
        processor.mark_synced("CSF-100_0.avif")

        # Act
        unsynced = processor.get_unsynced_files()

        # Assert
        assert "CSF-200_0.avif" in unsynced
        assert "CSF-100_0.avif" not in unsynced

        processor.close()

    def test_get_synced_files_returns_synced(self, images_dir: Path, mock_client: Mock) -> None:
        """get_synced_files() returns files that have been synced."""
        # Arrange
        processor = _make_processor(images_dir, mock_client)
        processor.process_images("CSF-100", [IMAGE_ENTRY])
        processor.mark_synced("CSF-100_0.avif")

        # Act
        synced = processor.get_synced_files()

        # Assert
        assert "CSF-100_0.avif" in synced

        processor.close()

    def test_new_images_default_to_unsynced(self, images_dir: Path, mock_client: Mock) -> None:
        """Newly processed images start with synced=False."""
        # Arrange
        processor = _make_processor(images_dir, mock_client)

        # Act
        processor.process_images("CSF-100", [IMAGE_ENTRY])

        # Assert
        unsynced = processor.get_unsynced_files()
        assert "CSF-100_0.avif" in unsynced

        processor.close()

    def test_legacy_entries_treated_as_unsynced(self, images_dir: Path) -> None:
        """Legacy flat-string manifest entries are treated as unsynced."""
        # Arrange — write legacy format
        images_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = images_dir / "manifest.json"
        manifest_path.write_text(json.dumps({"CSF-100_0.avif": RED_HASH}))

        processor = ImageProcessor(images_dir=images_dir)

        # Act — after migration, entries should be in new format
        unsynced = processor.get_unsynced_files()

        # Assert
        assert "CSF-100_0.avif" in unsynced

        processor.close()


class TestImageDownscaling:
    """Test max_dimension downscaling during AVIF encoding."""

    def test_large_image_downscaled_to_max_dimension(
        self, images_dir: Path, mock_client: Mock
    ) -> None:
        """Image exceeding max_dimension is downscaled proportionally."""
        # Arrange — 2000x1000 source image, max_dimension=1200
        large_jpeg = _make_jpeg_bytes(size=(2000, 1000))
        mock_client.get.return_value.content = large_jpeg
        processor = _make_processor(images_dir, mock_client)
        processor.max_dimension = 1200

        # Act
        processor.process_images("CSF-BIG", [IMAGE_ENTRY])

        # Assert — output dimensions within bounds
        avif_path = images_dir / "avif" / "CSF-BIG_0.avif"
        with Image.open(avif_path) as img:
            assert img.size[0] <= 1200
            assert img.size[1] <= 1200
            # Aspect ratio preserved: 2000x1000 → 1200x600
            assert img.size == (1200, 600)

        processor.close()

    def test_tall_image_downscaled_by_height(self, images_dir: Path, mock_client: Mock) -> None:
        """Portrait image is downscaled based on height exceeding limit."""
        # Arrange — 1000x2000 source, max_dimension=800
        tall_jpeg = _make_jpeg_bytes(size=(1000, 2000))
        mock_client.get.return_value.content = tall_jpeg
        processor = _make_processor(images_dir, mock_client)
        processor.max_dimension = 800

        # Act
        processor.process_images("CSF-TALL", [IMAGE_ENTRY])

        # Assert — height is the constraining dimension
        avif_path = images_dir / "avif" / "CSF-TALL_0.avif"
        with Image.open(avif_path) as img:
            assert img.size[0] <= 800
            assert img.size[1] <= 800
            assert img.size == (400, 800)

        processor.close()

    def test_small_image_not_upscaled(self, images_dir: Path, mock_client: Mock) -> None:
        """Image smaller than max_dimension is not upscaled."""
        # Arrange — 100x100 source, max_dimension=1200
        small_jpeg = _make_jpeg_bytes(size=(100, 100))
        mock_client.get.return_value.content = small_jpeg
        processor = _make_processor(images_dir, mock_client)

        # Act
        processor.process_images("CSF-SMALL", [IMAGE_ENTRY])

        # Assert — dimensions unchanged
        avif_path = images_dir / "avif" / "CSF-SMALL_0.avif"
        with Image.open(avif_path) as img:
            assert img.size == (100, 100)

        processor.close()

    def test_image_exactly_at_limit_not_resized(self, images_dir: Path, mock_client: Mock) -> None:
        """Image exactly at max_dimension is not resized."""
        # Arrange — 1200x800 source, max_dimension=1200
        exact_jpeg = _make_jpeg_bytes(size=(1200, 800))
        mock_client.get.return_value.content = exact_jpeg
        processor = _make_processor(images_dir, mock_client)

        # Act
        processor.process_images("CSF-EXACT", [IMAGE_ENTRY])

        # Assert
        avif_path = images_dir / "avif" / "CSF-EXACT_0.avif"
        with Image.open(avif_path) as img:
            assert img.size == (1200, 800)

        processor.close()


class TestProcessImagesEdgeCases:
    """Test edge cases in process_images."""

    def test_missing_url_skips_image(self, images_dir: Path, mock_client: Mock) -> None:
        """Image entry with no URL is skipped."""
        # Arrange
        processor = _make_processor(images_dir, mock_client)

        # Act
        result = processor.process_images("CSF-400", [{"alt_text": "No URL"}])

        # Assert
        assert result == []
        mock_client.get.assert_not_called()

        processor.close()

    def test_download_failure_skips_image(self, images_dir: Path, mock_client: Mock) -> None:
        """HTTP error during download skips that image and continues."""
        # Arrange
        mock_client.get.side_effect = httpx.HTTPStatusError("404", request=Mock(), response=Mock())
        processor = _make_processor(images_dir, mock_client)

        # Act
        result = processor.process_images("CSF-500", [IMAGE_ENTRY])

        # Assert
        assert result == []

        processor.close()


class TestEncodeAvifColorModes:
    """Test AVIF encoding handles all PIL image modes correctly."""

    def test_encodes_rgba_png_to_avif(self, images_dir: Path, mock_client: Mock) -> None:
        """RGBA source is composited onto white background then encoded."""
        # Arrange
        mock_client.get.return_value.content = _make_png_bytes("RGBA")
        processor = _make_processor(images_dir, mock_client)

        # Act
        result = processor.process_images("CSF-600", [IMAGE_ENTRY])

        # Assert
        assert len(result) == 1
        avif_path = images_dir / "avif" / "CSF-600_0.avif"
        assert avif_path.exists()
        with Image.open(avif_path) as img:
            assert img.mode == "RGB"

        processor.close()

    def test_encodes_palette_png_to_avif(self, images_dir: Path, mock_client: Mock) -> None:
        """Palette (P) mode source is converted via RGBA then encoded."""
        # Arrange
        mock_client.get.return_value.content = _make_png_bytes("P")
        processor = _make_processor(images_dir, mock_client)

        # Act
        result = processor.process_images("CSF-601", [IMAGE_ENTRY])

        # Assert
        assert len(result) == 1
        avif_path = images_dir / "avif" / "CSF-601_0.avif"
        assert avif_path.exists()

        processor.close()

    def test_encodes_grayscale_to_avif(self, images_dir: Path, mock_client: Mock) -> None:
        """Grayscale (L) source is converted to RGB then encoded."""
        # Arrange
        mock_client.get.return_value.content = _make_png_bytes("L")
        processor = _make_processor(images_dir, mock_client)

        # Act
        result = processor.process_images("CSF-602", [IMAGE_ENTRY])

        # Assert
        assert len(result) == 1
        avif_path = images_dir / "avif" / "CSF-602_0.avif"
        assert avif_path.exists()

        processor.close()

    def test_encodes_la_png_to_avif(self, images_dir: Path, mock_client: Mock) -> None:
        """LA (grayscale + alpha) source is composited then encoded."""
        # Arrange
        mock_client.get.return_value.content = _make_png_bytes("LA")
        processor = _make_processor(images_dir, mock_client)

        # Act
        result = processor.process_images("CSF-603", [IMAGE_ENTRY])

        # Assert
        assert len(result) == 1
        avif_path = images_dir / "avif" / "CSF-603_0.avif"
        assert avif_path.exists()

        processor.close()
