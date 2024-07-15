import sys
import logging
from typing import Type, Optional, Any

from niamoto.cli.commands import cli
from niamoto.core.utils.logging_utils import setup_logging


def handle_exception(exc_type: Type[BaseException], exc_value: BaseException, exc_traceback: Optional[Any]) -> None:
    """
    Global exception handler to log uncaught exceptions.

    Args:
        exc_type: The type of the exception.
        exc_value: The exception instance.
        exc_traceback: A traceback object encapsulating the call stack.

    Note:
        This function will log all uncaught exceptions except for KeyboardInterrupt.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        # Special handling for keyboard interrupt (Ctrl+C)
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


def init_logging() -> None:
    """
    Initialize global logging for the application.

    This function sets up logging with a 'main' component name, which will create
    or use a 'main.log' file for general application logs.
    """
    setup_logging(component_name="main")


def main() -> None:
    """
    The main entry point for the NiamotoCore application.

    This function initializes logging, sets up global exception handling,
    and runs the command-line interface. Any unhandled exceptions will be
    logged before the application exits.

    Returns:
        None

    Raises:
        SystemExit: If an unhandled exception occurs, the program will exit with status code 1.
    """
    try:
        # Initialize logging
        init_logging()

        # Set up the global exception handler
        sys.excepthook = handle_exception

        # Run the command-line interface
        cli()
    except Exception as e:
        # Log any unexpected errors that occur in the main function
        logging.error(f"An error occurred in the main function: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
