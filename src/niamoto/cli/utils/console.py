"""
Console output utilities for the Niamoto CLI.
Provides consistent formatting for different types of messages with unified icons.
"""

import os
import platform
from rich.console import Console
from typing import Any, Optional, List, Dict

console = Console()


# Detect if we're on Windows and if emoji support might be limited
def _should_use_emojis() -> bool:
    """Determine if emojis should be used based on platform and terminal capabilities."""
    # Check environment variable override
    emoji_env = os.getenv("NIAMOTO_USE_EMOJIS", "").lower()
    if emoji_env in ("1", "true", "yes", "on"):
        return True
    elif emoji_env in ("0", "false", "no", "off"):
        return False

    # Auto-detect based on platform
    if platform.system() == "Windows":
        # Check if we're in a modern terminal that supports emojis
        try:
            # Test emoji rendering capability
            test_console = Console(file=None, legacy_windows=False)
            return not test_console.legacy_windows
        except Exception:
            return False
    return True


# Global setting for emoji usage
USE_EMOJIS = _should_use_emojis()


def print_success(message: str, icon: bool = True) -> None:
    """Print a success message in green."""
    # Don't print anything if message is empty or only whitespace
    if not message or not message.strip():
        return
    if icon:
        prefix = "✅ " if USE_EMOJIS else "[✓] "
    else:
        prefix = ""
    console.print(f"{prefix}{message}", style="green")


def print_error(message: str, icon: bool = True) -> None:
    """Print an error message in red."""
    # Don't print anything if message is empty or only whitespace
    if not message or not message.strip():
        return
    if icon:
        prefix = "❌ " if USE_EMOJIS else "[✗] "
    else:
        prefix = ""
    console.print(f"{prefix}{message}", style="bold red")


def print_warning(message: str, icon: bool = True) -> None:
    """Print a warning message in yellow."""
    # Don't print anything if message is empty or only whitespace
    if not message or not message.strip():
        return
    if icon:
        prefix = "⚠️  " if USE_EMOJIS else "[!] "
    else:
        prefix = ""
    console.print(f"{prefix}{message}", style="yellow")


def print_info(message: str, icon: bool = True) -> None:
    """Print an info message in blue."""
    # Don't add icon if message starts with newline or is empty/whitespace only
    if message.startswith("\n") or not message.strip():
        console.print(message, style="blue")
    else:
        if icon:
            prefix = "ℹ️  " if USE_EMOJIS else "[i] "
        else:
            prefix = ""
        console.print(f"{prefix}{message}", style="blue")


def print_start(message: str) -> None:
    """Print a start message with icon."""
    prefix = "🌱 " if USE_EMOJIS else "[*] "
    console.print(f"{prefix}{message}", style="bold blue")


def print_processing(message: str) -> None:
    """Print a processing message with icon."""
    prefix = "⚡ " if USE_EMOJIS else "[~] "
    console.print(f"{prefix}{message}", style="cyan")


def print_section(title: str) -> None:
    """Print a section header."""
    prefix = "📋 " if USE_EMOJIS else "[#] "
    console.print(f"\n{prefix}{title}", style="bold magenta")


def print_summary_header(title: str) -> None:
    """Print a summary section header."""
    prefix = "📊 " if USE_EMOJIS else "[=] "
    console.print(f"\n{prefix}{title}", style="bold blue")


def print_operation_start(operation: str) -> None:
    """Print operation start message."""
    prefix = "🔄 " if USE_EMOJIS else "[>] "
    console.print(f"{prefix}Starting {operation}...", style="blue")


def print_operation_complete(operation: str, details: Optional[str] = None) -> None:
    """Print operation completion message."""
    prefix = "✅ " if USE_EMOJIS else "[✓] "
    message = f"{prefix}{operation} completed"
    if details:
        message += f" - {details}"
    console.print(message, style="green")


def print_files_processed(count: int, file_type: str = "files") -> None:
    """Print files processed message."""
    prefix = "📁 " if USE_EMOJIS else "[+] "
    console.print(f"{prefix}Processed {count} {file_type}", style="cyan")


def print_duration(seconds: float) -> None:
    """Print duration message."""
    if seconds < 60:
        duration_str = f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        duration_str = f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        duration_str = f"{hours}h {minutes}m"

    prefix = "⏱️  " if USE_EMOJIS else "[T] "
    console.print(f"{prefix}Duration: {duration_str}", style="dim")


def print_stats(stats: Dict[str, Any]) -> None:
    """Print statistics in a formatted way."""
    prefix = "📈 " if USE_EMOJIS else "[%] "
    console.print(f"{prefix}Statistics:", style="bold cyan")
    for key, value in stats.items():
        if isinstance(value, (int, float)):
            console.print(f"   {key}: {value:,}", style="cyan")
        else:
            console.print(f"   {key}: {value}", style="cyan")


def print_metrics_summary(operation_name: str, metrics_lines: List[str]) -> None:
    """Print a formatted metrics summary."""
    prefix = "📊 " if USE_EMOJIS else "[=] "
    console.print(f"\n{prefix}{operation_name} Summary:", style="bold blue")
    for line in metrics_lines:
        # Skip empty lines or lines that only contain emojis/icons
        if (
            line
            and line.strip()
            and line.strip()
            not in [
                "✅",
                "❌",
                "⚠️",
                "📊",
                "🎯",
                "📁",
                "📈",
                "[✓]",
                "[✗]",
                "[!]",
                "[=]",
                "[>]",
                "[+]",
                "[%]",
            ]
        ):
            console.print(f"   {line}", style="cyan")


def print_operation_metrics(metrics: Any, operation_type: str) -> None:
    """Print operation-specific metrics using the MetricsFormatter."""
    from .metrics import MetricsFormatter

    formatter_map = {
        "import": MetricsFormatter.format_import_metrics,
        "transform": MetricsFormatter.format_transform_metrics,
        "export": MetricsFormatter.format_export_metrics,
    }

    formatter = formatter_map.get(operation_type)
    if formatter:
        metrics_lines = formatter(metrics)
        operation_name = operation_type.capitalize()
        print_metrics_summary(operation_name, metrics_lines)
    else:
        # Fallback to basic summary
        print_summary_header(f"{operation_type.capitalize()} Summary")
        print_duration(metrics.duration.total_seconds())

        if metrics.errors:
            print_error(f"{len(metrics.errors)} errors encountered")
        if metrics.warnings:
            print_warning(f"{len(metrics.warnings)} warnings")


def print_step_header(step_name: str) -> None:
    """Print a step header for sub-operations."""
    console.print(f"📋 {step_name}...", style="bold cyan")


def print_step_complete(
    step_name: str, count: Optional[int] = None, duration: Optional[float] = None
) -> None:
    """Print step completion message."""
    message = f"✅ {step_name} completed"
    if count is not None:
        message += f" • {count:,} items"
    if duration is not None:
        if duration < 60:
            message += f" • {duration:.1f}s"
        else:
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            message += f" • {minutes}m {seconds}s"
    console.print(message, style="green")


def print_step_progress(step_name: str, current: int, total: int) -> None:
    """Print step progress without progress bar."""
    percentage = (current / total * 100) if total > 0 else 0
    console.print(
        f"  {step_name}: {current:,}/{total:,} ({percentage:.1f}%)", style="cyan"
    )


def print_linking_status(
    total: int, linked: int, failed: int, link_type: str = "items"
) -> None:
    """Print linking status with statistics."""
    linked_pct = (linked / total * 100) if total > 0 else 0
    failed_pct = (failed / total * 100) if total > 0 else 0

    from rich.table import Table

    table = Table(title=f"{link_type.title()} Link Status")
    table.add_column("Metric", style="bold")
    table.add_column("Count", justify="right")
    table.add_column("Percentage", justify="right")

    table.add_row(f"Total {link_type}", f"{total:,}", "100%")
    table.add_row(
        "Successfully linked", f"{linked:,}", f"{linked_pct:.1f}%", style="green"
    )
    table.add_row(
        "Failed to link",
        f"{failed:,}",
        f"{failed_pct:.1f}%",
        style="red" if failed > 0 else "dim",
    )

    console.print(table)


def print_unlinked_samples(samples: List[str], sample_type: str = "items") -> None:
    """Print samples of unlinked items."""
    if not samples:
        return

    from rich.panel import Panel

    sample_lines = []
    for sample in samples[:5]:  # Show max 5 samples
        sample_lines.append(f"  - {sample}")

    if len(samples) > 5:
        sample_lines.append(f"  ... and {len(samples) - 5} more")

    content = "\n".join(sample_lines)
    panel = Panel(
        content,
        title=f"Sample of Unlinked {sample_type.title()}",
        border_style="yellow",
    )
    console.print(panel)


def print_import_result(
    file_path: str, count: int, data_type: str, details: Optional[str] = None
) -> None:
    """Print import result with file path and count."""
    message = f"✅ {count:,} {data_type} imported from {file_path}"
    if details:
        message += f". {details}"
    console.print(message, style="green")


def print_file_processed(file_path: str, count: int, action: str = "processed") -> None:
    """Print file processing result."""
    console.print(f"📁 {count:,} features {action} from {file_path}", style="cyan")


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable units."""
    size = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def format_number(number: int) -> str:
    """Format large numbers with thousand separators."""
    return f"{number:,}"


def print_table(data: list[dict[str, Any]], title: str) -> None:
    """Print data in a formatted table."""
    from rich.table import Table

    table = Table(title=title)

    # Add columns from the first row keys
    if data:
        for key in data[0].keys():
            table.add_column(key, style="cyan")

        # Add rows
        for row in data:
            table.add_row(*[str(v) for v in row.values()])

    # Always print the table, even if empty
    console.print(table)
