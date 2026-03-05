"""Image syncer for delivering AVIF images to WordPress.

Supports two strategies:
- LocalFileSyncer: copies files directly to a WordPress uploads directory (DDEV / local)
- RemoteAPISyncer: uploads via the WordPress REST API (production / remote)

After a successful sync, local AVIF files can be cleaned up — the images/avif/
directory is a staging area, not permanent storage.
"""

import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

import httpx
import structlog

from src.scraper.image_processor import ImageProcessor

logger = structlog.get_logger()

REMOTE_BATCH_SIZE = 20
HTTP_SERVER_ERROR_THRESHOLD = 500


@dataclass
class SyncResult:
    """Result of an image sync operation.

    Attributes:
        uploaded: Number of files uploaded/copied
        skipped: Number of files skipped (already exist at destination)
        failed: Number of files that failed to sync
        errors: Error messages for failed files
    """

    uploaded: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


class ImageSyncStrategy(ABC):
    """Abstract strategy for syncing images to WordPress."""

    @abstractmethod
    def sync_batch(self, file_paths: list[Path]) -> SyncResult:
        """Sync a batch of image files to WordPress.

        Args:
            file_paths: List of local AVIF file paths to sync

        Returns:
            SyncResult with counts of uploaded/skipped/failed files
        """

    @abstractmethod
    def verify_connection(self) -> bool:
        """Verify that the sync target is reachable.

        Returns:
            True if connection is valid, False otherwise
        """


class LocalFileSyncer(ImageSyncStrategy):
    """Sync images by copying files directly to a WordPress uploads directory.

    Suitable for DDEV or other local WordPress installations where the
    filesystem is directly accessible.

    Attributes:
        target_dir: Destination directory inside WordPress uploads
    """

    def __init__(self, wp_uploads_dir: Path) -> None:
        """Initialize local file syncer.

        Args:
            wp_uploads_dir: Path to WordPress wp-content/uploads directory
        """
        self.target_dir = Path(wp_uploads_dir) / "csf-parts" / "images" / "avif"

    def sync_batch(self, file_paths: list[Path]) -> SyncResult:
        """Copy AVIF files to the WordPress uploads directory.

        Skips files that already exist at the destination with the same size.

        Args:
            file_paths: List of local AVIF file paths to copy

        Returns:
            SyncResult with counts
        """
        result = SyncResult()
        self.target_dir.mkdir(parents=True, exist_ok=True)

        for src_path in file_paths:
            dest_path = self.target_dir / src_path.name
            try:
                # Skip if file exists with same size
                if dest_path.exists() and dest_path.stat().st_size == src_path.stat().st_size:
                    result.skipped += 1
                    continue

                shutil.copy2(src_path, dest_path)
                result.uploaded += 1
                logger.debug("image_synced_local", file=src_path.name)

            except OSError as e:
                result.failed += 1
                result.errors.append(f"{src_path.name}: {e}")
                logger.warning("image_sync_failed_local", file=src_path.name, error=str(e))

        return result

    def verify_connection(self) -> bool:
        """Verify the target directory is writable.

        Returns:
            True if directory exists or can be created and is writable
        """
        try:
            self.target_dir.mkdir(parents=True, exist_ok=True)
            return self.target_dir.is_dir()
        except OSError:
            return False


class RemoteAPISyncer(ImageSyncStrategy):
    """Sync images via the WordPress REST API.

    Uploads AVIF files to the csf/v1/images/upload endpoint in batches.

    Attributes:
        wp_url: Base WordPress URL
        api_key: API key for authentication
    """

    def __init__(self, wp_url: str, api_key: str, timeout: int = 60) -> None:
        """Initialize remote API syncer.

        Args:
            wp_url: WordPress site URL (e.g., "https://example.com")
            api_key: CSF API key for X-CSF-API-Key header
            timeout: HTTP request timeout in seconds
        """
        self.wp_url = wp_url.rstrip("/")
        self.api_key = api_key
        self.endpoint = f"{self.wp_url}/wp-json/csf/v1/images/upload"
        self.client = httpx.Client(timeout=timeout)

    def sync_batch(self, file_paths: list[Path]) -> SyncResult:
        """Upload AVIF files to WordPress via REST API.

        Sends files in batches of REMOTE_BATCH_SIZE as multipart uploads.

        Args:
            file_paths: List of local AVIF file paths to upload

        Returns:
            SyncResult with counts
        """
        result = SyncResult()

        for i in range(0, len(file_paths), REMOTE_BATCH_SIZE):
            batch = file_paths[i : i + REMOTE_BATCH_SIZE]
            batch_result = self._upload_batch(batch)
            result.uploaded += batch_result.uploaded
            result.skipped += batch_result.skipped
            result.failed += batch_result.failed
            result.errors.extend(batch_result.errors)

        return result

    def _upload_batch(self, file_paths: list[Path]) -> SyncResult:
        """Upload a single batch of files.

        Args:
            file_paths: Batch of file paths to upload

        Returns:
            SyncResult for this batch
        """
        result = SyncResult()
        files = []

        try:
            for path in file_paths:
                files.append(("files", (path.name, path.read_bytes(), "image/avif")))

            response = self.client.post(
                self.endpoint,
                files=files,
                headers={"X-CSF-API-Key": self.api_key},
            )
            response.raise_for_status()
            data = response.json()

            result.uploaded = data.get("results", {}).get("uploaded", 0)
            result.skipped = data.get("results", {}).get("skipped", 0)

            errors = data.get("results", {}).get("errors", [])
            if errors:
                result.failed = len(errors)
                result.errors.extend(errors)

        except (httpx.HTTPError, OSError, ValueError) as e:
            # Entire batch failed
            result.failed = len(file_paths)
            result.errors.append(f"Batch upload failed: {e}")
            logger.warning("image_sync_batch_failed", error=str(e))

        return result

    def verify_connection(self) -> bool:
        """Verify the WordPress REST API is reachable and authenticated.

        Returns:
            True if endpoint responds to OPTIONS/HEAD, False otherwise
        """
        try:
            response = self.client.head(
                self.endpoint,
                headers={"X-CSF-API-Key": self.api_key},
            )
        except httpx.HTTPError:
            return False
        else:
            # Accept 200, 404 (endpoint exists but may not support HEAD),
            # or 405 (method not allowed — endpoint exists)
            return response.status_code < HTTP_SERVER_ERROR_THRESHOLD

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()


class ImageSyncer:
    """Orchestrates image syncing and cleanup.

    Coordinates between the ImageProcessor (which tracks sync status
    in its manifest) and a sync strategy (local or remote).

    Supports two modes:
    - Batch sync via sync(): sync all unsynced images at once
    - Streaming sync via sync_and_cleanup_for_sku(): sync per-SKU during scraping

    Attributes:
        strategy: The sync strategy to use
        image_processor: ImageProcessor with manifest tracking
        cumulative_result: Running totals across all streaming sync calls
    """

    def __init__(
        self,
        strategy: ImageSyncStrategy,
        image_processor: ImageProcessor,
    ) -> None:
        """Initialize image syncer.

        Args:
            strategy: Sync strategy (LocalFileSyncer or RemoteAPISyncer)
            image_processor: ImageProcessor instance with manifest
        """
        self.strategy = strategy
        self.image_processor = image_processor
        self.cumulative_result = SyncResult()

    def sync(self) -> SyncResult:
        """Sync unsynced images to WordPress.

        Reads the manifest for unsynced files, syncs them via the
        configured strategy, and marks successfully synced files.

        Returns:
            SyncResult with totals
        """
        unsynced = self.image_processor.get_unsynced_files()
        if not unsynced:
            logger.info("image_sync_nothing_to_sync")
            return SyncResult()

        # Resolve to actual file paths, filtering out files that don't exist on disk
        file_paths = []
        for filename in unsynced:
            path = self.image_processor.avif_dir / filename
            if path.exists():
                file_paths.append(path)
            else:
                logger.debug("image_sync_file_missing", filename=filename)

        if not file_paths:
            logger.info("image_sync_no_files_on_disk")
            return SyncResult()

        logger.info("image_sync_starting", count=len(file_paths))
        result = self.strategy.sync_batch(file_paths)

        # Mark successfully synced files in manifest
        synced_filenames = {p.name for p in file_paths}
        failed_filenames = {e.split(":")[0] for e in result.errors}
        for filename in synced_filenames - failed_filenames:
            self.image_processor.mark_synced(filename)

        # Persist manifest with updated sync status
        self.image_processor._save_manifest()  # noqa: SLF001

        logger.info(
            "image_sync_complete",
            uploaded=result.uploaded,
            skipped=result.skipped,
            failed=result.failed,
        )
        return result

    def sync_and_cleanup_for_sku(self, sku: str) -> SyncResult:
        """Sync all unsynced images for a SKU, then delete local copies.

        Used for streaming sync during scraping — called after each detail
        page is processed so images are delivered incrementally rather than
        accumulating on disk.

        Args:
            sku: Part SKU (e.g., "CSF-3680") to match against filenames

        Returns:
            SyncResult for this SKU's images
        """
        unsynced = self.image_processor.get_unsynced_files()
        sku_prefix = f"{sku}_"
        sku_files = [f for f in unsynced if f.startswith(sku_prefix)]

        if not sku_files:
            return SyncResult()

        # Resolve to file paths, filtering out missing files
        file_paths = []
        for filename in sku_files:
            path = self.image_processor.avif_dir / filename
            if path.exists():
                file_paths.append(path)

        if not file_paths:
            return SyncResult()

        # Sync this SKU's images
        result = self.strategy.sync_batch(file_paths)

        # Mark successfully synced files in manifest
        synced_filenames = {p.name for p in file_paths}
        failed_filenames = {e.split(":")[0] for e in result.errors}
        for filename in synced_filenames - failed_filenames:
            self.image_processor.mark_synced(filename)

        # Persist manifest with updated sync status
        self.image_processor._save_manifest()  # noqa: SLF001

        # Delete synced local files to free disk space
        for filename in synced_filenames - failed_filenames:
            path = self.image_processor.avif_dir / filename
            if path.exists():
                try:
                    path.unlink()
                except OSError as e:
                    logger.warning("streaming_cleanup_failed", filename=filename, error=str(e))

        # Accumulate totals
        self.cumulative_result.uploaded += result.uploaded
        self.cumulative_result.skipped += result.skipped
        self.cumulative_result.failed += result.failed
        self.cumulative_result.errors.extend(result.errors)

        logger.debug(
            "streaming_sync_sku_complete",
            sku=sku,
            uploaded=result.uploaded,
            skipped=result.skipped,
            failed=result.failed,
        )

        return result

    def cleanup(self) -> int:
        """Delete synced AVIF files from the local staging directory.

        Only deletes files where synced=True in the manifest. Files that
        failed to sync are preserved for retry.

        Returns:
            Number of files deleted
        """
        synced = self.image_processor.get_synced_files()
        deleted = 0

        for filename in synced:
            path = self.image_processor.avif_dir / filename
            if path.exists():
                try:
                    path.unlink()
                    deleted += 1
                    logger.debug("image_cleanup_deleted", filename=filename)
                except OSError as e:
                    logger.warning("image_cleanup_failed", filename=filename, error=str(e))

        if deleted > 0:
            logger.info("image_cleanup_complete", deleted=deleted)

        return deleted
