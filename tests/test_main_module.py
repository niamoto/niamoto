"""Tests for __main__ module."""

import sys
from unittest.mock import patch


class TestMainModule:
    """Test __main__ module execution."""

    def test_main_module_calls_cli(self):
        """Test that executing as module calls cli function."""
        # Import the cli function

        # Mock the cli function
        with patch("niamoto.cli.cli") as mock_cli:
            # Simulate running python -m niamoto
            # We need to execute the __main__.py code
            with patch.object(sys, "argv", ["niamoto"]):
                # Import and execute __main__
                import importlib.util

                spec = importlib.util.spec_from_file_location(
                    "__main__",
                    "src/niamoto/__main__.py",
                )
                module = importlib.util.module_from_spec(spec)

                # Set __name__ to __main__ to trigger execution
                module.__name__ = "__main__"

                # Execute the module
                try:
                    spec.loader.exec_module(module)
                except SystemExit:
                    # CLI might call sys.exit, that's okay
                    pass

                # Verify cli was called
                mock_cli.assert_called_once()
