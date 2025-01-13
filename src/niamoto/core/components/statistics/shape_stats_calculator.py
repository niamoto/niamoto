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
from shapely.geometry import mapping, Point
from shapely.geometry.base import BaseGeometry
from shapely.prepared import prep
from shapely import wkt, wkb

from niamoto.common.config import Config
from niamoto.common.database import Database
from niamoto.core.models import ShapeRef
from .statistics_calculator import StatisticsCalculator

LARGE_SHAPE_THRESHOLD_KM2 = 1000


class ShapeStatsCalculator(StatisticsCalculator):
    """
    A class used to calculate statistics for shapes.

    Inherits from:
        StatisticsCalculator
    """

    def __init__(
        self, db: Database, occurrences: list[dict[Hashable, Any]], group_config: dict
    ):
        super().__init__(
            db=db,
            occurrences=occurrences,
            group_config=group_config,
            log_component="shape_stats",
        )
        self.config = Config()

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

            # shape_occurrences = self._get_shape_occurrences(shape_ref)
            # if not shape_occurrences:
            #     return

            shape_occurrences = []

            stats = self.calculate_stats(shape_id, shape_occurrences)

            self.create_or_update_stats_entry(shape_id, stats)

        except Exception as e:
            self.logger.error(f"Failed to process shape {shape_ref.id}: {e}")

    def calculate_stats(
        self, group_id: int, group_occurrences: List[Dict[Hashable, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate statistics for a shape based on current configuration and raw data.
        """
        stats: Dict[str, Any] = {}

        # Get shape reference
        shape_ref = (
            self.db.session.query(ShapeRef).filter(ShapeRef.id == group_id).first()
        )
        if not shape_ref:
            self.logger.error(f"Shape with ID {group_id} not found.")
            return stats

        try:
            # Load raw data for this shape
            df = pd.read_csv(self.group_config["raw_data"], sep=";")
            shape_data = df[df["id"] == group_id]

            if shape_data.empty:
                self.logger.error(f"No raw data found for shape {group_id}")
                return stats

            # Process each configured field
            for field, field_config in self.widgets_data.items():
                try:
                    transformations = field_config.get("transformations", [])
                    for transformation in transformations:
                        transform_name = transformation.get("name")
                        result = self._process_transformation(
                            transform_name, transformation, shape_ref, shape_data
                        )
                        if result is not None:
                            stats[field] = result
                except Exception as e:
                    self.logger.error(f"Error processing field {field}: {str(e)}")

            return stats

        except Exception as e:
            self.logger.error(f"Error processing shape {group_id}: {str(e)}")
            return stats

    def _process_transformation(
        self,
        transform_name: str,
        config: dict,
        shape_ref: ShapeRef,
        shape_data: pd.DataFrame,
    ) -> Any:
        """Process a single transformation based on its type"""
        try:
            if transform_name == "collect_fields":
                return self._process_collect_fields(config, shape_ref, shape_data)
            elif transform_name == "geometry_coords":
                return self._process_geometry_coords(shape_ref)
            elif transform_name == "extract_multi_class_object":
                return self._process_forest_cover(config, shape_data)
            elif transform_name == "extract_by_class_object":
                return self._process_class_object(config, shape_data)
            elif transform_name == "extract_elevation_distribution":
                return self._process_elevation_distribution(shape_data)
            elif transform_name == "extract_holdridge":
                return self._process_holdridge(shape_data)
            elif transform_name == "extract_elevation_matrix":
                return self._process_elevation_matrix(shape_data)
            elif transform_name == "extract_forest_types_by_elevation":
                return self._process_forest_types_elevation(shape_data)
            elif transform_name == "extract_distribution":
                return self._process_distribution(config, shape_data)
        except Exception as e:
            self.logger.error(f"Error in transformation {transform_name}: {str(e)}")
            return None

    @staticmethod
    def _process_collect_fields(
        config: dict, shape_ref: ShapeRef, shape_data: pd.DataFrame
    ) -> dict:
        """Process collect_fields transformation"""
        result = {}
        for item in config.get("items", []):
            source = item.get("source")
            if source == "shape_ref":
                result[item["key"]] = getattr(shape_ref, item["field"])
            elif source == "raw_data":
                class_object = item.get("class_object")
                if isinstance(class_object, list):
                    # Handle range values (like rainfall min/max)
                    values = []
                    for co in class_object:
                        value = float(
                            shape_data[shape_data["class_object"] == co][
                                "class_value"
                            ].iloc[0]
                        )
                        values.append(value)
                    result[item["key"]] = {"min": min(values), "max": max(values)}
                else:
                    value = float(
                        shape_data[shape_data["class_object"] == class_object][
                            "class_value"
                        ].iloc[0]
                    )
                    result[item["key"]] = value
        return result

    def _process_geometry_coords(self, shape_ref: ShapeRef) -> dict:
        """Process geometry_coords transformation"""
        shape_gdf = self.load_shape_geometry(str(shape_ref.location))
        forest_gdf = (
            self.load_layer_as_gdf(shape_gdf, "forest_cover", "vector")
            if shape_gdf is not None
            else None
        )

        return {
            "shape_coords": self.get_simplified_coordinates(str(shape_ref.location)),
            "forest_coords": self.get_coordinates_from_gdf(forest_gdf)
            if forest_gdf is not None
            else {},
        }

    @staticmethod
    def _process_forest_cover(config: dict, shape_data: pd.DataFrame) -> dict:
        """Process forest cover transformation"""
        result = {}
        for param in config.get("params", []):
            label = param["label"]
            class_object = param["class_object"]
            data = shape_data[shape_data["class_object"] == class_object]

            result[label] = {
                "foret": float(
                    data[data["class_name"] == "Forêt"]["class_value"].iloc[0]
                ),
                "hors_foret": float(
                    data[data["class_name"] == "Hors-forêt"]["class_value"].iloc[0]
                ),
            }
        return result

    @staticmethod
    def _process_class_object(config: dict, shape_data: pd.DataFrame) -> dict:
        """
        Process class object extraction with optional category ordering.

        Args:
            config (dict): Configuration containing class_object and optional categories_order
            shape_data (pd.DataFrame): The shape data to process

        Returns:
            dict: Processed data with ordered categories and their corresponding values
        """
        class_object = config.get("class_object")
        categories_order = config.get("categories_order", [])

        # Filter data for the specified class_object
        data = shape_data[shape_data["class_object"] == class_object].copy()

        if categories_order:
            # Create a categorical type with the specified order
            data["class_name"] = pd.Categorical(
                data["class_name"], categories=categories_order, ordered=True
            )
            # Sort based on the categorical order
            data = data.sort_values("class_name")

            # Ensure all categories are represented
            result_categories = []
            result_values = []
            for category in categories_order:
                category_data = data[data["class_name"] == category]
                result_categories.append(category)
                result_values.append(
                    float(category_data["class_value"].iloc[0])
                    if not category_data.empty
                    else 0.0
                )

            return {"categories": result_categories, "values": result_values}
        else:
            # If no order specified, just sort alphabetically
            data = data.sort_values("class_name")
            return {
                "categories": data["class_name"].tolist(),
                "values": data["class_value"].astype(float).tolist(),
            }

    @staticmethod
    def _process_elevation_distribution(shape_data: pd.DataFrame) -> dict:
        """Process elevation distribution"""
        forest_elev = shape_data[
            shape_data["class_object"] == "forest_elevation"
        ].copy()
        land_elev = shape_data[shape_data["class_object"] == "land_elevation"].copy()

        forest_elev.loc[:, "class_name"] = pd.to_numeric(forest_elev["class_name"])
        land_elev.loc[:, "class_name"] = pd.to_numeric(land_elev["class_name"])

        forest_elev = forest_elev.sort_values("class_name").reset_index(drop=True)
        land_elev = land_elev.sort_values("class_name").reset_index(drop=True)

        return {
            "altitudes": forest_elev["class_name"].tolist(),
            "forest": forest_elev["class_value"].astype(float).tolist(),
            "non_forest": (land_elev["class_value"] - forest_elev["class_value"])
            .astype(float)
            .tolist(),
        }

    @staticmethod
    def _process_holdridge(shape_data: pd.DataFrame) -> dict:
        """Process holdridge data"""
        forest = shape_data[shape_data["class_object"] == "holdridge_forest"]
        non_forest = shape_data[shape_data["class_object"] == "holdridge_forest_out"]

        return {
            "forest": {
                "sec": float(
                    forest[forest["class_name"] == "Sec"]["class_value"].iloc[0]
                ),
                "humide": float(
                    forest[forest["class_name"] == "Humide"]["class_value"].iloc[0]
                ),
                "tres_humide": float(
                    forest[forest["class_name"] == "Très Humide"]["class_value"].iloc[0]
                ),
            },
            "non_forest": {
                "sec": float(
                    non_forest[non_forest["class_name"] == "Sec"]["class_value"].iloc[0]
                ),
                "humide": float(
                    non_forest[non_forest["class_name"] == "Humide"][
                        "class_value"
                    ].iloc[0]
                ),
                "tres_humide": float(
                    non_forest[non_forest["class_name"] == "Très Humide"][
                        "class_value"
                    ].iloc[0]
                ),
            },
        }

    @staticmethod
    def _process_elevation_matrix(shape_data: pd.DataFrame) -> dict:
        """Process elevation matrix data"""
        forest_um = shape_data[
            shape_data["class_object"] == "ratio_forest_um_elevation"
        ].copy()
        forest_num = shape_data[
            shape_data["class_object"] == "ratio_forest_num_elevation"
        ].copy()

        forest_um.loc[:, "class_name"] = pd.to_numeric(forest_um["class_name"])
        forest_num.loc[:, "class_name"] = pd.to_numeric(forest_num["class_name"])

        forest_um = forest_um.sort_values("class_name").reset_index(drop=True)
        forest_num = forest_num.sort_values("class_name").reset_index(drop=True)

        return {
            "altitudes": forest_um["class_name"].tolist(),
            "um": (forest_um["class_value"] * 100).tolist(),
            "num": (forest_num["class_value"] * 100).tolist(),
            "hors_foret_um": [
                100 if not pd.isnull(x) else 0 for x in forest_um["class_value"]
            ],
            "hors_foret_num": [
                100 if not pd.isnull(x) else 0 for x in forest_num["class_value"]
            ],
        }

    @staticmethod
    def _process_forest_types_elevation(shape_data: pd.DataFrame) -> dict:
        """Process forest types by elevation"""
        elevation_types = {
            "secondaire": "forest_secondary_elevation",
            "mature": "forest_mature_elevation",
            "coeur": "forest_core_elevation",
        }

        result = {"altitudes": [], "secondaire": [], "mature": [], "coeur": []}

        # Get and sort altitudes from any of the elevation types
        first_type = next(iter(elevation_types.values()))
        elevation_data = shape_data[shape_data["class_object"] == first_type].copy()
        elevation_data.loc[:, "class_name"] = pd.to_numeric(
            elevation_data["class_name"]
        )
        elevation_data = elevation_data.sort_values("class_name")
        result["altitudes"] = elevation_data["class_name"].tolist()

        # Get values for each forest type
        for key, class_object in elevation_types.items():
            data = shape_data[shape_data["class_object"] == class_object].copy()
            data.loc[:, "class_name"] = pd.to_numeric(data["class_name"])
            data = data.sort_values("class_name")
            result[key] = data["class_value"].astype(float).tolist()

        return result

    @staticmethod
    def _process_distribution(config: dict, shape_data: pd.DataFrame) -> dict:
        """Process distribution data"""
        class_object = config.get("class_object")
        data = shape_data[shape_data["class_object"] == class_object].copy()
        data.loc[:, "class_name"] = pd.to_numeric(data["class_name"])
        data = data.sort_values("class_name")

        return {
            "sizes": data["class_name"].tolist(),
            "values": data["class_value"].astype(float).tolist(),
        }

    def _get_shape_occurrences(self, shape_ref: ShapeRef) -> List[Dict[Hashable, Any]]:
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

        occurrence_location_field = self.group_config.get("occurrence_location_field")

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
        def is_within_shape(geo_str: str) -> bool:
            """
            Check if a point is within the shape.
            Args:
                geo_str (str): The geometric representation of the point.

            Returns:
                bool: True if the point is within the shape, False otherwise.

            """
            try:
                # Try to parse as WKT (POINT format)
                if geo_str.startswith("POINT"):
                    point_geom = wkt.loads(geo_str)
                # Try to parse as WKB (hexadecimal format)
                else:
                    point_geom = wkb.loads(geo_str, hex=True)

                # If the geometry is not a Point, create a Point from its centroid
                if not isinstance(point_geom, Point):
                    point_geom = Point(point_geom.centroid)

                return prepared_shape.contains(point_geom)
            except Exception as er:
                self.logger.warning(f"Invalid geometry string: {geo_str}. Error: {er}")
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

    def _get_layer(self, layer_name: str) -> Optional[Dict[str, Any]]:
        """Get layer configuration by name."""
        layers = self.config.sources.get("layers", [])
        return next(
            (layer for layer in layers if layer.get("name") == layer_name), None
        )

    def _get_layer_path(self, layer_name: str) -> Optional[str]:
        """Get layer path from configuration."""
        layer = self._get_layer(layer_name)
        return layer.get("path") if layer else None

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
        layer_path = self._get_layer_path(layer_name)

        if not layer_path:
            self.logger.warning(f"Path not found for layer {layer_name}")
            return gpd.GeoDataFrame()

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
            geometry = wkt.loads(wkt_str)

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
                            fixed_polygons = list(polygonize(boundary))
                            clean_polygons.extend(fixed_polygons)
                geometry = MultiPolygon(clean_polygons)
            elif isinstance(geometry, Polygon):
                if not geometry.is_valid:
                    boundary = geometry.boundary
                    if boundary.is_valid:
                        fixed_polygons = list(polygonize(boundary))
                        if len(fixed_polygons) == 1:
                            geometry = fixed_polygons[0]
                        else:
                            geometry = MultiPolygon(fixed_polygons)

            # Calculate area in km²
            geod = pyproj.Geod(ellps="WGS84")
            area_m2 = abs(geod.geometry_area_perimeter(geometry)[0])
            area_km2 = area_m2 / 1_000_000  # Convert m² to km²

            # Simplify large geometries with adjusted tolerance
            if area_km2 > LARGE_SHAPE_THRESHOLD_KM2:
                base_tolerance = 0.0001  # Reduced base tolerance
                area_factor = (
                    area_km2 / LARGE_SHAPE_THRESHOLD_KM2
                ) ** 0.25  # Adjusted scaling
                tolerance = base_tolerance * area_factor
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
            simplified_geom = geom.simplify(tolerance=0.0001, preserve_topology=True)
            return mapping(simplified_geom)
        else:
            # Handle the case where geom is None. This could involve logging an error or returning an empty dict.
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
        return cast(int, shape_ref.id)

    def build_spatial_index(self) -> index.Index:
        """
        Build a spatial index for all occurrences.

        Returns:
            index.Index: An R-tree spatial index.
        """
        idx = index.Index()
        occurrence_location_field = self.group_config.get("occurrence_location_field")

        def parse_geometry(geo_str: str) -> Point:
            """
            Parse geometry string to Point object.

            Args:
                geo_str (str): The geometric representation of the point.

            Returns:
                Point: Shapely Point object.

            Raises:
                ValueError: If the geometry cannot be parsed or is not a Point.
            """
            if pd.isna(geo_str):
                raise ValueError("Invalid geometry: NaN value")

            try:
                # Try to parse as WKT (POINT format)
                if isinstance(geo_str, str) and geo_str.upper().startswith("POINT"):
                    geom = wkt.loads(geo_str)
                # Try to parse as WKB (hexadecimal format)
                elif isinstance(geo_str, str):
                    geom = wkb.loads(geo_str, hex=True)
                else:
                    raise ValueError(f"Unexpected geometry type: {type(geo_str)}")

                # If the geometry is not a Point, create a Point from its centroid
                if not isinstance(geom, Point):
                    geom = Point(geom.centroid)

                return geom
            except Exception as e:
                raise ValueError(f"Failed to parse geometry: {e}")

        nan_count = 0
        for pos, occurrence in enumerate(self.occurrences):
            if isinstance(occurrence, dict):
                point_str = occurrence.get(occurrence_location_field)
                try:
                    point = parse_geometry(point_str)
                    idx.insert(pos, (point.x, point.y, point.x, point.y))
                except ValueError as e:
                    if "NaN value" in str(e):
                        nan_count += 1
                        if nan_count <= 10:  # Log only the first 10 NaN errors
                            self.logger.warning(
                                f"NaN value encountered at position {pos}. Skipping this occurrence."
                            )
                        elif nan_count == 11:
                            self.logger.warning(
                                "Additional NaN values encountered. Suppressing further NaN warnings."
                            )
                    else:
                        self.logger.error(
                            f"Error processing occurrence at position {pos}: {e}"
                        )

        if nan_count > 0:
            self.logger.info(f"Total NaN values encountered: {nan_count}")

        return idx
