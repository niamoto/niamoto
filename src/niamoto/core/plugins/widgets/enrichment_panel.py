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
                    --ep-paper: #ffffff;
                    --ep-paper-strong: #fcfbf8;
                    --ep-surface: rgba(255, 255, 255, 0.99);
                    --ep-surface-soft: rgba(255, 255, 255, 0.94);
                    --ep-border: var(--border, #dfd9cd);
                    --ep-border-strong: #cfc5b3;
                    --ep-text: var(--foreground, #233126);
                    --ep-subtle: var(--muted-foreground, #6d6f63);
                    --ep-accent: var(--foreground, #3b4038);
                    --ep-accent-soft: rgba(246, 246, 242, 0.96);
                    --ep-accent-warm: #8b8478;
                    --ep-link: var(--foreground, #233126);
                    --ep-link-foreground: var(--success-foreground, #f8fff9);
                    --ep-shadow-soft: 0 1px 2px rgba(53, 48, 35, 0.03);
                    --ep-shadow: 0 3px 10px rgba(53, 48, 35, 0.045);
                    color: var(--ep-text);
                    font-family: inherit;
                }}
                .enrichment-panel-widget .ep-shell {{
                    position: relative;
                    padding: 1.15rem 1.1rem 1rem;
                    border-radius: 0.28rem;
                    border: 1px solid var(--ep-border);
                    background: linear-gradient(
                        180deg,
                        rgba(255, 255, 255, 0.99) 0%,
                        var(--ep-paper) 72%,
                        var(--ep-paper-strong) 100%
                    );
                    box-shadow: var(--ep-shadow);
                    overflow: hidden;
                }}
                .enrichment-panel-widget .ep-shell::before {{
                    content: "";
                    position: absolute;
                    inset: 0 0 auto 0;
                    height: 1px;
                    background: var(--ep-border-strong);
                    opacity: 0.9;
                }}
                .enrichment-panel-widget .ep-source-rail {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 0.4rem;
                    margin-bottom: 1rem;
                }}
                .enrichment-panel-widget .ep-chip {{
                    display: inline-flex;
                    align-items: center;
                    gap: 0.3rem;
                    padding: 0.18rem 0.56rem;
                    border-radius: 0.22rem;
                    border: 1px solid var(--ep-border);
                    background: rgba(255, 255, 255, 0.96);
                    color: var(--ep-subtle);
                    font-size: 0.74rem;
                    font-weight: 600;
                    line-height: 1.1;
                }}
                .enrichment-panel-widget .ep-count {{
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    min-width: 1.95rem;
                    padding: 0.18rem 0.52rem;
                    border-radius: 0.22rem;
                    background: rgba(255, 255, 255, 0.96);
                    border: 1px solid var(--ep-border);
                    color: var(--ep-subtle);
                    font-size: 0.72rem;
                    font-weight: 600;
                }}
                .enrichment-panel-widget .ep-summary-grid {{
                    display: grid;
                    gap: 0.85rem;
                    margin-bottom: 1.05rem;
                }}
                .enrichment-panel-widget .ep-card {{
                    min-width: 0;
                    transition: transform 160ms ease, border-color 160ms ease,
                        background-color 160ms ease;
                }}
                .enrichment-panel-widget .ep-card--summary {{
                    padding: 0.9rem 0.95rem 0.95rem;
                    border: 1px solid var(--ep-border);
                    border-radius: 0.18rem;
                    background: rgba(255, 255, 255, 0.99);
                    border-color: var(--ep-border-strong);
                    box-shadow: none;
                }}
                .enrichment-panel-widget .ep-card--section {{
                    padding: 0.9rem 0;
                    border-top: 1px solid var(--ep-border);
                    background: transparent;
                }}
                .enrichment-panel-widget .ep-item-grid > .ep-card:first-child {{
                    border-top: none;
                    padding-top: 0.2rem;
                }}
                .enrichment-panel-widget .ep-card--image {{
                    padding-top: 1rem;
                }}
                .enrichment-panel-widget .ep-card__meta {{
                    display: flex;
                    align-items: baseline;
                    justify-content: space-between;
                    gap: 0.95rem;
                    margin-bottom: 0.32rem;
                }}
                .enrichment-panel-widget .ep-card__badges {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 0.35rem;
                    justify-content: flex-end;
                }}
                .enrichment-panel-widget .ep-label {{
                    color: var(--ep-subtle);
                    font-size: 0.72rem;
                    font-weight: 600;
                    line-height: 1.2;
                    letter-spacing: 0.08em;
                    text-transform: uppercase;
                }}
                .enrichment-panel-widget .ep-value {{
                    color: var(--ep-text);
                    font-size: 1.02rem;
                    line-height: 1.55;
                    word-break: break-word;
                }}
                .enrichment-panel-widget .ep-card--summary .ep-label {{
                    color: var(--ep-subtle);
                }}
                .enrichment-panel-widget .ep-card--summary .ep-value {{
                    font-size: 1.32rem;
                    font-weight: 700;
                    line-height: 1.18;
                }}
                .enrichment-panel-widget .ep-section {{
                    border: 1px solid var(--ep-border);
                    border-radius: 0.18rem;
                    background: rgba(255, 255, 255, 0.995);
                    margin-top: 0.85rem;
                    overflow: hidden;
                    box-shadow: none;
                    transition: border-color 180ms ease, transform 180ms ease,
                        box-shadow 180ms ease;
                }}
                .enrichment-panel-widget .ep-section[open] {{
                    border-color: var(--ep-border-strong);
                    box-shadow: var(--ep-shadow-soft);
                }}
                .enrichment-panel-widget .ep-section-summary {{
                    cursor: pointer;
                    list-style: none;
                    padding: 0.95rem 1rem 0.85rem;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    gap: 0.9rem;
                    background: transparent;
                }}
                .enrichment-panel-widget .ep-section-summary::-webkit-details-marker {{
                    display: none;
                }}
                .enrichment-panel-widget .ep-section-summary:focus-visible {{
                    outline: 2px solid rgba(63, 106, 83, 0.22);
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
                    gap: 0.55rem;
                }}
                .enrichment-panel-widget .ep-section-title {{
                    color: var(--ep-text);
                    font-size: 1.35rem;
                    font-weight: 700;
                    line-height: 1.1;
                    letter-spacing: -0.01em;
                }}
                .enrichment-panel-widget .ep-section-summary-right {{
                    display: inline-flex;
                    align-items: center;
                    gap: 0.45rem;
                    color: var(--ep-subtle);
                    flex-shrink: 0;
                }}
                .enrichment-panel-widget .ep-chevron {{
                    font-size: 1rem;
                    line-height: 1;
                    color: var(--ep-subtle);
                    transition: transform 180ms ease, opacity 180ms ease;
                }}
                .enrichment-panel-widget .ep-section[open] .ep-chevron {{
                    transform: rotate(90deg);
                    opacity: 0.9;
                }}
                .enrichment-panel-widget .ep-item-grid {{
                    display: flex;
                    flex-direction: column;
                    gap: 0;
                    padding: 0 1rem 0.85rem;
                }}
                .enrichment-panel-widget .ep-section[open] .ep-item-grid {{
                    animation: ep-fade-in 180ms ease;
                }}
                .enrichment-panel-widget .ep-list {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 0.42rem;
                }}
                .enrichment-panel-widget .ep-image-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
                    gap: 0.7rem;
                }}
                .enrichment-panel-widget .ep-image-wrap {{
                    border-radius: 0.12rem;
                    overflow: hidden;
                    border: 1px solid var(--ep-border);
                    background: rgba(255, 255, 255, 0.96);
                    box-shadow: none;
                }}
                .enrichment-panel-widget .ep-image {{
                    display: block;
                    width: 100%;
                    aspect-ratio: 4 / 3;
                    object-fit: cover;
                    background: var(--ep-paper-strong);
                    transition: transform 180ms ease;
                }}
                .enrichment-panel-widget .ep-image-wrap:hover .ep-image {{
                    transform: scale(1.03);
                }}
                .enrichment-panel-widget a {{
                    color: var(--ep-link);
                    text-decoration: underline;
                    text-decoration-color: rgba(35, 49, 38, 0.28);
                    text-underline-offset: 0.12em;
                }}
                .enrichment-panel-widget a:hover {{
                    text-decoration-color: rgba(35, 49, 38, 0.55);
                }}
                .enrichment-panel-widget .ep-link {{
                    display: inline-flex;
                    align-items: center;
                    gap: 0.35rem;
                    font-size: 1.04rem;
                    font-weight: 700;
                    line-height: 1.45;
                }}
                .enrichment-panel-widget .ep-pill {{
                    display: inline-flex;
                    align-items: center;
                    padding: 0.22rem 0.65rem;
                    border-radius: 0.2rem;
                    border: 1px solid transparent;
                    font-size: 0.8rem;
                    font-weight: 700;
                    line-height: 1.15;
                }}
                .enrichment-panel-widget .ep-pill--positive {{
                    background: rgba(240, 244, 239, 0.95);
                    border-color: rgba(112, 126, 114, 0.2);
                    color: #465248;
                }}
                .enrichment-panel-widget .ep-pill--negative {{
                    background: rgba(247, 239, 237, 0.96);
                    border-color: rgba(143, 121, 115, 0.2);
                    color: #6f5a55;
                }}
                .enrichment-panel-widget .ep-pill--neutral {{
                    background: rgba(245, 244, 240, 0.96);
                    border-color: rgba(120, 124, 109, 0.16);
                    color: #5f6258;
                }}
                .enrichment-panel-widget .ep-card--list .ep-chip {{
                    background: rgba(255, 255, 255, 0.98);
                    color: var(--ep-subtle);
                }}
                .enrichment-panel-widget .ep-card--link .ep-card__meta,
                .enrichment-panel-widget .ep-card--image .ep-card__meta {{
                    margin-bottom: 0.6rem;
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
                        padding: 0.9rem 0.85rem 0.8rem;
                        border-radius: 0.18rem;
                    }}
                    .enrichment-panel-widget .ep-summary-grid {{
                        grid-template-columns: 1fr !important;
                    }}
                    .enrichment-panel-widget .ep-section-summary {{
                        align-items: flex-start;
                    }}
                    .enrichment-panel-widget .ep-section-title {{
                        font-size: 1.2rem;
                    }}
                    .enrichment-panel-widget .ep-image-grid {{
                        grid-template-columns: repeat(2, minmax(0, 1fr));
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
            section_id = html.escape(section.id, quote=True)
            source_id_attr = html.escape(section.source_id or "", quote=True)
            parts.append(
                f"""
                <details class="ep-section" data-section-id="{section_id}" data-source-id="{source_id_attr}"{open_attr}>
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
        item_format = item.format or "text"
        format_class = f"ep-card--{html.escape(item_format)}"
        source_id_attr = html.escape(item.source_id or "", quote=True)
        format_attr = html.escape(item_format, quote=True)
        item_id_attr = html.escape(item.id or "", quote=True)
        item_kind = "summary" if emphasize else "section"
        return f"""
        <article
            class="ep-card {card_variant} {format_class}"
            data-item-kind="{item_kind}"
            data-item-id="{item_id_attr}"
            data-format="{format_attr}"
            data-source-id="{source_id_attr}"
        >
            <div class="ep-card__meta">
                <div class="ep-label">{html.escape(item.label)}</div>
                <div class="ep-card__badges">{source_badge}</div>
            </div>
            <div class="ep-value">{value_html}</div>
        </article>
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
