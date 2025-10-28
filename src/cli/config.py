"""Configuration file support for CLI.

This module provides YAML-based configuration file support with Pydantic validation.
Configuration files allow users to define default settings for scraping, output,
filtering, and export operations. CLI options can override config file settings.

Design:
- DRY: Single source of truth for configuration
- SOLID: Single Responsibility (config loading/validation), Open/Closed (extensible)
- Type-safe: Full Pydantic validation with mypy strict mode
"""

from pathlib import Path

import structlog
import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_core.core_schema import ValidationInfo

logger = structlog.get_logger()


class ScrapingConfig(BaseModel):
    """Configuration for web scraping behavior.

    Attributes:
        min_delay: Minimum delay between requests in seconds (respectful scraping)
        max_delay: Maximum delay between requests in seconds (respectful scraping)
        user_agent: User agent string for HTTP requests (must identify bot)
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts for failed requests
        respect_robots_txt: Whether to check and honor robots.txt
    """

    min_delay: float = Field(
        default=1.0,
        ge=0.5,
        le=10.0,
        description="Minimum delay between requests (seconds)",
    )
    max_delay: float = Field(
        default=3.0,
        ge=0.5,
        le=10.0,
        description="Maximum delay between requests (seconds)",
    )
    user_agent: str = Field(
        default="CSF-Parts-Scraper/1.0 (https://github.com/yourusername/carpart-scraper)",
        min_length=10,
        description="User agent string for requests",
    )
    timeout: int = Field(
        default=30,
        ge=5,
        le=120,
        description="Request timeout (seconds)",
    )
    max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts",
    )
    respect_robots_txt: bool = Field(
        default=True,
        description="Check and honor robots.txt",
    )

    @field_validator("max_delay")
    @classmethod
    def validate_delay_range(cls, v: float, info: ValidationInfo) -> float:
        """Validate max_delay is greater than or equal to min_delay.

        Args:
            v: max_delay value
            info: Validation info containing other field values

        Returns:
            Validated max_delay

        Raises:
            ValueError: If max_delay < min_delay
        """
        if hasattr(info, "data") and "min_delay" in info.data:
            min_delay = info.data["min_delay"]
            if v < min_delay:
                msg = f"max_delay ({v}) must be >= min_delay ({min_delay})"
                raise ValueError(msg)
        return v

    @field_validator("user_agent")
    @classmethod
    def validate_user_agent(cls, v: str) -> str:
        """Validate user agent is descriptive and identifies as a bot.

        Args:
            v: User agent string

        Returns:
            Validated user agent

        Raises:
            ValueError: If user agent appears deceptive
        """
        # Ensure it doesn't look like it's pretending to be a browser
        forbidden_patterns = ["mozilla/5.0", "chrome/", "safari/", "firefox/"]
        v_lower = v.lower()
        if any(pattern in v_lower for pattern in forbidden_patterns):
            msg = "User agent must not pretend to be a browser (respectful scraping)"
            raise ValueError(msg)
        return v

    model_config = {
        "frozen": True,
        "str_strip_whitespace": True,
    }


class OutputConfig(BaseModel):
    """Configuration for output file settings.

    Attributes:
        directory: Output directory for exported files
        format: Export format (currently supports 'json')
        pretty: Whether to pretty-print JSON output (indent=2)
        file_prefix: Prefix for output filenames
    """

    directory: Path = Field(
        default=Path("exports"),
        description="Output directory for exports",
    )
    format: str = Field(
        default="json",
        description="Export format",
    )
    pretty: bool = Field(
        default=True,
        description="Pretty-print output",
    )
    file_prefix: str = Field(
        default="csf",
        min_length=1,
        max_length=50,
        description="Filename prefix",
    )

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        """Validate export format is supported.

        Args:
            v: Format string

        Returns:
            Lowercase format string

        Raises:
            ValueError: If format is not supported
        """
        v = v.lower()
        supported_formats = {"json"}
        if v not in supported_formats:
            msg = f"Unsupported format '{v}'. Supported: {supported_formats}"
            raise ValueError(msg)
        return v

    @field_validator("directory")
    @classmethod
    def validate_directory(cls, v: Path) -> Path:
        """Validate and normalize directory path.

        Args:
            v: Directory path

        Returns:
            Absolute directory path
        """
        # Resolve to absolute path
        return v.resolve()

    model_config = {
        "frozen": True,
        "str_strip_whitespace": True,
    }


class FilteringConfig(BaseModel):
    """Configuration for data filtering.

    Attributes:
        makes: List of vehicle makes to include (empty = all)
        years: List of years to include (empty = all)
        categories: List of part categories to include (empty = all)
        min_price: Minimum price filter (optional)
        max_price: Maximum price filter (optional)
    """

    makes: list[str] = Field(
        default_factory=list,
        description="Vehicle makes to include (empty = all)",
    )
    years: list[int] = Field(
        default_factory=list,
        description="Years to include (empty = all)",
    )
    categories: list[str] = Field(
        default_factory=list,
        description="Part categories to include (empty = all)",
    )
    min_price: float | None = Field(
        default=None,
        ge=0,
        description="Minimum price filter",
    )
    max_price: float | None = Field(
        default=None,
        ge=0,
        description="Maximum price filter",
    )

    @field_validator("makes")
    @classmethod
    def normalize_makes(cls, v: list[str]) -> list[str]:
        """Normalize make names to title case.

        Args:
            v: List of makes

        Returns:
            Normalized makes list
        """
        return [make.strip().title() for make in v if make.strip()]

    @field_validator("years")
    @classmethod
    def validate_years(cls, v: list[int]) -> list[int]:
        """Validate years are reasonable.

        Args:
            v: List of years

        Returns:
            Validated years list

        Raises:
            ValueError: If any year is invalid
        """
        min_year = 1950
        max_year = 2030
        for year in v:
            if year < min_year or year > max_year:
                msg = f"Year {year} out of range [{min_year}, {max_year}]"
                raise ValueError(msg)
        return sorted(v)

    @field_validator("categories")
    @classmethod
    def normalize_categories(cls, v: list[str]) -> list[str]:
        """Normalize category names to title case.

        Args:
            v: List of categories

        Returns:
            Normalized categories list
        """
        return [cat.strip().title() for cat in v if cat.strip()]

    @field_validator("max_price")
    @classmethod
    def validate_price_range(cls, v: float | None, info: ValidationInfo) -> float | None:
        """Validate max_price is greater than min_price.

        Args:
            v: max_price value
            info: Validation info

        Returns:
            Validated max_price

        Raises:
            ValueError: If max_price < min_price
        """
        if v is not None and hasattr(info, "data") and "min_price" in info.data:
            min_price = info.data["min_price"]
            if min_price is not None and v < min_price:
                msg = f"max_price ({v}) must be >= min_price ({min_price})"
                raise ValueError(msg)
        return v

    model_config = {
        "frozen": True,
        "str_strip_whitespace": True,
    }


class ExportConfig(BaseModel):
    """Configuration for export operations.

    Attributes:
        incremental: Enable incremental export (append to existing files)
        hierarchical: Export in hierarchical format (Year > Make > Model > Parts)
        include_images: Include image URLs in export
        include_compatibility: Include vehicle compatibility data
        deduplicate: Remove duplicate parts (same SKU)
    """

    incremental: bool = Field(
        default=False,
        description="Enable incremental export mode",
    )
    hierarchical: bool = Field(
        default=False,
        description="Export in hierarchical format",
    )
    include_images: bool = Field(
        default=True,
        description="Include image URLs",
    )
    include_compatibility: bool = Field(
        default=True,
        description="Include compatibility data",
    )
    deduplicate: bool = Field(
        default=True,
        description="Remove duplicate parts",
    )

    model_config = {
        "frozen": True,
    }


class AppConfig(BaseModel):
    """Main application configuration.

    Combines all configuration sections into a single validated config object.
    Provides methods for loading from YAML files and merging with CLI overrides.

    Attributes:
        scraping: Scraping behavior configuration
        output: Output file settings
        filtering: Data filtering options
        export: Export operation settings
    """

    scraping: ScrapingConfig = Field(
        default_factory=ScrapingConfig,
        description="Scraping configuration",
    )
    output: OutputConfig = Field(
        default_factory=OutputConfig,
        description="Output configuration",
    )
    filtering: FilteringConfig = Field(
        default_factory=FilteringConfig,
        description="Filtering configuration",
    )
    export: ExportConfig = Field(
        default_factory=ExportConfig,
        description="Export configuration",
    )

    model_config = {
        "frozen": True,
    }

    @classmethod
    def from_yaml(cls, filepath: Path | str) -> "AppConfig":
        """Load configuration from YAML file.

        Args:
            filepath: Path to YAML configuration file

        Returns:
            Validated AppConfig instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If YAML is invalid or validation fails
            OSError: If file cannot be read

        Example:
            >>> config = AppConfig.from_yaml("config.yaml")
            >>> config.scraping.min_delay
            1.0
        """
        filepath = Path(filepath)

        if not filepath.exists():
            msg = f"Config file not found: {filepath}"
            raise FileNotFoundError(msg)

        try:
            with filepath.open(encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if data is None:
                # Empty file - use defaults
                logger.warning("config_file_empty", filepath=str(filepath))
                return cls()

            logger.info("config_loaded", filepath=str(filepath), keys=list(data.keys()))
            return cls(**data)

        except yaml.YAMLError as e:
            logger.exception("yaml_parse_error", filepath=str(filepath), error=str(e))
            msg = f"Invalid YAML in {filepath}: {e}"
            raise ValueError(msg) from e
        except Exception as e:
            logger.exception("config_load_error", filepath=str(filepath), error=str(e))
            msg = f"Failed to load config from {filepath}: {e}"
            raise OSError(msg) from e

    @classmethod
    def from_yaml_optional(cls, filepath: Path | str | None) -> "AppConfig":
        """Load configuration from YAML file if it exists, otherwise use defaults.

        This method is convenient for CLI applications where config file is optional.

        Args:
            filepath: Path to YAML file or None

        Returns:
            Validated AppConfig instance (defaults if file doesn't exist)

        Raises:
            ValueError: If YAML is invalid or validation fails
            OSError: If file exists but cannot be read

        Example:
            >>> config = AppConfig.from_yaml_optional("config.yaml")  # File optional
            >>> config = AppConfig.from_yaml_optional(None)  # Use defaults
        """
        if filepath is None:
            logger.info("no_config_file_specified", message="Using default configuration")
            return cls()

        filepath = Path(filepath)
        if not filepath.exists():
            logger.info(
                "config_file_not_found",
                filepath=str(filepath),
                message="Using default configuration",
            )
            return cls()

        return cls.from_yaml(filepath)

    def merge_cli_options(
        self, **overrides: str | float | bool | list[str] | list[int] | None
    ) -> "AppConfig":
        """Merge CLI option overrides with config file settings.

        CLI options take precedence over config file values.
        Only non-None override values are applied.

        Args:
            **overrides: Keyword arguments matching config structure
                Format: section__field=value (e.g., scraping__min_delay=2.0)

        Returns:
            New AppConfig instance with overrides applied

        Raises:
            ValueError: If override key is invalid

        Example:
            >>> config = AppConfig.from_yaml("config.yaml")
            >>> # Override scraping delay from CLI
            >>> config = config.merge_cli_options(scraping__min_delay=2.0)
            >>> config.scraping.min_delay
            2.0
        """
        # Convert current config to dict
        config_dict = self.model_dump()

        # Apply overrides
        for key, value in overrides.items():
            if value is None:
                continue

            # Handle nested keys (e.g., "scraping__min_delay")
            if "__" in key:
                section, field = key.split("__", 1)
                if section not in config_dict:
                    msg = f"Invalid config section: {section}"
                    raise ValueError(msg)
                if not isinstance(config_dict[section], dict):
                    msg = f"Config section {section} is not a dict"
                    raise ValueError(msg)
                if field not in config_dict[section]:
                    msg = f"Invalid config field: {section}.{field}"
                    raise ValueError(msg)
                config_dict[section][field] = value
                logger.debug(
                    "cli_override_applied",
                    section=section,
                    field=field,
                    value=value,
                )
            else:
                # Top-level override (unusual but supported)
                if key not in config_dict:
                    msg = f"Invalid config key: {key}"
                    raise ValueError(msg)
                config_dict[key] = value
                logger.debug("cli_override_applied", key=key, value=value)

        # Create new config with merged values
        return self.__class__(**config_dict)

    def to_yaml(self, filepath: Path | str) -> None:
        """Export configuration to YAML file.

        Useful for generating config templates or saving runtime configurations.

        Args:
            filepath: Destination YAML file path

        Raises:
            OSError: If file cannot be written

        Example:
            >>> config = AppConfig()
            >>> config.to_yaml("config.yaml")
        """
        filepath = Path(filepath)

        try:
            # Ensure parent directory exists
            filepath.parent.mkdir(parents=True, exist_ok=True)

            # Convert to dict and then YAML
            config_dict = self.model_dump(mode="json")

            # Convert Path objects to strings for YAML serialization
            if "output" in config_dict and "directory" in config_dict["output"]:
                config_dict["output"]["directory"] = str(config_dict["output"]["directory"])

            with filepath.open("w", encoding="utf-8") as f:
                yaml.dump(
                    config_dict,
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True,
                )

            logger.info("config_exported", filepath=str(filepath))

        except Exception as e:
            logger.exception("config_export_error", filepath=str(filepath), error=str(e))
            msg = f"Failed to export config to {filepath}: {e}"
            raise OSError(msg) from e


def load_config(
    config_path: Path | str | None = None,
    **cli_overrides: str | float | bool | list[str] | list[int] | None,
) -> AppConfig:
    """Load and validate configuration from file with CLI overrides.

    This is the main entry point for configuration loading in CLI applications.
    It handles:
    1. Loading from YAML file (if provided and exists)
    2. Applying CLI option overrides
    3. Returning validated config

    Args:
        config_path: Path to YAML config file (optional)
        **cli_overrides: CLI option overrides (e.g., scraping__min_delay=2.0)

    Returns:
        Validated AppConfig instance

    Raises:
        ValueError: If config validation fails
        OSError: If config file cannot be read

    Example:
        >>> # Load from file with CLI overrides
        >>> config = load_config("config.yaml", scraping__min_delay=2.0)
        >>> # Use defaults with CLI overrides
        >>> config = load_config(scraping__timeout=60)
        >>> # Just use defaults
        >>> config = load_config()
    """
    # Load base config
    config = AppConfig.from_yaml_optional(config_path)

    # Apply CLI overrides
    if cli_overrides:
        config = config.merge_cli_options(**cli_overrides)

    logger.info(
        "config_initialized",
        has_config_file=config_path is not None,
        override_count=len(cli_overrides),
    )

    return config


def generate_example_config(filepath: Path | str = "config.example.yaml") -> None:
    """Generate example configuration file with all options documented.

    Creates a complete example config file with comments explaining each option.
    This is useful for users getting started with configuration.

    Args:
        filepath: Destination path for example config (default: "config.example.yaml")

    Raises:
        OSError: If file cannot be written

    Example:
        >>> generate_example_config("config.example.yaml")
    """
    # Create default config and export
    config = AppConfig()
    config.to_yaml(filepath)

    logger.info("example_config_generated", filepath=str(filepath))
