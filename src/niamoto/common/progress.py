"""
Progress tracking utilities that can work with or without Rich.
"""

from typing import Optional
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class ProgressTracker:
    """A progress tracker that can work with or without Rich Progress bars."""

    def __init__(self, use_progress_bar: bool = True):
        """
        Initialize the progress tracker.

        Args:
            use_progress_bar: Whether to use Rich progress bars or just log messages
        """
        self.use_progress_bar = use_progress_bar
        self._progress = None
        self._task = None

    @contextmanager
    def track(self, description: str, total: Optional[int] = None):
        """
        Context manager for tracking progress.

        Args:
            description: Description of the task
            total: Total number of items to process

        Yields:
            A progress updater function
        """
        if self.use_progress_bar:
            # Use Rich Progress
            from rich.progress import (
                Progress,
                SpinnerColumn,
                BarColumn,
                TextColumn,
            )

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            ) as progress:
                task = progress.add_task(description, total=total)

                def update(advance: int = 1, description: Optional[str] = None):
                    if description:
                        progress.update(task, description=description)
                    progress.update(task, advance=advance)

                yield update
        else:
            # Use simple logging
            logger.info(f"Starting: {description}")
            current = 0

            def update(advance: int = 1, description: Optional[str] = None):
                nonlocal current
                current += advance
                if description:
                    logger.info(description)
                if total:
                    percentage = (current / total) * 100
                    if current % max(1, total // 10) == 0:  # Log every 10%
                        logger.info(f"Progress: {percentage:.0f}% ({current}/{total})")

            yield update

            logger.info(f"Completed: {description}")

    @contextmanager
    def status(self, message: str):
        """
        Context manager for showing a status message.

        Args:
            message: Status message to display
        """
        if self.use_progress_bar:
            from rich.console import Console

            console = Console()
            with console.status(message, spinner="dots"):
                yield
        else:
            logger.info(message)
            yield
            logger.info(f"Completed: {message}")


# Global progress tracker instance
_progress_tracker: Optional[ProgressTracker] = None


def get_progress_tracker() -> ProgressTracker:
    """Get the global progress tracker instance."""
    global _progress_tracker
    if _progress_tracker is None:
        _progress_tracker = ProgressTracker()
    return _progress_tracker


def set_progress_mode(use_progress_bar: bool):
    """
    Set whether to use progress bars globally.

    Args:
        use_progress_bar: True to use Rich progress bars, False to use logging
    """
    global _progress_tracker
    _progress_tracker = ProgressTracker(use_progress_bar=use_progress_bar)
