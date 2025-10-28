"""Progress bar utilities for CLI commands.

This module provides reusable progress tracking components using Rich library.
All components are designed to be imported and used by CLI commands for
beautiful, informative console output.

Components:
    - Scraping progress tracker (make/model/parts count)
    - Export progress tracker
    - Validation progress tracker
    - Colored status messages
    - Spinners for operations
    - Results tables
    - Progress bars with ETA
"""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from rich.console import Console
from rich.live import Live
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.spinner import Spinner
from rich.status import Status
from rich.table import Table
from rich.text import Text

# Initialize console for module-level use
console = Console()


# ============================================================================
# Status Messages
# ============================================================================


def print_success(message: str) -> None:
    """Print a success message in green.

    Args:
        message: Success message to display
    """
    console.print(f"[bold green]✓[/bold green] {message}")


def print_error(message: str) -> None:
    """Print an error message in red.

    Args:
        message: Error message to display
    """
    console.print(f"[bold red]✗[/bold red] {message}")


def print_warning(message: str) -> None:
    """Print a warning message in yellow.

    Args:
        message: Warning message to display
    """
    console.print(f"[bold yellow]⚠[/bold yellow] {message}")


def print_info(message: str) -> None:
    """Print an info message in blue.

    Args:
        message: Info message to display
    """
    console.print(f"[bold blue]i[/bold blue] {message}")


def print_header(title: str) -> None:
    """Print a header with separator lines.

    Args:
        title: Header title to display
    """
    console.print()
    console.rule(f"[bold cyan]{title}[/bold cyan]")
    console.print()


# ============================================================================
# Spinner Context Manager
# ============================================================================


@contextmanager
def operation_spinner(message: str) -> Generator[Status]:
    """Context manager for displaying a spinner during an operation.

    Args:
        message: Message to display next to spinner

    Yields:
        Status object that can be updated

    Examples:
        >>> with operation_spinner("Processing data") as status:
        ...     # Do work
        ...     status.update("Still processing...")
        ...     # More work
    """
    with console.status(f"[bold blue]{message}[/bold blue]", spinner="dots") as status:
        yield status


# ============================================================================
# Progress Bar Factories
# ============================================================================


def create_base_progress() -> Progress:
    """Create a base progress bar with standard columns.

    Returns:
        Configured Progress instance

    Examples:
        >>> progress = create_base_progress()
        >>> task = progress.add_task("Processing", total=100)
        >>> with progress:
        ...     for i in range(100):
        ...         progress.update(task, advance=1)
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}[/bold blue]"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
        TextColumn("•"),
        TimeRemainingColumn(),
        console=console,
    )


def create_simple_progress() -> Progress:
    """Create a simple progress bar without time estimates.

    Returns:
        Configured Progress instance for simple tasks

    Examples:
        >>> progress = create_simple_progress()
        >>> task = progress.add_task("Loading", total=10)
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}[/bold blue]"),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
    )


# ============================================================================
# Scraping Progress Tracker
# ============================================================================


class ScrapingProgress:
    """Progress tracker for scraping operations.

    Tracks progress across makes, models, and parts with nested progress bars.

    Attributes:
        progress: Rich Progress instance
        make_task: Task ID for make progress
        model_task: Task ID for model progress
        part_task: Task ID for part progress

    Examples:
        >>> tracker = ScrapingProgress(total_makes=5)
        >>> tracker.start()
        >>> tracker.start_make("Audi", total_models=10)
        >>> tracker.start_model("A4", total_parts=50)
        >>> for i in range(50):
        ...     tracker.advance_part()
        >>> tracker.finish_model()
        >>> tracker.finish_make()
        >>> tracker.stop()
    """

    def __init__(self, total_makes: int = 0) -> None:
        """Initialize scraping progress tracker.

        Args:
            total_makes: Total number of makes to process
        """
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}[/bold blue]"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            TextColumn("•"),
            TimeRemainingColumn(),
            console=console,
        )
        self.make_task: TaskID | None = None
        self.model_task: TaskID | None = None
        self.part_task: TaskID | None = None
        self._total_makes = total_makes
        self._live: Live | None = None

    def start(self) -> None:
        """Start the progress display."""
        if self._total_makes > 0:
            self.make_task = self.progress.add_task(
                "[cyan]Makes", total=self._total_makes, visible=True
            )
        self._live = Live(self.progress, console=console, refresh_per_second=10)
        self._live.start()

    def stop(self) -> None:
        """Stop the progress display."""
        if self._live:
            self._live.stop()

    def start_make(self, make_name: str, total_models: int) -> None:
        """Start processing a new make.

        Args:
            make_name: Name of the make
            total_models: Total models for this make
        """
        if self.model_task is not None:
            self.progress.remove_task(self.model_task)

        self.model_task = self.progress.add_task(
            f"[green]{make_name} - Models", total=total_models, visible=True
        )

    def start_model(self, model_name: str, total_parts: int) -> None:
        """Start processing a new model.

        Args:
            model_name: Name of the model
            total_parts: Total parts for this model
        """
        if self.part_task is not None:
            self.progress.remove_task(self.part_task)

        self.part_task = self.progress.add_task(
            f"[yellow]{model_name} - Parts", total=total_parts, visible=True
        )

    def advance_part(self, amount: int = 1) -> None:
        """Advance the part progress counter.

        Args:
            amount: Number of parts to advance by (default: 1)
        """
        if self.part_task is not None:
            self.progress.advance(self.part_task, amount)

    def finish_model(self) -> None:
        """Finish processing current model."""
        if self.model_task is not None:
            self.progress.advance(self.model_task, 1)
        if self.part_task is not None:
            self.progress.remove_task(self.part_task)
            self.part_task = None

    def finish_make(self) -> None:
        """Finish processing current make."""
        if self.make_task is not None:
            self.progress.advance(self.make_task, 1)
        if self.model_task is not None:
            self.progress.remove_task(self.model_task)
            self.model_task = None

    def update_status(self, message: str) -> None:
        """Update the status message.

        Args:
            message: New status message
        """
        # Add a transient message without creating a new task
        console.print(f"[dim]{message}[/dim]")


# ============================================================================
# Export Progress Tracker
# ============================================================================


class ExportProgress:
    """Progress tracker for export operations.

    Tracks progress of exporting parts to various formats.

    Attributes:
        progress: Rich Progress instance
        task: Task ID for export progress

    Examples:
        >>> tracker = ExportProgress(total_items=1000, format_name="JSON")
        >>> tracker.start()
        >>> for i in range(1000):
        ...     tracker.advance()
        >>> tracker.stop()
    """

    def __init__(self, total_items: int, format_name: str = "file") -> None:
        """Initialize export progress tracker.

        Args:
            total_items: Total number of items to export
            format_name: Name of export format (e.g., 'JSON', 'CSV')
        """
        self.progress = create_base_progress()
        self.task: TaskID | None = None
        self._total_items = total_items
        self._format_name = format_name
        self._live: Live | None = None

    def start(self) -> None:
        """Start the export progress display."""
        self.task = self.progress.add_task(
            f"[cyan]Exporting to {self._format_name}", total=self._total_items
        )
        self._live = Live(self.progress, console=console, refresh_per_second=10)
        self._live.start()

    def stop(self) -> None:
        """Stop the export progress display."""
        if self._live:
            self._live.stop()

    def advance(self, amount: int = 1) -> None:
        """Advance the export progress counter.

        Args:
            amount: Number of items to advance by (default: 1)
        """
        if self.task is not None:
            self.progress.advance(self.task, amount)

    def set_description(self, description: str) -> None:
        """Update the task description.

        Args:
            description: New description text
        """
        if self.task is not None:
            self.progress.update(self.task, description=f"[cyan]{description}")


# ============================================================================
# Validation Progress Tracker
# ============================================================================


class ValidationProgress:
    """Progress tracker for validation operations.

    Tracks progress of validating parts data with error counting.

    Attributes:
        progress: Rich Progress instance
        task: Task ID for validation progress
        error_count: Number of validation errors encountered

    Examples:
        >>> tracker = ValidationProgress(total_items=500)
        >>> tracker.start()
        >>> for item in items:
        ...     if validate(item):
        ...         tracker.advance_success()
        ...     else:
        ...         tracker.advance_error()
        >>> tracker.stop()
        >>> print(f"Errors: {tracker.error_count}")
    """

    def __init__(self, total_items: int) -> None:
        """Initialize validation progress tracker.

        Args:
            total_items: Total number of items to validate
        """
        self.progress = create_base_progress()
        self.task: TaskID | None = None
        self._total_items = total_items
        self.error_count = 0
        self._live: Live | None = None

    def start(self) -> None:
        """Start the validation progress display."""
        self.task = self.progress.add_task("[cyan]Validating parts", total=self._total_items)
        self._live = Live(self.progress, console=console, refresh_per_second=10)
        self._live.start()

    def stop(self) -> None:
        """Stop the validation progress display."""
        if self._live:
            self._live.stop()

    def advance_success(self) -> None:
        """Advance counter for a successful validation."""
        if self.task is not None:
            self.progress.advance(self.task, 1)

    def advance_error(self) -> None:
        """Advance counter for a failed validation.

        Also increments the error count.
        """
        self.error_count += 1
        if self.task is not None:
            self.progress.advance(self.task, 1)
            # Update description to show error count
            self.progress.update(
                self.task,
                description=f"[yellow]Validating parts (errors: {self.error_count})",
            )


# ============================================================================
# Results Table
# ============================================================================


def create_results_table(
    title: str,
    columns: list[str],
    rows: list[list[Any]],
    show_header: bool = True,
) -> Table:
    """Create a formatted results table.

    Args:
        title: Table title
        columns: List of column headers
        rows: List of row data (each row is a list of values)
        show_header: Whether to show column headers (default: True)

    Returns:
        Configured Rich Table

    Examples:
        >>> table = create_results_table(
        ...     title="Scraping Results",
        ...     columns=["Make", "Models", "Parts"],
        ...     rows=[
        ...         ["Audi", "25", "1,234"],
        ...         ["BMW", "30", "1,567"],
        ...     ]
        ... )
        >>> console.print(table)
    """
    table = Table(title=title, show_header=show_header, header_style="bold cyan")

    # Add columns
    for column in columns:
        table.add_column(column, style="white")

    # Add rows
    for row in rows:
        # Convert all values to strings
        str_row = [str(val) for val in row]
        table.add_row(*str_row)

    return table


def print_results_table(
    title: str,
    columns: list[str],
    rows: list[list[Any]],
    show_header: bool = True,
) -> None:
    """Print a formatted results table.

    Args:
        title: Table title
        columns: List of column headers
        rows: List of row data (each row is a list of values)
        show_header: Whether to show column headers (default: True)

    Examples:
        >>> print_results_table(
        ...     title="Export Summary",
        ...     columns=["Format", "Parts", "Size"],
        ...     rows=[["JSON", "1,234", "2.5 MB"]]
        ... )
    """
    table = create_results_table(title, columns, rows, show_header)
    console.print(table)


# ============================================================================
# Summary Statistics
# ============================================================================


def print_summary_stats(stats: dict[str, Any], title: str = "Summary") -> None:
    """Print summary statistics in a formatted table.

    Args:
        stats: Dictionary of statistic name to value
        title: Title for the statistics table

    Examples:
        >>> print_summary_stats({
        ...     "Total Parts": 1234,
        ...     "Total Makes": 5,
        ...     "Total Models": 120,
        ...     "Success Rate": "98.5%",
        ... })
    """
    table = Table(title=title, show_header=False, box=None)
    table.add_column("Metric", style="bold cyan", no_wrap=True)
    table.add_column("Value", style="bold white")

    for key, value in stats.items():
        table.add_row(key, str(value))

    console.print()
    console.print(table)
    console.print()


# ============================================================================
# Simple Progress Context Manager
# ============================================================================


@contextmanager
def simple_progress(
    description: str,
    total: int,
) -> Generator[tuple[Progress, TaskID]]:
    """Context manager for simple progress tracking.

    Args:
        description: Task description
        total: Total number of items

    Yields:
        Tuple of (Progress instance, task ID)

    Examples:
        >>> with simple_progress("Processing files", 100) as (progress, task):
        ...     for i in range(100):
        ...         # Do work
        ...         progress.advance(task)
    """
    progress = create_base_progress()
    task = progress.add_task(f"[cyan]{description}", total=total)

    with progress:
        yield progress, task


# ============================================================================
# Indeterminate Spinner
# ============================================================================


def show_spinner(message: str) -> Spinner:
    """Create a spinner for indeterminate progress.

    Args:
        message: Message to display

    Returns:
        Spinner instance

    Examples:
        >>> spinner = show_spinner("Loading data...")
        >>> # Display spinner in a status or live context
    """
    return Spinner("dots", text=Text(message, style="bold blue"))


# ============================================================================
# Confirmation Prompts
# ============================================================================


def confirm(message: str, default: bool = False) -> bool:
    """Prompt user for yes/no confirmation.

    Args:
        message: Confirmation prompt message
        default: Default value if user just presses enter

    Returns:
        True if user confirmed, False otherwise

    Examples:
        >>> if confirm("Delete all data?", default=False):
        ...     delete_data()
    """
    default_text = "Y/n" if default else "y/N"
    response = console.input(f"[bold yellow]?[/bold yellow] {message} [{default_text}]: ")

    if not response:
        return default

    return response.lower() in {"y", "yes"}
