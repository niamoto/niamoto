"""Tests for the CLI package entrypoint."""

import importlib
import sys

import click
from click.testing import CliRunner


def _fresh_cli_module():
    sys.modules.pop("niamoto.cli", None)
    return importlib.import_module("niamoto.cli")


def test_importing_cli_package_does_not_replace_excepthook(monkeypatch):
    def sentinel_hook(*_args):
        return None

    monkeypatch.delenv("NIAMOTO_DEBUG", raising=False)
    monkeypatch.setattr(sys, "excepthook", sentinel_hook)

    _fresh_cli_module()

    assert sys.excepthook is sentinel_hook


def test_cli_invocation_installs_concise_exception_hook(monkeypatch):
    def sentinel_hook(*_args):
        return None

    monkeypatch.delenv("NIAMOTO_DEBUG", raising=False)
    monkeypatch.setattr(sys, "excepthook", sentinel_hook)
    cli_module = _fresh_cli_module()

    @click.command("test-startup-hook")
    def test_startup_hook():
        click.echo("ok")

    cli_module.cli.add_command(test_startup_hook)
    try:
        result = CliRunner().invoke(cli_module.cli, ["test-startup-hook"])
    finally:
        cli_module.cli.commands.pop("test-startup-hook", None)

    assert result.exit_code == 0
    assert sys.excepthook is cli_module._clean_exception_hook
