"""Transformer that normalizes reference enrichment payloads for display widgets."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from niamoto.core.enrichment_display import (
    extract_enrichment_sources,
    infer_display_format,
    resolve_source_path,
)
from niamoto.core.plugins.base import PluginType, TransformerPlugin, register
from niamoto.core.plugins.models import BasePluginParams, PluginConfig


DisplayFormat = Literal["text", "number", "badge", "link", "image", "list"]


class EnrichmentProfileItem(BaseModel):
    """Display item referenced from one enrichment source payload."""

    label: str = Field(..., description="Display label")
    path: str = Field(
        ...,
        description="Path relative to extra_data.api_enrichment.sources.<source_id>.data",
    )
    source_id: Optional[str] = Field(
        default=None,
        description="Optional source override. Inherits section source when omitted.",
    )
    format: Optional[DisplayFormat] = Field(
        default=None,
        description="Optional display format override",
        json_schema_extra={
            "ui:widget": "select",
            "ui:options": ["text", "number", "badge", "link", "image", "list"],
        },
    )


class EnrichmentProfileSection(BaseModel):
    """Logical section within an enrichment panel."""

    id: str = Field(..., description="Stable section identifier")
    title: str = Field(..., description="Display title")
    source_id: Optional[str] = Field(
        default=None,
        description="Default source for items in this section",
    )
    collapsed: bool = Field(
        default=False,
        description="Whether the section should start collapsed",
        json_schema_extra={"ui:widget": "checkbox"},
    )
    items: List[EnrichmentProfileItem] = Field(
        default_factory=list, description="Items rendered in this section"
    )


class ReferenceEnrichmentProfileParams(BasePluginParams):
    """Parameters for the reference enrichment profile transformer."""

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Build a normalized profile from reference enrichment payloads"
        }
    )

    source: str = Field(
        ...,
        description="Reference source entity name",
        json_schema_extra={
            "ui:widget": "entity-select",
            "ui:entity-filter": {"kind": "reference"},
        },
    )
    summary_items: List[EnrichmentProfileItem] = Field(
        default_factory=list,
        description="Summary items rendered above sections",
    )
    sections: List[EnrichmentProfileSection] = Field(
        default_factory=list,
        description="Sections rendered by the enrichment panel widget",
    )


class ReferenceEnrichmentProfileConfig(PluginConfig):
    """Complete plugin configuration."""

    plugin: Literal["reference_enrichment_profile"] = "reference_enrichment_profile"
    params: ReferenceEnrichmentProfileParams


@register("reference_enrichment_profile", PluginType.TRANSFORMER)
class ReferenceEnrichmentProfile(TransformerPlugin):
    """Normalize enrichment source payloads into a stable widget contract."""

    config_model = ReferenceEnrichmentProfileConfig
    param_schema = ReferenceEnrichmentProfileParams

    output_structure = {
        "summary": "list",
        "sections": "list",
        "sources": "list",
        "meta": "dict",
    }

    def validate_config(
        self, config: Dict[str, Any]
    ) -> ReferenceEnrichmentProfileConfig:
        return self.config_model(**config)

    def _resolve_source_frame(
        self,
        data: Union[pd.DataFrame, Dict[str, Any]],
        source_name: str,
    ) -> Any:
        if isinstance(data, dict):
            if source_name in data:
                return data[source_name]
            if len(data) == 1:
                return next(iter(data.values()))
            return None
        return data

    def _load_extra_data(self, source_data: Any) -> Any:
        if isinstance(source_data, pd.DataFrame):
            if source_data.empty or "extra_data" not in source_data.columns:
                return {}
            return source_data.iloc[0].get("extra_data")

        if isinstance(source_data, dict):
            return source_data.get("extra_data")

        return {}

    def _normalize_item(
        self,
        item: EnrichmentProfileItem,
        sources: dict[str, dict[str, Any]],
        default_source_id: str | None = None,
    ) -> dict[str, Any] | None:
        source_id = item.source_id or default_source_id
        if not source_id:
            return None

        source = sources.get(source_id)
        if not source:
            return None

        value = resolve_source_path(source.get("data"), item.path)
        if value is None:
            return None

        normalized: dict[str, Any] = {
            "id": f"{source_id}:{item.path}",
            "source_id": source_id,
            "source_label": source.get("label") or source_id,
            "label": item.label,
            "value": value,
            "format": item.format or infer_display_format(item.path, [value]),
        }
        return normalized

    def transform(
        self,
        data: Union[pd.DataFrame, Dict[str, Any]],
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        validated = self.validate_config(config)
        source_data = self._resolve_source_frame(data, validated.params.source)
        extra_data = self._load_extra_data(source_data)
        sources = extract_enrichment_sources(extra_data)

        summary = [
            normalized
            for item in validated.params.summary_items
            if (normalized := self._normalize_item(item, sources)) is not None
        ]

        sections = []
        used_source_ids: set[str] = {item["source_id"] for item in summary}
        for section in validated.params.sections:
            normalized_items = [
                normalized
                for item in section.items
                if (
                    normalized := self._normalize_item(
                        item, sources, default_source_id=section.source_id
                    )
                )
                is not None
            ]
            if not normalized_items:
                continue
            used_source_ids.update(item["source_id"] for item in normalized_items)
            section_source = (
                sources.get(section.source_id) if section.source_id else None
            )
            sections.append(
                {
                    "id": section.id,
                    "title": section.title,
                    "source_id": section.source_id,
                    "source_label": (
                        section_source.get("label")
                        if isinstance(section_source, dict)
                        else None
                    ),
                    "collapsed": section.collapsed,
                    "items": normalized_items,
                }
            )

        return {
            "summary": summary,
            "sections": sections,
            "sources": [
                {
                    "id": source_id,
                    "label": sources[source_id].get("label") or source_id,
                }
                for source_id in sorted(used_source_ids)
                if source_id in sources
            ],
            "meta": {
                "visible_sections": len(sections),
                "has_hidden_items": False,
                "source_count": len(used_source_ids),
            },
        }
