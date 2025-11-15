"""Tests for GUI command."""

from unittest.mock import patch, MagicMock
from click.testing import CliRunner
import sys

from niamoto.cli.commands.gui import gui


class TestGuiCommand:
    """Test GUI command."""

    def test_gui_missing_dependencies(self):
        """Test GUI command when dependencies are not installed."""
        runner = CliRunner()

        # Temporarily remove uvicorn from sys.modules if it exists
        uvicorn_module = sys.modules.pop("uvicorn", None)
        try:
            with patch.dict("sys.modules", {"uvicorn": None}):
                result = runner.invoke(gui)
                assert result.exit_code != 0
                assert "GUI dependencies not installed" in result.output
        finally:
            # Restore uvicorn if it was there
            if uvicorn_module is not None:
                sys.modules["uvicorn"] = uvicorn_module

    def test_gui_default_options(self):
        """Test GUI command with default options."""
        runner = CliRunner()

        mock_uvicorn = MagicMock()
        mock_uvicorn.run.side_effect = KeyboardInterrupt()

        with patch.dict("sys.modules", {"uvicorn": mock_uvicorn}):
            with patch("niamoto.gui.api.app.create_app") as mock_create_app:
                with patch(
                    "niamoto.gui.api.context.set_working_directory"
                ) as mock_set_wd:
                    with patch(
                        "niamoto.cli.commands.gui.Timer"
                    ):  # Prevent browser opening
                        mock_app = MagicMock()
                        mock_create_app.return_value = mock_app

                        result = runner.invoke(gui)

                        # Verify app was created and working directory set
                        mock_create_app.assert_called_once()
                        mock_set_wd.assert_called_once()

                        # Verify uvicorn was called with correct defaults
                        mock_uvicorn.run.assert_called_once()
                        call_kwargs = mock_uvicorn.run.call_args[1]
                        assert call_kwargs["host"] == "127.0.0.1"
                        assert call_kwargs["port"] == 8080
                        assert call_kwargs["reload"] is False

                        assert "Starting Niamoto GUI" in result.output

    def test_gui_custom_port_and_host(self):
        """Test GUI command with custom port and host."""
        runner = CliRunner()

        mock_uvicorn = MagicMock()
        mock_uvicorn.run.side_effect = KeyboardInterrupt()

        with patch.dict("sys.modules", {"uvicorn": mock_uvicorn}):
            with patch("niamoto.gui.api.app.create_app"):
                with patch("niamoto.gui.api.context.set_working_directory"):
                    with patch(
                        "niamoto.cli.commands.gui.Timer"
                    ):  # Prevent browser opening
                        result = runner.invoke(
                            gui, ["--port", "9000", "--host", "0.0.0.0"]
                        )

                        call_kwargs = mock_uvicorn.run.call_args[1]
                        assert call_kwargs["host"] == "0.0.0.0"
                        assert call_kwargs["port"] == 9000
                        assert "Server: http://0.0.0.0:9000" in result.output

    def test_gui_reload_option(self):
        """Test GUI command with reload option enabled."""
        runner = CliRunner()

        mock_uvicorn = MagicMock()
        mock_uvicorn.run.side_effect = KeyboardInterrupt()

        with patch.dict("sys.modules", {"uvicorn": mock_uvicorn}):
            with patch("niamoto.gui.api.app.create_app"):
                with patch("niamoto.gui.api.context.set_working_directory"):
                    with patch(
                        "niamoto.cli.commands.gui.Timer"
                    ):  # Prevent browser opening
                        runner.invoke(gui, ["--reload"])

                        call_kwargs = mock_uvicorn.run.call_args[1]
                        assert call_kwargs["reload"] is True
                        # When reload is True, should pass string path instead of app instance
                        assert call_kwargs["host"] == "127.0.0.1"

    def test_gui_no_browser_option(self):
        """Test GUI command with --no-browser option."""
        runner = CliRunner()

        mock_uvicorn = MagicMock()
        mock_uvicorn.run.side_effect = KeyboardInterrupt()

        with patch.dict("sys.modules", {"uvicorn": mock_uvicorn}):
            with patch("niamoto.gui.api.app.create_app"):
                with patch("niamoto.gui.api.context.set_working_directory"):
                    with patch("niamoto.cli.commands.gui.Timer") as mock_timer:
                        result = runner.invoke(gui, ["--no-browser"])

                        # Timer should not be started when --no-browser is set
                        mock_timer.assert_not_called()
                        assert result.exit_code == 0

    def test_gui_opens_browser_by_default(self):
        """Test that browser opens by default."""
        runner = CliRunner()

        mock_uvicorn = MagicMock()
        mock_uvicorn.run.side_effect = KeyboardInterrupt()

        with patch.dict("sys.modules", {"uvicorn": mock_uvicorn}):
            with patch("niamoto.gui.api.app.create_app"):
                with patch("niamoto.gui.api.context.set_working_directory"):
                    with patch("niamoto.cli.commands.gui.Timer") as mock_timer:
                        runner.invoke(gui)

                        # Timer should be started to open browser
                        mock_timer.assert_called_once()
                        timer_args = mock_timer.call_args[0]
                        assert timer_args[0] == 1.5  # 1.5 second delay
                        # Verify that a callable was passed (the open_browser function)
                        assert callable(timer_args[1])
                        # Verify timer.start() was called
                        mock_timer.return_value.start.assert_called_once()

    def test_gui_keyboard_interrupt(self):
        """Test GUI command handles keyboard interrupt gracefully."""
        runner = CliRunner()

        mock_uvicorn = MagicMock()
        mock_uvicorn.run.side_effect = KeyboardInterrupt()

        with patch.dict("sys.modules", {"uvicorn": mock_uvicorn}):
            with patch("niamoto.gui.api.app.create_app"):
                with patch("niamoto.gui.api.context.set_working_directory"):
                    with patch(
                        "niamoto.cli.commands.gui.Timer"
                    ):  # Prevent browser opening
                        result = runner.invoke(gui, ["--no-browser"])

                        assert "Shutting down Niamoto GUI" in result.output
                        assert result.exit_code == 0

    def test_gui_server_error(self):
        """Test GUI command handles server errors."""
        runner = CliRunner()

        mock_uvicorn = MagicMock()
        mock_uvicorn.run.side_effect = Exception("Server error")

        with patch.dict("sys.modules", {"uvicorn": mock_uvicorn}):
            with patch("niamoto.gui.api.app.create_app"):
                with patch("niamoto.gui.api.context.set_working_directory"):
                    with patch(
                        "niamoto.cli.commands.gui.Timer"
                    ):  # Prevent browser opening
                        result = runner.invoke(gui, ["--no-browser"])

                        assert result.exit_code != 0
