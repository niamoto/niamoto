"""Registry storing observed schemas for transform-only file sources."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from niamoto.common.database import Database
from niamoto.common.exceptions import DatabaseQueryError


class TransformSourceMetadata(BaseModel):
    """Metadata stored for a transform-only file source."""

    name: str
    path: str
    grouping: str
    config: Dict[str, Any] = Field(default_factory=dict)


class TransformSourceRegistry:
    """Persist observed schemas for auxiliary transform CSV sources."""

    SOURCES_TABLE = "niamoto_metadata_transform_sources"

    def __init__(self, db: Database) -> None:
        self.db = db
        self._ensure_tables()

    def register_source(
        self,
        *,
        name: str,
        path: str,
        grouping: str,
        config: Dict[str, Any],
    ) -> None:
        """Upsert metadata for a transform source."""

        payload = json.dumps(config, ensure_ascii=False)
        sql = f"""
            INSERT OR REPLACE INTO {self.SOURCES_TABLE} (name, path, grouping, config)
            VALUES (:name, :path, :grouping, :config)
        """
        self.db.execute_sql(
            sql,
            {
                "name": name,
                "path": path,
                "grouping": grouping,
                "config": payload,
            },
        )

    def get(self, name: str) -> TransformSourceMetadata:
        """Return metadata for one transform source."""

        sql = f"""
            SELECT name, path, grouping, config
            FROM {self.SOURCES_TABLE}
            WHERE name = :name
        """
        row = self.db.execute_sql(sql, {"name": name}, fetch=True)
        if row is None:
            raise DatabaseQueryError(
                query="transform_source_lookup",
                message="Transform source not found",
                details={"name": name},
            )
        return self._row_to_metadata(row)

    def list_sources(self) -> List[TransformSourceMetadata]:
        """Return all registered transform sources."""

        sql = f"SELECT name, path, grouping, config FROM {self.SOURCES_TABLE}"
        try:
            rows = self.db.execute_sql(sql, fetch_all=True)
        except DatabaseQueryError:
            return []
        if not rows:
            return []
        return [self._row_to_metadata(row) for row in rows]

    def _ensure_tables(self) -> None:
        create_sources = f"""
            CREATE TABLE IF NOT EXISTS {self.SOURCES_TABLE} (
                name TEXT PRIMARY KEY,
                path TEXT NOT NULL,
                grouping TEXT NOT NULL,
                config TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        if getattr(self.db, "read_only", False):
            return
        self.db.execute_sql(create_sources)

    def _row_to_metadata(self, row: Any) -> TransformSourceMetadata:
        """Normalize a database row into source metadata."""

        name: Optional[str] = None
        path: Optional[str] = None
        grouping: Optional[str] = None
        payload: Any = None

        if hasattr(row, "_mapping"):
            mapping = row._mapping
            name = mapping.get("name")
            path = mapping.get("path")
            grouping = mapping.get("grouping")
            payload = mapping.get("config")
        elif isinstance(row, Mapping):
            name = row.get("name")
            path = row.get("path")
            grouping = row.get("grouping")
            payload = row.get("config")
        elif isinstance(row, Sequence) and not isinstance(row, (str, bytes, bytearray)):
            if len(row) < 4:
                raise DatabaseQueryError(
                    query="transform_source_lookup",
                    message="Transform source row has unexpected length",
                    details={"row": list(row)},
                )
            name, path, grouping, payload = row[:4]
        else:
            raise DatabaseQueryError(
                query="transform_source_lookup",
                message="Unsupported transform source row format",
                details={"row": str(row)},
            )

        if not isinstance(name, str) or not name:
            raise DatabaseQueryError(
                query="transform_source_lookup",
                message="Invalid transform source name",
                details={"name": name},
            )
        if not isinstance(path, str) or not path:
            raise DatabaseQueryError(
                query="transform_source_lookup",
                message="Invalid transform source path",
                details={"path": path},
            )
        if not isinstance(grouping, str) or not grouping:
            raise DatabaseQueryError(
                query="transform_source_lookup",
                message="Invalid transform source grouping",
                details={"grouping": grouping},
            )

        if isinstance(payload, str):
            try:
                config_dict = json.loads(payload)
            except (json.JSONDecodeError, ValueError) as exc:
                raise DatabaseQueryError(
                    query="transform_source_lookup",
                    message="Invalid JSON in transform source config",
                    details={"config": payload, "error": str(exc)},
                )
        elif isinstance(payload, Mapping):
            config_dict = dict(payload)
        else:
            config_dict = {}

        return TransformSourceMetadata(
            name=name,
            path=path,
            grouping=grouping,
            config=config_dict,
        )
