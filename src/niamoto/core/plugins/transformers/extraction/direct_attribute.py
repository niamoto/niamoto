"""
Plugin for getting a direct attribute from a source.
"""

from typing import Dict, Any
from pydantic import Field, field_validator
import os
import pandas as pd
import geopandas as gpd

from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
from niamoto.common.exceptions import DatabaseError
from niamoto.common.config import Config


class DirectAttributeConfig(PluginConfig):
    """Configuration for direct attribute plugin"""

    plugin: str = "direct_attribute"
    params: Dict[str, Any] = Field(default_factory=lambda: {"source": "", "field": ""})

    @field_validator("params")
    @classmethod
    def validate_params(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate params configuration."""
        if not isinstance(v, dict):
            raise ValueError("params must be a dictionary")

        required_fields = ["source", "field"]
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Missing required field: {field}")

        if not isinstance(v["source"], str):
            raise ValueError("source must be a string")

        if not isinstance(v["field"], str):
            raise ValueError("field must be a string")

        return v


@register("direct_attribute", PluginType.TRANSFORMER)
class DirectAttribute(TransformerPlugin):
    """Plugin for getting a direct attribute"""

    config_model = DirectAttributeConfig

    def __init__(self, db):
        super().__init__(db)
        self.config = Config()
        self.imports_config = self.config.get_imports_config

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration."""
        try:
            return self.config_model(**config).dict()
        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}")

    def _get_field_from_table(self, source: str, field: str, id_value: int) -> Any:
        """Get a field value from any table."""
        try:
            query = f"""
                SELECT {field} FROM {source} WHERE id = {id_value}
            """
            result = self.db.execute_select(query).fetchone()
            # Return raw value without string conversion to preserve format
            return result[0] if result and result[0] is not None else None
        except Exception as e:
            raise DatabaseError(f"Error getting field {field} from {source}") from e

    def _get_field_value(self, source: str, field: str, id_value: int) -> Any:
        """Get a field value from a source (table or import)."""
        try:
            # D'abord vérifier si la source est dans import.yml
            if source in self.imports_config:
                import_config = self.imports_config[source]

                # Construire le chemin complet du fichier
                file_path = os.path.join(
                    os.path.dirname(self.config.config_dir), import_config["path"]
                )

                # Charger les données selon le type
                if import_config["type"] == "csv":
                    df = pd.read_csv(file_path)
                elif import_config["type"] == "vector":
                    df = gpd.read_file(file_path)
                else:
                    raise ValueError(
                        f"Unsupported import type: {import_config['type']}"
                    )

                # Récupérer la valeur en utilisant l'identifiant spécifié
                identifier = import_config["identifier"]
                row = df[df[identifier] == id_value]
                if not row.empty:
                    # Return the raw value instead of converting to string
                    return row[field].iloc[0]
                else:
                    return None

            return self._get_field_from_table(source, field, id_value)

        except Exception as e:
            raise ValueError(f"Error getting field {field} from {source}") from e

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data according to configuration."""
        try:
            # Préserver group_id avant validation
            group_id = config.get("group_id")
            validated_config = self.validate_config(config)

            if group_id is None:
                return {"value": None}

            # Get field value
            source = validated_config["params"]["source"]
            field = validated_config["params"]["field"]
            value = self._get_field_value(source, field, group_id)

            # Handle numeric values while preserving format
            original_format = value
            max_value = validated_config["params"].get("max_value")

            if value is not None:
                try:
                    # Check if we need to apply max value restriction
                    float_value = float(value)
                    if max_value is not None and float_value > float(max_value):
                        value = float(max_value)
                    else:
                        # Preserve original format by converting back to string
                        # only if we didn't apply max_value
                        value = original_format
                except ValueError:
                    # If value can't be converted to float, keep it as is
                    pass

                # Ensure consistent string representation
                if isinstance(value, (float, int)):
                    # Convert to string while preserving format
                    if isinstance(original_format, str) and "." in original_format:
                        # Try to maintain decimal precision from original
                        decimal_places = len(original_format.split(".")[-1])
                        value = f"{value:.{decimal_places}f}"
                    else:
                        # Convert to string while removing .0 for integers
                        value = (
                            str(value).rstrip("0").rstrip(".")
                            if "." in str(value)
                            else str(value)
                        )

            return {
                "value": value,
                "units": validated_config["params"].get("units", ""),
            }

        except Exception as e:
            raise ValueError(f"Error transforming data: {str(e)}")
