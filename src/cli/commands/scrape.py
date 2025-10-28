"""Scrape command for CLI.

This module implements the main 'scrape' command for extracting parts data
from CSF MyCarParts website.
"""

import sys
from pathlib import Path
from typing import Any

import click
import structlog
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table

from src.scraper.orchestrator import ScraperOrchestrator

logger = structlog.get_logger()
console = Console()


@click.command()
@click.option(
    "--make",
    type=str,
    default=None,
    help="Filter by vehicle make (e.g., 'Honda', 'Toyota')",
)
@click.option(
    "--year",
    type=int,
    default=None,
    help="Filter by model year (e.g., 2025, 2024)",
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, dir_okay=True, writable=True, path_type=Path),
    default="exports",
    help="Export directory path (default: exports/)",
)
@click.option(
    "--incremental",
    is_flag=True,
    default=False,
    help="Use incremental export (append to existing files)",
)
@click.option(
    "--delay",
    type=float,
    default=None,
    help="Override default delay between requests in seconds (default: 1.0-3.0)",
)
def scrape(
    make: str | None,
    year: int | None,
    output_dir: Path,
    incremental: bool,
    delay: float | None,
) -> None:
    r"""Scrape automotive parts data from CSF MyCarParts.

    Extracts part information, specifications, images, and vehicle compatibility
    data. Exports to JSON format suitable for WordPress import.

    Examples:
        \b
        # Scrape all data
        $ carpart scrape

        \b
        # Scrape only Honda vehicles
        $ carpart scrape --make Honda

        \b
        # Scrape only 2025 model year
        $ carpart scrape --year 2025

        \b
        # Scrape Honda 2025 vehicles with custom output
        $ carpart scrape --make Honda --year 2025 --output-dir ./honda_2025

        \b
        # Use incremental mode (append to existing export)
        $ carpart scrape --incremental

        \b
        # Override delay (faster scraping - use with caution)
        $ carpart scrape --delay 0.5
    """
    try:
        # Display startup banner
        _display_banner(make, year, output_dir, incremental, delay)

        # Initialize orchestrator
        with ScraperOrchestrator(
            output_dir=output_dir, incremental=incremental, delay_override=delay
        ) as orchestrator:
            # Execute scraping with progress tracking
            stats = _scrape_with_progress(orchestrator, make, year)

            # Export data
            _export_with_progress(orchestrator)

            # Display summary
            _display_summary(stats, orchestrator)

    except KeyboardInterrupt:
        console.print("\n[yellow]Scraping interrupted by user.[/yellow]")
        console.print("[dim]Progress has been saved. Use --incremental to resume.[/dim]")
        sys.exit(1)
    except Exception as e:
        logger.exception("scraping_failed", error=str(e))
        console.print(f"[red]Error:[/red] {e}")
        console.print("[dim]Check logs for details. Use --incremental to resume if possible.[/dim]")
        sys.exit(1)


def _display_banner(
    make: str | None,
    year: int | None,
    output_dir: Path,
    incremental: bool,
    delay: float | None,
) -> None:
    """Display startup banner with configuration.

    Args:
        make: Make filter
        year: Year filter
        output_dir: Export directory
        incremental: Incremental mode flag
        delay: Delay override
    """
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]CSF MyCarParts Scraper[/bold cyan]\n"
            "[dim]Respectful automotive parts data extraction[/dim]",
            border_style="cyan",
        )
    )
    console.print()

    # Build configuration table
    config_table = Table(show_header=False, box=None, padding=(0, 2))
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="white")

    config_table.add_row("Make Filter", make or "[dim]All makes[/dim]")
    config_table.add_row("Year Filter", str(year) if year else "[dim]All years[/dim]")
    config_table.add_row("Output Directory", str(output_dir))
    config_table.add_row("Export Mode", "[yellow]Incremental[/yellow]" if incremental else "Full")
    config_table.add_row(
        "Request Delay",
        f"{delay}s (custom)" if delay else "[dim]1.0-3.0s (respectful)[/dim]",
    )

    console.print(config_table)
    console.print()


def _scrape_with_progress(
    orchestrator: ScraperOrchestrator, make: str | None, year: int | None
) -> dict[str, Any]:
    """Execute scraping with Rich progress bar.

    Args:
        orchestrator: Scraper orchestrator instance
        make: Make filter
        year: Year filter

    Returns:
        Dict of scraping statistics
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            "[cyan]Scraping parts data...", total=None
        )  # Indeterminate for now

        # Execute scraping
        stats = orchestrator.scrape_all(make_filter=make, year_filter=year)

        progress.update(task, completed=100, total=100)

    return stats


def _export_with_progress(orchestrator: ScraperOrchestrator) -> None:
    """Export data with progress indication.

    Args:
        orchestrator: Scraper orchestrator instance
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold green]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[green]Exporting data to JSON...", total=None)

        # Export data
        orchestrator.export_data()

        progress.update(task, completed=1, total=1)


def _display_summary(stats: dict[str, Any], orchestrator: ScraperOrchestrator) -> None:  # noqa: ARG001
    """Display scraping summary.

    Args:
        stats: Scraping statistics (reserved for future use)
        orchestrator: Scraper orchestrator instance
    """
    console.print()
    console.print(
        Panel.fit(
            "[bold green]Scraping Complete![/bold green]\n[dim]Data exported successfully[/dim]",
            border_style="green",
        )
    )
    console.print()

    # Build summary table
    summary_table = Table(show_header=False, box=None, padding=(0, 2))
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green bold")

    current_stats = orchestrator.get_stats()
    summary_table.add_row("Unique Parts", str(current_stats["unique_parts"]))
    summary_table.add_row("Parts Scraped", str(current_stats["parts_scraped"]))
    summary_table.add_row("Vehicles Tracked", str(current_stats.get("vehicles_tracked", 0)))
    summary_table.add_row("Export Directory", str(orchestrator.output_dir.absolute()))

    console.print(summary_table)
    console.print()

    # Success message
    console.print(
        "[dim]Next steps:[/dim]\n"
        "  • Review exported JSON files in the output directory\n"
        "  • Import data to WordPress using the plugin\n"
        "  • Use --incremental flag for subsequent updates\n"
    )
