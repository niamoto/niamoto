"""Tests for GUI command."""

import os
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
import sys

from niamoto.cli.commands.gui import gui


@contextmanager
def mocked_gui_runtime(mock_uvicorn):
    """Provide fake GUI modules so tests control runtime import side effects."""
    fake_app_module = MagicMock()
    fake_context_module = MagicMock()
    fake_context_module.resolve_explicit_working_directory.return_value = None

    with patch.dict(
        "sys.modules",
        {
            "uvicorn": mock_uvicorn,
            "niamoto.gui.api.app": fake_app_module,
            "niamoto.gui.api.context": fake_context_module,
        },
    ):
        yield fake_app_module, fake_context_module


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

        with mocked_gui_runtime(mock_uvicorn) as (
            fake_app_module,
            fake_context_module,
        ):
            with patch("niamoto.cli.commands.gui.Timer"):  # Prevent browser opening
                mock_app = MagicMock()
                fake_app_module.create_app.return_value = mock_app

                result = runner.invoke(gui)

                # Verify app was created
                fake_app_module.create_app.assert_called_once()
                fake_context_module.set_working_directory.assert_not_called()

                # Verify uvicorn was called with correct defaults
                mock_uvicorn.run.assert_called_once()
                call_kwargs = mock_uvicorn.run.call_args[1]
                assert call_kwargs["host"] == "127.0.0.1"
                assert call_kwargs["port"] == 8080
                assert call_kwargs["reload"] is False

                assert "Starting Niamoto GUI" in result.output

    def test_gui_does_not_invent_niamoto_home_without_selected_project(
        self, monkeypatch
    ):
        """Test GUI command keeps startup in welcome mode when no project is selected."""
        runner = CliRunner()
        mock_uvicorn = MagicMock()
        mock_uvicorn.run.side_effect = KeyboardInterrupt()

        observed = {}

        def fake_create_app():
            observed["niamoto_home"] = os.environ.get("NIAMOTO_HOME")
            return MagicMock()

        monkeypatch.delenv("NIAMOTO_HOME", raising=False)

        with runner.isolated_filesystem():
            with mocked_gui_runtime(mock_uvicorn) as (
                fake_app_module,
                fake_context_module,
            ):
                fake_app_module.create_app.side_effect = fake_create_app
                result = runner.invoke(gui, ["--no-browser"])

            assert result.exit_code == 0
            assert observed["niamoto_home"] is None
            fake_context_module.set_working_directory.assert_not_called()

    def test_gui_uses_explicit_niamoto_home_before_app_creation(self, monkeypatch):
        """Test GUI command preserves an explicit project path for the API app."""
        runner = CliRunner()
        mock_uvicorn = MagicMock()
        mock_uvicorn.run.side_effect = KeyboardInterrupt()

        observed = {}

        def fake_create_app():
            observed["niamoto_home"] = os.environ.get("NIAMOTO_HOME")
            return MagicMock()

        with runner.isolated_filesystem():
            expected_dir = os.getcwd()
            monkeypatch.setenv("NIAMOTO_HOME", expected_dir)
            with mocked_gui_runtime(mock_uvicorn) as (
                fake_app_module,
                fake_context_module,
            ):
                fake_context_module.resolve_explicit_working_directory.return_value = (
                    Path(expected_dir)
                )
                fake_app_module.create_app.side_effect = fake_create_app
                result = runner.invoke(gui, ["--no-browser"])

            assert result.exit_code == 0
            assert observed["niamoto_home"] == expected_dir
            fake_context_module.set_working_directory.assert_called_once()

    def test_gui_ignores_invalid_niamoto_home_before_app_creation(self, monkeypatch):
        """Test GUI command drops an invalid explicit project path before app startup."""
        runner = CliRunner()
        mock_uvicorn = MagicMock()
        mock_uvicorn.run.side_effect = KeyboardInterrupt()

        observed = {}

        def fake_create_app():
            observed["niamoto_home"] = os.environ.get("NIAMOTO_HOME")
            return MagicMock()

        invalid_dir = "/tmp/missing-niamoto-project"
        monkeypatch.setenv("NIAMOTO_HOME", invalid_dir)

        with mocked_gui_runtime(mock_uvicorn) as (
            fake_app_module,
            fake_context_module,
        ):
            fake_app_module.create_app.side_effect = fake_create_app
            fake_context_module.resolve_explicit_working_directory.return_value = None
            result = runner.invoke(gui, ["--no-browser"])

        assert result.exit_code == 0
        assert observed["niamoto_home"] is None
        fake_context_module.set_working_directory.assert_not_called()

    def test_gui_custom_port_and_host(self):
        """Test GUI command with custom port and host."""
        runner = CliRunner()

        mock_uvicorn = MagicMock()
        mock_uvicorn.run.side_effect = KeyboardInterrupt()

        with mocked_gui_runtime(mock_uvicorn):
            with patch("niamoto.cli.commands.gui.Timer"):  # Prevent browser opening
                result = runner.invoke(gui, ["--port", "9000", "--host", "0.0.0.0"])

                call_kwargs = mock_uvicorn.run.call_args[1]
                assert call_kwargs["host"] == "0.0.0.0"
                assert call_kwargs["port"] == 9000
                assert "Server: http://0.0.0.0:9000" in result.output

    def test_gui_reload_option(self):
        """Test GUI command with reload option enabled."""
        runner = CliRunner()

        mock_uvicorn = MagicMock()
        mock_uvicorn.run.side_effect = KeyboardInterrupt()

        with mocked_gui_runtime(mock_uvicorn):
            with patch("niamoto.cli.commands.gui.Timer"):  # Prevent browser opening
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

        with mocked_gui_runtime(mock_uvicorn):
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

        with mocked_gui_runtime(mock_uvicorn):
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

        with mocked_gui_runtime(mock_uvicorn):
            with patch("niamoto.cli.commands.gui.Timer"):  # Prevent browser opening
                result = runner.invoke(gui, ["--no-browser"])

                assert "Shutting down Niamoto GUI" in result.output
                assert result.exit_code == 0

    def test_gui_server_error(self):
        """Test GUI command handles server errors."""
        runner = CliRunner()

        mock_uvicorn = MagicMock()
        mock_uvicorn.run.side_effect = Exception("Server error")

        with mocked_gui_runtime(mock_uvicorn):
            with patch("niamoto.cli.commands.gui.Timer"):  # Prevent browser opening
                result = runner.invoke(gui, ["--no-browser"])

                assert result.exit_code != 0
