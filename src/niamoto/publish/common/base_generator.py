import json
from typing import Optional, Any, Dict
from niamoto.core.models import TaxonRef, PlotRef, ShapeRef
from shapely import wkt
from shapely.geometry import mapping, shape


class BaseGenerator:
    """
    The BaseGenerator class provides common methods for generating data dictionaries.
    """

    @staticmethod
    def taxon_to_dict(taxon: TaxonRef, stats: Optional[Any]) -> Dict[str, Any]:
        """
        Converts a TaxonRef object to a dictionary.
        Args:
            taxon (TaxonRef): The TaxonRef object to convert.
            stats (dict, optional): A dictionary containing statistics for the taxon.

        Returns:
            dict: The dictionary representation of the TaxonRef object.

        """
        taxon_dict = {
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
            frequencies = {}
            for key, value in stats.items():
                if key.endswith("_bins"):
                    freq_key = key[:-5]
                    if value is not None:
                        frequencies[freq_key] = json.loads(value.replace("'", '"'))
                else:
                    taxon_dict[key] = value

            taxon_dict["frequencies"] = frequencies

        return taxon_dict

    @staticmethod
    def plot_to_dict(plot: PlotRef, stats: Optional[Any]) -> Dict[str, Any]:
        """
        Converts a PlotRef object to a dictionary.
        Args:
            plot (PlotRef): The PlotRef object to convert.
            stats (dict, optional): A dictionary containing statistics for the plot.

        Returns:
            dict: The dictionary representation of the PlotRef object.

        """
        geometry_str = str(plot.geometry) if plot.geometry is not None else None
        plot_dict = {
            "id": plot.id,
            "locality": plot.locality,
            "geometry": mapping(wkt.loads(geometry_str)) if geometry_str is not None else None,
        }

        if stats:
            frequencies = {}
            for key, value in stats.items():
                if key.endswith("_bins"):
                    freq_key = key[:-5]
                    if value is not None:
                        frequencies[freq_key] = json.loads(value.replace("'", '"'))
                else:
                    plot_dict[key] = value

            plot_dict["frequencies"] = frequencies

        return plot_dict

    @staticmethod
    def shape_to_dict(shape_ref: ShapeRef, stats: Optional[Any]) -> Dict[str, Any]:
        """
        Converts a ShapeRef object to a dictionary with detailed information.

        Args:
            shape_ref (niamoto.core.models.models.ShapeRef): The shape object to convert.
            stats (dict, optional): A dictionary containing statistics for the shape.

        Returns:
            dict: A detailed dictionary representation of the shape.
        """
        shape_dict = {
            "id": shape_ref.id,
            "name": shape_ref.label,
            "type": shape_ref.type,
        }

        if stats:
            simplify_tolerance = 0.01  # Adjust tolerance as needed
            if "shape_coordinates" in stats and stats["shape_coordinates"]:
                try:
                    shape_coords = json.loads(stats["shape_coordinates"])

                    if shape_coords.get("type").lower() == "featurecollection":
                        features = shape_coords["features"]
                        simplified_features = []

                        for feature in features:
                            geom = shape(feature["geometry"])
                            simplified_geom = geom.simplify(
                                simplify_tolerance, preserve_topology=True
                            )
                            feature["geometry"] = mapping(simplified_geom)
                            simplified_features.append(feature)

                        shape_dict["shape_coordinates"] = {
                            "type": "FeatureCollection",
                            "features": simplified_features,
                        }
                    else:
                        shape_geom = shape(shape_coords)
                        simplified_shape_geom = shape_geom.simplify(
                            simplify_tolerance, preserve_topology=True
                        )
                        shape_dict["shape_coordinates"] = mapping(simplified_shape_geom)

                except (json.JSONDecodeError, TypeError):
                    shape_dict["shape_coordinates"] = None

            if "forest_coordinates" in stats and stats["forest_coordinates"]:
                try:
                    forest_coords = json.loads(stats["forest_coordinates"])

                    forest_geom = shape(forest_coords)
                    simplified_forest_geom = forest_geom.simplify(
                        simplify_tolerance, preserve_topology=True
                    )
                    shape_dict["forest_coordinates"] = mapping(simplified_forest_geom)

                except (json.JSONDecodeError, TypeError):
                    shape_dict["forest_coordinates"] = None

            frequencies = {}
            for key, value in stats.items():
                if key.endswith("_bins"):
                    freq_key = key[:-5]
                    if value is not None:
                        frequencies[freq_key] = json.loads(value.replace("'", '"'))
                else:
                    shape_dict[key] = value

            shape_dict["frequencies"] = frequencies

        return shape_dict
