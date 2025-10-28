"""Validate command for CLI.

Validates JSON export files and directories against Pydantic models.
Provides beautiful validation reports using Rich tables.
"""

import sys
from pathlib import Path

import click
import structlog
from rich.console import Console
from rich.table import Table

from src.cli.validators import DataValidator, ValidationResult

logger = structlog.get_logger()
console = Console()


@click.command()
@click.option(
    "--input",
    "-i",
    "input_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="JSON file or directory to validate",
)
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="Strict mode: warnings are treated as errors",
)
@click.option(
    "--report",
    "-r",
    "report_path",
    type=click.Path(path_type=Path),
    help="Output path for validation report (optional)",
)
def validate(input_path: Path, strict: bool, report_path: Path | None) -> None:
    r"""Validate JSON export files against Pydantic models.

    Validates JSON files containing parts, compatibility data, or hierarchical exports.
    Checks structure, required fields, and data integrity.

    \b
    Examples:
        # Validate a single file
        carpart validate --input exports/parts.json

        # Validate in strict mode (warnings become errors)
        carpart validate --input exports/parts.json --strict

        # Validate directory and save report
        carpart validate --input exports/ --report validation_report.txt

    \b
    Exit Codes:
        0: All files valid (no errors)
        1: Validation failed (errors found)
    """
    logger.info("validation_started", path=str(input_path), strict=strict)

    console.print(f"\n[bold cyan]Validating:[/bold cyan] {input_path}\n")

    # Initialize validator
    validator = DataValidator(strict=strict)

    try:
        if input_path.is_file():
            # Validate single file
            result = validator.validate_json_file(input_path)
            results = {input_path.name: result}
        else:
            # Validate directory
            results = validator.validate_directory(input_path)

        # Display results
        _display_results(results, strict)

        # Generate report if requested
        if report_path:
            _generate_report(results, report_path, strict)
            console.print(f"\n[bold green]Report saved to:[/bold green] {report_path}")

        # Determine exit code
        any_invalid = any(not result.is_valid for result in results.values())

        if any_invalid:
            console.print("\n[bold red]Validation FAILED[/bold red]\n")
            logger.error("validation_failed", files_with_errors=len(results))
            sys.exit(1)
        else:
            console.print("\n[bold green]Validation PASSED[/bold green]\n")
            logger.info("validation_passed", files_validated=len(results))
            sys.exit(0)

    except (FileNotFoundError, ValueError) as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        logger.exception("validation_error", error=str(e))
        sys.exit(1)


def _display_results(results: dict[str, ValidationResult], strict: bool) -> None:
    """Display validation results in Rich table format.

    Args:
        results: Dict mapping filename to ValidationResult
        strict: Whether strict mode is enabled
    """
    # Summary table
    summary_table = Table(title="Validation Summary", show_header=True, header_style="bold cyan")
    summary_table.add_column("File", style="white", no_wrap=True)
    summary_table.add_column("Status", justify="center")
    summary_table.add_column("Items", justify="right", style="cyan")
    summary_table.add_column("Valid", justify="right", style="green")
    summary_table.add_column("Errors", justify="right", style="red")
    summary_table.add_column("Warnings", justify="right", style="yellow")

    for filename, result in results.items():
        # Determine status
        if result.is_valid:
            status = "[bold green]✓ PASS[/bold green]"
        else:
            status = "[bold red]✗ FAIL[/bold red]"

        summary_table.add_row(
            filename,
            status,
            str(result.total_items),
            str(result.valid_items),
            str(result.error_count),
            str(result.warning_count),
        )

    console.print(summary_table)

    # Display detailed issues for each file
    for filename, result in results.items():
        if result.errors or (strict and result.warnings):
            console.print(f"\n[bold yellow]Issues in {filename}:[/bold yellow]\n")

            # Errors table
            if result.errors:
                error_table = Table(
                    title="Errors", show_header=True, header_style="bold red", border_style="red"
                )
                error_table.add_column("Field", style="white")
                error_table.add_column("Message", style="red")
                error_table.add_column("Details", style="dim")

                for error in result.errors:
                    error_table.add_row(
                        error.field,
                        error.message,
                        error.details or "",
                    )

                console.print(error_table)

            # Warnings table (if strict mode or if there are warnings to show)
            if result.warnings:
                warning_table = Table(
                    title="Warnings",
                    show_header=True,
                    header_style="bold yellow",
                    border_style="yellow",
                )
                warning_table.add_column("Field", style="white")
                warning_table.add_column("Message", style="yellow")

                for warning in result.warnings:
                    warning_table.add_row(
                        warning.field,
                        warning.message,
                    )

                console.print(warning_table)
        elif result.warnings and not strict:
            # Just show warning count
            console.print(
                f"\n[yellow]{filename}:[/yellow] {result.warning_count} warning(s) "
                f"(use --strict to see details)"
            )


def _generate_report(results: dict[str, ValidationResult], report_path: Path, strict: bool) -> None:
    """Generate text validation report.

    Args:
        results: Dict mapping filename to ValidationResult
        report_path: Output path for report
        strict: Whether strict mode is enabled
    """
    lines: list[str] = []
    lines.append("=" * 80)
    lines.append("VALIDATION REPORT")
    lines.append("=" * 80)
    lines.append("")

    # Overall summary
    total_files = len(results)
    passed_files = sum(1 for r in results.values() if r.is_valid)
    failed_files = total_files - passed_files
    total_errors = sum(r.error_count for r in results.values())
    total_warnings = sum(r.warning_count for r in results.values())

    lines.append(f"Total Files: {total_files}")
    lines.append(f"Passed: {passed_files}")
    lines.append(f"Failed: {failed_files}")
    lines.append(f"Total Errors: {total_errors}")
    lines.append(f"Total Warnings: {total_warnings}")
    lines.append(f"Strict Mode: {'Enabled' if strict else 'Disabled'}")
    lines.append("")

    # Per-file details
    for filename, result in results.items():
        lines.append("-" * 80)
        lines.append(f"File: {filename}")
        lines.append("-" * 80)
        lines.append(f"Status: {'PASS' if result.is_valid else 'FAIL'}")
        lines.append(f"Total Items: {result.total_items}")
        lines.append(f"Valid Items: {result.valid_items}")
        lines.append(f"Errors: {result.error_count}")
        lines.append(f"Warnings: {result.warning_count}")
        lines.append("")

        # Errors
        if result.errors:
            lines.append("ERRORS:")
            for error in result.errors:
                lines.append(f"  - Field: {error.field}")
                lines.append(f"    Message: {error.message}")
                if error.details:
                    lines.append(f"    Details: {error.details}")
                lines.append("")

        # Warnings
        if result.warnings:
            lines.append("WARNINGS:")
            for warning in result.warnings:
                lines.append(f"  - Field: {warning.field}")
                lines.append(f"    Message: {warning.message}")
                lines.append("")

    lines.append("=" * 80)
    lines.append("END OF REPORT")
    lines.append("=" * 80)

    # Write report
    report_text = "\n".join(lines)
    report_path.write_text(report_text, encoding="utf-8")
    logger.info("report_generated", path=str(report_path))
