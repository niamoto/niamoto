"""
Unified progress management for Niamoto CLI commands.
Provides consistent progress bars and status reporting across all operations.
"""

from typing import Optional, Dict, Any, List, Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TaskID,
    ProgressColumn,
)
from niamoto.common.utils.emoji import emoji


class ProgressManager:
    """Unified progress manager for Niamoto CLI operations."""

    def __init__(self, console: Optional[Console] = None):
        """Initialize the progress manager."""
        self.console = console or Console()
        self._current_progress: Optional[Progress] = None
        self._tasks: Dict[str, TaskID] = {}
        self._task_start_times: Dict[str, datetime] = {}
        self._start_time: Optional[datetime] = None
        self._stats: Dict[str, Any] = {}

    @property
    def standard_columns(self) -> List[ProgressColumn]:
        """Standard progress bar columns for consistency."""
        return [
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(complete_style="green", finished_style="bright_green"),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        ]

    @contextmanager
    def progress_context(
        self, total_operations: Optional[int] = None
    ) -> Iterator["ProgressManager"]:
        """Context manager for progress tracking."""
        self._start_time = datetime.now()
        self._task_start_times.clear()
        self._stats = {
            "operations_completed": 0,
            "total_operations": total_operations or 0,
            "errors": 0,
            "warnings": 0,
        }

        with Progress(
            *self.standard_columns,
            console=self.console,
            refresh_per_second=10,
        ) as progress:
            self._current_progress = progress
            try:
                yield self
            finally:
                self._current_progress = None
                self._tasks.clear()
                self._task_start_times.clear()

    def add_task(
        self, name: str, description: str, total: Optional[int] = None
    ) -> TaskID:
        """Add a new progress task."""
        if not self._current_progress:
            raise RuntimeError("Progress context not active")

        # Store task start time
        self._task_start_times[name] = datetime.now()

        task_id = self._current_progress.add_task(description=description, total=total)
        self._tasks[name] = task_id
        return task_id

    def update_task(
        self,
        name: str,
        advance: int = 1,
        description: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Update a progress task."""
        if not self._current_progress or name not in self._tasks:
            return

        # Calculate elapsed time for this task
        if name in self._task_start_times:
            elapsed = (datetime.now() - self._task_start_times[name]).total_seconds()
            elapsed_str = f" • {elapsed:.1f}s"
        else:
            elapsed_str = ""

        # Update description to include real-time duration
        if description:
            # If description contains completed status, keep it as is
            checkmark = emoji("✓", "[OK]")
            if f"[{checkmark}]" in description and "completed" in description:
                final_description = description
            else:
                # Add real-time duration to ongoing task
                final_description = f"{description}{elapsed_str}"
            self._current_progress.update(
                self._tasks[name], description=final_description
            )

        self._current_progress.update(self._tasks[name], advance=advance)

        # Apply any additional kwargs
        if kwargs:
            self._current_progress.update(self._tasks[name], **kwargs)

        if advance > 0:
            self._stats["operations_completed"] += advance

    def complete_task(self, name: str, success_message: Optional[str] = None) -> None:
        """Mark a task as completed."""
        if not self._current_progress or name not in self._tasks:
            return

        task_id = self._tasks[name]

        # First ensure the task is at 100% progress
        task = self._current_progress.tasks[task_id]
        if task.total and task.completed < task.total:
            # Complete any remaining progress to reach 100%
            remaining = task.total - task.completed
            self._current_progress.update(task_id, advance=remaining)

        # Calculate final elapsed time for display
        if name in self._task_start_times:
            elapsed = (datetime.now() - self._task_start_times[name]).total_seconds()
            elapsed_str = (
                f" • {elapsed:.1f}s"
                if elapsed < 60
                else f" • {int(elapsed // 60)}m {int(elapsed % 60)}s"
            )
        else:
            elapsed_str = ""

        # Update the description to show completion with final time
        checkmark = emoji("✓", "[OK]")
        if success_message and f"[{checkmark}]" in success_message:
            final_description = f"[green]{success_message}{elapsed_str}[/green]"
        else:
            final_description = f"[green][{checkmark}] {success_message or 'completed'}{elapsed_str}[/green]"
        self._current_progress.update(task_id, description=final_description)

        # Set final completion state to keep bar at 100%
        self._current_progress.update(
            task_id, completed=task.total if task.total else 100
        )

    def add_error(self, message: str) -> None:
        """Record an error."""
        self._stats["errors"] += 1
        self.console.print(f"{emoji('❌', '[X]')} {message}", style="bold red")

    def add_warning(self, message: str) -> None:
        """Record a warning."""
        self._stats["warnings"] += 1
        self.console.print(f"{emoji('⚠', '[!]')}  {message}", style="yellow")

    def show_summary(
        self,
        operation_name: str = "Operation",
        additional_stats: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Show a summary of the operation."""
        if not self._start_time:
            return

        duration = datetime.now() - self._start_time

        self.console.print(
            f"\n{emoji('📊', '[=]')} {operation_name} Summary:", style="bold blue"
        )
        self.console.print(f"   Duration: {self._format_duration(duration)}")
        self.console.print(
            f"   Operations completed: {self._stats['operations_completed']}"
        )

        if self._stats["total_operations"] > 0:
            self.console.print(
                f"   Total operations: {self._stats['total_operations']}"
            )

        if self._stats["errors"] > 0:
            self.console.print(f"   Errors: {self._stats['errors']}", style="red")

        if self._stats["warnings"] > 0:
            self.console.print(
                f"   Warnings: {self._stats['warnings']}", style="yellow"
            )

        if additional_stats:
            for key, value in additional_stats.items():
                self.console.print(f"   {key}: {value}")

        checkmark = emoji("✓", "[OK]")
        warning = emoji("⚠", "[!]")
        status = (
            f"[{checkmark}] Success"
            if self._stats["errors"] == 0
            else f"{warning}  Completed with errors"
        )
        style = "green" if self._stats["errors"] == 0 else "yellow"
        self.console.print(f"\n{status}", style=f"bold {style}")

    def _format_duration(self, duration: timedelta) -> str:
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


def create_simple_progress(description: str, total: Optional[int] = None) -> Progress:
    """Create a simple progress bar for one-off operations."""
    return Progress(
        SpinnerColumn(),
        TextColumn(f"[progress.description]{description}"),
        BarColumn(complete_style="green", finished_style="bright_green"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%")
        if total
        else TextColumn(""),
        console=Console(),
        refresh_per_second=10,
    )


class OperationTracker:
    """Simple tracker for operations without progress bars."""

    def __init__(self, console: Optional[Console] = None):
        """Initialize the operation tracker."""
        self.console = console or Console()
        self.start_time = datetime.now()
        self.operations = 0
        self.errors = 0
        self.warnings = 0

    def start_operation(self, message: str) -> None:
        """Start an operation."""
        self.console.print(f"{emoji('🚀', '>>')} {message}", style="blue")

    def complete_operation(self, message: str) -> None:
        """Complete an operation successfully."""
        self.operations += 1
        self.console.print(f"[{emoji('✓', '[OK]')}] {message}", style="green")

    def error(self, message: str) -> None:
        """Record an error."""
        self.errors += 1
        self.console.print(f"[{emoji('✗', '[X]')}] {message}", style="bold red")

    def warning(self, message: str) -> None:
        """Record a warning."""
        self.warnings += 1
        self.console.print(f"{emoji('⚠', '[!]')}  {message}", style="yellow")

    def info(self, message: str) -> None:
        """Show info message."""
        self.console.print(f"{emoji('ℹ', '[i]')}  {message}", style="blue")

    def show_summary(self, operation_name: str = "Operation") -> None:
        """Show operation summary."""
        duration = datetime.now() - self.start_time

        self.console.print(
            f"\n{emoji('📊', '[=]')} {operation_name} Summary:", style="bold blue"
        )
        self.console.print(f"   Duration: {self._format_duration(duration)}")
        self.console.print(f"   Operations: {self.operations}")

        if self.errors > 0:
            self.console.print(f"   Errors: {self.errors}", style="red")

        if self.warnings > 0:
            self.console.print(f"   Warnings: {self.warnings}", style="yellow")

        checkmark = emoji("✓", "[OK]")
        warning = emoji("⚠", "[!]")
        status = (
            f"[{checkmark}] Success"
            if self.errors == 0
            else f"{warning}  Completed with errors"
        )
        style = "green" if self.errors == 0 else "yellow"
        self.console.print(f"\n{status}", style=f"bold {style}")

    def _format_duration(self, duration: timedelta) -> str:
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
