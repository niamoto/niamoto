"""
Allow niamoto to be executed as a module with python -m niamoto.
"""

from niamoto.cli import cli

if __name__ == "__main__":
    cli()
