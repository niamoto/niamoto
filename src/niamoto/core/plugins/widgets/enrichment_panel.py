"""Widget for rendering structured reference enrichment profiles."""

from __future__ import annotations

import html
import json
import logging
import re
from typing import Any, Literal, Optional, Set

from pydantic import BaseModel, ConfigDict, Field

from niamoto.core.plugins.base import PluginType, WidgetPlugin, register
from niamoto.core.plugins.models import BasePluginParams

logger = logging.getLogger(__name__)

DisplayFormat = Literal["text", "number", "badge", "link", "image", "list"]
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


class EnrichmentPanelItem(BaseModel):
    """Normalized display item produced by the transformer."""

    id: Optional[str] = Field(default=None, description="Stable item identifier")
    source_id: Optional[str] = Field(default=None, description="Origin source id")
    source_label: Optional[str] = Field(
        default=None, description="Human-readable origin source label"
    )
    label: str = Field(..., description="Item label")
    value: Any = Field(default=None, description="Resolved value")
    format: Optional[DisplayFormat] = Field(
        default=None,
        description="Display format",
        json_schema_extra={
            "ui:widget": "select",
            "ui:options": ["text", "number", "badge", "link", "image", "list"],
        },
    )


class EnrichmentPanelSection(BaseModel):
    """Logical section rendered by the widget."""

    id: str = Field(..., description="Stable section identifier")
    title: str = Field(..., description="Section title")
    source_id: Optional[str] = Field(default=None, description="Default source id")
    source_label: Optional[str] = Field(
        default=None, description="Default source label"
    )
    collapsed: bool = Field(
        default=False,
        description="Whether the section should start collapsed",
        json_schema_extra={"ui:widget": "checkbox"},
    )
    items: list[EnrichmentPanelItem] = Field(
        default_factory=list, description="Section items"
    )


class EnrichmentPanelData(BaseModel):
    """Normalized widget input produced by the transformer."""

    summary: list[EnrichmentPanelItem] = Field(
        default_factory=list, description="Summary cards"
    )
    sections: list[EnrichmentPanelSection] = Field(
        default_factory=list, description="Detailed sections"
    )
    sources: list[dict[str, str]] = Field(
        default_factory=list, description="Visible sources"
    )
    meta: dict[str, Any] = Field(default_factory=dict, description="Extra metadata")


class EnrichmentPanelParams(BasePluginParams):
    """Parameters for the enrichment panel widget."""

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Render a compact profile from enriched reference data",
            "examples": [
                {"summary_columns": 3, "show_source_badges": True},
            ],
        }
    )

    summary_columns: int = Field(
        default=3,
        ge=1,
        le=4,
        description="Number of columns used for summary cards",
        json_schema_extra={"ui:widget": "number", "ui:min": 1, "ui:max": 4},
    )
    show_source_badges: bool = Field(
        default=True,
        description="Display source badges on items and sections",
        json_schema_extra={"ui:widget": "checkbox"},
    )
    empty_message: str = Field(
        default="No enrichment data available.",
        description="Message displayed when there is nothing to render",
        json_schema_extra={"ui:widget": "text"},
    )


@register("enrichment_panel", PluginType.WIDGET)
class EnrichmentPanelWidget(WidgetPlugin):
    """Render a compact, sectioned view of enriched reference metadata."""

    param_schema = EnrichmentPanelParams
    compatible_structures = [
        {
            "summary": "list",
            "sections": "list",
            "sources": "list",
            "meta": "dict",
        }
    ]

    def get_dependencies(self) -> Set[str]:
        return set()

    def render(self, data: Optional[Any], params: EnrichmentPanelParams) -> str:
        if not isinstance(data, dict):
            return f"<p class='info'>{html.escape(params.empty_message)}</p>"

        try:
            normalized = EnrichmentPanelData.model_validate(data)
        except Exception as exc:
            logger.warning("Invalid enrichment_panel payload: %s", exc)
            return "<p class='error'>Invalid enrichment profile data.</p>"

        if not normalized.summary and not normalized.sections:
            return f"<p class='info'>{html.escape(params.empty_message)}</p>"

        summary_html = self._render_summary(normalized.summary, params)
        sections_html = self._render_sections(normalized.sections, params)
        sources_html = self._render_sources(normalized.sources, params)

        return f"""
        <div class="enrichment-panel-widget">
            <style>
                .enrichment-panel-widget {{
                    --ep-surface: #ffffff;
                    --ep-surface-muted: #f8fbfe;
                    --ep-shell: #f5f9fc;
                    --ep-border: #d7e3ee;
                    --ep-border-strong: #c8d7e5;
                    --ep-text: #0f172a;
                    --ep-subtle: #5f738b;
                    --ep-subtle-strong: #415972;
                    --ep-accent: #0f766e;
                    --ep-accent-soft: #ecfdf5;
                    --ep-shadow: 0 1px 2px rgba(15, 23, 42, 0.05),
                        0 12px 28px rgba(148, 163, 184, 0.12);
                    color: var(--ep-text);
                    font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
                        "Segoe UI", sans-serif;
                }}
                .enrichment-panel-widget .ep-shell {{
                    padding: 1rem;
                    border-radius: 1.25rem;
                    border: 1px solid var(--ep-border);
                    background: linear-gradient(180deg, #ffffff 0%, var(--ep-shell) 100%);
                }}
                .enrichment-panel-widget .ep-source-rail {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 0.45rem;
                    margin-bottom: 0.9rem;
                }}
                .enrichment-panel-widget .ep-chip {{
                    display: inline-flex;
                    align-items: center;
                    gap: 0.25rem;
                    padding: 0.18rem 0.58rem;
                    border-radius: 999px;
                    border: 1px solid var(--ep-border);
                    background: rgba(255, 255, 255, 0.88);
                    color: var(--ep-subtle-strong);
                    font-size: 0.73rem;
                    line-height: 1.1;
                    backdrop-filter: blur(8px);
                }}
                .enrichment-panel-widget .ep-count {{
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    min-width: 1.8rem;
                    padding: 0.18rem 0.5rem;
                    border-radius: 999px;
                    background: #eef4fa;
                    border: 1px solid var(--ep-border);
                    color: var(--ep-subtle);
                    font-size: 0.72rem;
                    font-weight: 700;
                }}
                .enrichment-panel-widget .ep-summary-grid {{
                    display: grid;
                    gap: 0.8rem;
                    margin-bottom: 0.95rem;
                }}
                .enrichment-panel-widget .ep-card {{
                    background: var(--ep-surface);
                    border: 1px solid var(--ep-border);
                    border-radius: 1rem;
                    padding: 0.95rem;
                    min-width: 0;
                    transition: transform 160ms ease, box-shadow 160ms ease,
                        border-color 160ms ease;
                }}
                .enrichment-panel-widget .ep-card:hover {{
                    transform: translateY(-1px);
                    border-color: var(--ep-border-strong);
                }}
                .enrichment-panel-widget .ep-card--summary {{
                    background: linear-gradient(180deg, #ffffff 0%, #f8fbfe 100%);
                    border-color: var(--ep-border-strong);
                    box-shadow: var(--ep-shadow);
                }}
                .enrichment-panel-widget .ep-card--section {{
                    background: var(--ep-surface-muted);
                }}
                .enrichment-panel-widget .ep-card__meta {{
                    display: flex;
                    align-items: flex-start;
                    justify-content: space-between;
                    gap: 0.75rem;
                    margin-bottom: 0.55rem;
                }}
                .enrichment-panel-widget .ep-card__badges {{
                    display: flex;
                    flex-wrap: wrap;
                    justify-content: flex-end;
                    gap: 0.35rem;
                }}
                .enrichment-panel-widget .ep-label {{
                    color: var(--ep-subtle);
                    font-size: 0.72rem;
                    font-weight: 700;
                    line-height: 1.2;
                    letter-spacing: 0.03em;
                    text-transform: uppercase;
                }}
                .enrichment-panel-widget .ep-value {{
                    color: var(--ep-text);
                    font-size: 1rem;
                    line-height: 1.45;
                    word-break: break-word;
                }}
                .enrichment-panel-widget .ep-card--summary .ep-value {{
                    font-size: 1.18rem;
                    font-weight: 600;
                }}
                .enrichment-panel-widget .ep-section {{
                    border: 1px solid var(--ep-border);
                    border-radius: 1.05rem;
                    background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
                    margin-top: 0.85rem;
                    overflow: hidden;
                    transition: border-color 180ms ease, box-shadow 180ms ease;
                }}
                .enrichment-panel-widget .ep-section[open] {{
                    border-color: var(--ep-border-strong);
                    box-shadow: var(--ep-shadow);
                }}
                .enrichment-panel-widget .ep-section-summary {{
                    cursor: pointer;
                    list-style: none;
                    padding: 0.95rem 1rem;
                    display: flex;
                    align-items: flex-start;
                    justify-content: space-between;
                    gap: 0.75rem;
                    background: transparent;
                }}
                .enrichment-panel-widget .ep-section-summary::-webkit-details-marker {{
                    display: none;
                }}
                .enrichment-panel-widget .ep-section-summary:focus-visible {{
                    outline: 2px solid rgba(15, 118, 110, 0.25);
                    outline-offset: -2px;
                }}
                .enrichment-panel-widget .ep-section-heading {{
                    min-width: 0;
                    display: flex;
                    flex-direction: column;
                    gap: 0.4rem;
                }}
                .enrichment-panel-widget .ep-section-title-row {{
                    display: flex;
                    flex-wrap: wrap;
                    align-items: center;
                    gap: 0.5rem;
                }}
                .enrichment-panel-widget .ep-section-title {{
                    color: var(--ep-text);
                    font-size: 1.02rem;
                    font-weight: 700;
                    line-height: 1.25;
                }}
                .enrichment-panel-widget .ep-section-summary-right {{
                    display: inline-flex;
                    align-items: center;
                    gap: 0.45rem;
                    color: var(--ep-subtle);
                    flex-shrink: 0;
                }}
                .enrichment-panel-widget .ep-chevron {{
                    font-size: 1.05rem;
                    line-height: 1;
                    transition: transform 180ms ease, color 180ms ease;
                }}
                .enrichment-panel-widget .ep-section[open] .ep-chevron {{
                    transform: rotate(90deg);
                    color: var(--ep-accent);
                }}
                .enrichment-panel-widget .ep-item-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                    gap: 0.75rem;
                    padding: 0 1rem 1rem;
                }}
                .enrichment-panel-widget .ep-section[open] .ep-item-grid {{
                    animation: ep-fade-in 180ms ease;
                }}
                .enrichment-panel-widget .ep-list {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 0.35rem;
                }}
                .enrichment-panel-widget .ep-image-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(108px, 1fr));
                    gap: 0.65rem;
                }}
                .enrichment-panel-widget .ep-image-wrap {{
                    border-radius: 0.8rem;
                    overflow: hidden;
                    border: 1px solid #deebf5;
                    background: #ffffff;
                    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
                }}
                .enrichment-panel-widget .ep-image {{
                    display: block;
                    width: 100%;
                    aspect-ratio: 4 / 3;
                    object-fit: cover;
                    background: #eef4fa;
                    transition: transform 180ms ease;
                }}
                .enrichment-panel-widget .ep-image-wrap:hover .ep-image {{
                    transform: scale(1.03);
                }}
                .enrichment-panel-widget a {{
                    color: var(--ep-accent);
                    text-decoration: none;
                }}
                .enrichment-panel-widget a:hover {{
                    text-decoration: underline;
                }}
                .enrichment-panel-widget .ep-link {{
                    display: inline-flex;
                    align-items: center;
                    gap: 0.35rem;
                    font-weight: 600;
                }}
                .enrichment-panel-widget .ep-pill {{
                    display: inline-flex;
                    align-items: center;
                    padding: 0.22rem 0.62rem;
                    border-radius: 999px;
                    border: 1px solid transparent;
                    font-size: 0.82rem;
                    font-weight: 700;
                    line-height: 1.15;
                }}
                .enrichment-panel-widget .ep-pill--positive {{
                    background: #dcfce7;
                    border-color: #bbf7d0;
                    color: #166534;
                }}
                .enrichment-panel-widget .ep-pill--negative {{
                    background: #fee2e2;
                    border-color: #fecaca;
                    color: #991b1b;
                }}
                .enrichment-panel-widget .ep-pill--neutral {{
                    background: #e0f2fe;
                    border-color: #bae6fd;
                    color: #0c4a6e;
                }}
                @keyframes ep-fade-in {{
                    from {{
                        opacity: 0;
                        transform: translateY(-4px);
                    }}
                    to {{
                        opacity: 1;
                        transform: translateY(0);
                    }}
                }}
                @media (max-width: 640px) {{
                    .enrichment-panel-widget .ep-shell {{
                        padding: 0.8rem;
                        border-radius: 1rem;
                    }}
                    .enrichment-panel-widget .ep-summary-grid {{
                        grid-template-columns: 1fr !important;
                    }}
                    .enrichment-panel-widget .ep-item-grid {{
                        grid-template-columns: 1fr;
                    }}
                }}
            </style>
            <div class="ep-shell">
                {sources_html}
                {summary_html}
                {sections_html}
            </div>
        </div>
        """

    def _render_sources(
        self, sources: list[dict[str, str]], params: EnrichmentPanelParams
    ) -> str:
        if not sources:
            return ""
        if len(sources) == 1 and params.show_source_badges:
            return ""

        chips = "".join(
            f"<span class='ep-chip'>{html.escape(source.get('label', source.get('id', 'Source')))}</span>"
            for source in sources
        )
        return f"<div class='ep-source-rail'>{chips}</div>"

    def _render_summary(
        self,
        summary_items: list[EnrichmentPanelItem],
        params: EnrichmentPanelParams,
    ) -> str:
        if not summary_items:
            return ""

        column_count = max(1, min(params.summary_columns, 4))
        cards = "".join(
            self._render_item_card(item, params, emphasize=True)
            for item in summary_items
        )
        return (
            "<div class='ep-summary-grid' style='"
            f"grid-template-columns: repeat({column_count}, minmax(0, 1fr));'>"
            f"{cards}</div>"
        )

    def _render_sections(
        self,
        sections: list[EnrichmentPanelSection],
        params: EnrichmentPanelParams,
    ) -> str:
        parts: list[str] = []
        for section in sections:
            items_html = "".join(
                self._render_item_card(
                    item,
                    params,
                    emphasize=False,
                    parent_source_label=section.source_label,
                )
                for item in section.items
            )
            source_badge = ""
            if params.show_source_badges and section.source_label:
                source_badge = (
                    f"<span class='ep-chip'>{html.escape(section.source_label)}</span>"
                )
            count_badge = f"<span class='ep-count'>{len(section.items)}</span>"
            open_attr = "" if section.collapsed else " open"
            parts.append(
                f"""
                <details class="ep-section"{open_attr}>
                    <summary class="ep-section-summary">
                        <span class="ep-section-heading">
                            <span class="ep-section-title-row">
                                <span class="ep-section-title">{html.escape(section.title)}</span>
                                {source_badge}
                            </span>
                        </span>
                        <span class="ep-section-summary-right">
                            {count_badge}
                            <span class="ep-chevron" aria-hidden="true">&rsaquo;</span>
                        </span>
                    </summary>
                    <div class="ep-item-grid">
                        {items_html}
                    </div>
                </details>
                """
            )
        return "".join(parts)

    def _render_item_card(
        self,
        item: EnrichmentPanelItem,
        params: EnrichmentPanelParams,
        *,
        emphasize: bool,
        parent_source_label: Optional[str] = None,
    ) -> str:
        source_badge = ""
        if (
            params.show_source_badges
            and item.source_label
            and item.source_label != parent_source_label
        ):
            source_badge = (
                f"<span class='ep-chip'>{html.escape(item.source_label)}</span>"
            )

        value_html = self._render_item_value(item)
        card_variant = "ep-card--summary" if emphasize else "ep-card--section"
        format_class = f"ep-card--{html.escape(item.format or 'text')}"
        return f"""
        <div class="ep-card {card_variant} {format_class}">
            <div class="ep-card__meta">
                <div class="ep-label">{html.escape(item.label)}</div>
                <div class="ep-card__badges">{source_badge}</div>
            </div>
            <div class="ep-value">{value_html}</div>
        </div>
        """

    def _render_item_value(self, item: EnrichmentPanelItem) -> str:
        value = item.value
        fmt = item.format or "text"

        if fmt == "number":
            return html.escape(self._format_number(value))
        if fmt == "badge":
            return self._render_badge(value)
        if fmt == "link":
            return self._render_link(value)
        if fmt == "image":
            return self._render_images(value, item.label)
        if fmt == "list":
            return self._render_list(value)
        return html.escape(self._stringify_value(value))

    def _format_number(self, value: Any) -> str:
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return self._stringify_value(value)

        if numeric_value.is_integer():
            return f"{int(numeric_value):,}".replace(",", " ")
        return f"{numeric_value:,.2f}".replace(",", " ").replace(".", ",")

    def _render_badge(self, value: Any) -> str:
        if isinstance(value, bool):
            label = "Yes" if value else "No"
            badge_class = "ep-pill--positive" if value else "ep-pill--negative"
        else:
            label = self._stringify_value(value)
            badge_class = "ep-pill--neutral"

        return f"<span class='ep-pill {badge_class}'>{html.escape(label)}</span>"

    def _render_link(self, value: Any) -> str:
        url = self._extract_url(value)
        if not url:
            return html.escape(self._stringify_value(value))

        safe_url = html.escape(url, quote=True)
        label = html.escape(
            self._stringify_value(value if isinstance(value, str) else url)
        )
        return (
            f'<a class=\'ep-link\' href="{safe_url}" target="_blank" rel="noopener noreferrer">'
            f"<span>{label}</span><span aria-hidden='true'>↗</span></a>"
        )

    def _render_images(self, value: Any, label: str) -> str:
        image_urls = self._extract_image_urls(value)
        if not image_urls:
            return html.escape(self._stringify_value(value))

        images = "".join(
            f"<div class='ep-image-wrap'><img class='ep-image' src=\"{html.escape(url, quote=True)}\" "
            f'alt="{html.escape(label, quote=True)}" loading="lazy" /></div>'
            for url in image_urls[:6]
        )
        return f"<div class='ep-image-grid'>{images}</div>"

    def _render_list(self, value: Any) -> str:
        items = value if isinstance(value, list) else [value]
        normalized = [self._stringify_value(item) for item in items if item is not None]
        if not normalized:
            return "<span style='color:#94a3b8;'>-</span>"

        chips = "".join(
            f"<span class='ep-chip'>{html.escape(item)}</span>" for item in normalized
        )
        return f"<div class='ep-list'>{chips}</div>"

    def _stringify_value(self, value: Any) -> str:
        if value is None:
            return "-"
        if isinstance(value, bool):
            return "Yes" if value else "No"
        if isinstance(value, list):
            return ", ".join(
                self._stringify_value(item) for item in value if item is not None
            )
        if isinstance(value, dict):
            if "value" in value:
                return self._stringify_value(value.get("value"))
            try:
                return json.dumps(value, ensure_ascii=False, sort_keys=True)
            except TypeError:
                return str(value)
        return str(value)

    def _extract_url(self, value: Any) -> Optional[str]:
        if isinstance(value, str) and _URL_RE.match(value.strip()):
            return value.strip()
        if isinstance(value, dict):
            for key in ("url", "href", "link", "source_url"):
                candidate = value.get(key)
                if isinstance(candidate, str) and _URL_RE.match(candidate.strip()):
                    return candidate.strip()
        return None

    def _extract_image_urls(self, value: Any) -> list[str]:
        urls: list[str] = []

        def collect(candidate: Any) -> None:
            if len(urls) >= 6 or candidate is None:
                return
            if isinstance(candidate, str):
                stripped = candidate.strip()
                if _URL_RE.match(stripped) and stripped not in urls:
                    urls.append(stripped)
                return
            if isinstance(candidate, list):
                for nested in candidate:
                    collect(nested)
                    if len(urls) >= 6:
                        return
                return
            if isinstance(candidate, dict):
                preferred_keys = (
                    "thumbnail",
                    "small_thumb",
                    "image_small_thumb",
                    "thumb",
                    "image",
                    "image_big_thumb",
                    "big_thumb",
                    "url",
                    "source_url",
                )
                for key in preferred_keys:
                    if key in candidate:
                        collect(candidate.get(key))
                        if len(urls) >= 6:
                            return
                for nested_value in candidate.values():
                    collect(nested_value)
                    if len(urls) >= 6:
                        return

        collect(value)
        return urls
