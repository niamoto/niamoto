"""
Plugin for vector overlay analysis.
Performs various overlay operations between a main geometry (shape) and an
external vector layer. It supports:

- intersection: Calculates the intersection between the two layers
- clip: Clipping the external layer by the main geometry
- coverage: Calculates the coverage rate (% of the main area covered)
- aggregate: Aggregates statistics by category (if attribute_field is specified)

The results are formatted to be used directly in visualization widgets
or for further analysis.
"""

from typing import Dict, Any, List
from pydantic import Field, field_validator
import pandas as pd
import geopandas as gpd
import os
import logging
from shapely.ops import unary_union

from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
from niamoto.common.exceptions import DataTransformError


class VectorOverlayConfig(PluginConfig):
    """Configuration for the vector overlay analysis plugin"""

    plugin: str = "vector_overlay"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "overlay_path": "",  # Path to the overlay layer
            "shape_field": "geometry",  # Field containing the main geometry
            "operation": "intersection",  # intersection, union, difference, clip, etc.
            "attribute_field": None,  # Field to use for categorization
            "where": None,  # SQL filter for the overlay layer
            "area_unit": "ha",  # Unit of area: ha, km2 or m2
        }
    )

    @field_validator("params")
    def validate_params(cls, v):
        """Validate the plugin parameters."""
        # Overlay path is only required for operations other than 'coverage'
        if v.get("operation") != "coverage" and (
            "overlay_path" not in v or not v["overlay_path"]
        ):
            raise ValueError(
                "The path to the overlay layer is required for operations other than 'coverage'"
            )

        # Validate the operation
        valid_operations = [
            "intersection",
            "union",
            "difference",
            "symmetric_difference",
            "clip",
            "coverage",
            "identity",
            "aggregate",
        ]

        if "operation" in v and v["operation"] not in valid_operations:
            raise ValueError(
                f"Unsupported operation: {v['operation']}. "
                f"Valid options: {', '.join(valid_operations)}"
            )

        # Validate the unit of area
        if "area_unit" in v:
            valid_units = ["ha", "km2", "m2"]
            if v["area_unit"] not in valid_units:
                raise ValueError(
                    f"Invalid unit of area: {v['area_unit']}. "
                    f"Valid options: {', '.join(valid_units)}"
                )

        return v


@register("vector_overlay", PluginType.TRANSFORMER)
class VectorOverlay(TransformerPlugin):
    """
    Plugin for vector overlay analysis.

    This plugin allows performing various overlay operations between a
    main geometry (shape) and an external vector layer. It supports:

    - intersection: Calculate the intersection between the two layers
    - clip: Clip the external layer by the main geometry
    - coverage: Calculate the coverage rate (% of the main area covered)
    - aggregate: Aggregate statistics by category (if attribute_field is specified)

    The results are formatted to be used directly in visualization widgets
    or for more advanced analyses.
    """

    config_model = VectorOverlayConfig

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the plugin configuration."""
        try:
            return self.config_model(**config)
        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                f"Invalid configuration: {str(e)}", details={"config": config}
            )

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform a vector overlay analysis.

        Args:
            data: GeoDataFrame containing the main shape
            config: Configuration with overlay options

        Returns:
            Dictionary with the analysis results
        """
        try:
            # Validate the configuration
            validated_config = self.validate_config(config)
            params = validated_config.params

            # 1. Prepare the main GeoDataFrame
            main_gdf = self._prepare_main_geodataframe(data, params)

            # 2. Determine the operation and execute
            operation = params.get("operation", "intersection")

            # If it's a coverage operation without overlay_path, treat separately
            if operation == "coverage" and "overlay_path" not in params:
                return self._calculate_total_area(
                    main_gdf, params.get("area_unit", "ha")
                )

            # 3. Load the overlay layer
            overlay_gdf = self._load_overlay_layer(params)

            # Ensure the CRS matches
            if main_gdf.crs != overlay_gdf.crs:
                self.logger.info(
                    f"Converting the CRS of the overlay layer from {overlay_gdf.crs} to {main_gdf.crs}"
                )
                overlay_gdf = overlay_gdf.to_crs(main_gdf.crs)

            # 4. Execute the appropriate overlay operation
            return self._execute_overlay_operation(
                main_gdf, overlay_gdf, operation, params
            )

        except Exception as e:
            self.logger.error(f"Error during vector overlay analysis: {str(e)}")
            if isinstance(e, DataTransformError):
                raise e
            else:
                raise DataTransformError(
                    f"Error during vector overlay analysis: {str(e)}",
                    details={"config": config},
                )

    def _prepare_main_geodataframe(
        self, data: pd.DataFrame, params: Dict[str, Any]
    ) -> gpd.GeoDataFrame:
        """
        Prepare the main GeoDataFrame from the input data.

        Args:
            data: Input data
            params: Configuration parameters

        Returns:
            Main GeoDataFrame
        """
        self.logger.info(
            f"Preparing the main GeoDataFrame, input type: {type(data).__name__}"
        )

        if isinstance(data, gpd.GeoDataFrame):
            self.logger.debug(
                f"Input is already a GeoDataFrame, columns: {list(data.columns)}"
            )
            # Use the GeoDataFrame directly
            main_gdf = data
        else:
            self.logger.debug("Attempting to extract geometry from the input data")
            # Check that the data is a DataFrame
            if not isinstance(data, pd.DataFrame):
                raise DataTransformError(
                    "The input data must be a DataFrame",
                    details={"data_type": type(data).__name__},
                )

            shape_field = params.get("shape_field", "geometry")

            # Complex case: shape_field is a dict, list or reference
            if isinstance(shape_field, (dict, list)) or (
                isinstance(shape_field, str) and shape_field.startswith("@")
            ):
                raise DataTransformError(
                    "Cannot extract geometry from a complex field or reference",
                    details={"shape_field_type": type(shape_field).__name__},
                )

            # Standard case: extract from a field
            if shape_field not in data.columns:
                raise DataTransformError(
                    f"Geometry field '{shape_field}' not found in the input data",
                    details={"available_columns": list(data.columns)},
                )

            # Create a GeoDataFrame with the specified geometry
            main_gdf = gpd.GeoDataFrame(data, geometry=shape_field)

        # Final check
        if not isinstance(main_gdf, gpd.GeoDataFrame) or main_gdf.empty:
            raise DataTransformError(
                "Cannot create a valid GeoDataFrame from the input data",
                details={"main_gdf_type": type(main_gdf).__name__},
            )

        return main_gdf

    def _calculate_total_area(
        self, gdf: gpd.GeoDataFrame, area_unit: str
    ) -> Dict[str, Any]:
        """
        Calculate the total area of a GeoDataFrame.

        Args:
            gdf: GeoDataFrame
            area_unit: Unit of area (ha, km2, m2)

        Returns:
            Dictionary with the results of the area calculation
        """
        area_factor = self._get_area_factor(area_unit)

        try:
            # Project to an appropriate projected CRS for precise area calculations
            if gdf.crs and gdf.crs.is_geographic:
                self.logger.info(
                    "Projecting to an appropriate projected CRS for area calculation"
                )
                projected_gdf = self._project_to_appropriate_utm(gdf)
                total_area = projected_gdf.geometry.area.sum() * area_factor
            else:
                total_area = gdf.geometry.area.sum() * area_factor

            return {
                "total_area": float(total_area),
                "area_unit": area_unit,
                "coverage_area": float(total_area),
                "coverage_percentage": 100.0,
            }
        except Exception as area_err:
            self.logger.error(f"Error during area calculation: {str(area_err)}")
            return {
                "total_area": 0.0,
                "area_unit": area_unit,
                "coverage_area": 0.0,
                "coverage_percentage": 0.0,
                "area_error": str(area_err),
            }

    def _get_area_factor(self, area_unit: str) -> float:
        """
        Gets the area conversion factor according to the unit.

        Args:
            area_unit: Area unit (ha, km2, m2)

        Returns:
            Conversion factor
        """
        if area_unit == "ha":
            return 0.0001  # m² to ha
        elif area_unit == "km2":
            return 0.000001  # m² to km²
        else:
            return 1.0  # m²

    def _project_to_appropriate_utm(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Projects a GeoDataFrame to an appropriate UTM zone determined dynamically.

        Args:
            gdf: GeoDataFrame to project

        Returns:
            Projected GeoDataFrame
        """
        try:
            # Check that the GeoDataFrame has a defined projection
            if not gdf.crs:
                self.logger.warning(
                    "The GeoDataFrame does not have a defined CRS, cannot project"
                )
                return gdf

            # Ensure that the GeoDataFrame is in WGS84 (EPSG:4326) for correct UTM zone calculation
            if gdf.crs != "EPSG:4326":
                gdf_wgs84 = gdf.to_crs("EPSG:4326")
            else:
                gdf_wgs84 = gdf

            # Calculate the centroid to determine the UTM zone
            centroid = gdf_wgs84.unary_union.centroid

            # Calculate the UTM zone number from the longitude
            # Formula: ((longitude + 180)/6) + 1 (gives a zone number between 1-60)
            zone_number = int((centroid.x + 180) // 6) + 1

            # Determine the hemisphere from the latitude
            zone_hemisphere = "N" if centroid.y >= 0 else "S"

            # Special case for New Caledonia (if necessary)
            if 162 <= centroid.x <= 169 and -23 <= centroid.y <= -19:
                self.logger.debug("Using UTM 58S projection for New Caledonia")
                return gdf.to_crs("EPSG:3163")  # UTM 58S

            # Get the EPSG code for the UTM zone
            # Range: 32601-32660 for North, 32701-32760 for South
            utm_epsg = (
                32600 + zone_number if zone_hemisphere == "N" else 32700 + zone_number
            )

            self.logger.debug(
                f"Projecting to UTM zone {zone_number}{zone_hemisphere} (EPSG:{utm_epsg})"
            )

            # Project the GeoDataFrame to the calculated UTM zone
            return gdf.to_crs(f"EPSG:{utm_epsg}")

        except Exception as e:
            self.logger.warning(f"Error during UTM projection: {str(e)}")
            # On error, return the original GeoDataFrame
            return gdf

    def _load_overlay_layer(self, params: Dict[str, Any]) -> gpd.GeoDataFrame:
        """
        Loads the overlay layer.

        Args:
            params: Configuration parameters

        Returns:
            GeoDataFrame of the overlay layer
        """
        overlay_path = params.get("overlay_path")
        if not overlay_path:
            raise DataTransformError("Overlay path not specified")

        self.logger.info(f"Loading overlay layer: {overlay_path}")

        try:
            # Resolve the path
            resolved_path = self._resolve_path(overlay_path)

            # Load the layer
            overlay_gdf = gpd.read_file(resolved_path)
            self.logger.debug(
                f"Loaded layer with {len(overlay_gdf)} entities, CRS: {overlay_gdf.crs}"
            )

            # Apply a WHERE filter if specified
            where_clause = params.get("where")
            if where_clause:
                overlay_gdf = self._apply_where_filter(overlay_gdf, where_clause)

            return overlay_gdf

        except Exception as e:
            raise DataTransformError(
                f"Error loading overlay layer: {str(e)}",
                details={"overlay_path": overlay_path},
            )

    def _apply_where_filter(
        self, gdf: gpd.GeoDataFrame, where_clause: str
    ) -> gpd.GeoDataFrame:
        """
        Applies a WHERE filter to a GeoDataFrame.

        Args:
            gdf: GeoDataFrame to filter
            where_clause: WHERE clause

        Returns:
            Filtered GeoDataFrame
        """
        self.logger.info(f"Applying filter: {where_clause}")

        try:
            if isinstance(where_clause, str):
                # Use eval for simple expressions
                mask = gdf.eval(where_clause, engine="python")
                filtered_gdf = gdf[mask]
                self.logger.debug(f"After filtering: {len(filtered_gdf)} features")
                return filtered_gdf
            else:
                self.logger.warning(
                    f"Unsupported WHERE clause type: {type(where_clause).__name__}"
                )
                return gdf
        except Exception as e:
            self.logger.warning(f"Error applying filter: {str(e)}")
            return gdf

    def _execute_overlay_operation(
        self,
        main_gdf: gpd.GeoDataFrame,
        overlay_gdf: gpd.GeoDataFrame,
        operation: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Executes the specified overlay operation.

        Args:
            main_gdf: Main GeoDataFrame
            overlay_gdf: Overlay GeoDataFrame
            operation: Type of operation
            params: Configuration parameters

        Returns:
            Results of the operation
        """
        self.logger.info(f"Executing {operation} operation")

        # Basic geopandas operations
        if operation in ["intersection", "union", "difference", "symmetric_difference"]:
            return self._perform_basic_operation(
                main_gdf, overlay_gdf, operation, params
            )

        # Specific operations
        elif operation == "clip":
            return self._perform_clip_operation(main_gdf, overlay_gdf, params)
        elif operation == "coverage":
            return self._perform_coverage_operation(main_gdf, overlay_gdf, params)
        elif operation == "aggregate":
            return self._perform_aggregate_operation(main_gdf, overlay_gdf, params)
        elif operation == "identity":
            return self._perform_identity_operation(main_gdf, overlay_gdf, params)
        else:
            raise DataTransformError(f"Operation not implemented: {operation}")

    def _perform_basic_operation(
        self,
        main_gdf: gpd.GeoDataFrame,
        overlay_gdf: gpd.GeoDataFrame,
        operation: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Executes a basic operation (intersection, union, difference, symmetric_difference).

        Args:
            main_gdf: Main GeoDataFrame
            overlay_gdf: Overlay GeoDataFrame
            operation: Type of operation
            params: Configuration parameters

        Returns:
            Results of the operation
        """
        try:
            # Execute the operation
            result_gdf = gpd.overlay(main_gdf, overlay_gdf, how=operation)
            self.logger.info(
                f"{operation} operation completed, {len(result_gdf)} resulting entities"
            )

            # Calculate statistics
            stats = self._calculate_statistics(
                result_gdf, params.get("area_unit", "ha")
            )

            return {"stats": stats, "result_gdf": result_gdf}
        except Exception as e:
            raise DataTransformError(f"Error during {operation} operation: {str(e)}")

    def _perform_clip_operation(
        self,
        main_gdf: gpd.GeoDataFrame,
        overlay_gdf: gpd.GeoDataFrame,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Executes a clip operation.

        Args:
            main_gdf: Main GeoDataFrame (clip mask)
            overlay_gdf: GeoDataFrame to clip
            params: Configuration parameters

        Returns:
            Operation results
        """
        try:
            # Execute the clip
            clipped_gdf = gpd.clip(overlay_gdf, main_gdf)
            self.logger.info(
                f"Clip operation completed, {len(clipped_gdf)} resulting features"
            )

            # Calculate statistics
            area_unit = params.get("area_unit", "ha")
            area_factor = self._get_area_factor(area_unit)

            # Prepare results
            clipped_features = []
            attribute_field = params.get("attribute_field")

            for idx, row in clipped_gdf.iterrows():
                area = row.geometry.area * area_factor
                feature_info = {"id": idx, "area": float(area)}

                # Include attribute if specified
                if attribute_field and attribute_field in row:
                    feature_info["attribute"] = row[attribute_field]

                clipped_features.append(feature_info)

            # Calculate total area
            total_area = self._calculate_total_area(main_gdf, area_unit)["total_area"]

            result = {
                "total_area": total_area,
                "area_unit": area_unit,
                "clipped_features": clipped_features,
                "feature_count": len(clipped_features),
            }

            # Generate attribute summary if requested
            if attribute_field and attribute_field in clipped_gdf.columns:
                summary = self._generate_attribute_summary(clipped_features, total_area)
                result["summary"] = summary

            return result

        except Exception as e:
            raise DataTransformError(f"Error during clip operation: {str(e)}")

    def _perform_coverage_operation(
        self,
        main_gdf: gpd.GeoDataFrame,
        overlay_gdf: gpd.GeoDataFrame,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Calculates the coverage rate.

        Args:
            main_gdf: Main GeoDataFrame (overlay mask)
            overlay_gdf: GeoDataFrame to overlay
            params: Configuration parameters

        Returns:
            Operation results
        """
        try:
            area_unit = params.get("area_unit", "ha")
            area_factor = self._get_area_factor(area_unit)

            # Calculate the total area of the main geometry
            total_area = self._calculate_total_area(main_gdf, area_unit)["total_area"]

            # If no entities in the overlay layer, return 0% coverage
            if overlay_gdf.empty:
                return {
                    "total_area": total_area,
                    "area_unit": area_unit,
                    "coverage_area": 0.0,
                    "coverage_percentage": 0.0,
                }

            # Union the geometries to avoid double counting
            overlay_geoms = overlay_gdf.geometry.tolist()
            union_geom = unary_union(overlay_geoms)

            # Union the main geometries as well
            main_geoms = main_gdf.geometry.tolist()
            main_union = unary_union(main_geoms)

            # Calculate the intersection
            intersection = main_union.intersection(union_geom)

            # Project for a precise area calculation
            if main_gdf.crs and main_gdf.crs.is_geographic:
                # Create a temporary GeoDataFrame for the projection
                temp_gdf = gpd.GeoDataFrame(
                    geometry=[main_union, intersection], crs=main_gdf.crs
                )
                projected_gdf = self._project_to_appropriate_utm(temp_gdf)

                # Extract the projected geometries
                projected_main = projected_gdf.geometry.iloc[0]
                projected_intersection = projected_gdf.geometry.iloc[1]

                # Calculate the areas
                main_area = projected_main.area * area_factor
                intersection_area = projected_intersection.area * area_factor
            else:
                main_area = main_union.area * area_factor
                intersection_area = intersection.area * area_factor

            # Calculate the percentage
            coverage_percentage = (
                (intersection_area / main_area) * 100 if main_area > 0 else 0
            )

            return {
                "total_area": float(main_area),
                "area_unit": area_unit,
                "coverage_area": float(intersection_area),
                "coverage_percentage": float(coverage_percentage),
            }

        except Exception as e:
            raise DataTransformError(f"Error during coverage operation: {str(e)}")

    def _perform_aggregate_operation(
        self,
        main_gdf: gpd.GeoDataFrame,
        overlay_gdf: gpd.GeoDataFrame,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Aggregates statistics by attribute.

        Args:
            main_gdf: Main GeoDataFrame
            overlay_gdf: GeoDataFrame to overlay
            params: Configuration parameters

        Returns:
            Operation results
        """
        attribute_field = params.get("attribute_field")
        if not attribute_field:
            raise DataTransformError(
                "The attribute field is required for the 'aggregate' operation"
            )

        if attribute_field not in overlay_gdf.columns:
            raise DataTransformError(
                f"Attribute field '{attribute_field}' not found in the overlay layer",
                details={"available_fields": list(overlay_gdf.columns)},
            )

        try:
            area_unit = params.get("area_unit", "ha")

            # Calculate the total area
            total_area = self._calculate_total_area(main_gdf, area_unit)["total_area"]

            # Execute the intersection
            intersection_gdf = gpd.overlay(main_gdf, overlay_gdf, how="intersection")

            # If no intersection, return an empty result
            if intersection_gdf.empty:
                return {
                    "total_area": total_area,
                    "area_unit": area_unit,
                    "aggregation": {"categories": [], "areas": [], "percentages": []},
                }

            # Project for a precise area calculation
            if intersection_gdf.crs and intersection_gdf.crs.is_geographic:
                projected_gdf = self._project_to_appropriate_utm(intersection_gdf)
            else:
                projected_gdf = intersection_gdf

            # Calculate the area for each entity
            area_factor = self._get_area_factor(area_unit)
            projected_gdf["_area"] = projected_gdf.geometry.area * area_factor

            # Group by attribute and aggregate areas
            aggregation = {}

            for attr, group in projected_gdf.groupby(attribute_field):
                aggregation[attr] = group["_area"].sum()

            # Format the results
            categories = list(aggregation.keys())
            areas = [float(area) for area in aggregation.values()]
            percentages = [
                round(area / total_area * 100, 2) if total_area > 0 else 0
                for area in areas
            ]

            return {
                "total_area": total_area,
                "area_unit": area_unit,
                "aggregation": {
                    "categories": categories,
                    "areas": areas,
                    "percentages": percentages,
                },
            }

        except Exception as e:
            raise DataTransformError(f"Error during aggregation: {str(e)}")

    def _perform_identity_operation(
        self,
        main_gdf: gpd.GeoDataFrame,
        overlay_gdf: gpd.GeoDataFrame,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Executes an identity operation (intersection with attribute conservation).

        Args:
            main_gdf: Main GeoDataFrame
            overlay_gdf: GeoDataFrame to overlay
            params: Configuration parameters

        Returns:
            Operation results
        """
        try:
            # Execute the identity operation (equivalent to intersection but with attribute conservation)
            identity_gdf = gpd.overlay(main_gdf, overlay_gdf, how="identity")

            # Calculate statistics
            area_unit = params.get("area_unit", "ha")
            area_factor = self._get_area_factor(area_unit)

            # Prepare results
            identity_features = []
            attribute_field = params.get("attribute_field")

            for idx, row in identity_gdf.iterrows():
                area = row.geometry.area * area_factor

                feature_info = {"id": idx, "area": float(area)}

                # Add all attributes from the overlay layer
                for col in overlay_gdf.columns:
                    if col != "geometry" and col in row:
                        feature_info[col] = row[col]

                identity_features.append(feature_info)

            # Calculate the total area
            total_area = self._calculate_total_area(main_gdf, area_unit)["total_area"]

            result = {
                "total_area": total_area,
                "area_unit": area_unit,
                "identity_features": identity_features,
                "feature_count": len(identity_features),
            }

            # Generate an attribute summary if requested
            if attribute_field and attribute_field in identity_gdf.columns:
                summary = self._generate_attribute_summary(
                    identity_features, total_area, attribute_field
                )
                result["summary"] = summary

            return result

        except Exception as e:
            raise DataTransformError(f"Error during identity operation: {str(e)}")

    def _calculate_statistics(
        self, gdf: gpd.GeoDataFrame, area_unit: str
    ) -> Dict[str, Any]:
        """
        Calculate statistics for a GeoDataFrame.

        Args:
            gdf: GeoDataFrame
            area_unit: Unit of area

        Returns:
            Dictionary of statistics
        """
        stats = {}

        # Number of entities
        stats["feature_count"] = len(gdf)

        if not gdf.empty:
            # Calculate area if the geometry allows
            if gdf.geometry.iloc[0].geom_type in ["Polygon", "MultiPolygon"]:
                area_factor = self._get_area_factor(area_unit)

                try:
                    # Project to an appropriate projected CRS for precise area calculations
                    if gdf.crs and gdf.crs.is_geographic:
                        projected_gdf = self._project_to_appropriate_utm(gdf)
                        area_series = projected_gdf.geometry.area * area_factor
                    else:
                        area_series = gdf.geometry.area * area_factor

                    stats["total_area"] = float(area_series.sum())
                    stats["min_area"] = float(area_series.min())
                    stats["max_area"] = float(area_series.max())
                    stats["mean_area"] = float(area_series.mean())
                except Exception as e:
                    self.logger.warning(f"Error during area calculation: {str(e)}")
                    stats["area_error"] = str(e)

            # Statistics for numeric columns
            numeric_columns = gdf.select_dtypes(include=["number"]).columns
            for col in numeric_columns:
                if col != gdf.geometry.name:  # Exclude the geometry column
                    col_stats = {
                        f"{col}_sum": float(gdf[col].sum()),
                        f"{col}_min": float(gdf[col].min()),
                        f"{col}_max": float(gdf[col].max()),
                        f"{col}_mean": float(gdf[col].mean()),
                    }
                    stats.update(col_stats)

        return stats

    def _generate_attribute_summary(
        self,
        features: List[Dict[str, Any]],
        total_area: float,
        attribute_field: str = "attribute",
    ) -> Dict[str, Any]:
        """
        Generate an attribute summary of statistics.

        Args:
            features: List of features with attributes
            total_area: Total area
            attribute_field: Name of the attribute field

        Returns:
            Attribute summary
        """
        summary = {}

        for feature in features:
            if attribute_field not in feature:
                continue

            attr = feature[attribute_field]
            area = feature["area"]

            if attr in summary:
                summary[attr] += area
            else:
                summary[attr] = area

        categories = list(summary.keys())
        areas = [float(area) for area in summary.values()]
        percentages = [
            round(area / total_area * 100, 2) if total_area > 0 else 0 for area in areas
        ]

        return {"categories": categories, "areas": areas, "percentages": percentages}

    def _resolve_path(self, path: str) -> str:
        """
        Resolve a relative path to an absolute path.

        Args:
            path: Path to resolve

        Returns:
            Absolute path
        """
        if os.path.isabs(path):
            return path

        base_dir = self._get_base_directory()
        return os.path.join(base_dir, path)

    def _get_base_directory(self) -> str:
        """
        Get the base directory for relative paths.

        Returns:
            Base directory path
        """
        # By default, use the current working directory
        return os.getcwd()
