"""Unit tests for scrape command.

This module contains comprehensive tests for the CLI scrape command and
ScraperOrchestrator, following AAA (Arrange-Act-Assert) testing pattern.
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest
from click.testing import CliRunner
from pytest_mock import MockerFixture

from src.cli.commands.scrape import scrape
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
def mock_subprocess(mocker: MockerFixture) -> Mock:
    """Provide mocked subprocess.run for scrape command delegation.

    Args:
        mocker: pytest-mock fixture

    Returns:
        Mock subprocess.run
    """
    mock_run = mocker.patch("src.cli.commands.scrape.subprocess.run")
    mock_result = Mock()
    mock_result.returncode = 0
    mock_run.return_value = mock_result
    return mock_run


# ============================================================================
# Click Command Tests
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

    def test_scrape_has_images_only_option(self) -> None:
        """Test scrape command has --images-only option."""
        # Arrange
        param_names = [param.name for param in scrape.params]

        # Act & Assert
        assert "images_only" in param_names


class TestScrapeCommandOptions:
    """Test scrape command option handling."""

    def test_make_option_passes_to_subprocess(
        self, cli_runner: CliRunner, mock_subprocess: Mock
    ) -> None:
        """Test --make option is forwarded to run_scrape.py subprocess."""
        # Arrange
        make_value = "Honda"

        # Act
        result = cli_runner.invoke(scrape, ["--make", make_value])

        # Assert
        assert result.exit_code == 0
        mock_subprocess.assert_called_once()
        cmd = mock_subprocess.call_args[0][0]
        assert "--make" in cmd
        assert make_value in cmd

    def test_year_option_passes_to_subprocess(
        self, cli_runner: CliRunner, mock_subprocess: Mock
    ) -> None:
        """Test --year option is forwarded to run_scrape.py subprocess."""
        # Arrange
        year_value = "2025"

        # Act
        result = cli_runner.invoke(scrape, ["--year", year_value])

        # Assert
        assert result.exit_code == 0
        mock_subprocess.assert_called_once()
        cmd = mock_subprocess.call_args[0][0]
        assert "--year" in cmd
        assert year_value in cmd

    def test_output_dir_passes_to_subprocess(
        self, cli_runner: CliRunner, mock_subprocess: Mock, tmp_path: Path
    ) -> None:
        """Test --output-dir is forwarded to run_scrape.py subprocess."""
        # Arrange
        output_dir = tmp_path / "custom_exports"

        # Act
        result = cli_runner.invoke(scrape, ["--output-dir", str(output_dir)])

        # Assert
        assert result.exit_code == 0
        mock_subprocess.assert_called_once()
        cmd = mock_subprocess.call_args[0][0]
        assert "--output-dir" in cmd
        assert str(output_dir) in cmd

    def test_catalog_only_passes_flag(self, cli_runner: CliRunner, mock_subprocess: Mock) -> None:
        """Test --catalog-only flag is forwarded."""
        # Act
        result = cli_runner.invoke(scrape, ["--catalog-only"])

        # Assert
        assert result.exit_code == 0
        cmd = mock_subprocess.call_args[0][0]
        assert "--catalog" in cmd

    def test_images_only_passes_flag(self, cli_runner: CliRunner, mock_subprocess: Mock) -> None:
        """Test --images-only flag is forwarded."""
        # Act
        result = cli_runner.invoke(scrape, ["--images-only"])

        # Assert
        assert result.exit_code == 0
        cmd = mock_subprocess.call_args[0][0]
        assert "--images" in cmd

    def test_default_runs_both_phases(self, cli_runner: CliRunner, mock_subprocess: Mock) -> None:
        """Test default invocation runs both catalog and images phases."""
        # Act
        result = cli_runner.invoke(scrape)

        # Assert
        assert result.exit_code == 0
        cmd = mock_subprocess.call_args[0][0]
        assert "--catalog" in cmd
        assert "--images" in cmd


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

    def test_catalog_only_and_images_only_mutually_exclusive(
        self, cli_runner: CliRunner, mock_subprocess: Mock
    ) -> None:
        """Test --catalog-only and --images-only are mutually exclusive."""
        # Act
        result = cli_runner.invoke(scrape, ["--catalog-only", "--images-only"])

        # Assert
        assert result.exit_code == 1
        mock_subprocess.assert_not_called()


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
        assert "--images-only" in result.output


class TestScrapeCommandWorkflow:
    """Test scrape command full workflow."""

    def test_scrape_delegates_to_run_scrape(
        self, cli_runner: CliRunner, mock_subprocess: Mock
    ) -> None:
        """Test scrape command delegates to run_scrape.py."""
        # Act
        result = cli_runner.invoke(scrape)

        # Assert
        assert result.exit_code == 0
        mock_subprocess.assert_called_once()
        cmd = mock_subprocess.call_args[0][0]
        assert "run_scrape.py" in cmd

    def test_scrape_with_all_options(self, cli_runner: CliRunner, mock_subprocess: Mock) -> None:
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
            ],
        )

        # Assert
        assert result.exit_code == 0
        mock_subprocess.assert_called_once()
        cmd = mock_subprocess.call_args[0][0]
        assert "--make" in cmd
        assert make_value in cmd
        assert "--year" in cmd
        assert year_value in cmd
        assert "--output-dir" in cmd
        assert output_dir_value in cmd


class TestScrapeCommandErrorHandling:
    """Test scrape command error handling."""

    def test_scrape_handles_keyboard_interrupt(
        self, cli_runner: CliRunner, mock_subprocess: Mock
    ) -> None:
        """Test scrape command handles KeyboardInterrupt gracefully."""
        # Arrange
        mock_subprocess.side_effect = KeyboardInterrupt()

        # Act
        result = cli_runner.invoke(scrape)

        # Assert
        assert result.exit_code == 1
        assert "interrupted" in result.output.lower()

    def test_scrape_handles_subprocess_failure(
        self, cli_runner: CliRunner, mock_subprocess: Mock
    ) -> None:
        """Test scrape command handles subprocess failure."""
        # Arrange
        mock_subprocess.side_effect = subprocess.CalledProcessError(2, "run_scrape.py")

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

    def test_scrape_all_returns_statistics(self, mocker: MockerFixture) -> None:
        """Test scrape_all returns statistics dictionary."""
        # Arrange
        orchestrator = ScraperOrchestrator()
        # Mock _build_hierarchy to return empty list (no applications to process)
        mocker.patch.object(orchestrator, "_build_hierarchy", return_value=[])

        # Act
        stats = orchestrator.scrape_all()

        # Assert
        assert isinstance(stats, dict)
        assert "unique_parts" in stats
        assert "total_applications" in stats
        assert "parts_scraped" in stats

    def test_scrape_all_accepts_make_filter(self, mocker: MockerFixture) -> None:
        """Test scrape_all accepts make filter."""
        # Arrange
        orchestrator = ScraperOrchestrator()
        make_value = "Honda"
        # Mock _build_hierarchy to return empty list (no applications to process)
        mocker.patch.object(orchestrator, "_build_hierarchy", return_value=[])

        # Act
        stats = orchestrator.scrape_all(make_filter=make_value)

        # Assert
        assert stats["make_filter"] == make_value

    def test_scrape_all_accepts_year_filter(self, mocker: MockerFixture) -> None:
        """Test scrape_all accepts year filter."""
        # Arrange
        orchestrator = ScraperOrchestrator()
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

    def test_export_data_uses_incremental_mode(self, mocker: MockerFixture) -> None:
        """Test export_data uses incremental mode when enabled."""
        # Arrange
        orchestrator = ScraperOrchestrator(incremental=True)
        mock_part = MagicMock()
        orchestrator.unique_parts = {"SKU-001": mock_part}

        # Mock exporter methods
        mock_export_incremental = mocker.patch.object(
            orchestrator.exporter,
            "export_parts_incremental",
            return_value=Path("exports/parts.json"),
        )

        # Act
        orchestrator.export_data()

        # Assert
        mock_export_incremental.assert_called_once()
        call_kwargs = mock_export_incremental.call_args.kwargs
        assert call_kwargs["append"] is True


class TestScraperOrchestratorCleanup:
    """Test ScraperOrchestrator cleanup."""

    def test_close_calls_fetcher_close(self, mocker: MockerFixture) -> None:
        """Test close method calls fetcher.close()."""
        # Arrange
        orchestrator = ScraperOrchestrator()
        mock_fetcher_close = mocker.patch.object(orchestrator.fetcher, "close")

        # Act
        orchestrator.close()

        # Assert
        mock_fetcher_close.assert_called_once()
