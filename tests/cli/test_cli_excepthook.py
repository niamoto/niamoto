"""Regression tests for CLI startup exception handling."""

from niamoto.cli import _clean_exception_hook


def test_clean_exception_hook_prints_unhandled_errors(capsys):
    """Unhandled exceptions should never fail silently."""
    error = RuntimeError("startup failed")

    _clean_exception_hook(RuntimeError, error, None)

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "Error (RuntimeError): startup failed\n"


def test_clean_exception_hook_suppresses_already_handled_errors(capsys):
    """Errors displayed by the shared handler should not be duplicated."""
    error = RuntimeError("already displayed")
    error._handled = True

    _clean_exception_hook(RuntimeError, error, None)

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
