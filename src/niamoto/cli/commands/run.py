"""
Command to run the complete Niamoto pipeline: import, transform, and export.
"""

from typing import Optional

import click

from niamoto.common.utils.error_handler import error_handler
from ..utils.console import print_success, print_info, print_error, print_warning
from .imports import import_all
from .transform import process_transformations
from .export import export_command
from .initialize import reset_environment, get_config_dir, confirm_reset


@click.command(name="run")
@click.option(
    "--skip-import",
    is_flag=True,
    help="Skip the import phase.",
)
@click.option(
    "--skip-transform",
    is_flag=True,
    help="Skip the transform phase.",
)
@click.option(
    "--skip-export",
    is_flag=True,
    help="Skip the export phase.",
)
@click.option(
    "--group",
    type=str,
    help="Only process a specific group (applies to transform and export phases).",
)
@click.option(
    "--target",
    type=str,
    help="Name of the specific export target to run (applies to export phase).",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Show detailed processing information.",
)
@click.option(
    "--no-reset",
    is_flag=True,
    help="Skip the automatic environment reset before running the pipeline.",
)
@click.option(
    "--force-reset",
    is_flag=True,
    help="Force reset without confirmation prompt (DANGEROUS: deletes all data).",
)
@click.pass_context
@error_handler(log=True, raise_error=True)
def run_pipeline(
    ctx: click.Context,
    skip_import: bool,
    skip_transform: bool,
    skip_export: bool,
    group: Optional[str],
    target: Optional[str],
    verbose: bool,
    no_reset: bool,
    force_reset: bool,
) -> None:
    """
    Run the complete Niamoto data pipeline: import, transform, and export.

    This command executes all phases of the Niamoto pipeline in sequence:
    0. Reset: Clean environment (unless --no-reset is used)
    1. Import: Load data from CSV, GIS formats (import.yml)
    2. Transform: Calculate statistics via plugins (transform.yml)
    3. Export: Generate static sites with visualizations (export.yml)

    ⚠️  WARNING: By default, this command RESETS your environment, which:
        - Deletes the entire database
        - Removes all generated exports
        - Clears all logs
        You will be prompted for confirmation unless --force-reset is used.

    You can skip specific phases using the --skip-* options.

    Examples:
        niamoto run --no-reset  # RECOMMENDED: Run without resetting
        niamoto run --force-reset  # Run with automatic reset (for scripts)
        niamoto run --skip-import  # Run only transform and export
        niamoto run --group taxon  # Process only taxon data
        niamoto run --target my_site  # Use specific export target
    """
    print_info("\n🌱 Starting Niamoto pipeline...")

    try:
        # Reset phase (unless skipped)
        if not no_reset:
            print_info("\n[bold]Phase 0: Reset Environment[/bold]")

            # SECURITY: Require confirmation unless --force-reset is used
            if not force_reset:
                if not confirm_reset():
                    print_warning(
                        "Pipeline cancelled. Use --no-reset to skip reset phase."
                    )
                    return

            config_dir = get_config_dir()
            reset_environment(config_dir)
            print_info("Environment reset completed.")
        else:
            print_info("\n[dim]Skipping environment reset[/dim]")
        # Import phase
        if not skip_import:
            print_info("\n[bold]Phase 1: Import[/bold]")
            ctx.invoke(import_all)
        else:
            print_info("\n[dim]Skipping import phase[/dim]")

        # Transform phase
        if not skip_transform:
            print_info("\n[bold]Phase 2: Transform[/bold]")
            ctx.invoke(
                process_transformations,
                group=group,
                data=None,
                verbose=verbose,
                recreate_table=True,
            )
        else:
            print_info("\n[dim]Skipping transform phase[/dim]")

        # Export phase
        if not skip_export:
            print_info("\n[bold]Phase 3: Export[/bold]")
            ctx.invoke(
                export_command, target=target, group=group, list=False, dry_run=False
            )
        else:
            print_info("\n[dim]Skipping export phase[/dim]")

        print_success("\n✨ Pipeline completed successfully!")

    except Exception as e:
        print_error(f"\n❌ Pipeline failed: {str(e)}")
        raise
