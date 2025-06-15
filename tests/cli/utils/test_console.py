"""Test console utilities."""

import pytest
from unittest.mock import patch, MagicMock
from rich.table import Table
from rich.panel import Panel

from niamoto.cli.utils.console import (
    print_success,
    print_error,
    print_warning,
    print_info,
    print_start,
    print_processing,
    print_section,
    print_summary_header,
    print_operation_start,
    print_operation_complete,
    print_files_processed,
    print_duration,
    print_stats,
    print_metrics_summary,
    print_operation_metrics,
    print_step_header,
    print_step_complete,
    print_step_progress,
    print_linking_status,
    print_unlinked_samples,
    print_import_result,
    print_file_processed,
    print_table,
    format_file_size,
    format_number,
    console,
)


@pytest.fixture
def mock_console():
    """Mock console for testing."""
    with patch("niamoto.cli.utils.console.console") as mock:
        yield mock


def test_print_success(mock_console):
    """Test success message printing."""
    message = "Operation successful"
    print_success(message)
    mock_console.print.assert_called_once_with(f"✅ {message}", style="green")


def test_print_error(mock_console):
    """Test error message printing."""
    message = "An error occurred"
    print_error(message)
    mock_console.print.assert_called_once_with(f"❌ {message}", style="bold red")


def test_print_warning(mock_console):
    """Test warning message printing."""
    message = "Warning message"
    print_warning(message)
    mock_console.print.assert_called_once_with(f"⚠️  {message}", style="yellow")


def test_print_info(mock_console):
    """Test info message printing."""
    message = "Information message"
    print_info(message)
    mock_console.print.assert_called_once_with(f"ℹ️  {message}", style="blue")


def test_print_table_empty_data(mock_console):
    """Test table printing with empty data."""
    data = []
    title = "Empty Table"
    print_table(data, title)
    mock_console.print.assert_called_once()
    table = mock_console.print.call_args[0][0]
    assert isinstance(table, Table)
    assert table.title == title


def test_print_table_with_data(mock_console):
    """Test table printing with data."""
    data = [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]
    title = "People"

    print_table(data, title)

    mock_console.print.assert_called_once()
    table = mock_console.print.call_args[0][0]

    assert isinstance(table, Table)
    assert table.title == title

    # Check that the table has the correct columns
    assert len(table.columns) == 2
    assert table.columns[0].header == "name"
    assert table.columns[1].header == "age"
    assert table.columns[0].style == "cyan"
    assert table.columns[1].style == "cyan"


def test_console_instance():
    """Test that console is properly instantiated."""
    from rich.console import Console

    assert isinstance(console, Console)


class TestPrintFunctions:
    """Test print functions with icon parameter."""

    def test_print_success_with_icon(self, mock_console):
        """Test success message printing with icon."""
        message = "Operation successful"
        print_success(message, icon=True)
        mock_console.print.assert_called_once_with(f"✅ {message}", style="green")

    def test_print_success_without_icon(self, mock_console):
        """Test success message printing without icon."""
        message = "Operation successful"
        print_success(message, icon=False)
        mock_console.print.assert_called_once_with(f"{message}", style="green")

    def test_print_success_empty_message(self, mock_console):
        """Test success message with empty message."""
        print_success("")
        mock_console.print.assert_not_called()

    def test_print_success_whitespace_only(self, mock_console):
        """Test success message with whitespace only."""
        print_success("   ")
        mock_console.print.assert_not_called()

    def test_print_error_with_icon(self, mock_console):
        """Test error message printing with icon."""
        message = "An error occurred"
        print_error(message, icon=True)
        mock_console.print.assert_called_once_with(f"❌ {message}", style="bold red")

    def test_print_error_without_icon(self, mock_console):
        """Test error message printing without icon."""
        message = "An error occurred"
        print_error(message, icon=False)
        mock_console.print.assert_called_once_with(f"{message}", style="bold red")

    def test_print_error_empty_message(self, mock_console):
        """Test error message with empty message."""
        print_error("")
        mock_console.print.assert_not_called()

    def test_print_warning_with_icon(self, mock_console):
        """Test warning message printing with icon."""
        message = "Warning message"
        print_warning(message, icon=True)
        mock_console.print.assert_called_once_with(f"⚠️  {message}", style="yellow")

    def test_print_warning_without_icon(self, mock_console):
        """Test warning message printing without icon."""
        message = "Warning message"
        print_warning(message, icon=False)
        mock_console.print.assert_called_once_with(f"{message}", style="yellow")

    def test_print_warning_empty_message(self, mock_console):
        """Test warning message with empty message."""
        print_warning("")
        mock_console.print.assert_not_called()

    def test_print_info_with_icon(self, mock_console):
        """Test info message printing with icon."""
        message = "Information message"
        print_info(message, icon=True)
        mock_console.print.assert_called_once_with(f"ℹ️  {message}", style="blue")

    def test_print_info_without_icon(self, mock_console):
        """Test info message printing without icon."""
        message = "Information message"
        print_info(message, icon=False)
        mock_console.print.assert_called_once_with(f"{message}", style="blue")

    def test_print_info_with_newline(self, mock_console):
        """Test info message starting with newline."""
        message = "\nInformation message"
        print_info(message)
        mock_console.print.assert_called_once_with(message, style="blue")

    def test_print_info_empty_message(self, mock_console):
        """Test info message with empty message."""
        print_info("")
        mock_console.print.assert_called_once_with("", style="blue")


class TestOperationMessages:
    """Test operation-related messages."""

    def test_print_start(self, mock_console):
        """Test start message printing."""
        message = "Starting operation"
        print_start(message)
        mock_console.print.assert_called_once_with(f"🌱 {message}", style="bold blue")

    def test_print_processing(self, mock_console):
        """Test processing message printing."""
        message = "Processing data"
        print_processing(message)
        mock_console.print.assert_called_once_with(f"⚡ {message}", style="cyan")

    def test_print_section(self, mock_console):
        """Test section header printing."""
        title = "Section Title"
        print_section(title)
        mock_console.print.assert_called_once_with(
            f"\n📋 {title}", style="bold magenta"
        )

    def test_print_summary_header(self, mock_console):
        """Test summary header printing."""
        title = "Summary Title"
        print_summary_header(title)
        mock_console.print.assert_called_once_with(f"\n📊 {title}", style="bold blue")

    def test_print_operation_start(self, mock_console):
        """Test operation start message."""
        operation = "import"
        print_operation_start(operation)
        mock_console.print.assert_called_once_with(
            f"🔄 Starting {operation}...", style="blue"
        )

    def test_print_operation_complete_without_details(self, mock_console):
        """Test operation complete message without details."""
        operation = "import"
        print_operation_complete(operation)
        mock_console.print.assert_called_once_with(
            f"✅ {operation} completed", style="green"
        )

    def test_print_operation_complete_with_details(self, mock_console):
        """Test operation complete message with details."""
        operation = "import"
        details = "100 records processed"
        print_operation_complete(operation, details)
        mock_console.print.assert_called_once_with(
            f"✅ {operation} completed - {details}", style="green"
        )


class TestFileAndStatsMessages:
    """Test file processing and statistics messages."""

    def test_print_files_processed_default(self, mock_console):
        """Test files processed message with default file type."""
        count = 5
        print_files_processed(count)
        mock_console.print.assert_called_once_with(
            f"📁 Processed {count} files", style="cyan"
        )

    def test_print_files_processed_custom_type(self, mock_console):
        """Test files processed message with custom file type."""
        count = 3
        file_type = "CSV files"
        print_files_processed(count, file_type)
        mock_console.print.assert_called_once_with(
            f"📁 Processed {count} {file_type}", style="cyan"
        )

    def test_print_duration_seconds(self, mock_console):
        """Test duration printing for seconds."""
        seconds = 45.6
        print_duration(seconds)
        mock_console.print.assert_called_once_with("⏱️  Duration: 45.6s", style="dim")

    def test_print_duration_minutes(self, mock_console):
        """Test duration printing for minutes."""
        seconds = 125.7  # 2 minutes 5 seconds
        print_duration(seconds)
        mock_console.print.assert_called_once_with("⏱️  Duration: 2m 5s", style="dim")

    def test_print_duration_hours(self, mock_console):
        """Test duration printing for hours."""
        seconds = 3725.3  # 1 hour 2 minutes
        print_duration(seconds)
        mock_console.print.assert_called_once_with("⏱️  Duration: 1h 2m", style="dim")

    def test_print_stats(self, mock_console):
        """Test statistics printing."""
        stats = {"total_records": 1000, "success_rate": 95.5, "status": "completed"}
        print_stats(stats)

        # Check that it was called multiple times (header + each stat)
        assert mock_console.print.call_count == 4

        # Check the header call
        mock_console.print.assert_any_call("📈 Statistics:", style="bold cyan")

        # Check individual stat calls
        mock_console.print.assert_any_call("   total_records: 1,000", style="cyan")
        mock_console.print.assert_any_call("   success_rate: 95.5", style="cyan")
        mock_console.print.assert_any_call("   status: completed", style="cyan")


class TestStepMessages:
    """Test step-related messages."""

    def test_print_step_header(self, mock_console):
        """Test step header printing."""
        step_name = "Loading data"
        print_step_header(step_name)
        mock_console.print.assert_called_once_with(
            f"📋 {step_name}...", style="bold cyan"
        )

    def test_print_step_complete_basic(self, mock_console):
        """Test step complete message without count or duration."""
        step_name = "Data loading"
        print_step_complete(step_name)
        mock_console.print.assert_called_once_with(
            f"✅ {step_name} completed", style="green"
        )

    def test_print_step_complete_with_count(self, mock_console):
        """Test step complete message with count."""
        step_name = "Data loading"
        count = 1500
        print_step_complete(step_name, count=count)
        mock_console.print.assert_called_once_with(
            f"✅ {step_name} completed • 1,500 items", style="green"
        )

    def test_print_step_complete_with_duration_seconds(self, mock_console):
        """Test step complete message with duration in seconds."""
        step_name = "Data loading"
        duration = 45.6
        print_step_complete(step_name, duration=duration)
        mock_console.print.assert_called_once_with(
            f"✅ {step_name} completed • 45.6s", style="green"
        )

    def test_print_step_complete_with_duration_minutes(self, mock_console):
        """Test step complete message with duration in minutes."""
        step_name = "Data loading"
        duration = 125.7  # 2 minutes 5 seconds
        print_step_complete(step_name, duration=duration)
        mock_console.print.assert_called_once_with(
            f"✅ {step_name} completed • 2m 5s", style="green"
        )

    def test_print_step_complete_with_count_and_duration(self, mock_console):
        """Test step complete message with both count and duration."""
        step_name = "Data loading"
        count = 1500
        duration = 45.6
        print_step_complete(step_name, count=count, duration=duration)
        mock_console.print.assert_called_once_with(
            f"✅ {step_name} completed • 1,500 items • 45.6s", style="green"
        )

    def test_print_step_progress(self, mock_console):
        """Test step progress printing."""
        step_name = "Processing files"
        current = 75
        total = 100
        print_step_progress(step_name, current, total)
        mock_console.print.assert_called_once_with(
            f"  {step_name}: 75/100 (75.0%)", style="cyan"
        )

    def test_print_step_progress_zero_total(self, mock_console):
        """Test step progress printing with zero total."""
        step_name = "Processing files"
        current = 0
        total = 0
        print_step_progress(step_name, current, total)
        mock_console.print.assert_called_once_with(
            f"  {step_name}: 0/0 (0.0%)", style="cyan"
        )


class TestLinkingMessages:
    """Test linking status messages."""

    def test_print_linking_status(self, mock_console):
        """Test linking status printing."""
        total = 100
        linked = 85
        failed = 15
        link_type = "samples"

        print_linking_status(total, linked, failed, link_type)

        # Should be called once with a Table
        mock_console.print.assert_called_once()
        table = mock_console.print.call_args[0][0]
        assert isinstance(table, Table)
        assert table.title == "Samples Link Status"

    def test_print_linking_status_default_type(self, mock_console):
        """Test linking status printing with default link type."""
        total = 50
        linked = 40
        failed = 10

        print_linking_status(total, linked, failed)

        # Should be called once with a Table
        mock_console.print.assert_called_once()
        table = mock_console.print.call_args[0][0]
        assert isinstance(table, Table)
        assert table.title == "Items Link Status"

    def test_print_unlinked_samples_empty(self, mock_console):
        """Test unlinked samples printing with empty list."""
        samples = []
        print_unlinked_samples(samples)
        mock_console.print.assert_not_called()

    def test_print_unlinked_samples_few_items(self, mock_console):
        """Test unlinked samples printing with few items."""
        samples = ["sample1", "sample2", "sample3"]
        sample_type = "trees"

        print_unlinked_samples(samples, sample_type)

        mock_console.print.assert_called_once()
        panel = mock_console.print.call_args[0][0]
        assert isinstance(panel, Panel)
        assert panel.title == "Sample of Unlinked Trees"

    def test_print_unlinked_samples_many_items(self, mock_console):
        """Test unlinked samples printing with many items."""
        samples = [f"sample{i}" for i in range(10)]

        print_unlinked_samples(samples)

        mock_console.print.assert_called_once()
        panel = mock_console.print.call_args[0][0]
        assert isinstance(panel, Panel)
        assert "... and 5 more" in panel.renderable


class TestImportAndFileMessages:
    """Test import and file processing messages."""

    def test_print_import_result_without_details(self, mock_console):
        """Test import result message without details."""
        file_path = "/path/to/file.csv"
        count = 500
        data_type = "records"

        print_import_result(file_path, count, data_type)
        expected = f"✅ 500 records imported from {file_path}"
        mock_console.print.assert_called_once_with(expected, style="green")

    def test_print_import_result_with_details(self, mock_console):
        """Test import result message with details."""
        file_path = "/path/to/file.csv"
        count = 500
        data_type = "records"
        details = "All records valid"

        print_import_result(file_path, count, data_type, details)
        expected = f"✅ 500 records imported from {file_path}. {details}"
        mock_console.print.assert_called_once_with(expected, style="green")

    def test_print_file_processed_default_action(self, mock_console):
        """Test file processed message with default action."""
        file_path = "/path/to/file.geojson"
        count = 250

        print_file_processed(file_path, count)
        expected = f"📁 250 features processed from {file_path}"
        mock_console.print.assert_called_once_with(expected, style="cyan")

    def test_print_file_processed_custom_action(self, mock_console):
        """Test file processed message with custom action."""
        file_path = "/path/to/file.geojson"
        count = 250
        action = "imported"

        print_file_processed(file_path, count, action)
        expected = f"📁 250 features {action} from {file_path}"
        mock_console.print.assert_called_once_with(expected, style="cyan")


class TestUtilityFunctions:
    """Test utility functions."""

    def test_format_file_size_bytes(self):
        """Test file size formatting for bytes."""
        result = format_file_size(500)
        assert result == "500.0 B"

    def test_format_file_size_kb(self):
        """Test file size formatting for kilobytes."""
        result = format_file_size(1536)  # 1.5 KB
        assert result == "1.5 KB"

    def test_format_file_size_mb(self):
        """Test file size formatting for megabytes."""
        result = format_file_size(1572864)  # 1.5 MB
        assert result == "1.5 MB"

    def test_format_file_size_gb(self):
        """Test file size formatting for gigabytes."""
        result = format_file_size(1610612736)  # 1.5 GB
        assert result == "1.5 GB"

    def test_format_file_size_tb(self):
        """Test file size formatting for terabytes."""
        result = format_file_size(1649267441664)  # 1.5 TB
        assert result == "1.5 TB"

    def test_format_number(self):
        """Test number formatting with thousand separators."""
        assert format_number(1000) == "1,000"
        assert format_number(1234567) == "1,234,567"
        assert format_number(100) == "100"


class TestMetricsMessages:
    """Test metrics-related messages."""

    def test_print_metrics_summary(self, mock_console):
        """Test metrics summary printing."""
        operation_name = "Import"
        metrics_lines = [
            "Files processed: 5",
            "Records imported: 1,000",
            "Duration: 45.6s",
        ]

        print_metrics_summary(operation_name, metrics_lines)

        # Should print header + each line
        assert mock_console.print.call_count == 4
        mock_console.print.assert_any_call("\n📊 Import Summary:", style="bold blue")
        mock_console.print.assert_any_call("   Files processed: 5", style="cyan")
        mock_console.print.assert_any_call("   Records imported: 1,000", style="cyan")
        mock_console.print.assert_any_call("   Duration: 45.6s", style="cyan")

    def test_print_metrics_summary_with_empty_lines(self, mock_console):
        """Test metrics summary printing with empty lines and icons."""
        operation_name = "Export"
        metrics_lines = [
            "Files created: 3",
            "",  # Empty line should be skipped
            "✅",  # Icon-only line should be skipped
            "Duration: 30.2s",
        ]

        print_metrics_summary(operation_name, metrics_lines)

        # Should print header + only valid lines
        assert mock_console.print.call_count == 3
        mock_console.print.assert_any_call("\n📊 Export Summary:", style="bold blue")
        mock_console.print.assert_any_call("   Files created: 3", style="cyan")
        mock_console.print.assert_any_call("   Duration: 30.2s", style="cyan")

    @patch("niamoto.cli.utils.metrics.MetricsFormatter")
    def test_print_operation_metrics_import(self, mock_formatter_class, mock_console):
        """Test operation metrics printing for import."""
        # Mock the formatter
        mock_formatter_class.format_import_metrics.return_value = [
            "Files: 5",
            "Records: 1000",
        ]

        # Mock metrics object
        mock_metrics = MagicMock()

        print_operation_metrics(mock_metrics, "import")

        # Should call the import formatter
        mock_formatter_class.format_import_metrics.assert_called_once_with(mock_metrics)

        # Should print summary
        assert mock_console.print.call_count == 3  # Header + 2 lines
        mock_console.print.assert_any_call("\n📊 Import Summary:", style="bold blue")

    @patch("niamoto.cli.utils.metrics.MetricsFormatter")
    def test_print_operation_metrics_unknown_type(
        self, mock_formatter_class, mock_console
    ):
        """Test operation metrics printing for unknown type."""
        # Mock metrics object with attributes for fallback
        mock_metrics = MagicMock()
        mock_metrics.duration.total_seconds.return_value = 45.6
        mock_metrics.errors = []
        mock_metrics.warnings = ["Warning 1"]

        print_operation_metrics(mock_metrics, "unknown")

        # Should not call any specific formatter
        mock_formatter_class.format_import_metrics.assert_not_called()
        mock_formatter_class.format_transform_metrics.assert_not_called()
        mock_formatter_class.format_export_metrics.assert_not_called()

        # Should use fallback and print warning
        assert mock_console.print.call_count >= 2
