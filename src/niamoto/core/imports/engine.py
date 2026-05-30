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
import uuid

import pandas as pd
import geopandas as gpd
from sqlalchemy.sql import text

from niamoto.common.database import Database
from niamoto.common.exceptions import DatabaseQueryError
from niamoto.common.table_resolver import quote_identifier
from niamoto.core.imports.registry import EntityRegistry, EntityKind
from niamoto.core.imports.config_models import (
    ExtractionConfig,
    HierarchyConfig,
    MultiFeatureSource,
)
from niamoto.core.imports.data_analyzer import DataAnalyzer
from niamoto.core.imports.transformer_suggester import TransformerSuggester

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
        self.data_analyzer = DataAnalyzer()
        self.transformer_suggester = TransformerSuggester()

    def _write_dataframe_to_table(self, df: pd.DataFrame, table_name: str) -> None:
        """Persist a DataFrame without triggering DuckDB reflection on replace.

        Recent SQLAlchemy + duckdb-engine combinations can fail when pandas uses
        ``if_exists="replace"`` because pandas reflects the table through
        PostgreSQL-style system catalogs. For DuckDB we avoid that code path by
        writing a staging table, then swapping it into place after the write
        succeeds.
        """
        staging_table = self._staging_table_name(table_name)
        backup_table: Optional[str] = None
        installed = False
        try:
            self._write_dataframe_to_staging(df, staging_table)
            backup_table = self._replace_table_with_staging(staging_table, table_name)
            installed = True
        except Exception:
            if installed:
                self._restore_table_backup(backup_table, table_name)
            else:
                self._drop_table_if_exists(staging_table)
            raise
        else:
            self._drop_table_if_exists(backup_table)

    def _write_dataframe_to_staging(self, df: pd.DataFrame, staging_table: str) -> None:
        """Write a DataFrame into a caller-owned staging table."""
        df.to_sql(staging_table, self.db.engine, if_exists="fail", index=False)

    def _staging_table_name(self, table_name: str) -> str:
        """Return a temporary table name used for atomic-ish replacements."""
        safe_name = "".join(
            char if char.isalnum() or char == "_" else "_" for char in table_name
        )
        return f"__niamoto_tmp_{safe_name[:24]}_{uuid.uuid4().hex[:12]}"

    def _drop_table_if_exists(self, table_name: Optional[str]) -> None:
        if not table_name:
            return
        quoted_table = quote_identifier(self.db, table_name)
        try:
            self.db.execute_sql(f"DROP TABLE IF EXISTS {quoted_table}")
            self.db.invalidate_table_names_cache()
        except Exception:
            logger.warning("Failed to drop staging table %s", table_name, exc_info=True)

    def _replace_table_with_staging(
        self, staging_table: str, table_name: str
    ) -> Optional[str]:
        """Swap a fully written staging table into the target table name.

        Existing targets are renamed to a temporary backup first. Callers keep
        that backup until the surrounding import has fully succeeded, so later
        registry/count failures can restore the previous table.
        """
        self.db.invalidate_table_names_cache()
        backup_table = (
            self._staging_table_name(f"{table_name}_backup")
            if self.db.has_table(table_name)
            else None
        )
        quoted_staging = quote_identifier(self.db, staging_table)
        quoted_target = quote_identifier(self.db, table_name)
        quoted_backup = (
            quote_identifier(self.db, backup_table)
            if backup_table is not None
            else None
        )
        try:
            with self.db.engine.begin() as connection:
                if quoted_backup is not None:
                    connection.execute(
                        text(f"ALTER TABLE {quoted_target} RENAME TO {quoted_backup}")
                    )
                connection.execute(
                    text(f"ALTER TABLE {quoted_staging} RENAME TO {quoted_target}")
                )
        except Exception:
            self.db.invalidate_table_names_cache()
            if backup_table and self.db.has_table(backup_table):
                self._restore_table_backup(backup_table, table_name)
            raise
        self.db.invalidate_table_names_cache()
        return backup_table

    def _restore_table_backup(
        self, backup_table: Optional[str], table_name: str
    ) -> None:
        """Restore the previous target table after a failed staged replacement."""
        quoted_target = quote_identifier(self.db, table_name)
        quoted_backup = (
            quote_identifier(self.db, backup_table)
            if backup_table is not None
            else None
        )
        with self.db.engine.begin() as connection:
            connection.execute(text(f"DROP TABLE IF EXISTS {quoted_target}"))
            if quoted_backup is not None:
                connection.execute(
                    text(f"ALTER TABLE {quoted_backup} RENAME TO {quoted_target}")
                )
        self.db.invalidate_table_names_cache()

    def _count_table_rows(self, table_name: str) -> int:
        """Return the row count for a quoted table name."""
        quoted_table = quote_identifier(self.db, table_name)
        count_df = pd.read_sql(
            f"SELECT COUNT(*) as count FROM {quoted_table}", self.db.engine
        )
        return int(count_df.iloc[0]["count"])

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

        df = self._read_csv(csv_path)
        source_columns = set(df.columns)
        if df.empty:
            # Ensure we still create a table with the expected columns
            df = self._ensure_dataframe_structure(df, id_field=id_field)

        primary_key = id_field or self._ensure_identifier(df)
        if "extra_data" not in df.columns:
            df["extra_data"] = None

        staging_table = self._staging_table_name(table_name)
        backup_table: Optional[str] = None
        installed = False
        try:
            # Use DuckDB-native ingestion when the source identifier already matches
            # the metadata we will register. If we need to generate default IDs, write
            # the normalized DataFrame so the physical table and registry stay aligned.
            if self.db.is_duckdb:
                needs_generated_default_id = (
                    not id_field
                    and primary_key == "id"
                    and ("id" not in source_columns or df["id"].isnull().any())
                )
                if needs_generated_default_id:
                    self._write_dataframe_to_staging(df, staging_table)
                else:
                    quoted_staging_table = quote_identifier(self.db, staging_table)

                    # Ensure absolute path for DuckDB
                    absolute_csv_path = csv_path.absolute()
                    escaped_path = str(absolute_csv_path).replace("'", "''")

                    # Scan the full CSV for dialect and type detection. DuckDB's
                    # default sample can miss late quoted values and mixed IDs.
                    create_sql = f"""
                        CREATE TABLE {quoted_staging_table} AS
                        SELECT * FROM read_csv_auto(
                            '{escaped_path}',
                            header=true,
                            auto_detect=true,
                            sample_size=-1
                        )
                    """
                    self.db.execute_sql(create_sql)

                    # Add extra_data column for metadata storage
                    alter_sql = (
                        f"ALTER TABLE {quoted_staging_table} "
                        "ADD COLUMN extra_data JSON DEFAULT NULL"
                    )
                    self.db.execute_sql(alter_sql)
            else:
                # Fallback to pandas for SQLite
                self._write_dataframe_to_staging(df, staging_table)

            # Convert WKT geometry columns on the staged table. If any later step
            # fails, the existing production table has not been touched yet.
            self._convert_wkt_columns_to_geometry(staging_table, df.columns.tolist())

            # Analyze dataset for transformer suggestions
            semantic_profile = None
            try:
                semantic_profile = self._analyze_for_transformers(
                    df=df,
                    csv_path=csv_path,
                    entity_name=entity_name,
                )
            except Exception as e:
                logger.warning(
                    f"Failed to generate transformer suggestions for '{entity_name}': {e}",
                    exc_info=True,
                )

            metadata = self._build_metadata(
                df,
                primary_key=primary_key,
                source_path=str(csv_path),
                extra_config=extra_config,
            )

            # Add semantic profile to metadata
            if semantic_profile:
                metadata["semantic_profile"] = semantic_profile

            row_count = self._count_table_rows(staging_table)
            backup_table = self._replace_table_with_staging(staging_table, table_name)
            installed = True
            self.registry.register_entity(
                name=entity_name,
                kind=kind,
                table_name=table_name,
                config=metadata,
            )
        except Exception:
            if installed:
                self._restore_table_backup(backup_table, table_name)
            else:
                self._drop_table_if_exists(staging_table)
            raise
        else:
            self._drop_table_if_exists(backup_table)

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

        # Add extra_data column if not present
        if "extra_data" not in hierarchy_df.columns:
            hierarchy_df["extra_data"] = None

        # Create from DataFrame (works with both SQLite and DuckDB)
        self._write_dataframe_to_table(hierarchy_df, table_name)

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
            gdf = gpd.read_file(source_path, engine="pyogrio")

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
        self._write_dataframe_to_table(df, table_name)

        # Convert WKT location to native GEOMETRY for spatial queries
        self._add_native_geometry_column(table_name, "location", "geometry")

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
    # WKT column patterns to detect and convert to native GEOMETRY
    WKT_COLUMN_PATTERNS = ["geo_pt", "geo", "wkt", "geometry", "geom", "the_geom"]

    def _convert_wkt_columns_to_geometry(self, table_name: str, columns: list) -> None:
        """Detect WKT columns and convert them to native GEOMETRY.

        Args:
            table_name: Name of the table
            columns: List of column names to check
        """
        for col in columns:
            col_lower = col.lower()
            # Check if column name matches WKT patterns
            for pattern in self.WKT_COLUMN_PATTERNS:
                if col_lower == pattern or col_lower.startswith(f"{pattern}_"):
                    # Create geometry column name (geo_pt -> geo_pt_geom)
                    geom_col = f"{col}_geom"
                    self._add_native_geometry_column(table_name, col, geom_col)
                    break

    def _add_native_geometry_column(
        self, table_name: str, wkt_column: str, geometry_column: str
    ) -> None:
        """Add a native GEOMETRY column converted from WKT text.

        This enables fast spatial queries with proper index support.

        Args:
            table_name: Name of the table
            wkt_column: Name of the column containing WKT text
            geometry_column: Name of the new GEOMETRY column to create
        """
        try:
            quoted_table = quote_identifier(self.db, table_name)
            quoted_wkt = quote_identifier(self.db, wkt_column)
            quoted_geometry = quote_identifier(self.db, geometry_column)
            with self.db.engine.connect() as conn:
                # Add GEOMETRY column
                conn.execute(
                    text(
                        f"ALTER TABLE {quoted_table} ADD COLUMN {quoted_geometry} GEOMETRY"
                    )
                )

                # Populate from WKT (only for non-null values)
                conn.execute(
                    text(
                        f"""
                        UPDATE {quoted_table}
                        SET {quoted_geometry} = ST_GeomFromText({quoted_wkt})
                        WHERE {quoted_wkt} IS NOT NULL
                    """
                    )
                )

                conn.commit()
                logger.info(
                    f"Added native GEOMETRY column '{geometry_column}' to {table_name}"
                )
        except Exception as e:
            # Don't fail the import if geometry conversion fails
            logger.warning(f"Could not add native geometry column to {table_name}: {e}")

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
        """Read CSV/TSV using pandas with fallback separator and encoding handling.

        Tries UTF-8 first, falls back to latin-1 on UnicodeDecodeError.
        Tries comma separator first, falls back to semicolon with decimal comma.

        Args:
            path: Path to CSV/TSV file
            nrows: Optional limit on number of rows to read (for metadata sampling)
        """
        import csv as csv_module

        # Sniff delimiter from first 8KB
        sep = ","
        try:
            with open(path, "r", encoding="utf-8") as f:
                sample = f.read(8192)
                dialect = csv_module.Sniffer().sniff(sample, delimiters=",\t;|")
                sep = dialect.delimiter
        except Exception:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    first_line = f.readline()
                    if "\t" in first_line:
                        sep = "\t"
            except Exception:
                pass

        try:
            return pd.read_csv(
                path, sep=sep, encoding="utf-8", nrows=nrows, low_memory=False
            )
        except UnicodeDecodeError:
            # Re-detect delimiter with latin-1 encoding (UTF-8 sniff may have failed)
            try:
                with open(path, "r", encoding="latin-1") as f:
                    sample = f.read(8192)
                    dialect = csv_module.Sniffer().sniff(sample, delimiters=",\t;|")
                    sep = dialect.delimiter
            except Exception:
                pass
            return pd.read_csv(
                path, sep=sep, encoding="latin-1", nrows=nrows, low_memory=False
            )
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

    def _analyze_for_transformers(
        self,
        df: pd.DataFrame,
        csv_path: Path,
        entity_name: str,
    ) -> Dict[str, object]:
        """
        Analyze dataset and generate transformer suggestions.

        Args:
            df: DataFrame with the data
            csv_path: Path to the CSV file (for profiler)
            entity_name: Name of the entity

        Returns:
            Dictionary with semantic profile including transformer suggestions
        """
        from niamoto.core.imports.profiler import DataProfiler

        logger.info(f"Analyzing dataset '{entity_name}' for transformer suggestions...")

        # 1. Profile with DataProfiler — reuse already-loaded DataFrame
        # Pass total_count=len(df) since the full DataFrame is already in memory
        profiler = DataProfiler()
        dataset_profile = profiler.profile_dataframe(df, csv_path, total_count=len(df))

        # 2. Enrich each column with DataAnalyzer
        enriched_profiles = []
        column_diagnostics = {}
        for col_profile in dataset_profile.columns:
            if col_profile.name in df.columns:
                try:
                    enriched = self.data_analyzer.enrich_profile(
                        col_profile, df[col_profile.name]
                    )
                    enriched_profiles.append(enriched)
                    column_diagnostics[col_profile.name] = {
                        "status": "analyzed",
                    }
                except Exception as e:
                    logger.warning(
                        f"Failed to enrich profile for column '{col_profile.name}': {e}"
                    )
                    column_diagnostics[col_profile.name] = {
                        "status": "error",
                        "reason": f"enrichment_failed: {e}",
                    }
                    continue

        # 3. Generate transformer suggestions
        suggestions = self.transformer_suggester.suggest_for_dataset(
            enriched_profiles, entity_name
        )

        # Update diagnostics with suggestion counts
        for col_name in column_diagnostics:
            if column_diagnostics[col_name]["status"] == "analyzed":
                suggestion_count = len(suggestions.get(col_name, []))
                column_diagnostics[col_name]["suggestions"] = suggestion_count

        # Determine profiling status
        error_count = sum(
            1 for d in column_diagnostics.values() if d["status"] == "error"
        )
        total_cols = len(column_diagnostics)
        if error_count == 0:
            profiling_status = "complete"
        elif error_count < total_cols:
            profiling_status = "partial"
        else:
            profiling_status = "failed"

        # 3b. Affordance-based suggestions (complements category-based)
        from niamoto.core.imports.ml.affordance_matcher import AffordanceMatcher

        affordance_matcher = AffordanceMatcher()
        affordance_suggestions = {}
        for col_profile in dataset_profile.columns:
            if col_profile.semantic_profile:
                aff_suggs = affordance_matcher.suggest_for_profile(
                    col_profile.semantic_profile
                )
                if aff_suggs:
                    affordance_suggestions[col_profile.name] = [
                        {
                            "transformer": s.transformer,
                            "widget": s.widget,
                            "score": s.score,
                            "reason": s.reason,
                        }
                        for s in aff_suggs
                    ]

        # 3c. Dataset-level pattern detection
        from niamoto.core.imports.ml.dataset_patterns import detect_dataset_patterns

        all_profiles = [
            cp.semantic_profile for cp in dataset_profile.columns if cp.semantic_profile
        ]
        dataset_patterns = detect_dataset_patterns(all_profiles)

        # 4. Build semantic profile structure
        semantic_profile = {
            "schema_version": 3,
            "profiling_status": profiling_status,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "column_diagnostics": column_diagnostics,
            "columns": [
                {
                    "name": ep.name,
                    "dtype": ep.dtype,
                    "semantic_type": ep.semantic_type,
                    "unique_ratio": ep.unique_ratio,
                    "confidence": ep.confidence,
                    "data_category": ep.data_category.value,
                    "field_purpose": ep.field_purpose.value,
                    "cardinality": ep.cardinality,
                    "null_ratio": ep.null_ratio,
                    "suggested_bins": ep.suggested_bins,
                    "suggested_labels": ep.suggested_labels,
                    "value_range": ep.value_range,
                    **(
                        {"semantic_profile": cp.semantic_profile.to_dict()}
                        if cp.semantic_profile
                        else {}
                    ),
                }
                for ep, cp in zip(
                    enriched_profiles,
                    [
                        c
                        for c in dataset_profile.columns
                        if c.name in {e.name for e in enriched_profiles}
                    ],
                )
            ],
            "transformer_suggestions": {
                col_name: [
                    {
                        "transformer": s.transformer_name,
                        "confidence": s.confidence,
                        "reason": s.reason,
                        "config": s.pre_filled_config,
                    }
                    for s in suggestions_list
                ]
                for col_name, suggestions_list in suggestions.items()
            },
            "affordance_suggestions": affordance_suggestions,
            "dataset_patterns": [
                {
                    "name": p.name,
                    "description": p.description,
                    "confidence": p.confidence,
                    "suggestions": p.suggestions,
                }
                for p in dataset_patterns
            ],
        }

        logger.info(
            f"Generated suggestions for {len(suggestions)} columns "
            f"({sum(len(s) for s in suggestions.values())} total suggestions)"
        )

        return semantic_profile

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
