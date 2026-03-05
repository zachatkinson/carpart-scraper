"""Image processor for downloading and converting scraped images.

This module downloads images from S3 URLs during scraping and converts them
to AVIF format immediately, avoiding S3 URL expiration issues.

Uses a manifest file to track source hashes, ETags, and sync status so that
AVIF re-encoding only happens when the upstream image has actually changed.
Supports ETag-based conditional requests (If-None-Match) to skip downloading
unchanged images entirely.
"""

import hashlib
import json
import shutil
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx
import structlog
from PIL import Image

logger = structlog.get_logger()

ManifestEntry = dict[str, Any]

HTTP_NOT_MODIFIED = 304


class ImageProcessor:
    """Download and convert images to AVIF format during scraping.

    Processes images immediately after scraping to avoid S3 URL expiration.
    Downloads from S3, converts to AVIF, and returns local file paths.

    Uses HTTP ETags for conditional requests — if the server returns 304
    Not Modified, the download and AVIF conversion are skipped entirely.

    Attributes:
        images_dir: Base directory for image storage
        avif_dir: Directory for AVIF files (staging area)
        avif_quality: AVIF quality setting (0-100)
        timeout: HTTP request timeout in seconds
    """

    def __init__(
        self,
        images_dir: Path | str = "images",
        avif_quality: int = 85,
        timeout: int = 30,
    ) -> None:
        """Initialize image processor.

        Args:
            images_dir: Directory for storing images (default: "images")
            avif_quality: AVIF quality 0-100 (default: 85)
            timeout: HTTP timeout in seconds (default: 30)
        """
        self.images_dir = Path(images_dir)
        self.avif_dir = self.images_dir / "avif"
        self.avif_quality = avif_quality
        self.timeout = timeout

        # Create directories
        self.avif_dir.mkdir(parents=True, exist_ok=True)

        # HTTP client with timeout
        self.client = httpx.Client(timeout=timeout)

        # Load manifest for content-hash based staleness detection
        self._manifest_path = self.images_dir / "manifest.json"
        self._manifest: dict[str, ManifestEntry] = self._load_manifest()

        logger.info(
            "image_processor_initialized",
            avif_dir=str(self.avif_dir),
            quality=avif_quality,
            manifest_entries=len(self._manifest),
        )

    def process_images(self, sku: str, image_urls: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Download and convert images for a part.

        Uses ETag-based conditional requests to skip unchanged images.
        When the server returns 304 Not Modified, no download or AVIF
        conversion occurs — the existing local reference is returned.

        Args:
            sku: Part SKU (used for filename)
            image_urls: List of image dicts with 'url', 'alt_text', 'is_primary'

        Returns:
            List of processed image dicts with local 'url' paths

        Example:
            >>> processor = ImageProcessor()
            >>> images = processor.process_images("CSF-3680", [
            ...     {"url": "https://s3.../image.jpg", "alt_text": "Part", "is_primary": True}
            ... ])
            >>> images[0]['url']
            'images/avif/CSF-3680_0.avif'
        """
        processed_images = []

        for idx, img_info in enumerate(image_urls):
            s3_url = img_info.get("url")
            if not s3_url:
                logger.warning("missing_image_url", sku=sku, index=idx)
                continue

            # Generate AVIF filename
            avif_filename = f"{sku}_{idx}.avif"
            avif_path = self.avif_dir / avif_filename

            image_ref = {
                "url": f"images/avif/{avif_filename}",
                "alt_text": img_info.get("alt_text", ""),
                "is_primary": img_info.get("is_primary", False),
            }

            try:
                # Build conditional request headers using stored ETag
                headers: dict[str, str] = {}
                entry = self._manifest.get(avif_filename, {})
                stored_etag = entry.get("etag") if isinstance(entry, dict) else None

                if stored_etag and avif_path.exists():
                    headers["If-None-Match"] = stored_etag

                response = self.client.get(s3_url, headers=headers)

                if response.status_code == HTTP_NOT_MODIFIED:
                    logger.debug("image_not_modified_etag", sku=sku, index=idx)
                    processed_images.append(image_ref)
                    continue

                response.raise_for_status()

                # Capture ETag from response
                new_etag = response.headers.get("etag")

                source_hash = hashlib.md5(response.content).hexdigest()  # noqa: S324

                # Check manifest to see if source image is unchanged
                stored_hash = entry.get("source_hash") if isinstance(entry, dict) else entry
                if avif_path.exists() and stored_hash == source_hash:
                    logger.debug("image_unchanged_skipping", sku=sku, index=idx)
                    # Update ETag in manifest even if hash matches (ETag may be new)
                    self._set_entry(avif_filename, source_hash, new_etag)
                    processed_images.append(image_ref)
                    continue

                # New or changed image — encode to AVIF
                self._encode_avif(response.content, avif_path)
                self._set_entry(avif_filename, source_hash, new_etag)

                logger.debug(
                    "image_processed",
                    sku=sku,
                    index=idx,
                    size=avif_path.stat().st_size,
                    changed=avif_path.exists(),
                )

                processed_images.append(image_ref)

            except (httpx.HTTPError, OSError, ValueError, TypeError) as e:
                logger.exception(
                    "image_processing_failed",
                    sku=sku,
                    index=idx,
                    url=s3_url,
                    error=str(e),
                )
                # Continue without this image rather than failing the whole part
                continue

        return processed_images

    # ------------------------------------------------------------------
    # Manifest helpers
    # ------------------------------------------------------------------

    def _set_entry(self, filename: str, source_hash: str, etag: str | None = None) -> None:
        """Update a manifest entry, marking it as unsynced.

        Args:
            filename: AVIF filename key
            source_hash: MD5 hex digest of source image bytes
            etag: HTTP ETag from server response (optional)
        """
        self._manifest[filename] = {
            "source_hash": source_hash,
            "etag": etag,
            "synced": False,
        }

    def mark_synced(self, filename: str) -> None:
        """Mark an image as synced to WordPress.

        Args:
            filename: AVIF filename to mark as synced
        """
        entry = self._manifest.get(filename)
        if entry is not None:
            entry["synced"] = True

    def get_unsynced_files(self) -> list[str]:
        """Get list of AVIF filenames that haven't been synced.

        Returns:
            List of filenames where synced is False or missing.
        """
        return [
            filename for filename, entry in self._manifest.items() if not entry.get("synced", False)
        ]

    def get_synced_files(self) -> list[str]:
        """Get list of AVIF filenames that have been synced.

        Returns:
            List of filenames where synced is True.
        """
        return [
            filename
            for filename, entry in self._manifest.items()
            if isinstance(entry, dict) and entry.get("synced", False)
        ]

    # ------------------------------------------------------------------
    # Manifest persistence
    # ------------------------------------------------------------------

    def _load_manifest(self) -> dict[str, ManifestEntry]:
        """Load the image hash manifest from disk.

        Handles migration from the legacy location (images/avif/manifest.json)
        and auto-migrates legacy flat-string entries to the new schema.

        Returns:
            Dict mapping AVIF filenames to manifest entries.
        """
        legacy_path = self.images_dir / "avif" / "manifest.json"

        # Migrate legacy location if needed
        if legacy_path.exists() and not self._manifest_path.exists():
            logger.info(
                "manifest_migrating_location",
                old=str(legacy_path),
                new=str(self._manifest_path),
            )
            shutil.move(str(legacy_path), str(self._manifest_path))

        if self._manifest_path.exists():
            try:
                raw: dict[str, Any] = dict(json.loads(self._manifest_path.read_text()))
                return self._migrate_manifest(raw)
            except (json.JSONDecodeError, ValueError):
                logger.warning("manifest_corrupted_resetting", path=str(self._manifest_path))
        return {}

    @staticmethod
    def _migrate_manifest(raw: dict[str, Any]) -> dict[str, ManifestEntry]:
        """Migrate legacy manifest entries to the new schema.

        Legacy format: {"filename": "md5_hash_string"}
        New format: {"filename": {"source_hash": "...", "etag": null, "synced": false}}

        Args:
            raw: Raw manifest data (may contain legacy or new entries)

        Returns:
            Manifest with all entries in the new schema
        """
        migrated: dict[str, ManifestEntry] = {}
        for filename, value in raw.items():
            if isinstance(value, str):
                # Legacy flat-string entry — wrap it
                migrated[filename] = {
                    "source_hash": value,
                    "etag": None,
                    "synced": False,
                }
            elif isinstance(value, dict):
                migrated[filename] = value
            else:
                # Unknown format — skip
                logger.warning("manifest_unknown_entry", filename=filename)
        return migrated

    def _save_manifest(self) -> None:
        """Persist the image hash manifest to disk."""
        self._manifest_path.write_text(json.dumps(self._manifest, indent=2))

    # ------------------------------------------------------------------
    # AVIF encoding
    # ------------------------------------------------------------------

    def _encode_avif(self, raw_bytes: bytes, avif_path: Path) -> None:
        """Convert raw image bytes to AVIF and save to disk.

        Args:
            raw_bytes: Source image bytes (JPEG, PNG, etc.)
            avif_path: Destination path for the AVIF file
        """
        with Image.open(BytesIO(raw_bytes)) as img:
            rgb_img = self._convert_to_rgb(img)
            rgb_img.save(
                avif_path,
                format="AVIF",
                quality=self.avif_quality,
                speed=4,
            )

    @staticmethod
    def _convert_to_rgb(img: Image.Image) -> Image.Image:
        """Convert image to RGB mode for AVIF encoding.

        Args:
            img: Source PIL Image in any mode.

        Returns:
            RGB-mode PIL Image.
        """
        if img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            converted = img.convert("RGBA") if img.mode == "P" else img
            background.paste(converted, mask=converted.split()[-1])
            return background
        if img.mode != "RGB":
            return img.convert("RGB")
        return img

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close HTTP client and persist manifest."""
        self._save_manifest()
        self.client.close()

    def __enter__(self) -> "ImageProcessor":
        """Context manager entry."""
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager exit."""
        self.close()
