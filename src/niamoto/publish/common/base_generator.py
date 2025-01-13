import json
from typing import Optional, Any, Dict
from niamoto.core.models import TaxonRef, PlotRef, ShapeRef
from shapely import wkt
from shapely.geometry import mapping


class BaseGenerator:
    """
    The BaseGenerator class provides common methods for generating data dictionaries.
    """

    @staticmethod
    def parse_json_field(field: Any) -> Any:
        """

        Returns:

        """
        if isinstance(field, str):
            try:
                return json.loads(field)
            except json.JSONDecodeError:
                return field
        return field

    def taxon_to_dict(self, taxon: TaxonRef, stats: Optional[Any]) -> Dict[str, Any]:
        """
        Converts a TaxonRef object to a dictionary.
        Args:
            taxon (TaxonRef): The TaxonRef object to convert.
            stats (dict, optional): A dictionary containing statistics for the taxon.

        Returns:
            dict: The dictionary representation of the TaxonRef object.

        """
        stats_dict = {
            "id": taxon.id,
            "full_name": taxon.full_name,
            "authors": taxon.authors,
            "rank_name": taxon.rank_name,
            "metadata": taxon.extra_data if taxon.extra_data is not None else {},
            "lft": taxon.lft,
            "rght": taxon.rght,
            "level": taxon.level,
            "parent_id": taxon.parent_id,
        }

        if stats:
            # Parse les champs JSON
            parsed_stats = {}
            for key, value in stats.items():
                parsed_stats[key] = self.parse_json_field(value)
            stats_dict.update(parsed_stats)

        return stats_dict

    def plot_to_dict(self, plot: PlotRef, stats: Optional[Any]) -> Dict[str, Any]:
        """
        Converts a PlotRef object to a dictionary.
        Args:
            plot (PlotRef): The PlotRef object to convert.
            stats (dict, optional): A dictionary containing statistics for the plot.

        Returns:
            dict: The dictionary representation of the PlotRef object.

        """
        geometry_str = str(plot.geometry) if plot.geometry is not None else None
        stats_dict = {
            "id": plot.id,
            "locality": plot.locality,
            "geometry": mapping(wkt.loads(geometry_str))
            if geometry_str is not None
            else None,
        }

        if stats:
            # Parse les champs JSON
            parsed_stats = {}
            for key, value in stats.items():
                parsed_stats[key] = self.parse_json_field(value)
            stats_dict.update(parsed_stats)

        return stats_dict

    def shape_to_dict(self, shape: ShapeRef, stats: Optional[Any]) -> Dict[str, Any]:
        """
        Converts a ShapeRef object to a dictionary with detailed information.

        Args:
            shape (niamoto.core.models.models.ShapeRef): The shape object to convert.
            stats (dict, optional): A dictionary containing statistics for the shape.

        Returns:
            dict: A detailed dictionary representation of the shape.
        """

        # Conversion en dictionnaire de base
        stats_dict = {
            "id": shape.id,
            "name": shape.label,
            "type": shape.type,
        }

        # Ajout des statistiques s'il y en a
        if stats:
            # Parse les champs JSON
            parsed_stats = {}
            for key, value in stats.items():
                parsed_stats[key] = self.parse_json_field(value)
            stats_dict.update(parsed_stats)

        return stats_dict
