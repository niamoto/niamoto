from typing import Dict, Any, Literal
from pydantic import field_validator, Field, ConfigDict

import pandas as pd

from niamoto.core.plugins.models import PluginConfig, BasePluginParams
from niamoto.core.plugins.base import LoaderPlugin, PluginType, register


class SpatialParams(BasePluginParams):
    """Parameters for spatial loader"""

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Load data using spatial containment queries",
            "examples": [{"key": "geometry", "geometry_field": "geom"}],
        }
    )

    key: str = Field(
        ...,
        description="Key field for spatial reference",
        json_schema_extra={"ui:widget": "field-select"},
    )
    geometry_field: str = Field(
        ...,
        description="Name of the geometry field",
        json_schema_extra={"ui:widget": "field-select"},
    )

    @field_validator("geometry_field")
    @classmethod
    def validate_geometry_field(cls, v: str) -> str:
        """Validate geometry field configuration"""
        if not v:
            raise ValueError("geometry_field is required")
        return v


class SpatialConfig(PluginConfig):
    """Configuration for spatial loader"""

    plugin: Literal["spatial_containment"] = "spatial_containment"
    params: SpatialParams


@register("spatial_containment", PluginType.LOADER)
class SpatialLoader(LoaderPlugin):
    """Loader using spatial queries"""

    config_model = SpatialConfig

    def validate_config(self, config: Dict[str, Any]) -> SpatialConfig:
        """Validate plugin configuration."""
        # Extract params if they exist in the config
        if "params" not in config:
            # For backward compatibility, build params from top-level fields
            params = {k: v for k, v in config.items() if k != "plugin"}
            config = {"plugin": "spatial_containment", "params": params}
        return self.config_model(**config)

    def load_data(self, group_id: int, config: Dict[str, Any]) -> pd.DataFrame:
        validated_config = self.validate_config(config)
        params = validated_config.params

        # Get shape geometry
        shape_query = f"""
            SELECT {params.geometry_field}
            FROM {config["reference"]["name"]}
            WHERE id = :id
        """
        shape_geom = self.db.execute(shape_query, {"id": group_id}).scalar()

        # Get contained data
        query = f"""
            SELECT m.*
            FROM {config["main"]} m
            WHERE ST_Contains(
                ST_GeomFromText(:shape_geom),
                m.{params.geometry_field}
            )
        """

        with self.db.engine.connect() as conn:
            return pd.read_sql(
                query, conn, params={"id": group_id, "shape_geom": shape_geom}
            )
