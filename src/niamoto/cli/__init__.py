"""
Main CLI package for Niamoto.
"""

from .commands import create_cli

# Create the CLI instance that will be used as the entry point
cli = create_cli()

__all__ = ["cli"]
