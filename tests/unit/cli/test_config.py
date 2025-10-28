"""Unit tests for config module.

Tests all configuration classes with comprehensive validation coverage.
Follows AAA (Arrange-Act-Assert) pattern for clarity.

Design:
- DRY: Uses fixtures and helpers to avoid duplication
- SOLID: Each test has single responsibility
- Type-safe: Full type hints with mypy strict mode
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from src.cli.config import (
    AppConfig,
    ExportConfig,
    FilteringConfig,
    OutputConfig,
    ScrapingConfig,
    load_config,
)


class TestScrapingConfig:
    """Tests for ScrapingConfig validation."""

    def test_default_values_are_valid(self) -> None:
        """Test default config values are valid."""
        # Arrange & Act
        config = ScrapingConfig()

        # Assert
        assert config.min_delay == 1.0
        assert config.max_delay == 3.0
        assert config.timeout == 30
        assert config.max_retries == 3
        assert config.respect_robots_txt is True

    def test_min_delay_below_minimum_raises_error(self) -> None:
        """Test min_delay below 0.5 raises validation error."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            ScrapingConfig(min_delay=0.3)

        # Assert
        assert "min_delay" in str(exc_info.value)
        assert "greater than or equal to 0.5" in str(exc_info.value)

    def test_min_delay_above_maximum_raises_error(self) -> None:
        """Test min_delay above 10.0 raises validation error."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            ScrapingConfig(min_delay=15.0)

        # Assert
        assert "min_delay" in str(exc_info.value)
        assert "less than or equal to 10" in str(exc_info.value)

    def test_min_delay_at_lower_bound_is_valid(self) -> None:
        """Test min_delay at lower bound (0.5) is valid."""
        # Arrange & Act
        config = ScrapingConfig(min_delay=0.5)

        # Assert
        assert config.min_delay == 0.5

    def test_min_delay_at_upper_bound_is_valid(self) -> None:
        """Test min_delay at upper bound (10.0) is valid."""
        # Arrange & Act
        config = ScrapingConfig(min_delay=10.0)

        # Assert
        assert config.min_delay == 10.0

    def test_max_delay_below_minimum_raises_error(self) -> None:
        """Test max_delay below 0.5 raises validation error."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            ScrapingConfig(max_delay=0.3)

        # Assert
        assert "max_delay" in str(exc_info.value)

    def test_max_delay_above_maximum_raises_error(self) -> None:
        """Test max_delay above 10.0 raises validation error."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            ScrapingConfig(max_delay=15.0)

        # Assert
        assert "max_delay" in str(exc_info.value)

    def test_max_delay_less_than_min_delay_raises_error(self) -> None:
        """Test max_delay < min_delay raises validation error."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            ScrapingConfig(min_delay=5.0, max_delay=3.0)

        # Assert
        assert "max_delay" in str(exc_info.value)
        assert "must be >=" in str(exc_info.value)

    def test_max_delay_equal_to_min_delay_is_valid(self) -> None:
        """Test max_delay == min_delay is valid."""
        # Arrange & Act
        config = ScrapingConfig(min_delay=2.0, max_delay=2.0)

        # Assert
        assert config.min_delay == 2.0
        assert config.max_delay == 2.0

    def test_max_delay_greater_than_min_delay_is_valid(self) -> None:
        """Test max_delay > min_delay is valid."""
        # Arrange & Act
        config = ScrapingConfig(min_delay=1.0, max_delay=5.0)

        # Assert
        assert config.min_delay == 1.0
        assert config.max_delay == 5.0

    def test_user_agent_with_mozilla_pattern_raises_error(self) -> None:
        """Test user agent with Mozilla pattern raises error."""
        # Arrange
        browser_like_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            ScrapingConfig(user_agent=browser_like_ua)

        # Assert
        assert "user_agent" in str(exc_info.value)
        assert "must not pretend to be a browser" in str(exc_info.value)

    def test_user_agent_with_chrome_pattern_raises_error(self) -> None:
        """Test user agent with Chrome pattern raises error."""
        # Arrange
        browser_like_ua = "Custom Agent Chrome/120.0"

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            ScrapingConfig(user_agent=browser_like_ua)

        # Assert
        assert "must not pretend to be a browser" in str(exc_info.value)

    def test_user_agent_with_safari_pattern_raises_error(self) -> None:
        """Test user agent with Safari pattern raises error."""
        # Arrange
        browser_like_ua = "Something Safari/17.0 Agent"

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            ScrapingConfig(user_agent=browser_like_ua)

        # Assert
        assert "must not pretend to be a browser" in str(exc_info.value)

    def test_user_agent_with_firefox_pattern_raises_error(self) -> None:
        """Test user agent with Firefox pattern raises error."""
        # Arrange
        browser_like_ua = "Firefox/121.0 Custom Agent"

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            ScrapingConfig(user_agent=browser_like_ua)

        # Assert
        assert "must not pretend to be a browser" in str(exc_info.value)

    def test_user_agent_with_valid_bot_identifier_is_valid(self) -> None:
        """Test user agent with valid bot identifier is valid."""
        # Arrange
        bot_ua = "CSF-Parts-Scraper/1.0 (contact@example.com)"

        # Act
        config = ScrapingConfig(user_agent=bot_ua)

        # Assert
        assert config.user_agent == bot_ua

    def test_timeout_below_minimum_raises_error(self) -> None:
        """Test timeout below 5 raises validation error."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            ScrapingConfig(timeout=3)

        # Assert
        assert "timeout" in str(exc_info.value)

    def test_timeout_above_maximum_raises_error(self) -> None:
        """Test timeout above 120 raises validation error."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            ScrapingConfig(timeout=150)

        # Assert
        assert "timeout" in str(exc_info.value)

    def test_timeout_at_lower_bound_is_valid(self) -> None:
        """Test timeout at lower bound (5) is valid."""
        # Arrange & Act
        config = ScrapingConfig(timeout=5)

        # Assert
        assert config.timeout == 5

    def test_timeout_at_upper_bound_is_valid(self) -> None:
        """Test timeout at upper bound (120) is valid."""
        # Arrange & Act
        config = ScrapingConfig(timeout=120)

        # Assert
        assert config.timeout == 120

    def test_max_retries_below_minimum_raises_error(self) -> None:
        """Test max_retries below 1 raises validation error."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            ScrapingConfig(max_retries=0)

        # Assert
        assert "max_retries" in str(exc_info.value)

    def test_max_retries_above_maximum_raises_error(self) -> None:
        """Test max_retries above 10 raises validation error."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            ScrapingConfig(max_retries=15)

        # Assert
        assert "max_retries" in str(exc_info.value)

    def test_max_retries_at_lower_bound_is_valid(self) -> None:
        """Test max_retries at lower bound (1) is valid."""
        # Arrange & Act
        config = ScrapingConfig(max_retries=1)

        # Assert
        assert config.max_retries == 1

    def test_max_retries_at_upper_bound_is_valid(self) -> None:
        """Test max_retries at upper bound (10) is valid."""
        # Arrange & Act
        config = ScrapingConfig(max_retries=10)

        # Assert
        assert config.max_retries == 10


class TestOutputConfig:
    """Tests for OutputConfig validation."""

    def test_default_values_are_valid(self) -> None:
        """Test default config values are valid."""
        # Arrange & Act
        config = OutputConfig()

        # Assert
        # Note: Validators don't run on Field defaults, so directory remains relative
        assert config.directory == Path("exports")
        assert config.format == "json"
        assert config.pretty is True
        assert config.file_prefix == "csf"

    def test_directory_path_is_resolved_to_absolute(self) -> None:
        """Test directory path is converted to absolute path."""
        # Arrange
        relative_path = Path("relative/exports")

        # Act
        config = OutputConfig(directory=relative_path)

        # Assert
        assert config.directory.is_absolute()
        assert config.directory == relative_path.resolve()

    def test_format_is_converted_to_lowercase(self) -> None:
        """Test format is normalized to lowercase."""
        # Arrange & Act
        config = OutputConfig(format="JSON")

        # Assert
        assert config.format == "json"

    def test_unsupported_format_raises_error(self) -> None:
        """Test unsupported export format raises validation error."""
        # Arrange
        invalid_format = "xml"

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            OutputConfig(format=invalid_format)

        # Assert
        assert "format" in str(exc_info.value)
        assert "Unsupported format" in str(exc_info.value)

    def test_json_format_is_valid(self) -> None:
        """Test JSON format is valid."""
        # Arrange & Act
        config = OutputConfig(format="json")

        # Assert
        assert config.format == "json"

    def test_file_prefix_empty_raises_error(self) -> None:
        """Test empty file_prefix raises validation error."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            OutputConfig(file_prefix="")

        # Assert
        assert "file_prefix" in str(exc_info.value)

    def test_file_prefix_too_long_raises_error(self) -> None:
        """Test file_prefix exceeding max length raises error."""
        # Arrange
        long_prefix = "a" * 51

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            OutputConfig(file_prefix=long_prefix)

        # Assert
        assert "file_prefix" in str(exc_info.value)

    def test_file_prefix_at_max_length_is_valid(self) -> None:
        """Test file_prefix at max length (50) is valid."""
        # Arrange
        max_length_prefix = "a" * 50

        # Act
        config = OutputConfig(file_prefix=max_length_prefix)

        # Assert
        assert config.file_prefix == max_length_prefix
        assert len(config.file_prefix) == 50


class TestFilteringConfig:
    """Tests for FilteringConfig validation."""

    def test_default_values_are_valid(self) -> None:
        """Test default config values are valid."""
        # Arrange & Act
        config = FilteringConfig()

        # Assert
        assert config.makes == []
        assert config.years == []
        assert config.categories == []
        assert config.min_price is None
        assert config.max_price is None

    def test_makes_are_normalized_to_title_case(self) -> None:
        """Test make names are normalized to title case."""
        # Arrange
        makes_input = ["toyota", "HONDA", "FoRd"]

        # Act
        config = FilteringConfig(makes=makes_input)

        # Assert
        assert config.makes == ["Toyota", "Honda", "Ford"]

    def test_makes_with_whitespace_are_trimmed(self) -> None:
        """Test make names with whitespace are trimmed."""
        # Arrange
        makes_input = ["  toyota  ", "honda\n", "\tford"]

        # Act
        config = FilteringConfig(makes=makes_input)

        # Assert
        assert config.makes == ["Toyota", "Honda", "Ford"]

    def test_empty_makes_are_filtered_out(self) -> None:
        """Test empty make strings are removed."""
        # Arrange
        makes_input = ["toyota", "", "  ", "honda"]

        # Act
        config = FilteringConfig(makes=makes_input)

        # Assert
        assert config.makes == ["Toyota", "Honda"]

    def test_years_below_minimum_raises_error(self) -> None:
        """Test year below 1950 raises validation error."""
        # Arrange
        invalid_years = [1949, 2000]

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            FilteringConfig(years=invalid_years)

        # Assert
        assert "Year 1949 out of range" in str(exc_info.value)

    def test_years_above_maximum_raises_error(self) -> None:
        """Test year above 2030 raises validation error."""
        # Arrange
        invalid_years = [2000, 2031]

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            FilteringConfig(years=invalid_years)

        # Assert
        assert "Year 2031 out of range" in str(exc_info.value)

    def test_years_at_lower_bound_is_valid(self) -> None:
        """Test year at lower bound (1950) is valid."""
        # Arrange
        years_input = [1950, 2000]

        # Act
        config = FilteringConfig(years=years_input)

        # Assert
        assert 1950 in config.years

    def test_years_at_upper_bound_is_valid(self) -> None:
        """Test year at upper bound (2030) is valid."""
        # Arrange
        years_input = [2000, 2030]

        # Act
        config = FilteringConfig(years=years_input)

        # Assert
        assert 2030 in config.years

    def test_years_are_sorted(self) -> None:
        """Test years are automatically sorted in ascending order."""
        # Arrange
        unsorted_years = [2020, 2010, 2025, 2015]

        # Act
        config = FilteringConfig(years=unsorted_years)

        # Assert
        assert config.years == [2010, 2015, 2020, 2025]

    def test_categories_are_normalized_to_title_case(self) -> None:
        """Test category names are normalized to title case."""
        # Arrange
        categories_input = ["radiators", "CONDENSERS", "CoOlErS"]

        # Act
        config = FilteringConfig(categories=categories_input)

        # Assert
        assert config.categories == ["Radiators", "Condensers", "Coolers"]

    def test_categories_with_whitespace_are_trimmed(self) -> None:
        """Test category names with whitespace are trimmed."""
        # Arrange
        categories_input = ["  radiators  ", "condensers\n"]

        # Act
        config = FilteringConfig(categories=categories_input)

        # Assert
        assert config.categories == ["Radiators", "Condensers"]

    def test_min_price_negative_raises_error(self) -> None:
        """Test negative min_price raises validation error."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            FilteringConfig(min_price=-10.0)

        # Assert
        assert "min_price" in str(exc_info.value)

    def test_min_price_zero_is_valid(self) -> None:
        """Test min_price of zero is valid."""
        # Arrange & Act
        config = FilteringConfig(min_price=0.0)

        # Assert
        assert config.min_price == 0.0

    def test_max_price_negative_raises_error(self) -> None:
        """Test negative max_price raises validation error."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            FilteringConfig(max_price=-50.0)

        # Assert
        assert "max_price" in str(exc_info.value)

    def test_max_price_less_than_min_price_raises_error(self) -> None:
        """Test max_price < min_price raises validation error."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            FilteringConfig(min_price=100.0, max_price=50.0)

        # Assert
        assert "max_price" in str(exc_info.value)
        assert "must be >=" in str(exc_info.value)

    def test_max_price_equal_to_min_price_is_valid(self) -> None:
        """Test max_price == min_price is valid."""
        # Arrange & Act
        config = FilteringConfig(min_price=100.0, max_price=100.0)

        # Assert
        assert config.min_price == 100.0
        assert config.max_price == 100.0

    def test_max_price_greater_than_min_price_is_valid(self) -> None:
        """Test max_price > min_price is valid."""
        # Arrange & Act
        config = FilteringConfig(min_price=50.0, max_price=200.0)

        # Assert
        assert config.min_price == 50.0
        assert config.max_price == 200.0


class TestExportConfig:
    """Tests for ExportConfig validation."""

    def test_default_values_are_valid(self) -> None:
        """Test default config values are valid."""
        # Arrange & Act
        config = ExportConfig()

        # Assert
        assert config.incremental is False
        assert config.hierarchical is False
        assert config.include_images is True
        assert config.include_compatibility is True
        assert config.deduplicate is True

    def test_incremental_flag_can_be_enabled(self) -> None:
        """Test incremental flag can be set to True."""
        # Arrange & Act
        config = ExportConfig(incremental=True)

        # Assert
        assert config.incremental is True

    def test_hierarchical_flag_can_be_enabled(self) -> None:
        """Test hierarchical flag can be set to True."""
        # Arrange & Act
        config = ExportConfig(hierarchical=True)

        # Assert
        assert config.hierarchical is True

    def test_include_images_flag_can_be_disabled(self) -> None:
        """Test include_images flag can be set to False."""
        # Arrange & Act
        config = ExportConfig(include_images=False)

        # Assert
        assert config.include_images is False

    def test_include_compatibility_flag_can_be_disabled(self) -> None:
        """Test include_compatibility flag can be set to False."""
        # Arrange & Act
        config = ExportConfig(include_compatibility=False)

        # Assert
        assert config.include_compatibility is False

    def test_deduplicate_flag_can_be_disabled(self) -> None:
        """Test deduplicate flag can be set to False."""
        # Arrange & Act
        config = ExportConfig(deduplicate=False)

        # Assert
        assert config.deduplicate is False

    def test_all_flags_can_be_enabled_together(self) -> None:
        """Test all boolean flags can be True simultaneously."""
        # Arrange & Act
        config = ExportConfig(
            incremental=True,
            hierarchical=True,
            include_images=True,
            include_compatibility=True,
            deduplicate=True,
        )

        # Assert
        assert config.incremental is True
        assert config.hierarchical is True
        assert config.include_images is True
        assert config.include_compatibility is True
        assert config.deduplicate is True

    def test_all_flags_can_be_disabled_together(self) -> None:
        """Test all boolean flags can be False simultaneously."""
        # Arrange & Act
        config = ExportConfig(
            incremental=False,
            hierarchical=False,
            include_images=False,
            include_compatibility=False,
            deduplicate=False,
        )

        # Assert
        assert config.incremental is False
        assert config.hierarchical is False
        assert config.include_images is False
        assert config.include_compatibility is False
        assert config.deduplicate is False


class TestAppConfig:
    """Tests for AppConfig main configuration."""

    def test_default_values_create_valid_config(self) -> None:
        """Test default AppConfig is valid with all sections."""
        # Arrange & Act
        config = AppConfig()

        # Assert
        assert isinstance(config.scraping, ScrapingConfig)
        assert isinstance(config.output, OutputConfig)
        assert isinstance(config.filtering, FilteringConfig)
        assert isinstance(config.export, ExportConfig)

    def test_from_yaml_with_missing_file_raises_error(self, tmp_path: Path) -> None:
        """Test from_yaml with non-existent file raises FileNotFoundError."""
        # Arrange
        missing_file = tmp_path / "nonexistent.yaml"

        # Act & Assert
        with pytest.raises(FileNotFoundError) as exc_info:
            AppConfig.from_yaml(missing_file)

        # Assert
        assert "Config file not found" in str(exc_info.value)
        assert str(missing_file) in str(exc_info.value)

    def test_from_yaml_with_invalid_yaml_raises_error(self, tmp_path: Path) -> None:
        """Test from_yaml with invalid YAML raises ValueError."""
        # Arrange
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text("invalid: yaml: content:\n  - broken")

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid YAML") as exc_info:
            AppConfig.from_yaml(yaml_file)

        # Assert
        assert "Invalid YAML" in str(exc_info.value)

    def test_from_yaml_with_empty_file_uses_defaults(self, tmp_path: Path) -> None:
        """Test from_yaml with empty file returns default config."""
        # Arrange
        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("")

        # Act
        config = AppConfig.from_yaml(yaml_file)

        # Assert
        assert config.scraping.min_delay == 1.0
        assert config.output.format == "json"

    def test_from_yaml_loads_valid_config_file(self, tmp_path: Path) -> None:
        """Test from_yaml successfully loads valid YAML config."""
        # Arrange
        yaml_file = tmp_path / "config.yaml"
        yaml_content = """
scraping:
  min_delay: 2.0
  max_delay: 5.0
  timeout: 60
output:
  format: json
  file_prefix: test
filtering:
  makes: [toyota, honda]
  years: [2020, 2021]
export:
  incremental: true
"""
        yaml_file.write_text(yaml_content)

        # Act
        config = AppConfig.from_yaml(yaml_file)

        # Assert
        assert config.scraping.min_delay == 2.0
        assert config.scraping.max_delay == 5.0
        assert config.scraping.timeout == 60
        assert config.output.format == "json"
        assert config.output.file_prefix == "test"
        assert config.filtering.makes == ["Toyota", "Honda"]
        assert config.filtering.years == [2020, 2021]
        assert config.export.incremental is True

    def test_from_yaml_optional_with_none_returns_defaults(self) -> None:
        """Test from_yaml_optional with None returns default config."""
        # Arrange & Act
        config = AppConfig.from_yaml_optional(None)

        # Assert
        assert config.scraping.min_delay == 1.0
        assert config.output.format == "json"

    def test_from_yaml_optional_with_missing_file_returns_defaults(self, tmp_path: Path) -> None:
        """Test from_yaml_optional with missing file returns defaults."""
        # Arrange
        missing_file = tmp_path / "missing.yaml"

        # Act
        config = AppConfig.from_yaml_optional(missing_file)

        # Assert
        assert config.scraping.min_delay == 1.0
        assert config.output.format == "json"

    def test_from_yaml_optional_with_existing_file_loads_config(self, tmp_path: Path) -> None:
        """Test from_yaml_optional with existing file loads config."""
        # Arrange
        yaml_file = tmp_path / "config.yaml"
        yaml_content = """
scraping:
  min_delay: 3.0
"""
        yaml_file.write_text(yaml_content)

        # Act
        config = AppConfig.from_yaml_optional(yaml_file)

        # Assert
        assert config.scraping.min_delay == 3.0

    def test_to_yaml_creates_valid_yaml_file(self, tmp_path: Path) -> None:
        """Test to_yaml creates valid YAML file."""
        # Arrange
        config = AppConfig()
        yaml_file = tmp_path / "output.yaml"

        # Act
        config.to_yaml(yaml_file)

        # Assert
        assert yaml_file.exists()
        loaded_config = AppConfig.from_yaml(yaml_file)
        assert loaded_config.scraping.min_delay == config.scraping.min_delay

    def test_to_yaml_creates_parent_directories(self, tmp_path: Path) -> None:
        """Test to_yaml creates parent directories if needed."""
        # Arrange
        config = AppConfig()
        yaml_file = tmp_path / "nested" / "dir" / "config.yaml"

        # Act
        config.to_yaml(yaml_file)

        # Assert
        assert yaml_file.exists()
        assert yaml_file.parent.exists()

    def test_to_yaml_preserves_all_config_sections(self, tmp_path: Path) -> None:
        """Test to_yaml preserves all configuration sections."""
        # Arrange
        original_config = AppConfig()
        yaml_file = tmp_path / "config.yaml"

        # Act
        original_config.to_yaml(yaml_file)
        loaded_config = AppConfig.from_yaml(yaml_file)

        # Assert
        assert loaded_config.scraping.min_delay == original_config.scraping.min_delay
        assert loaded_config.output.format == original_config.output.format
        assert loaded_config.filtering.makes == original_config.filtering.makes
        assert loaded_config.export.incremental == original_config.export.incremental


class TestConfigMergeOverrides:
    """Tests for CLI override merging functionality."""

    def test_merge_cli_options_with_no_overrides_returns_unchanged(self) -> None:
        """Test merge_cli_options with no overrides returns same config."""
        # Arrange
        config = AppConfig()

        # Act
        merged = config.merge_cli_options()

        # Assert
        assert merged.scraping.min_delay == config.scraping.min_delay

    def test_merge_cli_options_with_none_values_ignored(self) -> None:
        """Test merge_cli_options ignores None values."""
        # Arrange
        config = AppConfig()
        original_delay = config.scraping.min_delay

        # Act
        merged = config.merge_cli_options(scraping__min_delay=None)

        # Assert
        assert merged.scraping.min_delay == original_delay

    def test_merge_cli_options_overrides_scraping_min_delay(self) -> None:
        """Test merge_cli_options correctly overrides scraping.min_delay."""
        # Arrange
        config = AppConfig()

        # Act
        # Use 2.5 which is less than default max_delay (3.0) to avoid validation error
        merged = config.merge_cli_options(scraping__min_delay=2.5)

        # Assert
        assert merged.scraping.min_delay == 2.5

    def test_merge_cli_options_overrides_scraping_timeout(self) -> None:
        """Test merge_cli_options correctly overrides scraping.timeout."""
        # Arrange
        config = AppConfig()

        # Act
        merged = config.merge_cli_options(scraping__timeout=60)

        # Assert
        assert merged.scraping.timeout == 60

    def test_merge_cli_options_overrides_output_format(self) -> None:
        """Test merge_cli_options correctly overrides output.format."""
        # Arrange
        config = AppConfig()

        # Act
        merged = config.merge_cli_options(output__format="json")

        # Assert
        assert merged.output.format == "json"

    def test_merge_cli_options_overrides_multiple_sections(self) -> None:
        """Test merge_cli_options can override multiple sections."""
        # Arrange
        config = AppConfig()

        # Act
        merged = config.merge_cli_options(
            scraping__min_delay=2.0,
            output__file_prefix="custom",
            export__incremental=True,
        )

        # Assert
        assert merged.scraping.min_delay == 2.0
        assert merged.output.file_prefix == "custom"
        assert merged.export.incremental is True

    def test_merge_cli_options_with_invalid_section_raises_error(self) -> None:
        """Test merge_cli_options with invalid section raises ValueError."""
        # Arrange
        config = AppConfig()

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid config section") as exc_info:
            config.merge_cli_options(invalid_section__field="value")

        # Assert
        assert "Invalid config section" in str(exc_info.value)

    def test_merge_cli_options_with_invalid_field_raises_error(self) -> None:
        """Test merge_cli_options with invalid field raises ValueError."""
        # Arrange
        config = AppConfig()

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid config field") as exc_info:
            config.merge_cli_options(scraping__invalid_field="value")

        # Assert
        assert "Invalid config field" in str(exc_info.value)

    def test_merge_cli_options_validates_overridden_values(self) -> None:
        """Test merge_cli_options validates override values."""
        # Arrange
        config = AppConfig()

        # Act & Assert - Should raise validation error for invalid delay
        with pytest.raises(ValidationError):
            config.merge_cli_options(scraping__min_delay=0.1)


class TestLoadConfig:
    """Tests for load_config convenience function."""

    def test_load_config_with_no_args_returns_defaults(self) -> None:
        """Test load_config with no arguments returns default config."""
        # Arrange & Act
        config = load_config()

        # Assert
        assert config.scraping.min_delay == 1.0
        assert config.output.format == "json"

    def test_load_config_with_missing_file_returns_defaults(self, tmp_path: Path) -> None:
        """Test load_config with missing file returns defaults."""
        # Arrange
        missing_file = tmp_path / "missing.yaml"

        # Act
        config = load_config(missing_file)

        # Assert
        assert config.scraping.min_delay == 1.0

    def test_load_config_loads_from_valid_file(self, tmp_path: Path) -> None:
        """Test load_config successfully loads from valid file."""
        # Arrange
        yaml_file = tmp_path / "config.yaml"
        yaml_content = """
scraping:
  min_delay: 4.0
"""
        yaml_file.write_text(yaml_content)

        # Act
        config = load_config(yaml_file)

        # Assert
        assert config.scraping.min_delay == 4.0

    def test_load_config_applies_cli_overrides(self, tmp_path: Path) -> None:
        """Test load_config applies CLI overrides to file config."""
        # Arrange
        yaml_file = tmp_path / "config.yaml"
        yaml_content = """
scraping:
  min_delay: 2.0
  timeout: 30
"""
        yaml_file.write_text(yaml_content)

        # Act
        config = load_config(yaml_file, scraping__timeout=60)

        # Assert
        assert config.scraping.min_delay == 2.0  # From file
        assert config.scraping.timeout == 60  # Overridden by CLI

    def test_load_config_cli_overrides_without_file(self) -> None:
        """Test load_config applies CLI overrides to defaults."""
        # Arrange & Act
        config = load_config(scraping__min_delay=3.0)

        # Assert
        assert config.scraping.min_delay == 3.0

    def test_load_config_with_multiple_overrides(self, tmp_path: Path) -> None:
        """Test load_config with multiple CLI overrides."""
        # Arrange
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("scraping:\n  min_delay: 1.0")

        # Act
        config = load_config(
            yaml_file,
            scraping__timeout=90,
            output__file_prefix="override",
            export__incremental=True,
        )

        # Assert
        assert config.scraping.min_delay == 1.0  # From file
        assert config.scraping.timeout == 90  # CLI override
        assert config.output.file_prefix == "override"  # CLI override
        assert config.export.incremental is True  # CLI override
