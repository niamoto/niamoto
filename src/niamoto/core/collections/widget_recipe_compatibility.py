"""Read-only compatibility checks for configured widget recipes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from niamoto.core.collections.chart_fit import (
    MAX_COMFORTABLE_LABEL_LENGTH,
    MAX_DONUT_CATEGORIES,
    MAX_READABLE_BAR_CATEGORIES,
)

WidgetImpactStatus = Literal[
    "still_valid",
    "degraded",
    "broken",
    "newly_available",
    "unknown",
]


@dataclass(frozen=True)
class IncomingColumnProfile:
    """Lightweight profile for one incoming source column."""

    name: str
    type: str
    cardinality: int | None = None
    coverage: float | None = None
    label_max_length: int | None = None


@dataclass(frozen=True)
class IncomingDataProfile:
    """Read-only profile of incoming data used for pre-import prediction."""

    columns: dict[str, IncomingColumnProfile]

    @property
    def column_names(self) -> set[str]:
        return set(self.columns)


@dataclass(frozen=True)
class WidgetRecipeImpact:
    """Compatibility result for one configured widget recipe."""

    widget_id: str
    collection: str
    status: WidgetImpactStatus
    detail: str
    affected_columns: list[str] = field(default_factory=list)
    transformer_plugin: str | None = None
    widget_plugin: str | None = None


@dataclass(frozen=True)
class WidgetCompatibilityReport:
    """Widget impact report attached to a pre-import compatibility check."""

    entity_name: str
    impacts: list[WidgetRecipeImpact] = field(default_factory=list)
    repair_context: dict[str, Any] = field(default_factory=dict)

    @property
    def summary(self) -> dict[str, int]:
        counts = {
            "still_valid": 0,
            "degraded": 0,
            "broken": 0,
            "newly_available": 0,
            "unknown": 0,
        }
        for impact in self.impacts:
            counts[impact.status] += 1
        return counts


@dataclass(frozen=True)
class _WidgetRecipe:
    widget_id: str
    collection: str
    source_name: str | None
    transformer_plugin: str
    widget_plugin: str | None
    fields: list[str]
    primary_field: str | None = None


class WidgetRecipeCompatibilityService:
    """Classify configured widget recipes against an incoming data profile."""

    CLASS_OBJECT_STRUCTURAL_COLUMNS = {
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
    SIMPLE_FIELD_PARAMS = {
        "top_ranking": ("field", "aggregate_field"),
        "binned_distribution": ("field",),
        "binary_counter": ("field",),
        "statistical_summary": ("field",),
        "categorical_distribution": ("field",),
        "geospatial_extractor": ("field",),
        "shape_processor": ("field",),
    }

    def __init__(
        self,
        *,
        transform_config: list[dict[str, Any]],
        export_config: dict[str, Any] | None = None,
    ) -> None:
        self.transform_config = transform_config
        self.export_config = export_config or {}

    def classify(
        self,
        entity_name: str,
        incoming_profile: IncomingDataProfile,
        *,
        old_column_names: set[str] | None = None,
    ) -> WidgetCompatibilityReport:
        """Classify configured widgets and simple new opportunities."""

        recipes = [
            recipe
            for recipe in self._iter_recipes()
            if recipe.source_name == entity_name
        ]
        impacts = [
            self._classify_recipe(recipe, incoming_profile) for recipe in recipes
        ]
        impacts.extend(
            self._newly_available_impacts(
                entity_name,
                incoming_profile,
                recipes,
                old_column_names=old_column_names,
            )
        )
        return WidgetCompatibilityReport(
            entity_name=entity_name,
            impacts=impacts,
            repair_context={
                "entity": entity_name,
                "collections": sorted({recipe.collection for recipe in recipes}),
                "schema_fingerprint": self._schema_fingerprint(incoming_profile),
            },
        )

    def _classify_recipe(
        self,
        recipe: _WidgetRecipe,
        incoming_profile: IncomingDataProfile,
    ) -> WidgetRecipeImpact:
        if not incoming_profile.columns:
            return WidgetRecipeImpact(
                widget_id=recipe.widget_id,
                collection=recipe.collection,
                status="unknown",
                detail="Incoming data could not be profiled before import.",
                affected_columns=list(recipe.fields),
                transformer_plugin=recipe.transformer_plugin,
                widget_plugin=recipe.widget_plugin,
            )

        if not recipe.fields:
            return WidgetRecipeImpact(
                widget_id=recipe.widget_id,
                collection=recipe.collection,
                status="unknown",
                detail="Widget source fields could not be inferred from the recipe.",
                transformer_plugin=recipe.transformer_plugin,
                widget_plugin=recipe.widget_plugin,
            )

        missing = [
            field_name
            for field_name in recipe.fields
            if field_name not in incoming_profile.columns
        ]
        if missing:
            return WidgetRecipeImpact(
                widget_id=recipe.widget_id,
                collection=recipe.collection,
                status="broken",
                detail="Required source field is missing in the incoming data.",
                affected_columns=missing,
                transformer_plugin=recipe.transformer_plugin,
                widget_plugin=recipe.widget_plugin,
            )

        degraded_reason = self._degraded_reason(recipe, incoming_profile)
        if degraded_reason:
            return WidgetRecipeImpact(
                widget_id=recipe.widget_id,
                collection=recipe.collection,
                status="degraded",
                detail=degraded_reason,
                affected_columns=list(recipe.fields),
                transformer_plugin=recipe.transformer_plugin,
                widget_plugin=recipe.widget_plugin,
            )

        return WidgetRecipeImpact(
            widget_id=recipe.widget_id,
            collection=recipe.collection,
            status="still_valid",
            detail="Required source fields are present and chart readability checks passed.",
            affected_columns=list(recipe.fields),
            transformer_plugin=recipe.transformer_plugin,
            widget_plugin=recipe.widget_plugin,
        )

    def _degraded_reason(
        self,
        recipe: _WidgetRecipe,
        incoming_profile: IncomingDataProfile,
    ) -> str | None:
        if not recipe.fields:
            return None

        primary_field_name = recipe.primary_field or recipe.fields[0]
        primary_field = incoming_profile.columns.get(primary_field_name)
        if primary_field is None:
            return None

        cardinality = primary_field.cardinality
        label_max_length = primary_field.label_max_length
        widget_plugin = recipe.widget_plugin

        if widget_plugin == "donut_chart" and cardinality is not None:
            if cardinality > MAX_DONUT_CATEGORIES:
                return (
                    "Incoming cardinality is too high for a readable donut chart; "
                    "review a bar or ranking widget instead."
                )

        if widget_plugin == "bar_plot" and cardinality is not None:
            if cardinality > MAX_READABLE_BAR_CATEGORIES:
                return (
                    "Incoming cardinality is high enough to require ranking, grouping, "
                    "or scrolling before rendering."
                )

        if (
            label_max_length is not None
            and label_max_length > MAX_COMFORTABLE_LABEL_LENGTH
        ):
            return "Incoming labels may be too long for the configured chart."

        if primary_field.coverage is not None and primary_field.coverage < 0.1:
            return "Incoming field coverage is too low for a useful widget."

        return None

    def _newly_available_impacts(
        self,
        entity_name: str,
        incoming_profile: IncomingDataProfile,
        recipes: list[_WidgetRecipe],
        *,
        old_column_names: set[str] | None = None,
    ) -> list[WidgetRecipeImpact]:
        referenced_fields = {
            field_name for recipe in recipes for field_name in recipe.fields
        }
        target_collections = sorted({recipe.collection for recipe in recipes}) or [
            entity_name
        ]
        impacts = []
        for column_name, profile in sorted(incoming_profile.columns.items()):
            if old_column_names is not None and column_name in old_column_names:
                continue
            if column_name in referenced_fields:
                continue
            if profile.coverage is not None and profile.coverage < 0.5:
                continue
            if profile.type == "unknown":
                continue
            for collection in target_collections:
                impacts.append(
                    WidgetRecipeImpact(
                        widget_id=f"new:{entity_name}:{column_name}",
                        collection=collection,
                        status="newly_available",
                        detail="Incoming field is not used by current widget recipes.",
                        affected_columns=[column_name],
                    )
                )
        return impacts

    def _iter_recipes(self) -> list[_WidgetRecipe]:
        export_widgets = self._export_widgets_by_source()
        recipes: list[_WidgetRecipe] = []
        for group in self.transform_config:
            if not isinstance(group, dict):
                continue
            collection = str(group.get("group_by") or "")
            for widget_id, widget_cfg in (group.get("widgets_data") or {}).items():
                if not isinstance(widget_cfg, dict):
                    continue
                params = widget_cfg.get("params") or {}
                plugin = str(widget_cfg.get("plugin") or "")
                export_override = widget_cfg.get("export_override") or {}
                widget_plugin = (
                    export_override.get("plugin")
                    if isinstance(export_override, dict)
                    else None
                ) or export_widgets.get((collection, str(widget_id)))
                for source_name, fields in self._source_fields_for_widget(
                    plugin,
                    widget_cfg,
                    params,
                ).items():
                    recipes.append(
                        _WidgetRecipe(
                            widget_id=str(widget_id),
                            collection=collection,
                            source_name=str(source_name) if source_name else None,
                            transformer_plugin=plugin,
                            widget_plugin=widget_plugin,
                            fields=fields,
                            primary_field=self._primary_field_for_widget(
                                plugin,
                                widget_cfg,
                                params,
                                fields,
                            ),
                        )
                    )
        return recipes

    def _primary_field_for_widget(
        self,
        plugin: str,
        widget_cfg: dict[str, Any],
        params: dict[str, Any],
        fields: list[str],
    ) -> str | None:
        if plugin in self.SIMPLE_FIELD_PARAMS:
            value = widget_cfg.get("field") or params.get("field")
            if isinstance(value, str) and value:
                return value

        if plugin == "direct_attribute":
            value = widget_cfg.get("field") or params.get("field")
            if isinstance(value, str) and value:
                return value

        if plugin == "time_series_analysis":
            value = params.get("time_field") or params.get("field")
            if isinstance(value, str) and value:
                return value

        return fields[0] if fields else None

    def _source_fields_for_widget(
        self,
        plugin: str,
        widget_cfg: dict[str, Any],
        params: dict[str, Any],
    ) -> dict[str | None, list[str]]:
        grouped: dict[str | None, set[str]] = {}
        default_source = widget_cfg.get("source") or params.get("source")

        def add(source_name: Any, field_name: Any) -> None:
            if isinstance(field_name, str) and field_name:
                grouped.setdefault(
                    str(source_name) if source_name else None,
                    set(),
                ).add(field_name)

        def add_many(source_name: Any, field_names: list[str]) -> None:
            for field_name in field_names:
                add(source_name, field_name)

        if plugin == "transform_chain":
            for step in params.get("steps") or []:
                if not isinstance(step, dict):
                    continue
                step_plugin = step.get("plugin")
                step_params = step.get("params") or {}
                if not isinstance(step_plugin, str) or not isinstance(
                    step_params,
                    dict,
                ):
                    continue
                step_widget_cfg: dict[str, Any] = {
                    "plugin": step_plugin,
                    "params": step_params,
                }
                step_source = step.get("source") or default_source
                if step_source:
                    step_widget_cfg["source"] = step_source
                for source_name, fields in self._source_fields_for_widget(
                    step_plugin,
                    step_widget_cfg,
                    step_params,
                ).items():
                    add_many(source_name, fields)

        for param_name in self.SIMPLE_FIELD_PARAMS.get(plugin, ()):
            value = widget_cfg.get(param_name) or params.get(param_name)
            add(default_source, value)

        if plugin == "direct_attribute":
            add(default_source, widget_cfg.get("field") or params.get("field"))

        if plugin == "time_series_analysis":
            for field_name in ("field", "time_field"):
                add(default_source, params.get(field_name))
            for column in (params.get("fields") or {}).values():
                add(default_source, column)
            for column in params.get("value_fields") or []:
                add(default_source, column)

        if plugin == "field_aggregator":
            for field_cfg in params.get("fields") or []:
                if isinstance(field_cfg, dict):
                    add(
                        field_cfg.get("source") or default_source,
                        field_cfg.get("field"),
                    )

        if plugin == "geospatial_extractor":
            for field_name in ("properties", "children_properties"):
                for column in params.get(field_name) or []:
                    add(default_source, column)
            hierarchy_config = params.get("hierarchy_config") or {}
            if isinstance(hierarchy_config, dict):
                for field_name in (
                    "type_field",
                    "parent_field",
                    "left_field",
                    "right_field",
                ):
                    add(default_source, hierarchy_config.get(field_name))

        structural_columns = self.CLASS_OBJECT_STRUCTURAL_COLUMNS.get(plugin)
        if structural_columns:
            if plugin == "class_object_field_aggregator":
                for field_cfg in params.get("fields") or []:
                    if isinstance(field_cfg, dict):
                        add_many(
                            field_cfg.get("source") or default_source,
                            list(structural_columns),
                        )
            else:
                add_many(default_source, list(structural_columns))

        if plugin == "class_object_series_extractor":
            for field_name in ("size_field", "value_field"):
                field_cfg = params.get(field_name) or {}
                if isinstance(field_cfg, dict):
                    add(default_source, field_cfg.get("input"))

        if plugin in {
            "class_object_series_matrix_extractor",
            "class_object_series_by_axis_extractor",
        }:
            axis = params.get("axis") or {}
            if isinstance(axis, dict):
                add(default_source, axis.get("field"))

        if not grouped:
            grouped[default_source if isinstance(default_source, str) else None] = set()

        return {source: sorted(fields) for source, fields in grouped.items()}

    def _export_widgets_by_source(self) -> dict[tuple[str, str], str]:
        result: dict[tuple[str, str], str] = {}
        for export in self.export_config.get("exports", []) or []:
            if not isinstance(export, dict):
                continue
            for groups in (
                export.get("groups", []),
                (export.get("params") or {}).get("groups", [])
                if isinstance(export.get("params"), dict)
                else [],
            ):
                if not isinstance(groups, list):
                    continue
                for group in groups:
                    if not isinstance(group, dict):
                        continue
                    collection = str(group.get("group_by") or "")
                    for widget in group.get("widgets", []) or []:
                        if not isinstance(widget, dict):
                            continue
                        data_source = widget.get("data_source")
                        plugin = widget.get("plugin")
                        if data_source and plugin:
                            result[(collection, str(data_source))] = str(plugin)
        return result

    def _schema_fingerprint(self, incoming_profile: IncomingDataProfile) -> str:
        parts = [
            f"{name}:{profile.type}:{profile.cardinality}:{profile.coverage}"
            for name, profile in sorted(incoming_profile.columns.items())
        ]
        return "|".join(parts)
