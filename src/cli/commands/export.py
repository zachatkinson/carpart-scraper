"""Export command for CLI.

This module implements the export command that converts scraped data to JSON format
for WordPress import. Supports both flat and hierarchical export formats.
"""

import json
from pathlib import Path

import click
import structlog
from rich.console import Console
from rich.table import Table

from src.exporters.json_exporter import JSONExporter
from src.models.part import Part
from src.models.vehicle import VehicleCompatibility

logger = structlog.get_logger()
console = Console()


@click.command()
@click.option(
    "--input",
    "-i",
    "input_dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="Input directory containing scraped JSON data files.",
)
@click.option(
    "--output",
    "-o",
    "output_file",
    type=str,
    required=True,
    help="Output filename for the exported data (e.g., 'parts_export.json').",
)
@click.option(
    "--format",
    "-f",
    "export_format",
    type=click.Choice(["json", "hierarchical"], case_sensitive=False),
    default="json",
    help="Export format: 'json' for flat structure, 'hierarchical' for Year>Make>Model>Parts.",
)
@click.option(
    "--pretty/--no-pretty",
    default=True,
    help="Pretty-print JSON output with indentation (default: enabled).",
)
@click.option(
    "--output-dir",
    "-d",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default="exports",
    help="Output directory for exports (default: 'exports').",
)
def export(
    input_dir: Path,
    output_file: str,
    export_format: str,
    pretty: bool,
    output_dir: Path,
) -> None:
    r"""Export scraped data to JSON format for WordPress import.

    This command reads scraped data from JSON files and exports it in a clean,
    well-formatted structure suitable for WordPress import. Supports both flat
    and hierarchical organization.

    Examples:
        \b
        # Export in flat JSON format
        carpart export -i data/scraped -o parts.json

        \b
        # Export in hierarchical format (Year > Make > Model > Parts)
        carpart export -i data/scraped -o hierarchical.json -f hierarchical

        \b
        # Export with compact JSON (no pretty-printing)
        carpart export -i data/scraped -o compact.json --no-pretty

        \b
        # Export to custom output directory
        carpart export -i data/scraped -o parts.json -d /path/to/exports
    """
    try:
        console.print("\n[bold blue]CSF MyCarParts Data Exporter[/bold blue]")
        console.print(f"[dim]Reading data from: {input_dir}[/dim]\n")

        # Load parts data
        parts = _load_parts_from_directory(input_dir)
        if not parts:
            console.print("[yellow]Warning: No parts found in input directory[/yellow]")
            return

        console.print(f"[green]Loaded {len(parts)} parts[/green]")

        # Initialize exporter
        exporter = JSONExporter(output_dir=output_dir)

        # Export based on format
        if export_format.lower() == "hierarchical":
            # Load compatibility data for hierarchical export
            compatibility = _load_compatibility_from_directory(input_dir)
            if not compatibility:
                console.print(
                    "[yellow]Warning: No compatibility data found. "
                    "Hierarchical export requires compatibility mappings.[/yellow]"
                )
                return

            console.print(f"[green]Loaded {len(compatibility)} compatibility mappings[/green]")

            # Create parts lookup dictionary
            parts_by_sku = {part.sku: part for part in parts}

            # Export hierarchical
            output_path = exporter.export_hierarchical(
                compatibility=compatibility,
                parts_by_sku=parts_by_sku,
                filename=output_file,
                pretty=pretty,
            )
        else:
            # Export flat JSON
            output_path = exporter.export_parts(
                parts=parts,
                filename=output_file,
                pretty=pretty,
            )

        # Display export statistics
        _display_export_stats(exporter, output_path)

        console.print("\n[bold green]Export completed successfully![/bold green]")
        console.print(f"[dim]Output file: {output_path}[/dim]\n")

    except FileNotFoundError as e:
        console.print(f"[bold red]Error:[/bold red] Input directory not found: {e}")
        logger.exception("export_failed", error=str(e))
        raise click.Abort from e
    except (OSError, json.JSONDecodeError) as e:
        console.print(f"[bold red]Error:[/bold red] Failed to process data: {e}")
        logger.exception("export_failed", error=str(e))
        raise click.Abort from e
    except Exception as e:
        console.print(f"[bold red]Unexpected error:[/bold red] {e}")
        logger.exception("export_failed_unexpected", error=str(e))
        raise click.Abort from e


def _load_parts_from_directory(directory: Path) -> list[Part]:
    """Load Part instances from JSON files in directory.

    Args:
        directory: Directory containing parts JSON files

    Returns:
        List of validated Part instances

    Raises:
        OSError: If directory cannot be read
        json.JSONDecodeError: If JSON is invalid
    """
    parts: list[Part] = []

    # Look for parts.json or similar files
    parts_files = list(directory.glob("*parts*.json")) or list(directory.glob("*.json"))

    for file_path in parts_files:
        try:
            with file_path.open(encoding="utf-8") as f:
                data = json.load(f)

            # Handle different JSON structures
            if isinstance(data, dict):
                # Check for common structures
                if "parts" in data:
                    parts_data = data["parts"]
                elif "data" in data:
                    parts_data = data["data"]
                else:
                    # Assume single part
                    parts_data = [data]
            elif isinstance(data, list):
                parts_data = data
            else:
                logger.warning("unsupported_json_structure", file=str(file_path))
                continue

            # Parse parts
            for part_dict in parts_data:
                try:
                    part = Part(**part_dict)
                    parts.append(part)
                except (ValueError, TypeError) as e:
                    logger.warning("failed_to_parse_part", part=part_dict, error=str(e))

        except (OSError, json.JSONDecodeError) as e:
            logger.warning("failed_to_load_file", file=str(file_path), error=str(e))
            continue

    return parts


def _load_compatibility_from_directory(directory: Path) -> list[VehicleCompatibility]:
    """Load VehicleCompatibility instances from JSON files in directory.

    Args:
        directory: Directory containing compatibility JSON files

    Returns:
        List of validated VehicleCompatibility instances

    Raises:
        OSError: If directory cannot be read
        json.JSONDecodeError: If JSON is invalid
    """
    compatibility: list[VehicleCompatibility] = []

    # Look for compatibility.json or similar files
    compat_files = (
        list(directory.glob("*compatibility*.json")) or list(directory.glob("*compat*.json")) or []
    )

    for file_path in compat_files:
        try:
            with file_path.open(encoding="utf-8") as f:
                data = json.load(f)

            # Handle different JSON structures
            if isinstance(data, dict):
                if "compatibility" in data:
                    compat_data = data["compatibility"]
                elif "data" in data:
                    compat_data = data["data"]
                else:
                    # Assume single compatibility
                    compat_data = [data]
            elif isinstance(data, list):
                compat_data = data
            else:
                logger.warning("unsupported_json_structure", file=str(file_path))
                continue

            # Parse compatibility mappings
            for compat_dict in compat_data:
                try:
                    compat = VehicleCompatibility(**compat_dict)
                    compatibility.append(compat)
                except (ValueError, TypeError) as e:
                    logger.warning(
                        "failed_to_parse_compatibility", compat=compat_dict, error=str(e)
                    )

        except (OSError, json.JSONDecodeError) as e:
            logger.warning("failed_to_load_file", file=str(file_path), error=str(e))
            continue

    return compatibility


def _display_export_stats(exporter: JSONExporter, output_path: Path) -> None:
    """Display formatted export statistics.

    Args:
        exporter: JSONExporter instance
        output_path: Path to exported file
    """
    stats = exporter.get_export_stats(output_path)

    if "error" in stats:
        console.print(f"[yellow]Could not generate statistics: {stats['error']}[/yellow]")
        return

    # Create statistics table
    table = Table(title="Export Statistics", show_header=False, box=None)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Parts", str(stats.get("total_parts", 0)))
    table.add_row("File Size", f"{stats.get('file_size_mb', 0)} MB")
    table.add_row("Export Date", stats.get("export_date", "N/A"))
    table.add_row("Version", stats.get("version", "N/A"))

    console.print("\n")
    console.print(table)
