"""Collection-scoped widget proposal API service."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import pandas as pd

from niamoto.common.database import Database
from niamoto.common.table_resolver import quote_identifier, resolve_dataset_table
from niamoto.common.transform_config_models import validate_transform_config
from niamoto.core.collections.catalog import CollectionCatalogService
from niamoto.core.collections.models import CollectionCatalogEntry
from niamoto.core.collections.widget_proposal_models import (
    WidgetProposal,
    WidgetProposalGroups,
)
from niamoto.core.collections.widget_proposal_service import WidgetProposalService
from niamoto.core.imports.class_object_analyzer import (
    ClassObjectCategory,
    ClassObjectStats,
)
from niamoto.core.imports.data_analyzer import DataAnalyzer, EnrichedColumnProfile
from niamoto.core.imports.multi_field_detector import (
    MultiFieldPattern,
    MultiFieldPatternDetector,
)
from niamoto.core.imports.profiler import DataProfiler
from niamoto.gui.api.models.widget_proposals import (
    WidgetProposalApplyResponse,
    WidgetProposalConfigChange,
    WidgetProposalPreviewResponse,
    WidgetProposalSelection,
)
from niamoto.gui.api.services.templates.config_service import (
    EXPORT_CONFIG_WRITE_LOCK,
    TRANSFORM_CONFIG_WRITE_LOCK,
    find_or_create_transform_group,
    load_export_config,
    load_transform_config,
    save_export_config,
    save_transform_config,
)


@dataclass(frozen=True)
class _SourceAnalysis:
    profiles: list[EnrichedColumnProfile]
    class_objects: list[ClassObjectStats]
    multi_field_patterns: list[MultiFieldPattern]


class CollectionWidgetProposalService:
    """Build, preview, and apply widget proposals for collection Blocks."""

    def __init__(
        self,
        *,
        work_dir: str | Path,
        db_path: str | Path | None,
        import_config: dict[str, Any],
        transform_config: list[dict[str, Any]],
        export_config: dict[str, Any],
    ) -> None:
        self.work_dir = Path(work_dir)
        self.db_path = Path(db_path) if db_path else None
        self.import_config = import_config
        self.transform_config = transform_config
        self.export_config = export_config
        self.catalog_service = CollectionCatalogService(
            import_config=import_config,
            transform_config=transform_config,
            export_config=export_config,
        )
        self.proposal_service = WidgetProposalService()

    def get_proposals(self, collection_name: str) -> WidgetProposalGroups:
        """Return grouped proposals for a collection."""

        collection = self.catalog_service.get_collection(collection_name)
        source_name = self._source_name_for_collection(collection)
        analysis = self._analysis_for_source(source_name)
        return self.proposal_service.generate_for_collection(
            collection=collection.name,
            source_name=source_name,
            profiles=analysis.profiles,
            class_objects=analysis.class_objects,
            multi_field_patterns=analysis.multi_field_patterns,
            existing_proposal_keys=self._existing_widget_keys(collection.name),
        )

    def preview_apply(
        self,
        collection_name: str,
        selections: Sequence[WidgetProposalSelection],
    ) -> WidgetProposalPreviewResponse:
        """Build a side-effect-free preview for selected proposals."""

        proposals = self.get_proposals(collection_name)
        by_id = {proposal.id: proposal for proposal in proposals.all_proposals()}
        existing_widgets = self._existing_transform_widgets(collection_name)
        source_relation_error = self._source_relation_error(collection_name)

        changes: list[WidgetProposalConfigChange] = []
        conflicts: list[WidgetProposalConfigChange] = []
        invalid: list[WidgetProposalConfigChange] = []

        for selection in selections:
            proposal = by_id.get(selection.proposal_id)
            if proposal is None:
                change = WidgetProposalConfigChange(
                    proposal_id=selection.proposal_id,
                    widget_id=selection.proposal_id,
                    title="Unknown proposal",
                    action="invalid",
                    reason="Proposal is stale or no longer available.",
                )
                invalid.append(change)
                changes.append(change)
                continue

            change = self._change_for_selection(
                proposal,
                selection,
                existing_widgets=existing_widgets,
                source_relation_error=source_relation_error,
            )
            changes.append(change)
            if change.action == "conflict":
                conflicts.append(change)
            elif change.action == "invalid":
                invalid.append(change)

        return WidgetProposalPreviewResponse(
            collection=collection_name,
            writes_files=False,
            changes=changes,
            conflicts=conflicts,
            invalid=invalid,
            preview_token=self._preview_token(collection_name, changes),
        )

    def apply(
        self,
        collection_name: str,
        selections: Sequence[WidgetProposalSelection],
        *,
        preview_token: str | None = None,
    ) -> WidgetProposalApplyResponse:
        """Apply selected proposal recipes to transform.yml and export.yml."""

        with TRANSFORM_CONFIG_WRITE_LOCK, EXPORT_CONFIG_WRITE_LOCK:
            self._refresh_configs()
            preview = self.preview_apply(collection_name, selections)
            applicable = [
                change
                for change in preview.changes
                if change.action in {"add", "replace"}
            ]
            skipped = [
                change
                for change in preview.changes
                if change.action not in {"add", "replace"}
            ]

            if preview_token and preview.preview_token != preview_token:
                return WidgetProposalApplyResponse(
                    collection=collection_name,
                    success=False,
                    applied=[],
                    skipped=preview.changes,
                    message="Preview is stale; rebuild the preview before applying.",
                    preview_token=preview.preview_token,
                )

            if preview.conflicts or preview.invalid:
                return WidgetProposalApplyResponse(
                    collection=collection_name,
                    success=False,
                    applied=[],
                    skipped=skipped,
                    message="Resolve conflicts or stale proposals before applying.",
                    preview_token=preview.preview_token,
                )

            if not applicable:
                return WidgetProposalApplyResponse(
                    collection=collection_name,
                    success=True,
                    applied=[],
                    skipped=skipped,
                    message="No applicable widget proposals were selected.",
                    preview_token=preview.preview_token,
                )

            transform_config = deepcopy(self.transform_config)
            export_config = deepcopy(self.export_config)
            group = find_or_create_transform_group(transform_config, collection_name)
            group["sources"] = self._merged_sources(
                group.get("sources", []), collection_name
            )
            widgets_data = group.setdefault("widgets_data", {})

            for change in applicable:
                if change.transform_widget:
                    transform_widget = dict(change.transform_widget)
                    transform_widget.pop("export_override", None)
                    widgets_data[change.widget_id] = transform_widget

            validated_transform = validate_transform_config(transform_config)
            updated_export = self._build_export_config(
                export_config,
                collection_name,
                applicable,
            )

            transform_backup = None
            export_backup = None
            try:
                transform_backup = save_transform_config(
                    self.work_dir, validated_transform, create_backup=True
                )
                export_backup = save_export_config(
                    self.work_dir, updated_export, create_backup=True
                )
            except Exception:
                save_transform_config(self.work_dir, self.transform_config)
                save_export_config(self.work_dir, self.export_config)
                raise

            self.transform_config = validated_transform
            self.export_config = updated_export
            self._refresh_catalog_service()
            self._invalidate_preview_cache()

            backup_files = [
                str(path.relative_to(self.work_dir))
                for path in (transform_backup, export_backup)
                if path is not None and path.is_relative_to(self.work_dir)
            ]
            return WidgetProposalApplyResponse(
                collection=collection_name,
                success=True,
                applied=applicable,
                skipped=skipped,
                message=f"Applied {len(applicable)} widget proposal(s).",
                preview_token=preview.preview_token,
                written_files=["config/transform.yml", "config/export.yml"],
                backup_files=backup_files,
            )

    def _change_for_selection(
        self,
        proposal: WidgetProposal,
        selection: WidgetProposalSelection,
        *,
        existing_widgets: dict[str, Any],
        source_relation_error: str | None = None,
    ) -> WidgetProposalConfigChange:
        widget_id = proposal.id
        if selection.replacement == "skip":
            return WidgetProposalConfigChange(
                proposal_id=proposal.id,
                widget_id=widget_id,
                title=proposal.title,
                action="skip",
                reason="Selection was skipped by the user.",
            )

        if proposal.applyability != "applicable":
            return WidgetProposalConfigChange(
                proposal_id=proposal.id,
                widget_id=widget_id,
                title=proposal.title,
                action="invalid",
                reason=f"Proposal is {proposal.applyability} and cannot be applied directly.",
            )

        if source_relation_error:
            return WidgetProposalConfigChange(
                proposal_id=proposal.id,
                widget_id=widget_id,
                title=proposal.title,
                action="invalid",
                reason=source_relation_error,
            )

        if widget_id in existing_widgets and selection.replacement != "replace":
            return WidgetProposalConfigChange(
                proposal_id=proposal.id,
                widget_id=widget_id,
                title=proposal.title,
                action="conflict",
                reason="A widget with this proposal fingerprint already exists.",
            )

        transform_widget, export_widget = self._config_for_proposal(proposal)
        action = "replace" if widget_id in existing_widgets else "add"
        return WidgetProposalConfigChange(
            proposal_id=proposal.id,
            widget_id=widget_id,
            title=proposal.title,
            action=action,
            transform_widget=transform_widget,
            export_widget=export_widget,
        )

    def _config_for_proposal(
        self,
        proposal: WidgetProposal,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        recipe = proposal.recipe
        transformer = recipe.get("transformer", {})
        widget = recipe.get("widget", {})
        transform_widget = {
            "plugin": transformer.get("plugin"),
            "params": transformer.get("params") or {},
            "export_override": {
                "plugin": widget.get("plugin"),
                "title": proposal.title,
                "params": widget.get("params") or {},
            },
        }
        export_widget = {
            "plugin": widget.get("plugin"),
            "title": proposal.title,
            "data_source": proposal.id,
            "layout": {"colspan": 1, "order": 0},
        }
        if widget.get("params"):
            export_widget["params"] = widget["params"]
        return transform_widget, export_widget

    def _analysis_for_source(self, source_name: str) -> _SourceAnalysis:
        if self.db_path is None or not self.db_path.exists():
            return _SourceAnalysis([], [], [])

        db = Database(str(self.db_path), read_only=True)
        try:
            table_name = resolve_dataset_table(db, source_name)
            if not table_name:
                return _SourceAnalysis([], [], [])
            query = f"SELECT * FROM {quote_identifier(db, table_name)} LIMIT 5000"
            sample_df = pd.read_sql(query, db.engine)
            if sample_df.empty:
                return _SourceAnalysis([], [], [])
            dataset_profile = DataProfiler().profile_dataframe(
                sample_df,
                Path(table_name),
                total_count=len(sample_df),
            )
            analyzer = DataAnalyzer()
            profiles = [
                analyzer.enrich_profile(column_profile, sample_df[column_profile.name])
                for column_profile in dataset_profile.columns
                if column_profile.name in sample_df.columns
            ]
            return _SourceAnalysis(
                profiles=profiles,
                class_objects=self._class_objects_for_sample(sample_df),
                multi_field_patterns=MultiFieldPatternDetector().suggest_for_selection(
                    profiles, source_name
                ),
            )
        finally:
            db.close()

    def _profiles_for_source(self, source_name: str) -> list[EnrichedColumnProfile]:
        return self._analysis_for_source(source_name).profiles

    def _class_objects_for_sample(
        self, sample_df: pd.DataFrame
    ) -> list[ClassObjectStats]:
        column_lookup = {
            str(column).lower(): str(column) for column in sample_df.columns
        }
        required = {"class_object", "class_name", "class_value"}
        if not required.issubset(column_lookup):
            return []

        object_column = column_lookup["class_object"]
        name_column = column_lookup["class_name"]
        value_column = column_lookup["class_value"]
        numeric_values = pd.to_numeric(sample_df[value_column], errors="coerce")
        stats: list[ClassObjectStats] = []

        for class_object_name, group in sample_df.groupby(object_column, dropna=True):
            if class_object_name is None or str(class_object_name).strip() == "":
                continue

            class_names = [
                str(value)
                for value in group[name_column].dropna().astype(str).unique().tolist()
                if value != ""
            ]
            class_names = sorted(class_names)
            value_type = self._class_object_value_type(class_names)
            category = self._class_object_category(len(class_names), value_type)
            suggested_plugin, confidence = self._class_object_plugin(
                len(class_names),
                value_type,
            )
            values = numeric_values.loc[group.index].dropna().head(5).tolist()
            stats.append(
                ClassObjectStats(
                    name=str(class_object_name),
                    cardinality=len(class_names),
                    class_names=class_names[:10],
                    value_type=value_type,
                    sample_values=[float(value) for value in values],
                    suggested_plugin=suggested_plugin,
                    confidence=confidence,
                    category=category,
                    mapping_hints=self._class_object_mapping_hints(class_names),
                )
            )

        return stats

    def _class_object_value_type(self, class_names: Sequence[str]) -> str:
        if not class_names:
            return "categorical"
        numeric_count = 0
        for name in class_names:
            try:
                float(name)
            except (TypeError, ValueError):
                continue
            numeric_count += 1
        return "numeric" if numeric_count / len(class_names) >= 0.8 else "categorical"

    def _class_object_category(
        self,
        cardinality: int,
        value_type: str,
    ) -> ClassObjectCategory:
        if cardinality <= 1:
            return ClassObjectCategory.SCALAR
        if cardinality == 2:
            return ClassObjectCategory.BINARY
        if cardinality == 3:
            return ClassObjectCategory.TERNARY
        if value_type == "numeric":
            return ClassObjectCategory.NUMERIC_BINS
        if cardinality <= 15:
            return ClassObjectCategory.MULTI_CATEGORY
        return ClassObjectCategory.LARGE_CATEGORY

    def _class_object_plugin(
        self,
        cardinality: int,
        value_type: str,
    ) -> tuple[str, float]:
        if cardinality <= 1:
            return "class_object_field_aggregator", 0.95
        if cardinality == 2:
            return "class_object_binary_aggregator", 0.95
        if value_type == "numeric":
            return "class_object_series_extractor", 0.9
        if cardinality <= 5:
            return "class_object_series_extractor", 0.9
        if cardinality <= 15:
            return "class_object_series_extractor", 0.85
        return "class_object_series_extractor", 0.8

    def _class_object_mapping_hints(
        self,
        class_names: Sequence[str],
    ) -> dict[str, str]:
        mapping = {
            "oui": "positive",
            "yes": "positive",
            "true": "positive",
            "vrai": "positive",
            "1": "positive",
            "non": "negative",
            "no": "negative",
            "false": "negative",
            "faux": "negative",
            "0": "negative",
        }
        result: dict[str, str] = {}
        for name in class_names:
            result[name] = mapping.get(name.lower(), _slug_key(name))
        return result

    def _source_name_for_collection(self, collection: CollectionCatalogEntry) -> str:
        if collection.source_type == "dataset":
            return collection.source_name

        references = self.import_config.get("entities", {}).get("references", {})
        reference_config = references.get(collection.source_name, {})
        if isinstance(reference_config, dict):
            relation = reference_config.get("relation", {})
            if isinstance(relation, dict) and relation.get("dataset"):
                return str(relation["dataset"])
            connector = reference_config.get("connector", {})
            if isinstance(connector, dict) and connector.get("source"):
                return str(connector["source"])

        return collection.source_name

    def _existing_widget_keys(self, collection_name: str) -> set[str]:
        return set(self._existing_transform_widgets(collection_name))

    def _existing_transform_widgets(self, collection_name: str) -> dict[str, Any]:
        for group in self.transform_config:
            if isinstance(group, dict) and group.get("group_by") == collection_name:
                widgets = group.get("widgets_data", {})
                return widgets if isinstance(widgets, dict) else {}
        return {}

    def _existing_sources_for_collection(
        self,
        collection_name: str,
    ) -> list[dict[str, Any]]:
        for group in self.transform_config:
            if isinstance(group, dict) and group.get("group_by") == collection_name:
                sources = group.get("sources", [])
                return sources if isinstance(sources, list) else []
        return []

    def _source_relation_error(self, collection_name: str) -> str | None:
        collection = self.catalog_service.get_collection(collection_name)
        source_name = self._source_name_for_collection(collection)
        existing_sources = self._existing_sources_for_collection(collection_name)
        if any(
            isinstance(source, dict) and source.get("name") == source_name
            for source in existing_sources
        ):
            return None

        source_config = self._source_config_for_collection(
            collection,
            source_name,
            existing_sources,
        )
        if source_config is not None:
            return None

        return (
            f"No transform source relation could be derived for {source_name}; "
            "review or configure the collection source before applying widget proposals."
        )

    def _merged_sources(
        self,
        existing_sources: list[dict[str, Any]],
        collection_name: str,
    ) -> list[dict[str, Any]]:
        collection = self.catalog_service.get_collection(collection_name)
        source_name = self._source_name_for_collection(collection)
        if any(source.get("name") == source_name for source in existing_sources):
            return existing_sources

        source_config = self._source_config_for_collection(
            collection,
            source_name,
            existing_sources,
        )
        if source_config is None:
            raise ValueError(
                f"Cannot apply widget proposals for {collection_name}: no transform source relation could be derived for {source_name}."
            )

        return [*existing_sources, source_config]

    def _source_config_for_collection(
        self,
        collection: CollectionCatalogEntry,
        source_name: str,
        existing_sources: Sequence[dict[str, Any]],
    ) -> dict[str, Any] | None:
        for source in existing_sources:
            if isinstance(source, dict) and source.get("name") == source_name:
                return deepcopy(source)

        existing = self._existing_source_config(collection.name, source_name)
        if existing:
            return existing

        auxiliary_source = self._auxiliary_source_config(collection.name, source_name)
        if auxiliary_source:
            return auxiliary_source

        relation = self._reference_relation_config(collection, source_name)
        if relation:
            return {
                "name": source_name,
                "data": source_name,
                "grouping": collection.name,
                "relation": relation,
            }

        if (
            collection.source_type == "dataset"
            and collection.source_name == source_name
        ):
            id_field = self._id_field_for_entity(source_name) or "id"
            return {
                "name": source_name,
                "data": source_name,
                "grouping": collection.name,
                "relation": {
                    "plugin": "direct_reference",
                    "key": id_field,
                    "ref_key": id_field,
                },
            }

        return None

    def _id_field_for_entity(self, entity_name: str) -> str | None:
        entities = self.import_config.get("entities", {})
        for section in ("datasets", "references"):
            cfg = entities.get(section, {}).get(entity_name)
            if not isinstance(cfg, dict):
                continue
            schema = cfg.get("schema", {})
            if isinstance(schema, dict):
                id_field = schema.get("id_field") or schema.get("id")
                if id_field:
                    return str(id_field)
        return None

    def _existing_source_config(
        self,
        collection_name: str,
        source_name: str,
    ) -> dict[str, Any] | None:
        for group in self.transform_config:
            if not isinstance(group, dict) or group.get("group_by") != collection_name:
                continue
            for source in group.get("sources", []) or []:
                if isinstance(source, dict) and source.get("name") == source_name:
                    return deepcopy(source)
        return None

    def _auxiliary_source_config(
        self,
        collection_name: str,
        source_name: str,
    ) -> dict[str, Any] | None:
        for source in self.import_config.get("auxiliary_sources", []) or []:
            if not isinstance(source, dict) or source.get("name") != source_name:
                continue
            grouping = source.get("grouping") or source.get("group_by")
            if grouping and grouping != collection_name:
                continue
            source_config = {
                key: deepcopy(value)
                for key, value in source.items()
                if key in {"name", "data", "grouping", "relation", "path"}
            }
            source_config.setdefault("data", source_name)
            source_config.setdefault("grouping", collection_name)
            return source_config
        return None

    def _reference_relation_config(
        self,
        collection: CollectionCatalogEntry,
        source_name: str,
    ) -> dict[str, Any] | None:
        references = self.import_config.get("entities", {}).get("references", {})
        reference_config = references.get(collection.source_name, {})
        if not isinstance(reference_config, dict):
            return None

        relation = reference_config.get("relation", {})
        if not isinstance(relation, dict) or relation.get("dataset") != source_name:
            return None

        plugin = str(
            relation.get("plugin") or relation.get("type") or "direct_reference"
        )
        key = relation.get("foreign_key") or relation.get("key")
        ref_key = relation.get("reference_key") or relation.get("ref_key")
        ref_field = relation.get("ref_field")
        if not key or not (ref_key or ref_field):
            return None

        relation_config: dict[str, Any] = {
            "plugin": plugin,
            "key": key,
        }
        if ref_key:
            relation_config["ref_key"] = ref_key
        if ref_field:
            relation_config["ref_field"] = ref_field
        if relation.get("fields"):
            relation_config["fields"] = deepcopy(relation["fields"])
        return relation_config

    def _build_export_config(
        self,
        export_config: dict[str, Any],
        collection_name: str,
        changes: Sequence[WidgetProposalConfigChange],
    ) -> dict[str, Any]:
        updated = deepcopy(export_config) if isinstance(export_config, dict) else {}
        exports = updated.setdefault("exports", [])
        html_exporter = self._find_or_create_html_exporter(exports)
        groups = html_exporter.setdefault("groups", [])
        group = self._find_or_create_export_group(groups, collection_name)
        widgets = group.setdefault("widgets", [])
        by_source = {
            widget.get("data_source"): widget
            for widget in widgets
            if isinstance(widget, dict) and widget.get("data_source")
        }
        max_order = max(
            (
                widget.get("layout", {}).get("order", 0)
                for widget in widgets
                if isinstance(widget, dict)
            ),
            default=-1,
        )

        for change in changes:
            if not change.export_widget:
                continue
            export_widget = deepcopy(change.export_widget)
            existing = by_source.get(change.widget_id)
            if existing:
                preserved_layout = existing.get("layout", {})
                existing.clear()
                existing.update(export_widget)
                existing["layout"] = {
                    **export_widget.get("layout", {}),
                    **preserved_layout,
                }
            else:
                max_order += 1
                export_widget["layout"] = {
                    **export_widget.get("layout", {}),
                    "order": max_order,
                }
                widgets.append(export_widget)
                by_source[change.widget_id] = export_widget

        return updated

    def _find_or_create_html_exporter(
        self, exports: list[dict[str, Any]]
    ) -> dict[str, Any]:
        for export in exports:
            if (
                isinstance(export, dict)
                and export.get("exporter") == "html_page_exporter"
            ):
                return export

        export = {
            "name": "web_pages",
            "enabled": True,
            "exporter": "html_page_exporter",
            "params": {"template_dir": "templates/", "output_dir": "exports/web"},
            "groups": [],
        }
        exports.append(export)
        return export

    def _find_or_create_export_group(
        self,
        groups: list[dict[str, Any]],
        collection_name: str,
    ) -> dict[str, Any]:
        for group in groups:
            if isinstance(group, dict) and group.get("group_by") == collection_name:
                return group

        group = {
            "group_by": collection_name,
            "output_pattern": f"{collection_name}/{{id}}.html",
            "index_output_pattern": f"{collection_name}/index.html",
            "widgets": [],
        }
        groups.append(group)
        return group

    def _preview_token(
        self,
        collection_name: str,
        changes: Sequence[WidgetProposalConfigChange],
    ) -> str:
        payload = {
            "collection": collection_name,
            "changes": [
                change.model_dump(mode="json", exclude_none=True) for change in changes
            ],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:24]

    def _refresh_configs(self) -> None:
        self.transform_config = load_transform_config(self.work_dir)
        self.export_config = load_export_config(self.work_dir)
        self._refresh_catalog_service()

    def _refresh_catalog_service(self) -> None:
        self.catalog_service = CollectionCatalogService(
            import_config=self.import_config,
            transform_config=self.transform_config,
            export_config=self.export_config,
        )

    def _invalidate_preview_cache(self) -> None:
        try:
            from niamoto.gui.api.services.preview_engine.engine import (
                get_preview_engine,
            )

            engine = get_preview_engine()
            if engine:
                engine.invalidate()
        except Exception:
            pass


def _slug_key(value: str) -> str:
    import re
    import unicodedata

    normalized = unicodedata.normalize("NFD", value)
    ascii_value = "".join(
        character for character in normalized if unicodedata.category(character) != "Mn"
    )
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_value.lower()).strip("_")
    return slug or "value"
