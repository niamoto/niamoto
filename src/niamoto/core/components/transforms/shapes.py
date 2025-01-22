"""
Shape transforms calculator module.
"""
from typing import List, Dict, Any, Hashable, Optional, cast

import geopandas as gpd  # type: ignore
import numpy as np
import pandas as pd
import rasterio  # type: ignore
from rasterio.mask import mask  # type: ignore
from rtree import index
from shapely import (
    MultiPolygon,
    GeometryCollection,
    Polygon,
    make_valid,
    unary_union,
)
from shapely import wkt, wkb
from shapely.geometry import mapping, Point
from shapely.geometry.base import BaseGeometry
from shapely.prepared import prep

from niamoto.common.config import Config
from niamoto.common.database import Database
from niamoto.common.exceptions import DatabaseError, ProcessError
from niamoto.common.utils.error_handler import error_handler
from niamoto.core.models import ShapeRef
from .base_transformer import BaseTransformer

LARGE_SHAPE_THRESHOLD_KM2 = 1000


class ShapeTransformer(BaseTransformer):
    """
    A class used to calculate transforms for shapes.

    Inherits from:
        BaseTransformer
    """

    def __init__(
        self, db: Database, occurrences: list[dict[Hashable, Any]], group_config: dict
    ):
        super().__init__(
            db=db,
            occurrences=occurrences,
            group_config=group_config,
            log_component="transform",
        )
        self.config = Config()

    @error_handler(log=True, raise_error=True)
    def calculate_shape_stats(self) -> None:
        """
        Calculate transforms for all shapes.
        """
        try:
            shapes = self._retrieve_all_shapes()
            self.initialize_group_table()

            self._run_with_progress(
                items=shapes,
                description="Processing shapes...",
                process_method=self.process_shape,
            )

        except Exception as e:
            raise ProcessError("Failed to calculate shape transforms") from e

    @error_handler(log=True, raise_error=True)
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

            stats = self.transform_group(shape_id, shape_occurrences)

            self.create_or_update_group_entry(shape_id, stats)

        except Exception as e:
            raise ProcessError(f"Failed to process shape {shape_ref.id}") from e

    @error_handler(log=True, raise_error=True)
    def transform_group(
        self, group_id: int, group_occurrences: List[Dict[Hashable, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate transforms for a shape based on current configuration and raw data.
        """
        stats: Dict[str, Any] = {}

        # Get shape reference
        shape_ref = (
            self.db.session.query(ShapeRef).filter(ShapeRef.id == group_id).first()
        )
        if not shape_ref:
            raise ValueError(f"Shape with ID {group_id} not found.")

        # Load raw data for this shape
        try:
            df = pd.read_csv(self.group_config["raw_data"], sep=";")
        except FileNotFoundError:
            raise ProcessError(
                f"Input file not found: {self.group_config['raw_data']}. Please verify the file exists."
            )

        shape_data = df[df["id"] == group_id]

        if shape_data.empty:
            raise ValueError(f"No raw data found for shape {group_id}")

        # Process each configured field
        for field, field_config in self.widgets_data.items():
            transformations = field_config.get("transformations", [])
            for transformation in transformations:
                transform_name = transformation.get("name")
                result = self._process_transformation(
                    transform_name, transformation, shape_ref, shape_data
                )
                if result is not None:
                    stats[field] = result

        return stats

    @error_handler(log=True, raise_error=True)
    def _process_transformation(
        self,
        transform_name: str,
        config: dict,
        shape_ref: ShapeRef,
        shape_data: pd.DataFrame,
    ) -> Any:
        """Process a single transformation based on its type"""
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
        else:
            raise ValueError(f"Unknown transformation: {transform_name}")

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

    @error_handler(log=True, raise_error=True)
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

    @error_handler(log=True, raise_error=True)
    def _get_shape_occurrences(self, shape_ref: ShapeRef) -> List[Dict[Hashable, Any]]:
        """
        Get shape occurrences.

        Args:
            shape_ref (ShapeRef): The shape to get occurrences for.

        Returns:
            List[Dict[Hashable, Any]]: The shape occurrences.
        """
        shape_gdf = self.load_shape_geometry(str(shape_ref.location))
        if shape_gdf is None or shape_gdf.empty:
            raise ValueError(f"Invalid geometry for shape ID {shape_ref.id}.")

        shape_geom = shape_gdf.geometry.iloc[0]
        prepared_shape = prep(shape_geom)

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
        layers = self.config.imports.get("layers", [])
        return next(
            (layer for layer in layers if layer.get("name") == layer_name), None
        )

    def _get_layer_path(self, layer_name: str) -> Optional[str]:
        """Get layer path from configuration."""
        layer = self._get_layer(layer_name)
        return layer.get("path") if layer else None

    @error_handler(log=True, raise_error=True)
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
            raise ValueError(f"Path not found for layer {layer_name}")

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

    @error_handler(log=True, raise_error=True)
    def load_shape_geometry(self, wkb_str: str) -> Optional[Any]:
        """
        Load a geometry from a WKB hex string..

        Args:
            wkb_str (str): The WKB hex string.

        Returns:
            Any: The loaded geometry as a GeoDataFrame or None if loading fails.
        """
        # Load and validate geometry from WKB
        geometry = wkb.loads(wkb_str, hex=True)

        # Make geometry valid if needed
        if not geometry.is_valid:
            geometry = make_valid(geometry)

        # Handle GeometryCollection case
        if isinstance(geometry, GeometryCollection):
            polygons = [
                geom
                for geom in geometry.geoms
                if isinstance(geom, (Polygon, MultiPolygon))
            ]
            if not polygons:
                raise ValueError("No valid Polygons found in GeometryCollection")
            geometry = unary_union(polygons)

        # Check if geometry type is supported
        if not isinstance(geometry, (Polygon, MultiPolygon)):
            raise ValueError(f"Unsupported geometry type: {geometry.geom_type}")

        # Create and validate GeoDataFrame
        gdf = gpd.GeoDataFrame(geometry=[geometry], crs="EPSG:4326")
        gdf = gdf[gdf["geometry"].is_valid]

        if gdf.empty:
            raise ValueError("Shape became invalid after processing.")

        return gdf

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

    def _simplify_with_utm(
        self, geometry: BaseGeometry, log_area: bool = False
    ) -> BaseGeometry:
        """
        Simplify a geometry using UTM-based adaptive simplification.
        The simplification is done in UTM projection to ensure accurate measurements and consistent simplification.

        The process:
        1. Converts the geometry to appropriate UTM zone based on its centroid
        2. Calculates area and determines simplification tolerance:
           - For areas > 1000 km², tolerance increases with area (adaptive)
           - For smaller areas, uses fixed 5m tolerance
        3. Simplifies in UTM coordinates then converts back to WGS84

        Args:
            geometry: The geometry to simplify (in WGS84 coordinates)
            log_area: If True, logs the area of the geometry in km²

        Returns:
            The simplified geometry in WGS84 coordinates

        Raises:
            ValueError: If simplification process fails
        """
        try:
            # Calculate centroid for UTM zone determination
            # This is more accurate than using bounds for determining the appropriate zone
            centroid = geometry.centroid

            # Calculate UTM zone from longitude
            # Formula: ((longitude + 180)/6) + 1
            # This gives a zone number from 1-60
            zone_number = int((centroid.x + 180) // 6) + 1

            # Determine hemisphere from latitude
            # UTM zones have different EPSG codes for North/South hemispheres
            zone_hemisphere = "N" if centroid.y >= 0 else "S"

            # Get EPSG code for the UTM zone
            # Range: 32601-32660 for North, 32701-32760 for South
            utm_epsg = (
                32600 + zone_number if zone_hemisphere == "N" else 32700 + zone_number
            )

            # Convert geometry to calculated UTM zone
            # This ensures measurements and simplification are done in meters
            gdf_utm = gpd.GeoDataFrame(geometry=[geometry], crs="EPSG:4326").to_crs(
                f"EPSG:{utm_epsg}"
            )

            # Calculate area in square meters and optionally log it
            area_m2 = gdf_utm.geometry.area.iloc[0]
            if log_area:
                area_km2 = area_m2 / 1_000_000  # Convert to km²
                self.logger.info(f"Processing geometry with area: {area_km2:.2f} km²")

            # Calculate simplification tolerance
            # The formula adapts the tolerance based on the area, following these rules:
            # - Areas < 1000 km² : fixed 5m tolerance to preserve detail
            # - Areas > 1000 km² : adaptive tolerance using the formula: 10 * (area_km²/1000)^0.25
            #
            # Examples of resulting tolerances:
            # - 1000 km² → 10.00m (base tolerance)
            # - 4000 km² → 14.14m
            # - 9000 km² → 17.32m
            # - 16000 km² → 20.00m
            #
            # This ensures:
            # - Small areas keep high precision (5m minimum)
            # - Large areas get proportionally simplified
            # - Smooth progression (fourth root prevents aggressive simplification)
            # - Topology preservation (no self-intersections)
            if area_m2 > (1000 * 1000000):  # 1000 km²
                # Adaptive formula: 20 * (area_ratio)^0.25
                # The 0.25 power ensures tolerance doesn't grow too quickly with area
                tolerance = 10 * (area_m2 / (1000 * 1000000)) ** 0.25
            else:
                tolerance = 5  # 5 meters minimum for small areas

            # Perform simplification in UTM coordinates
            # preserve_topology=True ensures no invalid geometries are created
            simplified_utm = gdf_utm.geometry.simplify(
                tolerance, preserve_topology=True
            )
            gdf_utm.geometry = simplified_utm

            # Convert back to WGS84 (EPSG:4326) for storage/display
            gdf_wgs = gdf_utm.to_crs("EPSG:4326")

            return gdf_wgs.geometry.iloc[0]

        except Exception as e:
            raise ValueError(f"Error simplifying geometry: {e}")

    def get_simplified_coordinates(self, geometry_location: str) -> Dict[str, Any]:
        """
        Get simplified coordinates for a geometry.

        Args:
            geometry_location (str): The WKB hex string of the geometry

        Returns:
            dict: GeoJSON-like dictionary of simplified coordinates
        """
        try:
            gdf = self.load_shape_geometry(geometry_location)
            if gdf is None or gdf.empty:
                return {}

            simplified = self._simplify_with_utm(gdf.geometry.iloc[0])
            return mapping(simplified)

        except Exception as e:
            raise ValueError(f"Error simplifying geometry: {e}")

    def get_coordinates_from_gdf(self, gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
        """
        Get simplified coordinates from a GeoDataFrame, unifying geometries if multiple.

        Args:
            gdf (gpd.GeoDataFrame): GeoDataFrame containing the geometries

        Returns:
            dict: GeoJSON-like dictionary of simplified coordinates
        """
        if gdf is None or gdf.empty:
            return {}

        try:
            # GeoDataFrame contains multiple geometries
            geometry = (
                gdf.geometry.union_all() if len(gdf) > 1 else gdf.geometry.iloc[0]
            )
            simplified = self._simplify_with_utm(geometry)
            return mapping(simplified)

        except Exception as e:
            raise ValueError(f"Error simplifying geometry: {e}")

    def _retrieve_all_shapes(self) -> List[ShapeRef]:
        """
        Retrieve all shapes from the database.

        Returns:
            List[ShapeRef]: A list of shape references.
        """
        try:
            return self.db.session.query(ShapeRef).all()
        except Exception as e:
            raise DatabaseError("Failed to retrieve all shapes") from e

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

    @error_handler(log=True, raise_error=True)
    def build_spatial_index(self) -> index.Index:
        """
        Build a spatial index for all occurrences.

        Returns:
            index.Index: An R-tree spatial index.
        """
        try:
            idx = index.Index()
            occurrence_location_field = self.group_config.get(
                "occurrence_location_field"
            )

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
        except Exception as e:
            raise DatabaseError("Failed to build spatial index") from e
