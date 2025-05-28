"""
Plugin for forest fragmentation analysis.
Calculates various fragmentation metrics to evaluate the state and connectivity
of forest landscapes.
"""

from typing import Dict, Any, List
from pydantic import Field, field_validator
import pandas as pd
import geopandas as gpd
import os
from shapely.geometry import Polygon, MultiPolygon

from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
from niamoto.common.exceptions import DataTransformError


class FragmentationConfig(PluginConfig):
    """Configuration for the fragmentation analysis plugin"""

    plugin: str = "fragmentation_analysis"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "forest_path": "",  # Path to the forest layer
            "shape_field": "geometry",  # Field containing the main geometry
            "metrics": ["patch_count", "meff", "edge_density", "largest_patch_index"],
            "area_unit": "ha",  # Unit for area calculations: ha, km2 or m2
            "edge_width": 100,  # Edge width in meters for edge metrics
            "size_classes": [
                1,
                5,
                10,
                50,
                100,
                500,
                1000,
                float("inf"),
            ],  # Patch size classes (ha)
        }
    )

    @field_validator("params")
    def validate_metrics(cls, v):
        """Validates the fragmentation metrics."""
        valid_metrics = [
            "patch_count",
            "meff",
            "edge_density",
            "largest_patch_index",
            "patch_density",
            "core_area",
            "connectivity_index",
            "size_distribution",
        ]

        if "metrics" in v:
            for metric in v["metrics"]:
                if metric not in valid_metrics:
                    raise ValueError(
                        f"Unsupported metric: {metric}. Valid: {valid_metrics}"
                    )

        # Validate the area unit
        if "area_unit" in v:
            if v["area_unit"] not in ["ha", "km2", "m2"]:
                raise ValueError(
                    f"Invalid area unit: {v['area_unit']}. Use 'ha', 'km2' or 'm2'"
                )

        return v


@register("fragmentation_analysis", PluginType.TRANSFORMER)
class FragmentationAnalysis(TransformerPlugin):
    """
    Plugin for forest fragmentation analysis.

    Calculates various fragmentation metrics to evaluate the state and connectivity
    of forest landscapes, such as:
    - Number of patches (patch_count)
    - Effective mesh size (meff)
    - Edge density (edge_density)
    - Largest patch index (largest_patch_index)
    - Patch size distribution (size_distribution)
    """

    config_model = FragmentationConfig

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validates the plugin configuration."""
        try:
            validated_config = self.config_model(**config)
            params = validated_config.params

            # Validate the path to the forest layer
            if not params.get("forest_path"):
                raise DataTransformError(
                    "The path to the forest layer is required",
                    details={"config": params},
                )

            return validated_config
        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                f"Invalid configuration: {str(e)}", details={"config": config}
            )

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze forest fragmentation.

        Args:
            data: GeoDataFrame containing the shape of the area
            config: Configuration with analysis options

        Returns:
            Dictionary with fragmentation metrics
        """
        try:
            # Validate the configuration
            validated_config = self.validate_config(config)
            params = validated_config.params

            # Extract the geometry
            if not isinstance(data, gpd.GeoDataFrame):
                raise DataTransformError(
                    "Input data must be a GeoDataFrame",
                    details={"data_type": type(data).__name__},
                )

            shape_field = params.get("shape_field", "geometry")
            if shape_field not in data.columns and shape_field != "geometry":
                geometry = data.geometry
            else:
                geometry = data[shape_field]

            if geometry.empty:
                raise DataTransformError("No geometry found in the data")

            # Use the first geometry (usually there is only one per shape analysis)
            main_geom = geometry.iloc[0]

            # Get the area unit conversion factor
            area_unit = params.get("area_unit", "ha")
            if area_unit == "ha":
                area_factor = 0.0001  # m² to ha
            elif area_unit == "km2":
                area_factor = 0.000001  # m² to km²
            else:
                area_factor = 1.0  # m²

            # Calculate the total area in the requested unit
            landscape_area = main_geom.area * area_factor

            # Resolve the path to the forest layer
            forest_path = params["forest_path"]
            if not os.path.isabs(forest_path):
                base_dir = self._get_base_directory()
                forest_path = os.path.join(base_dir, forest_path)

            # Load the forest layer
            forest_gdf = gpd.read_file(forest_path)

            if forest_gdf.empty:
                return self._empty_results(params["metrics"], area_unit)

            # Ensure the CRS matches
            if data.crs != forest_gdf.crs:
                forest_gdf = forest_gdf.to_crs(data.crs)

            # Clip the forest to the main geometry
            try:
                forest_in_area = gpd.clip(
                    forest_gdf, gpd.GeoDataFrame(geometry=[main_geom], crs=data.crs)
                )
            except Exception as clip_err:
                self.logger.error(f"Error clipping the forest: {str(clip_err)}")
                return self._empty_results(params["metrics"], area_unit)

            if forest_in_area.empty:
                return self._empty_results(params["metrics"], area_unit)

            # Initialize the result
            result = {}
            metrics = params["metrics"]

            # Calculate basic metrics
            # 1. Number of patches (patch_count)
            if "patch_count" in metrics:
                # Get individual patches as separate geometries
                # Option 1: Use distinct geometries (if the layer already contains separate patches)
                individual_patches = forest_in_area.geometry

                # Option 2: Extract polygons from a MultiPolygon (if the forest is a single entity)
                # This is useful if the forest layer is a single MultiPolygon after clipping
                extracted_patches = []
                for geom in individual_patches:
                    if isinstance(geom, MultiPolygon):
                        extracted_patches.extend(list(geom.geoms))
                    else:
                        extracted_patches.append(geom)

                # Use the extracted patches if there are more of them
                patches = (
                    extracted_patches
                    if len(extracted_patches) > len(individual_patches)
                    else individual_patches
                )

                patch_count = len(patches)
                result["patch_count"] = patch_count

                # Calculate the sizes of the patches
                patch_sizes = []
                for patch in patches:
                    patch_area = patch.area * area_factor
                    patch_sizes.append(float(patch_area))

                result["patch_sizes"] = sorted(patch_sizes, reverse=True)
                result["total_forest_area"] = float(sum(patch_sizes))

                # Calculate the size distribution
                if len(patch_sizes) > 0:
                    # Define the size classes (in the chosen unit)
                    size_classes = params.get(
                        "size_classes", [1, 5, 10, 50, 100, 500, 1000, float("inf")]
                    )
                    class_labels = []

                    for i in range(len(size_classes) - 1):
                        if size_classes[i + 1] == float("inf"):
                            class_labels.append(f"> {size_classes[i]}")
                        else:
                            class_labels.append(
                                f"{size_classes[i]}-{size_classes[i + 1]}"
                            )

                    # Count the patches in each size class
                    size_class_counts = [0] * len(class_labels)
                    size_class_areas = [0] * len(class_labels)

                    for size in patch_sizes:
                        for i in range(len(size_classes) - 1):
                            if size_classes[i] <= size < size_classes[i + 1]:
                                size_class_counts[i] += 1
                                size_class_areas[i] += size
                                break

                    result["size_classes"] = {
                        "labels": class_labels,
                        "counts": size_class_counts,
                        "areas": [float(area) for area in size_class_areas],
                        "percentages": [
                            round(area / result["total_forest_area"] * 100, 2)
                            if result["total_forest_area"] > 0
                            else 0
                            for area in size_class_areas
                        ],
                    }

            # 2. Effective mesh size (MEFF)
            if "meff" in metrics and result.get("patch_sizes"):
                patch_sizes = result["patch_sizes"]
                if landscape_area > 0 and len(patch_sizes) > 0:
                    # Calculate MEFF = sum(patch_area² / total_area)
                    sum_squares = sum(size * size for size in patch_sizes)
                    meff = sum_squares / landscape_area

                    # If the unit is in ha and MEFF is large, convert to km²
                    if area_unit == "ha" and meff > 100:
                        result["meff"] = float(meff / 100)  # ha to km²
                        result["meff_unit"] = "km²"
                    else:
                        result["meff"] = float(meff)
                        result["meff_unit"] = area_unit
                else:
                    result["meff"] = 0.0
                    result["meff_unit"] = area_unit

                result["landscape_area"] = float(landscape_area)
                result["landscape_unit"] = area_unit

            # 3. Largest patch index (Largest Patch Index)
            if "largest_patch_index" in metrics and result.get("patch_sizes"):
                patch_sizes = result["patch_sizes"]
                if len(patch_sizes) > 0 and landscape_area > 0:
                    largest_patch = max(patch_sizes)
                    largest_patch_index = largest_patch / landscape_area * 100

                    result["largest_patch"] = float(largest_patch)
                    result["largest_patch_index"] = float(largest_patch_index)
                else:
                    result["largest_patch"] = 0.0
                    result["largest_patch_index"] = 0.0

            # 4. Edge density (Edge Density)
            if "edge_density" in metrics:
                # Calculate total edge length
                total_edge = 0
                for geom in forest_in_area.geometry:
                    if isinstance(geom, Polygon):
                        total_edge += geom.exterior.length
                        for interior in geom.interiors:
                            total_edge += interior.length
                    elif isinstance(geom, MultiPolygon):
                        for poly in geom.geoms:
                            total_edge += poly.exterior.length
                            for interior in poly.interiors:
                                total_edge += interior.length

                # Edge density = total edge length / total area
                # Convert according to units (m/ha or m/km²)
                if landscape_area > 0:
                    if area_unit == "ha":
                        edge_density = total_edge / (landscape_area * 10000)  # m/ha
                        edge_unit = "m/ha"
                    elif area_unit == "km2":
                        edge_density = total_edge / (landscape_area * 1000000)  # m/km²
                        edge_unit = "m/km²"
                    else:
                        edge_density = total_edge / landscape_area  # m/m²
                        edge_unit = "m/m²"
                else:
                    edge_density = 0
                    edge_unit = f"m/{area_unit}"

                result["edge_length"] = float(total_edge)
                result["edge_density"] = float(edge_density)
                result["edge_unit"] = edge_unit

            # 5. Landscape connectivity
            if "connectivity_index" in metrics and result.get("patch_sizes"):
                patch_sizes = result["patch_sizes"]
                if len(patch_sizes) > 1 and landscape_area > 0:
                    # Simple connectivity index: probability that two random points
                    # are in the same patch
                    sum_squares = sum(size * size for size in patch_sizes)
                    total_forest_area = sum(patch_sizes)

                    if total_forest_area > 0:
                        connectivity = sum_squares / (
                            total_forest_area * total_forest_area
                        )
                        result["connectivity_index"] = float(connectivity)
                    else:
                        result["connectivity_index"] = 0.0
                else:
                    # If only one patch, connectivity is 1
                    result["connectivity_index"] = 1.0 if len(patch_sizes) == 1 else 0.0

            # 6. Core area
            if "core_area" in metrics:
                edge_width = params.get("edge_width", 100)  # In meters

                # Create negative buffers for each patch to get the core areas
                core_areas = []
                total_core_area = 0

                for geom in forest_in_area.geometry:
                    # Apply negative buffer to get the core area
                    try:
                        core = geom.buffer(-edge_width)
                        if not core.is_empty:
                            core_area = core.area * area_factor
                            core_areas.append(float(core_area))
                            total_core_area += core_area
                    except Exception:
                        # Handle cases where the negative buffer makes the polygon disappear
                        pass

                result["core_areas"] = core_areas
                result["total_core_area"] = float(total_core_area)

                # Calculate the core area percentage
                if result.get("total_forest_area", 0) > 0:
                    core_percentage = (
                        total_core_area / result["total_forest_area"] * 100
                    )
                    result["core_area_percentage"] = float(core_percentage)
                else:
                    result["core_area_percentage"] = 0.0

            # Add the used area unit
            result["area_unit"] = area_unit

            return result

        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                f"Failed to calculate fragmentation metrics: {str(e)}",
                details={"config": config},
            )

    def _empty_results(self, metrics: List[str], area_unit: str) -> Dict[str, Any]:
        """Creates an empty result with the required metrics."""
        result = {
            "patch_count": 0,
            "patch_sizes": [],
            "total_forest_area": 0.0,
            "area_unit": area_unit,
        }

        if "meff" in metrics:
            result["meff"] = 0.0
            result["meff_unit"] = area_unit if area_unit != "ha" else "km²"

        if "largest_patch_index" in metrics:
            result["largest_patch"] = 0.0
            result["largest_patch_index"] = 0.0

        if "edge_density" in metrics:
            result["edge_length"] = 0.0
            result["edge_density"] = 0.0
            result["edge_unit"] = f"m/{area_unit}"

        if "connectivity_index" in metrics:
            result["connectivity_index"] = 0.0

        if "core_area" in metrics:
            result["core_areas"] = []
            result["total_core_area"] = 0.0
            result["core_area_percentage"] = 0.0

        if "size_distribution" in metrics:
            result["size_classes"] = {
                "labels": [],
                "counts": [],
                "areas": [],
                "percentages": [],
            }

        return result

    def _get_base_directory(self) -> str:
        """Gets the base directory for relative paths."""
        try:
            # Try to get the Niamoto configuration directory first
            from niamoto.common.config import Config

            config = Config()
            return os.path.dirname(config.config_dir)
        except Exception:
            # Fallback: use the current directory
            return os.getcwd()
