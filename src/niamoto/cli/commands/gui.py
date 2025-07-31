"""GUI command for Niamoto CLI."""

import click
import webbrowser
from threading import Timer
import logging

logger = logging.getLogger(__name__)


@click.command()
@click.option("--port", default=8080, help="Port for the web interface (default: 8080)")
@click.option(
    "--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)"
)
@click.option("--no-browser", is_flag=True, help="Do not open browser automatically")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
def gui(port: int, host: str, no_browser: bool, reload: bool):
    """Launch the Niamoto visual configuration interface.

    This command starts a FastAPI server that provides both the API
    and serves the React-based configuration interface.
    """
    try:
        # Import here to avoid circular imports and to check if dependencies are installed
        import uvicorn
        from niamoto.gui.api.app import create_app
    except ImportError as e:
        click.echo(
            click.style("Error: GUI dependencies not installed.", fg="red") + "\n"
            "Please install with: pip install niamoto[gui]"
        )
        raise click.ClickException(str(e))

    click.echo(
        click.style("Starting Niamoto GUI...", fg="green") + f"\n"
        f"Server: http://{host}:{port}\n"
        f"API Docs: http://{host}:{port}/docs"
    )

    # Create the app
    app = create_app()

    # Open browser after server starts (if not disabled)
    if not no_browser:

        def open_browser():
            url = f"http://{host}:{port}"
            click.echo(f"Opening browser at {url}")
            webbrowser.open(url)

        # Wait a bit for server to start
        Timer(1.5, open_browser).start()

    # Run the server
    try:
        uvicorn.run(
            "niamoto.gui.api.app:app" if reload else app,
            host=host,
            port=port,
            reload=reload,
            log_level="info",
        )
    except KeyboardInterrupt:
        click.echo("\nShutting down Niamoto GUI...")
    except Exception as e:
        logger.error(f"Error running GUI server: {e}")
        raise click.ClickException(str(e))
