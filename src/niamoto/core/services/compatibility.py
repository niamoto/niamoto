"""Pre-import impact check: analyze new CSV against existing pipeline config.

Compares a new source file schema against the columns referenced in
import.yml and transform.yml to report what will break, what might break,
and what is new.  Config is the source of truth; the EntityRegistry provides
context about what changed since the last import.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from niamoto.core.imports.config_models import ConnectorType
from niamoto.core.imports.engine import GenericImporter

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class ImpactLevel(str, Enum):
    BLOCKS_IMPORT = "blocks_import"
    BREAKS_TRANSFORM = "breaks_transform"
    WARNING = "warning"
    OPPORTUNITY = "opportunity"


class TargetKind(str, Enum):
    IMPORT_ENTITY = "import_entity"
    TRANSFORM_SOURCE = "transform_source"


@dataclass
class ColumnMatch:
    name: str
    old_type: str
    new_type: str


@dataclass
class ImpactItem:
    column: str
    level: ImpactLevel
    detail: str
    referenced_in: list[str] = field(default_factory=list)
    old_type: Optional[str] = None
    new_type: Optional[str] = None


@dataclass
class ImpactReport:
    entity_name: str
    file_path: str
    matched_columns: list[ColumnMatch] = field(default_factory=list)
    impacts: list[ImpactItem] = field(default_factory=list)
    error: Optional[str] = None
    skipped_reason: Optional[str] = None
    info_message: Optional[str] = None

    @property
    def has_blockers(self) -> bool:
        return any(i.level == ImpactLevel.BLOCKS_IMPORT for i in self.impacts)

    @property
    def has_warnings(self) -> bool:
        return any(
            i.level in (ImpactLevel.BREAKS_TRANSFORM, ImpactLevel.WARNING)
            for i in self.impacts
        )

    @property
    def has_opportunities(self) -> bool:
        return any(i.level == ImpactLevel.OPPORTUNITY for i in self.impacts)


# ---------------------------------------------------------------------------
# Reference type alias:  {column: [(path, level), ...]}
# ---------------------------------------------------------------------------

ColumnRefMap = Dict[str, List[Tuple[str, ImpactLevel]]]


# ---------------------------------------------------------------------------
# Config Reference Collector
# ---------------------------------------------------------------------------


class ConfigRefCollector:
    """Collect every column referenced in import.yml + transform.yml."""

    CLASS_OBJECT_STRUCTURAL_COLUMNS: Dict[str, Tuple[str, ...]] = {
        "class_object_series_extractor": ("class_object",),
        "class_object_field_aggregator": ("class_object", "class_value"),
        "class_object_categories_extractor": (
            "class_object",
            "class_name",
            "class_value",
        ),
        "class_object_binary_aggregator": (
            "class_object",
            "class_name",
            "class_value",
        ),
        "class_object_series_ratio_aggregator": (
            "class_object",
            "class_name",
            "class_value",
        ),
        "class_object_series_matrix_extractor": ("class_object", "class_value"),
        "class_object_series_by_axis_extractor": ("class_object", "class_value"),
        "class_object_categories_mapper": (
            "class_object",
            "class_name",
            "class_value",
        ),
    }
    SIMPLE_SOURCE_FIELD_PLUGINS: Dict[str, Tuple[str, ...]] = {
        "top_ranking": ("field", "aggregate_field"),
        "binned_distribution": ("field",),
        "binary_counter": ("field",),
        "statistical_summary": ("field",),
        "categorical_distribution": ("field",),
        "geospatial_extractor": ("field",),
        "shape_processor": ("field",),
    }
    GROUP_WIDGET_FIELD_PLUGINS: Dict[str, Tuple[str, ...]] = {
        "hierarchical_nav_widget": (
            "id_field",
            "name_field",
            "parent_id_field",
            "lft_field",
            "rght_field",
            "level_field",
            "group_by_field",
            "group_by_label_field",
        ),
    }

    def collect(
        self,
        entity_name: str,
        import_config: dict,
        transform_config: list[dict],
    ) -> ColumnRefMap:
        refs: ColumnRefMap = {}
        self._collect_import_refs(entity_name, import_config, refs)
        self._collect_auxiliary_source_refs(entity_name, import_config, refs)
        self._collect_transform_refs(entity_name, transform_config, refs)
        return refs

    # -- import.yml ----------------------------------------------------------

    def _collect_import_refs(
        self,
        entity_name: str,
        import_config: dict,
        refs: ColumnRefMap,
    ) -> None:
        entities = import_config.get("entities", {})
        datasets = entities.get("datasets", {})
        references = entities.get("references", {})

        if entity_name in datasets:
            self._collect_dataset_refs(entity_name, datasets[entity_name], refs)
            # Also collect extraction columns from DERIVED references that
            # depend on this dataset — removing those columns from the source
            # CSV would break the derived reference build.
            for ref_name, ref_cfg in references.items():
                connector = ref_cfg.get("connector", {})
                if (
                    connector.get("type") == ConnectorType.DERIVED.value
                    and connector.get("source") == entity_name
                ):
                    extraction = connector.get("extraction", {})
                    self._collect_extraction_refs(
                        entity_name, ref_name, extraction, refs
                    )
        elif entity_name in references:
            self._collect_reference_refs(entity_name, references[entity_name], refs)

    def _collect_auxiliary_source_refs(
        self,
        entity_name: str,
        import_config: dict,
        refs: ColumnRefMap,
    ) -> None:
        for source in import_config.get("auxiliary_sources", []) or []:
            source_name = source.get("name", "")
            data_entity = source.get("data", "")
            grouping_entity = source.get("grouping", "")
            relation = source.get("relation", {})
            prefix = f"import.yml > auxiliary_sources > {source_name}"
            self._collect_source_relation_refs(
                entity_name=entity_name,
                source_name=source_name,
                data_entity=data_entity,
                grouping_entity=grouping_entity,
                relation=relation,
                prefix=prefix,
                refs=refs,
            )

    def _collect_dataset_refs(
        self, entity_name: str, cfg: dict, refs: ColumnRefMap
    ) -> None:
        prefix = f"import.yml > {entity_name}"
        schema = cfg.get("schema", {})

        # id_field
        id_field = schema.get("id_field") or schema.get("id")
        if id_field:
            self._add(
                refs, id_field, f"{prefix} > schema.id_field", ImpactLevel.BLOCKS_IMPORT
            )

        # fields
        for f in schema.get("fields", []):
            name = f.get("name") if isinstance(f, dict) else f
            if name:
                self._add(
                    refs, name, f"{prefix} > schema.fields", ImpactLevel.BLOCKS_IMPORT
                )

        # links
        for link in cfg.get("links", []):
            if link.get("field"):
                self._add(
                    refs,
                    link["field"],
                    f"{prefix} > links > field",
                    ImpactLevel.BLOCKS_IMPORT,
                )
            if link.get("target_field"):
                self._add(
                    refs,
                    link["target_field"],
                    f"{prefix} > links > target_field",
                    ImpactLevel.BLOCKS_IMPORT,
                )

    def _collect_reference_refs(
        self, entity_name: str, cfg: dict, refs: ColumnRefMap
    ) -> None:
        prefix = f"import.yml > {entity_name}"
        schema = cfg.get("schema", {})

        # id_field
        id_field = schema.get("id_field") or schema.get("id")
        if id_field:
            self._add(
                refs, id_field, f"{prefix} > schema.id_field", ImpactLevel.BLOCKS_IMPORT
            )

        # fields
        for f in schema.get("fields", []):
            name = f.get("name") if isinstance(f, dict) else f
            if name:
                self._add(
                    refs, name, f"{prefix} > schema.fields", ImpactLevel.BLOCKS_IMPORT
                )

        # hierarchy levels
        hierarchy = cfg.get("hierarchy", {})
        for level in hierarchy.get("levels", []):
            col = level.get("column") if isinstance(level, dict) else level
            if col:
                self._add(
                    refs,
                    col,
                    f"{prefix} > hierarchy > {level.get('name', col) if isinstance(level, dict) else col}",
                    ImpactLevel.BLOCKS_IMPORT,
                )

        # extraction (for DERIVED — columns in the *source* dataset)
        connector = cfg.get("connector", {})
        extraction = connector.get("extraction", {})
        if extraction:
            self._collect_extraction_refs(entity_name, entity_name, extraction, refs)

    def _collect_extraction_refs(
        self,
        source_entity: str,
        ref_name: str,
        extraction: dict,
        refs: ColumnRefMap,
    ) -> None:
        """Collect columns from a DERIVED extraction config.

        These columns exist in the source dataset and are needed to build
        the derived reference.  Called both when checking the reference itself
        and when checking the source dataset it depends on.
        """
        prefix = f"import.yml > {ref_name} > extraction"
        for lvl in extraction.get("levels", []):
            col = lvl.get("column") if isinstance(lvl, dict) else lvl
            if col:
                lvl_name = lvl.get("name", col) if isinstance(lvl, dict) else col
                self._add(
                    refs,
                    col,
                    f"{prefix} > levels > {lvl_name}",
                    ImpactLevel.BLOCKS_IMPORT,
                )
        if extraction.get("id_column"):
            self._add(
                refs,
                extraction["id_column"],
                f"{prefix} > id_column",
                ImpactLevel.BLOCKS_IMPORT,
            )
        if extraction.get("name_column"):
            self._add(
                refs,
                extraction["name_column"],
                f"{prefix} > name_column",
                ImpactLevel.BLOCKS_IMPORT,
            )
        for col in extraction.get("additional_columns", []):
            self._add(
                refs,
                col,
                f"{prefix} > additional_columns",
                ImpactLevel.BLOCKS_IMPORT,
            )

    # -- transform.yml -------------------------------------------------------

    def _collect_transform_refs(
        self,
        entity_name: str,
        transform_config: list[dict],
        refs: ColumnRefMap,
    ) -> None:
        for group in transform_config:
            group_by = group.get("group_by", "")
            matched_widget_sources: set[str] = set()
            for source in group.get("sources", []):
                data_entity = source.get("data", "")
                grouping_entity = source.get("grouping", "")
                relation = source.get("relation", {})
                source_name = source.get("name", "")
                prefix = f"transform.yml > group {group_by} > source {source_name}"
                self._collect_source_relation_refs(
                    entity_name=entity_name,
                    source_name=source_name,
                    data_entity=data_entity,
                    grouping_entity=grouping_entity,
                    relation=relation,
                    prefix=prefix,
                    refs=refs,
                )
                if self._is_source_match(entity_name, source_name, data_entity):
                    matched_widget_sources.add(source_name)
                    if data_entity:
                        matched_widget_sources.add(data_entity)
                        if "/" in data_entity:
                            matched_widget_sources.add(Path(data_entity).stem)

            if group_by == entity_name:
                matched_widget_sources.add(entity_name)
                self._collect_group_widget_refs(
                    entity_name=entity_name,
                    group=group,
                    refs=refs,
                )

            for source_name in matched_widget_sources:
                self._collect_widget_source_refs(
                    source_name=source_name,
                    group=group,
                    refs=refs,
                )

    def _collect_source_relation_refs(
        self,
        *,
        entity_name: str,
        source_name: str,
        data_entity: str,
        grouping_entity: str,
        relation: dict,
        prefix: str,
        refs: ColumnRefMap,
    ) -> None:
        is_data_match = self._is_source_match(entity_name, source_name, data_entity)

        if is_data_match and relation.get("key"):
            self._add(
                refs,
                relation["key"],
                f"{prefix} > relation.key",
                ImpactLevel.BREAKS_TRANSFORM,
            )
        if is_data_match and relation.get("match_field"):
            self._add(
                refs,
                relation["match_field"],
                f"{prefix} > relation.match_field",
                ImpactLevel.BREAKS_TRANSFORM,
            )

        if grouping_entity == entity_name:
            if relation.get("ref_key"):
                self._add(
                    refs,
                    relation["ref_key"],
                    f"{prefix} > relation.ref_key",
                    ImpactLevel.BREAKS_TRANSFORM,
                )
            if relation.get("ref_field"):
                self._add(
                    refs,
                    relation["ref_field"],
                    f"{prefix} > relation.ref_field",
                    ImpactLevel.BREAKS_TRANSFORM,
                )
            for key, col in (relation.get("fields") or {}).items():
                self._add(
                    refs,
                    col,
                    f"{prefix} > relation.fields.{key}",
                    ImpactLevel.BREAKS_TRANSFORM,
                )

    def _collect_widget_source_refs(
        self,
        *,
        source_name: str,
        group: dict,
        refs: ColumnRefMap,
    ) -> None:
        group_by = group.get("group_by", "")
        widgets = group.get("widgets_data", {})
        for widget_name, widget_cfg in widgets.items():
            plugin_name = widget_cfg.get("plugin", "")
            params = widget_cfg.get("params", {}) or {}
            prefix = f"transform.yml > group {group_by} > widgets_data > {widget_name}"

            if plugin_name == "direct_attribute":
                widget_source = widget_cfg.get("source") or params.get("source")
                widget_field = widget_cfg.get("field") or params.get("field")
                if widget_source == source_name and widget_field:
                    self._add(
                        refs,
                        widget_field,
                        f"{prefix} > params.field",
                        ImpactLevel.BREAKS_TRANSFORM,
                    )

            if plugin_name == "field_aggregator":
                for index, field_cfg in enumerate(params.get("fields") or []):
                    if (
                        isinstance(field_cfg, dict)
                        and field_cfg.get("source") == source_name
                        and field_cfg.get("field")
                    ):
                        self._add(
                            refs,
                            field_cfg["field"],
                            f"{prefix} > params.fields[{index}].field",
                            ImpactLevel.BREAKS_TRANSFORM,
                        )

            self._collect_simple_widget_refs(
                source_name=source_name,
                plugin_name=plugin_name,
                params=params,
                prefix=prefix,
                refs=refs,
            )
            self._collect_time_series_widget_refs(
                source_name=source_name,
                plugin_name=plugin_name,
                params=params,
                prefix=prefix,
                refs=refs,
            )
            self._collect_top_ranking_widget_refs(
                source_name=source_name,
                current_entity=source_name,
                plugin_name=plugin_name,
                params=params,
                prefix=prefix,
                refs=refs,
            )
            self._collect_geospatial_widget_refs(
                source_name=source_name,
                plugin_name=plugin_name,
                params=params,
                prefix=prefix,
                refs=refs,
            )
            self._collect_class_object_widget_refs(
                source_name=source_name,
                plugin_name=plugin_name,
                params=params,
                prefix=prefix,
                refs=refs,
            )

    def _collect_group_widget_refs(
        self,
        *,
        entity_name: str,
        group: dict,
        refs: ColumnRefMap,
    ) -> None:
        group_by = group.get("group_by", "")
        widgets = group.get("widgets_data", {})
        for widget_name, widget_cfg in widgets.items():
            plugin_name = widget_cfg.get("plugin", "")
            params = widget_cfg.get("params", {}) or {}
            fields = self.GROUP_WIDGET_FIELD_PLUGINS.get(plugin_name)
            if not fields:
                continue
            referential_data = params.get("referential_data")
            prefix = f"transform.yml > group {group_by} > widgets_data > {widget_name}"
            if plugin_name == "hierarchical_nav_widget":
                if referential_data != entity_name or group_by != entity_name:
                    continue
            else:
                continue
            for field_name in fields:
                column = params.get(field_name)
                if column:
                    self._add(
                        refs,
                        column,
                        f"{prefix} > params.{field_name}",
                        ImpactLevel.BREAKS_TRANSFORM,
                    )

    def _collect_simple_widget_refs(
        self,
        *,
        source_name: str,
        plugin_name: str,
        params: dict,
        prefix: str,
        refs: ColumnRefMap,
    ) -> None:
        fields = self.SIMPLE_SOURCE_FIELD_PLUGINS.get(plugin_name)
        if not fields:
            return
        if params.get("source") != source_name:
            return
        for field_name in fields:
            column = params.get(field_name)
            if column:
                self._add(
                    refs,
                    column,
                    f"{prefix} > params.{field_name}",
                    ImpactLevel.BREAKS_TRANSFORM,
                )

    def _collect_time_series_widget_refs(
        self,
        *,
        source_name: str,
        plugin_name: str,
        params: dict,
        prefix: str,
        refs: ColumnRefMap,
    ) -> None:
        if plugin_name != "time_series_analysis":
            return
        if params.get("source") != source_name:
            return

        for field_name in ("field", "time_field"):
            column = params.get(field_name)
            if column:
                self._add(
                    refs,
                    column,
                    f"{prefix} > params.{field_name}",
                    ImpactLevel.BREAKS_TRANSFORM,
                )

        for key, column in (params.get("fields") or {}).items():
            if column:
                self._add(
                    refs,
                    column,
                    f"{prefix} > params.fields.{key}",
                    ImpactLevel.BREAKS_TRANSFORM,
                )

    def _collect_top_ranking_widget_refs(
        self,
        *,
        source_name: str,
        current_entity: str,
        plugin_name: str,
        params: dict,
        prefix: str,
        refs: ColumnRefMap,
    ) -> None:
        if plugin_name != "top_ranking":
            return

        widget_source = params.get("source")
        mode = params.get("mode", "direct")
        if widget_source == source_name:
            for field_name in ("field", "aggregate_field"):
                column = params.get(field_name)
                if column:
                    self._add(
                        refs,
                        column,
                        f"{prefix} > params.{field_name}",
                        ImpactLevel.BREAKS_TRANSFORM,
                    )

        hierarchy_table = params.get("hierarchy_table")
        if hierarchy_table == current_entity and mode in {
            "hierarchical",
            "join",
            "direct",
        }:
            hierarchy_columns = params.get("hierarchy_columns") or {}
            for field_name in ("id", "name", "rank", "parent_id", "left", "right"):
                column = hierarchy_columns.get(field_name)
                if column:
                    self._add(
                        refs,
                        column,
                        f"{prefix} > params.hierarchy_columns.{field_name}",
                        ImpactLevel.BREAKS_TRANSFORM,
                    )

        join_table = params.get("join_table")
        if join_table == current_entity and mode == "join":
            join_columns = params.get("join_columns") or {}
            for field_name in ("source_id", "target_id", "hierarchy_id"):
                column = join_columns.get(field_name)
                if column:
                    self._add(
                        refs,
                        column,
                        f"{prefix} > params.join_columns.{field_name}",
                        ImpactLevel.BREAKS_TRANSFORM,
                    )

    def _collect_geospatial_widget_refs(
        self,
        *,
        source_name: str,
        plugin_name: str,
        params: dict,
        prefix: str,
        refs: ColumnRefMap,
    ) -> None:
        if plugin_name != "geospatial_extractor":
            return
        if params.get("source") != source_name:
            return

        for field_name in ("field",):
            column = params.get(field_name)
            if column:
                self._add(
                    refs,
                    column,
                    f"{prefix} > params.{field_name}",
                    ImpactLevel.BREAKS_TRANSFORM,
                )

        for field_name in ("properties", "children_properties"):
            for index, column in enumerate(params.get(field_name) or []):
                if column:
                    self._add(
                        refs,
                        column,
                        f"{prefix} > params.{field_name}[{index}]",
                        ImpactLevel.BREAKS_TRANSFORM,
                    )

        hierarchy_config = params.get("hierarchy_config") or {}
        for field_name in (
            "type_field",
            "parent_field",
            "left_field",
            "right_field",
        ):
            column = hierarchy_config.get(field_name)
            if column:
                self._add(
                    refs,
                    column,
                    f"{prefix} > params.hierarchy_config.{field_name}",
                    ImpactLevel.BREAKS_TRANSFORM,
                )

    def _collect_class_object_widget_refs(
        self,
        *,
        source_name: str,
        plugin_name: str,
        params: dict,
        prefix: str,
        refs: ColumnRefMap,
    ) -> None:
        structural_columns = self.CLASS_OBJECT_STRUCTURAL_COLUMNS.get(plugin_name)
        if not structural_columns:
            return

        if plugin_name == "class_object_field_aggregator":
            for index, field_cfg in enumerate(params.get("fields") or []):
                if not isinstance(field_cfg, dict):
                    continue
                field_source = field_cfg.get("source") or params.get("source")
                if field_source != source_name:
                    continue
                self._add_required_columns(
                    refs=refs,
                    columns=structural_columns,
                    path_prefix=f"{prefix} > params.fields[{index}]",
                )
            return

        widget_source = params.get("source")
        if widget_source != source_name:
            return

        self._add_required_columns(
            refs=refs,
            columns=structural_columns,
            path_prefix=f"{prefix} > data",
        )

        if plugin_name == "class_object_series_extractor":
            for field_name in ("size_field", "value_field"):
                field_cfg = params.get(field_name) or {}
                input_column = field_cfg.get("input")
                if input_column:
                    self._add(
                        refs,
                        input_column,
                        f"{prefix} > params.{field_name}.input",
                        ImpactLevel.BREAKS_TRANSFORM,
                    )

        if plugin_name in {
            "class_object_series_matrix_extractor",
            "class_object_series_by_axis_extractor",
        }:
            axis_field = (params.get("axis") or {}).get("field")
            if axis_field:
                self._add(
                    refs,
                    axis_field,
                    f"{prefix} > params.axis.field",
                    ImpactLevel.BREAKS_TRANSFORM,
                )

    def _add_required_columns(
        self,
        *,
        refs: ColumnRefMap,
        columns: Tuple[str, ...],
        path_prefix: str,
    ) -> None:
        for column in columns:
            self._add(
                refs,
                column,
                f"{path_prefix}.{column}",
                ImpactLevel.BREAKS_TRANSFORM,
            )

    @staticmethod
    def _is_source_match(entity_name: str, source_name: str, data_entity: str) -> bool:
        return (
            data_entity == entity_name
            or source_name == entity_name
            or ("/" in data_entity and Path(data_entity).stem == entity_name)
        )

    @staticmethod
    def _is_transform_source_match(
        entity_name: str, source_name: str, data_entity: str
    ) -> bool:
        return "/" in data_entity and (
            source_name == entity_name or Path(data_entity).stem == entity_name
        )

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _add(
        refs: ColumnRefMap,
        column: str,
        path: str,
        level: ImpactLevel,
    ) -> None:
        refs.setdefault(column, []).append((path, level))


# ---------------------------------------------------------------------------
# CSV Schema Reader
# ---------------------------------------------------------------------------


class CSVSchemaReader:
    """Read CSV headers + sample, extract column names and coarse types."""

    @staticmethod
    def read_schema(
        file_path: Path,
    ) -> Tuple[List[Dict[str, str]], Optional[str]]:
        """Return (fields, error).

        ``fields`` is a list of ``{"name": str, "type": str}`` aligned with
        the coarse types persisted by ``engine.py._dtype_to_string``.
        """
        try:
            df = GenericImporter._read_csv(file_path, nrows=100)
        except Exception as exc:  # noqa: BLE001
            return [], str(exc)

        fields: List[Dict[str, str]] = []
        for col in df.columns:
            if df[col].notna().sum() == 0:
                inferred_type = "unknown"
            else:
                inferred_type = GenericImporter._dtype_to_string(df[col].dtype)
            fields.append(
                {
                    "name": str(col),
                    "type": inferred_type,
                }
            )
        return fields, None


# ---------------------------------------------------------------------------
# Entity Resolver
# ---------------------------------------------------------------------------


class EntityResolver:
    """Match an uploaded filename to an entity or transform source."""

    @staticmethod
    def resolve(
        filename: str,
        import_config: dict,
        transform_config: Optional[list[dict]] = None,
    ) -> Optional[str]:
        """Return entity/source name if exactly one basename match, else None.

        Scans both import.yml connector paths and transform.yml
        ``sources[].data`` values that are file paths (not entity names).
        """
        entities = import_config.get("entities", {})
        matches: list[str] = []

        # 1. import.yml connector paths
        for section in ("datasets", "references"):
            for name, cfg in entities.get(section, {}).items():
                connector = cfg.get("connector", {})
                ctype = connector.get("type", "")
                if ctype in (
                    ConnectorType.DERIVED.value,
                    ConnectorType.API.value,
                    ConnectorType.PLUGIN.value,
                ):
                    continue
                path = connector.get("path")
                if path and Path(path).name == filename:
                    matches.append(name)

        # 1b. import.yml auxiliary_sources
        for source in import_config.get("auxiliary_sources", []) or []:
            path = source.get("data", "")
            source_name = source.get("name", "")
            if path and Path(path).name == filename and source_name not in matches:
                matches.append(source_name)

        # 2. transform.yml sources[].data that are file paths (contain /)
        for group in transform_config or []:
            for source in group.get("sources", []):
                data = source.get("data", "")
                if "/" in data and Path(data).name == filename:
                    source_name = source.get("name", data)
                    if source_name not in matches:
                        matches.append(source_name)

        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            logger.warning(
                "Ambiguous entity match for '%s': %s — skipping check",
                filename,
                matches,
            )
        return None


# ---------------------------------------------------------------------------
# Compatibility Service (orchestrator)
# ---------------------------------------------------------------------------


class CompatibilityService:
    """Pre-import impact check: analyse new CSV against existing pipeline config."""

    _TYPELESS_SAMPLE_TYPES = {"unknown"}
    _SKIPPABLE_CONNECTORS = {
        ConnectorType.DERIVED.value: "Derived entity — check the source dataset instead",
        ConnectorType.API.value: "External connector — cannot check locally",
        ConnectorType.PLUGIN.value: "External connector — cannot check locally",
        ConnectorType.VECTOR.value: "Not supported in V1 (GPKG)",
        ConnectorType.FILE_MULTI_FEATURE.value: "Not supported in V1 (multi-feature)",
    }

    def __init__(self, working_directory: Path) -> None:
        self.working_directory = Path(working_directory)
        self._resolver = EntityResolver()
        self._collector = ConfigRefCollector()
        self._reader = CSVSchemaReader()

    # -- public API ----------------------------------------------------------

    def resolve_entity(self, filename: str) -> Optional[str]:
        """Resolve filename to entity/source name via import.yml + transform.yml."""
        import_config = self._load_import_config()
        transform_config = self._load_transform_config()
        return self._resolver.resolve(filename, import_config, transform_config)

    def check_compatibility(self, entity_name: str, file_path: str) -> ImpactReport:
        """Run full impact check for an entity against a new file.

        Checks connector type and returns a skip report for non-CSV
        connectors (VECTOR, FILE_MULTI_FEATURE, etc.).
        """
        # 1. Resolve & validate path
        resolved = (self.working_directory / file_path).resolve()
        if not resolved.is_relative_to(self.working_directory.resolve()):
            return ImpactReport(
                entity_name=entity_name,
                file_path=file_path,
                error="Path outside project directory",
            )

        # 2. Load configs
        import_config = self._load_import_config()
        transform_config = self._load_transform_config()
        target_kind = self._resolve_target_kind(
            entity_name, import_config, transform_config
        )

        # 2b. Check connector type — skip non-CSV connectors
        skip_reason = self._get_skip_reason(entity_name, import_config)
        if skip_reason:
            return ImpactReport(
                entity_name=entity_name,
                file_path=file_path,
                skipped_reason=skip_reason,
            )

        # 3. Read new CSV schema
        new_fields, read_error = self._reader.read_schema(resolved)
        if read_error:
            return ImpactReport(
                entity_name=entity_name,
                file_path=file_path,
                error=read_error,
            )

        new_schema = {f["name"]: f["type"] for f in new_fields}

        # 4. Load old schema from registry (context, not truth)
        old_schema = self._load_old_schema(
            entity_name, target_kind, import_config, transform_config
        )
        info_message = None
        if target_kind == TargetKind.TRANSFORM_SOURCE and not old_schema:
            info_message = (
                "First check for auxiliary source — validating required columns only "
                "until a transform run records a schema baseline"
            )

        # 5. Collect config references (source of truth)
        config_refs = self._collector.collect(
            entity_name, import_config, transform_config
        )

        # 6-9. Compare and produce report
        return self._compare(
            entity_name,
            file_path,
            new_schema,
            old_schema,
            config_refs,
            target_kind=target_kind,
            info_message=info_message,
        )

    def check_all(self, entity_filter: Optional[str] = None) -> list[ImpactReport]:
        """Check all entities (or one) from import.yml against their source files."""
        import_config = self._load_import_config()
        transform_config = self._load_transform_config()
        reports: list[ImpactReport] = []

        entities = import_config.get("entities", {})
        for section in ("datasets", "references"):
            for name, cfg in entities.get(section, {}).items():
                if entity_filter and name != entity_filter:
                    continue
                connector = cfg.get("connector", {})

                # Short-circuit skippable connectors
                skip_reason = self._get_skip_reason(name, import_config)
                if skip_reason:
                    reports.append(
                        ImpactReport(
                            entity_name=name,
                            file_path="",
                            skipped_reason=skip_reason,
                        )
                    )
                    continue

                # FILE / DUCKDB_CSV
                path = connector.get("path", "")
                if not path:
                    reports.append(
                        ImpactReport(
                            entity_name=name,
                            file_path="",
                            error="No source path configured",
                        )
                    )
                    continue

                reports.append(self.check_compatibility(name, path))

        for source in self._list_transform_sources(import_config, transform_config):
            name = source.get("name", "")
            path = source.get("path", "")
            if not name or not path:
                continue
            if entity_filter and name != entity_filter:
                continue
            reports.append(self.check_compatibility(name, path))

        return reports

    # -- private helpers -----------------------------------------------------

    def _get_skip_reason(self, entity_name: str, import_config: dict) -> Optional[str]:
        """Return a skip reason if the entity's connector is not checkable, else None."""
        entities = import_config.get("entities", {})
        for section in ("datasets", "references"):
            cfg = entities.get(section, {}).get(entity_name)
            if cfg:
                ctype = cfg.get("connector", {}).get("type", "")
                reason = self._SKIPPABLE_CONNECTORS.get(ctype)
                if reason and ctype == ConnectorType.DERIVED.value:
                    source = cfg.get("connector", {}).get("source", "?")
                    return f"Derived from {source} — check {source} instead"
                return reason
        return None  # Not in import.yml — could be a transform-only CSV source

    def _load_import_config(self) -> dict:
        path = self.working_directory / "config" / "import.yml"
        if not path.exists():
            return {"entities": {"datasets": {}, "references": {}}}
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}

    def _load_transform_config(self) -> list[dict]:
        path = self.working_directory / "config" / "transform.yml"
        if not path.exists():
            return []
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or []
        return data if isinstance(data, list) else []

    def _load_old_schema(
        self,
        entity_name: str,
        target_kind: TargetKind,
        import_config: dict,
        transform_config: list[dict],
    ) -> dict[str, str]:
        if target_kind == TargetKind.TRANSFORM_SOURCE:
            source = self._find_transform_source(
                entity_name, import_config, transform_config
            )
            if not source:
                return {}
            return self._load_transform_source_schema(source["name"])
        return self._load_registry_schema(entity_name)

    def _load_registry_schema(self, entity_name: str) -> dict[str, str]:
        """Load {col: type} from EntityRegistry.  Returns {} if unavailable."""
        try:
            from niamoto.common.database import Database
            from niamoto.core.imports.registry import EntityRegistry

            db_path = self._resolve_database_path()
            if not db_path or not db_path.exists():
                return {}
            db = Database(str(db_path), read_only=True)
            try:
                registry = EntityRegistry(db)
                meta = registry.get(entity_name)
                fields = meta.config.get("schema", {}).get("fields", [])
                return {
                    f["name"]: f.get("type", "string")
                    for f in fields
                    if isinstance(f, dict) and "name" in f
                }
            finally:
                try:
                    db.close_db_session()
                except Exception:  # noqa: BLE001
                    pass
                try:
                    db.engine.dispose()
                except Exception:  # noqa: BLE001
                    pass
        except Exception:  # noqa: BLE001
            return {}

    def _load_transform_source_schema(self, source_name: str) -> dict[str, str]:
        """Load {col: type} from TransformSourceRegistry. Returns {} if unavailable."""
        try:
            from niamoto.common.database import Database
            from niamoto.common.exceptions import DatabaseQueryError
            from niamoto.core.imports.source_registry import TransformSourceRegistry

            db_path = self._resolve_database_path()
            if not db_path or not db_path.exists():
                return {}
            db = Database(str(db_path), read_only=True)
            try:
                if not db.has_table(TransformSourceRegistry.SOURCES_TABLE):
                    return {}
                registry = TransformSourceRegistry(db)
                try:
                    meta = registry.get(source_name)
                except DatabaseQueryError:
                    return {}
                fields = meta.config.get("schema", {}).get("fields", [])
                return {
                    f["name"]: f.get("type", "string")
                    for f in fields
                    if isinstance(f, dict) and "name" in f
                }
            finally:
                try:
                    db.close_db_session()
                except Exception:  # noqa: BLE001
                    pass
                try:
                    db.engine.dispose()
                except Exception:  # noqa: BLE001
                    pass
        except Exception:  # noqa: BLE001
            return {}

    def _resolve_database_path(self) -> Optional[Path]:
        """Resolve the database path from config.yml."""
        config_path = self.working_directory / "config" / "config.yml"
        if not config_path.exists():
            return None
        try:
            with open(config_path, encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            db_rel = cfg.get("database", {}).get("path")
            if not db_rel:
                return None
            db_path = Path(db_rel)
            if not db_path.is_absolute():
                db_path = self.working_directory / db_path
            return db_path
        except Exception:  # noqa: BLE001
            return None

    def _compare(
        self,
        entity_name: str,
        file_path: str,
        new_schema: dict[str, str],
        old_schema: dict[str, str],
        config_refs: ColumnRefMap,
        *,
        target_kind: TargetKind,
        info_message: Optional[str] = None,
    ) -> ImpactReport:
        matched: list[ColumnMatch] = []
        impacts: list[ImpactItem] = []

        # All columns known from config + old schema
        all_known = set(config_refs.keys()) | set(old_schema.keys())

        for col in sorted(all_known):
            in_new = col in new_schema
            in_old = col in old_schema
            refs = config_refs.get(col, [])

            if not in_new and refs:
                # Missing column referenced in config
                highest_level = min(refs, key=lambda r: list(ImpactLevel).index(r[1]))[
                    1
                ]
                impacts.append(
                    ImpactItem(
                        column=col,
                        level=highest_level,
                        detail=f"Column '{col}' missing in new file",
                        referenced_in=[r[0] for r in refs],
                    )
                )
            elif in_new and in_old:
                old_t = old_schema[col]
                new_t = new_schema[col]
                matched.append(ColumnMatch(name=col, old_type=old_t, new_type=new_t))
                if (
                    old_t != new_t
                    and refs
                    and not self._is_non_informative_type_change(old_t, new_t)
                ):
                    impacts.append(
                        ImpactItem(
                            column=col,
                            level=ImpactLevel.WARNING,
                            detail=f"Type changed: {old_t} → {new_t}",
                            referenced_in=[r[0] for r in refs],
                            old_type=old_t,
                            new_type=new_t,
                        )
                    )
            elif in_new and not in_old and not refs:
                # Column in new file only — not referenced anywhere
                pass  # will be caught below as opportunity

        # Detect new columns (opportunity)
        if target_kind == TargetKind.IMPORT_ENTITY or old_schema:
            for col in sorted(new_schema.keys()):
                if col not in all_known:
                    impacts.append(
                        ImpactItem(
                            column=col,
                            level=ImpactLevel.OPPORTUNITY,
                            detail=f"New column '{col}' not yet in config",
                        )
                    )

        # Sort impacts by severity
        level_order = list(ImpactLevel)
        impacts.sort(key=lambda i: level_order.index(i.level))

        return ImpactReport(
            entity_name=entity_name,
            file_path=file_path,
            matched_columns=matched,
            impacts=impacts,
            info_message=info_message,
        )

    def _is_non_informative_type_change(self, old_type: str, new_type: str) -> bool:
        return (
            old_type in self._TYPELESS_SAMPLE_TYPES
            or new_type in self._TYPELESS_SAMPLE_TYPES
        )

    def _resolve_target_kind(
        self,
        entity_name: str,
        import_config: dict,
        transform_config: list[dict],
    ) -> TargetKind:
        entities = import_config.get("entities", {})
        for section in ("datasets", "references"):
            if entity_name in entities.get(section, {}):
                return TargetKind.IMPORT_ENTITY
        if self._find_transform_source(entity_name, import_config, transform_config):
            return TargetKind.TRANSFORM_SOURCE
        return TargetKind.IMPORT_ENTITY

    def _find_transform_source(
        self,
        entity_name: str,
        import_config: dict,
        transform_config: list[dict],
    ) -> Optional[dict[str, str]]:
        for source in self._list_transform_sources(import_config, transform_config):
            if (
                source["name"] == entity_name
                or Path(source["path"]).stem == entity_name
            ):
                return source
        return None

    def _list_transform_sources(
        self,
        import_config: dict,
        transform_config: list[dict],
    ) -> list[dict[str, str]]:
        entities = import_config.get("entities", {})
        entity_names = set(entities.get("datasets", {})) | set(
            entities.get("references", {})
        )
        sources: dict[str, dict[str, str]] = {}

        for source in import_config.get("auxiliary_sources", []) or []:
            name = source.get("name", "")
            path = source.get("data", "")
            grouping = source.get("grouping", "")
            if name and path and name not in entity_names:
                sources.setdefault(
                    name,
                    {"name": name, "path": path, "grouping": grouping},
                )

        for group in transform_config:
            for source in group.get("sources", []):
                path = source.get("data", "")
                name = source.get("name", "")
                grouping = source.get("grouping", "")
                if not name or not path or "/" not in path or name in entity_names:
                    continue
                sources.setdefault(
                    name,
                    {"name": name, "path": path, "grouping": grouping},
                )

        return list(sources.values())
