"""Lightweight generic import engine built on top of pandas + EntityRegistry.

This module offers a pragmatic bridge away from the legacy importer classes
by providing a DataFrame-centric ingestion path that writes straight into the
analytics store (DuckDB/SQLite via SQLAlchemy) and keeps the entity registry in
sync. It is intentionally simple: CSV/TSV inputs are supported today, while
additional connectors can be layered on later.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import logging

import pandas as pd
import geopandas as gpd
from sqlalchemy.sql import quoted_name

from niamoto.common.database import Database
from niamoto.common.exceptions import DatabaseQueryError
from niamoto.core.imports.registry import EntityRegistry, EntityKind
from niamoto.core.imports.config_models import (
    ExtractionConfig,
    HierarchyConfig,
    MultiFeatureSource,
)

logger = logging.getLogger(__name__)


class ImportResult(dict):
    """Simple result container returned by GenericImporter."""

    @property
    def rows(self) -> int:
        return self.get("rows", 0)

    @property
    def table(self) -> str:
        return self.get("table", "")


class GenericImporter:
    """Small helper that loads tabular data and registers entities."""

    def __init__(self, db: Database, registry: EntityRegistry) -> None:
        self.db = db
        self.registry = registry

    def import_from_csv(
        self,
        *,
        entity_name: str,
        table_name: str,
        source_path: str,
        kind: EntityKind,
        id_field: Optional[str] = None,
        extra_config: Optional[Dict[str, object]] = None,
    ) -> ImportResult:
        """Load a CSV/TSV file into the analytics database and register metadata."""

        csv_path = Path(source_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"Import source not found: {csv_path}")

        # Use DuckDB-native ingestion if available for better performance
        if self.db.is_duckdb:
            # DuckDB native CSV ingestion using read_csv_auto and CTAS
            primary_key = id_field or "id"
            quoted_table = str(quoted_name(table_name, quote=True))

            # Drop existing table if needed
            self.db.execute_sql(f"DROP TABLE IF EXISTS {quoted_table}")

            # Ensure absolute path for DuckDB
            absolute_csv_path = csv_path.absolute()
            escaped_path = str(absolute_csv_path).replace("'", "''")

            # Create table using DuckDB's read_csv_auto (auto-detects schema)
            create_sql = f"""
                CREATE TABLE {quoted_table} AS
                SELECT * FROM read_csv_auto('{escaped_path}', header=true, auto_detect=true)
            """
            self.db.execute_sql(create_sql)

            # Add extra_data column for metadata storage
            alter_sql = (
                f"ALTER TABLE {quoted_table} ADD COLUMN extra_data JSON DEFAULT NULL"
            )
            self.db.execute_sql(alter_sql)

            # Read minimal dataframe just for metadata extraction
            df = self._read_csv(csv_path, nrows=100)
            # Add extra_data to df for metadata purposes (column exists in DB now)
            df["extra_data"] = None
        else:
            # Fallback to pandas for SQLite
            df = self._read_csv(csv_path)
            if df.empty:
                # Ensure we still create a table with the expected columns
                df = self._ensure_dataframe_structure(df, id_field=id_field)

            primary_key = id_field or self._ensure_identifier(df)

            # Add extra_data column if not present (for metadata storage)
            if "extra_data" not in df.columns:
                df["extra_data"] = None

            df.to_sql(table_name, self.db.engine, if_exists="replace", index=False)

        metadata = self._build_metadata(
            df,
            primary_key=primary_key,
            source_path=str(csv_path),
            extra_config=extra_config,
        )
        self.registry.register_entity(
            name=entity_name,
            kind=kind,
            table_name=table_name,
            config=metadata,
        )

        # Get actual row count from the table (not from the sample df for DuckDB)
        if self.db.is_duckdb:
            import pandas as pd

            count_df = pd.read_sql(
                f"SELECT COUNT(*) as count FROM {quoted_table}", self.db.engine
            )
            row_count = int(count_df.iloc[0]["count"])
        else:
            row_count = len(df)

        return ImportResult(rows=row_count, table=table_name)

    def import_derived_reference(
        self,
        *,
        entity_name: str,
        table_name: str,
        source_table: str,
        extraction_config: ExtractionConfig,
        hierarchy_config: Optional[HierarchyConfig],
        kind: EntityKind,
    ) -> ImportResult:
        """Import a reference entity derived from a source dataset.

        Args:
            entity_name: Name of the entity to create
            table_name: Target table name
            source_table: Source dataset table name
            extraction_config: Extraction configuration
            hierarchy_config: Hierarchy configuration (optional)
            kind: Entity kind

        Returns:
            ImportResult with rows count and table name

        Note:
            This method works with both SQLite and DuckDB backends using standard SQL CTEs.
        """
        from niamoto.core.imports.hierarchy_builder import HierarchyBuilder

        # 1. Build hierarchy from source using SQL CTEs
        builder = HierarchyBuilder(self.db)
        hierarchy_df = builder.build_from_dataset(
            source_table, extraction_config, entity_name
        )
        source_entity_name = self._resolve_entity_name(source_table)

        # 1b. Add nested sets (lft/rght) for efficient hierarchical queries
        if len(hierarchy_df) > 0:
            hierarchy_df = builder.add_nested_sets(hierarchy_df)

        if len(hierarchy_df) == 0:
            # No data extracted, register empty entity
            external_id_field = (
                f"{entity_name}_id" if extraction_config.id_column else None
            )
            self.registry.register_entity(
                name=entity_name,
                kind=kind,
                table_name=table_name,
                config={
                    "derived": {
                        "source_entity": source_entity_name,
                        "extraction_levels": [
                            lv.name for lv in extraction_config.levels
                        ],
                        "id_strategy": extraction_config.id_strategy,
                        "incomplete_rows": extraction_config.incomplete_rows,
                        "external_id_field": external_id_field,
                        "external_name_field": "full_name"
                        if extraction_config.name_column
                        else None,
                        "extracted_at": datetime.now(timezone.utc).isoformat(),
                    },
                    "schema": {"id_field": "id", "fields": []},
                },
            )
            return ImportResult(rows=0, table=table_name)

        # 2. Write to database (SQLAlchemy via pandas.to_sql)
        # Drop existing
        self.db.execute_sql(f"DROP TABLE IF EXISTS {table_name}")

        # Add extra_data column if not present
        if "extra_data" not in hierarchy_df.columns:
            hierarchy_df["extra_data"] = None

        # Create from DataFrame (works with both SQLite and DuckDB)
        hierarchy_df.to_sql(
            table_name, self.db.engine, if_exists="replace", index=False
        )

        # 3. Register in registry with derived metadata
        external_id_field = f"{entity_name}_id" if extraction_config.id_column else None
        derived_metadata = {
            "source_entity": source_entity_name,
            "extraction_levels": [lv.name for lv in extraction_config.levels],
            "id_strategy": extraction_config.id_strategy,
            "incomplete_rows": extraction_config.incomplete_rows,
            "external_id_field": external_id_field,
            "external_name_field": "full_name"
            if extraction_config.name_column
            else None,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
        }

        metadata = self._build_metadata(
            hierarchy_df,
            primary_key="id",
            source_path=f"derived_from:{source_table}",
            extra_config={"derived": derived_metadata},
        )

        self.registry.register_entity(
            name=entity_name,
            kind=kind,
            table_name=table_name,
            config=metadata,
        )

        return ImportResult(rows=len(hierarchy_df), table=table_name)

    def import_multi_feature(
        self,
        *,
        entity_name: str,
        table_name: str,
        sources: List[MultiFeatureSource],
        kind: EntityKind,
        id_field: Optional[str] = None,
    ) -> ImportResult:
        """Import multiple spatial files as a single entity table.

        Each source file's features become rows with an entity_type column.

        Args:
            entity_name: Entity name for registry
            table_name: Target table name
            sources: List of spatial file sources
            kind: Entity kind
            id_field: Primary key field name (default: 'id')

        Returns:
            ImportResult with row count
        """
        logger.info(
            f"Importing multi-feature entity '{entity_name}' from {len(sources)} sources"
        )

        # Collect all features from all sources with 2-level hierarchy
        # Level 0: Type rows (one per source)
        # Level 1: Shape rows (features from each source)
        all_features = []
        feature_id = 1

        for source in sources:
            source_path = Path(source.path)
            if not source_path.exists():
                logger.warning(f"Skipping missing source: {source_path}")
                continue

            # Read spatial file (supports .gpkg, .shp, .geojson)
            logger.info(f"Reading {source.name} from {source_path}")
            gdf = gpd.read_file(source_path)

            # Ensure geometries are in WGS84 so downstream widgets/exports work with map providers
            if getattr(gdf, "crs", None):
                try:
                    if gdf.crs and gdf.crs.to_string().upper() not in {
                        "EPSG:4326",
                        "WGS84",
                        "CRS84",
                    }:
                        gdf = gdf.to_crs("EPSG:4326")
                except Exception as exc:  # pragma: no cover - defensive
                    logger.warning(
                        "Failed to reproject '%s' from %s to EPSG:4326: %s",
                        source.name,
                        gdf.crs,
                        exc,
                    )
            else:
                logger.debug(
                    "Source '%s' has no CRS metadata; assuming coordinates already in EPSG:4326",
                    source.name,
                )

            # 1. Create TYPE row (parent container for this source)
            type_row = {
                id_field or "id": feature_id,
                "name": source.name,
                "location": None,  # Type rows have no geometry
                "entity_type": "type",
                "shape_type": "type",
                "type": source.name,
                "level": 0,
                "parent_id": None,
            }
            type_id = feature_id
            all_features.append(type_row)
            feature_id += 1

            # 2. Create SHAPE rows (children features)
            for idx, row in gdf.iterrows():
                shape_id = f"{source.name.lower().replace(' ', '_')}_{idx + 1}"
                feature = {
                    id_field or "id": feature_id,
                    "shape_id": shape_id,
                    "name": row[source.name_field]
                    if source.name_field in row
                    else f"Feature {feature_id}",
                    "location": row.geometry.wkt
                    if hasattr(row.geometry, "wkt")
                    else None,
                    "entity_type": "shape",
                    "shape_type": "shape",
                    "type": source.name,
                    "level": 1,
                    "parent_id": type_id,
                }
                all_features.append(feature)
                feature_id += 1

        # Create DataFrame
        df = pd.DataFrame(all_features)

        if df.empty:
            logger.warning(f"No features found in {len(sources)} sources")
            return ImportResult(rows=0, table=table_name)

        # Add extra_data column if not present
        if "extra_data" not in df.columns:
            df["extra_data"] = None

        # Add nested sets for hierarchical queries (reuse HierarchyBuilder)
        from niamoto.core.imports.hierarchy_builder import HierarchyBuilder

        builder = HierarchyBuilder(self.db)
        df = builder.add_nested_sets(df)

        # Write to database
        primary_key = id_field or "id"
        df.to_sql(table_name, self.db.engine, if_exists="replace", index=False)

        # Build metadata
        metadata = self._build_metadata(
            df,
            primary_key=primary_key,
            source_path=f"{len(sources)} spatial files",
            extra_config={
                "sources": [{"name": s.name, "path": s.path} for s in sources],
                "imported_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        # Register entity
        self.registry.register_entity(
            name=entity_name,
            kind=kind,
            table_name=table_name,
            config=metadata,
        )

        logger.info(f"Imported {len(df)} features into {table_name}")
        return ImportResult(rows=len(df), table=table_name)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _resolve_entity_name(self, table_name: str) -> str:
        """Return the logical entity name for a physical table name."""

        try:
            metadata = self.registry.get(table_name)
            return metadata.name
        except DatabaseQueryError:
            pass

        try:
            for entity in self.registry.list_entities():
                if entity.table_name == table_name:
                    return entity.name
        except Exception:
            pass

        for prefix in ("dataset_", "entity_"):
            if table_name.startswith(prefix):
                return table_name[len(prefix) :]

        return table_name

    @staticmethod
    def _read_csv(path: Path, nrows: Optional[int] = None) -> pd.DataFrame:
        """Read CSV/TSV using pandas with fallback separator handling.

        Args:
            path: Path to CSV file
            nrows: Optional limit on number of rows to read (for metadata sampling)
        """

        try:
            return pd.read_csv(path, encoding="utf-8", nrows=nrows, low_memory=False)
        except (pd.errors.EmptyDataError, pd.errors.ParserError):
            return pd.read_csv(
                path,
                sep=";",
                decimal=",",
                encoding="utf-8",
                nrows=nrows,
                low_memory=False,
            )

    def _ensure_dataframe_structure(
        self, df: pd.DataFrame, *, id_field: Optional[str]
    ) -> pd.DataFrame:
        if id_field and id_field not in df.columns:
            df[id_field] = []
        if not id_field and "id" not in df.columns:
            df["id"] = []
        return df

    def _ensure_identifier(self, df: pd.DataFrame) -> str:
        if "id" not in df.columns:
            df.insert(0, "id", range(1, len(df) + 1))
        elif df["id"].isnull().any():
            df["id"] = df.index + 1
        return "id"

    def _build_metadata(
        self,
        df: pd.DataFrame,
        *,
        primary_key: str,
        source_path: str,
        extra_config: Optional[Dict[str, object]],
    ) -> Dict[str, object]:
        fields: List[Dict[str, object]] = []
        for column in df.columns:
            fields.append(
                {
                    "name": column,
                    "type": self._dtype_to_string(df[column].dtype),
                }
            )

        metadata: Dict[str, object] = {
            "schema": {
                "id_field": primary_key,
                "fields": fields,
            },
            "source": {
                "type": "csv",
                "path": source_path,
            },
        }

        if extra_config:
            metadata.update(extra_config)

        return metadata

    @staticmethod
    def _dtype_to_string(dtype: pd.api.types.ExtensionDtype) -> str:
        if pd.api.types.is_integer_dtype(dtype):
            return "integer"
        if pd.api.types.is_float_dtype(dtype):
            return "float"
        if pd.api.types.is_bool_dtype(dtype):
            return "boolean"
        if pd.api.types.is_datetime64_any_dtype(dtype):
            return "datetime"
        return "string"
