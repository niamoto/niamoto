import logging
import time
from typing import List, Dict, Any, Hashable, Union

import pandas as pd
import rasterio
from rasterio.mask import mask
from rtree import index
from shapely.geometry import mapping
from shapely.wkb import loads as wkb_loads
from shapely.wkt import loads as wkt_loads
from shapely.errors import WKTReadingError


from niamoto.core.models import ShapeRef
from .statistics_calculator import StatisticsCalculator


class ShapeStatsCalculator(StatisticsCalculator):
    """
    A class used to calculate statistics for shapes.

    Inherits from:
        StatisticsCalculator
    """

    def calculate_shape_stats(self) -> None:
        """
        Calculate statistics for all shapes.
        """
        start_time = time.time()

        try:
            shapes = self._retrieve_all_shapes()

            self.initialize_stats_table()

            for shape_ref in shapes:
                self.process_shape(shape_ref)

        except Exception as e:
            logging.error(f"An error occurred: {e}")
            self.console.print(f"An error occurred: {e}", style="bold red")
        finally:
            total_time = time.time() - start_time
            self.console.print(
                f"Total processing time: {total_time:.2f} seconds", style="italic blue"
            )

    def process_shape(self, shape_ref: ShapeRef) -> None:
        """
        Process a shape.

        Args:
            shape_ref (ShapeRef): The shape to process.
        """
        try:
            shape_id = self._extract_shape_id(shape_ref)
            if shape_id is None:
                return

            logging.debug(f"Processing shape with ID: {shape_id}")

            shape_occurrences = self.get_shape_occurrences(shape_ref)
            print(len(shape_occurrences))
            if not shape_occurrences:
                return

            stats = self.calculate_stats(shape_id, shape_occurrences)

            self.create_or_update_stats_entry(shape_id, stats)

        except Exception as e:
            logging.error(f"Failed to process shape {shape_ref.id}: {e}")
            self.console.print(
                f"Failed to process shape {shape_ref.id}: {e}", style="bold red"
            )

    def calculate_stats(
        self, group_id: int, group_occurrences: list[dict[Hashable, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate statistics for a group.

        Args:
            group_id (int): The group id.
            group_occurrences (list[dict[Hashable, Any]]): The group occurrences.

        Returns:
            Dict[str, Any]: The statistics.
        """
        logging.debug(f"Calculating stats for group ID: {group_id}")

        shape_ref = (
            self.db.session.query(ShapeRef).filter(ShapeRef.id == group_id).first()
        )
        stats: Dict[str, Union[int, Dict[str, Any], pd.Series[Any], float]] = {}

        # Convert occurrences to pandas DataFrame
        df_occurrences = pd.DataFrame(group_occurrences)

        # Iterate over fields in the mapping
        for field, field_config in self.fields.items():
            source_field = field_config.get("source_field")
            source = field_config.get("source")
            rank_type = field_config.get("rank_type", None)

            logging.debug(
                f"Processing field: {field}, source: {source}, source_field: {source_field}"
            )

            if source_field is None:
                # Special field without source_field (ex: total_occurrences)
                if field_config.get("transformations"):
                    for transformation in field_config.get("transformations", []):
                        if transformation.get("name") == "count":
                            stats[field] = len(group_occurrences)
                            break

            elif source == "shapes":
                if source_field in ["shape_location", "forest_location"]:
                    # Calculate area
                    stats[field] = self.calculate_area(
                        shape_ref.__dict__.get(source_field, "")
                    )

            elif source == "occurrences":
                if rank_type:
                    stats[field] = self.calculate_unique_ranks(
                        df_occurrences, rank_type
                    )
                else:
                    # Handle count and other transformations for occurrences
                    transformations = field_config.get("transformations", [])
                    for transformation in transformations:
                        transform_name = transformation.get("name")
                        logging.debug(
                            f"Applying transformation: {transform_name} to field: {field}"
                        )
                        if transform_name == "count":
                            stats[field] = len(group_occurrences)
                        elif transform_name == "unique":
                            stats[field] = df_occurrences[source_field].nunique()

            elif "rasters" in source:
                if source_field in ["altitude", "rainfall"]:
                    stats[field] = self.calculate_raster_stats(
                        shape_ref, source, source_field, field_config
                    )

        # Add group-specific stats
        specific_stats = self.calculate_specific_stats(group_id, group_occurrences)
        stats.update(specific_stats)

        return stats

    def calculate_specific_stats(
        self, group_id: int, group_occurrences: list[dict[Hashable, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate specific statistics for a shape.

        Args:
            group_id (int): The group id.
            group_occurrences (list[dict[Hashable, Any]]): The group occurrences.

        Returns:
            Dict[str, Any]: The specific statistics.
        """
        logging.debug(f"Calculating specific stats for group ID: {group_id}")

        shape_ref = (
            self.db.session.query(ShapeRef).filter(ShapeRef.id == group_id).first()
        )
        specific_stats: Dict[str, Any] = {}

        # Example for calculating fragmentation
        if "fragmentation" in self.fields:
            specific_stats["fragmentation"] = self.calculate_fragmentation(shape_ref)

        # Example for calculating forest coverage
        if "forest_coverage" in self.fields:
            specific_stats["forest_coverage"] = self.calculate_forest_coverage(
                shape_ref, group_occurrences
            )

        # Add other specific field calculations here...

        return specific_stats

    def calculate_area(self, wkt_geometry: str) -> float:
        """
        Calculate the area of a geometry from its WKT representation.

        Args:
            wkt_geometry (str): The WKT representation of the geometry.

        Returns:
            float: The area of the geometry.
        """
        geom = wkb_loads(wkt_geometry)
        return geom.area

    def calculate_unique_ranks(
        self, df_occurrences: pd.DataFrame, rank_type: str
    ) -> int:
        """
        Calculate the number of unique ranks (families, species, etc.).

        Args:
            df_occurrences (pd.DataFrame): DataFrame containing occurrences.
            rank_type (str): The rank type to calculate (e.g., 'id_family').

        Returns:
            int: The number of unique ranks.
        """
        return df_occurrences[rank_type].nunique()

    def calculate_raster_stats(
        self,
        shape_ref: ShapeRef,
        raster_path: str,
        source_field: str,
        field_config: dict,
    ) -> float:
        """
        Calculate statistics from raster data.

        Args:
            shape_ref (ShapeRef): The shape object.
            raster_path (str): The path to the raster file.
            source_field (str): The target field in the raster.
            field_config (dict): The field configuration.

        Returns:
            float: The calculated raster statistic.
        """
        with rasterio.open(raster_path) as src:
            shape_geom = wkb_loads(shape_ref.shape_location)
            out_image, out_transform = mask(src, [mapping(shape_geom)], crop=True)
            out_image = out_image[out_image != src.nodata]

            if "mean" in [t["name"] for t in field_config["transformations"]]:
                return out_image.mean()

            if "max" in [t["name"] for t in field_config["transformations"]]:
                return out_image.max()

            if "median" in [t["name"] for t in field_config["transformations"]]:
                return pd.Series(out_image.flatten()).median()

        return 0.0

    def calculate_fragmentation(self, shape_ref: ShapeRef) -> float:
        """
        Calculate the fragmentation metric for the forest areas within the shape.

        Args:
            shape_ref (ShapeRef): The shape object.

        Returns:
            float: The fragmentation metric.
        """
        # Placeholder for actual fragmentation calculation logic
        return 91.3  # Example value

    def calculate_forest_coverage(
        self, shape_ref: ShapeRef, occurrences: list[dict[Hashable, Any]]
    ) -> Dict[str, float]:
        """
        Calculate the forest coverage within the shape.

        Args:
            shape_ref (ShapeRef): The shape object.
            occurrences (list[dict[Hashable, Any]]): The occurrences within the shape.

        Returns:
            Dict[str, float]: The forest coverage percentages.
        """
        total_area = self.calculate_area(shape_ref.shape_location)
        forest_area = self.calculate_area(shape_ref.forest_location)
        forest_coverage_percentage = (forest_area / total_area) * 100
        return {
            "forest_area": forest_area,
            "total_area": total_area,
            "forest_coverage_percentage": forest_coverage_percentage,
        }

    def _retrieve_all_shapes(self) -> List[ShapeRef]:
        """
        Retrieve all shapes from the database.

        Returns:
            List[ShapeRef]: A list of shape references.
        """
        return self.db.session.query(ShapeRef).all()

    @staticmethod
    def _extract_shape_id(shape_ref: ShapeRef) -> int:
        """
        Extract the shape ID value.

        Args:
            shape_ref (ShapeRef): The shape from which to extract the ID.

        Returns:
            int: The shape ID.
        """
        return shape_ref.id

    def build_spatial_index(self) -> index.Index:
        """
        Build a spatial index for all occurrences.

        Returns:
            index.Index: An R-tree spatial index.
        """
        idx = index.Index()
        occurrence_location_field = self.group_config.get("source_location_field")

        for pos, occurrence in enumerate(self.occurrences):
            if isinstance(occurrence, dict):
                point_wkt = occurrence.get(occurrence_location_field)
                if (
                    point_wkt is not None
                    and isinstance(point_wkt, str)
                    and point_wkt.startswith("POINT")
                ):
                    try:
                        point_geom = wkt_loads(point_wkt)
                        if point_geom:
                            idx.insert(pos, point_geom.bounds)
                    except Exception as e:
                        logging.error(f"Error processing occurrence {occurrence}: {e}")

        return idx

    def get_shape_occurrences(self, shape_ref: ShapeRef) -> List[Dict[Hashable, Any]]:
        """
        Get shape occurrences.

        Args:
            shape_ref (ShapeRef): The shape to get occurrences for.

        Returns:
            List[Dict[Hashable, Any]]: The shape occurrences.
        """
        logging.debug(f"Getting occurrences for shape with ID: {shape_ref.id}")

        try:
            # Convert the WKB string to a Shapely geometry
            shape_geom = wkb_loads(bytes.fromhex(shape_ref.shape_location))
        except Exception as e:
            logging.error(
                f"Failed to load shape geometry for shape ID {shape_ref.id}: {e}"
            )
            return []

        occurrence_location_field = self.group_config.get("source_location_field")

        # Build the spatial index
        spatial_index = self.build_spatial_index()
        occurrences_within_shape = []

        # Pre-fetch the bounds of the shape_geom to avoid redundant calls
        shape_bounds = shape_geom.bounds

        # Collect the positions of occurrences that intersect with the shape bounds
        positions = list(spatial_index.intersection(shape_bounds))

        # Create a DataFrame for the relevant occurrences
        relevant_occurrences = [self.occurrences[pos] for pos in positions]
        df_occurrences = pd.DataFrame(relevant_occurrences)

        # Check if occurrences are within the shape
        def is_within_shape(wkt_str):
            try:
                point_geom = wkt_loads(wkt_str)
                return shape_geom.contains(point_geom)
            except WKTReadingError:
                return False

        # Apply the filtering function to the DataFrame
        df_occurrences["is_within_shape"] = df_occurrences[
            occurrence_location_field
        ].apply(is_within_shape)
        filtered_occurrences = df_occurrences[df_occurrences["is_within_shape"]]

        # Convert the filtered DataFrame back to a list of dictionaries
        occurrences_within_shape = filtered_occurrences.drop(
            columns=["is_within_shape"]
        ).to_dict("records")

        return occurrences_within_shape
