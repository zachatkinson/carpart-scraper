"""Unit tests for ImageProcessor.

Tests cover:
- Manifest-based staleness detection
- Re-encoding when source image changes
- Encoding when no manifest entry exists
- Manifest persistence across sessions
- Corrupted manifest recovery
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

    def test_first_run_downloads_encodes_and_stores_hash(
        self, images_dir: Path, mock_client: Mock
    ) -> None:
        """First run with no AVIF on disk encodes and stores hash."""
        # Arrange
        processor = _make_processor(images_dir, mock_client)

        # Act
        result = processor.process_images("CSF-100", [IMAGE_ENTRY])

        # Assert
        assert len(result) == 1
        assert result[0]["url"] == "images/avif/CSF-100_0.avif"
        assert (images_dir / "avif" / "CSF-100_0.avif").exists()
        assert processor._manifest["CSF-100_0.avif"] == RED_HASH  # noqa: SLF001

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
        avif_path = images_dir / "avif" / "CSF-100_0.avif"

        # Act — second run with blue image (different content)
        response_mock = mock_client.get.return_value
        response_mock.content = BLUE_JPEG
        result = processor.process_images("CSF-100", [IMAGE_ENTRY])

        # Assert — AVIF was re-encoded, manifest updated
        assert len(result) == 1
        assert processor._manifest["CSF-100_0.avif"] == BLUE_HASH  # noqa: SLF001
        # File was rewritten (size may differ for different source colors)
        assert avif_path.exists()

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

        # Assert — encoding was called, manifest now has the hash
        assert len(result) == 1
        encode_spy.assert_called_once()
        assert processor._manifest["CSF-100_0.avif"] == RED_HASH  # noqa: SLF001

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
        assert processor2._manifest.get("CSF-200_0.avif") == RED_HASH  # noqa: SLF001

        # Verify manifest.json exists on disk
        manifest_path = images_dir / "avif" / "manifest.json"
        assert manifest_path.exists()
        stored = json.loads(manifest_path.read_text())
        assert stored["CSF-200_0.avif"] == RED_HASH

        processor2.close()

    def test_corrupted_manifest_resets_gracefully(self, images_dir: Path) -> None:
        """Corrupted manifest.json is handled without crashing."""
        # Arrange — write invalid JSON to manifest
        avif_dir = images_dir / "avif"
        avif_dir.mkdir(parents=True, exist_ok=True)
        (avif_dir / "manifest.json").write_text("{invalid json!!!")

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
        manifest_path = images_dir / "avif" / "manifest.json"
        assert manifest_path.exists()
        stored = json.loads(manifest_path.read_text())
        assert "CSF-300_0.avif" in stored


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
