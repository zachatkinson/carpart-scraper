"""Scrape command for CLI.

This module implements the main 'scrape' command for extracting parts data
from CSF MyCarParts website. It delegates to the modular run_scrape.py script.
"""

import subprocess
import sys
from pathlib import Path

import click
import structlog
from rich.console import Console

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
    "--catalog-only",
    is_flag=True,
    default=False,
    help="Only scrape catalog data (skip images)",
)
@click.option(
    "--images-only",
    is_flag=True,
    default=False,
    help="Only fetch and convert images (requires existing parts.json)",
)
@click.pass_context
def scrape(  # noqa: PLR0913
    ctx: click.Context,
    make: str | None,
    year: int | None,
    output_dir: Path,
    catalog_only: bool,
    images_only: bool,
) -> None:
    r"""Scrape automotive parts data from CSF MyCarParts.

    This command delegates to the modular scraping pipeline (run_scrape.py)
    which orchestrates catalog scraping and image enrichment phases.

    Extracts part information, specifications, images, and vehicle compatibility
    data. Exports to JSON format suitable for WordPress import.

    Examples:
        \b
        # Full scrape (catalog + images)
        $ carpart scrape

        \b
        # Catalog only (no images)
        $ carpart scrape --catalog-only

        \b
        # Images only (requires existing parts.json)
        $ carpart scrape --images-only

        \b
        # Scrape only Honda vehicles
        $ carpart scrape --make Honda

        \b
        # Scrape only 2025 model year
        $ carpart scrape --year 2025

        \b
        # Scrape Honda 2025 vehicles with custom output
        $ carpart scrape --make Honda --year 2025 --output-dir ./honda_2025
    """
    try:
        # Determine which phases to run
        if catalog_only and images_only:
            console.print(
                "[red]Error:[/red] --catalog-only and --images-only are mutually exclusive"
            )
            sys.exit(1)

        # Build run_scrape.py command
        cmd = [sys.executable, "run_scrape.py"]

        # Add phase flags
        if catalog_only:
            cmd.append("--catalog")
        elif images_only:
            cmd.append("--images")
        else:
            # Default: run both phases
            cmd.extend(["--catalog", "--images"])

        # Add filters
        if make:
            cmd.extend(["--make", make])
        if year:
            cmd.extend(["--year", str(year)])

        # Add output directory
        cmd.extend(["--output-dir", str(output_dir)])

        # Add verbose flag if parent context has it
        if ctx.parent and ctx.parent.params.get("verbose"):
            cmd.append("--verbose")

        logger.info("delegating_to_run_scrape", command=" ".join(cmd))

        # Execute run_scrape.py (cmd built from trusted CLI args above)
        result = subprocess.run(cmd, check=True)  # noqa: S603
        sys.exit(result.returncode)

    except subprocess.CalledProcessError as e:
        logger.exception("scraping_failed", exit_code=e.returncode)
        console.print(f"[red]Scraping failed with exit code {e.returncode}[/red]")
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        console.print("\n[yellow]Scraping interrupted by user.[/yellow]")
        sys.exit(1)
    except Exception as e:
        logger.exception("scraping_error", error=str(e))
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
