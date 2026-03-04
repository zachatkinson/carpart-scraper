"""Image processor for downloading and converting scraped images.

This module downloads images from S3 URLs during scraping and converts them
to AVIF format immediately, avoiding S3 URL expiration issues.

Uses a manifest file to track MD5 hashes of source images so that AVIF
re-encoding only happens when the upstream image has actually changed.
"""

import hashlib
import json
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx
import structlog
from PIL import Image

logger = structlog.get_logger()


class ImageProcessor:
    """Download and convert images to AVIF format during scraping.

    Processes images immediately after scraping to avoid S3 URL expiration.
    Downloads from S3, converts to AVIF, and returns local file paths.

    Attributes:
        images_dir: Base directory for image storage
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
        self._manifest_path = self.avif_dir / "manifest.json"
        self._manifest: dict[str, str] = self._load_manifest()

        logger.info(
            "image_processor_initialized",
            avif_dir=str(self.avif_dir),
            quality=avif_quality,
            manifest_entries=len(self._manifest),
        )

    def process_images(self, sku: str, image_urls: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Download and convert images for a part.

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

            try:
                # Always download to check for content changes
                response = self.client.get(s3_url)
                response.raise_for_status()

                source_hash = hashlib.md5(response.content).hexdigest()  # noqa: S324

                # Check manifest to see if source image is unchanged
                if avif_path.exists() and self._manifest.get(avif_filename) == source_hash:
                    logger.debug("image_unchanged_skipping", sku=sku, index=idx)
                    processed_images.append(
                        {
                            "url": f"images/avif/{avif_filename}",
                            "alt_text": img_info.get("alt_text", ""),
                            "is_primary": img_info.get("is_primary", False),
                        }
                    )
                    continue

                # New or changed image — encode to AVIF
                self._encode_avif(response.content, avif_path)
                self._manifest[avif_filename] = source_hash

                logger.debug(
                    "image_processed",
                    sku=sku,
                    index=idx,
                    size=avif_path.stat().st_size,
                    changed=avif_path.exists(),
                )

                processed_images.append(
                    {
                        "url": f"images/avif/{avif_filename}",
                        "alt_text": img_info.get("alt_text", ""),
                        "is_primary": img_info.get("is_primary", False),
                    }
                )

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

    def _load_manifest(self) -> dict[str, str]:
        """Load the image hash manifest from disk.

        Returns:
            Dict mapping AVIF filenames to MD5 hashes of their source images.
        """
        if self._manifest_path.exists():
            try:
                return dict(json.loads(self._manifest_path.read_text()))
            except (json.JSONDecodeError, ValueError):
                logger.warning("manifest_corrupted_resetting", path=str(self._manifest_path))
        return {}

    def _save_manifest(self) -> None:
        """Persist the image hash manifest to disk."""
        self._manifest_path.write_text(json.dumps(self._manifest, indent=2))

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
