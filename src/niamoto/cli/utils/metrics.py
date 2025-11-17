"""
Metrics collection and display system for Niamoto CLI operations.
Provides standardized metrics collection and formatted display for import, transform, and export operations.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import re
from niamoto.common.utils.emoji import emoji


@dataclass
class OperationMetrics:
    """Container for operation-specific metrics."""

    operation_type: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_metric(self, key: str, value: Any) -> None:
        """Add a metric value."""
        self.metrics[key] = value

    def add_count(self, key: str, count: int) -> None:
        """Add or increment a count metric."""
        if key in self.metrics:
            self.metrics[key] += count
        else:
            self.metrics[key] = count

    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)

    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)

    def finish(self) -> None:
        """Mark the operation as finished."""
        self.end_time = datetime.now()

    @property
    def duration(self) -> timedelta:
        """Get the operation duration."""
        end = self.end_time or datetime.now()
        return end - self.start_time

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all metrics."""
        return {
            "operation_type": self.operation_type,
            "duration": self.duration,
            "metrics": self.metrics.copy(),
            "errors_count": len(self.errors),
            "warnings_count": len(self.warnings),
            "errors": self.errors.copy(),
            "warnings": self.warnings.copy(),
        }


class MetricsCollector:
    """Collects and processes metrics from Niamoto operations."""

    @staticmethod
    def parse_import_result(
        result: str, operation_type: str = "import"
    ) -> OperationMetrics:
        """Parse import result strings to extract metrics."""
        metrics = OperationMetrics(operation_type)

        # Enhanced patterns for real Niamoto import messages
        patterns = {
            # Taxonomy patterns - matches "1234 taxons imported from file.csv"
            "taxonomy": [
                r"(\d+)\s+taxons?\s+extracted\s+and\s+imported",
                r"(\d+)\s+taxons?\s+imported",
                r"(\d+)\s+taxa?\s+imported",
                r"Successfully imported (\d+) taxa",
            ],
            # Occurrence patterns - matches "Total occurrences imported: 5678"
            "occurrences": [
                r"Total occurrences imported:\s*(\d+)",
                r"(\d+)\s+occurrences?\s+imported",
                r"Successfully imported (\d+) occurrences",
            ],
            # Plot patterns - need to extract from various plot messages
            "plots": [
                r"(\d+)\s+plots?\s+imported",
                r"Successfully imported (\d+) plots",
                r"(\d+)\s+plots?\s+processed",
            ],
            # Shape patterns
            "shapes": [
                r"(\d+)\s+shapes?\s+imported",
                r"Successfully imported (\d+) shapes",
                r"(\d+)\s+shape files?\s+imported",
                r"(\d+)\s+processed,\s+\d+\s+added,\s+\d+\s+updated",
            ],
            # Detail patterns for taxonomy
            "families": [r"(\d+)\s+families"],
            "genera": [r"(\d+)\s+genera"],
            "species": [r"(\d+)\s+species"],
            # Link statistics for occurrences
            "linked_occurrences": [r"linked=(\d+)"],
            "unlinked_occurrences": [r"unlinked=(\d+)"],
        }

        # Extract numbers from the result string using multiple patterns
        for category, pattern_list in patterns.items():
            for pattern in pattern_list:
                matches = re.findall(pattern, result, re.IGNORECASE)
                if matches:
                    # Take the first match found
                    number = int(matches[0]) if matches[0] else 0
                    if number > 0:
                        metrics.add_metric(category, number)
                        break  # Stop after first successful pattern match for this category

        # Special handling for plot results that may have complex messages
        if "plots" not in metrics.metrics:
            # Try to extract plot count from messages like "45 plot locations processed"
            plot_patterns = [
                r"(\d+)\s+plot\s+locations?\s+processed",
                r"(\d+)\s+plots?\s+processed",
                r"imported\s+(\d+)\s+plots?",
            ]
            for pattern in plot_patterns:
                matches = re.findall(pattern, result, re.IGNORECASE)
                if matches:
                    metrics.add_metric("plots", int(matches[0]))
                    break

        # If no specific categories found, try to extract any significant number
        if not metrics.metrics:
            # Look for patterns like "imported 123" or "processed 456"
            fallback_patterns = [
                r"imported\s+(\d+)",
                r"processed\s+(\d+)",
                r"total\s*:?\s*(\d+)",
            ]
            for pattern in fallback_patterns:
                matches = re.findall(pattern, result, re.IGNORECASE)
                if matches:
                    metrics.add_metric("total_items", int(matches[0]))
                    break

        return metrics

    @staticmethod
    def create_transform_metrics(groups_processed: Dict[str, Any]) -> OperationMetrics:
        """Create transform metrics from processing results."""
        metrics = OperationMetrics("transform")

        total_items = 0
        total_widgets = 0
        earliest_start = None
        latest_end = None

        for group_name, group_stats in groups_processed.items():
            items = group_stats.get("total_items", 0)
            widgets_generated = group_stats.get("widgets_generated", 0)

            # Track timing from group results
            start_time = group_stats.get("start_time")
            if start_time and (earliest_start is None or start_time < earliest_start):
                earliest_start = start_time

            end_time = group_stats.get("end_time")
            if end_time and (latest_end is None or end_time > latest_end):
                latest_end = end_time

            metrics.add_metric(f"{group_name}_items", items)
            metrics.add_metric(f"{group_name}_widgets", widgets_generated)

            total_items += items
            total_widgets += widgets_generated

        # Set timing if we found any
        if earliest_start:
            metrics.start_time = earliest_start
        if latest_end:
            metrics.end_time = latest_end

        metrics.add_metric("total_items_processed", total_items)
        metrics.add_metric("total_widgets_generated", total_widgets)
        metrics.add_metric("groups_count", len(groups_processed))

        return metrics

    @staticmethod
    def create_export_metrics(export_results: Dict[str, Any]) -> OperationMetrics:
        """Create export metrics from export results."""
        metrics = OperationMetrics("export")

        total_files = 0
        successful_targets = 0
        earliest_start = None
        latest_end = None

        for target_name, target_results in export_results.items():
            if isinstance(target_results, dict):
                files = target_results.get("files_generated", 0)
                errors = target_results.get("errors", 0)

                # Track timing from target results
                start_time = target_results.get("start_time")
                if start_time and (
                    earliest_start is None or start_time < earliest_start
                ):
                    earliest_start = start_time

                # For end time, check if we have duration info
                if "duration" in target_results and start_time:
                    # Duration is a string like "2.3s", parse it
                    duration_str = target_results["duration"]
                    try:
                        # Parse duration like "2.3s"
                        import re

                        match = re.match(r"(\d+\.?\d*)s", duration_str)
                        if match:
                            from datetime import timedelta

                            duration_seconds = float(match.group(1))
                            end_time = start_time + timedelta(seconds=duration_seconds)
                            if latest_end is None or end_time > latest_end:
                                latest_end = end_time
                    except (ValueError, AttributeError):
                        pass

                metrics.add_metric(f"{target_name}_files", files)
                if errors == 0:
                    successful_targets += 1
                else:
                    metrics.add_metric(f"{target_name}_errors", errors)

                total_files += files
            else:
                # Simple completion
                successful_targets += 1

        # Set timing if we found any
        if earliest_start:
            metrics.start_time = earliest_start
        if latest_end:
            metrics.end_time = latest_end

        metrics.add_metric("total_files_generated", total_files)
        metrics.add_metric("successful_targets", successful_targets)
        metrics.add_metric("targets_count", len(export_results))

        return metrics


class MetricsFormatter:
    """Formats metrics for console display."""

    @staticmethod
    def format_duration(duration: timedelta) -> str:
        """Format duration in a human-readable way."""
        total_seconds = int(duration.total_seconds())

        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """Format file size in human-readable units."""
        size = float(size_bytes)
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    @staticmethod
    def format_number(number: int) -> str:
        """Format large numbers with thousand separators."""
        return f"{number:,}"

    @staticmethod
    def format_import_metrics(metrics: OperationMetrics) -> List[str]:
        """Format import metrics for display."""
        lines = []

        # Duration
        lines.append(
            f"{emoji('⏱', '[T]')}  Duration: {MetricsFormatter.format_duration(metrics.duration)}"
        )

        # Data imported section - only show if we have data
        data_items = []

        # Taxonomy info
        if "taxonomy" in metrics.metrics:
            taxa_count = metrics.metrics["taxonomy"]
            detail_parts = []
            if "families" in metrics.metrics:
                detail_parts.append(f"{metrics.metrics['families']} families")
            if "genera" in metrics.metrics:
                detail_parts.append(f"{metrics.metrics['genera']} genera")
            if "species" in metrics.metrics:
                detail_parts.append(f"{metrics.metrics['species']} species")

            detail = f" ({', '.join(detail_parts)})" if detail_parts else ""
            data_items.append(
                f"   • Taxonomy: {MetricsFormatter.format_number(taxa_count)} taxa{detail}"
            )

        # Other data types
        for key in ["occurrences", "plots", "shapes"]:
            if key in metrics.metrics:
                count = metrics.metrics[key]
                display_name = key.capitalize()

                # Add link statistics for occurrences
                if key == "occurrences" and "linked_occurrences" in metrics.metrics:
                    linked = metrics.metrics["linked_occurrences"]
                    unlinked = metrics.metrics.get("unlinked_occurrences", 0)
                    total = linked + unlinked
                    linked_percent = (
                        f"{linked / total * 100:.1f}%" if total > 0 else "0%"
                    )
                    link_info = (
                        f" ({linked:,} linked {linked_percent}, {unlinked:,} unlinked)"
                    )
                    data_items.append(
                        f"   • {display_name}: {MetricsFormatter.format_number(count)}{link_info}"
                    )
                else:
                    data_items.append(
                        f"   • {display_name}: {MetricsFormatter.format_number(count)}"
                    )

        # Check for any unrecognized data under 'total_items'
        if "total_items" in metrics.metrics and not data_items:
            total_items = metrics.metrics["total_items"]
            data_items.append(
                f"   • Items: {MetricsFormatter.format_number(total_items)} records"
            )

        # Only add the section header if we have data to show
        if data_items:
            lines.append(f"{emoji('📊', '[=]')} Data Imported:")
            lines.extend(data_items)

            # Totals
            total_success = sum(
                v
                for k, v in metrics.metrics.items()
                if k in ["taxonomy", "occurrences", "plots", "shapes", "total_items"]
            )
            if total_success > 0:
                lines.append(
                    f"{emoji('✅', '[OK]')} Success: {MetricsFormatter.format_number(total_success)} records imported"
                )
        else:
            # Fallback if no specific data was parsed
            lines.append(f"{emoji('📊', '[=]')} Import completed (metrics unavailable)")

        # Errors and warnings
        if metrics.errors:
            lines.append(
                f"{emoji('❌', '[X]')} Errors: {len(metrics.errors)} issues encountered"
            )
        if metrics.warnings:
            lines.append(
                f"{emoji('⚠', '[!]')}  Warnings: {len(metrics.warnings)} warnings"
            )

        return lines

    @staticmethod
    def format_transform_metrics(metrics: OperationMetrics) -> List[str]:
        """Format transform metrics for display."""
        lines = []

        # Duration
        lines.append(
            f"{emoji('⏱', '[T]')}  Duration: {MetricsFormatter.format_duration(metrics.duration)}"
        )

        # Groups processed
        lines.append(f"{emoji('🔄', '[>]')} Groups Processed:")

        # Process each group
        group_metrics: Dict[str, Dict[str, int]] = {}
        for key, value in metrics.metrics.items():
            if key.endswith("_items"):
                group_name = key.replace("_items", "")
                if group_name not in group_metrics:
                    group_metrics[group_name] = {}
                group_metrics[group_name]["items"] = value
            elif key.endswith("_widgets"):
                group_name = key.replace("_widgets", "")
                if group_name not in group_metrics:
                    group_metrics[group_name] = {}
                group_metrics[group_name]["widgets"] = value

        for group_name, group_data in group_metrics.items():
            items = group_data.get("items", 0)
            widgets = group_data.get("widgets", 0)
            lines.append(
                f"   - {group_name.capitalize()}: {MetricsFormatter.format_number(items)} items -> {widgets} widgets generated"
            )

        # Totals
        if "total_widgets_generated" in metrics.metrics:
            total_widgets = metrics.metrics["total_widgets_generated"]
            lines.append(
                f"{emoji('📊', '[=]')} Total Widgets: {total_widgets} widgets generated"
            )

        # Performance
        if (
            "total_items_processed" in metrics.metrics
            and metrics.duration.total_seconds() > 0
        ):
            items_per_second = (
                metrics.metrics["total_items_processed"]
                / metrics.duration.total_seconds()
            )
            lines.append(
                f"{emoji('⚡', '[~]')} Performance: {items_per_second:.0f} items/second"
            )

        # Errors and warnings
        if metrics.errors:
            lines.append(
                f"{emoji('❌', '[X]')} Errors: {len(metrics.errors)} issues encountered"
            )
        if metrics.warnings:
            lines.append(
                f"{emoji('⚠', '[!]')}  Warnings: {len(metrics.warnings)} warnings"
            )

        return lines

    @staticmethod
    def format_export_metrics(metrics: OperationMetrics) -> List[str]:
        """Format export metrics for display."""
        lines = []

        # Duration
        lines.append(
            f"{emoji('⏱', '[T]')}  Duration: {MetricsFormatter.format_duration(metrics.duration)}"
        )

        # Targets
        lines.append(f"{emoji('🎯', '[*]')} Targets:")

        # Process each target
        target_metrics: Dict[str, Dict[str, int]] = {}
        for key, value in metrics.metrics.items():
            if key.endswith("_files"):
                target_name = key.replace("_files", "")
                if target_name not in target_metrics:
                    target_metrics[target_name] = {}
                target_metrics[target_name]["files"] = value
            elif key.endswith("_errors"):
                target_name = key.replace("_errors", "")
                if target_name not in target_metrics:
                    target_metrics[target_name] = {}
                target_metrics[target_name]["errors"] = value

        for target_name, target_data in target_metrics.items():
            files = target_data.get("files", 0)
            errors = target_data.get("errors", 0)
            # Remove status icon to avoid orphan checkmarks
            error_text = f" ({errors} errors)" if errors > 0 else ""
            lines.append(
                f"   • {target_name}: {MetricsFormatter.format_number(files)} files generated{error_text}"
            )

        # Total
        if "total_files_generated" in metrics.metrics:
            total_files = metrics.metrics["total_files_generated"]
            lines.append(
                f"{emoji('📁', '[+]')} Total: {MetricsFormatter.format_number(total_files)} files generated"
            )

        # Success rate
        if (
            "successful_targets" in metrics.metrics
            and "targets_count" in metrics.metrics
            and metrics.metrics["targets_count"] > 0
        ):
            success_rate = (
                metrics.metrics["successful_targets"] / metrics.metrics["targets_count"]
            ) * 100
            lines.append(
                f"{emoji('📈', '[%]')} Success Rate: {success_rate:.0f}% targets completed successfully"
            )

        return lines
