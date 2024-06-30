import json
import logging
import os
import time
from typing import List, Dict, Any, Hashable, Union

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from pyproj import Transformer
from rasterio.mask import mask
from rtree import index
from shapely import box, MultiPolygon
from shapely.geometry import mapping, shape
from shapely.ops import transform
from shapely.wkb import loads as wkb_loads
from shapely.wkt import loads as wkt_loads
from shapely.errors import WKTReadingError

from niamoto.core.models import ShapeRef, TaxonRef
from .statistics_calculator import StatisticsCalculator

from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn


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

            # Sort shapes by area in ascending order
            shapes.sort(key=lambda shape_ref: self.calculate_area(shape_ref.shape_location))

            self.initialize_stats_table()

            with Progress(
                    SpinnerColumn(),
                    BarColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    TimeElapsedColumn()
            ) as progress:
                task = progress.add_task("[green]Calculating shape statistics...", total=len(shapes))
                for shape_ref in shapes:
                    self.process_shape(shape_ref)
                    progress.advance(task)

        except Exception as e:
            logging.error(f"An error occurred: {e}")
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

            shape_occurrences = self.get_shape_occurrences(shape_ref)
            if not shape_occurrences:
                return

            stats = self.calculate_stats(shape_id, shape_occurrences)

            self.create_or_update_stats_entry(shape_id, stats)

        except Exception as e:
            logging.error(f"Failed to process shape {shape_ref.id}: {e}")

    def get_shape_occurrences(self, shape_ref: ShapeRef) -> List[Dict[Hashable, Any]]:
        """
        Get shape occurrences.

        Args:
            shape_ref (ShapeRef): The shape to get occurrences for.

        Returns:
            List[Dict[Hashable, Any]]: The shape occurrences.
        """

        try:
            # Convert the WKB string to a Shapely geometry
            shape_geom = wkb_loads(bytes.fromhex(shape_ref.shape_location))

            # Simplify the shape geometry to speed up operations
            shape_geom = shape_geom.simplify(tolerance=0.01, preserve_topology=True)
        except Exception as e:
            logging.error(
                f"Failed to load shape geometry for shape ID {shape_ref.id}: {e}"
            )
            return []

        occurrence_location_field = self.group_config.get("source_location_field")

        # Build the spatial index
        spatial_index = self.build_spatial_index()

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

    def calculate_stats(self, group_id: int, group_occurrences: list) -> dict:
        stats = {}
        shape_ref = self.db.session.query(ShapeRef).filter(ShapeRef.id == group_id).first()
        df_occurrences = pd.DataFrame(group_occurrences)

        for field, config in self.fields.items():
            source_field = config.get('source_field')
            transformations = config.get('transformations', [])

            for transformation in transformations:
                transform_name = transformation.get('name')
                chart_type = transformation.get('chart_type')
                column_name = f"{field}_{transform_name}"

                if transform_name == 'area':
                    stats[column_name] = self.calculate_area(getattr(shape_ref, source_field))

                elif transform_name == 'coordinates' and chart_type == 'map':
                    stats[column_name] = self.get_simplified_coordinates(shape_ref.__dict__.get(source_field, ""))

                elif transform_name == 'count':
                    stats[column_name] = len(group_occurrences)

                elif transform_name == 'unique_taxonomic_count':
                    target_ranks = transformation.get('target_ranks')
                    stats[column_name] = self.calculate_unique_taxonomic_count(group_occurrences, target_ranks)

                elif transform_name == 'range':
                    raster_data = self.get_raster_data(config.get('source'), shape_ref)
                    if raster_data is not None and raster_data.size > 0:
                        min_val, max_val = self.calculate_range(raster_data)
                        stats[column_name] = json.dumps({
                            "min": float(min_val),
                            "max": float(max_val)
                        })
                    else:
                        stats[column_name] = json.dumps({
                            "min": 0.0,
                            "max": 0.0
                        })

                elif transform_name == 'median':
                    raster_data = self.get_raster_data(config.get('source'), shape_ref)
                    stats[column_name] = self.calculate_median(
                        raster_data) if raster_data is not None and raster_data.size > 0 else 0.0

                elif transform_name == 'max':
                    raster_data = self.get_raster_data(config.get('source'), shape_ref)
                    stats[column_name] = self.calculate_max(
                        raster_data) if raster_data is not None and raster_data.size > 0 else 0.0

                elif transform_name == 'fragmentation':
                    stats[column_name] = self.calculate_fragmentation(shape_ref)

                elif transform_name == 'cumulative_area':
                    stats[column_name] = self.calculate_forest_fragmentation(shape_ref)

        return stats

    def calculate_unique_taxonomic_count(self, occurrences: list[dict[Hashable, Any]], target_ranks: list[str]) -> int:
        """
        Calculate the unique count of taxonomic ranks in the occurrences.

        Args:
            occurrences (list[dict[Hashable, Any]]): The occurrences to calculate statistics for.
            target_ranks (list[str]): The taxonomic ranks to count.

        Returns:
            int: The unique count of the specified taxonomic ranks.
        """
        taxon_ids = {occ.get("taxon_ref_id") for occ in occurrences if occ.get("taxon_ref_id")}
        if not taxon_ids:
            return 0

        # Retrieve the taxons from the database
        taxons = self.db.session.query(TaxonRef).filter(TaxonRef.id.in_(taxon_ids)).all()
        taxon_dict = {taxon.id: taxon for taxon in taxons}

        # Retrieve the parent taxons of the taxons
        parent_ids = {taxon.parent_id for taxon in taxons if taxon.parent_id is not None}
        while parent_ids:
            parent_taxons = self.db.session.query(TaxonRef).filter(TaxonRef.id.in_(parent_ids)).all()
            for parent_taxon in parent_taxons:
                taxon_dict[parent_taxon.id] = parent_taxon
            parent_ids = {taxon.parent_id for taxon in parent_taxons if
                          taxon.parent_id is not None and taxon.parent_id not in taxon_dict}

        unique_taxons = set()

        # Count the unique taxons at the specified ranks
        for taxon in taxon_dict.values():
            current_taxon = taxon
            while current_taxon:
                if current_taxon.rank_name in target_ranks:
                    unique_taxons.add(current_taxon.id)
                    break
                current_taxon = taxon_dict.get(current_taxon.parent_id)

        return len(unique_taxons)

    @staticmethod
    def get_raster_data(raster_path: str, shape_ref: ShapeRef) -> np.array:
        full_raster_path = f"data/sources/{raster_path}"

        if not os.path.exists(full_raster_path):
            logging.error(f"Raster file not found: {full_raster_path}")
            return None

        try:
            with rasterio.open(full_raster_path) as src:
                shape_geom = wkb_loads(bytes.fromhex(shape_ref.shape_location))

                # Transform shape geometry if CRS are different
                shape_crs = "EPSG:4326"  # Assuming shape CRS is WGS84 (longitude/latitude)
                raster_crs = src.crs.to_string()  # CRS of the raster
                if shape_crs != raster_crs:
                    transformer = Transformer.from_crs(shape_crs, raster_crs, always_xy=True)
                    shape_geom = transform(transformer.transform, shape_geom)

                raster_bounds_geom = box(*src.bounds)
                if not shape_geom.intersects(raster_bounds_geom):
                    logging.error(f"Shape ID {shape_ref.id} does not overlap with the raster.")
                    return np.array([])

                # Simplify the shape geometry to speed up operations
                shape_geom = shape_geom.simplify(tolerance=0.01, preserve_topology=True)

                out_image, out_transform = mask(src, [mapping(shape_geom)], crop=True)
                out_image = out_image[out_image != src.nodata]

                if out_image.size == 0:
                    logging.error(f"No data found within the shape for shape ID {shape_ref.id}.")
                    return np.array([])

                return out_image

        except Exception as e:
            logging.error(f"Failed to process shape {shape_ref.id}: {e}")
            return None

    @staticmethod
    def calculate_area(wkt_geometry: str) -> float:
        """
        Calculate the area of a geometry in hectares.

        Args:
            wkt_geometry (str): The WKT representation of the geometry.

        Returns:
            float: The area of the geometry in hectares.
        """
        geom = wkb_loads(wkt_geometry)

        # Define the coordinate system transformation
        transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)

        # Reproject the geometry to EPSG:3857
        geom_projected = transform(transformer.transform, geom)

        # Calculate the area in square meters
        area_sqm = geom_projected.area

        # Convert square meters to hectares
        area_hectares = area_sqm / 10000

        return area_hectares

    @staticmethod
    def calculate_range(raster_data) -> (float, float):
        return raster_data.min(), raster_data.max()

    @staticmethod
    def calculate_median(data) -> float:
        return np.median(data)

    @staticmethod
    def calculate_max(data) -> float:
        return data.max()

    @staticmethod
    def get_simplified_coordinates(wkt_geometry: str) -> dict:
        geom = wkb_loads(wkt_geometry)
        simplified_geom = geom.simplify(tolerance=0.001, preserve_topology=True)
        return mapping(simplified_geom)

    @staticmethod
    def calculate_fragmentation(shape_ref: ShapeRef) -> float:
        """
        Calculate the effective mesh size for the forest areas within the shape.

        Args:
            shape_ref (ShapeRef): The shape object.

        Returns:
            float: The effective mesh size.
        """
        try:
            shape_geom = wkb_loads(bytes.fromhex(shape_ref.forest_location))

            if shape_geom.geom_type == 'GeometryCollection' or shape_geom.geom_type == 'MultiPolygon':
                forest_fragments = [shape(fragment) for fragment in shape_geom.geoms]
            else:
                forest_fragments = [shape_geom]

            total_forest_area = sum(fragment.area for fragment in forest_fragments)
            effective_mesh_size = total_forest_area / len(forest_fragments)
            return effective_mesh_size

        except Exception as e:
            logging.error(f"Failed to calculate fragmentation for shape ID {shape_ref.id}: {e}")
            return 0.0

    def calculate_forest_fragmentation(self, shape_ref: ShapeRef) -> Dict[str, float]:
        """
        Calculate the forest fragmentation for the fragments within the shape.

        Args:
            shape_ref (ShapeRef): The shape object.

        Returns:
            Dict[str, float]: A dictionary with class names and their corresponding cumulative areas.
        """
        try:
            shape_geom = wkb_loads(bytes.fromhex(shape_ref.forest_location))

            # Verify if the geometry is of type MultiPolygon
            if isinstance(shape_geom, MultiPolygon):
                forest_fragments = [shape(fragment) for fragment in shape_geom.geoms]
            else:
                forest_fragments = [shape_geom]

            # Convert the forest fragments to a GeoDataFrame
            gdf = gpd.GeoDataFrame(geometry=forest_fragments, crs="EPSG:4326")

            # Reproject to UTM to get areas in square meters
            gdf = gdf.to_crs(gdf.estimate_utm_crs())

            # Calculate the area of each fragment in hectares
            gdf['area_ha'] = gdf.area / 10000  # Convertir les mètres carrés en hectares
            fragment_areas = gdf['area_ha'].to_numpy()
            fragment_areas.sort()

            # Define the bins for the cumulative area
            bins = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 125, 150, 175, 200, 225, 250, 275, 300, 325, 350, 375, 400,
                    425, 450, 475, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900,
                    2000, 7000, 12000, 17000, 27000, 500000]

            # Initialise the dictionary to store the cumulative areas
            bin_areas = {str(bin_val): 0.0 for bin_val in bins}

            # Calculate the total area of forest fragments
            total_area = fragment_areas.sum()
            if total_area == 0:
                logging.warning(f"Total area of forest fragments is zero for shape ID {shape_ref.id}.")
                return bin_areas

            # Calculate the cumulative area for each bin
            cumulative_area = 0.0
            fragment_index = 0

            for bin_val in bins:
                while fragment_index < len(fragment_areas) and fragment_areas[fragment_index] <= bin_val:
                    cumulative_area += fragment_areas[fragment_index]
                    fragment_index += 1
                bin_areas[str(bin_val)] = cumulative_area / total_area

            return bin_areas

        except Exception as e:
            logging.error(f"Failed to calculate forest fragmentation for shape ID {shape_ref.id}: {e}")
            return {}

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
