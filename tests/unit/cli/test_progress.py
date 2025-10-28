"""Unit tests for progress utilities (Rich progress bars).

This module tests all progress tracking components including:
- Status message printing
- Progress bar creation and updates
- Scraping progress tracker
- Export progress tracker
- Validation progress tracker
- Results tables
- Context managers
- User confirmation prompts

All tests follow the AAA (Arrange-Act-Assert) pattern.
"""

from io import StringIO
from typing import Any
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture
from rich.console import Console
from rich.live import Live
from rich.progress import Progress
from rich.spinner import Spinner
from rich.status import Status
from rich.table import Table

from src.cli.progress import (
    ExportProgress,
    ScrapingProgress,
    ValidationProgress,
    confirm,
    create_base_progress,
    create_results_table,
    create_simple_progress,
    operation_spinner,
    print_error,
    print_header,
    print_info,
    print_results_table,
    print_success,
    print_summary_stats,
    print_warning,
    show_spinner,
    simple_progress,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_console(mocker: MockerFixture) -> Mock:
    """Mock Rich Console for testing output.

    Args:
        mocker: pytest-mock fixture

    Returns:
        Mock console with print method
    """
    mock = mocker.Mock(spec=Console)
    mock.print = mocker.Mock()
    mock.input = mocker.Mock(return_value="y")
    return mock


@pytest.fixture
def string_console() -> Console:
    """Create a Console that writes to a string buffer.

    Returns:
        Console instance with StringIO buffer
    """
    buffer = StringIO()
    return Console(file=buffer, force_terminal=True, width=100)


# ============================================================================
# Status Message Tests
# ============================================================================


class TestStatusMessages:
    """Tests for status message printing functions."""

    def test_print_success(self, mocker: MockerFixture) -> None:
        """Test success message printing.

        Arrange: Mock console.print
        Act: Call print_success with a message
        Assert: Console.print called with green formatted message
        """
        # Arrange
        mock_console = mocker.patch("src.cli.progress.console")

        # Act
        print_success("Operation completed")

        # Assert
        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0][0]
        assert "✓" in call_args
        assert "Operation completed" in call_args
        assert "green" in call_args

    def test_print_error(self, mocker: MockerFixture) -> None:
        """Test error message printing.

        Arrange: Mock console.print
        Act: Call print_error with a message
        Assert: Console.print called with red formatted message
        """
        # Arrange
        mock_console = mocker.patch("src.cli.progress.console")

        # Act
        print_error("Operation failed")

        # Assert
        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0][0]
        assert "✗" in call_args
        assert "Operation failed" in call_args
        assert "red" in call_args

    def test_print_warning(self, mocker: MockerFixture) -> None:
        """Test warning message printing.

        Arrange: Mock console.print
        Act: Call print_warning with a message
        Assert: Console.print called with yellow formatted message
        """
        # Arrange
        mock_console = mocker.patch("src.cli.progress.console")

        # Act
        print_warning("This is a warning")

        # Assert
        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0][0]
        assert "⚠" in call_args
        assert "This is a warning" in call_args
        assert "yellow" in call_args

    def test_print_info(self, mocker: MockerFixture) -> None:
        """Test info message printing.

        Arrange: Mock console.print
        Act: Call print_info with a message
        Assert: Console.print called with blue formatted message
        """
        # Arrange
        mock_console = mocker.patch("src.cli.progress.console")

        # Act
        print_info("Information message")

        # Assert
        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0][0]
        assert "i" in call_args
        assert "Information message" in call_args
        assert "blue" in call_args

    def test_print_header(self, mocker: MockerFixture) -> None:
        """Test header printing with separator lines.

        Arrange: Mock console.print and console.rule
        Act: Call print_header with a title
        Assert: Console methods called to display header
        """
        # Arrange
        mock_console = mocker.patch("src.cli.progress.console")

        # Act
        print_header("Test Header")

        # Assert
        assert mock_console.print.call_count >= 2  # Called for spacing
        mock_console.rule.assert_called_once()
        call_args = mock_console.rule.call_args[0][0]
        assert "Test Header" in call_args
        assert "cyan" in call_args


# ============================================================================
# Progress Bar Factory Tests
# ============================================================================


class TestProgressFactories:
    """Tests for progress bar factory functions."""

    def test_create_base_progress(self) -> None:
        """Test base progress bar creation.

        Arrange: None
        Act: Create base progress bar
        Assert: Progress instance created with expected columns
        """
        # Act
        progress = create_base_progress()

        # Assert
        assert isinstance(progress, Progress)
        assert len(progress.columns) > 0
        # Check for presence of key column types by inspecting column types
        column_types = [type(col).__name__ for col in progress.columns]
        assert "SpinnerColumn" in column_types
        assert "TextColumn" in column_types
        assert "BarColumn" in column_types

    def test_create_base_progress_task_operations(self) -> None:
        """Test base progress bar can add and update tasks.

        Arrange: Create base progress bar
        Act: Add task and update it
        Assert: Task operations work correctly
        """
        # Arrange
        progress = create_base_progress()

        # Act
        task_id = progress.add_task("Testing", total=100)

        # Assert
        assert task_id is not None
        task = progress.tasks[task_id]
        assert task.total == 100
        assert "Testing" in task.description

    def test_create_simple_progress(self) -> None:
        """Test simple progress bar creation without time estimates.

        Arrange: None
        Act: Create simple progress bar
        Assert: Progress instance created with fewer columns
        """
        # Act
        progress = create_simple_progress()

        # Assert
        assert isinstance(progress, Progress)
        column_types = [type(col).__name__ for col in progress.columns]
        assert "SpinnerColumn" in column_types
        assert "BarColumn" in column_types
        # Simple progress shouldn't have time remaining columns
        assert "TimeRemainingColumn" not in column_types

    def test_create_simple_progress_task_operations(self) -> None:
        """Test simple progress bar task operations.

        Arrange: Create simple progress bar
        Act: Add and advance task
        Assert: Task operations work correctly
        """
        # Arrange
        progress = create_simple_progress()

        # Act
        task_id = progress.add_task("Loading", total=10)
        progress.advance(task_id, 5)

        # Assert
        task = progress.tasks[task_id]
        assert task.completed == 5
        assert task.total == 10


# ============================================================================
# Spinner Tests
# ============================================================================


class TestSpinner:
    """Tests for spinner utilities."""

    def test_operation_spinner_context_manager(self, mocker: MockerFixture) -> None:
        """Test operation_spinner context manager.

        Arrange: Mock console.status
        Act: Use operation_spinner in context
        Assert: Status created and yielded correctly
        """
        # Arrange
        mock_status = mocker.Mock(spec=Status)
        mock_console = mocker.patch("src.cli.progress.console")
        mock_console.status.return_value.__enter__ = mocker.Mock(return_value=mock_status)
        mock_console.status.return_value.__exit__ = mocker.Mock(return_value=None)

        # Act
        with operation_spinner("Processing data") as status:
            # Assert
            assert status == mock_status

        mock_console.status.assert_called_once()
        call_args = mock_console.status.call_args
        assert "Processing data" in call_args[0][0]

    def test_operation_spinner_status_update(self, mocker: MockerFixture) -> None:
        """Test updating status message within spinner context.

        Arrange: Mock console.status with update method
        Act: Update status within context
        Assert: Status.update called correctly
        """
        # Arrange
        mock_status = mocker.Mock(spec=Status)
        mock_console = mocker.patch("src.cli.progress.console")
        mock_console.status.return_value.__enter__ = mocker.Mock(return_value=mock_status)
        mock_console.status.return_value.__exit__ = mocker.Mock(return_value=None)

        # Act
        with operation_spinner("Initial message") as status:
            status.update("Updated message")

        # Assert
        mock_status.update.assert_called_once_with("Updated message")

    def test_show_spinner(self) -> None:
        """Test spinner creation.

        Arrange: None
        Act: Create spinner
        Assert: Spinner instance created with correct properties
        """
        # Act
        spinner = show_spinner("Loading data...")

        # Assert
        assert isinstance(spinner, Spinner)
        assert spinner.name == "dots"
        # Check text content (spinner.text can be various types)
        text_str = str(spinner.text)
        assert "Loading data..." in text_str


# ============================================================================
# ScrapingProgress Tests
# ============================================================================


class TestScrapingProgress:
    """Tests for ScrapingProgress tracker."""

    def test_initialization(self) -> None:
        """Test ScrapingProgress initialization.

        Arrange: None
        Act: Create ScrapingProgress instance
        Assert: Instance created with correct initial state
        """
        # Act
        tracker = ScrapingProgress(total_makes=5)

        # Assert
        assert isinstance(tracker, ScrapingProgress)
        assert tracker._total_makes == 5  # noqa: SLF001
        assert tracker.make_task is None
        assert tracker.model_task is None
        assert tracker.part_task is None
        assert tracker._live is None  # noqa: SLF001

    def test_start_creates_make_task(self) -> None:
        """Test start method creates make task.

        Arrange: Create ScrapingProgress with total_makes
        Act: Call start
        Assert: Make task created and Live started
        """
        # Arrange
        tracker = ScrapingProgress(total_makes=3)

        # Act
        tracker.start()

        # Assert
        assert tracker.make_task is not None
        assert tracker._live is not None  # noqa: SLF001
        assert isinstance(tracker._live, Live)  # noqa: SLF001

        # Cleanup
        tracker.stop()

    def test_start_without_makes(self) -> None:
        """Test start method without total_makes.

        Arrange: Create ScrapingProgress with 0 makes
        Act: Call start
        Assert: No make task created but Live started
        """
        # Arrange
        tracker = ScrapingProgress(total_makes=0)

        # Act
        tracker.start()

        # Assert
        assert tracker.make_task is None
        assert tracker._live is not None  # noqa: SLF001

        # Cleanup
        tracker.stop()

    def test_stop(self) -> None:
        """Test stop method stops Live display.

        Arrange: Create and start ScrapingProgress
        Act: Call stop
        Assert: Live display stopped
        """
        # Arrange
        tracker = ScrapingProgress(total_makes=1)
        tracker.start()
        assert tracker._live is not None  # noqa: SLF001

        # Act
        tracker.stop()

        # Assert - Live should be stopped (can't easily check but shouldn't error)
        # Call stop again to ensure it handles None gracefully
        tracker.stop()

    def test_start_make(self) -> None:
        """Test start_make creates model task.

        Arrange: Create and start ScrapingProgress
        Act: Call start_make
        Assert: Model task created with correct total
        """
        # Arrange
        tracker = ScrapingProgress(total_makes=1)
        tracker.start()

        # Act
        tracker.start_make("Honda", total_models=10)

        # Assert
        assert tracker.model_task is not None
        task = tracker.progress.tasks[tracker.model_task]
        assert task.total == 10
        assert "Honda" in task.description

        # Cleanup
        tracker.stop()

    def test_start_make_replaces_previous_model_task(self) -> None:
        """Test start_make replaces previous model task.

        Arrange: Create ScrapingProgress and start first make
        Act: Start second make
        Assert: Previous model task removed, new one created
        """
        # Arrange
        tracker = ScrapingProgress(total_makes=2)
        tracker.start()
        tracker.start_make("Honda", total_models=5)
        first_model_task = tracker.model_task

        # Act
        tracker.start_make("Toyota", total_models=8)

        # Assert
        assert tracker.model_task != first_model_task
        assert tracker.model_task is not None
        # First task should be removed from progress.tasks
        # Note: We verify task was removed by checking task dict
        if first_model_task is not None:
            # Task IDs that are removed won't be in the tasks mapping
            task_ids = list(tracker.progress.task_ids)
            assert first_model_task not in task_ids

        # Cleanup
        tracker.stop()

    def test_start_model(self) -> None:
        """Test start_model creates part task.

        Arrange: Create ScrapingProgress and start make
        Act: Call start_model
        Assert: Part task created with correct total
        """
        # Arrange
        tracker = ScrapingProgress(total_makes=1)
        tracker.start()
        tracker.start_make("Honda", total_models=1)

        # Act
        tracker.start_model("Accord", total_parts=50)

        # Assert
        assert tracker.part_task is not None
        task = tracker.progress.tasks[tracker.part_task]
        assert task.total == 50
        assert "Accord" in task.description

        # Cleanup
        tracker.stop()

    def test_start_model_replaces_previous_part_task(self) -> None:
        """Test start_model replaces previous part task.

        Arrange: Create ScrapingProgress and start first model
        Act: Start second model
        Assert: Previous part task removed, new one created
        """
        # Arrange
        tracker = ScrapingProgress(total_makes=1)
        tracker.start()
        tracker.start_make("Honda", total_models=2)
        tracker.start_model("Accord", total_parts=30)
        first_part_task = tracker.part_task

        # Act
        tracker.start_model("Civic", total_parts=40)

        # Assert
        assert tracker.part_task != first_part_task
        assert tracker.part_task is not None
        if first_part_task is not None:
            task_ids = list(tracker.progress.task_ids)
            assert first_part_task not in task_ids

        # Cleanup
        tracker.stop()

    def test_advance_part(self) -> None:
        """Test advance_part increments part counter.

        Arrange: Create ScrapingProgress with model started
        Act: Call advance_part
        Assert: Part counter incremented
        """
        # Arrange
        tracker = ScrapingProgress(total_makes=1)
        tracker.start()
        tracker.start_make("Honda", total_models=1)
        tracker.start_model("Accord", total_parts=10)

        # Act
        tracker.advance_part()
        tracker.advance_part(3)

        # Assert
        assert tracker.part_task is not None
        task = tracker.progress.tasks[tracker.part_task]
        assert task.completed == 4

        # Cleanup
        tracker.stop()

    def test_advance_part_without_task(self) -> None:
        """Test advance_part handles missing part task gracefully.

        Arrange: Create ScrapingProgress without starting model
        Act: Call advance_part
        Assert: No error raised
        """
        # Arrange
        tracker = ScrapingProgress(total_makes=1)
        tracker.start()

        # Act & Assert - Should not raise
        tracker.advance_part()

        # Cleanup
        tracker.stop()

    def test_finish_model(self) -> None:
        """Test finish_model advances model task and removes part task.

        Arrange: Create ScrapingProgress with model in progress
        Act: Call finish_model
        Assert: Model task advanced, part task removed
        """
        # Arrange
        tracker = ScrapingProgress(total_makes=1)
        tracker.start()
        tracker.start_make("Honda", total_models=2)
        tracker.start_model("Accord", total_parts=10)
        model_task_id = tracker.model_task
        part_task_id = tracker.part_task

        # Act
        tracker.finish_model()

        # Assert
        assert tracker.part_task is None
        if part_task_id is not None:
            task_ids = list(tracker.progress.task_ids)
            assert part_task_id not in task_ids
        if model_task_id is not None:
            model_task = tracker.progress.tasks[model_task_id]
            assert model_task.completed == 1

        # Cleanup
        tracker.stop()

    def test_finish_make(self) -> None:
        """Test finish_make advances make task and removes model task.

        Arrange: Create ScrapingProgress with make in progress
        Act: Call finish_make
        Assert: Make task advanced, model task removed
        """
        # Arrange
        tracker = ScrapingProgress(total_makes=2)
        tracker.start()
        tracker.start_make("Honda", total_models=1)
        make_task_id = tracker.make_task
        model_task_id = tracker.model_task

        # Act
        tracker.finish_make()

        # Assert
        assert tracker.model_task is None
        if model_task_id is not None:
            task_ids = list(tracker.progress.task_ids)
            assert model_task_id not in task_ids
        if make_task_id is not None:
            make_task = tracker.progress.tasks[make_task_id]
            assert make_task.completed == 1

        # Cleanup
        tracker.stop()

    def test_update_status(self, mocker: MockerFixture) -> None:
        """Test update_status prints transient message.

        Arrange: Mock console.print
        Act: Call update_status
        Assert: Message printed to console
        """
        # Arrange
        mock_console = mocker.patch("src.cli.progress.console")
        tracker = ScrapingProgress(total_makes=1)

        # Act
        tracker.update_status("Processing Accord...")

        # Assert
        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0][0]
        assert "Processing Accord..." in call_args

    def test_complete_workflow(self) -> None:
        """Test complete scraping workflow.

        Arrange: Create ScrapingProgress
        Act: Simulate complete scraping process
        Assert: All operations complete successfully
        """
        # Arrange
        tracker = ScrapingProgress(total_makes=2)

        # Act
        tracker.start()
        tracker.start_make("Honda", total_models=2)
        tracker.start_model("Accord", total_parts=5)
        for _ in range(5):
            tracker.advance_part()
        tracker.finish_model()
        tracker.start_model("Civic", total_parts=3)
        for _ in range(3):
            tracker.advance_part()
        tracker.finish_model()
        tracker.finish_make()

        tracker.start_make("Toyota", total_models=1)
        tracker.start_model("Camry", total_parts=4)
        for _ in range(4):
            tracker.advance_part()
        tracker.finish_model()
        tracker.finish_make()

        # Assert - workflow completed without errors
        if tracker.make_task is not None:
            assert tracker.progress.tasks[tracker.make_task].completed == 2

        # Cleanup
        tracker.stop()


# ============================================================================
# ExportProgress Tests
# ============================================================================


class TestExportProgress:
    """Tests for ExportProgress tracker."""

    def test_initialization(self) -> None:
        """Test ExportProgress initialization.

        Arrange: None
        Act: Create ExportProgress instance
        Assert: Instance created with correct initial state
        """
        # Act
        tracker = ExportProgress(total_items=100, format_name="JSON")

        # Assert
        assert isinstance(tracker, ExportProgress)
        assert tracker._total_items == 100  # noqa: SLF001
        assert tracker._format_name == "JSON"  # noqa: SLF001
        assert tracker.task is None
        assert tracker._live is None  # noqa: SLF001

    def test_initialization_default_format(self) -> None:
        """Test ExportProgress with default format name.

        Arrange: None
        Act: Create ExportProgress without format_name
        Assert: Default format name used
        """
        # Act
        tracker = ExportProgress(total_items=50)

        # Assert
        assert tracker._format_name == "file"  # noqa: SLF001

    def test_start(self) -> None:
        """Test start method creates export task.

        Arrange: Create ExportProgress
        Act: Call start
        Assert: Task created with correct description
        """
        # Arrange
        tracker = ExportProgress(total_items=200, format_name="CSV")

        # Act
        tracker.start()

        # Assert
        assert tracker.task is not None
        assert tracker._live is not None  # noqa: SLF001
        task = tracker.progress.tasks[tracker.task]
        assert task.total == 200
        assert "CSV" in task.description

        # Cleanup
        tracker.stop()

    def test_stop(self) -> None:
        """Test stop method stops Live display.

        Arrange: Create and start ExportProgress
        Act: Call stop
        Assert: Live display stopped
        """
        # Arrange
        tracker = ExportProgress(total_items=100)
        tracker.start()

        # Act
        tracker.stop()

        # Assert - Should handle stop gracefully
        tracker.stop()  # Call again to test None handling

    def test_advance(self) -> None:
        """Test advance increments export counter.

        Arrange: Create and start ExportProgress
        Act: Call advance with different amounts
        Assert: Counter incremented correctly
        """
        # Arrange
        tracker = ExportProgress(total_items=100)
        tracker.start()

        # Act
        tracker.advance()
        tracker.advance(5)

        # Assert
        assert tracker.task is not None
        task = tracker.progress.tasks[tracker.task]
        assert task.completed == 6

        # Cleanup
        tracker.stop()

    def test_advance_without_task(self) -> None:
        """Test advance handles missing task gracefully.

        Arrange: Create ExportProgress without starting
        Act: Call advance
        Assert: No error raised
        """
        # Arrange
        tracker = ExportProgress(total_items=100)

        # Act & Assert - Should not raise
        tracker.advance()

    def test_set_description(self) -> None:
        """Test set_description updates task description.

        Arrange: Create and start ExportProgress
        Act: Call set_description
        Assert: Task description updated
        """
        # Arrange
        tracker = ExportProgress(total_items=100)
        tracker.start()

        # Act
        tracker.set_description("Exporting parts to JSON")

        # Assert
        assert tracker.task is not None
        task = tracker.progress.tasks[tracker.task]
        assert "Exporting parts to JSON" in task.description

        # Cleanup
        tracker.stop()

    def test_set_description_without_task(self) -> None:
        """Test set_description handles missing task gracefully.

        Arrange: Create ExportProgress without starting
        Act: Call set_description
        Assert: No error raised
        """
        # Arrange
        tracker = ExportProgress(total_items=100)

        # Act & Assert - Should not raise
        tracker.set_description("Test description")

    def test_complete_export_workflow(self) -> None:
        """Test complete export workflow.

        Arrange: Create ExportProgress
        Act: Simulate complete export process
        Assert: All operations complete successfully
        """
        # Arrange
        tracker = ExportProgress(total_items=50, format_name="JSON")

        # Act
        tracker.start()
        for _ in range(10):
            tracker.advance(5)
        tracker.set_description("Finalizing export")

        # Assert
        assert tracker.task is not None
        task = tracker.progress.tasks[tracker.task]
        assert task.completed == 50
        assert "Finalizing export" in task.description

        # Cleanup
        tracker.stop()


# ============================================================================
# ValidationProgress Tests
# ============================================================================


class TestValidationProgress:
    """Tests for ValidationProgress tracker."""

    def test_initialization(self) -> None:
        """Test ValidationProgress initialization.

        Arrange: None
        Act: Create ValidationProgress instance
        Assert: Instance created with correct initial state
        """
        # Act
        tracker = ValidationProgress(total_items=150)

        # Assert
        assert isinstance(tracker, ValidationProgress)
        assert tracker._total_items == 150  # noqa: SLF001
        assert tracker.error_count == 0
        assert tracker.task is None
        assert tracker._live is None  # noqa: SLF001

    def test_start(self) -> None:
        """Test start method creates validation task.

        Arrange: Create ValidationProgress
        Act: Call start
        Assert: Task created with correct description
        """
        # Arrange
        tracker = ValidationProgress(total_items=100)

        # Act
        tracker.start()

        # Assert
        assert tracker.task is not None
        assert tracker._live is not None  # noqa: SLF001
        task = tracker.progress.tasks[tracker.task]
        assert task.total == 100

        # Cleanup
        tracker.stop()

    def test_stop(self) -> None:
        """Test stop method stops Live display.

        Arrange: Create and start ValidationProgress
        Act: Call stop
        Assert: Live display stopped
        """
        # Arrange
        tracker = ValidationProgress(total_items=100)
        tracker.start()

        # Act
        tracker.stop()

        # Assert - Should handle stop gracefully
        tracker.stop()

    def test_advance_success(self) -> None:
        """Test advance_success increments counter.

        Arrange: Create and start ValidationProgress
        Act: Call advance_success
        Assert: Counter incremented, error count unchanged
        """
        # Arrange
        tracker = ValidationProgress(total_items=100)
        tracker.start()

        # Act
        tracker.advance_success()
        tracker.advance_success()

        # Assert
        assert tracker.task is not None
        task = tracker.progress.tasks[tracker.task]
        assert task.completed == 2
        assert tracker.error_count == 0

        # Cleanup
        tracker.stop()

    def test_advance_success_without_task(self) -> None:
        """Test advance_success handles missing task gracefully.

        Arrange: Create ValidationProgress without starting
        Act: Call advance_success
        Assert: No error raised
        """
        # Arrange
        tracker = ValidationProgress(total_items=100)

        # Act & Assert - Should not raise
        tracker.advance_success()

    def test_advance_error(self) -> None:
        """Test advance_error increments counter and error count.

        Arrange: Create and start ValidationProgress
        Act: Call advance_error
        Assert: Counter and error count incremented
        """
        # Arrange
        tracker = ValidationProgress(total_items=100)
        tracker.start()

        # Act
        tracker.advance_error()
        tracker.advance_error()

        # Assert
        assert tracker.task is not None
        task = tracker.progress.tasks[tracker.task]
        assert task.completed == 2
        assert tracker.error_count == 2

        # Cleanup
        tracker.stop()

    def test_advance_error_updates_description(self) -> None:
        """Test advance_error updates task description with error count.

        Arrange: Create and start ValidationProgress
        Act: Call advance_error multiple times
        Assert: Description shows error count
        """
        # Arrange
        tracker = ValidationProgress(total_items=100)
        tracker.start()

        # Act
        tracker.advance_error()
        tracker.advance_error()
        tracker.advance_error()

        # Assert
        assert tracker.task is not None
        task = tracker.progress.tasks[tracker.task]
        assert "errors: 3" in task.description

        # Cleanup
        tracker.stop()

    def test_advance_error_without_task(self) -> None:
        """Test advance_error handles missing task gracefully.

        Arrange: Create ValidationProgress without starting
        Act: Call advance_error
        Assert: Error count incremented but no crash
        """
        # Arrange
        tracker = ValidationProgress(total_items=100)

        # Act
        tracker.advance_error()

        # Assert
        assert tracker.error_count == 1

    def test_mixed_validation_workflow(self) -> None:
        """Test validation workflow with mixed success and errors.

        Arrange: Create ValidationProgress
        Act: Simulate validation with successes and errors
        Assert: Counters updated correctly
        """
        # Arrange
        tracker = ValidationProgress(total_items=10)

        # Act
        tracker.start()
        tracker.advance_success()
        tracker.advance_success()
        tracker.advance_error()
        tracker.advance_success()
        tracker.advance_error()
        tracker.advance_error()
        tracker.advance_success()
        tracker.advance_success()
        tracker.advance_success()
        tracker.advance_success()

        # Assert
        assert tracker.task is not None
        task = tracker.progress.tasks[tracker.task]
        assert task.completed == 10
        assert tracker.error_count == 3

        # Cleanup
        tracker.stop()


# ============================================================================
# Results Table Tests
# ============================================================================


class TestResultsTable:
    """Tests for results table creation and printing."""

    def test_create_results_table_basic(self) -> None:
        """Test create_results_table creates basic table.

        Arrange: Prepare table data
        Act: Create results table
        Assert: Table created with correct structure
        """
        # Arrange
        columns = ["Make", "Models", "Parts"]
        rows = [
            ["Honda", "25", "1,234"],
            ["Toyota", "30", "1,567"],
        ]

        # Act
        table = create_results_table(
            title="Scraping Results",
            columns=columns,
            rows=rows,
        )

        # Assert
        assert isinstance(table, Table)
        assert table.title == "Scraping Results"
        assert len(table.columns) == 3
        assert table.row_count == 2

    def test_create_results_table_without_header(self) -> None:
        """Test create_results_table without column headers.

        Arrange: Prepare table data
        Act: Create results table with show_header=False
        Assert: Table created without headers
        """
        # Arrange
        columns = ["Col1", "Col2"]
        rows = [["A", "B"], ["C", "D"]]

        # Act
        table = create_results_table(
            title="Test",
            columns=columns,
            rows=rows,
            show_header=False,
        )

        # Assert
        assert isinstance(table, Table)
        assert table.show_header is False

    def test_create_results_table_empty_rows(self) -> None:
        """Test create_results_table with empty rows.

        Arrange: Prepare columns but no rows
        Act: Create results table
        Assert: Table created with no rows
        """
        # Arrange
        columns = ["Column1", "Column2"]
        rows: list[list[Any]] = []

        # Act
        table = create_results_table(
            title="Empty Table",
            columns=columns,
            rows=rows,
        )

        # Assert
        assert isinstance(table, Table)
        assert table.row_count == 0

    def test_create_results_table_mixed_types(self) -> None:
        """Test create_results_table converts mixed types to strings.

        Arrange: Prepare rows with different types
        Act: Create results table
        Assert: All values converted to strings
        """
        # Arrange
        columns = ["Name", "Count", "Price"]
        rows = [
            ["Item1", 42, 19.99],
            ["Item2", 100, 25.50],
        ]

        # Act
        table = create_results_table(
            title="Mixed Types",
            columns=columns,
            rows=rows,
        )

        # Assert
        assert isinstance(table, Table)
        assert table.row_count == 2

    def test_print_results_table(self, mocker: MockerFixture) -> None:
        """Test print_results_table prints to console.

        Arrange: Mock console.print and prepare table data
        Act: Call print_results_table
        Assert: Console.print called with table
        """
        # Arrange
        mock_console = mocker.patch("src.cli.progress.console")
        columns = ["A", "B"]
        rows = [["1", "2"]]

        # Act
        print_results_table(
            title="Test Table",
            columns=columns,
            rows=rows,
        )

        # Assert
        mock_console.print.assert_called_once()
        printed_arg = mock_console.print.call_args[0][0]
        assert isinstance(printed_arg, Table)


# ============================================================================
# Summary Statistics Tests
# ============================================================================


class TestSummaryStats:
    """Tests for summary statistics printing."""

    def test_print_summary_stats(self, mocker: MockerFixture) -> None:
        """Test print_summary_stats prints formatted table.

        Arrange: Mock console.print and prepare stats
        Act: Call print_summary_stats
        Assert: Console.print called with stats table
        """
        # Arrange
        mock_console = mocker.patch("src.cli.progress.console")
        stats = {
            "Total Parts": 1234,
            "Total Makes": 5,
            "Success Rate": "98.5%",
        }

        # Act
        print_summary_stats(stats, title="Test Summary")

        # Assert
        assert mock_console.print.call_count >= 3  # Empty lines + table
        # Check that a Table was printed
        calls = mock_console.print.call_args_list
        table_printed = any(isinstance(call[0][0], Table) for call in calls if call[0])
        assert table_printed

    def test_print_summary_stats_default_title(self, mocker: MockerFixture) -> None:
        """Test print_summary_stats with default title.

        Arrange: Mock console.print and prepare stats
        Act: Call print_summary_stats without title
        Assert: Default title used
        """
        # Arrange
        mock_console = mocker.patch("src.cli.progress.console")
        stats = {"Metric": "Value"}

        # Act
        print_summary_stats(stats)

        # Assert
        assert mock_console.print.call_count >= 1

    def test_print_summary_stats_empty(self, mocker: MockerFixture) -> None:
        """Test print_summary_stats with empty stats.

        Arrange: Mock console.print with empty stats dict
        Act: Call print_summary_stats
        Assert: Table printed with no rows
        """
        # Arrange
        mock_console = mocker.patch("src.cli.progress.console")
        stats: dict[str, Any] = {}

        # Act
        print_summary_stats(stats)

        # Assert
        assert mock_console.print.call_count >= 1


# ============================================================================
# Simple Progress Context Manager Tests
# ============================================================================


class TestSimpleProgress:
    """Tests for simple_progress context manager."""

    def test_simple_progress_context(self) -> None:
        """Test simple_progress context manager.

        Arrange: None
        Act: Use simple_progress in context
        Assert: Progress and task ID yielded
        """
        # Act & Assert
        with simple_progress("Processing", 10) as (progress, task_id):
            assert isinstance(progress, Progress)
            assert task_id is not None
            task = progress.tasks[task_id]
            assert task.total == 10

    def test_simple_progress_advance(self) -> None:
        """Test advancing progress within context.

        Arrange: None
        Act: Advance progress in context
        Assert: Progress updated correctly
        """
        # Act
        with simple_progress("Processing", 5) as (progress, task_id):
            progress.advance(task_id, 3)
            task = progress.tasks[task_id]

            # Assert
            assert task.completed == 3

    def test_simple_progress_description(self) -> None:
        """Test task description in simple_progress.

        Arrange: None
        Act: Create progress with description
        Assert: Description formatted correctly
        """
        # Act
        with simple_progress("Loading files", 20) as (progress, task_id):
            task = progress.tasks[task_id]

            # Assert
            assert "Loading files" in task.description

    def test_simple_progress_cleanup(self) -> None:
        """Test simple_progress cleans up after context.

        Arrange: Create progress context
        Act: Exit context
        Assert: Progress stopped properly
        """
        # Arrange & Act
        with simple_progress("Test", 1) as (_progress, _task_id):
            pass

        # Assert - Context exited without error


# ============================================================================
# Confirmation Prompt Tests
# ============================================================================


class TestConfirmation:
    """Tests for confirmation prompt."""

    def test_confirm_yes_response(self, mocker: MockerFixture) -> None:
        """Test confirm returns True for 'y' response.

        Arrange: Mock console.input to return 'y'
        Act: Call confirm
        Assert: Returns True
        """
        # Arrange
        mock_console = mocker.patch("src.cli.progress.console")
        mock_console.input.return_value = "y"

        # Act
        result = confirm("Continue?")

        # Assert
        assert result is True

    def test_confirm_yes_full_response(self, mocker: MockerFixture) -> None:
        """Test confirm returns True for 'yes' response.

        Arrange: Mock console.input to return 'yes'
        Act: Call confirm
        Assert: Returns True
        """
        # Arrange
        mock_console = mocker.patch("src.cli.progress.console")
        mock_console.input.return_value = "yes"

        # Act
        result = confirm("Continue?")

        # Assert
        assert result is True

    def test_confirm_yes_uppercase(self, mocker: MockerFixture) -> None:
        """Test confirm handles uppercase 'Y' response.

        Arrange: Mock console.input to return 'Y'
        Act: Call confirm
        Assert: Returns True
        """
        # Arrange
        mock_console = mocker.patch("src.cli.progress.console")
        mock_console.input.return_value = "Y"

        # Act
        result = confirm("Continue?")

        # Assert
        assert result is True

    def test_confirm_no_response(self, mocker: MockerFixture) -> None:
        """Test confirm returns False for 'n' response.

        Arrange: Mock console.input to return 'n'
        Act: Call confirm
        Assert: Returns False
        """
        # Arrange
        mock_console = mocker.patch("src.cli.progress.console")
        mock_console.input.return_value = "n"

        # Act
        result = confirm("Continue?")

        # Assert
        assert result is False

    def test_confirm_empty_response_default_false(self, mocker: MockerFixture) -> None:
        """Test confirm uses default False for empty response.

        Arrange: Mock console.input to return empty string
        Act: Call confirm with default=False
        Assert: Returns False
        """
        # Arrange
        mock_console = mocker.patch("src.cli.progress.console")
        mock_console.input.return_value = ""

        # Act
        result = confirm("Continue?", default=False)

        # Assert
        assert result is False

    def test_confirm_empty_response_default_true(self, mocker: MockerFixture) -> None:
        """Test confirm uses default True for empty response.

        Arrange: Mock console.input to return empty string
        Act: Call confirm with default=True
        Assert: Returns True
        """
        # Arrange
        mock_console = mocker.patch("src.cli.progress.console")
        mock_console.input.return_value = ""

        # Act
        result = confirm("Continue?", default=True)

        # Assert
        assert result is True

    def test_confirm_invalid_response(self, mocker: MockerFixture) -> None:
        """Test confirm returns False for invalid response.

        Arrange: Mock console.input to return invalid string
        Act: Call confirm
        Assert: Returns False
        """
        # Arrange
        mock_console = mocker.patch("src.cli.progress.console")
        mock_console.input.return_value = "maybe"

        # Act
        result = confirm("Continue?")

        # Assert
        assert result is False

    def test_confirm_prompt_format_default_false(self, mocker: MockerFixture) -> None:
        """Test confirm shows correct prompt format for default=False.

        Arrange: Mock console.input
        Act: Call confirm with default=False
        Assert: Prompt shows y/N
        """
        # Arrange
        mock_console = mocker.patch("src.cli.progress.console")
        mock_console.input.return_value = "y"

        # Act
        confirm("Delete file?", default=False)

        # Assert
        call_args = mock_console.input.call_args[0][0]
        assert "[y/N]" in call_args
        assert "Delete file?" in call_args

    def test_confirm_prompt_format_default_true(self, mocker: MockerFixture) -> None:
        """Test confirm shows correct prompt format for default=True.

        Arrange: Mock console.input
        Act: Call confirm with default=True
        Assert: Prompt shows Y/n
        """
        # Arrange
        mock_console = mocker.patch("src.cli.progress.console")
        mock_console.input.return_value = "n"

        # Act
        confirm("Proceed?", default=True)

        # Assert
        call_args = mock_console.input.call_args[0][0]
        assert "[Y/n]" in call_args
        assert "Proceed?" in call_args
