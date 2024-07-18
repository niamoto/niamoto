"""
Shape statistics calculator module.
"""
import logging
import time
from typing import List, Dict, Any, Hashable, Optional, cast

import geopandas as gpd  # type: ignore
import numpy as np
import pandas as pd
import pyproj
import rasterio  # type: ignore
from matplotlib import pyplot as plt
from rasterio.features import rasterize  # type: ignore
from rasterio.mask import mask  # type: ignore
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rtree import index
from shapely import (
    MultiPolygon,
    GeometryCollection,
    Polygon,
    polygonize,
    make_valid,
    unary_union,
)
from shapely.errors import WKTReadingError
from shapely.geometry import mapping, Point
from shapely.geometry.base import BaseGeometry
from shapely.prepared import prep
from shapely.wkt import loads as wkt_loads

from niamoto.common.database import Database
from niamoto.core.models import ShapeRef, TaxonRef
from .statistics_calculator import StatisticsCalculator
from ...services.mapper import MapperService

LARGE_SHAPE_THRESHOLD_KM2 = 1000


class ShapeStatsCalculator(StatisticsCalculator):
    """
    A class used to calculate statistics for shapes.

    Inherits from:
        StatisticsCalculator
    """

    def __init__(
            self,
            db: Database,
            mapper_service: MapperService,
            occurrences: list[dict[Hashable, Any]],
            group_by: str,
    ):
        super().__init__(
            db, mapper_service, occurrences, group_by, log_component="shape_stats"
        )

    def calculate_shape_stats(self) -> None:
        """
        Calculate statistics for all shapes.
        """
        start_time = time.time()

        try:
            shapes = self._retrieve_all_shapes()

            self.initialize_stats_table()

            with Progress(
                    SpinnerColumn(),
                    BarColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    TimeElapsedColumn(),
            ) as progress:
                task = progress.add_task(
                    "[green]Calculating shape statistics...", total=len(shapes)
                )
                for shape_ref in shapes:
                    self.process_shape(shape_ref)
                    progress.advance(task)

        except Exception as e:
            logging.error(f"An error occurred: {e}")
        finally:
            total_time = time.time() - start_time
            self.console.print(
                f"⏱ Total processing time: {total_time:.2f} seconds",
                style="italic blue",
            )

    def process_shape(self, shape_ref: ShapeRef) -> None:
        """
        Process a shape.

        Args:
            shape_ref (ShapeRef): The shape to process.
        """
        try:
            shape_id = self._extract_shape_id(shape_ref)

            shape_occurrences = self.get_shape_occurrences(shape_ref)
            if not shape_occurrences:
                return

            stats = self.calculate_stats(shape_id, shape_occurrences)

            self.create_or_update_stats_entry(shape_id, stats)

        except Exception as e:
            self.logger.error(f"Failed to process shape {shape_ref.id}: {e}")

    def get_shape_occurrences(self, shape_ref: ShapeRef) -> List[Dict[Hashable, Any]]:
        """
        Get shape occurrences.

        Args:
            shape_ref (ShapeRef): The shape to get occurrences for.

        Returns:
            List[Dict[Hashable, Any]]: The shape occurrences.
        """
        try:
            shape_gdf = self.load_shape_geometry(str(shape_ref.location))
            if shape_gdf is None or shape_gdf.empty:
                self.logger.error(f"Invalid geometry for shape ID {shape_ref.id}.")
                return []

            shape_geom = shape_gdf.geometry.iloc[0]
            prepared_shape = prep(shape_geom)
        except Exception as e:
            self.logger.error(
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

        if df_occurrences.empty:
            return []

        # Check if occurrences are within the shape
        def is_within_shape(wkt_str: str) -> bool:
            """
            Check if a point is within the shape.
            Args:
                wkt_str (str): The WKT representation of the point.

            Returns:
                bool: True if the point is within the shape, False otherwise.

            """
            try:
                point_geom = wkt_loads(wkt_str)
                return prepared_shape.contains(point_geom)
            except WKTReadingError:
                self.logger.warning(f"Invalid WKT: {wkt_str}")
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

    def calculate_stats(self, group_id: int, group_occurrences: List[Dict[Hashable, Any]]) -> Dict[str, Any]:
        """
        Calculate statistics for a given shape and its occurrences.

        Args:
            group_id (int): The ID of the shape.
            group_occurrences (list): The occurrences related to the shape.

        Returns:
            dict: The calculated statistics.
        """
        stats: Dict[str, Any] = {}
        shape_ref = (
            self.db.session.query(ShapeRef).filter(ShapeRef.id == group_id).first()
        )

        if shape_ref is None:
            self.logger.error(f"Shape with ID {group_id} not found.")
            return stats

        # Load and clean shape geometry once
        shape_gdf = self.load_shape_geometry(str(shape_ref.location))
        if shape_gdf is None or shape_gdf.empty:
            self.logger.error(f"Shape geometry for {group_id} is invalid.")
            return stats

        # Load layers once
        loaded_layers = self.load_all_layers(shape_gdf)

        for field, config in self.fields.items():
            data_sources = config.get("data_source", {})
            if not isinstance(data_sources, list):
                data_sources = [data_sources]
            transformations = config.get("transformations", [])

            try:
                for data_source in data_sources:
                    if data_source.get("type") == "layer":
                        layer_name = data_source.get("name")
                        gdf = loaded_layers.get(layer_name)
                        if gdf is not None and not gdf.empty and shape_ref is not None:
                            stats.update(
                                self.process_layer_stats(
                                    shape_ref, gdf, field, transformations
                                )
                            )
                        else:
                            self.logger.warning(
                                f"Empty GeoDataFrame for {layer_name} in shape {group_id}"
                            )
                    elif (
                            data_source.get("type") == "shape"
                            and data_source.get("name") == "self" and shape_ref is not None
                    ):
                        stats.update(
                            self.process_shape_stats(shape_ref, field, transformations)
                        )
                    elif (
                            data_source.get("type") == "source"
                            and data_source.get("name") == "occurrences"
                    ):
                        stats.update(
                            self.process_occurrence_stats(
                                group_occurrences, field, transformations
                            )
                        )
            except Exception as e:
                self.logger.error(
                    f"Error processing {field} for shape {group_id}: {str(e)}"
                )

        return stats

    def load_all_layers(
            self, shape_gdf: Any
    ) -> Dict[str, Any]:
        """
        Load all layers based on the configuration.

        Args:
            shape_gdf (Any): The shape geometry DataFrame.

        Returns:
            Dict[str, Any]: A dictionary of loaded and clipped layers.
        """
        loaded_layers = {}

        for _field, config in self.fields.items():
            data_sources = config.get("data_source", {})
            if not isinstance(data_sources, list):
                data_sources = [data_sources]

            for data_source in data_sources:
                if data_source.get("type") == "layer":
                    layer_name = data_source.get("name")
                    if layer_name not in loaded_layers:
                        layer_type = self.mapper_service.get_layer_type(layer_name)
                        if layer_type is not None:
                            gdf = self.load_layer_as_gdf(shape_gdf, layer_name, layer_type)
                            loaded_layers[layer_name] = gdf

        return loaded_layers

    def load_layer_as_gdf(
            self, shape_gdf: Any, layer_name: str, layer_type: str
    ) -> Any:
        """
        Load a layer as a GeoDataFrame and clip it to the shape geometry.

        Args:
            shape_gdf (Any): The shape geometry DataFrame.
            layer_name (str): The name of the layer.
            layer_type (str): The type of the layer ('raster' or 'vector').

        Returns:
            Any: The loaded and clipped layer data.
        """
        layer_path = self.mapper_service.get_layer_path(layer_name)

        if layer_type == "raster":
            with rasterio.open(layer_path) as src:
                raster_crs = src.crs
                shape_gdf = shape_gdf.to_crs(raster_crs)

                try:
                    out_image, out_transform = mask(src, shape_gdf.geometry, crop=True)
                    out_image = out_image[0]  # Get the first band
                    valid_data = out_image[out_image != src.nodata]

                    if valid_data.size == 0:
                        self.logger.warning(
                            f"No data found within the shape for {layer_name}."
                        )
                        return gpd.GeoDataFrame()

                    # Create a GeoDataFrame with all valid pixel values
                    rows, cols = np.where(out_image != src.nodata)
                    xs, ys = rasterio.transform.xy(out_transform, rows, cols)
                    points = [Point(x, y) for x, y in zip(xs, ys)]

                    gdf = gpd.GeoDataFrame(
                        {"geometry": points, "value": valid_data}, crs=raster_crs
                    )

                    return gdf
                except ValueError as e:
                    if "Input shapes do not overlap raster" in str(e):
                        self.logger.warning(
                            f"Shape does not overlap with raster {layer_name}."
                        )
                        return gpd.GeoDataFrame()
                    else:
                        raise

        elif layer_type == "vector":
            gdf = gpd.read_file(layer_path)

            # Ensure both GeoDataFrames are in the same CRS
            if gdf.crs != shape_gdf.crs:
                shape_gdf = shape_gdf.to_crs(gdf.crs)

            # Clip the layer to the shape geometry
            clipped = gpd.clip(gdf, shape_gdf)

            # Remove any invalid geometries
            clipped = clipped[clipped.geometry.is_valid]

            # Remove any empty geometries
            clipped = clipped[~clipped.geometry.is_empty]

            return clipped

        return gpd.GeoDataFrame()

    def load_shape_geometry(self, wkt_str: str) -> Optional[Any]:
        """
        Load a geometry from a WKT string.

        Args:
            wkt_str (str): The WKT string.

        Returns:
            Any: The loaded geometry as a GeoDataFrame or None if loading fails.
        """
        try:
            geometry = wkt_loads(wkt_str)

            # Attempt to make the geometry valid
            if not geometry.is_valid:
                self.logger.warning("Invalid geometry detected. Attempting to fix...")
                geometry = make_valid(geometry)

            if not geometry.is_valid:
                self.logger.warning(
                    "Geometry still invalid after make_valid(). Attempting buffer(0)..."
                )
                geometry = geometry.buffer(0)

            if isinstance(geometry, GeometryCollection):
                self.logger.warning(
                    "GeometryCollection encountered, extracting Polygons and MultiPolygons"
                )
                polygons = [
                    geom
                    for geom in geometry.geoms
                    if isinstance(geom, (Polygon, MultiPolygon))
                ]
                if polygons:
                    geometry = unary_union(polygons)
                else:
                    self.logger.error("No valid Polygons found in GeometryCollection")
                    return None

            if not isinstance(geometry, (Polygon, MultiPolygon)):
                self.logger.error(f"Unsupported geometry type: {geometry.geom_type}")
                return None

            # Additional cleanup step
            if isinstance(geometry, MultiPolygon):
                clean_polygons = []
                for poly in geometry.geoms:
                    if poly.is_valid:
                        clean_polygons.append(poly)
                    else:
                        # Try to fix invalid polygons
                        boundary = poly.boundary
                        if boundary.is_valid:
                            fixed_polygons = list(polygonize(boundary))  # type: ignore
                            clean_polygons.extend(fixed_polygons)
                geometry = MultiPolygon(clean_polygons)
            elif isinstance(geometry, Polygon):
                if not geometry.is_valid:
                    boundary = geometry.boundary
                    if boundary.is_valid:
                        fixed_polygons = list(polygonize(boundary))  # type: ignore
                        if len(fixed_polygons) == 1:
                            geometry = fixed_polygons[0]
                        else:
                            geometry = MultiPolygon(fixed_polygons)

            # Calculate area in km²
            geod = pyproj.Geod(ellps="WGS84")
            area_m2 = abs(geod.geometry_area_perimeter(geometry)[0])
            area_km2 = area_m2 / 1_000_000  # Convert m² to km²

            # Simplify large geometries
            if area_km2 > LARGE_SHAPE_THRESHOLD_KM2:
                tolerance = 0.001 * (area_km2 ** 0.5)
                geometry = geometry.simplify(tolerance, preserve_topology=True)

                if isinstance(geometry, Polygon):
                    self.logger.info(
                        f"Geometry simplified. New vertex count: {len(geometry.exterior.coords)}"
                    )
                elif isinstance(geometry, MultiPolygon):
                    total_vertices = sum(
                        len(poly.exterior.coords) for poly in geometry.geoms
                    )
                    self.logger.info(
                        f"Geometry simplified. New total vertex count: {total_vertices}"
                    )

            # Create a GeoDataFrame with the geometry and set its CRS
            gdf = gpd.GeoDataFrame(geometry=[geometry], crs="EPSG:4326")
            # Clean the shape geometry
            gdf["geometry"] = gdf["geometry"].apply(self.clean_geometry)
            gdf = gdf[gdf["geometry"].is_valid]

            if gdf.empty:
                self.logger.warning("Shape became invalid after cleaning.")
                return gpd.GeoDataFrame()

            return gdf
        except Exception as e:
            self.logger.error(f"Failed to load geometry from WKT string: {str(e)}")
            return None

    @staticmethod
    def clean_geometry(geom: BaseGeometry) -> BaseGeometry:
        """
        Clean the geometry by making it valid and removing any non-Polygon geometries.
        Args:
            geom (shapely.geometry.base.BaseGeometry): The geometry to clean.

        Returns:
            shapely.geometry.base.BaseGeometry: The cleaned geometry.
        """
        if not geom.is_valid:
            geom = make_valid(geom)
        if isinstance(geom, GeometryCollection):
            geom = unary_union(
                [g for g in geom.geoms if g.geom_type in ["Polygon", "MultiPolygon"]]
            )
        return geom

    def process_layer_stats(
            self,
            shape_ref: ShapeRef,
            gdf: Any,
            field: str,
            transformations: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Process statistics for a layer.

        Args:
            shape_ref (ShapeRef): The shape reference.
            gdf (Any): The GeoDataFrame containing layer data.
            field (str): The field name.
            transformations (List[Dict[str, Any]]): The list of transformations to apply.

        Returns:
            Dict[str, Any]: The processed statistics.
        """
        stats: Dict[str, Any] = {}
        field_config = self.fields.get(field, {})
        for transformation in transformations:
            transform_name = transformation.get("name")
            column_name = f"{field}_{transform_name}"
            try:
                if transform_name == "area":
                    stats[column_name] = self.calculate_area_from_gdf(gdf)
                elif transform_name == "coordinates":
                    stats[column_name] = self.get_coordinates_from_gdf(gdf)
                elif transform_name == "effective_mesh_size":
                    stats[column_name] = self.calculate_effective_mesh_size_from_gdf(
                        gdf
                    )
                elif transform_name == "fragment_size_distribution":
                    stats[
                        column_name
                    ] = self.calculate_fragmentation_distribution_from_gdf(
                        gdf, field_config
                    )
                elif transform_name == "elevation_distribution":
                    stats[column_name] = self.calculate_elevation_distribution(
                        shape_ref
                    )
                elif transform_name in [
                    "mean",
                    "median",
                    "max",
                    "range",
                    "distribution",
                ]:
                    if "value" not in gdf.columns or gdf["value"].empty:
                        stats[column_name] = None
                    else:
                        stats[column_name] = self.calculate_raster_statistics(
                            gdf, transform_name
                        )
            except Exception as e:
                self.logger.error(
                    f"Error processing {transform_name} for {field} in shape {shape_ref.id}: {str(e)}"
                )
                stats[column_name] = 0.0
        return stats

    @staticmethod
    def calculate_area_from_gdf(gdf: Any) -> float:
        """
        Calculate the total area from a GeoDataFrame.

        Args:
            gdf (Any): The GeoDataFrame containing geometries.

        Returns:
            float: The total area in hectares.
        """
        gdf_proj = gdf.to_crs(gdf.estimate_utm_crs())
        return float(gdf_proj.area.sum() / 10000)

    @staticmethod
    def get_coordinates_from_gdf(gdf: Any) -> Dict[str, Any]:
        """
        Get the simplified coordinates of the union of geometries in the GeoDataFrame.

        Args:
            gdf (Any): The GeoDataFrame containing geometries.

        Returns:
            Dict[str, Any]: The simplified coordinates as a GeoJSON-like dictionary.
        """
        if gdf.empty:
            return {}
        simplified_geom = gdf.geometry.union_all().simplify(
            tolerance=0.001, preserve_topology=True
        )
        return mapping(simplified_geom)

    def calculate_effective_mesh_size_from_gdf(self, gdf: Any) -> float:
        """
        Calculate the effective mesh size from a GeoDataFrame.

        Args:
            gdf (Any): The GeoDataFrame containing geometries.

        Returns:
            float: The effective mesh size in square kilometers.
        """

        # Reproject the GeoDataFrame to a suitable UTM coordinate system
        gdf_proj = gdf.to_crs(gdf.estimate_utm_crs())

        # Convert area to hectares (1 hectare = 10,000 square meters)
        areas_ha = gdf_proj.area / 10000

        # Calculate the total area in hectares
        total_area = areas_ha.sum()

        # Calculate the sum of squared areas
        sum_squared_areas = (areas_ha ** 2).sum()

        if total_area > 0:
            # Calculate the Effective Mesh Size (MEFF) in hectares
            meff = sum_squared_areas / total_area

            # Convert MEFF from hectares to square kilometers (1 km² = 100 ha)
            meff_km2 = meff / 100
            return float(meff_km2)
        else:
            # Log a warning if the total area is zero and return 0
            self.logger.warning("Total area is zero")
            return 0.0

    def calculate_fragmentation_distribution_from_gdf(
            self, gdf: Any, field_config: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Calculate the fragmentation distribution from a GeoDataFrame.

        Args:
            gdf (Any): The GeoDataFrame containing geometries.
            field_config (Dict[str, Any]): The field configuration containing transformation details.

        Returns:
            Dict[str, float]: The fragmentation distribution.
        """
        # Ensure we're working with a copy to avoid modifying the original
        gdf = gdf.copy()

        if "geometry" not in gdf.columns:
            self.logger.warning("No geometry column found in the GeoDataFrame")
            return {}

        gdf_proj = gdf.to_crs(gdf.estimate_utm_crs())
        gdf_proj["area_ha"] = gdf_proj.geometry.area / 10000

        fragment_areas = gdf_proj["area_ha"].sort_values(ascending=True)
        total_area = fragment_areas.sum()

        if total_area == 0:
            self.logger.warning("Total area is zero")
            return {}

        bins: List[int] = next(
            (
                t["chart_options"]["bins"]
                for t in field_config["transformations"]
                if t["name"] == "fragment_size_distribution"
            ),
            [],
        )

        if not bins:
            self.logger.warning("No bins found in configuration")
            return {}

        bin_areas = {str(bin_val): 0.0 for bin_val in bins}
        cumulative_area = 0.0
        last_bin = 0

        for bin_val in bins:
            bin_sum = fragment_areas[
                (fragment_areas > last_bin) & (fragment_areas <= bin_val)
                ].sum()
            cumulative_area += bin_sum
            bin_areas[str(bin_val)] = (
                    cumulative_area / total_area * 100
            )  # Convert to percentage
            last_bin = bin_val

        return bin_areas

    @staticmethod
    def calculate_raster_statistics(gdf: Any, statistic: str) -> Any:
        """
        Calculate raster statistics from a GeoDataFrame.

        Args:
            gdf (Any): The GeoDataFrame containing raster values.
            statistic (str): The type of statistic to calculate ('mean', 'median', 'max', 'range', 'distribution').

        Returns:
            Any: The calculated statistic.
        """
        raster_values = gdf["value"].to_numpy()

        if statistic == "mean":
            return float(np.mean(raster_values))
        elif statistic == "median":
            return float(np.median(raster_values))
        elif statistic == "max":
            return float(np.max(raster_values))
        elif statistic == "range":
            return {
                "min": float(np.min(raster_values)),
                "max": float(np.max(raster_values)),
            }
        elif statistic == "distribution":
            hist, bin_edges = np.histogram(raster_values, bins="auto")
            return {str(bin_edges[i]): int(hist[i]) for i in range(len(hist))}

    def process_shape_stats(
            self, shape_ref: ShapeRef, field: str, transformations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:  # This indicates that the returned dictionary can have any type of values.
        """
        Process shape statistics for a given field.

        Args:
            shape_ref (ShapeRef): The shape reference.
            field (str): The field name.
            transformations (List[Dict[str, Any]]): The list of transformations to apply.

        Returns:
            Dict[str, Any]: The processed statistics.
        """
        stats: Dict[str, Any] = {}
        for transformation in transformations:
            transform_name = transformation.get("name")
            column_name = f"{field}_{transform_name}"
            if transform_name == "area":
                stats[column_name] = self.calculate_area(str(shape_ref.location))
            elif transform_name == "coordinates":
                stats[column_name] = self.get_simplified_coordinates(str(shape_ref.location))
        return stats

    def process_occurrence_stats(
            self,
            group_occurrences: List[Dict[Hashable, Any]],
            field: str,
            transformations: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Process occurrence statistics for a given field.

        Args:
            group_occurrences (List[Dict[Hashable, Any]]): The occurrences to process.
            field (str): The field name.
            transformations (List[Dict[str, Any]]): The list of transformations to apply.

        Returns:
            Dict[str, Any]: The processed statistics.
        """
        stats: Dict[str, Any] = {}
        for transformation in transformations:
            transform_name = transformation.get("name")
            column_name = f"{field}_{transform_name}"
            if transform_name == "unique_taxonomic_count":
                target_ranks = transformation.get("target_ranks", [])
                stats[column_name] = self.calculate_unique_taxonomic_count(
                    group_occurrences, target_ranks
                )
            elif transform_name == "count":
                stats[column_name] = len(group_occurrences)
        return stats

    def calculate_unique_taxonomic_count(
            self, occurrences: List[Dict[Hashable, Any]], target_ranks: List[str]
    ) -> int:
        """
        Calculate the unique count of taxonomic ranks in the occurrences.

        Args:
            occurrences (List[Dict[Hashable, Any]]): The occurrences to calculate statistics for.
            target_ranks (List[str]): The taxonomic ranks to count.

        Returns:
            int: The unique count of the specified taxonomic ranks.
        """
        taxon_ids = {
            occ.get("taxon_ref_id") for occ in occurrences if occ.get("taxon_ref_id")
        }
        if not taxon_ids:
            return 0

        # Retrieve the taxons from the database
        taxons = (
            self.db.session.query(TaxonRef).filter(TaxonRef.id.in_(taxon_ids)).all()
        )
        taxon_dict: Dict[int, TaxonRef] = {int(taxon.id): taxon for taxon in taxons}

        # Retrieve the parent taxons of the taxons
        parent_ids = {
            taxon.parent_id for taxon in taxons if taxon.parent_id is not None
        }
        while parent_ids:
            parent_taxons = (
                self.db.session.query(TaxonRef)
                .filter(TaxonRef.id.in_(parent_ids))
                .all()
            )
            for parent_taxon in parent_taxons:
                taxon_dict[int(parent_taxon.id)] = parent_taxon
            parent_ids = {
                taxon.parent_id
                for taxon in parent_taxons
                if taxon.parent_id is not None and int(taxon.parent_id) not in taxon_dict
            }

        unique_taxons = set()

        # Count the unique taxons at the specified ranks
        for taxon in taxon_dict.values():
            current_taxon: Optional[TaxonRef] = taxon
            while current_taxon:
                if current_taxon.rank_name in target_ranks:
                    unique_taxons.add(current_taxon.id)
                    break
                # Ensure parent_id is not None before accessing taxon_dict
                parent_id: Optional[int] = current_taxon.parent_id
                if parent_id is None:
                    break
                current_taxon = taxon_dict.get(int(parent_id))

        return len(unique_taxons)

    def get_simplified_coordinates(self, wkt_geometry: str) -> Dict[str, Any]:
        """
        Get simplified coordinates for a WKT geometry.

        Args:
            wkt_geometry (str): The WKT representation of the geometry.

        Returns:
            dict: The simplified coordinates as a GeoJSON-like dictionary.
        """
        geom = self.load_shape_geometry(wkt_geometry)
        if geom is not None:
            simplified_geom = geom.simplify(tolerance=0.001, preserve_topology=True)
            return mapping(simplified_geom)
        else:
            # Handle the case where geom is None. This could involve logging an error or returning an empty dict.
            return {}

    def calculate_area(self, wkt_geometry: str) -> float:
        """
        Calculate the area of a geometry in hectares.

        Args:
            wkt_geometry (str): The WKT representation of the geometry.

        Returns:
            float: The area of the geometry in hectares.
        """
        try:
            gdf = self.load_shape_geometry(wkt_geometry)
            if gdf is None or gdf.empty:
                return 0.0

            # Project to a suitable UTM projection
            gdf_projected = gdf.to_crs(gdf.estimate_utm_crs())

            area_sqm = gdf_projected.geometry.area.sum()

            if np.isnan(area_sqm) or np.isinf(area_sqm):
                self.logger.warning(f"Invalid area calculated: {area_sqm}")
                return 0.0

            return float(area_sqm / 10000)  # Convert to hectares
        except Exception as e:
            self.logger.error(f"Error calculating area: {str(e)}")
            return 0.0

    def calculate_elevation_distribution(self, shape_ref: ShapeRef) -> Dict[str, Any]:
        """
        Calculate the elevation distribution for a shape.

        Args:
            shape_ref (ShapeRef): The shape reference.

        Returns:
            Dict[str, Any]: The elevation distribution data.
        """
        try:
            # Load the shape geometry
            # Ensure shape_ref.location is a string before passing it to load_shape_geometry
            if shape_ref.location is not None:
                shape_geom = self.load_shape_geometry(str(shape_ref.location))

            # Load the elevation and forest cover layers
            elevation_path = self.mapper_service.get_layer_path("elevation")
            forest_path = self.mapper_service.get_layer_path("forest_cover")

            with rasterio.open(elevation_path) as elevation_src:
                # Ensure that shape_geom is in the correct CRS
                if shape_geom is not None:
                    shape_geom = shape_geom.to_crs(elevation_src.crs)
                else:
                    self.logger.error("Shape geometry is None, cannot proceed with elevation distribution calculation.")
                    return {}

                # Mask the elevation data with the shape geometry
                elevation_data, transform = mask(
                    elevation_src,
                    shape_geom.geometry,
                    crop=True,
                    nodata=elevation_src.nodata,
                )

                # Load the forest cover data
                forest_gdf = gpd.read_file(forest_path)
                forest_gdf = forest_gdf.to_crs(elevation_src.crs)

                # Rasterize the forest cover data
                forest_raster = rasterize(
                    [(geom, 1) for geom in forest_gdf.geometry],
                    out_shape=elevation_data.shape[1:],
                    transform=transform,
                    fill=0,
                    dtype=rasterio.uint8,
                )

                # Flatten the data
                elevation_flat = elevation_data[0].flatten()
                forest_flat = forest_raster.flatten()

                # Create masks for forest and non-forest pixels
                valid_elevation_mask = elevation_flat != elevation_src.nodata
                forest_mask = (forest_flat == 1) & valid_elevation_mask
                non_forest_mask = (forest_flat == 0) & valid_elevation_mask

                # Determine the altitude range and interval automatically
                valid_elevations = elevation_flat[valid_elevation_mask]

                if valid_elevations.size == 0:
                    self.logger.warning(
                        f"No valid elevation data found for shape {shape_ref.id}"
                    )
                    return {}

                min_elevation = np.floor(valid_elevations.min())
                max_elevation = np.ceil(valid_elevations.max())

                # Check if min and max are equal
                if min_elevation == max_elevation:
                    self.logger.warning(
                        f"Constant elevation ({min_elevation}) for shape {shape_ref.id}"
                    )
                    return {
                        "altitudes": [float(min_elevation)],  # Convert to Python float
                        "forest": [int(np.sum(forest_mask))],  # Convert to Python int
                        "non_forest": [
                            int(np.sum(non_forest_mask))
                        ],  # Convert to Python int
                    }

                # Determine the number of intervals (aim for about 20 intervals)
                target_intervals = 20
                interval = (
                        np.ceil((max_elevation - min_elevation) / target_intervals / 100)
                        * 100
                )  # Round to the nearest hundred

                # Ensure the interval is not zero or too small
                if interval < 1:
                    interval = 1

                # Create altitude bins
                try:
                    altitude_bins = np.arange(
                        min_elevation, max_elevation + interval, interval
                    )
                except ValueError as e:
                    self.logger.error(
                        f"Error creating altitude bins for shape {shape_ref.id}: {str(e)}"
                    )
                    self.logger.error(
                        f"min_elevation: {min_elevation}, max_elevation: {max_elevation}, interval: {interval}"
                    )
                    return {}

                # Ensure we have at least two bins
                if len(altitude_bins) < 2:
                    altitude_bins = np.array([min_elevation, max_elevation])

                # Calculate the histogram for forest and non-forest pixels
                forest_hist, _ = np.histogram(
                    elevation_flat[forest_mask], bins=altitude_bins
                )
                non_forest_hist, _ = np.histogram(
                    elevation_flat[non_forest_mask], bins=altitude_bins
                )

                # Convert the histograms to areas in hectares
                pixel_area_ha = (
                        abs(elevation_src.transform[0] * elevation_src.transform[4]) / 10000
                )
                forest_areas = forest_hist * pixel_area_ha
                non_forest_areas = non_forest_hist * pixel_area_ha

                # Prepare the elevation distribution data
                elevation_distribution = {
                    "altitudes": [float(alt) for alt in altitude_bins[:-1].tolist()],
                    # Exclude the last value and convert to Python float
                    "forest": [
                        float(area) for area in forest_areas.tolist()
                    ],  # Convert to Python float
                    "non_forest": [
                        float(area) for area in non_forest_areas.tolist()
                    ],  # Convert to Python float
                }

            return elevation_distribution

        except Exception as e:
            self.logger.error(
                f"Error in calculate_elevation_distribution for shape {shape_ref.id}: {str(e)}"
            )
            import traceback

            self.logger.error(traceback.format_exc())
            return {}

    @staticmethod
    def plot_elevation_distribution(data: Dict[str, Any]) -> None:
        """
        Plot the elevation distribution.

        Args:
            data (Dict[str, Any]): The elevation distribution data.
        """
        altitudes = data["altitudes"]
        forest = data["forest"]
        non_forest = data["non_forest"]

        # 1. Stacked histogram (original plot)
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.barh(altitudes, forest, label="Forest", color="#548235", height=90)
        ax.barh(
            altitudes,
            non_forest,
            left=forest,
            label="Non-forest",
            color="#ecdcad",
            height=90,
        )
        ax.set_ylabel("Altitude (m)")
        ax.set_xlabel("Area (ha)")
        ax.set_title("Altitudinal Distribution (Histogram)")
        ax.legend(loc="lower right")
        ax.invert_yaxis()
        ax.set_xlim(0, max(max(forest), max(non_forest)) * 1.1)
        plt.tight_layout()
        plt.show()

        # 2. Area plot
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.fill_betweenx(
            altitudes, 0, forest, label="Forest", color="#548235", alpha=0.7
        )
        ax.fill_betweenx(
            altitudes,
            forest,
            [f + nf for f, nf in zip(forest, non_forest)],
            label="Non-forest",
            color="#ecdcad",
            alpha=0.7,
        )
        ax.set_ylabel("Altitude (m)")
        ax.set_xlabel("Area (ha)")
        ax.set_title("Altitudinal Distribution (Area Plot)")
        ax.legend(loc="lower right")
        ax.invert_yaxis()
        ax.set_xlim(0, max([f + nf for f, nf in zip(forest, non_forest)]) * 1.1)
        plt.tight_layout()
        plt.show()

        # 3. Forest cover percentage
        total_area = [f + nf for f, nf in zip(forest, non_forest)]
        forest_percentage = [
            f / t * 100 if t > 0 else 0 for f, t in zip(forest, total_area)
        ]

        fig, ax = plt.subplots(figsize=(10, 8))
        ax.barh(altitudes, forest_percentage, color="#548235", height=90)
        ax.set_ylabel("Altitude (m)")
        ax.set_xlabel("Forest cover percentage")
        ax.set_title("Forest cover percentage by altitude")
        ax.invert_yaxis()
        ax.set_xlim(0, 100)
        for i, v in enumerate(forest_percentage):
            ax.text(v + 1, altitudes[i], f"{v:.1f}%", va="center")
        plt.tight_layout()
        plt.show()

    def _safe_area_calculation(self, polygon: Polygon) -> float:
        """
        Safely calculate the area of a polygon.

        Args:
            polygon (Polygon): The polygon to calculate the area for.

        Returns:
            float: The area of the polygon.
        """
        try:
            area = polygon.area
            if np.isnan(area) or np.isinf(area):
                self.logger.warning(f"Invalid area for polygon: {polygon.wkt[:100]}...")
                return 0.0
            return area
        except Exception as e:
            self.logger.error(f"Error calculating polygon area: {str(e)}")
            return 0.0

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
        return cast(int, shape_ref.id)

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
                        # Use string manipulation instead of wkt_loads for faster processing
                        coords = point_wkt.strip("POINT ()").split()
                        x, y = float(coords[0]), float(coords[1])
                        idx.insert(pos, (x, y, x, y))
                    except (ValueError, IndexError) as e:
                        self.logger.error(
                            f"Error processing occurrence at position {pos} with value {point_wkt}: {e}"
                        )

        return idx
