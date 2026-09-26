"""Tests for the sync-images CLI command.

The command is exercised through Click's runner with the image processor,
sync strategies and syncer mocked at the module boundary, so the tests pin
the command's behaviour (what it prints, what it calls, how it exits)
rather than the collaborators' internals.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner
from pytest_mock import MockerFixture

from src.cli.commands.sync_images import _create_strategy, sync_images


@pytest.fixture
def cli_runner() -> CliRunner:
    """Click runner for invoking the command."""
    return CliRunner()


@pytest.fixture
def processor(mocker: MockerFixture, tmp_path: Path) -> MagicMock:
    """ImageProcessor stand-in with two unsynced files, one of which exists on disk."""
    avif_dir = tmp_path / "avif"
    avif_dir.mkdir()
    (avif_dir / "CSF-1_0.avif").write_bytes(b"avif")
    mock = MagicMock()
    mock.avif_dir = avif_dir
    mock.get_unsynced_files.return_value = ["CSF-1_0.avif", "CSF-2_0.avif"]
    mocker.patch("src.cli.commands.sync_images.ImageProcessor", return_value=mock)
    return mock


@pytest.fixture
def syncer(mocker: MockerFixture) -> MagicMock:
    """ImageSyncer stand-in reporting one upload and one failure."""
    mock = MagicMock()
    mock.sync.return_value = MagicMock(
        uploaded=1, skipped=0, failed=1, errors=["CSF-2_0.avif: 500"]
    )
    mock.cleanup.return_value = 1
    mocker.patch("src.cli.commands.sync_images.ImageSyncer", return_value=mock)
    return mock


@pytest.fixture
def local_strategy(mocker: MockerFixture) -> MagicMock:
    """LocalFileSyncer stand-in whose connection check passes."""
    mock = MagicMock()
    mock.verify_connection.return_value = True
    mocker.patch("src.cli.commands.sync_images.LocalFileSyncer", return_value=mock)
    return mock


class TestSyncImagesCommand:
    """Behaviour of `carpart sync-images`."""

    def test_nothing_to_sync_reports_and_exits_cleanly(
        self, cli_runner: CliRunner, processor: MagicMock, tmp_path: Path
    ) -> None:
        """With no unsynced files the command says so and touches nothing else."""
        # Arrange
        processor.get_unsynced_files.return_value = []

        # Act
        result = cli_runner.invoke(sync_images, ["--wp-url", str(tmp_path)])

        # Assert
        assert result.exit_code == 0
        assert "already synced" in result.output
        processor.close.assert_called_once()

    def test_dry_run_lists_files_with_disk_status_and_syncs_nothing(
        self,
        cli_runner: CliRunner,
        processor: MagicMock,
        local_strategy: MagicMock,
        syncer: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Dry run names each pending file, says whether it is on disk, and never syncs."""
        # Act
        result = cli_runner.invoke(sync_images, ["--wp-url", str(tmp_path), "--dry-run"])

        # Assert
        assert result.exit_code == 0
        assert "2 files would be synced" in result.output
        assert "CSF-1_0.avif (on disk)" in result.output
        assert "CSF-2_0.avif (missing)" in result.output
        syncer.sync.assert_not_called()
        local_strategy.verify_connection.assert_not_called()

    def test_local_sync_reports_results_errors_and_cleans_up(
        self,
        cli_runner: CliRunner,
        processor: MagicMock,
        local_strategy: MagicMock,
        syncer: MagicMock,
        tmp_path: Path,
    ) -> None:
        """A local-path target syncs, prints the tallies and errors, then cleans up."""
        # Act
        result = cli_runner.invoke(sync_images, ["--wp-url", str(tmp_path)])

        # Assert
        assert result.exit_code == 0
        assert "Uploaded:  1" in result.output
        assert "Failed:    1" in result.output
        assert "CSF-2_0.avif: 500" in result.output
        assert "Cleaned up: 1 local files" in result.output
        syncer.cleanup.assert_called_once()
        processor.close.assert_called_once()

    def test_no_cleanup_flag_keeps_local_files(
        self,
        cli_runner: CliRunner,
        processor: MagicMock,
        local_strategy: MagicMock,
        syncer: MagicMock,
        tmp_path: Path,
    ) -> None:
        """--no-cleanup syncs but leaves the staged files alone."""
        # Act
        result = cli_runner.invoke(sync_images, ["--wp-url", str(tmp_path), "--no-cleanup"])

        # Assert
        assert result.exit_code == 0
        syncer.cleanup.assert_not_called()
        assert "Cleaned up" not in result.output

    def test_remote_target_without_key_is_a_usage_error(
        self, cli_runner: CliRunner, processor: MagicMock
    ) -> None:
        """An HTTP target needs an API key; the command refuses before connecting."""
        # Act
        result = cli_runner.invoke(sync_images, ["--wp-url", "https://site.example"])

        # Assert
        assert result.exit_code == 2
        assert "--wp-api-key is required" in result.output

    def test_unreachable_target_exits_with_failure(
        self, cli_runner: CliRunner, processor: MagicMock, mocker: MockerFixture, syncer: MagicMock
    ) -> None:
        """A failed connection check aborts with exit code 1 and no sync attempt."""
        # Arrange
        remote = MagicMock()
        remote.verify_connection.return_value = False
        mocker.patch("src.cli.commands.sync_images.RemoteAPISyncer", return_value=remote)

        # Act
        result = cli_runner.invoke(
            sync_images, ["--wp-url", "https://site.example", "--wp-api-key", "k"]
        )

        # Assert
        assert result.exit_code == 1
        assert "Cannot connect" in result.output
        syncer.sync.assert_not_called()
        processor.close.assert_called_once()

    def test_unexpected_error_is_reported_and_exits_with_failure(
        self, cli_runner: CliRunner, processor: MagicMock, tmp_path: Path
    ) -> None:
        """Any other failure is surfaced as an error line with exit code 1."""
        # Arrange
        processor.get_unsynced_files.side_effect = OSError("manifest unreadable")

        # Act
        result = cli_runner.invoke(sync_images, ["--wp-url", str(tmp_path)])

        # Assert
        assert result.exit_code == 1
        assert "manifest unreadable" in result.output


class TestCreateStrategy:
    """Target selection from the --wp-url value."""

    def test_directory_selects_local_syncer(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """An existing directory means a local file copy."""
        # Arrange
        local = mocker.patch("src.cli.commands.sync_images.LocalFileSyncer")

        # Act
        _create_strategy(str(tmp_path), None)

        # Assert
        local.assert_called_once_with(wp_uploads_dir=tmp_path)

    def test_url_with_key_selects_remote_syncer(self, mocker: MockerFixture) -> None:
        """An HTTP(S) URL plus key means the REST uploader."""
        # Arrange
        remote = mocker.patch("src.cli.commands.sync_images.RemoteAPISyncer")

        # Act
        _create_strategy("https://site.example", "secret")

        # Assert
        remote.assert_called_once_with(wp_url="https://site.example", api_key="secret")

    def test_unrecognised_target_is_a_usage_error(self) -> None:
        """Something that is neither a path nor a URL is rejected up front."""
        # Act & Assert
        with pytest.raises(Exception, match="must be a local directory path or HTTP"):
            _create_strategy("not-a-target", None)
