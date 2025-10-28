"""Stats command for analyzing scraped data and exports.

This module provides the 'stats' CLI command for generating statistics
about automotive parts data, including part counts, categories, vehicles,
and file information.
"""

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from src.utils.stats_analyzer import DataStats, StatsAnalyzer


@click.command()
@click.option(
    "--input",
    "-i",
    "input_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="JSON file or directory to analyze",
)
@click.option(
    "--detailed",
    "-d",
    is_flag=True,
    default=False,
    help="Show detailed breakdown with additional statistics",
)
def stats(input_path: Path, detailed: bool) -> None:
    """Analyze automotive parts data and display statistics.

    Generates comprehensive statistics for scraped data or exported files,
    including part counts, category breakdowns, vehicle compatibility,
    and file information.

    Examples:
        # Analyze a single JSON file
        carpart stats --input exports/parts.json

        # Analyze all JSON files in a directory
        carpart stats --input prototype_output/

        # Show detailed statistics
        carpart stats --input exports/parts.json --detailed
    """
    console = Console()
    analyzer = StatsAnalyzer()

    try:
        # Determine if input is file or directory
        if input_path.is_file():
            console.print(f"\n[bold cyan]Analyzing file:[/bold cyan] {input_path}")
            stats_data = analyzer.analyze_file(input_path, detailed=detailed)
        else:
            console.print(f"\n[bold cyan]Analyzing directory:[/bold cyan] {input_path}")
            stats_data = analyzer.analyze_directory(input_path, detailed=detailed)

        # Display general statistics
        _display_general_stats(console, stats_data, input_path)

        # Display category breakdown
        if stats_data.parts_by_category:
            _display_category_breakdown(console, stats_data)

        # Display vehicle statistics
        if stats_data.has_compatibility_data:
            _display_vehicle_stats(console, stats_data)

        # Display detailed information if requested
        if detailed:
            _display_detailed_stats(console, stats_data)

        console.print("\n[bold green]✓[/bold green] Analysis complete!\n")

    except FileNotFoundError as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}\n", style="red")
        raise click.Abort from e
    except ValueError as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}\n", style="red")
        raise click.Abort from e
    except (OSError, KeyError) as e:
        console.print(f"\n[bold red]Unexpected error:[/bold red] {e}\n", style="red")
        raise click.Abort from e


def _display_general_stats(console: Console, stats_data: DataStats, input_path: Path) -> None:  # noqa: ARG001
    """Display general statistics table.

    Args:
        console: Rich console instance
        stats_data: Statistics data to display
        input_path: Path to analyzed file/directory (reserved for future use)
    """
    table = Table(title="General Statistics", show_header=True, header_style="bold")
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="magenta", justify="right")

    table.add_row("Total Parts", str(stats_data.total_parts))
    table.add_row("Unique SKUs", str(stats_data.unique_skus))

    # Add duplicate information
    if stats_data.duplicate_count > 0:
        dup_pct = stats_data.deduplication_rate * 100
        table.add_row(
            "Duplicates Detected",
            f"{stats_data.duplicate_count} ({dup_pct:.1f}%)",
            style="yellow",
        )

    table.add_row("Total Vehicles", str(stats_data.total_vehicles))

    # File size in human-readable format
    file_size = _format_file_size(stats_data.file_size_bytes)
    table.add_row("File Size", file_size)

    # Export date
    if stats_data.export_date:
        date_str = stats_data.export_date.strftime("%Y-%m-%d %H:%M:%S UTC")
        table.add_row("Analysis Date", date_str)

    # Data availability flags
    table.add_row(
        "Compatibility Data",
        "Yes" if stats_data.has_compatibility_data else "No",
        style="green" if stats_data.has_compatibility_data else "dim",
    )
    table.add_row(
        "Price Data",
        "Yes" if stats_data.price_data_available else "No",
        style="green" if stats_data.price_data_available else "dim",
    )

    console.print()
    console.print(table)


def _display_category_breakdown(console: Console, stats_data: DataStats) -> None:
    """Display parts by category table.

    Args:
        console: Rich console instance
        stats_data: Statistics data to display
    """
    table = Table(title="Parts by Category", show_header=True, header_style="bold")
    table.add_column("Category", style="cyan")
    table.add_column("Count", style="magenta", justify="right")
    table.add_column("Percentage", style="green", justify="right")

    # Sort categories by count (descending)
    sorted_categories = sorted(
        stats_data.parts_by_category.items(), key=lambda x: x[1], reverse=True
    )

    for category, count in sorted_categories:
        percentage = (count / stats_data.total_parts * 100) if stats_data.total_parts > 0 else 0
        table.add_row(category, str(count), f"{percentage:.1f}%")

    console.print()
    console.print(table)


def _display_vehicle_stats(console: Console, stats_data: DataStats) -> None:
    """Display vehicle statistics table.

    Args:
        console: Rich console instance
        stats_data: Statistics data to display
    """
    if not stats_data.vehicles_by_make:
        return

    table = Table(title="Vehicles by Make", show_header=True, header_style="bold")
    table.add_column("Make", style="cyan")
    table.add_column("Count", style="magenta", justify="right")
    table.add_column("Percentage", style="green", justify="right")

    # Sort makes by count (descending)
    sorted_makes = sorted(stats_data.vehicles_by_make.items(), key=lambda x: x[1], reverse=True)

    total_vehicles = sum(stats_data.vehicles_by_make.values())

    for make, count in sorted_makes:
        percentage = (count / total_vehicles * 100) if total_vehicles > 0 else 0
        table.add_row(make, str(count), f"{percentage:.1f}%")

    console.print()
    console.print(table)


def _display_detailed_stats(console: Console, stats_data: DataStats) -> None:
    """Display detailed statistics.

    Args:
        console: Rich console instance
        stats_data: Statistics data to display
    """
    console.print("\n[bold]Detailed Analysis[/bold]")

    # Average parts per category
    if stats_data.parts_by_category:
        avg_parts_per_category = stats_data.total_parts / len(stats_data.parts_by_category)
        console.print(
            f"  Average parts per category: [magenta]{avg_parts_per_category:.1f}[/magenta]"
        )

    # Data density (parts per KB)
    if stats_data.file_size_bytes > 0:
        parts_per_kb = stats_data.total_parts / (stats_data.file_size_bytes / 1024)
        console.print(f"  Data density: [magenta]{parts_per_kb:.2f}[/magenta] parts/KB")

    # SKU utilization rate
    if stats_data.total_parts > 0:
        sku_utilization = stats_data.unique_skus / stats_data.total_parts
        console.print(f"  SKU utilization: [magenta]{sku_utilization * 100:.1f}%[/magenta]")


def _format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string (e.g., "1.5 MB", "500 KB")
    """
    kb = 1024
    mb = kb * 1024
    gb = mb * 1024

    if size_bytes < kb:
        return f"{size_bytes} B"
    if size_bytes < mb:
        return f"{size_bytes / kb:.1f} KB"
    if size_bytes < gb:
        return f"{size_bytes / mb:.1f} MB"
    return f"{size_bytes / gb:.1f} GB"
