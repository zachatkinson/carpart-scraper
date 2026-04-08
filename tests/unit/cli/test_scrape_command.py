"""Unit tests for scrape command.

This module contains comprehensive tests for the CLI scrape command,
following AAA (Arrange-Act-Assert) testing pattern.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner
from pytest_mock import MockerFixture

from src.cli.commands.scrape import _is_remote_wp, scrape
from src.scraper.orchestrator import ScraperOrchestrator

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide Click CLI test runner.

    Returns:
        CliRunner instance for testing Click commands
    """
    return CliRunner()


@pytest.fixture
def mock_orchestrator(mocker: MockerFixture) -> MagicMock:
    """Provide mocked ScraperOrchestrator for scrape command.

    Args:
        mocker: pytest-mock fixture

    Returns:
        Mock ScraperOrchestrator class
    """
    mock_cls = mocker.patch("src.cli.commands.scrape.ScraperOrchestrator")
    mock_instance = MagicMock(spec=ScraperOrchestrator)

    # Default return values
    mock_instance.scrape_all.return_value = {
        "unique_parts": 5,
        "total_applications": 10,
        "applications_processed": 10,
        "applications_skipped_unchanged": 0,
        "parts_scraped": 15,
        "new_parts": 5,
        "changed_parts": 0,
        "vehicles_tracked": 20,
        "make_filter": None,
        "year_filter": None,
        "details_fetched": True,
        "details_fetched_count": 5,
        "resumed": False,
        "applications_failed": 0,
        "details_failed": 0,
        "failure_summary": {"total_failures": 0, "by_phase": {}, "retryable": 0, "permanent": 0},
    }
    mock_instance.export_data.return_value = {
        "parts": Path("exports/parts.json"),
        "compatibility": Path("exports/compatibility.json"),
    }
    mock_instance.export_complete.return_value = Path("exports/parts_complete.json")
    mock_instance.export_complete_delta.return_value = Path("exports/parts_delta.json")
    mock_instance.new_skus = set()
    mock_instance.changed_skus = set()
    mock_instance.unique_parts = {}
    mock_instance.image_syncer = None
    mock_instance.image_processor = MagicMock()

    # Context manager support
    mock_instance.__enter__ = MagicMock(return_value=mock_instance)
    mock_instance.__exit__ = MagicMock(return_value=False)
    mock_cls.return_value = mock_instance

    return mock_cls


# ============================================================================
# Click Command Registration Tests
# ============================================================================


class TestScrapeCommandRegistration:
    """Test that scrape command is registered correctly."""

    def test_scrape_is_click_command(self) -> None:
        """Test scrape command is a Click command."""
        # Arrange & Act & Assert
        assert hasattr(scrape, "callback")
        assert hasattr(scrape, "params")

    def test_scrape_has_make_option(self) -> None:
        """Test scrape command has --make option."""
        # Arrange
        param_names = [param.name for param in scrape.params]

        # Act & Assert
        assert "make" in param_names

    def test_scrape_has_year_option(self) -> None:
        """Test scrape command has --year option."""
        # Arrange
        param_names = [param.name for param in scrape.params]

        # Act & Assert
        assert "year" in param_names

    def test_scrape_has_output_dir_option(self) -> None:
        """Test scrape command has --output-dir option."""
        # Arrange
        param_names = [param.name for param in scrape.params]

        # Act & Assert
        assert "output_dir" in param_names

    def test_scrape_has_catalog_only_option(self) -> None:
        """Test scrape command has --catalog-only option."""
        # Arrange
        param_names = [param.name for param in scrape.params]

        # Act & Assert
        assert "catalog_only" in param_names

    def test_scrape_has_incremental_option(self) -> None:
        """Test scrape command has --incremental option."""
        # Arrange
        param_names = [param.name for param in scrape.params]

        # Act & Assert
        assert "incremental" in param_names

    def test_scrape_has_resume_option(self) -> None:
        """Test scrape command has --resume option."""
        # Arrange
        param_names = [param.name for param in scrape.params]

        # Act & Assert
        assert "resume" in param_names

    def test_scrape_has_sync_images_option(self) -> None:
        """Test scrape command has --sync-images option."""
        # Arrange
        param_names = [param.name for param in scrape.params]

        # Act & Assert
        assert "sync_images" in param_names

    def test_scrape_has_wp_url_option(self) -> None:
        """Test scrape command has --wp-url option."""
        # Arrange
        param_names = [param.name for param in scrape.params]

        # Act & Assert
        assert "wp_url" in param_names

    def test_scrape_has_wp_api_key_option(self) -> None:
        """Test scrape command has --wp-api-key option."""
        # Arrange
        param_names = [param.name for param in scrape.params]

        # Act & Assert
        assert "wp_api_key" in param_names


# ============================================================================
# Click Command Option Handling Tests
# ============================================================================


class TestScrapeCommandOptions:
    """Test scrape command option handling."""

    def test_make_option_passes_to_orchestrator(
        self, cli_runner: CliRunner, mock_orchestrator: MagicMock
    ) -> None:
        """Test --make option is forwarded to orchestrator.scrape_all()."""
        # Arrange
        make_value = "Honda"

        # Act
        result = cli_runner.invoke(scrape, ["--make", make_value])

        # Assert
        assert result.exit_code == 0
        mock_instance = mock_orchestrator.return_value
        mock_instance.scrape_all.assert_called_once()
        call_kwargs = mock_instance.scrape_all.call_args.kwargs
        assert call_kwargs["make_filter"] == make_value

    def test_year_option_passes_to_orchestrator(
        self, cli_runner: CliRunner, mock_orchestrator: MagicMock
    ) -> None:
        """Test --year option is forwarded to orchestrator.scrape_all()."""
        # Arrange
        year_value = 2025

        # Act
        result = cli_runner.invoke(scrape, ["--year", str(year_value)])

        # Assert
        assert result.exit_code == 0
        mock_instance = mock_orchestrator.return_value
        call_kwargs = mock_instance.scrape_all.call_args.kwargs
        assert call_kwargs["year_filter"] == year_value

    def test_output_dir_passes_to_orchestrator_constructor(
        self, cli_runner: CliRunner, mock_orchestrator: MagicMock, tmp_path: Path
    ) -> None:
        """Test --output-dir is forwarded to ScraperOrchestrator constructor."""
        # Arrange
        output_dir = tmp_path / "custom_exports"

        # Act
        result = cli_runner.invoke(scrape, ["--output-dir", str(output_dir)])

        # Assert
        assert result.exit_code == 0
        mock_orchestrator.assert_called_once()
        call_kwargs = mock_orchestrator.call_args.kwargs
        assert call_kwargs["output_dir"] == output_dir

    def test_catalog_only_sets_fetch_details_false(
        self, cli_runner: CliRunner, mock_orchestrator: MagicMock
    ) -> None:
        """Test --catalog-only flag sets fetch_details=False."""
        # Act
        result = cli_runner.invoke(scrape, ["--catalog-only"])

        # Assert
        assert result.exit_code == 0
        mock_instance = mock_orchestrator.return_value
        call_kwargs = mock_instance.scrape_all.call_args.kwargs
        assert call_kwargs["fetch_details"] is False

    def test_default_sets_fetch_details_true(
        self, cli_runner: CliRunner, mock_orchestrator: MagicMock
    ) -> None:
        """Test default invocation sets fetch_details=True."""
        # Act
        result = cli_runner.invoke(scrape)

        # Assert
        assert result.exit_code == 0
        mock_instance = mock_orchestrator.return_value
        call_kwargs = mock_instance.scrape_all.call_args.kwargs
        assert call_kwargs["fetch_details"] is True

    def test_incremental_passes_to_constructor(
        self, cli_runner: CliRunner, mock_orchestrator: MagicMock
    ) -> None:
        """Test --incremental flag is forwarded to orchestrator constructor."""
        # Act
        result = cli_runner.invoke(scrape, ["--incremental"])

        # Assert
        assert result.exit_code == 0
        call_kwargs = mock_orchestrator.call_args.kwargs
        assert call_kwargs["incremental"] is True

    def test_resume_passes_to_scrape_all(
        self, cli_runner: CliRunner, mock_orchestrator: MagicMock
    ) -> None:
        """Test --resume flag is forwarded to scrape_all()."""
        # Act
        result = cli_runner.invoke(scrape, ["--resume"])

        # Assert
        assert result.exit_code == 0
        mock_instance = mock_orchestrator.return_value
        call_kwargs = mock_instance.scrape_all.call_args.kwargs
        assert call_kwargs["resume"] is True


# ============================================================================
# Validation Tests
# ============================================================================


class TestScrapeCommandValidation:
    """Test scrape command input validation."""

    def test_invalid_year_raises_error(self, cli_runner: CliRunner) -> None:
        """Test invalid year option raises error."""
        # Arrange
        invalid_year = "not-a-year"

        # Act
        result = cli_runner.invoke(scrape, ["--year", invalid_year])

        # Assert
        assert result.exit_code != 0
        assert "Invalid value" in result.output or "Error" in result.output


# ============================================================================
# Help Text Tests
# ============================================================================


class TestScrapeCommandHelp:
    """Test scrape command help text."""

    def test_help_text_displays_correctly(self, cli_runner: CliRunner) -> None:
        """Test help text displays correctly."""
        # Arrange & Act
        result = cli_runner.invoke(scrape, ["--help"])

        # Assert
        assert result.exit_code == 0
        assert "Scrape automotive parts data" in result.output
        assert "--make" in result.output
        assert "--year" in result.output
        assert "--output-dir" in result.output
        assert "--catalog-only" in result.output
        assert "--incremental" in result.output
        assert "--resume" in result.output
        assert "--sync-images" in result.output
        assert "--wp-url" in result.output
        assert "--wp-api-key" in result.output


# ============================================================================
# Workflow Tests
# ============================================================================


class TestScrapeCommandWorkflow:
    """Test scrape command full workflow."""

    def test_scrape_creates_orchestrator_as_context_manager(
        self, cli_runner: CliRunner, mock_orchestrator: MagicMock
    ) -> None:
        """Test scrape command creates orchestrator and uses it as context manager."""
        # Act
        result = cli_runner.invoke(scrape)

        # Assert
        assert result.exit_code == 0
        mock_orchestrator.assert_called_once()
        mock_instance = mock_orchestrator.return_value
        mock_instance.__enter__.assert_called_once()
        mock_instance.__exit__.assert_called_once()

    def test_scrape_calls_export_data(
        self, cli_runner: CliRunner, mock_orchestrator: MagicMock
    ) -> None:
        """Test scrape command calls export_data() after scraping."""
        # Act
        result = cli_runner.invoke(scrape)

        # Assert
        assert result.exit_code == 0
        mock_instance = mock_orchestrator.return_value
        mock_instance.export_data.assert_called_once()

    def test_scrape_calls_export_complete_when_fetch_details(
        self, cli_runner: CliRunner, mock_orchestrator: MagicMock
    ) -> None:
        """Test scrape command calls export_complete() when details are fetched."""
        # Act
        result = cli_runner.invoke(scrape)

        # Assert
        assert result.exit_code == 0
        mock_instance = mock_orchestrator.return_value
        mock_instance.export_complete.assert_called_once()

    def test_scrape_skips_export_complete_for_catalog_only(
        self, cli_runner: CliRunner, mock_orchestrator: MagicMock
    ) -> None:
        """Test scrape command skips export_complete() with --catalog-only."""
        # Act
        result = cli_runner.invoke(scrape, ["--catalog-only"])

        # Assert
        assert result.exit_code == 0
        mock_instance = mock_orchestrator.return_value
        mock_instance.export_complete.assert_not_called()

    def test_scrape_with_all_options(
        self, cli_runner: CliRunner, mock_orchestrator: MagicMock
    ) -> None:
        """Test scrape command with all options specified."""
        # Arrange
        make_value = "Toyota"
        year_value = "2024"
        output_dir_value = "custom_output"

        # Act
        result = cli_runner.invoke(
            scrape,
            [
                "--make",
                make_value,
                "--year",
                year_value,
                "--output-dir",
                output_dir_value,
                "--catalog-only",
                "--incremental",
            ],
        )

        # Assert
        assert result.exit_code == 0
        call_kwargs = mock_orchestrator.call_args.kwargs
        assert call_kwargs["incremental"] is True

        mock_instance = mock_orchestrator.return_value
        scrape_kwargs = mock_instance.scrape_all.call_args.kwargs
        assert scrape_kwargs["make_filter"] == make_value
        assert scrape_kwargs["year_filter"] == 2024
        assert scrape_kwargs["fetch_details"] is False

    def test_scrape_prints_summary(
        self, cli_runner: CliRunner, mock_orchestrator: MagicMock
    ) -> None:
        """Test scrape command prints a summary after completion."""
        # Act
        result = cli_runner.invoke(scrape)

        # Assert
        assert result.exit_code == 0
        assert "Scraping complete" in result.output
        assert "Unique parts" in result.output


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestScrapeCommandErrorHandling:
    """Test scrape command error handling."""

    def test_scrape_handles_keyboard_interrupt(
        self, cli_runner: CliRunner, mock_orchestrator: MagicMock
    ) -> None:
        """Test scrape command handles KeyboardInterrupt gracefully."""
        # Arrange
        mock_instance = mock_orchestrator.return_value
        mock_instance.scrape_all.side_effect = KeyboardInterrupt()

        # Act
        result = cli_runner.invoke(scrape)

        # Assert
        assert result.exit_code == 1
        assert "interrupted" in result.output.lower()

    def test_scrape_handles_unexpected_exception(
        self, cli_runner: CliRunner, mock_orchestrator: MagicMock
    ) -> None:
        """Test scrape command handles unexpected exceptions."""
        # Arrange
        mock_instance = mock_orchestrator.return_value
        mock_instance.scrape_all.side_effect = RuntimeError("Connection failed")

        # Act
        result = cli_runner.invoke(scrape)

        # Assert
        assert result.exit_code == 1
        assert "Connection failed" in result.output


# ============================================================================
# Exit Code Tests
# ============================================================================


class TestScrapeCommandExitCodes:
    """Test scrape command exit code computation."""

    def test_exit_code_0_on_success(
        self, cli_runner: CliRunner, mock_orchestrator: MagicMock
    ) -> None:
        """Test exit code 0 when scraping succeeds with no failures."""
        # Act
        result = cli_runner.invoke(scrape)

        # Assert
        assert result.exit_code == 0

    def test_exit_code_2_on_high_failure_rate(
        self, cli_runner: CliRunner, mock_orchestrator: MagicMock
    ) -> None:
        """Test exit code 2 when failure rate exceeds 5%."""
        # Arrange
        mock_instance = mock_orchestrator.return_value
        mock_instance.scrape_all.return_value = {
            "unique_parts": 5,
            "total_applications": 100,
            "applications_processed": 90,
            "applications_skipped_unchanged": 0,
            "parts_scraped": 10,
            "new_parts": 5,
            "changed_parts": 0,
            "vehicles_tracked": 20,
            "make_filter": None,
            "year_filter": None,
            "details_fetched": True,
            "details_fetched_count": 5,
            "resumed": False,
            "applications_failed": 10,
            "details_failed": 0,
            "failure_summary": {
                "total_failures": 10,
                "by_phase": {"application": 10},
                "retryable": 8,
                "permanent": 2,
            },
        }

        # Act
        result = cli_runner.invoke(scrape)

        # Assert
        assert result.exit_code == 2


# ============================================================================
# ScraperOrchestrator Tests
# ============================================================================


class TestScraperOrchestratorInit:
    """Test ScraperOrchestrator initialization."""

    def test_init_initializes_with_default_dependencies(self) -> None:
        """Test __init__ initializes with default dependencies."""
        # Arrange & Act
        orchestrator = ScraperOrchestrator()

        # Assert
        assert orchestrator.fetcher is not None
        assert orchestrator.ajax_parser is not None
        assert orchestrator.html_parser is not None
        assert orchestrator.exporter is not None

    def test_init_sets_default_output_dir(self) -> None:
        """Test __init__ sets default output directory."""
        # Arrange & Act
        orchestrator = ScraperOrchestrator()

        # Assert
        assert orchestrator.output_dir == Path("exports")

    def test_init_sets_custom_output_dir(self) -> None:
        """Test __init__ sets custom output directory."""
        # Arrange
        custom_dir = Path("custom_exports")

        # Act
        orchestrator = ScraperOrchestrator(output_dir=custom_dir)

        # Assert
        assert orchestrator.output_dir == custom_dir

    def test_init_sets_incremental_mode(self) -> None:
        """Test __init__ sets incremental mode."""
        # Arrange & Act
        orchestrator = ScraperOrchestrator(incremental=True)

        # Assert
        assert orchestrator.incremental is True

    def test_init_sets_delay_override(self) -> None:
        """Test __init__ sets delay override."""
        # Arrange
        delay_value = 2.5

        # Act
        orchestrator = ScraperOrchestrator(delay_override=delay_value)

        # Assert
        assert orchestrator.delay_override == delay_value

    def test_init_initializes_state_tracking(self) -> None:
        """Test __init__ initializes state tracking."""
        # Arrange & Act
        orchestrator = ScraperOrchestrator()

        # Assert
        assert orchestrator.unique_parts == {}
        assert orchestrator.vehicle_compat == {}
        assert orchestrator.parts_scraped == 0


class TestScraperOrchestratorContextManager:
    """Test ScraperOrchestrator context manager."""

    def test_enter_returns_self(self) -> None:
        """Test __enter__ returns self."""
        # Arrange
        orchestrator = ScraperOrchestrator()

        # Act
        result = orchestrator.__enter__()

        # Assert
        assert result is orchestrator

    def test_exit_calls_close(self, mocker: MockerFixture) -> None:
        """Test __exit__ calls close method."""
        # Arrange
        orchestrator = ScraperOrchestrator()
        mock_close = mocker.patch.object(orchestrator, "close")

        # Act
        orchestrator.__exit__(None, None, None)

        # Assert
        mock_close.assert_called_once()

    def test_context_manager_works_correctly(self) -> None:
        """Test context manager protocol works correctly."""
        # Arrange & Act
        with ScraperOrchestrator() as orchestrator:
            # Assert - inside context
            assert orchestrator is not None
            assert isinstance(orchestrator, ScraperOrchestrator)

        # No exception raised means cleanup happened successfully


class TestScraperOrchestratorScrapeAll:
    """Test ScraperOrchestrator scrape_all method."""

    def test_scrape_all_returns_statistics(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test scrape_all returns statistics dictionary."""
        # Arrange
        orchestrator = ScraperOrchestrator(
            output_dir=tmp_path / "exports", checkpoint_dir=tmp_path / "checkpoints"
        )
        # Mock _build_hierarchy to return empty list (no applications to process)
        mocker.patch.object(orchestrator, "_build_hierarchy", return_value=[])

        # Act
        stats = orchestrator.scrape_all()

        # Assert
        assert isinstance(stats, dict)
        assert "unique_parts" in stats
        assert "total_applications" in stats
        assert "parts_scraped" in stats

    def test_scrape_all_accepts_make_filter(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test scrape_all accepts make filter."""
        # Arrange
        orchestrator = ScraperOrchestrator(
            output_dir=tmp_path / "exports", checkpoint_dir=tmp_path / "checkpoints"
        )
        make_value = "Honda"
        # Mock _build_hierarchy to return empty list (no applications to process)
        mocker.patch.object(orchestrator, "_build_hierarchy", return_value=[])

        # Act
        stats = orchestrator.scrape_all(make_filter=make_value)

        # Assert
        assert stats["make_filter"] == make_value

    def test_scrape_all_accepts_year_filter(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test scrape_all accepts year filter."""
        # Arrange
        orchestrator = ScraperOrchestrator(
            output_dir=tmp_path / "exports", checkpoint_dir=tmp_path / "checkpoints"
        )
        year_value = 2025
        # Mock _build_hierarchy to return empty list (no applications to process)
        mocker.patch.object(orchestrator, "_build_hierarchy", return_value=[])

        # Act
        stats = orchestrator.scrape_all(year_filter=year_value)

        # Assert
        assert stats["year_filter"] == year_value

    def test_scrape_all_placeholder_documented(self) -> None:
        """Test scrape_all is documented as placeholder."""
        # Arrange & Act
        docstring = ScraperOrchestrator.scrape_all.__doc__

        # Assert
        assert docstring is not None
        assert "workflow" in docstring.lower() or "scraping" in docstring.lower()


class TestScraperOrchestratorStateTracking:
    """Test ScraperOrchestrator state tracking."""

    def test_unique_parts_dict_initialized_empty(self) -> None:
        """Test unique_parts dict is initialized empty."""
        # Arrange & Act
        orchestrator = ScraperOrchestrator()

        # Assert
        assert isinstance(orchestrator.unique_parts, dict)
        assert len(orchestrator.unique_parts) == 0

    def test_vehicle_compat_dict_initialized_empty(self) -> None:
        """Test vehicle_compat dict is initialized empty."""
        # Arrange & Act
        orchestrator = ScraperOrchestrator()

        # Assert
        assert isinstance(orchestrator.vehicle_compat, dict)
        assert len(orchestrator.vehicle_compat) == 0

    def test_parts_scraped_counter_initialized_zero(self) -> None:
        """Test parts_scraped counter is initialized to zero."""
        # Arrange & Act
        orchestrator = ScraperOrchestrator()

        # Assert
        assert orchestrator.parts_scraped == 0

    def test_get_stats_returns_current_state(self) -> None:
        """Test get_stats returns current state."""
        # Arrange
        orchestrator = ScraperOrchestrator()

        # Act
        stats = orchestrator.get_stats()

        # Assert
        assert stats["unique_parts"] == 0
        assert stats["parts_scraped"] == 0
        assert stats["vehicles_tracked"] == 0

    def test_get_stats_calculates_vehicles_tracked(self) -> None:
        """Test get_stats calculates vehicles_tracked correctly."""
        # Arrange
        orchestrator = ScraperOrchestrator()
        # Simulate some vehicle compatibility data
        mock_vehicle1 = MagicMock()
        mock_vehicle2 = MagicMock()
        orchestrator.vehicle_compat = {
            "SKU-001": [mock_vehicle1, mock_vehicle2],
            "SKU-002": [mock_vehicle1],
        }

        # Act
        stats = orchestrator.get_stats()

        # Assert
        assert stats["vehicles_tracked"] == 3  # 2 + 1


class TestScraperOrchestratorExport:
    """Test ScraperOrchestrator export functionality."""

    def test_export_data_returns_file_paths(self, mocker: MockerFixture) -> None:
        """Test export_data returns file paths dictionary."""
        # Arrange
        orchestrator = ScraperOrchestrator()
        mock_part = MagicMock()
        orchestrator.unique_parts = {"SKU-001": mock_part}

        # Mock exporter methods
        mock_export_parts = mocker.patch.object(
            orchestrator.exporter, "export_parts", return_value=Path("exports/parts.json")
        )

        # Act
        paths = orchestrator.export_data()

        # Assert
        assert isinstance(paths, dict)
        assert "parts" in paths
        mock_export_parts.assert_called_once()

    def test_export_data_uses_incremental_mode(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test export_data uses incremental mode when previous exports exist."""
        # Arrange — create previous export so incremental append is triggered
        (tmp_path / "parts.json").write_text('{"parts": []}')

        orchestrator = ScraperOrchestrator(incremental=True, output_dir=str(tmp_path))
        mock_part = MagicMock()
        orchestrator.unique_parts = {"SKU-001": mock_part}

        # Mock exporter methods
        mock_export_incremental = mocker.patch.object(
            orchestrator.exporter,
            "export_parts_incremental",
            return_value=tmp_path / "parts.json",
        )

        # Act
        orchestrator.export_data()

        # Assert
        mock_export_incremental.assert_called_once()
        call_kwargs = mock_export_incremental.call_args.kwargs
        assert call_kwargs["append"] is True

    def test_export_complete_delegates_to_exporter(self, mocker: MockerFixture) -> None:
        """Test export_complete delegates to exporter with correct arguments."""
        # Arrange
        orchestrator = ScraperOrchestrator()
        mock_part = MagicMock()
        mock_vehicle = MagicMock()
        orchestrator.unique_parts = {"CSF-001": mock_part}
        orchestrator.vehicle_compat = {"CSF-001": [mock_vehicle]}

        mock_export_complete = mocker.patch.object(
            orchestrator.exporter,
            "export_complete",
            return_value=Path("exports/parts_complete.json"),
        )

        # Act
        result = orchestrator.export_complete()

        # Assert
        assert result == Path("exports/parts_complete.json")
        mock_export_complete.assert_called_once_with([mock_part], {"CSF-001": [mock_vehicle]})


class TestScraperOrchestratorCleanup:
    """Test ScraperOrchestrator cleanup."""

    def test_close_calls_fetcher_close(self, mocker: MockerFixture) -> None:
        """Test close method calls fetcher.close()."""
        # Arrange
        orchestrator = ScraperOrchestrator()
        mock_fetcher_close = mocker.patch.object(orchestrator.fetcher, "close")
        mocker.patch.object(orchestrator.image_processor, "close")

        # Act
        orchestrator.close()

        # Assert
        mock_fetcher_close.assert_called_once()

    def test_close_calls_image_processor_close(self, mocker: MockerFixture) -> None:
        """Test close method calls image_processor.close() to persist manifest."""
        # Arrange
        orchestrator = ScraperOrchestrator()
        mocker.patch.object(orchestrator.fetcher, "close")
        mock_ip_close = mocker.patch.object(orchestrator.image_processor, "close")

        # Act
        orchestrator.close()

        # Assert
        mock_ip_close.assert_called_once()


# ============================================================================
# Remote WP Detection Tests
# ============================================================================


class TestIsRemoteWp:
    """Test _is_remote_wp helper."""

    def test_https_url_is_remote(self) -> None:
        """HTTPS URLs are detected as remote."""
        assert _is_remote_wp("https://example.com") is True

    def test_http_url_is_remote(self) -> None:
        """HTTP URLs are detected as remote."""
        assert _is_remote_wp("http://example.com") is True

    def test_local_path_is_not_remote(self) -> None:
        """Local paths are not detected as remote."""
        assert _is_remote_wp("/path/to/uploads") is False

    def test_none_is_not_remote(self) -> None:
        """None is not detected as remote."""
        assert _is_remote_wp(None) is False


# ============================================================================
# State Sync Integration Tests
# ============================================================================


class TestStateSyncIntegration:
    """Test state sync pull/push around scrape command."""

    def test_remote_mode_pulls_state_before_scrape(
        self, cli_runner: CliRunner, mock_orchestrator: MagicMock, mocker: MockerFixture
    ) -> None:
        """State is pulled from WP before scraping in remote mode."""
        # Arrange
        mock_state_syncer_cls = mocker.patch("src.cli.commands.scrape.StateSyncer")
        mock_state_instance = MagicMock()
        mock_state_syncer_cls.return_value = mock_state_instance

        # Act
        result = cli_runner.invoke(
            scrape,
            ["--wp-url", "https://example.com", "--wp-api-key", "test-key"],
        )

        # Assert
        assert result.exit_code == 0
        mock_state_syncer_cls.assert_called_once_with(
            wp_url="https://example.com", api_key="test-key"
        )
        assert mock_state_instance.pull.call_count == 3

    def test_remote_mode_pushes_state_after_scrape(
        self, cli_runner: CliRunner, mock_orchestrator: MagicMock, mocker: MockerFixture
    ) -> None:
        """State is pushed to WP after scraping in remote mode."""
        # Arrange
        mock_state_syncer_cls = mocker.patch("src.cli.commands.scrape.StateSyncer")
        mock_state_instance = MagicMock()
        mock_state_syncer_cls.return_value = mock_state_instance

        # Act
        result = cli_runner.invoke(
            scrape,
            ["--wp-url", "https://example.com", "--wp-api-key", "test-key"],
        )

        # Assert
        assert result.exit_code == 0
        assert mock_state_instance.push.call_count == 3
        mock_state_instance.close.assert_called_once()

    def test_local_mode_skips_state_sync(
        self, cli_runner: CliRunner, mock_orchestrator: MagicMock, mocker: MockerFixture
    ) -> None:
        """State sync is not performed in local mode."""
        # Arrange
        mock_state_syncer_cls = mocker.patch("src.cli.commands.scrape.StateSyncer")

        # Act
        result = cli_runner.invoke(scrape)

        # Assert
        assert result.exit_code == 0
        mock_state_syncer_cls.assert_not_called()


# ============================================================================
# Streaming Sync Integration Tests
# ============================================================================


class TestStreamingSyncIntegration:
    """Test streaming image sync integration in scrape command."""

    def test_sync_images_sets_syncer_on_orchestrator(
        self,
        cli_runner: CliRunner,
        mock_orchestrator: MagicMock,
        mocker: MockerFixture,
        tmp_path: Path,
    ) -> None:
        """--sync-images creates an image syncer and sets it on the orchestrator."""
        # Arrange
        mock_syncer = MagicMock()
        mock_syncer.cumulative_result = MagicMock(uploaded=3, skipped=0, failed=0)
        mock_create = mocker.patch(
            "src.cli.commands.scrape._create_image_syncer",
            return_value=mock_syncer,
        )

        wp_uploads = tmp_path / "uploads"
        wp_uploads.mkdir()

        # Act
        result = cli_runner.invoke(
            scrape,
            ["--sync-images", "--wp-url", str(wp_uploads)],
        )

        # Assert
        assert result.exit_code == 0
        mock_create.assert_called_once()
