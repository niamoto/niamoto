"""
Main entry point for the Niamoto CLI application.
"""

import logging
import sys

from rich.console import Console

from niamoto.cli import cli as create_cli
from niamoto.common.exceptions import LoggingError, NiamotoError
from niamoto.common.utils import error_handler, setup_global_exception_handler
from niamoto.common.utils.logging_utils import setup_logging

console = Console()


@error_handler(log=True, raise_error=False, console_output=True)
def init_logging() -> None:
    """
    Initialize global logging for the application.

    Raises:
        LoggingError: If logging setup fails
    """
    try:
        setup_logging(
            component_name="main",
            enable_console=True,
            enable_file=True,
            log_level=logging.INFO,
        )
    except Exception as e:
        raise LoggingError("Failed to initialize logging", details={"error": str(e)})


def main() -> None:
    """
    The main entry point for the Niamoto application.

    This function initializes logging, sets up global exception handling,
    and runs the command-line interface. Any unhandled exceptions will be
    logged and displayed to the user appropriately.
    """
    try:
        # Initialize logging first
        init_logging()

        # Set up global exception handler for unhandled exceptions
        setup_global_exception_handler()

        # Create and run the CLI
        cli = create_cli()
        cli()

    except Exception as e:
        # Format the error message based on the type of exception
        if isinstance(e, NiamotoError):
            error_msg = f"Application error: {str(e)}"
            if hasattr(e, "details") and e.details:
                console.print("[red]Error Details:[/red]")
                for key, value in e.details.items():
                    console.print(f"  [yellow]{key}:[/yellow] {value}")
        else:
            error_msg = f"An unexpected error occurred: {str(e)}"

        # Afficher l'erreur en rouge
        console.print(f"[red]✗ {error_msg}[/red]")

        # Dans un environnement de développement, afficher la stack trace complète
        if "--debug" in sys.argv:
            console.print_exception()

        sys.exit(1)


if __name__ == "__main__":
    main()
