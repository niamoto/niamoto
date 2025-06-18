"""Test progress management utilities."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from rich.console import Console

from niamoto.cli.utils.progress import (
    ProgressManager,
    create_simple_progress,
    OperationTracker,
)


class TestProgressManager:
    """Test ProgressManager class."""

    def test_init_default_console(self):
        """Test ProgressManager initialization with default console."""
        manager = ProgressManager()
        assert isinstance(manager.console, Console)
        assert manager._current_progress is None
        assert manager._tasks == {}
        assert manager._start_time is None

    def test_init_custom_console(self):
        """Test ProgressManager initialization with custom console."""
        custom_console = MagicMock()
        manager = ProgressManager(console=custom_console)
        assert manager.console is custom_console

    def test_standard_columns(self):
        """Test standard progress columns."""
        manager = ProgressManager()
        columns = manager.standard_columns
        assert len(columns) == 4
        # Check that we have the expected column types
        column_types = [type(col).__name__ for col in columns]
        assert "SpinnerColumn" in column_types
        assert "TextColumn" in column_types
        assert "BarColumn" in column_types

    @patch("niamoto.cli.utils.progress.datetime")
    def test_progress_context_basic(self, mock_datetime):
        """Test basic progress context functionality."""
        start_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = start_time

        manager = ProgressManager()

        with manager.progress_context() as ctx:
            assert ctx is manager
            assert manager._start_time == start_time
            assert manager._stats["operations_completed"] == 0
            assert manager._stats["total_operations"] == 0
            assert manager._current_progress is not None

        # After context, should be cleaned up
        assert manager._current_progress is None
        assert manager._tasks == {}

    @patch("niamoto.cli.utils.progress.datetime")
    def test_progress_context_with_total(self, mock_datetime):
        """Test progress context with total operations."""
        start_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = start_time

        manager = ProgressManager()

        with manager.progress_context(total_operations=5) as ctx:
            assert ctx._stats["total_operations"] == 5

    def test_add_task_without_context(self):
        """Test adding task without active progress context."""
        manager = ProgressManager()

        with pytest.raises(RuntimeError, match="Progress context not active"):
            manager.add_task("test", "Test task")

    @patch("niamoto.cli.utils.progress.datetime")
    def test_add_task_with_context(self, mock_datetime):
        """Test adding task with active progress context."""
        start_time = datetime(2023, 1, 1, 12, 0, 0)
        task_start = datetime(2023, 1, 1, 12, 0, 5)
        mock_datetime.now.side_effect = [start_time, task_start]

        manager = ProgressManager()

        with manager.progress_context():
            task_id = manager.add_task("test_task", "Testing task", total=100)

            assert "test_task" in manager._tasks
            assert manager._tasks["test_task"] == task_id
            assert manager._task_start_times["test_task"] == task_start

    @patch("niamoto.cli.utils.progress.datetime")
    def test_update_task(self, mock_datetime):
        """Test updating task progress."""
        start_time = datetime(2023, 1, 1, 12, 0, 0)
        task_start = datetime(2023, 1, 1, 12, 0, 5)
        update_time1 = datetime(2023, 1, 1, 12, 0, 10)
        update_time2 = datetime(2023, 1, 1, 12, 0, 15)
        mock_datetime.now.side_effect = [
            start_time,
            task_start,
            update_time1,
            update_time2,
        ]

        manager = ProgressManager()

        with manager.progress_context():
            manager.add_task("test_task", "Testing task", total=100)

            # Test update with advance
            manager.update_task("test_task", advance=10)
            assert manager._stats["operations_completed"] == 10

            # Test update with description
            manager.update_task("test_task", advance=5, description="Updated task")
            assert manager._stats["operations_completed"] == 15

    def test_update_task_nonexistent(self):
        """Test updating non-existent task."""
        manager = ProgressManager()

        with manager.progress_context():
            # Should not raise error, just return
            manager.update_task("nonexistent", advance=5)
            assert manager._stats["operations_completed"] == 0

    def test_update_task_without_context(self):
        """Test updating task without active context."""
        manager = ProgressManager()

        # Should not raise error, just return
        manager.update_task("test", advance=5)

    @patch("niamoto.cli.utils.progress.datetime")
    def test_complete_task(self, mock_datetime):
        """Test completing a task."""
        start_time = datetime(2023, 1, 1, 12, 0, 0)
        task_start = datetime(2023, 1, 1, 12, 0, 5)
        complete_time = datetime(2023, 1, 1, 12, 0, 35)
        mock_datetime.now.side_effect = [start_time, task_start, complete_time]

        manager = ProgressManager()

        with manager.progress_context():
            manager.add_task("test_task", "Testing task", total=100)
            manager.complete_task("test_task", "Task completed successfully")

    def test_complete_task_nonexistent(self):
        """Test completing non-existent task."""
        manager = ProgressManager()

        with manager.progress_context():
            # Should not raise error, just return
            manager.complete_task("nonexistent")

    def test_complete_task_without_context(self):
        """Test completing task without active context."""
        manager = ProgressManager()

        # Should not raise error, just return
        manager.complete_task("test")

    def test_add_error(self):
        """Test adding error messages."""
        mock_console = MagicMock()
        manager = ProgressManager(console=mock_console)

        with manager.progress_context():
            manager.add_error("Test error message")

        assert manager._stats["errors"] == 1
        mock_console.print.assert_called_with("❌ Test error message", style="bold red")

    def test_add_warning(self):
        """Test adding warning messages."""
        mock_console = MagicMock()
        manager = ProgressManager(console=mock_console)

        with manager.progress_context():
            manager.add_warning("Test warning message")

        assert manager._stats["warnings"] == 1
        mock_console.print.assert_called_with("⚠️  Test warning message", style="yellow")

    @patch("niamoto.cli.utils.progress.datetime")
    def test_show_summary_basic(self, mock_datetime):
        """Test showing basic summary."""
        start_time = datetime(2023, 1, 1, 12, 0, 0)
        end_time = datetime(2023, 1, 1, 12, 0, 45)
        mock_datetime.now.side_effect = [start_time, end_time]

        mock_console = MagicMock()
        manager = ProgressManager(console=mock_console)

        with manager.progress_context(total_operations=5):
            manager._stats["operations_completed"] = 3
            manager.show_summary("Test Operation")

        # Check that summary was printed
        mock_console.print.assert_any_call(
            "\n📊 Test Operation Summary:", style="bold blue"
        )
        mock_console.print.assert_any_call("   Duration: 45s")
        mock_console.print.assert_any_call("   Operations completed: 3")
        mock_console.print.assert_any_call("   Total operations: 5")
        mock_console.print.assert_any_call("\n[✓] Success", style="bold green")

    @patch("niamoto.cli.utils.progress.datetime")
    def test_show_summary_with_errors_warnings(self, mock_datetime):
        """Test showing summary with errors and warnings."""
        start_time = datetime(2023, 1, 1, 12, 0, 0)
        end_time = datetime(2023, 1, 1, 12, 2, 30)  # 2m 30s
        mock_datetime.now.side_effect = [start_time, end_time]

        mock_console = MagicMock()
        manager = ProgressManager(console=mock_console)

        with manager.progress_context():
            manager._stats["errors"] = 2
            manager._stats["warnings"] = 1
            manager.show_summary("Test Operation")

        mock_console.print.assert_any_call("   Duration: 2m 30s")
        mock_console.print.assert_any_call("   Errors: 2", style="red")
        mock_console.print.assert_any_call("   Warnings: 1", style="yellow")
        mock_console.print.assert_any_call(
            "\n⚠️  Completed with errors", style="bold yellow"
        )

    @patch("niamoto.cli.utils.progress.datetime")
    def test_show_summary_with_additional_stats(self, mock_datetime):
        """Test showing summary with additional statistics."""
        start_time = datetime(2023, 1, 1, 12, 0, 0)
        end_time = datetime(2023, 1, 1, 12, 0, 30)
        mock_datetime.now.side_effect = [start_time, end_time]

        mock_console = MagicMock()
        manager = ProgressManager(console=mock_console)

        additional_stats = {"Files processed": 25, "Data imported": "1,500 records"}

        with manager.progress_context():
            manager.show_summary("Test Operation", additional_stats)

        mock_console.print.assert_any_call("   Files processed: 25")
        mock_console.print.assert_any_call("   Data imported: 1,500 records")

    def test_show_summary_without_context(self):
        """Test showing summary without active context."""
        mock_console = MagicMock()
        manager = ProgressManager(console=mock_console)

        # Should return early without printing
        manager.show_summary()
        mock_console.print.assert_not_called()

    def test_format_duration_seconds(self):
        """Test duration formatting for seconds."""
        manager = ProgressManager()
        duration = timedelta(seconds=45)
        result = manager._format_duration(duration)
        assert result == "45s"

    def test_format_duration_minutes(self):
        """Test duration formatting for minutes."""
        manager = ProgressManager()
        duration = timedelta(seconds=125)  # 2m 5s
        result = manager._format_duration(duration)
        assert result == "2m 5s"

    def test_format_duration_hours(self):
        """Test duration formatting for hours."""
        manager = ProgressManager()
        duration = timedelta(seconds=3725)  # 1h 2m
        result = manager._format_duration(duration)
        assert result == "1h 2m"


class TestCreateSimpleProgress:
    """Test create_simple_progress function."""

    def test_create_simple_progress_with_total(self):
        """Test creating simple progress with total."""
        progress = create_simple_progress("Test operation", total=100)
        assert progress is not None
        # Progress should have 4 columns when total is provided
        assert len(progress.columns) == 4

    def test_create_simple_progress_without_total(self):
        """Test creating simple progress without total."""
        progress = create_simple_progress("Test operation")
        assert progress is not None
        # Progress should have 4 columns (empty TextColumn when no total)
        assert len(progress.columns) == 4


class TestOperationTracker:
    """Test OperationTracker class."""

    def test_init_default_console(self):
        """Test OperationTracker initialization with default console."""
        tracker = OperationTracker()
        assert isinstance(tracker.console, Console)
        assert isinstance(tracker.start_time, datetime)
        assert tracker.operations == 0
        assert tracker.errors == 0
        assert tracker.warnings == 0

    def test_init_custom_console(self):
        """Test OperationTracker initialization with custom console."""
        custom_console = MagicMock()
        tracker = OperationTracker(console=custom_console)
        assert tracker.console is custom_console

    def test_start_operation(self):
        """Test starting an operation."""
        mock_console = MagicMock()
        tracker = OperationTracker(console=mock_console)

        tracker.start_operation("Starting test operation")
        mock_console.print.assert_called_once_with(
            "🚀 Starting test operation", style="blue"
        )

    def test_complete_operation(self):
        """Test completing an operation."""
        mock_console = MagicMock()
        tracker = OperationTracker(console=mock_console)

        tracker.complete_operation("Operation completed successfully")

        assert tracker.operations == 1
        mock_console.print.assert_called_once_with(
            "[✓] Operation completed successfully", style="green"
        )

    def test_error(self):
        """Test recording an error."""
        mock_console = MagicMock()
        tracker = OperationTracker(console=mock_console)

        tracker.error("An error occurred")

        assert tracker.errors == 1
        mock_console.print.assert_called_once_with(
            "[✗] An error occurred", style="bold red"
        )

    def test_warning(self):
        """Test recording a warning."""
        mock_console = MagicMock()
        tracker = OperationTracker(console=mock_console)

        tracker.warning("A warning occurred")

        assert tracker.warnings == 1
        mock_console.print.assert_called_once_with(
            "⚠️  A warning occurred", style="yellow"
        )

    def test_info(self):
        """Test showing info message."""
        mock_console = MagicMock()
        tracker = OperationTracker(console=mock_console)

        tracker.info("Information message")
        mock_console.print.assert_called_once_with(
            "ℹ️  Information message", style="blue"
        )

    @patch("niamoto.cli.utils.progress.datetime")
    def test_show_summary_success(self, mock_datetime):
        """Test showing summary for successful operation."""
        start_time = datetime(2023, 1, 1, 12, 0, 0)
        end_time = datetime(2023, 1, 1, 12, 0, 45)
        mock_datetime.now.side_effect = [start_time, end_time]

        mock_console = MagicMock()
        tracker = OperationTracker(console=mock_console)
        tracker.operations = 5

        tracker.show_summary("Test Operation")

        mock_console.print.assert_any_call(
            "\n📊 Test Operation Summary:", style="bold blue"
        )
        mock_console.print.assert_any_call("   Duration: 45s")
        mock_console.print.assert_any_call("   Operations: 5")
        mock_console.print.assert_any_call("\n[✓] Success", style="bold green")

    @patch("niamoto.cli.utils.progress.datetime")
    def test_show_summary_with_errors_warnings(self, mock_datetime):
        """Test showing summary with errors and warnings."""
        start_time = datetime(2023, 1, 1, 12, 0, 0)
        end_time = datetime(2023, 1, 1, 12, 1, 30)  # 1m 30s
        mock_datetime.now.side_effect = [start_time, end_time]

        mock_console = MagicMock()
        tracker = OperationTracker(console=mock_console)
        tracker.operations = 3
        tracker.errors = 1
        tracker.warnings = 2

        tracker.show_summary("Test Operation")

        mock_console.print.assert_any_call("   Duration: 1m 30s")
        mock_console.print.assert_any_call("   Operations: 3")
        mock_console.print.assert_any_call("   Errors: 1", style="red")
        mock_console.print.assert_any_call("   Warnings: 2", style="yellow")
        mock_console.print.assert_any_call(
            "\n⚠️  Completed with errors", style="bold yellow"
        )

    def test_format_duration_seconds(self):
        """Test duration formatting for seconds."""
        tracker = OperationTracker()
        duration = timedelta(seconds=30)
        result = tracker._format_duration(duration)
        assert result == "30s"

    def test_format_duration_minutes(self):
        """Test duration formatting for minutes."""
        tracker = OperationTracker()
        duration = timedelta(seconds=95)  # 1m 35s
        result = tracker._format_duration(duration)
        assert result == "1m 35s"

    def test_format_duration_hours(self):
        """Test duration formatting for hours."""
        tracker = OperationTracker()
        duration = timedelta(seconds=4200)  # 1h 10m
        result = tracker._format_duration(duration)
        assert result == "1h 10m"

    def test_multiple_operations(self):
        """Test multiple operations and their tracking."""
        mock_console = MagicMock()
        tracker = OperationTracker(console=mock_console)

        # Simulate a complete workflow
        tracker.start_operation("Starting import")
        tracker.complete_operation("Import completed")
        tracker.warning("Minor issue detected")
        tracker.info("Processing data")
        tracker.complete_operation("Processing completed")
        tracker.error("Export failed")

        assert tracker.operations == 2
        assert tracker.errors == 1
        assert tracker.warnings == 1

        # Verify all calls were made
        assert mock_console.print.call_count == 6
