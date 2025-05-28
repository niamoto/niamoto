"""Plugin listing command for Niamoto CLI."""

import click
from rich.console import Console
from rich.table import Table
from typing import Optional

from niamoto.core.plugins.registry import PluginRegistry
from niamoto.core.plugins.base import PluginType
from niamoto.core.plugins.plugin_loader import PluginLoader
from niamoto.cli.utils.console import console as default_console
from niamoto.common.config import Config
from pathlib import Path


@click.command()
@click.option(
    "--type",
    "-t",
    type=click.Choice([t.value for t in PluginType], case_sensitive=False),
    help="Filter plugins by type",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "simple"], case_sensitive=False),
    default="table",
    help="Output format",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show additional plugin details",
)
def plugins(type: Optional[str], format: str, verbose: bool) -> None:
    """List all available Niamoto plugins.

    Examples:
        niamoto plugins
        niamoto plugins --type transformer
        niamoto plugins --format simple
        niamoto plugins --verbose
    """
    console = default_console or Console()

    try:
        # Load plugins first
        loader = PluginLoader()
        loader.load_core_plugins()

        # Try to load project plugins if we're in a niamoto project
        try:
            config = Config(Path.cwd() / "config")
            if config.plugins_dir and Path(config.plugins_dir).exists():
                loader.load_project_plugins(config.plugins_dir)
        except Exception:
            # Not in a project directory or no project plugins, that's ok
            pass
        # Get all plugins from the registry
        all_plugins = {}

        # The registry stores plugins by type
        for plugin_type in PluginType:
            type_plugins = PluginRegistry._plugins.get(plugin_type, {})
            for name, plugin_class in type_plugins.items():
                all_plugins[name] = {"type": plugin_type, "class": plugin_class}

        # Filter by type if specified
        if type:
            plugin_type = PluginType(type)
            plugins_dict = {
                name: info
                for name, info in all_plugins.items()
                if info["type"] == plugin_type
            }
        else:
            plugins_dict = all_plugins

        if not plugins_dict:
            console.print(
                f"[yellow]No plugins found{' of type ' + type if type else ''}[/yellow]"
            )
            return

        if format == "simple":
            _display_simple(console, plugins_dict, verbose)
        else:
            _display_table(console, plugins_dict, verbose)

        # Display summary
        total = len(plugins_dict)
        by_type = {}
        for info in plugins_dict.values():
            ptype = info["type"].value
            by_type[ptype] = by_type.get(ptype, 0) + 1

        console.print(f"\n[dim]Total: {total} plugins")
        console.print(
            "[dim]By type: "
            + ", ".join(f"{t}: {c}" for t, c in by_type.items())
            + "[/dim]"
        )

    except Exception as e:
        console.print(f"[red]Error listing plugins: {e}[/red]")
        raise click.ClickException(str(e))


def _display_table(console: Console, plugins: dict, verbose: bool) -> None:
    """Display plugins in a rich table format."""
    table = Table(title="Available Niamoto Plugins", show_lines=True)

    # Define columns
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Type", style="magenta")
    table.add_column("Description", style="white")
    if verbose:
        table.add_column("Module", style="dim")
        table.add_column("Class", style="dim")
        table.add_column("Has Schema", style="green")

    # Sort plugins by type then name
    sorted_plugins = sorted(plugins.items(), key=lambda x: (x[1]["type"].value, x[0]))

    for name, info in sorted_plugins:
        plugin_class = info["class"]
        description = _get_description(plugin_class)

        row = [
            name,
            info["type"].value,
            description,
        ]

        if verbose:
            module = plugin_class.__module__
            class_name = plugin_class.__name__
            has_schema = "✓" if hasattr(plugin_class, "param_schema") else "✗"
            row.extend([module, class_name, has_schema])

        table.add_row(*row)

    console.print(table)


def _display_simple(console: Console, plugins: dict, verbose: bool) -> None:
    """Display plugins in a simple text format."""
    # Group by type
    by_type = {}
    for name, info in plugins.items():
        ptype = info["type"].value
        if ptype not in by_type:
            by_type[ptype] = []
        by_type[ptype].append((name, info))

    for ptype, plugin_list in sorted(by_type.items()):
        console.print(f"\n[bold magenta]{ptype.upper()} PLUGINS:[/bold magenta]")

        for name, info in sorted(plugin_list):
            plugin_class = info["class"]
            description = _get_description(plugin_class)

            console.print(f"  [cyan]{name}[/cyan] - {description}")

            if verbose:
                module = plugin_class.__module__
                console.print(f"    [dim]Module: {module}[/dim]")
                console.print(f"    [dim]Class: {plugin_class.__name__}[/dim]")
                if hasattr(plugin_class, "param_schema"):
                    console.print("    [dim]Has parameter schema: ✓[/dim]")


def _get_description(plugin_class) -> str:
    """Extract the first line of the plugin's docstring as description."""
    if plugin_class.__doc__:
        # Get first non-empty line
        lines = plugin_class.__doc__.strip().split("\n")
        for line in lines:
            line = line.strip()
            if line:
                # Remove trailing period if present
                if line.endswith("."):
                    line = line[:-1]
                return line
    return "No description available"
