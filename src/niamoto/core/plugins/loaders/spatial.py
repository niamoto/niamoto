from typing import Dict, Any, Literal
from pydantic import field_validator

import pandas as pd

from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import LoaderPlugin, PluginType, register


class SpatialConfig(PluginConfig):
    """Configuration for spatial loader"""

    plugin: Literal["spatial"]
    key: str
    geometry_field: str

    @field_validator("geometry_field")
    @classmethod
    def validate_geometry_field(cls, v: str) -> str:
        """Validate geometry field configuration"""
        if not v:
            raise ValueError("geometry_field is required")
        return v


@register("spatial_containment", PluginType.LOADER)
class SpatialLoader(LoaderPlugin):
    """Loader using spatial queries"""

    config_model = SpatialConfig

    def validate_config(self, config: Dict[str, Any]) -> SpatialConfig:
        """Validate plugin configuration."""
        return self.config_model(**config)

    def load_data(self, group_id: int, config: Dict[str, Any]) -> pd.DataFrame:
        validated_config = self.validate_config(config)

        # Get shape geometry
        shape_query = f"""
            SELECT {validated_config.geometry_field}
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
                m.{validated_config.geometry_field}
            )
        """

        return pd.read_sql(
            query, self.db.engine, params={"id": group_id, "shape_geom": shape_geom}
        )
