"""Generic import service using entity registry and typed configurations."""

from __future__ import annotations

from pathlib import Path
import logging

from niamoto.common.database import Database
from niamoto.common.utils import error_handler
from niamoto.common.exceptions import (
    FileReadError,
    DataImportError,
    ValidationError,
    DatabaseQueryError,
)
from niamoto.core.imports.engine import GenericImporter
from niamoto.core.imports.registry import EntityRegistry, EntityKind
from niamoto.core.imports.config_models import (
    GenericImportConfig,
    ReferenceEntityConfig,
    DatasetEntityConfig,
    ConnectorType,
)

logger = logging.getLogger(__name__)


class ImporterService:
    """Service for importing entities using the generic import engine and registry."""

    def __init__(self, db_path: str) -> None:
        """Initialize the import service.

        Args:
            db_path: Path to the database file
        """
        self.db = Database(db_path)
        self.registry = EntityRegistry(self.db)
        self.engine = GenericImporter(self.db, self.registry)

    @error_handler(log=True, raise_error=True)
    def import_reference(
        self,
        name: str,
        config: ReferenceEntityConfig,
        reset_table: bool = False,
    ) -> str:
        """Import a reference entity from generic configuration.

        Args:
            name: Entity name
            config: Reference configuration
            reset_table: If True, drop and recreate the table

        Returns:
            Status message with row count

        Raises:
            ValidationError: If configuration is invalid
            FileReadError: If source file not found
            DataImportError: If import fails
        """
        if not name:
            raise ValidationError("name", "Entity name cannot be empty")

        # Build table name
        table_name = f"entity_{name}"

        # Determine entity kind
        kind = EntityKind.REFERENCE
        if config.kind == "hierarchical":
            kind = EntityKind.REFERENCE
        elif config.kind == "spatial":
            kind = EntityKind.REFERENCE

        # Reset table if requested
        if reset_table and self.db.has_table(table_name):
            self.db.execute_sql(f"DROP TABLE IF EXISTS {table_name}")
            logger.info(f"Dropped existing table: {table_name}")

        try:
            # Detect connector mode
            if config.connector.type == ConnectorType.DERIVED:
                # DERIVED MODE: Extract from source dataset
                logger.info(
                    f"Importing derived reference '{name}' from source '{config.connector.source}'"
                )

                # 1. Validate source exists
                try:
                    source_entity = self.registry.get(config.connector.source)
                except DatabaseQueryError:
                    raise ValidationError(
                        "connector.source",
                        f"Source entity '{config.connector.source}' not found. "
                        f"Ensure datasets are imported before derived references.",
                    )

                if not source_entity:
                    raise ValidationError(
                        "connector.source",
                        f"Source entity '{config.connector.source}' not found. "
                        f"Ensure datasets are imported before derived references.",
                    )

                # 2. Import via hierarchy builder
                result = self.engine.import_derived_reference(
                    entity_name=name,
                    table_name=table_name,
                    source_table=source_entity.table_name,
                    extraction_config=config.connector.extraction,
                    hierarchy_config=config.hierarchy,
                    kind=kind,
                )

                return f"Derived {result.rows} hierarchical records into {table_name} from {source_entity.table_name}"

            elif config.connector.type == ConnectorType.FILE_MULTI_FEATURE:
                # FILE_MULTI_FEATURE MODE: Import multiple spatial files as features
                logger.info(
                    f"Importing multi-feature reference '{name}' from {len(config.connector.sources)} sources"
                )

                # Import via multi-feature engine
                result = self.engine.import_multi_feature(
                    entity_name=name,
                    table_name=table_name,
                    sources=config.connector.sources,
                    kind=kind,
                    id_field=config.schema.id_field if config.schema else None,
                )

                return f"Imported {result.rows} features into {table_name} from {len(config.connector.sources)} source files"

            else:
                # DIRECT MODE: Import from file (existing logic)
                # Validate connector configuration
                if not config.connector or not config.connector.path:
                    raise ValidationError(
                        "connector.path", "Connector path must be specified"
                    )

                source_path = Path(config.connector.path).resolve()
                if not source_path.exists():
                    raise FileReadError(
                        str(source_path),
                        "Source file not found",
                        details={"path": str(source_path)},
                    )

                # Import using generic engine
                result = self.engine.import_from_csv(
                    entity_name=name,
                    table_name=table_name,
                    source_path=str(source_path),
                    kind=kind,
                    id_field=config.schema.id_field if config.schema else None,
                    extra_config={
                        "hierarchy": config.hierarchy.model_dump()
                        if config.hierarchy
                        else None,
                        "enrichment": [e.model_dump() for e in config.enrichment]
                        if config.enrichment
                        else [],
                    },
                )

                return f"Imported {result.rows} records into {table_name} from {source_path.name}"

        except Exception as exc:
            if isinstance(exc, (ValidationError, FileReadError)):
                raise
            raise DataImportError(
                f"Failed to import reference '{name}'",
                details={"error": str(exc)},
            ) from exc

    @error_handler(log=True, raise_error=True)
    def import_dataset(
        self,
        name: str,
        config: DatasetEntityConfig,
        reset_table: bool = False,
    ) -> str:
        """Import a dataset entity from generic configuration.

        Args:
            name: Entity name
            config: Dataset configuration
            reset_table: If True, drop and recreate the table

        Returns:
            Status message with row count

        Raises:
            ValidationError: If configuration is invalid
            FileReadError: If source file not found
            DataImportError: If import fails
        """
        if not name:
            raise ValidationError("name", "Entity name cannot be empty")

        # Validate connector configuration
        if not config.connector or not config.connector.path:
            raise ValidationError("connector.path", "Connector path must be specified")

        source_path = Path(config.connector.path).resolve()
        if not source_path.exists():
            raise FileReadError(
                str(source_path),
                "Source file not found",
                details={"path": str(source_path)},
            )

        try:
            # Build table name
            table_name = f"dataset_{name}"

            # Reset table if requested
            if reset_table and self.db.has_table(table_name):
                self.db.execute_sql(f"DROP TABLE IF EXISTS {table_name}")
                logger.info(f"Dropped existing table: {table_name}")

            # Import using generic engine
            result = self.engine.import_from_csv(
                entity_name=name,
                table_name=table_name,
                source_path=str(source_path),
                kind=EntityKind.DATASET,
                id_field=config.schema.id_field if config.schema else None,
                extra_config={
                    "links": [link.model_dump() for link in config.links]
                    if config.links
                    else [],
                    "options": config.options.model_dump() if config.options else {},
                },
            )

            return f"Imported {result.rows} records into {table_name} from {source_path.name}"

        except Exception as exc:
            raise DataImportError(
                f"Failed to import dataset '{name}'",
                details={"file": str(source_path), "error": str(exc)},
            ) from exc

    def _validate_dependencies(self, config: GenericImportConfig) -> None:
        """Validate no circular dependencies in derived references.

        Args:
            config: Import configuration to validate

        Raises:
            ValidationError: If circular dependencies are detected
        """
        entities = config.entities
        if not entities or not entities.references:
            return

        references = entities.references
        datasets = entities.datasets or {}

        derived_deps: dict[str, str] = {}
        for ref_name, ref_config in references.items():
            if ref_config.connector.type != ConnectorType.DERIVED:
                continue

            source = ref_config.connector.source

            # Ignore dependencies on datasets even if they share the same name
            if source == ref_name and source in datasets:
                continue

            if (
                source in references
                and references[source].connector.type == ConnectorType.DERIVED
            ):
                derived_deps[ref_name] = source

        # Check for cycles (simple DFS)
        def has_cycle(node, visited, rec_stack):
            visited.add(node)
            rec_stack.add(node)

            if node in derived_deps:
                neighbor = derived_deps[node]
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        visited = set()
        for ref_name in derived_deps:
            if ref_name not in visited:
                if has_cycle(ref_name, visited, set()):
                    raise ValidationError(
                        "entities.references",
                        f"Circular dependency detected involving '{ref_name}'",
                    )

    @error_handler(log=True, raise_error=True)
    def import_all(
        self,
        generic_config: GenericImportConfig,
        reset_table: bool = False,
    ) -> str:
        """Import all entities from a generic import configuration.

        This imports in 3 phases:
        1. Datasets (sources for derived references)
        2. Derived references (depend on datasets)
        3. Direct references (no dependencies)

        Args:
            generic_config: Generic import configuration
            reset_table: If True, drop and recreate all tables

        Returns:
            Status message with import summary

        Raises:
            ValidationError: If circular dependencies detected
            DataImportError: If any import fails
        """
        # Validate dependencies first
        self._validate_dependencies(generic_config)

        results = []

        try:
            # Phase 1: Import datasets (sources for derived references)
            if generic_config.entities and generic_config.entities.datasets:
                logger.info("Phase 1: Importing datasets...")
                for ds_name, ds_config in generic_config.entities.datasets.items():
                    result = self.import_dataset(ds_name, ds_config, reset_table)
                    results.append(f"  [Dataset] {result}")

            # Phase 2: Import derived references (depend on datasets)
            if generic_config.entities and generic_config.entities.references:
                logger.info("Phase 2: Importing derived references...")
                derived_refs = {
                    name: cfg
                    for name, cfg in generic_config.entities.references.items()
                    if cfg.connector.type == ConnectorType.DERIVED
                }
                for ref_name, ref_config in derived_refs.items():
                    result = self.import_reference(ref_name, ref_config, reset_table)
                    results.append(f"  [Derived Ref] {result}")

            # Phase 3: Import direct references (no dependencies)
            if generic_config.entities and generic_config.entities.references:
                logger.info("Phase 3: Importing direct references...")
                direct_refs = {
                    name: cfg
                    for name, cfg in generic_config.entities.references.items()
                    if cfg.connector.type != ConnectorType.DERIVED
                }
                for ref_name, ref_config in direct_refs.items():
                    result = self.import_reference(ref_name, ref_config, reset_table)
                    results.append(f"  [Direct Ref] {result}")

            summary = "\n".join(results) if results else "No entities imported"
            return f"Import completed successfully:\n{summary}"

        except Exception as exc:
            if isinstance(exc, ValidationError):
                raise
            raise DataImportError(
                "Failed to import configuration",
                details={"error": str(exc)},
            ) from exc
