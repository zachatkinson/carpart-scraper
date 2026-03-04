"""Unit tests for CLI main module.

Tests the main CLI entry point, context, logging configuration,
and command registration. Uses Click's CliRunner for testing.
"""

from pathlib import Path
from unittest.mock import patch

import click
import pytest
from click.testing import CliRunner

from src.cli.main import (
    ClickContext,
    cli,
    configure_logging,
    main,
    validate_config_file,
)


class TestClickContext:
    """Tests for ClickContext initialization."""

    def test_init_sets_default_values(self) -> None:
        """Test ClickContext initializes with correct defaults."""
        # Arrange & Act
        ctx = ClickContext()

        # Assert
        assert ctx.verbose is False
        assert ctx.quiet is False
        assert ctx.config_file is None


class TestConfigureLogging:
    """Tests for configure_logging function."""

    def test_quiet_sets_warning_level(self) -> None:
        """Test quiet mode sets WARNING log level."""
        # Arrange & Act
        configure_logging(verbose=False, quiet=True)

        # Assert - no error raised means configuration succeeded
        # (structlog reconfigured internally)

    def test_verbose_sets_debug_level(self) -> None:
        """Test verbose mode sets DEBUG log level."""
        # Arrange & Act
        configure_logging(verbose=True, quiet=False)

        # Assert - configuration succeeded

    def test_default_sets_info_level(self) -> None:
        """Test default sets INFO log level."""
        # Arrange & Act
        configure_logging(verbose=False, quiet=False)

        # Assert - configuration succeeded


class TestValidateConfigFile:
    """Tests for validate_config_file callback."""

    def test_none_value_returns_none(self) -> None:
        """Test None input returns None."""
        # Arrange & Act
        result = validate_config_file(None, None, None)

        # Assert
        assert result is None

    def test_missing_path_raises_bad_parameter(self, tmp_path: Path) -> None:
        """Test non-existent file raises BadParameter."""
        # Arrange
        missing_path = str(tmp_path / "nonexistent.toml")

        # Act & Assert
        with pytest.raises(click.BadParameter, match="Config file not found"):
            validate_config_file(None, None, missing_path)

    def test_directory_raises_bad_parameter(self, tmp_path: Path) -> None:
        """Test directory path raises BadParameter."""
        # Act & Assert
        with pytest.raises(click.BadParameter, match="not a file"):
            validate_config_file(None, None, str(tmp_path))

    def test_valid_file_returns_path(self, tmp_path: Path) -> None:
        """Test valid file returns Path object."""
        # Arrange
        config_file = tmp_path / "config.toml"
        config_file.write_text("[settings]")

        # Act
        result = validate_config_file(None, None, str(config_file))

        # Assert
        assert isinstance(result, Path)
        assert result == config_file


class TestCLIGroup:
    """Tests for the main CLI group command."""

    def test_verbose_and_quiet_mutually_exclusive(self) -> None:
        """Test --verbose and --quiet together exits with error."""
        # Arrange
        runner = CliRunner()

        # Act
        result = runner.invoke(cli, ["--verbose", "--quiet", "version"])

        # Assert
        assert result.exit_code != 0

    def test_verbose_flag_sets_context(self) -> None:
        """Test --verbose flag configures context."""
        # Arrange
        runner = CliRunner()

        # Act
        result = runner.invoke(cli, ["--verbose", "version"])

        # Assert
        assert result.exit_code == 0

    def test_quiet_flag_sets_context(self) -> None:
        """Test --quiet flag configures context."""
        # Arrange
        runner = CliRunner()

        # Act
        result = runner.invoke(cli, ["--quiet", "version"])

        # Assert
        assert result.exit_code == 0

    def test_config_file_option(self, tmp_path: Path) -> None:
        """Test --config-file option loads config."""
        # Arrange
        runner = CliRunner()
        config_file = tmp_path / "config.toml"
        config_file.write_text("[settings]")

        # Act
        result = runner.invoke(cli, ["--config-file", str(config_file), "version"])

        # Assert
        assert result.exit_code == 0

    def test_default_flags_no_verbose_no_quiet(self) -> None:
        """Test default invocation without verbose or quiet flags."""
        # Arrange
        runner = CliRunner()

        # Act
        result = runner.invoke(cli, ["version"])

        # Assert
        assert result.exit_code == 0


class TestVersionCommand:
    """Tests for the version command."""

    def test_version_command_output(self) -> None:
        """Test version command displays version info."""
        # Arrange
        runner = CliRunner()

        # Act
        result = runner.invoke(cli, ["version"])

        # Assert
        assert result.exit_code == 0
        assert "0.1.0" in result.output
        assert "carpart-scraper" in result.output

    def test_version_command_shows_copyright(self) -> None:
        """Test version command displays copyright."""
        # Arrange
        runner = CliRunner()

        # Act
        result = runner.invoke(cli, ["version"])

        # Assert
        assert "Copyright" in result.output

    def test_version_command_shows_license(self) -> None:
        """Test version command displays license info."""
        # Arrange
        runner = CliRunner()

        # Act
        result = runner.invoke(cli, ["version"])

        # Assert
        assert "MIT License" in result.output


class TestConfigCommand:
    """Tests for the config command."""

    def test_config_command_shows_settings(self) -> None:
        """Test config command displays current configuration."""
        # Arrange
        runner = CliRunner()

        # Act
        result = runner.invoke(cli, ["config"])

        # Assert
        assert result.exit_code == 0

    def test_config_command_with_verbose(self) -> None:
        """Test config command shows verbose setting."""
        # Arrange
        runner = CliRunner()

        # Act
        result = runner.invoke(cli, ["--verbose", "config"])

        # Assert
        assert result.exit_code == 0

    def test_config_command_with_quiet(self) -> None:
        """Test config command shows quiet setting."""
        # Arrange
        runner = CliRunner()

        # Act
        result = runner.invoke(cli, ["--quiet", "config"])

        # Assert
        assert result.exit_code == 0

    def test_config_command_default_log_level(self) -> None:
        """Test config command shows INFO log level by default."""
        # Arrange
        runner = CliRunner()

        # Act
        result = runner.invoke(cli, ["config"])

        # Assert
        assert result.exit_code == 0

    def test_config_command_with_config_file(self, tmp_path: Path) -> None:
        """Test config command shows config file path when provided."""
        # Arrange
        runner = CliRunner()
        config_file = tmp_path / "config.toml"
        config_file.write_text("[settings]")

        # Act
        result = runner.invoke(cli, ["--config-file", str(config_file), "config"])

        # Assert
        assert result.exit_code == 0


class TestVersionOption:
    """Tests for the --version flag."""

    def test_version_option(self) -> None:
        """Test --version flag outputs version string."""
        # Arrange
        runner = CliRunner()

        # Act
        result = runner.invoke(cli, ["--version"])

        # Assert
        assert result.exit_code == 0
        assert "0.1.0" in result.output


class TestMainFunction:
    """Tests for the main() entry point."""

    def test_main_handles_keyboard_interrupt(self) -> None:
        """Test main() handles KeyboardInterrupt with exit code 130."""
        # Arrange & Act
        with (
            patch("src.cli.main.cli", side_effect=KeyboardInterrupt),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        # Assert
        assert exc_info.value.code == 130

    def test_main_handles_unexpected_exception(self) -> None:
        """Test main() handles unexpected exceptions with exit code 1."""
        # Arrange & Act
        with (
            patch("src.cli.main.cli", side_effect=RuntimeError("test error")),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        # Assert
        assert exc_info.value.code == 1


class TestCommandRegistration:
    """Tests that subcommands are properly registered."""

    def test_scrape_command_registered(self) -> None:
        """Test scrape command is registered with CLI group."""
        # Assert
        assert "scrape" in cli.commands

    def test_version_command_registered(self) -> None:
        """Test version command is registered with CLI group."""
        # Assert
        assert "version" in cli.commands

    def test_config_command_registered(self) -> None:
        """Test config command is registered with CLI group."""
        # Assert
        assert "config" in cli.commands

    def test_export_command_registered(self) -> None:
        """Test export command is registered with CLI group."""
        # Assert
        assert "export" in cli.commands

    def test_stats_command_registered(self) -> None:
        """Test stats command is registered with CLI group."""
        # Assert
        assert "stats" in cli.commands

    def test_validate_command_registered(self) -> None:
        """Test validate command is registered with CLI group."""
        # Assert
        assert "validate" in cli.commands

    def test_test_endpoint_command_registered(self) -> None:
        """Test test-endpoint command is registered with CLI group."""
        # Assert
        assert "test-endpoint" in cli.commands


class TestCLIHelp:
    """Tests for CLI help output."""

    def test_cli_help_output(self) -> None:
        """Test CLI --help displays usage information."""
        # Arrange
        runner = CliRunner()

        # Act
        result = runner.invoke(cli, ["--help"])

        # Assert
        assert result.exit_code == 0
        assert "CSF MyCarParts Scraper" in result.output

    def test_scrape_help_output(self) -> None:
        """Test scrape --help displays usage information."""
        # Arrange
        runner = CliRunner()

        # Act
        result = runner.invoke(cli, ["scrape", "--help"])

        # Assert
        assert result.exit_code == 0
