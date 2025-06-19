"""Test metrics collection and formatting utilities."""

from datetime import datetime, timedelta
from unittest.mock import patch

from niamoto.cli.utils.metrics import (
    OperationMetrics,
    MetricsCollector,
    MetricsFormatter,
)


class TestOperationMetrics:
    """Test OperationMetrics class."""

    def test_init_default(self):
        """Test OperationMetrics initialization with defaults."""
        metrics = OperationMetrics("test_operation")
        assert metrics.operation_type == "test_operation"
        assert metrics.end_time is None
        assert metrics.metrics == {}
        assert metrics.errors == []
        assert metrics.warnings == []
        assert isinstance(metrics.start_time, datetime)

    def test_init_with_custom_start_time(self):
        """Test OperationMetrics initialization with custom start time."""
        start_time = datetime(2023, 1, 1, 12, 0, 0)
        metrics = OperationMetrics("test_operation", start_time=start_time)
        assert metrics.start_time == start_time

    def test_add_metric(self):
        """Test adding metrics."""
        metrics = OperationMetrics("test")
        metrics.add_metric("key1", "value1")
        metrics.add_metric("key2", 42)

        assert metrics.metrics["key1"] == "value1"
        assert metrics.metrics["key2"] == 42

    def test_add_count_new_key(self):
        """Test adding count for new key."""
        metrics = OperationMetrics("test")
        metrics.add_count("files_processed", 5)

        assert metrics.metrics["files_processed"] == 5

    def test_add_count_existing_key(self):
        """Test adding count for existing key."""
        metrics = OperationMetrics("test")
        metrics.add_count("files_processed", 5)
        metrics.add_count("files_processed", 3)

        assert metrics.metrics["files_processed"] == 8

    def test_add_error(self):
        """Test adding error messages."""
        metrics = OperationMetrics("test")
        metrics.add_error("Error 1")
        metrics.add_error("Error 2")

        assert len(metrics.errors) == 2
        assert "Error 1" in metrics.errors
        assert "Error 2" in metrics.errors

    def test_add_warning(self):
        """Test adding warning messages."""
        metrics = OperationMetrics("test")
        metrics.add_warning("Warning 1")
        metrics.add_warning("Warning 2")

        assert len(metrics.warnings) == 2
        assert "Warning 1" in metrics.warnings
        assert "Warning 2" in metrics.warnings

    def test_finish(self):
        """Test finishing operation."""
        metrics = OperationMetrics("test")
        assert metrics.end_time is None

        metrics.finish()
        assert isinstance(metrics.end_time, datetime)
        assert metrics.end_time > metrics.start_time

    def test_duration_not_finished(self):
        """Test duration calculation when operation not finished."""
        start_time = datetime(2023, 1, 1, 12, 0, 0)
        metrics = OperationMetrics("test", start_time=start_time)

        with patch("niamoto.cli.utils.metrics.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 30)
            duration = metrics.duration

        assert duration == timedelta(seconds=30)

    def test_duration_finished(self):
        """Test duration calculation when operation finished."""
        start_time = datetime(2023, 1, 1, 12, 0, 0)
        end_time = datetime(2023, 1, 1, 12, 0, 45)

        metrics = OperationMetrics("test", start_time=start_time)
        metrics.end_time = end_time

        assert metrics.duration == timedelta(seconds=45)

    def test_get_summary(self):
        """Test getting operation summary."""
        start_time = datetime(2023, 1, 1, 12, 0, 0)
        metrics = OperationMetrics("test", start_time=start_time)
        metrics.add_metric("files", 5)
        metrics.add_error("Error 1")
        metrics.add_warning("Warning 1")
        metrics.add_warning("Warning 2")

        summary = metrics.get_summary()

        assert summary["operation_type"] == "test"
        assert isinstance(summary["duration"], timedelta)
        assert summary["metrics"] == {"files": 5}
        assert summary["errors_count"] == 1
        assert summary["warnings_count"] == 2
        assert summary["errors"] == ["Error 1"]
        assert summary["warnings"] == ["Warning 1", "Warning 2"]


class TestMetricsCollector:
    """Test MetricsCollector class."""

    def test_parse_import_result_taxonomy(self):
        """Test parsing taxonomy import results."""
        result = "1234 taxons extracted and imported with 45 families, 150 genera, 800 species"
        metrics = MetricsCollector.parse_import_result(result)

        assert metrics.operation_type == "import"
        assert metrics.metrics["taxonomy"] == 1234
        assert metrics.metrics["families"] == 45
        assert metrics.metrics["genera"] == 150
        assert metrics.metrics["species"] == 800

    def test_parse_import_result_occurrences(self):
        """Test parsing occurrences import results."""
        result = "Total occurrences imported: 5678 with linked=5000 unlinked=678"
        metrics = MetricsCollector.parse_import_result(result)

        assert metrics.metrics["occurrences"] == 5678
        assert metrics.metrics["linked_occurrences"] == 5000
        assert metrics.metrics["unlinked_occurrences"] == 678

    def test_parse_import_result_plots(self):
        """Test parsing plots import results."""
        result = "Successfully imported 45 plots from the dataset"
        metrics = MetricsCollector.parse_import_result(result)

        assert metrics.metrics["plots"] == 45

    def test_parse_import_result_shapes(self):
        """Test parsing shapes import results."""
        result = "123 processed, 100 added, 23 updated shapes imported"
        metrics = MetricsCollector.parse_import_result(result)

        assert metrics.metrics["shapes"] == 123

    def test_parse_import_result_plot_locations(self):
        """Test parsing plot locations."""
        result = "45 plot locations processed successfully"
        metrics = MetricsCollector.parse_import_result(result)

        assert metrics.metrics["plots"] == 45

    def test_parse_import_result_fallback(self):
        """Test fallback parsing for generic results."""
        result = "Successfully imported 999 items into the database"
        metrics = MetricsCollector.parse_import_result(result)

        assert metrics.metrics["total_items"] == 999

    def test_parse_import_result_no_matches(self):
        """Test parsing when no patterns match."""
        result = "Operation completed successfully"
        metrics = MetricsCollector.parse_import_result(result)

        assert metrics.metrics == {}

    def test_parse_import_result_custom_operation_type(self):
        """Test parsing with custom operation type."""
        result = "100 taxons imported"
        metrics = MetricsCollector.parse_import_result(result, "custom_import")

        assert metrics.operation_type == "custom_import"
        assert metrics.metrics["taxonomy"] == 100

    def test_create_transform_metrics(self):
        """Test creating transform metrics from processing results."""
        groups_processed = {
            "forest": {
                "total_items": 1000,
                "widgets_generated": 5,
                "start_time": datetime(2023, 1, 1, 12, 0, 0),
                "end_time": datetime(2023, 1, 1, 12, 0, 30),
            },
            "shrubland": {
                "total_items": 500,
                "widgets_generated": 3,
                "start_time": datetime(2023, 1, 1, 12, 0, 10),
                "end_time": datetime(2023, 1, 1, 12, 0, 40),
            },
        }

        metrics = MetricsCollector.create_transform_metrics(groups_processed)

        assert metrics.operation_type == "transform"
        assert metrics.metrics["forest_items"] == 1000
        assert metrics.metrics["forest_widgets"] == 5
        assert metrics.metrics["shrubland_items"] == 500
        assert metrics.metrics["shrubland_widgets"] == 3
        assert metrics.metrics["total_items_processed"] == 1500
        assert metrics.metrics["total_widgets_generated"] == 8
        assert metrics.metrics["groups_count"] == 2
        assert metrics.start_time == datetime(2023, 1, 1, 12, 0, 0)
        assert metrics.end_time == datetime(2023, 1, 1, 12, 0, 40)

    def test_create_transform_metrics_empty(self):
        """Test creating transform metrics with empty results."""
        groups_processed = {}
        metrics = MetricsCollector.create_transform_metrics(groups_processed)

        assert metrics.operation_type == "transform"
        assert metrics.metrics["total_items_processed"] == 0
        assert metrics.metrics["total_widgets_generated"] == 0
        assert metrics.metrics["groups_count"] == 0

    def test_create_export_metrics(self):
        """Test creating export metrics from export results."""
        export_results = {
            "website": {
                "files_generated": 25,
                "errors": 0,
                "start_time": datetime(2023, 1, 1, 12, 0, 0),
                "duration": "30.5s",
            },
            "api": {
                "files_generated": 10,
                "errors": 2,
                "start_time": datetime(2023, 1, 1, 12, 0, 15),
            },
        }

        metrics = MetricsCollector.create_export_metrics(export_results)

        assert metrics.operation_type == "export"
        assert metrics.metrics["website_files"] == 25
        assert metrics.metrics["api_files"] == 10
        assert metrics.metrics["api_errors"] == 2
        assert metrics.metrics["total_files_generated"] == 35
        assert metrics.metrics["successful_targets"] == 1  # Only website succeeded
        assert metrics.metrics["targets_count"] == 2

    def test_create_export_metrics_simple_completion(self):
        """Test creating export metrics with simple completion status."""
        export_results = {"target1": "completed", "target2": True}

        metrics = MetricsCollector.create_export_metrics(export_results)

        assert metrics.metrics["successful_targets"] == 2
        assert metrics.metrics["targets_count"] == 2
        assert metrics.metrics["total_files_generated"] == 0

    def test_create_export_metrics_duration_parsing_error(self):
        """Test creating export metrics with invalid duration format."""
        export_results = {
            "target": {
                "files_generated": 5,
                "start_time": datetime(2023, 1, 1, 12, 0, 0),
                "duration": "invalid_format",
            }
        }

        metrics = MetricsCollector.create_export_metrics(export_results)

        # Should not crash and should still process other data
        assert metrics.metrics["target_files"] == 5


class TestMetricsFormatter:
    """Test MetricsFormatter class."""

    def test_format_duration_seconds(self):
        """Test formatting duration in seconds."""
        duration = timedelta(seconds=45)
        result = MetricsFormatter.format_duration(duration)
        assert result == "45s"

    def test_format_duration_minutes(self):
        """Test formatting duration in minutes."""
        duration = timedelta(seconds=125)  # 2m 5s
        result = MetricsFormatter.format_duration(duration)
        assert result == "2m 5s"

    def test_format_duration_hours(self):
        """Test formatting duration in hours."""
        duration = timedelta(seconds=3725)  # 1h 2m
        result = MetricsFormatter.format_duration(duration)
        assert result == "1h 2m"

    def test_format_file_size_bytes(self):
        """Test formatting file size in bytes."""
        result = MetricsFormatter.format_file_size(500)
        assert result == "500.0 B"

    def test_format_file_size_kb(self):
        """Test formatting file size in kilobytes."""
        result = MetricsFormatter.format_file_size(1536)  # 1.5 KB
        assert result == "1.5 KB"

    def test_format_file_size_mb(self):
        """Test formatting file size in megabytes."""
        result = MetricsFormatter.format_file_size(1572864)  # 1.5 MB
        assert result == "1.5 MB"

    def test_format_file_size_gb(self):
        """Test formatting file size in gigabytes."""
        result = MetricsFormatter.format_file_size(1610612736)  # 1.5 GB
        assert result == "1.5 GB"

    def test_format_file_size_tb(self):
        """Test formatting file size in terabytes."""
        result = MetricsFormatter.format_file_size(1649267441664)  # 1.5 TB
        assert result == "1.5 TB"

    def test_format_number(self):
        """Test formatting numbers with thousand separators."""
        assert MetricsFormatter.format_number(1000) == "1,000"
        assert MetricsFormatter.format_number(1234567) == "1,234,567"
        assert MetricsFormatter.format_number(100) == "100"

    def test_format_import_metrics_taxonomy(self):
        """Test formatting import metrics with taxonomy data."""
        metrics = OperationMetrics("import")
        metrics.add_metric("taxonomy", 1000)
        metrics.add_metric("families", 45)
        metrics.add_metric("genera", 150)
        metrics.add_metric("species", 800)
        metrics.finish()

        lines = MetricsFormatter.format_import_metrics(metrics)

        # Check that it includes duration, taxonomy data, and success summary
        duration_line = next((line for line in lines if "Duration:" in line), None)
        assert duration_line is not None

        taxonomy_line = next((line for line in lines if "Taxonomy:" in line), None)
        assert taxonomy_line is not None
        assert "1,000 taxa" in taxonomy_line
        assert "45 families" in taxonomy_line

        success_line = next((line for line in lines if "Success:" in line), None)
        assert success_line is not None

    def test_format_import_metrics_occurrences_with_links(self):
        """Test formatting import metrics with occurrence link data."""
        metrics = OperationMetrics("import")
        metrics.add_metric("occurrences", 1000)
        metrics.add_metric("linked_occurrences", 850)
        metrics.add_metric("unlinked_occurrences", 150)
        metrics.finish()

        lines = MetricsFormatter.format_import_metrics(metrics)

        occurrence_line = next((line for line in lines if "Occurrences:" in line), None)
        assert occurrence_line is not None
        assert "1,000" in occurrence_line
        assert "850 linked" in occurrence_line
        assert "85.0%" in occurrence_line
        assert "150 unlinked" in occurrence_line

    def test_format_import_metrics_fallback(self):
        """Test formatting import metrics with fallback total_items."""
        metrics = OperationMetrics("import")
        metrics.add_metric("total_items", 500)
        metrics.finish()

        lines = MetricsFormatter.format_import_metrics(metrics)

        items_line = next((line for line in lines if "Items:" in line), None)
        assert items_line is not None
        assert "500 records" in items_line

    def test_format_import_metrics_no_data(self):
        """Test formatting import metrics with no data."""
        metrics = OperationMetrics("import")
        metrics.finish()

        lines = MetricsFormatter.format_import_metrics(metrics)

        fallback_line = next(
            (line for line in lines if "metrics unavailable" in line), None
        )
        assert fallback_line is not None

    def test_format_import_metrics_with_errors_warnings(self):
        """Test formatting import metrics with errors and warnings."""
        metrics = OperationMetrics("import")
        metrics.add_metric("taxonomy", 100)
        metrics.add_error("Error 1")
        metrics.add_error("Error 2")
        metrics.add_warning("Warning 1")
        metrics.finish()

        lines = MetricsFormatter.format_import_metrics(metrics)

        error_line = next((line for line in lines if "Errors:" in line), None)
        assert error_line is not None
        assert "2 issues" in error_line

        warning_line = next((line for line in lines if "Warnings:" in line), None)
        assert warning_line is not None
        assert "1 warnings" in warning_line

    def test_format_transform_metrics(self):
        """Test formatting transform metrics."""
        metrics = OperationMetrics("transform")
        metrics.add_metric("forest_items", 1000)
        metrics.add_metric("forest_widgets", 5)
        metrics.add_metric("shrubland_items", 500)
        metrics.add_metric("shrubland_widgets", 3)
        metrics.add_metric("total_items_processed", 1500)
        metrics.add_metric("total_widgets_generated", 8)
        metrics.add_metric("groups_count", 2)
        metrics.start_time = datetime(2023, 1, 1, 12, 0, 0)
        metrics.end_time = datetime(2023, 1, 1, 12, 0, 30)

        lines = MetricsFormatter.format_transform_metrics(metrics)

        # Check duration
        duration_line = next((line for line in lines if "Duration:" in line), None)
        assert duration_line is not None

        # Check groups processed
        groups_line = next(
            (line for line in lines if "Groups Processed:" in line), None
        )
        assert groups_line is not None

        # Check individual group data
        forest_line = next((line for line in lines if "Forest:" in line), None)
        assert forest_line is not None
        assert "1,000 items" in forest_line
        assert "5 widgets" in forest_line

        # Check totals
        total_line = next((line for line in lines if "Total Widgets:" in line), None)
        assert total_line is not None
        assert "8 widgets" in total_line

        # Check performance
        performance_line = next(
            (line for line in lines if "Performance:" in line), None
        )
        assert performance_line is not None
        assert "items/second" in performance_line

    def test_format_transform_metrics_no_performance(self):
        """Test formatting transform metrics without performance data."""
        metrics = OperationMetrics("transform")
        metrics.add_metric("total_widgets_generated", 5)
        metrics.start_time = datetime(2023, 1, 1, 12, 0, 0)
        metrics.end_time = datetime(2023, 1, 1, 12, 0, 0)  # Zero duration

        lines = MetricsFormatter.format_transform_metrics(metrics)

        # Should not include performance line
        performance_line = next(
            (line for line in lines if "Performance:" in line), None
        )
        assert performance_line is None

    def test_format_export_metrics(self):
        """Test formatting export metrics."""
        metrics = OperationMetrics("export")
        metrics.add_metric("website_files", 25)
        metrics.add_metric("api_files", 10)
        metrics.add_metric("api_errors", 2)
        metrics.add_metric("total_files_generated", 35)
        metrics.add_metric("successful_targets", 1)
        metrics.add_metric("targets_count", 2)
        metrics.finish()

        lines = MetricsFormatter.format_export_metrics(metrics)

        # Check duration
        duration_line = next((line for line in lines if "Duration:" in line), None)
        assert duration_line is not None

        # Check targets section
        targets_line = next((line for line in lines if "Targets:" in line), None)
        assert targets_line is not None

        # Check individual targets
        website_line = next((line for line in lines if "website:" in line), None)
        assert website_line is not None
        assert "25 files" in website_line

        api_line = next((line for line in lines if "api:" in line), None)
        assert api_line is not None
        assert "10 files" in api_line
        assert "2 errors" in api_line

        # Check total
        total_line = next((line for line in lines if "Total:" in line), None)
        assert total_line is not None
        assert "35 files" in total_line

        # Check success rate
        success_line = next((line for line in lines if "Success Rate:" in line), None)
        assert success_line is not None
        assert "50%" in success_line

    def test_format_export_metrics_all_successful(self):
        """Test formatting export metrics when all targets successful."""
        metrics = OperationMetrics("export")
        metrics.add_metric("target1_files", 10)
        metrics.add_metric("target2_files", 5)
        metrics.add_metric("successful_targets", 2)
        metrics.add_metric("targets_count", 2)
        metrics.finish()

        lines = MetricsFormatter.format_export_metrics(metrics)

        success_line = next((line for line in lines if "Success Rate:" in line), None)
        assert success_line is not None
        assert "100%" in success_line

    def test_format_export_metrics_no_success_rate(self):
        """Test formatting export metrics without success rate data."""
        metrics = OperationMetrics("export")
        metrics.add_metric("total_files_generated", 10)
        metrics.finish()

        lines = MetricsFormatter.format_export_metrics(metrics)

        # Should not include success rate line
        success_line = next((line for line in lines if "Success Rate:" in line), None)
        assert success_line is None
