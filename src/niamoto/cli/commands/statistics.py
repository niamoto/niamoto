# commands/statistics.py

"""
Commands for calculating various statistics in Niamoto.
"""

import click
from typing import Optional

from ..utils.console import print_success, print_error
from niamoto.core.services.statistics import StatisticService
from niamoto.common.config import Config


@click.group(name="stats")
def statistic_commands():
    """Commands for calculating statistics."""
    pass


@statistic_commands.command(name="calculate")
@click.option(
    "--group",
    type=str,
    help="Group to calculate statistics for (e.g., taxon, plot).",
)
@click.option(
    "--csv-file",
    type=str,
    help="Optional CSV file with occurrence data.",
)
def calculate_statistics(group: Optional[str], csv_file: Optional[str]) -> None:
    """Calculate statistics for specified group."""
    try:
        config = Config()
        service = StatisticService(config.database_path, config)
        service.calculate_statistics(group_by=group, csv_file=csv_file)
        print_success("Statistics calculated successfully")

    except Exception as e:
        print_error(f"Statistics calculation failed: {str(e)}")
        raise click.Abort()
