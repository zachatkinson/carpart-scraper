"""Push/pull scraper state files to/from WordPress REST API.

Enables ephemeral CI runners (e.g., GitHub Actions) to persist state across
cron runs. State files (etags.json, manifest.json) are stored on the WordPress
server at wp-content/uploads/csf-parts/state/.

For local mode (wp_url is a directory), state already persists on disk,
so this module is only needed for remote mode.
"""

import json
from pathlib import Path

import httpx
import structlog

logger = structlog.get_logger()

HTTP_NOT_FOUND = 404
HTTP_SERVER_ERROR_THRESHOLD = 500

# Parts are pushed in chunks so a single request body stays small enough for
# the WordPress server to decode within its PHP memory limit. A full-catalog
# push (~13 MB JSON) in one request causes an out-of-memory 500 on hosts with
# default limits.
PARTS_CHUNK_SIZE = 200

# Importing a chunk creates/updates posts server-side, which is slower than a
# state-file write — allow more time than the default client timeout.
PARTS_PUSH_TIMEOUT_SECONDS = 300

# Only these keys are allowed — prevents arbitrary file writes on the server
ALLOWED_KEYS = frozenset({"etags", "detail_etags", "manifest"})


class StateSyncer:
    """Push/pull scraper state files to/from WordPress REST API.

    Attributes:
        wp_url: Base WordPress URL
        api_key: API key for X-CSF-API-Key header
    """

    def __init__(self, wp_url: str, api_key: str, timeout: int = 30) -> None:
        """Initialize state syncer.

        Args:
            wp_url: WordPress site URL (e.g., "https://example.com")
            api_key: CSF API key for authentication
            timeout: HTTP request timeout in seconds
        """
        self.wp_url = wp_url.rstrip("/")
        self.api_key = api_key
        self.client = httpx.Client(timeout=timeout)

    def _endpoint(self, key: str) -> str:
        """Build endpoint URL for a state key.

        Args:
            key: State key (e.g., "etags", "manifest")

        Returns:
            Full endpoint URL
        """
        return f"{self.wp_url}/wp-json/csf/v1/scraper-state/{key}"

    def pull(self, key: str, local_path: Path) -> bool:
        """Download state from WordPress to a local path.

        Args:
            key: State key (must be in ALLOWED_KEYS)
            local_path: Local file path to write the downloaded state

        Returns:
            True if state was downloaded, False if 404 or error
        """
        if key not in ALLOWED_KEYS:
            logger.warning("state_pull_invalid_key", key=key)
            return False

        try:
            response = self.client.get(
                self._endpoint(key),
                headers={"X-CSF-API-Key": self.api_key},
            )

            if response.status_code == HTTP_NOT_FOUND:
                logger.info("state_pull_not_found", key=key)
                return False

            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.warning("state_pull_failed", key=key, error=str(e))
            return False
        else:
            # Ensure parent directory exists
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_text(response.text)

            logger.info(
                "state_pull_success",
                key=key,
                path=str(local_path),
                size=len(response.text),
            )
            return True

    def push(self, key: str, local_path: Path) -> bool:
        """Upload a local state file to WordPress.

        Args:
            key: State key (must be in ALLOWED_KEYS)
            local_path: Local file path to upload

        Returns:
            True if state was uploaded, False on error
        """
        if key not in ALLOWED_KEYS:
            logger.warning("state_push_invalid_key", key=key)
            return False

        if not local_path.exists():
            logger.info("state_push_file_missing", key=key, path=str(local_path))
            return False

        try:
            content = local_path.read_text()
            response = self.client.post(
                self._endpoint(key),
                headers={
                    "X-CSF-API-Key": self.api_key,
                    "Content-Type": "application/json",
                },
                content=content,
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.warning("state_push_failed", key=key, error=str(e))
            return False
        else:
            logger.info(
                "state_push_success",
                key=key,
                path=str(local_path),
                size=len(content),
            )
            return True

    def push_parts(self, parts_file: Path, chunk_size: int = PARTS_CHUNK_SIZE) -> bool:
        """Push a parts export to the WordPress import endpoint in chunks.

        Splits the parts list into batches of ``chunk_size`` and POSTs each
        batch to /csf/v1/import separately, so request bodies stay within the
        server's PHP memory limit regardless of catalog size. Aborts on the
        first failed chunk; the import is idempotent (SKU-keyed upsert), so a
        retry re-imports safely.

        Args:
            parts_file: Path to a parts export (parts_complete.json or
                parts_delta.json)
            chunk_size: Maximum number of parts per request

        Returns:
            True if all chunks imported successfully, False on error
        """
        if not parts_file.exists():
            logger.info("parts_push_file_missing", path=str(parts_file))
            return False

        try:
            data = json.loads(parts_file.read_text())
        except (OSError, json.JSONDecodeError) as e:
            logger.exception("parts_push_read_failed", error=str(e), path=str(parts_file))
            return False

        parts = data.get("parts", [])
        metadata = data.get("metadata", {})

        if not parts:
            logger.info("parts_push_skipped_empty", path=str(parts_file))
            return True

        endpoint = f"{self.wp_url}/wp-json/csf/v1/import"
        chunks = [parts[i : i + chunk_size] for i in range(0, len(parts), chunk_size)]
        totals = {"created": 0, "updated": 0, "unchanged": 0, "skipped": 0}

        for chunk_num, chunk in enumerate(chunks, start=1):
            try:
                response = self.client.post(
                    endpoint,
                    headers={"X-CSF-API-Key": self.api_key},
                    json={"metadata": metadata, "parts": chunk},
                    timeout=PARTS_PUSH_TIMEOUT_SECONDS,
                )
                response.raise_for_status()
                results = response.json().get("results", {})
            except httpx.HTTPError as e:
                logger.exception(
                    "parts_push_failed",
                    chunk=chunk_num,
                    total_chunks=len(chunks),
                    error=str(e),
                    path=str(parts_file),
                )
                return False

            for key in totals:
                totals[key] += int(results.get(key, 0))

            logger.info(
                "parts_push_chunk_complete",
                chunk=chunk_num,
                total_chunks=len(chunks),
                parts_in_chunk=len(chunk),
            )

        logger.info(
            "parts_push_success",
            created=totals["created"],
            updated=totals["updated"],
            unchanged=totals["unchanged"],
            skipped=totals["skipped"],
            total_chunks=len(chunks),
            path=str(parts_file),
        )
        return True

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()
