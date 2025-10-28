"""CLI application entry point for carpart-scraper.

This module provides the main CLI interface using Click for command-line
argument parsing and Rich for beautiful terminal output.
"""

import logging
import sys
from pathlib import Path

import click
import structlog
from rich.console import Console
from rich.table import Table

# Configure structlog with Rich handler for beautiful output
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(min_level=logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=False,
)

logger = structlog.get_logger()
console = Console()


class ClickContext:
    """Container for CLI context shared across commands."""

    def __init__(self) -> None:
        """Initialize CLI context."""
        self.verbose: bool = False
        self.quiet: bool = False
        self.config_file: Path | None = None


pass_context = click.make_pass_decorator(ClickContext, ensure=True)


def configure_logging(verbose: bool, quiet: bool) -> None:
    """Configure logging based on verbosity flags.

    Args:
        verbose: Enable verbose (DEBUG level) logging
        quiet: Enable quiet mode (WARNING level and above only)
    """
    if quiet:
        log_level = logging.WARNING
    elif verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(min_level=log_level),
    )


def validate_config_file(
    ctx: click.Context,  # noqa: ARG001
    param: click.Parameter,  # noqa: ARG001
    value: str | None,
) -> Path | None:
    """Validate config file path exists.

    Args:
        ctx: Click context
        param: Click parameter
        value: Config file path string

    Returns:
        Path object if valid, None if not provided

    Raises:
        click.BadParameter: If config file doesn't exist
    """
    if value is None:
        return None

    config_path = Path(value)
    if not config_path.exists():
        msg = f"Config file not found: {config_path}"
        raise click.BadParameter(msg)

    if not config_path.is_file():
        msg = f"Config path is not a file: {config_path}"
        raise click.BadParameter(msg)

    return config_path


@click.group()
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Enable verbose output (DEBUG level logging)",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    default=False,
    help="Enable quiet mode (WARNING level and above only)",
)
@click.option(
    "--config-file",
    "-c",
    type=click.Path(exists=False, dir_okay=False, path_type=str),
    callback=validate_config_file,
    help="Path to configuration file",
)
@click.version_option(version="0.1.0", prog_name="carpart-scraper")
@click.pass_context
def cli(
    ctx: click.Context,
    verbose: bool,
    quiet: bool,
    config_file: Path | None,
) -> None:
    r"""CSF MyCarParts Scraper - Industry-leading automotive parts data extraction.

    A professional web scraper for CSF MyCarParts automotive parts data with
    comprehensive vehicle compatibility information.

    \b
    Features:
    - Respectful web scraping with rate limiting
    - Vehicle compatibility data extraction
    - Multiple export formats (JSON, CSV)
    - Comprehensive error handling and logging
    - Type-safe data validation

    \b
    Examples:
        # Scrape with verbose logging
        carpart scrape --verbose

        # Use custom config file
        carpart --config-file config.toml scrape

        # Show version
        carpart --version

    For detailed documentation, visit:
    https://github.com/yourusername/carpart-scraper
    """
    # Validate mutually exclusive options
    if verbose and quiet:
        console.print(
            "[bold red]Error:[/bold red] --verbose and --quiet are mutually exclusive",
            style="red",
        )
        sys.exit(1)

    # Configure logging
    configure_logging(verbose, quiet)

    # Initialize context
    ctx.obj = ClickContext()
    ctx.obj.verbose = verbose
    ctx.obj.quiet = quiet
    ctx.obj.config_file = config_file

    # Log startup
    if verbose:
        logger.debug(
            "cli_initialized",
            verbose=verbose,
            quiet=quiet,
            config_file=str(config_file) if config_file else None,
        )


@cli.command()
@pass_context
def version(ctx: ClickContext) -> None:  # noqa: ARG001
    """Display version information.

    Args:
        ctx: Click context (required by @pass_context decorator)
    """
    console.print("[bold green]carpart-scraper[/bold green] version [cyan]0.1.0[/cyan]")
    console.print("Copyright (c) 2025 Development Team")
    console.print("Licensed under MIT License")


@cli.command()
@pass_context
def config(ctx: ClickContext) -> None:
    """Display current configuration.

    Shows the active configuration including verbosity settings,
    config file path, and other runtime settings.
    """
    table = Table(title="Current Configuration", show_header=True, header_style="bold magenta")
    table.add_column("Setting", style="cyan", width=20)
    table.add_column("Value", style="green")

    table.add_row("Verbose", str(ctx.verbose))
    table.add_row("Quiet", str(ctx.quiet))
    table.add_row(
        "Config File",
        str(ctx.config_file) if ctx.config_file else "[dim]Not specified[/dim]",
    )

    # Determine log level
    if ctx.quiet:
        log_level = "WARNING"
    elif ctx.verbose:
        log_level = "DEBUG"
    else:
        log_level = "INFO"
    table.add_row("Log Level", log_level)

    console.print(table)


# Import and register commands
from src.cli.commands.export import export  # noqa: E402
from src.cli.commands.scrape import scrape  # noqa: E402
from src.cli.commands.stats import stats  # noqa: E402
from src.cli.commands.test_endpoint import test_endpoint  # noqa: E402
from src.cli.commands.validate import validate  # noqa: E402

cli.add_command(scrape)
cli.add_command(test_endpoint)
cli.add_command(stats)
cli.add_command(validate)
cli.add_command(export)


def main() -> None:
    """Entry point for the CLI application.

    This function is called when the CLI is invoked directly or through
    the installed console script.
    """
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(130)  # Standard exit code for Ctrl+C
    except Exception as e:
        logger.exception("unexpected_error", error=str(e))
        console.print(f"[bold red]Unexpected error:[/bold red] {e}", style="red")
        sys.exit(1)


if __name__ == "__main__":
    main()
