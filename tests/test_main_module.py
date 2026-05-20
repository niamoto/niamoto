"""Tests for __main__ module."""

import runpy
import sys
from unittest.mock import patch


class TestMainModule:
    """Test __main__ module execution."""

    def test_main_module_calls_cli(self):
        """Test that executing as module calls the main entrypoint."""
        with patch("niamoto.main.main") as mock_main:
            with patch.object(sys, "argv", ["niamoto"]):
                runpy.run_module("niamoto.__main__", run_name="__main__")

        mock_main.assert_called_once()
