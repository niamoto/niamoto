from typing import Dict, Any, Literal
from pydantic import field_validator, Field, ConfigDict

import pandas as pd

from niamoto.core.plugins.models import PluginConfig, BasePluginParams
from niamoto.core.plugins.base import LoaderPlugin, PluginType, register
from niamoto.core.imports.registry import EntityRegistry


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

    def __init__(self, db, registry=None):
        """Initialize with database and optional EntityRegistry.

        Args:
            db: Database instance
            registry: EntityRegistry instance (created if not provided)
        """
        super().__init__(db)
        self.registry = registry or EntityRegistry(db)

    def _resolve_table_name(self, logical_name: str) -> str:
        """Resolve logical entity name to physical table name via EntityRegistry.

        Args:
            logical_name: Entity name from config (e.g., "shapes", "occurrences")

        Returns:
            Physical table name (e.g., "entity_shapes", "entity_occurrences")
            Falls back to logical_name if not found in registry (backward compatibility)
        """
        try:
            metadata = self.registry.get(logical_name)
            return metadata.table_name
        except Exception:
            # Fallback: assume it's already a physical table name
            return logical_name

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

        # Resolve entity names to physical table names via EntityRegistry
        reference_table = self._resolve_table_name(config["reference"]["name"])
        main_table = self._resolve_table_name(config["main"])

        # Get shape geometry
        shape_query = f"""
            SELECT {params.geometry_field}
            FROM {reference_table}
            WHERE id = :id
        """
        shape_geom = self.db.execute(shape_query, {"id": group_id}).scalar()

        # Get contained data
        query = f"""
            SELECT m.*
            FROM {main_table} m
            WHERE ST_Contains(
                ST_GeomFromText(:shape_geom),
                m.{params.geometry_field}
            )
        """

        # Use text() wrapped query with engine directly to avoid pandas warning
        from sqlalchemy import text

        return pd.read_sql(
            text(query),
            self.db.engine,
            params={"shape_geom": shape_geom},
        )
