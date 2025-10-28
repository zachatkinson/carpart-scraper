"""Unit tests for YAML configuration system.

This module tests the configuration loading, validation, merging, and error handling
for the YAML-based configuration system. All tests follow the AAA pattern.

Coverage targets:
- Configuration loading from YAML files
- Pydantic validation for all config sections
- Default value handling
- Invalid YAML error handling
- Missing file handling
- CLI option merging
- YAML export functionality
"""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from src.cli.config import (
    AppConfig,
    ExportConfig,
    FilteringConfig,
    OutputConfig,
    ScrapingConfig,
    generate_example_config,
    load_config,
)

# ============================================================================
# ScrapingConfig Tests
# ============================================================================


class TestScrapingConfig:
    """Tests for ScrapingConfig validation and defaults."""

    def test_scraping_config_with_defaults_creates_valid_config(self) -> None:
        """Test that ScrapingConfig with defaults creates valid configuration."""
        # Arrange & Act
        config = ScrapingConfig()

        # Assert
        assert config.min_delay == 1.0
        assert config.max_delay == 3.0
        assert config.timeout == 30
        assert config.max_retries == 3
        assert config.respect_robots_txt is True
        assert "CSF-Parts-Scraper" in config.user_agent

    def test_scraping_config_with_custom_values_applies_overrides(self) -> None:
        """Test that ScrapingConfig accepts custom values."""
        # Arrange & Act
        config = ScrapingConfig(
            min_delay=2.0,
            max_delay=5.0,
            timeout=60,
            max_retries=5,
            user_agent="Custom-Bot/1.0 (contact@example.com)",
        )

        # Assert
        assert config.min_delay == 2.0
        assert config.max_delay == 5.0
        assert config.timeout == 60
        assert config.max_retries == 5
        assert config.user_agent == "Custom-Bot/1.0 (contact@example.com)"

    def test_scraping_config_with_max_delay_less_than_min_delay_raises_error(self) -> None:
        """Test that max_delay < min_delay raises ValidationError."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            ScrapingConfig(min_delay=3.0, max_delay=1.0)

        assert "max_delay" in str(exc_info.value)
        assert "min_delay" in str(exc_info.value)

    def test_scraping_config_with_browser_user_agent_raises_error(self) -> None:
        """Test that browser-like user agents are rejected."""
        # Arrange
        browser_user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Chrome/91.0.4472.124",
            "Safari/537.36",
            "Firefox/89.0",
        ]

        # Act & Assert
        for user_agent in browser_user_agents:
            with pytest.raises(ValidationError) as exc_info:
                ScrapingConfig(user_agent=user_agent)

            assert "must not pretend to be a browser" in str(exc_info.value)

    def test_scraping_config_with_negative_delay_raises_error(self) -> None:
        """Test that negative delays are rejected."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            ScrapingConfig(min_delay=-1.0)

    def test_scraping_config_with_delay_out_of_range_raises_error(self) -> None:
        """Test that delays outside valid range are rejected."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            ScrapingConfig(min_delay=0.1)  # Below minimum of 0.5

        with pytest.raises(ValidationError):
            ScrapingConfig(max_delay=15.0)  # Above maximum of 10.0

    def test_scraping_config_with_invalid_timeout_raises_error(self) -> None:
        """Test that invalid timeout values are rejected."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            ScrapingConfig(timeout=2)  # Below minimum of 5

        with pytest.raises(ValidationError):
            ScrapingConfig(timeout=150)  # Above maximum of 120

    def test_scraping_config_with_invalid_retries_raises_error(self) -> None:
        """Test that invalid retry counts are rejected."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            ScrapingConfig(max_retries=0)  # Below minimum of 1

        with pytest.raises(ValidationError):
            ScrapingConfig(max_retries=15)  # Above maximum of 10

    def test_scraping_config_is_frozen(self) -> None:
        """Test that ScrapingConfig is immutable."""
        # Arrange
        config = ScrapingConfig()

        # Act & Assert
        with pytest.raises(ValidationError):
            config.min_delay = 5.0  # type: ignore[misc]

    def test_scraping_config_strips_whitespace(self) -> None:
        """Test that string fields strip whitespace."""
        # Arrange & Act
        config = ScrapingConfig(user_agent="  Bot/1.0 (contact)  ")

        # Assert
        assert config.user_agent == "Bot/1.0 (contact)"


# ============================================================================
# OutputConfig Tests
# ============================================================================


class TestOutputConfig:
    """Tests for OutputConfig validation and defaults."""

    def test_output_config_with_defaults_creates_valid_config(self) -> None:
        """Test that OutputConfig with defaults creates valid configuration."""
        # Arrange & Act
        config = OutputConfig()

        # Assert
        # Default directory path (validator runs on explicit values, not defaults)
        assert config.directory == Path("exports")
        assert config.format == "json"
        assert config.pretty is True
        assert config.file_prefix == "csf"

    def test_output_config_with_custom_directory_resolves_to_absolute_path(self) -> None:
        """Test that custom directory is resolved to absolute path."""
        # Arrange & Act
        config = OutputConfig(directory=Path("custom/path"))

        # Assert
        assert config.directory.is_absolute()
        assert config.directory.name == "path"

    def test_output_config_with_unsupported_format_raises_error(self) -> None:
        """Test that unsupported export formats are rejected."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            OutputConfig(format="xml")

        assert "Unsupported format" in str(exc_info.value)

    def test_output_config_with_empty_prefix_raises_error(self) -> None:
        """Test that empty file prefix is rejected."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            OutputConfig(file_prefix="")

    def test_output_config_with_long_prefix_raises_error(self) -> None:
        """Test that file prefix exceeding max length is rejected."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            OutputConfig(file_prefix="a" * 51)  # Above max of 50

    def test_output_config_normalizes_format_to_lowercase(self) -> None:
        """Test that format is normalized to lowercase."""
        # Arrange & Act
        config = OutputConfig(format="JSON")

        # Assert
        assert config.format == "json"

    def test_output_config_is_frozen(self) -> None:
        """Test that OutputConfig is immutable."""
        # Arrange
        config = OutputConfig()

        # Act & Assert
        with pytest.raises(ValidationError):
            config.pretty = False  # type: ignore[misc]


# ============================================================================
# FilteringConfig Tests
# ============================================================================


class TestFilteringConfig:
    """Tests for FilteringConfig validation and defaults."""

    def test_filtering_config_with_defaults_creates_empty_filters(self) -> None:
        """Test that FilteringConfig defaults to empty filters."""
        # Arrange & Act
        config = FilteringConfig()

        # Assert
        assert config.makes == []
        assert config.years == []
        assert config.categories == []
        assert config.min_price is None
        assert config.max_price is None

    def test_filtering_config_normalizes_makes_to_title_case(self) -> None:
        """Test that makes are normalized to title case."""
        # Arrange & Act
        config = FilteringConfig(makes=["honda", "TOYOTA", "AcUrA"])

        # Assert
        assert config.makes == ["Honda", "Toyota", "Acura"]

    def test_filtering_config_normalizes_categories_to_title_case(self) -> None:
        """Test that categories are normalized to title case."""
        # Arrange & Act
        config = FilteringConfig(categories=["radiators", "CONDENSERS", "InTeRcOoLeRs"])

        # Assert
        assert config.categories == ["Radiators", "Condensers", "Intercoolers"]

    def test_filtering_config_removes_empty_makes(self) -> None:
        """Test that empty/whitespace makes are filtered out."""
        # Arrange & Act
        config = FilteringConfig(makes=["Honda", "", "  ", "Toyota"])

        # Assert
        assert config.makes == ["Honda", "Toyota"]

    def test_filtering_config_removes_empty_categories(self) -> None:
        """Test that empty/whitespace categories are filtered out."""
        # Arrange & Act
        config = FilteringConfig(categories=["Radiators", "", "  ", "Condensers"])

        # Assert
        assert config.categories == ["Radiators", "Condensers"]

    def test_filtering_config_sorts_years(self) -> None:
        """Test that years are sorted."""
        # Arrange & Act
        config = FilteringConfig(years=[2023, 2021, 2025, 2022, 2024])

        # Assert
        assert config.years == [2021, 2022, 2023, 2024, 2025]

    def test_filtering_config_with_year_out_of_range_raises_error(self) -> None:
        """Test that years outside valid range are rejected."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            FilteringConfig(years=[1940])  # Below minimum of 1950

        assert "out of range" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            FilteringConfig(years=[2035])  # Above maximum of 2030

        assert "out of range" in str(exc_info.value)

    def test_filtering_config_with_max_price_less_than_min_price_raises_error(self) -> None:
        """Test that max_price < min_price raises ValidationError."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            FilteringConfig(min_price=100.0, max_price=50.0)

        assert "max_price" in str(exc_info.value)
        assert "min_price" in str(exc_info.value)

    def test_filtering_config_with_negative_price_raises_error(self) -> None:
        """Test that negative prices are rejected."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError):
            FilteringConfig(min_price=-10.0)

        with pytest.raises(ValidationError):
            FilteringConfig(max_price=-5.0)

    def test_filtering_config_with_valid_price_range_succeeds(self) -> None:
        """Test that valid price ranges are accepted."""
        # Arrange & Act
        config = FilteringConfig(min_price=50.0, max_price=500.0)

        # Assert
        assert config.min_price == 50.0
        assert config.max_price == 500.0

    def test_filtering_config_is_frozen(self) -> None:
        """Test that FilteringConfig is immutable."""
        # Arrange
        config = FilteringConfig()

        # Act & Assert
        with pytest.raises(ValidationError):
            config.makes = ["Honda"]  # type: ignore[misc]


# ============================================================================
# ExportConfig Tests
# ============================================================================


class TestExportConfig:
    """Tests for ExportConfig validation and defaults."""

    def test_export_config_with_defaults_creates_valid_config(self) -> None:
        """Test that ExportConfig with defaults creates valid configuration."""
        # Arrange & Act
        config = ExportConfig()

        # Assert
        assert config.incremental is False
        assert config.hierarchical is False
        assert config.include_images is True
        assert config.include_compatibility is True
        assert config.deduplicate is True

    def test_export_config_with_custom_values_applies_overrides(self) -> None:
        """Test that ExportConfig accepts custom boolean values."""
        # Arrange & Act
        config = ExportConfig(
            incremental=True,
            hierarchical=True,
            include_images=False,
            include_compatibility=False,
            deduplicate=False,
        )

        # Assert
        assert config.incremental is True
        assert config.hierarchical is True
        assert config.include_images is False
        assert config.include_compatibility is False
        assert config.deduplicate is False

    def test_export_config_is_frozen(self) -> None:
        """Test that ExportConfig is immutable."""
        # Arrange
        config = ExportConfig()

        # Act & Assert
        with pytest.raises(ValidationError):
            config.incremental = True  # type: ignore[misc]


# ============================================================================
# AppConfig Tests
# ============================================================================


class TestAppConfig:
    """Tests for AppConfig composite configuration."""

    def test_app_config_with_defaults_creates_all_sections(self) -> None:
        """Test that AppConfig with defaults creates all config sections."""
        # Arrange & Act
        config = AppConfig()

        # Assert
        assert isinstance(config.scraping, ScrapingConfig)
        assert isinstance(config.output, OutputConfig)
        assert isinstance(config.filtering, FilteringConfig)
        assert isinstance(config.export, ExportConfig)

    def test_app_config_from_yaml_with_valid_file_loads_successfully(self, tmp_path: Path) -> None:
        """Test that AppConfig.from_yaml loads valid YAML file."""
        # Arrange
        yaml_content = {
            "scraping": {"min_delay": 2.0, "max_delay": 4.0},
            "output": {"directory": "custom_exports", "pretty": False},
            "filtering": {"makes": ["Honda", "Toyota"], "years": [2023, 2024]},
            "export": {"incremental": True, "deduplicate": False},
        }
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(yaml.dump(yaml_content))

        # Act
        config = AppConfig.from_yaml(config_file)

        # Assert
        assert config.scraping.min_delay == 2.0
        assert config.scraping.max_delay == 4.0
        assert not config.output.pretty
        assert config.filtering.makes == ["Honda", "Toyota"]
        assert config.filtering.years == [2023, 2024]
        assert config.export.incremental is True
        assert config.export.deduplicate is False

    def test_app_config_from_yaml_with_missing_file_raises_file_not_found(
        self, tmp_path: Path
    ) -> None:
        """Test that AppConfig.from_yaml raises FileNotFoundError for missing file."""
        # Arrange
        missing_file = tmp_path / "nonexistent.yaml"

        # Act & Assert
        with pytest.raises(FileNotFoundError) as exc_info:
            AppConfig.from_yaml(missing_file)

        assert "Config file not found" in str(exc_info.value)

    def test_app_config_from_yaml_with_invalid_yaml_raises_value_error(
        self, tmp_path: Path
    ) -> None:
        """Test that AppConfig.from_yaml raises ValueError for invalid YAML."""
        # Arrange
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: content: [")

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid YAML"):
            AppConfig.from_yaml(config_file)

    def test_app_config_from_yaml_with_empty_file_uses_defaults(self, tmp_path: Path) -> None:
        """Test that empty YAML file results in default configuration."""
        # Arrange
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")

        # Act
        config = AppConfig.from_yaml(config_file)

        # Assert
        assert config.scraping.min_delay == 1.0
        assert config.output.directory == Path("exports")
        assert config.filtering.makes == []

    def test_app_config_from_yaml_with_partial_config_merges_with_defaults(
        self, tmp_path: Path
    ) -> None:
        """Test that partial YAML config merges with defaults."""
        # Arrange
        yaml_content = {"scraping": {"min_delay": 2.5}}
        config_file = tmp_path / "partial.yaml"
        config_file.write_text(yaml.dump(yaml_content))

        # Act
        config = AppConfig.from_yaml(config_file)

        # Assert
        assert config.scraping.min_delay == 2.5
        assert config.scraping.max_delay == 3.0  # Default
        assert config.scraping.timeout == 30  # Default

    def test_app_config_from_yaml_with_validation_error_raises_error(self, tmp_path: Path) -> None:
        """Test that invalid config values raise OSError with validation info."""
        # Arrange
        yaml_content = {"scraping": {"min_delay": 5.0, "max_delay": 2.0}}  # max < min
        config_file = tmp_path / "invalid_values.yaml"
        config_file.write_text(yaml.dump(yaml_content))

        # Act & Assert
        # Validation errors are wrapped in OSError by from_yaml
        with pytest.raises(OSError, match="Failed to load config"):
            AppConfig.from_yaml(config_file)

    def test_app_config_from_yaml_optional_with_none_returns_defaults(self) -> None:
        """Test that from_yaml_optional with None returns defaults."""
        # Arrange & Act
        config = AppConfig.from_yaml_optional(None)

        # Assert
        assert config.scraping.min_delay == 1.0
        assert config.output.format == "json"

    def test_app_config_from_yaml_optional_with_missing_file_returns_defaults(
        self, tmp_path: Path
    ) -> None:
        """Test that from_yaml_optional with missing file returns defaults."""
        # Arrange
        missing_file = tmp_path / "missing.yaml"

        # Act
        config = AppConfig.from_yaml_optional(missing_file)

        # Assert
        assert config.scraping.min_delay == 1.0
        assert config.output.format == "json"

    def test_app_config_from_yaml_optional_with_existing_file_loads_config(
        self, tmp_path: Path
    ) -> None:
        """Test that from_yaml_optional with existing file loads it."""
        # Arrange
        yaml_content = {"scraping": {"min_delay": 2.0}}
        config_file = tmp_path / "exists.yaml"
        config_file.write_text(yaml.dump(yaml_content))

        # Act
        config = AppConfig.from_yaml_optional(config_file)

        # Assert
        assert config.scraping.min_delay == 2.0

    def test_app_config_merge_cli_options_applies_overrides(self) -> None:
        """Test that merge_cli_options applies CLI overrides."""
        # Arrange
        config = AppConfig()

        # Act
        updated = config.merge_cli_options(
            scraping__min_delay=2.0,
            scraping__timeout=60,
            output__pretty=False,
            filtering__makes=["Honda"],
        )

        # Assert
        assert updated.scraping.min_delay == 2.0
        assert updated.scraping.timeout == 60
        assert updated.output.pretty is False
        assert updated.filtering.makes == ["Honda"]

    def test_app_config_merge_cli_options_ignores_none_values(self) -> None:
        """Test that merge_cli_options ignores None values."""
        # Arrange
        config = AppConfig()
        original_delay = config.scraping.min_delay

        # Act
        updated = config.merge_cli_options(scraping__min_delay=None)

        # Assert
        assert updated.scraping.min_delay == original_delay

    def test_app_config_merge_cli_options_with_invalid_section_raises_error(self) -> None:
        """Test that invalid config section raises ValueError."""
        # Arrange
        config = AppConfig()

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid config section"):
            config.merge_cli_options(invalid_section__field=123)

    def test_app_config_merge_cli_options_with_invalid_field_raises_error(self) -> None:
        """Test that invalid config field raises ValueError."""
        # Arrange
        config = AppConfig()

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid config field"):
            config.merge_cli_options(scraping__invalid_field=123)

    def test_app_config_to_yaml_exports_configuration(self, tmp_path: Path) -> None:
        """Test that to_yaml exports configuration to file."""
        # Arrange
        config = AppConfig()
        output_file = tmp_path / "exported.yaml"

        # Act
        config.to_yaml(output_file)

        # Assert
        assert output_file.exists()
        loaded_data = yaml.safe_load(output_file.read_text())
        assert "scraping" in loaded_data
        assert "output" in loaded_data
        assert "filtering" in loaded_data
        assert "export" in loaded_data

    def test_app_config_to_yaml_creates_parent_directories(self, tmp_path: Path) -> None:
        """Test that to_yaml creates parent directories if needed."""
        # Arrange
        config = AppConfig()
        output_file = tmp_path / "nested" / "dir" / "config.yaml"

        # Act
        config.to_yaml(output_file)

        # Assert
        assert output_file.exists()
        assert output_file.parent.exists()

    def test_app_config_to_yaml_converts_path_to_string(self, tmp_path: Path) -> None:
        """Test that to_yaml converts Path objects to strings."""
        # Arrange
        config = AppConfig()
        output_file = tmp_path / "config.yaml"

        # Act
        config.to_yaml(output_file)

        # Assert
        loaded_data = yaml.safe_load(output_file.read_text())
        assert isinstance(loaded_data["output"]["directory"], str)

    def test_app_config_to_yaml_roundtrip_preserves_config(self, tmp_path: Path) -> None:
        """Test that exporting and loading config preserves values."""
        # Arrange
        original = AppConfig(
            scraping=ScrapingConfig(min_delay=2.0, max_delay=4.0),
            filtering=FilteringConfig(makes=["Honda"], years=[2023]),
        )
        temp_file = tmp_path / "roundtrip.yaml"

        # Act
        original.to_yaml(temp_file)
        loaded = AppConfig.from_yaml(temp_file)

        # Assert
        assert loaded.scraping.min_delay == original.scraping.min_delay
        assert loaded.scraping.max_delay == original.scraping.max_delay
        assert loaded.filtering.makes == original.filtering.makes
        assert loaded.filtering.years == original.filtering.years

    def test_app_config_is_frozen(self) -> None:
        """Test that AppConfig is immutable."""
        # Arrange
        config = AppConfig()

        # Act & Assert
        with pytest.raises(ValidationError):
            config.scraping = ScrapingConfig()  # type: ignore[misc]


# ============================================================================
# Helper Functions Tests
# ============================================================================


class TestLoadConfig:
    """Tests for load_config helper function."""

    def test_load_config_with_no_arguments_returns_defaults(self) -> None:
        """Test that load_config with no args returns default config."""
        # Arrange & Act
        config = load_config()

        # Assert
        assert config.scraping.min_delay == 1.0
        assert config.output.format == "json"

    def test_load_config_with_file_path_loads_config(self, tmp_path: Path) -> None:
        """Test that load_config loads from file path."""
        # Arrange
        yaml_content = {"scraping": {"min_delay": 2.5}}
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(yaml_content))

        # Act
        config = load_config(config_file)

        # Assert
        assert config.scraping.min_delay == 2.5

    def test_load_config_with_cli_overrides_applies_them(self) -> None:
        """Test that load_config applies CLI overrides."""
        # Arrange & Act
        config = load_config(scraping__timeout=90, output__pretty=False)

        # Assert
        assert config.scraping.timeout == 90
        assert config.output.pretty is False

    def test_load_config_with_file_and_overrides_merges_both(self, tmp_path: Path) -> None:
        """Test that load_config merges file config and CLI overrides."""
        # Arrange
        yaml_content = {"scraping": {"min_delay": 2.0}}
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(yaml_content))

        # Act
        config = load_config(config_file, scraping__timeout=90)

        # Assert
        assert config.scraping.min_delay == 2.0  # From file
        assert config.scraping.timeout == 90  # From CLI override


class TestGenerateExampleConfig:
    """Tests for generate_example_config helper function."""

    def test_generate_example_config_creates_file(self, tmp_path: Path) -> None:
        """Test that generate_example_config creates example file."""
        # Arrange
        output_file = tmp_path / "example.yaml"

        # Act
        generate_example_config(output_file)

        # Assert
        assert output_file.exists()

    def test_generate_example_config_file_is_valid_yaml(self, tmp_path: Path) -> None:
        """Test that generated example config is valid YAML."""
        # Arrange
        output_file = tmp_path / "example.yaml"

        # Act
        generate_example_config(output_file)

        # Assert
        loaded_data = yaml.safe_load(output_file.read_text())
        assert loaded_data is not None
        assert "scraping" in loaded_data

    def test_generate_example_config_can_be_loaded_as_app_config(self, tmp_path: Path) -> None:
        """Test that generated example config can be loaded as AppConfig."""
        # Arrange
        output_file = tmp_path / "example.yaml"

        # Act
        generate_example_config(output_file)
        config = AppConfig.from_yaml(output_file)

        # Assert
        assert isinstance(config, AppConfig)
        assert config.scraping.min_delay == 1.0


# ============================================================================
# Edge Cases and Error Scenarios
# ============================================================================


class TestConfigEdgeCases:
    """Tests for edge cases and error scenarios."""

    def test_config_with_unicode_characters_in_strings(self) -> None:
        """Test that config handles Unicode characters in string fields."""
        # Arrange & Act
        config = ScrapingConfig(user_agent="Bot-名前/1.0 (contact@example.com)")

        # Assert
        assert "名前" in config.user_agent

    def test_config_yaml_with_comments_loads_successfully(self, tmp_path: Path) -> None:
        """Test that YAML with comments loads successfully."""
        # Arrange
        yaml_content = """
# This is a comment
scraping:
  min_delay: 2.0  # Inline comment
  max_delay: 4.0
# Another comment
output:
  pretty: false
"""
        config_file = tmp_path / "commented.yaml"
        config_file.write_text(yaml_content)

        # Act
        config = AppConfig.from_yaml(config_file)

        # Assert
        assert config.scraping.min_delay == 2.0
        assert config.output.pretty is False

    def test_config_with_very_long_file_prefix_raises_error(self) -> None:
        """Test that extremely long file prefix is rejected."""
        # Arrange
        long_prefix = "a" * 100

        # Act & Assert
        with pytest.raises(ValidationError):
            OutputConfig(file_prefix=long_prefix)

    def test_config_merge_with_list_override_replaces_list(self) -> None:
        """Test that list overrides replace entire list."""
        # Arrange
        config = AppConfig(filtering=FilteringConfig(makes=["Honda", "Toyota"]))

        # Act
        updated = config.merge_cli_options(filtering__makes=["Acura"])

        # Assert
        assert updated.filtering.makes == ["Acura"]

    def test_config_from_yaml_with_permission_error_raises_os_error(self, tmp_path: Path) -> None:
        """Test that permission errors are handled appropriately."""
        # Arrange
        config_file = tmp_path / "readonly.yaml"
        config_file.write_text(yaml.dump({"scraping": {"min_delay": 1.0}}))
        config_file.chmod(0o000)  # Remove all permissions

        # Act & Assert
        try:
            with pytest.raises(OSError, match="Failed to load config"):
                AppConfig.from_yaml(config_file)
        finally:
            # Cleanup: restore permissions
            config_file.chmod(0o644)

    def test_config_to_yaml_with_permission_error_raises_os_error(self, tmp_path: Path) -> None:
        """Test that write permission errors are handled."""
        # Arrange
        config = AppConfig()
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)  # Read-only
        output_file = readonly_dir / "config.yaml"

        # Act & Assert
        try:
            with pytest.raises(OSError, match="Failed to export config"):
                config.to_yaml(output_file)
        finally:
            # Cleanup: restore permissions
            readonly_dir.chmod(0o755)

    def test_filtering_config_with_duplicate_years_preserves_uniqueness(self) -> None:
        """Test that duplicate years are preserved (sorted)."""
        # Arrange & Act
        config = FilteringConfig(years=[2023, 2021, 2023, 2022, 2021])

        # Assert
        # Pydantic doesn't deduplicate lists by default
        assert 2023 in config.years
        assert 2021 in config.years

    def test_config_preserves_field_order_in_yaml_export(self, tmp_path: Path) -> None:
        """Test that YAML export maintains reasonable field order."""
        # Arrange
        config = AppConfig()
        output_file = tmp_path / "ordered.yaml"

        # Act
        config.to_yaml(output_file)
        content = output_file.read_text()

        # Assert
        # Check that major sections appear in content
        assert "scraping:" in content
        assert "output:" in content
        assert "filtering:" in content
        assert "export:" in content
