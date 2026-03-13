"""Unit tests for StateSyncer.

Tests cover:
- pull(): downloads state from WP, handles 404, handles errors
- push(): uploads state to WP, handles missing files, handles errors
- Key validation against allowlist
"""

import json
from pathlib import Path

import httpx
import pytest
from pytest_mock import MockerFixture

from src.scraper.state_syncer import ALLOWED_KEYS, StateSyncer

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def syncer(mocker: MockerFixture) -> StateSyncer:
    """Provide a StateSyncer with a mocked HTTP client."""
    s = StateSyncer(wp_url="https://example.com", api_key="test-key")
    s.client.close()
    s.client = mocker.Mock(spec=httpx.Client)
    return s


# ---------------------------------------------------------------------------
# Pull Tests
# ---------------------------------------------------------------------------


class TestStateSyncerPull:
    """Test StateSyncer.pull() downloads state files."""

    def test_pull_downloads_and_writes_file(
        self, syncer: StateSyncer, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        """pull() writes response body to local path on 200."""
        # Arrange
        local_path = tmp_path / "checkpoints" / "etags.json"
        mock_response = mocker.Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = '{"url1": "hash1"}'
        mock_response.raise_for_status = mocker.Mock()
        syncer.client.get.return_value = mock_response

        # Act
        result = syncer.pull("etags", local_path)

        # Assert
        assert result is True
        assert local_path.exists()
        assert json.loads(local_path.read_text()) == {"url1": "hash1"}

    def test_pull_returns_false_on_404(
        self, syncer: StateSyncer, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        """pull() returns False when server returns 404."""
        # Arrange
        local_path = tmp_path / "etags.json"
        mock_response = mocker.Mock(spec=httpx.Response)
        mock_response.status_code = 404
        syncer.client.get.return_value = mock_response

        # Act
        result = syncer.pull("etags", local_path)

        # Assert
        assert result is False
        assert not local_path.exists()

    def test_pull_returns_false_on_http_error(self, syncer: StateSyncer, tmp_path: Path) -> None:
        """pull() returns False on network error."""
        # Arrange
        local_path = tmp_path / "etags.json"
        syncer.client.get.side_effect = httpx.HTTPError("Connection refused")

        # Act
        result = syncer.pull("etags", local_path)

        # Assert
        assert result is False

    def test_pull_rejects_invalid_key(self, syncer: StateSyncer, tmp_path: Path) -> None:
        """pull() returns False for keys not in the allowlist."""
        # Arrange
        local_path = tmp_path / "bad.json"

        # Act
        result = syncer.pull("evil_key", local_path)

        # Assert
        assert result is False
        syncer.client.get.assert_not_called()

    def test_pull_creates_parent_directory(
        self, syncer: StateSyncer, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        """pull() creates parent directories for the local path."""
        # Arrange
        local_path = tmp_path / "deep" / "nested" / "etags.json"
        mock_response = mocker.Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = "{}"
        mock_response.raise_for_status = mocker.Mock()
        syncer.client.get.return_value = mock_response

        # Act
        result = syncer.pull("etags", local_path)

        # Assert
        assert result is True
        assert local_path.parent.exists()


# ---------------------------------------------------------------------------
# Push Tests
# ---------------------------------------------------------------------------


class TestStateSyncerPush:
    """Test StateSyncer.push() uploads state files."""

    def test_push_uploads_file_content(
        self, syncer: StateSyncer, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        """push() POSTs file content to the endpoint on success."""
        # Arrange
        local_path = tmp_path / "etags.json"
        local_path.write_text('{"url1": "hash1"}')
        mock_response = mocker.Mock(spec=httpx.Response)
        mock_response.raise_for_status = mocker.Mock()
        syncer.client.post.return_value = mock_response

        # Act
        result = syncer.push("etags", local_path)

        # Assert
        assert result is True
        syncer.client.post.assert_called_once()
        call_kwargs = syncer.client.post.call_args
        assert "application/json" in str(call_kwargs)

    def test_push_returns_false_for_missing_file(self, syncer: StateSyncer, tmp_path: Path) -> None:
        """push() returns False when local file does not exist."""
        # Arrange
        local_path = tmp_path / "nonexistent.json"

        # Act
        result = syncer.push("etags", local_path)

        # Assert
        assert result is False
        syncer.client.post.assert_not_called()

    def test_push_returns_false_on_http_error(self, syncer: StateSyncer, tmp_path: Path) -> None:
        """push() returns False on network error."""
        # Arrange
        local_path = tmp_path / "etags.json"
        local_path.write_text("{}")
        syncer.client.post.side_effect = httpx.HTTPError("500 Internal Server Error")

        # Act
        result = syncer.push("etags", local_path)

        # Assert
        assert result is False

    def test_push_rejects_invalid_key(self, syncer: StateSyncer, tmp_path: Path) -> None:
        """push() returns False for keys not in the allowlist."""
        # Arrange
        local_path = tmp_path / "bad.json"
        local_path.write_text("{}")

        # Act
        result = syncer.push("evil_key", local_path)

        # Assert
        assert result is False
        syncer.client.post.assert_not_called()


# ---------------------------------------------------------------------------
# Endpoint Construction Tests
# ---------------------------------------------------------------------------


class TestStateSyncerEndpoint:
    """Test StateSyncer endpoint URL construction via observable behavior."""

    def test_pull_uses_correct_endpoint_url(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """pull() requests the correct csf/v1/scraper-state/ URL."""
        # Arrange
        syncer = StateSyncer(wp_url="https://example.com/", api_key="key")
        syncer.client.close()
        syncer.client = mocker.Mock(spec=httpx.Client)
        mock_response = mocker.Mock(spec=httpx.Response)
        mock_response.status_code = 404
        syncer.client.get.return_value = mock_response

        # Act
        syncer.pull("etags", tmp_path / "etags.json")

        # Assert — check the URL passed to client.get
        call_url = syncer.client.get.call_args.args[0]
        assert call_url == "https://example.com/wp-json/csf/v1/scraper-state/etags"

    def test_trailing_slash_stripped_from_wp_url(
        self, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        """Trailing slash on wp_url does not cause double slashes in URL."""
        # Arrange
        syncer = StateSyncer(wp_url="https://example.com/", api_key="key")
        syncer.client.close()
        syncer.client = mocker.Mock(spec=httpx.Client)
        mock_response = mocker.Mock(spec=httpx.Response)
        mock_response.status_code = 404
        syncer.client.get.return_value = mock_response

        # Act
        syncer.pull("manifest", tmp_path / "manifest.json")

        # Assert — no double slash (excluding https://)
        call_url = syncer.client.get.call_args.args[0]
        assert "//" not in call_url.replace("https://", "")


# ---------------------------------------------------------------------------
# Allowed Keys Tests
# ---------------------------------------------------------------------------


class TestAllowedKeys:
    """Test that ALLOWED_KEYS is properly restricted."""

    def test_etags_is_allowed(self) -> None:
        """'etags' is in the allowlist."""
        assert "etags" in ALLOWED_KEYS

    def test_detail_etags_is_allowed(self) -> None:
        """'detail_etags' is in the allowlist."""
        assert "detail_etags" in ALLOWED_KEYS

    def test_manifest_is_allowed(self) -> None:
        """'manifest' is in the allowlist."""
        assert "manifest" in ALLOWED_KEYS

    def test_arbitrary_keys_are_rejected(self) -> None:
        """Random keys are not in the allowlist."""
        assert "passwords" not in ALLOWED_KEYS
        assert "wp_config" not in ALLOWED_KEYS


# ---------------------------------------------------------------------------
# push_parts Tests
# ---------------------------------------------------------------------------


class TestPushParts:
    """Test push_parts method for importing parts into WordPress."""

    def test_push_parts_success(
        self, syncer: StateSyncer, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        """Successfully pushes parts JSON to WP import endpoint."""
        # Arrange
        parts_file = tmp_path / "parts_complete.json"
        parts_file.write_text(json.dumps({"parts": [{"sku": "CSF-001"}]}))

        mock_response = mocker.Mock(spec=httpx.Response)
        mock_response.json.return_value = {
            "success": True,
            "results": {"created": 1, "updated": 0, "skipped": 0},
        }
        syncer.client.post.return_value = mock_response

        # Act
        result = syncer.push_parts(parts_file)

        # Assert
        assert result is True
        syncer.client.post.assert_called_once()
        call_url = syncer.client.post.call_args.args[0]
        assert "/wp-json/csf/v1/import" in call_url

    def test_push_parts_file_missing(self, syncer: StateSyncer, tmp_path: Path) -> None:
        """Returns False when parts file does not exist."""
        # Act
        result = syncer.push_parts(tmp_path / "nonexistent.json")

        # Assert
        assert result is False
        syncer.client.post.assert_not_called()

    def test_push_parts_http_error(self, syncer: StateSyncer, tmp_path: Path) -> None:
        """Returns False on HTTP error."""
        # Arrange
        parts_file = tmp_path / "parts_complete.json"
        parts_file.write_text('{"parts": []}')
        syncer.client.post.side_effect = httpx.HTTPError("Server error")

        # Act
        result = syncer.push_parts(parts_file)

        # Assert
        assert result is False
