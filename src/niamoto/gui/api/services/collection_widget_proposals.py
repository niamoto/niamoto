"""Collection-scoped widget proposal API service."""

from __future__ import annotations

import hashlib
import json
import threading
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import pandas as pd

from niamoto.common.database import Database
from niamoto.common.table_resolver import (
    quote_identifier,
    resolve_dataset_table,
    resolve_reference_table,
)
from niamoto.common.transform_config_models import validate_transform_config
from niamoto.core.collections.catalog import CollectionCatalogService
from niamoto.core.collections.models import CollectionCatalogEntry
from niamoto.core.collections.widget_proposal_models import (
    ChartFitResult,
    ProposalProvenance,
    ProposalScore,
    TransformedShape,
    TransformationCandidate,
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
from niamoto.gui.api.services.collection_widget_proposal_models import (
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
    save_transform_and_export_configs,
)


@dataclass(frozen=True)
class _SourceAnalysis:
    profiles: list[EnrichedColumnProfile]
    class_objects: list[ClassObjectStats]
    multi_field_patterns: list[MultiFieldPattern]


@dataclass(frozen=True)
class _SourceAnalysisCacheKey:
    db_path: str
    source_name: str
    mtime_ns: int


_SOURCE_ANALYSIS_CACHE_LOCK = threading.RLock()
_SOURCE_ANALYSIS_CACHE: dict[_SourceAnalysisCacheKey, _SourceAnalysis] = {}
_SKIPPED_SAMPLE_COLUMN_TYPES = ("BLOB", "BYTEA", "BINARY")


@dataclass(frozen=True)
class _ExistingWidgetSignatures:
    transform: set[str]
    export: set[str]

    @property
    def has_any(self) -> bool:
        return bool(self.transform or self.export)


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
        existing_keys = self._existing_widget_keys(collection.name)
        groups = self.proposal_service.generate_for_collection(
            collection=collection.name,
            source_name=source_name,
            profiles=analysis.profiles,
            class_objects=analysis.class_objects,
            multi_field_patterns=analysis.multi_field_patterns,
            existing_proposal_keys=existing_keys,
        )
        for proposal in self._foundational_widget_proposals(
            collection,
            source_name,
            existing_keys,
        )[::-1]:
            self._append_proposal(groups, proposal, prepend=True)
        groups = self._mark_existing_equivalent_proposals(groups, collection.name)
        self._prioritize_page_structure(groups)
        groups.partial = bool(groups.skipped or groups.missing_chart)
        return groups

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
            transform_changes = [
                change for change in applicable if change.transform_widget
            ]
            if transform_changes:
                group = find_or_create_transform_group(
                    transform_config, collection_name
                )
                if any(
                    self._transform_requires_source_relation(
                        collection_name,
                        change.transform_widget,
                    )
                    for change in transform_changes
                ):
                    group["sources"] = self._merged_sources(
                        group.get("sources", []), collection_name
                    )
                else:
                    group.setdefault("sources", group.get("sources", []))
                widgets_data = group.setdefault("widgets_data", {})

                for change in transform_changes:
                    transform_widget = dict(change.transform_widget)
                    transform_widget.pop("export_override", None)
                    widgets_data[change.widget_id] = transform_widget

            validated_transform = validate_transform_config(transform_config)
            updated_export = self._build_export_config(
                export_config,
                collection_name,
                applicable,
            )

            transform_backup, export_backup = save_transform_and_export_configs(
                self.work_dir,
                validated_transform,
                updated_export,
                create_backup=True,
            )

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

        transform_widget, export_widget = self._config_for_proposal(proposal)
        if source_relation_error and self._transform_requires_source_relation(
            proposal.collection,
            transform_widget,
        ):
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
    ) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        recipe = proposal.recipe
        transformer = recipe.get("transformer", {})
        widget = recipe.get("widget", {})
        transform_widget = None
        if transformer.get("plugin"):
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

    def _transform_requires_source_relation(
        self,
        collection_name: str,
        transform_widget: dict[str, Any] | None,
    ) -> bool:
        if not transform_widget:
            return False

        plugin = transform_widget.get("plugin")
        if plugin != "field_aggregator":
            return True

        collection = self.catalog_service.get_collection(collection_name)
        group_sources = {collection.name, collection.source_name, None, ""}
        params = transform_widget.get("params") or {}
        fields = params.get("fields") or []
        if not isinstance(fields, list):
            return True

        for field in fields:
            if not isinstance(field, dict):
                continue
            source = field.get("source")
            if source not in group_sources:
                return True
        return False

    def _foundational_widget_proposals(
        self,
        collection: CollectionCatalogEntry,
        source_name: str,
        existing_keys: set[str],
    ) -> list[WidgetProposal]:
        """Return collection page essentials not derived from raw field scoring."""

        if collection.source_type != "reference":
            return []

        context = self._reference_context(collection)
        proposals = [self._navigation_proposal(collection, context, existing_keys)]
        general_info = self._general_info_proposal(
            collection,
            source_name,
            context,
            existing_keys,
        )
        if general_info is not None:
            proposals.append(general_info)
        return proposals

    def _reference_context(
        self,
        collection: CollectionCatalogEntry,
    ) -> dict[str, Any]:
        """Inspect a reference table enough to configure page-level widgets."""

        reference_name = collection.source_name
        columns: list[str] = []
        table_name = None
        sample_df = pd.DataFrame()

        if self.db_path is not None and self.db_path.exists():
            db = Database(str(self.db_path), read_only=True)
            try:
                table_name = resolve_reference_table(db, reference_name)
                if table_name and db.has_table(table_name):
                    columns = db.get_table_columns(table_name)
                    if columns:
                        safe_columns = [
                            column
                            for column in columns
                            if not column.lower().endswith("_geom")
                        ]
                        if safe_columns:
                            select_sql = ", ".join(
                                quote_identifier(db, column) for column in safe_columns
                            )
                            sample_df = pd.read_sql(
                                f"SELECT {select_sql} FROM {quote_identifier(db, table_name)} LIMIT 100",
                                db.engine,
                            )
            finally:
                db.close()

        schema = {}
        references = self.import_config.get("entities", {}).get("references", {})
        reference_config = references.get(reference_name, {})
        if isinstance(reference_config, dict):
            maybe_schema = reference_config.get("schema", {})
            if isinstance(maybe_schema, dict):
                schema = maybe_schema

        id_field = str(schema.get("id_field") or "id")
        name_field = str(schema.get("name_field") or "")
        if columns:
            id_field = self._pick_identifier_column(columns, preferred=id_field)
            name_field = self._pick_name_column(columns, id_field, name_field)
        elif not name_field:
            name_field = "name"

        left_field = self._schema_value(
            schema,
            "left_field",
            "lft_field",
            "left",
            default="lft",
        )
        right_field = self._schema_value(
            schema,
            "right_field",
            "rght_field",
            "right",
            default="rght",
        )
        parent_field = self._schema_value(
            schema,
            "parent_id_field",
            "parent_field",
            "parent",
            default="parent_id",
        )
        level_field = self._schema_value(
            schema,
            "level_field",
            "level",
            default="level",
        )
        columns_set = set(columns)
        return {
            "table_name": table_name,
            "columns": columns,
            "sample_df": sample_df,
            "id_field": id_field,
            "name_field": name_field,
            "left_field": left_field,
            "right_field": right_field,
            "parent_field": parent_field,
            "level_field": level_field,
            "has_nested_set": {left_field, right_field} <= columns_set,
            "has_parent": parent_field in columns_set,
            "has_level": level_field in columns_set,
        }

    def _schema_value(
        self,
        schema: dict[str, Any],
        *keys: str,
        default: str,
    ) -> str:
        for key in keys:
            value = schema.get(key)
            if value:
                return str(value)

        fields = schema.get("fields")
        if isinstance(fields, dict):
            for key in keys:
                value = fields.get(key)
                if value:
                    return str(value)

        return default

    def _navigation_proposal(
        self,
        collection: CollectionCatalogEntry,
        context: dict[str, Any],
        existing_keys: set[str],
    ) -> WidgetProposal:
        proposal_id = f"{collection.name}_hierarchical_nav_widget"
        status = "already_configured" if proposal_id in existing_keys else "recommended"
        nav_params = {
            "referential_data": collection.source_name,
            "id_field": context["id_field"],
            "name_field": context["name_field"],
            "base_url": f"{{{{ depth }}}}{collection.name}/",
            "show_search": True,
        }
        if context.get("has_nested_set"):
            nav_params["lft_field"] = context.get("left_field") or "lft"
            nav_params["rght_field"] = context.get("right_field") or "rght"
        if context.get("has_parent"):
            nav_params["parent_id_field"] = context.get("parent_field") or "parent_id"
        if context.get("has_level"):
            nav_params["level_field"] = context.get("level_field") or "level"

        shape = TransformedShape(
            kind="table",
            columns=list(context.get("columns") or []),
            metadata={"foundational": True, "page_widget": "navigation"},
        )
        candidate = TransformationCandidate(
            id=proposal_id,
            collection=collection.name,
            origin="template_suggestion",
            source_name=collection.source_name,
            field_names=[context["id_field"], context["name_field"]],
            intent="Add collection navigation",
            shape=shape,
            freshness="current",
            reconstructability="full",
            provenance=ProposalProvenance(
                source="template_suggestion",
                source_name=collection.source_name,
                field_names=[context["id_field"], context["name_field"]],
                evidence=["reference collection navigation"],
            ),
        )
        return WidgetProposal(
            id=proposal_id,
            collection=collection.name,
            title=f"Navigation {collection.name.replace('_', ' ').title()}",
            status=status,
            candidate=candidate,
            shape=shape,
            primary_fit=ChartFitResult(
                widget="hierarchical_nav_widget",
                status="primary",
                score=0.95,
                reason="Reference collections need detail-page navigation.",
                params=nav_params,
                rank=1,
            ),
            score=ProposalScore(
                dimensions={
                    "utility": 0.95,
                    "evidence": 0.9,
                    "coverage": 1.0,
                    "cardinality": 0.85,
                    "chart_fit": 0.95,
                    "provenance": 0.9,
                    "reconstructability": 1.0,
                },
                weights={},
            ),
            applyability="not_applicable"
            if status == "already_configured"
            else "applicable",
            fingerprint=proposal_id,
            recipe={
                "widget": {"plugin": "hierarchical_nav_widget", "params": nav_params}
            },
            details={"foundational": True},
        )

    def _general_info_proposal(
        self,
        collection: CollectionCatalogEntry,
        source_name: str,
        context: dict[str, Any],
        existing_keys: set[str],
    ) -> WidgetProposal | None:
        field_configs = self._general_info_fields(collection, source_name, context)
        if len(field_configs) < 2:
            return None

        proposal_id = f"general_info_{collection.name}_field_aggregator_info_grid"
        status = "already_configured" if proposal_id in existing_keys else "recommended"
        item_params = [
            {
                "label": _humanize_label(str(field["target"])),
                "source": str(field["target"]),
                **(
                    {"format": "number"}
                    if field.get("transformation") == "count"
                    else {}
                ),
            }
            for field in field_configs
        ]
        widget_params = {
            "items": item_params,
            "grid_columns": min(max(len(item_params), 1), 3),
        }
        transformer_params = {"fields": field_configs}
        shape = TransformedShape(
            kind="metric_group",
            metric_count=len(field_configs),
            columns=[str(field["target"]) for field in field_configs],
            metadata={"foundational": True, "page_widget": "general_info"},
        )
        candidate = TransformationCandidate(
            id=proposal_id,
            collection=collection.name,
            origin="template_suggestion",
            source_name=collection.source_name,
            field_names=[str(field["field"]) for field in field_configs],
            transformer_plugin="field_aggregator",
            transformer_config=transformer_params,
            intent="Add general information panel",
            shape=shape,
            freshness="current",
            reconstructability="full",
            provenance=ProposalProvenance(
                source="template_suggestion",
                source_name=collection.source_name,
                field_names=[str(field["field"]) for field in field_configs],
                evidence=["reference summary fields"],
            ),
        )
        return WidgetProposal(
            id=proposal_id,
            collection=collection.name,
            title="Informations générales",
            status=status,
            candidate=candidate,
            shape=shape,
            primary_fit=ChartFitResult(
                widget="info_grid",
                status="primary",
                score=0.9,
                reason="Readable for compact identity and count fields.",
                params=widget_params,
                rank=1,
            ),
            score=ProposalScore(
                dimensions={
                    "utility": 0.92,
                    "evidence": 0.86,
                    "coverage": 0.9,
                    "cardinality": 0.9,
                    "chart_fit": 0.9,
                    "provenance": 0.86,
                    "reconstructability": 1.0,
                },
                weights={},
            ),
            applyability="not_applicable"
            if status == "already_configured"
            else "applicable",
            fingerprint=proposal_id,
            recipe={
                "transformer": {
                    "plugin": "field_aggregator",
                    "params": transformer_params,
                },
                "widget": {"plugin": "info_grid", "params": widget_params},
            },
            details={"foundational": True},
        )

    def _general_info_fields(
        self,
        collection: CollectionCatalogEntry,
        source_name: str,
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        sample_df = context.get("sample_df")
        if not isinstance(sample_df, pd.DataFrame) or sample_df.empty:
            return []

        fields: list[dict[str, Any]] = []
        preferred = [
            context.get("name_field"),
            "full_name",
            "name",
            "label",
            "rank",
            "rank_name",
            "type",
            "category",
        ]
        for column in preferred:
            if column and column in sample_df.columns:
                self._append_general_info_field(fields, collection.source_name, column)
            if len(fields) >= 5:
                break

        if len(fields) < 5:
            scored_columns = self._score_general_info_columns(sample_df, context)
            for column, _score in scored_columns:
                self._append_general_info_field(fields, collection.source_name, column)
                if len(fields) >= 5:
                    break

        count_field = self._count_field_for_source(source_name)
        if count_field and self._can_read_related_source(collection, source_name):
            fields.append(
                {
                    "source": source_name,
                    "field": count_field,
                    "target": f"{source_name}_count",
                    "transformation": "count",
                }
            )

        return fields[:6]

    def _can_read_related_source(
        self,
        collection: CollectionCatalogEntry,
        source_name: str,
    ) -> bool:
        if source_name == collection.source_name:
            return True
        existing_sources = self._existing_sources_for_collection(collection.name)
        source_config = self._source_config_for_collection(
            collection,
            source_name,
            existing_sources,
        )
        return source_config is not None

    def _append_general_info_field(
        self,
        fields: list[dict[str, Any]],
        source: str,
        column: str,
    ) -> None:
        target = _slug_key(column)
        if any(field.get("target") == target for field in fields):
            return
        fields.append({"source": source, "field": column, "target": target})

    def _score_general_info_columns(
        self,
        sample_df: pd.DataFrame,
        context: dict[str, Any],
    ) -> list[tuple[str, float]]:
        excluded = {
            "id",
            "parent",
            str(context.get("id_field") or ""),
            str(context.get("left_field") or ""),
            str(context.get("right_field") or ""),
            str(context.get("level_field") or ""),
            str(context.get("parent_field") or ""),
        }
        scored: list[tuple[str, float]] = []
        for column in sample_df.columns:
            column_lower = str(column).lower()
            if column_lower in excluded:
                continue
            if column_lower.startswith("id_") or column_lower.endswith(
                ("_id", "_geom")
            ):
                continue

            non_null = sample_df[column].dropna()
            if non_null.empty:
                continue
            null_ratio = 1 - (len(non_null) / len(sample_df))
            if null_ratio > 0.8:
                continue

            score = 1 - null_ratio
            if any(
                token in column_lower
                for token in ("name", "label", "type", "rank", "status", "category")
            ):
                score += 0.5
            if non_null.nunique() <= max(20, len(non_null) * 0.5):
                score += 0.2
            scored.append((str(column), score))

        return sorted(scored, key=lambda item: (-item[1], item[0]))

    def _count_field_for_source(self, source_name: str) -> str | None:
        if self.db_path is None or not self.db_path.exists():
            return None

        db = Database(str(self.db_path), read_only=True)
        try:
            table_name = resolve_dataset_table(db, source_name)
            if not table_name:
                return None
            columns = db.get_table_columns(table_name)
        finally:
            db.close()

        if not columns:
            return None
        return self._id_field_for_entity(source_name) or columns[0]

    def _append_proposal(
        self,
        groups: WidgetProposalGroups,
        proposal: WidgetProposal,
        *,
        prepend: bool = False,
    ) -> None:
        def add(target: list[WidgetProposal]) -> None:
            if prepend:
                target.insert(0, proposal)
            else:
                target.append(proposal)

        if proposal.status == "recommended":
            add(groups.recommended)
        elif proposal.status == "warning":
            add(groups.warnings)
        elif proposal.status == "missing_chart":
            add(groups.missing_chart)
        elif proposal.status == "skipped":
            add(groups.skipped)
        elif proposal.status == "already_configured":
            add(groups.already_configured)
        else:
            add(groups.review_only)

    def _prioritize_page_structure(self, groups: WidgetProposalGroups) -> None:
        """Keep page structure widgets ahead of analytical charts."""

        for group_name in (
            "recommended",
            "warnings",
            "review_only",
            "already_configured",
        ):
            proposals = getattr(groups, group_name)
            proposals.sort(key=_page_structure_priority)

    def _mark_existing_equivalent_proposals(
        self,
        groups: WidgetProposalGroups,
        collection_name: str,
    ) -> WidgetProposalGroups:
        """Move proposals whose generated config already exists to configured."""

        existing_signatures = self._existing_widget_signatures(collection_name)
        if not existing_signatures.has_any:
            return groups

        next_groups = WidgetProposalGroups(
            collection=groups.collection,
            partial=groups.partial,
            messages=list(groups.messages),
        )
        for proposal in groups.all_proposals():
            marked = proposal
            if (
                proposal.status != "already_configured"
                and self._proposal_is_already_configured(proposal, existing_signatures)
            ):
                marked = proposal.model_copy(
                    update={
                        "status": "already_configured",
                        "applyability": "not_applicable",
                    }
                )
            self._append_proposal(next_groups, marked)
        return next_groups

    def _existing_widget_signatures(
        self,
        collection_name: str,
    ) -> _ExistingWidgetSignatures:
        transform_signatures: set[str] = set()
        export_signatures: set[str] = set()
        for widget in self._existing_transform_widgets(collection_name).values():
            if isinstance(widget, dict):
                signature = self._transform_widget_signature(widget)
                if signature:
                    transform_signatures.add(signature)

        for widget in self._existing_export_widgets(collection_name):
            signature = self._export_widget_signature(widget)
            if signature:
                export_signatures.add(signature)
        return _ExistingWidgetSignatures(
            transform=transform_signatures,
            export=export_signatures,
        )

    def _proposal_is_already_configured(
        self,
        proposal: WidgetProposal,
        existing_signatures: _ExistingWidgetSignatures,
    ) -> bool:
        transform_widget, export_widget = self._config_for_proposal(proposal)
        export_signature = (
            self._export_widget_signature(export_widget) if export_widget else None
        )
        if transform_widget:
            transform_signature = self._transform_widget_signature(transform_widget)
            return bool(
                transform_signature
                and export_signature
                and transform_signature in existing_signatures.transform
                and export_signature in existing_signatures.export
            )
        return bool(export_signature and export_signature in existing_signatures.export)

    def _transform_widget_signature(self, widget: dict[str, Any]) -> str | None:
        plugin = widget.get("plugin")
        if not plugin:
            return None
        params = widget.get("params") if isinstance(widget.get("params"), dict) else {}
        return f"transform:{plugin}:{_stable_config_key(params)}"

    def _export_widget_signature(self, widget: dict[str, Any]) -> str | None:
        plugin = widget.get("plugin")
        if not plugin:
            return None
        params = widget.get("params") if isinstance(widget.get("params"), dict) else {}
        return f"export:{plugin}:{_stable_config_key(params)}"

    def _pick_identifier_column(
        self,
        columns: Sequence[str],
        *,
        preferred: str | None = None,
    ) -> str:
        if preferred and preferred in columns:
            return preferred
        for candidate in ("id", "uuid", "identifier", "gid"):
            if candidate in columns:
                return candidate
        return str(columns[0]) if columns else "id"

    def _pick_name_column(
        self,
        columns: Sequence[str],
        id_field: str,
        preferred: str | None = None,
    ) -> str:
        if preferred and preferred in columns:
            return preferred
        for candidate in ("full_name", "display_name", "name", "label", "title"):
            if candidate in columns and candidate != id_field:
                return candidate
        for column in columns:
            if column != id_field:
                return str(column)
        return id_field

    def _analysis_for_source(self, source_name: str) -> _SourceAnalysis:
        if self.db_path is None or not self.db_path.exists():
            return _SourceAnalysis([], [], [])

        cache_key = _SourceAnalysisCacheKey(
            db_path=str(self.db_path.resolve()),
            source_name=source_name,
            mtime_ns=self.db_path.stat().st_mtime_ns,
        )
        with _SOURCE_ANALYSIS_CACHE_LOCK:
            cached = _SOURCE_ANALYSIS_CACHE.get(cache_key)
            if cached is not None:
                return cached

        db = Database(str(self.db_path), read_only=True)
        analysis = _SourceAnalysis([], [], [])
        try:
            table_name = resolve_dataset_table(db, source_name)
            if table_name:
                sample_columns = self._sample_columns_for_table(db, table_name)
                if sample_columns:
                    select_list = ", ".join(
                        quote_identifier(db, column_name)
                        for column_name in sample_columns
                    )
                    query = f"SELECT {select_list} FROM {quote_identifier(db, table_name)} LIMIT 5000"
                    sample_df = pd.read_sql(query, db.engine)
                    if not sample_df.empty:
                        dataset_profile = DataProfiler().profile_dataframe(
                            sample_df,
                            Path(table_name),
                            total_count=len(sample_df),
                        )
                        analyzer = DataAnalyzer()
                        profiles = [
                            analyzer.enrich_profile(
                                column_profile,
                                sample_df[column_profile.name],
                            )
                            for column_profile in dataset_profile.columns
                            if column_profile.name in sample_df.columns
                        ]
                        analysis = _SourceAnalysis(
                            profiles=profiles,
                            class_objects=self._class_objects_for_sample(sample_df),
                            multi_field_patterns=MultiFieldPatternDetector().suggest_for_selection(
                                profiles,
                                source_name,
                            ),
                        )
        finally:
            db.close()

        with _SOURCE_ANALYSIS_CACHE_LOCK:
            _SOURCE_ANALYSIS_CACHE[cache_key] = analysis
        return analysis

    def _sample_columns_for_table(self, db: Database, table_name: str) -> list[str]:
        try:
            describe_df = pd.read_sql(
                f"DESCRIBE SELECT * FROM {quote_identifier(db, table_name)}",
                db.engine,
            )
        except Exception:
            return []

        columns: list[str] = []
        for row in describe_df.to_dict("records"):
            column_name = row.get("column_name")
            column_type = str(row.get("column_type") or "").upper()
            if not column_name:
                continue
            if any(skipped in column_type for skipped in _SKIPPED_SAMPLE_COLUMN_TYPES):
                continue
            columns.append(str(column_name))
        return columns

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
        return {
            *self._existing_transform_widgets(collection_name),
            *self._existing_export_widget_keys(collection_name),
        }

    def _existing_transform_widgets(self, collection_name: str) -> dict[str, Any]:
        for group in self.transform_config:
            if isinstance(group, dict) and group.get("group_by") == collection_name:
                widgets = group.get("widgets_data", {})
                return widgets if isinstance(widgets, dict) else {}
        return {}

    def _existing_export_widget_keys(self, collection_name: str) -> set[str]:
        keys: set[str] = set()
        for widget in self._existing_export_widgets(collection_name):
            data_source = widget.get("data_source")
            if data_source:
                keys.add(str(data_source))
            elif widget.get("plugin") == "hierarchical_nav_widget":
                keys.add(f"{collection_name}_hierarchical_nav_widget")
        return keys

    def _existing_export_widgets(self, collection_name: str) -> list[dict[str, Any]]:
        widgets: list[dict[str, Any]] = []
        exports = (
            self.export_config.get("exports", [])
            if isinstance(self.export_config, dict)
            else []
        )
        for export in exports:
            if not isinstance(export, dict):
                continue
            for group in self._iter_export_groups(export):
                if (
                    not isinstance(group, dict)
                    or group.get("group_by") != collection_name
                ):
                    continue
                for widget in group.get("widgets", []) or []:
                    if isinstance(widget, dict):
                        widgets.append(widget)
        return widgets

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
                "grouping": collection.source_name,
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
        groups = self._export_group_container_for_collection(
            html_exporter,
            collection_name,
        )
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

    def _iter_export_groups(self, export: dict[str, Any]):
        root_groups = export.get("groups", [])
        if isinstance(root_groups, list):
            yield from root_groups
        params = export.get("params", {})
        if isinstance(params, dict):
            params_groups = params.get("groups", [])
            if isinstance(params_groups, list):
                yield from params_groups

    def _export_group_container_for_collection(
        self,
        export: dict[str, Any],
        collection_name: str,
    ) -> list[dict[str, Any]]:
        for container in self._export_group_containers(export):
            if any(
                isinstance(group, dict) and group.get("group_by") == collection_name
                for group in container
            ):
                return container

        groups = export.get("groups")
        if isinstance(groups, list):
            return groups
        groups = []
        export["groups"] = groups
        return groups

    def _export_group_containers(
        self,
        export: dict[str, Any],
    ) -> list[list[dict[str, Any]]]:
        containers: list[list[dict[str, Any]]] = []
        root_groups = export.get("groups")
        if isinstance(root_groups, list):
            containers.append(root_groups)
        params = export.get("params")
        if isinstance(params, dict):
            params_groups = params.get("groups")
            if isinstance(params_groups, list):
                containers.append(params_groups)
        return containers

    def _find_or_create_export_group(
        self,
        groups: list[dict[str, Any]],
        collection_name: str,
    ) -> dict[str, Any]:
        for group in groups:
            if isinstance(group, dict) and group.get("group_by") == collection_name:
                return group

        path_segment = _slug_key(collection_name)
        group = {
            "group_by": collection_name,
            "output_pattern": f"{path_segment}/{{id}}.html",
            "index_output_pattern": f"{path_segment}/index.html",
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


def _stable_config_key(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _page_structure_priority(proposal: WidgetProposal) -> int:
    page_widget = proposal.shape.metadata.get("page_widget")
    if page_widget == "navigation":
        return 0
    if page_widget == "general_info":
        return 1
    if proposal.shape.kind == "map_layer":
        return 2
    if proposal.primary_fit and proposal.primary_fit.widget == "interactive_map":
        return 2
    return 10


def _humanize_label(value: str) -> str:
    return value.replace("_", " ").strip().title()
