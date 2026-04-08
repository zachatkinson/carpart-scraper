"""Push/pull scraper state files to/from WordPress REST API.

Enables ephemeral CI runners (e.g., GitHub Actions) to persist state across
cron runs. State files (etags.json, manifest.json) are stored on the WordPress
server at wp-content/uploads/csf-parts/state/.

For local mode (wp_url is a directory), state already persists on disk,
so this module is only needed for remote mode.
"""

from pathlib import Path

import httpx
import structlog

logger = structlog.get_logger()

HTTP_NOT_FOUND = 404
HTTP_SERVER_ERROR_THRESHOLD = 500

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

    def push_parts(self, parts_file: Path) -> bool:
        """Push parts_complete.json to WordPress import endpoint.

        Posts the parts JSON data to /csf/v1/import, which triggers
        the WP plugin's importer to create/update part posts.

        Args:
            parts_file: Path to parts_complete.json

        Returns:
            True if import succeeded, False on error
        """
        if not parts_file.exists():
            logger.info("parts_push_file_missing", path=str(parts_file))
            return False

        try:
            content = parts_file.read_text()
            endpoint = f"{self.wp_url}/wp-json/csf/v1/import"

            response = self.client.post(
                endpoint,
                headers={
                    "X-CSF-API-Key": self.api_key,
                    "Content-Type": "application/json",
                },
                content=content,
                timeout=120,
            )
            response.raise_for_status()
            result = response.json()

            results = result.get("results", {})
            logger.info(
                "parts_push_success",
                created=results.get("created", 0),
                updated=results.get("updated", 0),
                unchanged=results.get("unchanged", 0),
                skipped=results.get("skipped", 0),
                path=str(parts_file),
            )

        except httpx.HTTPError as e:
            logger.exception("parts_push_failed", error=str(e), path=str(parts_file))
            return False
        else:
            return True

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()
