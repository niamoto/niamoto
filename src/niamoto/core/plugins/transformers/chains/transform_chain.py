"""
Plugin for chaining multiple transformations.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import pandas as pd
import geopandas as gpd

from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
from niamoto.core.plugins.registry import PluginRegistry
from niamoto.common.exceptions import DataTransformError


class TransformStepConfig(BaseModel):
    """Configuration for a single step in a transform chain"""

    plugin: str = Field(..., description="Transformer plugin to use")
    params: Dict[str, Any] = Field(
        default_factory=dict, description="Parameters for the transformer"
    )
    output_key: str = Field(..., description="Key under which to store the output")


class TransformChainConfig(PluginConfig):
    """Configuration for transform chain plugin"""

    plugin: str = "transform_chain"
    steps: Optional[List[TransformStepConfig]] = Field(
        None, description="Steps in the transform chain (legacy format)"
    )
    params: Optional[Dict[str, Any]] = Field(
        None, description="Parameters including steps"
    )


@register("transform_chain", PluginType.TRANSFORMER)
class TransformChain(TransformerPlugin):
    """Plugin for chaining multiple transformations"""

    config_model = TransformChainConfig

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate plugin configuration."""
        try:
            validated_config = self.config_model(**config)

            # Get steps from either top-level or params.steps
            steps = []
            if validated_config.steps:
                # Legacy format with steps at top level
                steps = validated_config.steps
            elif validated_config.params and "steps" in validated_config.params:
                # New format with steps in params
                params_steps = validated_config.params["steps"]
                # Convert each step dict to TransformStepConfig
                for step_dict in params_steps:
                    steps.append(TransformStepConfig(**step_dict))

            if not steps:
                raise DataTransformError(
                    "No steps found in transform chain configuration",
                    details={"config": config},
                )

            # Validate each step
            for step in steps:
                # Check if the referenced plugin exists
                if not PluginRegistry.has_plugin(step.plugin, PluginType.TRANSFORMER):
                    raise DataTransformError(
                        f"Plugin {step.plugin} not found",
                        details={
                            "available_plugins": PluginRegistry.list_plugins()[
                                PluginType.TRANSFORMER
                            ]
                        },
                    )

            # Add steps to validated_config for easier access
            validated_config.steps = steps
            return validated_config
        except Exception as e:
            raise DataTransformError(f"Invalid transform chain configuration: {str(e)}")

    def _resolve_references(
        self, params: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Résout les références dans les paramètres.

        Args:
            params: Paramètres à traiter
            context: Contexte contenant les résultats précédents

        Returns:
            Paramètres avec références résolues
        """
        if not params:
            return {}

        resolved = {}

        for key, value in params.items():
            if isinstance(value, str) and value.startswith("@"):
                # C'est une référence à un résultat précédent
                ref_parts = value[1:].split(".")
                ref_key = ref_parts[0]

                if ref_key not in context:
                    # La référence n'existe pas, utiliser la valeur telle quelle
                    resolved[key] = value
                    continue

                ref_value = context[ref_key]

                # Si la référence a des sous-parties (ex: @step1.field1)
                if len(ref_parts) > 1:
                    try:
                        for part in ref_parts[1:]:
                            if isinstance(ref_value, dict) and part in ref_value:
                                ref_value = ref_value[part]
                            elif hasattr(ref_value, part):
                                ref_value = getattr(ref_value, part)
                            else:
                                # Sous-partie non trouvée, utiliser la valeur complète
                                ref_value = context[ref_key]
                                break
                    except Exception:
                        # En cas d'erreur, utiliser la valeur telle quelle
                        resolved[key] = value
                        continue

                resolved[key] = ref_value
            elif isinstance(value, dict):
                # Résoudre récursivement les références dans les sous-dictionnaires
                resolved[key] = self._resolve_references(value, context)
            elif isinstance(value, list):
                # Résoudre les références dans les listes
                resolved_list = []
                for item in value:
                    if isinstance(item, dict):
                        resolved_list.append(self._resolve_references(item, context))
                    elif isinstance(item, str) and item.startswith("@"):
                        # Référence dans une liste
                        ref_parts = item[1:].split(".")
                        ref_key = ref_parts[0]

                        if ref_key not in context:
                            resolved_list.append(item)
                            continue

                        ref_value = context[ref_key]

                        # Si la référence a des sous-parties
                        if len(ref_parts) > 1:
                            try:
                                for part in ref_parts[1:]:
                                    if (
                                        isinstance(ref_value, dict)
                                        and part in ref_value
                                    ):
                                        ref_value = ref_value[part]
                                    elif hasattr(ref_value, part):
                                        ref_value = getattr(ref_value, part)
                                    else:
                                        ref_value = context[ref_key]
                                        break
                            except Exception:
                                resolved_list.append(item)
                                continue

                        resolved_list.append(ref_value)
                    else:
                        resolved_list.append(item)

                resolved[key] = resolved_list
            else:
                # Valeur simple, pas de résolution nécessaire
                resolved[key] = value

        return resolved

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a chain of transformations.

        Args:
            data: Input DataFrame
            config: Configuration dictionary with either:
                - steps: List of transformation steps (legacy format)
                - params.steps: List of transformation steps (new format)

        Returns:
            Dictionary with combined results from all steps

        Raises:
            DataTransformError: If any step fails
        """
        try:
            # Validate configuration
            validated_config = self.validate_config(config)

            # Context for storing intermediate results
            context = {}
            # Final result
            result = {}
            # Current data being passed between steps
            current_data = data
            # Keep track of the last GeoDataFrame for geospatial operations
            last_geodataframe = None

            # Execute each step
            for step_config in validated_config.steps:
                # Get plugin class
                plugin_class = PluginRegistry.get_plugin(
                    step_config.plugin, PluginType.TRANSFORMER
                )
                plugin_instance = plugin_class(self.db)

                # Resolve references in parameters
                resolved_params = self._resolve_references(step_config.params, context)

                # Prepare step configuration
                step_full_config = {
                    "plugin": step_config.plugin,
                    "params": resolved_params,
                    # Copy group_id if present
                    "group_id": config.get("group_id"),
                }

                # Execute transformation
                try:
                    # Check if this is a geospatial plugin and if we have a GeoDataFrame stored
                    is_geospatial = step_config.plugin in [
                        "vector_overlay",
                        "raster_stats",
                    ]

                    if is_geospatial:
                        print(
                            f"DEBUG - Transform Chain - Is geospatial: True, Last GeoDataFrame: {last_geodataframe is not None}"
                        )

                    if (
                        is_geospatial
                        and last_geodataframe is not None
                        and not isinstance(current_data, gpd.GeoDataFrame)
                    ):
                        step_result = plugin_instance.transform(
                            last_geodataframe, step_full_config
                        )
                    else:
                        step_result = plugin_instance.transform(
                            current_data, step_full_config
                        )

                    # Store the GeoDataFrame if this step produced one
                    if isinstance(step_result, dict) and "_gdf" in step_result:
                        last_geodataframe = step_result["_gdf"]
                        print(
                            "DEBUG - Transform Chain - Stored GeoDataFrame from _gdf key"
                        )
                    elif isinstance(step_result, dict) and "result_gdf" in step_result:
                        last_geodataframe = step_result["result_gdf"]
                        print(
                            "DEBUG - Transform Chain - Stored GeoDataFrame from result_gdf key"
                        )
                    elif isinstance(current_data, gpd.GeoDataFrame):
                        last_geodataframe = current_data
                        print("DEBUG - Transform Chain - Kept current GeoDataFrame")

                except Exception as e:
                    print(
                        f"DEBUG - Transform Chain - Error in step {step_config.plugin}: {str(e)}"
                    )
                    if hasattr(e, "__traceback__"):
                        import traceback

                        traceback_str = "".join(traceback.format_tb(e.__traceback__))
                        print(f"DEBUG - Transform Chain - Traceback: {traceback_str}")
                    raise DataTransformError(
                        f"Error in step {step_config.plugin}: {str(e)}",
                        details={"step": step_config.plugin, "params": resolved_params},
                    )

                # Store result in context and final result
                context[step_config.output_key] = step_result
                result[step_config.output_key] = step_result

                # Update current data for next step
                current_data = step_result

            return result

        except Exception as e:
            print(e)
            raise DataTransformError(
                "Failed to execute transform chain",
                details={"error": str(e), "config": config},
            )
