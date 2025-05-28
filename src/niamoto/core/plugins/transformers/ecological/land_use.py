"""
Plugin for a complete analysis of land use.
Integrates multiple vector layers to calculate the surface area of each land use
category within a geographic area.
"""

from typing import Dict, Any, List
from pydantic import Field, field_validator
import pandas as pd
import geopandas as gpd
import os

from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
from niamoto.common.exceptions import DataTransformError


class LayerConfig(Dict[str, Any]):
    """Configuration for a layer in the land use analysis"""

    path: str
    field: str
    categories: List[str]


class LandUseConfig(PluginConfig):
    """Configuration for the land use analysis plugin"""

    plugin: str = "land_use_analysis"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "layers": [
                {
                    "path": "",  # Path to the layer
                    "field": "",  # Field containing the category
                    "categories": [],  # List of categories to analyze
                }
            ],
            "shape_field": "geometry",  # Field containing the main geometry
            "area_unit": "ha",  # Unit of surface area: ha, km2 or m2
        }
    )

    @field_validator("params")
    def validate_layers(cls, v):
        """Validate the layer configuration."""
        if "layers" not in v:
            raise ValueError("The 'layers' parameter is required")

        if not isinstance(v["layers"], list) or len(v["layers"]) == 0:
            raise ValueError("The 'layers' parameter must be a non-empty list")

        for i, layer in enumerate(v["layers"]):
            if not isinstance(layer, dict):
                raise ValueError(f"Layer {i} must be a dictionary")

            if "path" not in layer or not layer["path"]:
                raise ValueError(f"The path is missing for layer {i}")

            if "categories" not in layer or not isinstance(layer["categories"], list):
                raise ValueError(f"The categories are missing or invalid for layer {i}")

        # Validate the unit of surface area
        if "area_unit" in v:
            if v["area_unit"] not in ["ha", "km2", "m2"]:
                raise ValueError(
                    f"Invalid unit of surface area: {v['area_unit']}. Use 'ha', 'km2' or 'm2'"
                )

        return v


@register("land_use_analysis", PluginType.TRANSFORMER)
class LandUseAnalysis(TransformerPlugin):
    """
    Plugin for a complete analysis of land use.

    This plugin allows analyzing multiple vector layers and calculating the
    surface areas for different categories. It supports:
    - Substrats (UM/NUM)
    - Zones de vie Holdridge (Sec, Humide, Très Humide)
    - Protected areas (reserves, etc.)
    - Water intakes (PPE)
    - Mining concessions
    - Forest cover

    The results are formatted for visualization in a graph.
    """

    config_model = LandUseConfig

    def validate_config(self, config: Dict[str, Any]) -> LandUseConfig:
        """Validate the plugin configuration."""
        try:
            validated_config = self.config_model(**config)
            return validated_config
        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                f"Invalid configuration for {self.__class__.__name__}: {str(e)}",
                details={"config": config, "error": str(e)},
            ) from e

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze land use from multiple layers.

        Args:
            data: GeoDataFrame containing the main geometry
            config: Configuration with layers and options

        Returns:
            Dictionary with categories and surface areas of land use
        """
        try:
            # Validate the configuration
            validated_config = self.validate_config(config)
            params = validated_config.params

            # Extract the main geometry
            if not isinstance(data, gpd.GeoDataFrame):
                raise DataTransformError(
                    "The input data must be a GeoDataFrame",
                    details={"data_type": type(data).__name__},
                )

            shape_field = params.get("shape_field", "geometry")
            if shape_field not in data.columns and shape_field != "geometry":
                geometry = data.geometry
            else:
                geometry = data[shape_field]

            if geometry.empty:
                raise DataTransformError("No geometry found in the data")

            # Use the first geometry (usually one per shape analysis)
            main_geom = geometry.iloc[0]

            # Calculate the total surface area (in m²)
            total_area_m2 = main_geom.area

            # Get the conversion factor for the unit of surface area
            area_unit = params.get("area_unit", "ha")
            if area_unit == "ha":
                area_factor = 0.0001  # m² to ha
            elif area_unit == "km2":
                area_factor = 0.000001  # m² to km²
            else:
                area_factor = 1.0  # m²

            # Convert the total surface area to the requested unit
            total_area = total_area_m2 * area_factor

            # Initialize the results
            categories = []
            areas = []

            # Base directory for relative paths
            base_dir = self._get_base_directory()

            # Process each layer
            for layer_config in params["layers"]:
                layer_path = layer_config["path"]
                field = layer_config.get("field", "")
                layer_categories = layer_config["categories"]

                # Resolve the relative path if necessary
                if not os.path.isabs(layer_path):
                    layer_path = os.path.join(base_dir, layer_path)

                try:
                    # Load the layer
                    layer_gdf = gpd.read_file(layer_path)

                    if layer_gdf.empty:
                        self._add_empty_results(layer_categories, categories, areas)
                        continue

                    # Ensure the CRS matches
                    if data.crs != layer_gdf.crs:
                        layer_gdf = layer_gdf.to_crs(data.crs)

                    # Clip the layer to the main geometry
                    try:
                        layer_in_area = gpd.clip(
                            layer_gdf,
                            gpd.GeoDataFrame(geometry=[main_geom], crs=data.crs),
                        )
                    except Exception as clip_err:
                        self.logger.error(
                            f"Error clipping layer {layer_path}: {str(clip_err)}"
                        )
                        layer_in_area = gpd.GeoDataFrame(geometry=[], crs=data.crs)

                    # If no data after clipping, add empty results
                    if layer_in_area.empty:
                        self._add_empty_results(layer_categories, categories, areas)
                        continue

                    # If a field is specified, calculate the surface area by category
                    if field:
                        for category in layer_categories:
                            # Filter by category
                            try:
                                category_gdf = layer_in_area[
                                    layer_in_area[field] == category
                                ]
                            except Exception as filter_err:
                                self.logger.error(
                                    f"Error filtering by {field}={category}: {str(filter_err)}"
                                )
                                categories.append(category)
                                areas.append(0.0)
                                continue

                            if category_gdf.empty:
                                categories.append(category)
                                areas.append(0.0)
                            else:
                                # Calculate the surface area in hectares
                                # Note: dissolve to avoid double counting
                                try:
                                    dissolved = category_gdf.dissolve()
                                    area = dissolved.geometry.area.sum() * area_factor
                                except Exception:
                                    # Fallback: sum of areas
                                    area = (
                                        category_gdf.geometry.area.sum() * area_factor
                                    )

                                categories.append(category)
                                areas.append(float(area))
                    else:
                        # If no field, calculate the total surface area
                        # Note: dissolve to avoid double counting
                        try:
                            dissolved = layer_in_area.dissolve()
                            area = dissolved.geometry.area.sum() * area_factor
                        except Exception:
                            # Fallback: sum of areas
                            area = layer_in_area.geometry.area.sum() * area_factor

                        # Use the first category specified
                        category = (
                            layer_categories[0] if layer_categories else "Unknown"
                        )
                        categories.append(category)
                        areas.append(float(area))

                except Exception as e:
                    self.logger.error(f"Error analyzing layer {layer_path}: {str(e)}")
                    # Add empty results for this layer
                    self._add_empty_results(layer_categories, categories, areas)

            return {
                "categories": categories,
                "areas": areas,
                "total_area": float(total_area),
                "area_unit": area_unit,
            }

        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                f"Failed to analyze land use: {str(e)}", details={"config": config}
            )

    def _add_empty_results(
        self, layer_categories: List[str], categories: List[str], areas: List[float]
    ) -> None:
        """Adds empty results for the specified categories."""
        for category in layer_categories:
            categories.append(category)
            areas.append(0.0)

    def _get_base_directory(self) -> str:
        """Gets the base directory for relative paths."""
        try:
            # Try to get the Niamoto config directory
            from niamoto.common.config import Config

            config = Config()
            return os.path.dirname(config.config_dir)
        except Exception:
            # Fallback: use the current directory
            return os.getcwd()
