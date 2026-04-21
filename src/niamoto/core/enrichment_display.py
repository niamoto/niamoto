"""Helpers for rendering and configuring reference enrichment display widgets.

This module centralizes the logic used to:

- inspect ``extra_data.api_enrichment.sources.*`` payloads
- infer displayable fields and formats
- build field catalogs for the GUI
- generate default panel configs for suggestions

The goal is to keep enrichment-specific heuristics in one place so the
transformer, suggestion service, and field-picking API stay aligned.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any, Iterable

from niamoto.common.utils.dict_utils import get_nested_value

DisplayFormat = str

_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
_IMAGE_KEYWORDS = (
    "thumbnail",
    "thumb",
    "image",
    "media",
    "photo",
    "illustration",
    "source_url",
)
_IMAGE_URL_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")
_BADGE_KEYWORDS = (
    "status",
    "rank",
    "type",
    "category",
    "match_type",
    "iucn",
    "endemic",
    "monitored",
    "basis_of_record",
)
_PRIORITY_SUMMARY_SUFFIXES = (
    "canonical_name",
    "scientific_name",
    "accepted_name",
    "preferred_common_name",
    "matched_name",
    "rank",
    "status",
    "endemic",
    "iucn_category",
    "occurrence_count",
    "datasets_count",
    "media_count",
    "synonyms_count",
    "vernacular_count",
    "distribution_count",
    "references_count",
)


def _coerce_json_like(value: Any) -> Any:
    """Parse JSON strings while leaving native Python values unchanged."""

    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                return value
    return value


def _humanize_token(value: str) -> str:
    value = value.replace("-", " ").replace("_", " ").strip()
    if not value:
        return "Value"
    acronyms = {
        "api": "API",
        "gbif": "GBIF",
        "taxref": "TAXREF",
        "bhl": "BHL",
        "col": "Catalogue of Life",
        "id": "ID",
        "iucn": "IUCN",
        "url": "URL",
    }
    parts = []
    for token in value.split():
        lower = token.lower()
        parts.append(acronyms.get(lower, token.capitalize()))
    return " ".join(parts)


def _humanize_path(path: str) -> str:
    if path in ("", "."):
        return "Source data"
    return _humanize_token(path.split(".")[-1])


def canonicalize_source_id(source_id: str) -> str:
    lower = source_id.lower()
    if lower.startswith("api-gbif") or lower == "gbif":
        return "gbif"
    if lower.startswith("api-taxref") or lower == "taxref":
        return "taxref"
    if lower.startswith("api-endemia") or lower == "endemia":
        return "endemia"
    return lower


def extract_enrichment_sources(extra_data: Any) -> dict[str, dict[str, Any]]:
    """Extract normalized enrichment sources from an ``extra_data`` payload."""

    payload = _coerce_json_like(extra_data)
    if not isinstance(payload, dict):
        return {}

    api_enrichment = _coerce_json_like(payload.get("api_enrichment"))
    if not isinstance(api_enrichment, dict):
        return {}

    sources = api_enrichment.get("sources")
    if isinstance(sources, dict):
        normalized: dict[str, dict[str, Any]] = {}
        for source_id, source_payload in sources.items():
            if not isinstance(source_payload, dict):
                continue
            data = _coerce_json_like(source_payload.get("data"))
            normalized[source_id] = {
                "id": source_id,
                "label": source_payload.get("label") or _humanize_token(source_id),
                "status": source_payload.get("status"),
                "data": data if data is not None else {},
                "meta": {
                    key: value
                    for key, value in source_payload.items()
                    if key not in {"data"}
                },
            }
        return normalized

    # Legacy single-source structure: expose as a synthetic source.
    return {
        "legacy": {
            "id": "legacy",
            "label": "API Enrichment",
            "status": api_enrichment.get("status"),
            "data": api_enrichment,
            "meta": {},
        }
    }


def _is_scalar(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool)) or value is None


def _is_url(value: Any) -> bool:
    return isinstance(value, str) and bool(_URL_RE.match(value.strip()))


def _looks_like_image_url(value: Any) -> bool:
    if not _is_url(value):
        return False
    lower = str(value).lower()
    return any(lower.endswith(ext) for ext in _IMAGE_URL_EXTENSIONS) or any(
        keyword in lower for keyword in ("thumbnail", "thumb", "image", "media")
    )


def _is_image_like_mapping(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    for key, nested in value.items():
        lower_key = str(key).lower()
        if any(keyword in lower_key for keyword in _IMAGE_KEYWORDS) and _is_url(nested):
            return True
    return False


def _is_image_like_list(value: Any) -> bool:
    if not isinstance(value, list) or not value:
        return False
    first_items = value[:4]
    return all(
        _looks_like_image_url(item) or _is_image_like_mapping(item)
        for item in first_items
    )


def is_image_like(value: Any) -> bool:
    coerced = _coerce_json_like(value)
    return (
        _looks_like_image_url(coerced)
        or _is_image_like_mapping(coerced)
        or _is_image_like_list(coerced)
    )


def resolve_source_path(source_data: Any, path: str) -> Any:
    """Resolve a relative path inside one enrichment source payload."""

    data = _coerce_json_like(source_data)
    if path in ("", "."):
        return data
    if not isinstance(data, dict):
        return None
    value = get_nested_value(data, path)
    value = _coerce_json_like(value)
    if isinstance(value, dict) and "value" in value and not is_image_like(value):
        return value.get("value")
    return value


def _flatten_display_values(value: Any, prefix: str = "") -> list[tuple[str, Any]]:
    """Flatten displayable nested values into dotted paths.

    Complex nested objects are skipped unless they look like an image payload.
    Lists are kept only when they contain compact scalar values or image-like items.
    """

    collected: list[tuple[str, Any]] = []
    value = _coerce_json_like(value)

    if prefix in ("", ".") and is_image_like(value):
        collected.append((".", value))

    if isinstance(value, dict):
        if prefix and is_image_like(value):
            collected.append((prefix, value))

        for nested_key, nested_value in value.items():
            next_prefix = f"{prefix}.{nested_key}" if prefix else str(nested_key)
            collected.extend(_flatten_display_values(nested_value, next_prefix))
        return collected

    if isinstance(value, list):
        if prefix and is_image_like(value):
            collected.append((prefix, value))
            return collected

        scalar_items = [
            _coerce_json_like(item)
            for item in value
            if _is_scalar(_coerce_json_like(item))
        ]
        if scalar_items:
            collected.append((prefix, scalar_items[:12]))
        return collected

    collected.append((prefix, value))
    return collected


def infer_display_format(path: str, values: list[Any]) -> DisplayFormat:
    non_null_values = [value for value in values if value is not None]
    if not non_null_values:
        return "text"

    if any(is_image_like(value) for value in non_null_values):
        return "image"

    if any(isinstance(value, list) for value in non_null_values):
        return "list"

    if any(_is_url(value) for value in non_null_values):
        return "link"

    if all(isinstance(value, bool) for value in non_null_values):
        return "badge"

    if all(
        isinstance(value, (int, float)) and not isinstance(value, bool)
        for value in non_null_values
    ):
        return "number"

    lower_path = path.lower()
    if any(keyword in lower_path for keyword in _BADGE_KEYWORDS):
        return "badge"

    return "text"


def infer_section_hint(path: str, fmt: DisplayFormat) -> str:
    lower_path = path.lower()
    if fmt == "image" or lower_path.startswith("media"):
        return "Media"
    if fmt == "link" or lower_path.startswith("links"):
        return "Links"
    if lower_path.startswith("provenance"):
        return "Provenance"
    first_segment = path.split(".", 1)[0] if path else ""
    if first_segment and first_segment not in {"", "."}:
        return _humanize_token(first_segment)
    return "Details"


def _summary_priority(path: str, fmt: DisplayFormat) -> int:
    if fmt in {"image", "link", "list"}:
        return -10
    lower_path = path.lower()
    for index, suffix in enumerate(_PRIORITY_SUMMARY_SUFFIXES):
        if lower_path.endswith(suffix):
            return 100 - index
    if lower_path.startswith("match."):
        return 70
    if lower_path.startswith("taxonomy."):
        return 60
    if lower_path.startswith("occurrence_summary.") or lower_path.startswith(
        "distribution_summary."
    ):
        return 55
    return 10


def build_source_field_catalog(
    source_id: str,
    source_label: str,
    sample_payloads: Iterable[Any],
) -> dict[str, Any]:
    """Build a field catalog for one enrichment source from sample payloads."""

    values_by_path: dict[str, list[Any]] = defaultdict(list)

    for payload in sample_payloads:
        for path, value in _flatten_display_values(payload):
            if not path:
                continue
            values_by_path[path].append(value)

    fields: list[dict[str, Any]] = []
    for path, values in values_by_path.items():
        fmt = infer_display_format(path, values)
        unique_samples: list[Any] = []
        seen = set()
        for value in values:
            if value is None:
                continue
            marker = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
            if marker in seen:
                continue
            seen.add(marker)
            unique_samples.append(value)
            if len(unique_samples) >= 5:
                break
        fields.append(
            {
                "source_id": source_id,
                "source_label": source_label,
                "path": path,
                "label": _humanize_path(path),
                "format": fmt,
                "section_hint": infer_section_hint(path, fmt),
                "sample_values": unique_samples,
            }
        )

    fields.sort(key=lambda field: (field["section_hint"], field["label"]))
    return {
        "id": source_id,
        "label": source_label,
        "field_count": len(fields),
        "fields": fields,
    }


def build_enrichment_catalog(extra_data_values: Iterable[Any]) -> list[dict[str, Any]]:
    """Build a per-source field catalog from multiple ``extra_data`` samples."""

    source_samples: dict[str, dict[str, Any]] = {}
    for raw_extra_data in extra_data_values:
        for source_id, source_entry in extract_enrichment_sources(
            raw_extra_data
        ).items():
            bucket = source_samples.setdefault(
                source_id,
                {
                    "label": source_entry.get("label") or _humanize_token(source_id),
                    "payloads": [],
                },
            )
            bucket["payloads"].append(source_entry.get("data") or {})

    catalogs = [
        build_source_field_catalog(source_id, payload["label"], payload["payloads"])
        for source_id, payload in source_samples.items()
    ]
    catalogs.sort(key=lambda catalog: catalog["label"].lower())
    return catalogs


def _index_catalog_fields(
    source_catalog: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    return {
        field["path"]: field
        for field in source_catalog.get("fields", [])
        if isinstance(field, dict)
    }


def _field_item(
    source_id: str,
    field: dict[str, Any],
    *,
    label: str | None = None,
    fmt: str | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "source_id": source_id,
        "path": field["path"],
        "label": label or field["label"],
    }
    chosen_format = fmt or field.get("format")
    if chosen_format:
        item["format"] = chosen_format
    return item


def _filter_existing_fields(
    field_index: dict[str, dict[str, Any]], paths: Iterable[str]
) -> list[dict[str, Any]]:
    return [field_index[path] for path in paths if path in field_index]


def _generic_panel_config(
    source_catalog: dict[str, Any],
) -> dict[str, Any]:
    source_id = source_catalog["id"]
    field_index = _index_catalog_fields(source_catalog)
    fields = list(field_index.values())

    summary_fields = [
        field
        for field in sorted(
            fields,
            key=lambda field: (
                -_summary_priority(field["path"], field.get("format", "text")),
                field["label"],
            ),
        )
        if field.get("format") not in {"image", "link", "list"}
    ][:6]

    def make_section(
        section_id: str,
        title: str,
        candidates: Iterable[dict[str, Any]],
        *,
        collapsed: bool,
    ) -> dict[str, Any] | None:
        items = [_field_item(source_id, field) for field in list(candidates)[:8]]
        if not items:
            return None
        return {
            "id": section_id,
            "title": title,
            "source_id": source_id,
            "collapsed": collapsed,
            "items": items,
        }

    summary_paths = {field["path"] for field in summary_fields}
    detail_fields = [
        field
        for field in fields
        if field["path"] not in summary_paths
        and field.get("format") not in {"image", "link"}
        and not str(field["path"]).startswith("provenance.")
    ]
    link_fields = [field for field in fields if field.get("format") == "link"]
    image_fields = [field for field in fields if field.get("format") == "image"]
    provenance_fields = [
        field for field in fields if str(field["path"]).startswith("provenance.")
    ]

    sections = [
        section
        for section in [
            make_section("details", "Details", detail_fields, collapsed=False),
            make_section("links", "Links", link_fields, collapsed=True),
            make_section("media", "Media", image_fields, collapsed=True),
            make_section(
                "provenance",
                "Provenance",
                provenance_fields,
                collapsed=True,
            ),
        ]
        if section is not None
    ]

    return {
        "summary_items": [_field_item(source_id, field) for field in summary_fields],
        "sections": sections,
    }


def _gbif_panel_config(source_catalog: dict[str, Any]) -> dict[str, Any]:
    source_id = source_catalog["id"]
    field_index = _index_catalog_fields(source_catalog)

    summary = [
        _field_item(source_id, field, label=label)
        for path, label in [
            ("match.canonical_name", "Canonical name"),
            ("match.rank", "Rank"),
            ("match.status", "Status"),
            (
                "occurrence_summary.occurrence_count",
                "Occurrences",
            ),
            ("occurrence_summary.datasets_count", "Datasets"),
            ("media_summary.media_count", "Media"),
        ]
        if (field := field_index.get(path))
    ]

    def section(
        section_id: str, title: str, paths: list[str], collapsed: bool
    ) -> dict[str, Any] | None:
        existing = _filter_existing_fields(field_index, paths)
        if not existing:
            return None
        return {
            "id": section_id,
            "title": title,
            "source_id": source_id,
            "collapsed": collapsed,
            "items": [_field_item(source_id, field) for field in existing],
        }

    sections = [
        section(
            "identity",
            "Identity",
            [
                "match.scientific_name",
                "match.canonical_name",
                "match.rank",
                "match.status",
                "match.confidence",
                "match.match_type",
            ],
            False,
        ),
        section(
            "taxonomy",
            "Taxonomy",
            [
                "taxonomy.kingdom",
                "taxonomy.phylum",
                "taxonomy.class",
                "taxonomy.order",
                "taxonomy.family",
                "taxonomy.genus",
                "taxonomy.species",
                "taxonomy.synonyms_count",
                "taxonomy.iucn_category",
                "taxonomy.vernacular_names",
            ],
            True,
        ),
        section(
            "occurrences",
            "Occurrences",
            [
                "occurrence_summary.occurrence_count",
                "occurrence_summary.datasets_count",
                "occurrence_summary.countries",
                "occurrence_summary.basis_of_record",
            ],
            False,
        ),
        section(
            "media",
            "Media",
            [
                "media_summary.media_count",
                "media_summary.items",
            ],
            True,
        ),
        section(
            "links",
            "Links",
            [path for path in field_index if path.startswith("links.")],
            True,
        ),
        section(
            "provenance",
            "Provenance",
            [path for path in field_index if path.startswith("provenance.")],
            True,
        ),
    ]

    sections = [section for section in sections if section is not None]
    if not summary and not sections:
        return _generic_panel_config(source_catalog)

    return {"summary_items": summary[:6], "sections": sections}


def _taxref_panel_config(source_catalog: dict[str, Any]) -> dict[str, Any]:
    source_id = source_catalog["id"]
    field_index = _index_catalog_fields(source_catalog)

    summary = [
        _field_item(source_id, field)
        for path in [
            "match.scientific_name",
            "match.rank",
            "match.status",
            "nomenclature.synonyms_count",
            "taxonomy.family",
        ]
        if (field := field_index.get(path))
    ]

    sections = []
    for section_id, title, paths, collapsed in [
        (
            "identity",
            "Identity",
            [
                "match.scientific_name",
                "match.canonical_name",
                "match.rank",
                "match.status",
                "match.taxon_id",
            ],
            False,
        ),
        (
            "taxonomy",
            "Taxonomy",
            [
                "taxonomy.family",
                "taxonomy.genus",
                "taxonomy.species",
                "taxonomy.vernacular_names",
            ],
            True,
        ),
        (
            "nomenclature",
            "Nomenclature",
            [
                "nomenclature.accepted_name",
                "nomenclature.synonyms_count",
                "nomenclature.synonyms_sample",
            ],
            True,
        ),
        (
            "links",
            "Links",
            [path for path in field_index if path.startswith("links.")],
            True,
        ),
        (
            "provenance",
            "Provenance",
            [path for path in field_index if path.startswith("provenance.")],
            True,
        ),
    ]:
        existing = _filter_existing_fields(field_index, paths)
        if existing:
            sections.append(
                {
                    "id": section_id,
                    "title": title,
                    "source_id": source_id,
                    "collapsed": collapsed,
                    "items": [_field_item(source_id, field) for field in existing],
                }
            )

    if not summary and not sections:
        return _generic_panel_config(source_catalog)

    return {"summary_items": summary[:6], "sections": sections}


def _endemia_panel_config(source_catalog: dict[str, Any]) -> dict[str, Any]:
    source_id = source_catalog["id"]
    field_index = _index_catalog_fields(source_catalog)

    summary = [
        _field_item(source_id, field)
        for path in ["full_name", "rank_name", "endemic", "monitored", "api_id"]
        if (field := field_index.get(path))
    ]

    details = _filter_existing_fields(
        field_index,
        [
            "full_name",
            "rank_name",
            "endemic",
            "monitored",
            "api_id",
            "status",
        ],
    )
    links = [field for field in field_index.values() if field.get("format") == "link"]
    media = (
        [field_index["."]]
        if "." in field_index and field_index["."].get("format") == "image"
        else []
    )

    sections = []
    if details:
        sections.append(
            {
                "id": "details",
                "title": "Details",
                "source_id": source_id,
                "collapsed": False,
                "items": [_field_item(source_id, field) for field in details],
            }
        )
    if media:
        sections.append(
            {
                "id": "media",
                "title": "Media",
                "source_id": source_id,
                "collapsed": True,
                "items": [
                    _field_item(source_id, field, label="Images") for field in media
                ],
            }
        )
    if links:
        sections.append(
            {
                "id": "links",
                "title": "Links",
                "source_id": source_id,
                "collapsed": True,
                "items": [_field_item(source_id, field) for field in links],
            }
        )

    if not summary and not sections:
        return _generic_panel_config(source_catalog)

    return {"summary_items": summary[:6], "sections": sections}


def build_default_panel_config(source_catalog: dict[str, Any]) -> dict[str, Any]:
    """Build default summary/sections config for one source catalog."""

    builder = {
        "gbif": _gbif_panel_config,
        "taxref": _taxref_panel_config,
        "endemia": _endemia_panel_config,
    }.get(canonicalize_source_id(source_catalog["id"]), _generic_panel_config)
    return builder(source_catalog)
