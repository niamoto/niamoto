"""Tests for common progress module."""

import logging
from unittest.mock import patch, MagicMock

from niamoto.common.progress import (
    ProgressTracker,
    get_progress_tracker,
    set_progress_mode,
)


class TestProgressTracker:
    """Test ProgressTracker class."""

    def test_init_with_progress_bar(self):
        """Test initialization with progress bar enabled."""
        tracker = ProgressTracker(use_progress_bar=True)
        assert tracker.use_progress_bar is True

    def test_init_without_progress_bar(self):
        """Test initialization with progress bar disabled."""
        tracker = ProgressTracker(use_progress_bar=False)
        assert tracker.use_progress_bar is False

    def test_track_with_progress_bar(self):
        """Test track context manager with Rich progress bar."""
        tracker = ProgressTracker(use_progress_bar=True)

        with patch("rich.progress.Progress") as mock_progress_class:
            mock_progress = MagicMock()
            mock_progress_class.return_value.__enter__.return_value = mock_progress
            mock_task = MagicMock()
            mock_progress.add_task.return_value = mock_task

            with tracker.track("Test task", total=100) as update:
                # Call the update function
                update(advance=10)
                mock_progress.update.assert_called()

                # Update with description
                update(advance=5, description="Updated description")
                assert mock_progress.update.call_count >= 2

    def test_track_without_progress_bar(self, caplog):
        """Test track context manager with logging fallback."""
        tracker = ProgressTracker(use_progress_bar=False)

        with caplog.at_level(logging.INFO):
            with tracker.track("Test task", total=10) as update:
                update(advance=1)
                update(advance=1, description="Custom message")

        # Verify logging messages
        assert "Starting: Test task" in caplog.text
        assert "Completed: Test task" in caplog.text

    def test_status_with_progress_bar(self):
        """Test status context manager with Rich console."""
        tracker = ProgressTracker(use_progress_bar=True)

        with patch("rich.console.Console") as mock_console_class:
            mock_console = MagicMock()
            mock_console_class.return_value = mock_console

            with tracker.status("Processing..."):
                pass

            mock_console.status.assert_called_once_with("Processing...", spinner="dots")

    def test_status_without_progress_bar(self, caplog):
        """Test status context manager with logging fallback."""
        tracker = ProgressTracker(use_progress_bar=False)

        with caplog.at_level(logging.INFO):
            with tracker.status("Processing..."):
                pass

        assert "Processing..." in caplog.text
        assert "Completed: Processing..." in caplog.text


class TestGlobalProgressTracker:
    """Test global progress tracker functions."""

    def test_get_progress_tracker_creates_instance(self):
        """Test that get_progress_tracker creates a singleton instance."""
        tracker = get_progress_tracker()
        assert isinstance(tracker, ProgressTracker)

        # Should return the same instance
        tracker2 = get_progress_tracker()
        assert tracker is tracker2

    def test_set_progress_mode(self):
        """Test setting global progress mode."""
        set_progress_mode(use_progress_bar=False)
        tracker = get_progress_tracker()
        assert tracker.use_progress_bar is False

        set_progress_mode(use_progress_bar=True)
        tracker = get_progress_tracker()
        assert tracker.use_progress_bar is True
