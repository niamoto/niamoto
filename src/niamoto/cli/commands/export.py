# src/niamoto/cli/commands/export.py

"""
Commands for generating exports from Niamoto data.

The export command processes targets defined in export.yml:
- Each target can have its own exporter plugin (html_page_exporter, json_api_exporter, etc.)
- Targets can be run individually or all at once
- Groups within targets can be filtered
"""

from typing import Optional
from pathlib import Path

import click

from niamoto.common.config import Config
from niamoto.common.exceptions import ConfigurationError, ProcessError
from niamoto.common.utils.error_handler import error_handler
from niamoto.core.services.exporter import ExporterService
from ..utils.console import print_success, print_info, print_error, print_warning


@click.command(name="export")
@click.option(
    "--target",
    "-t",
    type=str,
    help="Name of the specific export target to run (as defined in export.yml). "
    "If omitted, runs all enabled targets.",
)
@click.option(
    "--group",
    "-g",
    type=str,
    help="Only export data for this specific group (e.g., 'taxon', 'plot', 'shape'). "
    "Only works when a specific target is specified.",
)
@click.option(
    "--list",
    "-l",
    is_flag=True,
    help="List all available export targets and their status.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be exported without actually running the export.",
)
@error_handler(log=True, raise_error=True)
def export_command(
    target: Optional[str], group: Optional[str], list: bool, dry_run: bool
) -> None:
    """
    Export Niamoto data according to configurations in export.yml.

    Examples:

    \b
    # Run all enabled exports
    niamoto export

    \b
    # Run only the 'web_pages' target
    niamoto export --target web_pages

    \b
    # Run only the 'json_api' target
    niamoto export --target json_api

    \b
    # Export only taxon data from web_pages target
    niamoto export --target web_pages --group taxon

    \b
    # List all available export targets
    niamoto export --list
    """
    try:
        # Initialize configuration
        config = Config()
        db_path = config.database_path
        db_path_obj = Path(db_path) if db_path else None

        if not db_path_obj or not db_path_obj.exists():
            print_error(f"Database not found at: {db_path_obj}")
            return

        # Initialize the ExporterService
        service = ExporterService(db_path=str(db_path_obj), config=config)

        # Handle --list option
        if list:
            _list_export_targets(service)
            return

        # Validate options
        if group and not target:
            print_error("The --group option requires --target to be specified.")
            print_info("Use 'niamoto export --list' to see available targets.")
            return

        # Handle dry run
        if dry_run:
            _show_dry_run(service, target, group)
            return

        # Run the export process
        if target:
            print_info(f"🚀 Running export target: '{target}'")
            if group:
                print_info(f"   Filtering to group: '{group}'")
        else:
            print_info("🚀 Running all enabled export targets...")

        # Execute the export
        results = service.run_export(target_name=target, group_filter=group)

        # Show summary
        _show_export_summary(results)

        print_success("✅ Export process completed successfully!")

    except ConfigurationError as e:
        print_error(f"❌ Configuration error: {e}")
        raise
    except ProcessError as e:
        print_error(f"❌ Export failed: {e}")
        raise
    except Exception as e:
        print_error(f"❌ Unexpected error: {e}")
        raise


def _list_export_targets(service: ExporterService) -> None:
    """List all available export targets from configuration."""
    print_info("\n📋 Available export targets:\n")

    try:
        targets = service.get_export_targets()

        if not targets:
            print_warning("No export targets found in configuration.")
            return

        for target_name, target_info in targets.items():
            status = (
                "✅ enabled" if target_info.get("enabled", False) else "❌ disabled"
            )
            exporter = target_info.get("exporter", "unknown")

            print(f"  • {target_name:<20} [{status}] - Exporter: {exporter}")

            # Show groups if available
            groups = target_info.get("groups", [])
            if groups:
                group_names = [g.get("group_by", "unknown") for g in groups]
                print(f"    Groups: {', '.join(group_names)}")

            # Show output directory if available
            output_dir = target_info.get("params", {}).get("output_dir")
            if output_dir:
                print(f"    Output: {output_dir}")

            print()  # Empty line between targets

    except Exception as e:
        print_error(f"Failed to list targets: {e}")


def _show_dry_run(
    service: ExporterService, target: Optional[str], group: Optional[str]
) -> None:
    """Show what would be exported without actually running."""
    print_info("\n🔍 DRY RUN - The following would be exported:\n")

    try:
        targets = service.get_export_targets()

        # Filter targets based on command options
        if target:
            if target not in targets:
                print_error(f"Target '{target}' not found in configuration.")
                return
            targets = {target: targets[target]}

        # Show only enabled targets
        targets = {k: v for k, v in targets.items() if v.get("enabled", False)}

        for target_name, target_info in targets.items():
            print(f"📦 Target: {target_name}")
            print(f"   Exporter: {target_info.get('exporter', 'unknown')}")
            print(
                f"   Output: {target_info.get('params', {}).get('output_dir', 'unknown')}"
            )

            groups = target_info.get("groups", [])
            if group:
                # Filter to specific group
                groups = [g for g in groups if g.get("group_by") == group]
                if not groups:
                    print_warning(f"   ⚠️  Group '{group}' not found in this target")
                    continue

            if groups:
                print("   Groups to export:")
                for g in groups:
                    group_name = g.get("group_by", "unknown")
                    print(f"     - {group_name}")

            print()

    except Exception as e:
        print_error(f"Failed to analyze export configuration: {e}")


def _show_export_summary(results: dict) -> None:
    """Show a summary of the export results."""
    if not results:
        return

    print_info("\n📊 Export Summary:\n")

    for target_name, target_results in results.items():
        if isinstance(target_results, dict):
            files_generated = target_results.get("files_generated", 0)
            errors = target_results.get("errors", 0)
            duration = target_results.get("duration", "unknown")

            status = "✅" if errors == 0 else "⚠️"
            print(f"  {status} {target_name}:")
            print(f"     Files generated: {files_generated}")
            if errors > 0:
                print(f"     Errors: {errors}")
            print(f"     Duration: {duration}")
        else:
            print(f"  ✅ {target_name}: Completed")

    print()  # Empty line after summary
