"""Entity Registry storing metadata about imported entities."""

from __future__ import annotations

import json
from enum import Enum
from typing import Any, Dict, List, Optional
from collections.abc import Mapping, Sequence

from pydantic import BaseModel, Field

from niamoto.common.database import Database
from niamoto.common.exceptions import DatabaseQueryError


class EntityKind(str, Enum):
    """Kinds of entities managed by the registry."""

    REFERENCE = "reference"
    DATASET = "dataset"


class EntityMetadata(BaseModel):
    """Metadata stored for each registered entity."""

    name: str
    kind: EntityKind
    table_name: str
    config: Dict[str, Any] = Field(default_factory=dict)


class EntityRegistry:
    """Persisted index of entities available in the import pipeline."""

    ENTITIES_TABLE = "niamoto_metadata_entities"

    def __init__(self, db: Database) -> None:
        self.db = db
        self._ensure_tables()

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def register_entity(
        self,
        name: str,
        kind: EntityKind,
        table_name: str,
        config: Dict[str, Any],
    ) -> None:
        """Upsert metadata for an entity."""

        payload = json.dumps(config, ensure_ascii=False)

        sql = f"""
            INSERT OR REPLACE INTO {self.ENTITIES_TABLE} (name, kind, table_name, config)
            VALUES (:name, :kind, :table_name, :config)
        """
        self.db.execute_sql(
            sql,
            {
                "name": name,
                "kind": kind.value,
                "table_name": table_name,
                "config": payload,
            },
        )

    def get(self, name: str) -> EntityMetadata:
        """Return metadata for an entity name."""

        sql = f"""
            SELECT name, kind, table_name, config
            FROM {self.ENTITIES_TABLE}
            WHERE name = :name
        """
        row = self.db.execute_sql(sql, {"name": name}, fetch=True)

        if row is None:
            raise DatabaseQueryError(
                query="registry_lookup",
                message="Entity not found",
                details={"name": name},
            )

        return self._row_to_metadata(row)

    def list_entities(self, kind: Optional[EntityKind] = None) -> List[EntityMetadata]:
        """Return all registered entities optionally filtered by kind."""

        sql = f"SELECT name, kind, table_name, config FROM {self.ENTITIES_TABLE}"
        params: Dict[str, Any] = {}
        if kind is not None:
            sql += " WHERE kind = :kind"
            params["kind"] = kind.value

        try:
            rows = self.db.execute_sql(sql, params, fetch_all=True)
        except DatabaseQueryError:
            return []
        if not rows:
            return []

        return [self._row_to_metadata(row) for row in rows]

    def remove(self, name: str) -> None:
        """Delete an entity."""

        self.db.execute_sql(
            f"DELETE FROM {self.ENTITIES_TABLE} WHERE name = :name",
            {"name": name},
        )

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    def _ensure_tables(self) -> None:
        create_entities = f"""
            CREATE TABLE IF NOT EXISTS {self.ENTITIES_TABLE} (
                name TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                table_name TEXT NOT NULL,
                config TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        if getattr(self.db, "read_only", False):
            return
        self.db.execute_sql(create_entities)

    def _row_to_metadata(self, row: Any) -> EntityMetadata:
        """Normalize database row structures into entity metadata."""

        if row is None:
            raise DatabaseQueryError(
                query="registry_lookup",
                message="Entity metadata row is missing",
                details={"row": row},
            )

        name: Optional[str] = None
        kind_value: Optional[str] = None
        table_name: Optional[str] = None
        payload: Any = None

        # SQLAlchemy Row offers _mapping with dict-like access
        if hasattr(row, "_mapping"):
            mapping = row._mapping
            name = mapping.get("name")
            kind_value = mapping.get("kind")
            table_name = mapping.get("table_name")
            payload = mapping.get("config")

        # Plain dict-like structures
        elif isinstance(row, Mapping):
            name = row.get("name")
            kind_value = row.get("kind")
            table_name = row.get("table_name")
            payload = row.get("config")

        # Tuple/list shaped rows (sqlite)
        elif isinstance(row, Sequence) and not isinstance(row, (str, bytes, bytearray)):
            if len(row) < 4:
                raise DatabaseQueryError(
                    query="registry_lookup",
                    message="Entity metadata row has unexpected length",
                    details={"row": list(row)},
                )
            name, kind_value, table_name, payload = row[:4]

        # Anything else is unsupported
        else:
            raise DatabaseQueryError(
                query="registry_lookup",
                message="Unsupported entity metadata row format",
                details={"row": str(row)},
            )

        if not isinstance(name, str) or not name:
            raise DatabaseQueryError(
                query="registry_lookup",
                message="Incomplete entity metadata row",
                details={
                    "name": name,
                    "kind": kind_value,
                    "table": table_name,
                },
            )

        if not isinstance(kind_value, str) or not kind_value:
            raise DatabaseQueryError(
                query="registry_lookup",
                message="Invalid entity kind value",
                details={"kind": kind_value},
            )

        if not isinstance(table_name, str) or not table_name:
            raise DatabaseQueryError(
                query="registry_lookup",
                message="Invalid table name value",
                details={"table": table_name},
            )

        if isinstance(payload, str):
            try:
                config_dict = json.loads(payload)
            except (json.JSONDecodeError, ValueError) as e:
                raise DatabaseQueryError(
                    query="registry_lookup",
                    message="Invalid JSON in config field",
                    details={"config": payload, "error": str(e)},
                )
        elif isinstance(payload, Mapping):
            config_dict = dict(payload)
        else:
            config_dict = {}

        try:
            kind_enum = EntityKind(kind_value)
        except ValueError as e:
            raise DatabaseQueryError(
                query="registry_lookup",
                message="Invalid entity kind value",
                details={"kind": kind_value, "error": str(e)},
            )

        return EntityMetadata(
            name=name,
            kind=kind_enum,
            table_name=table_name,
            config=config_dict,
        )
