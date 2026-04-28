"""Site configuration API endpoints for managing export.yml site settings."""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from fastapi import APIRouter, HTTPException, UploadFile, File, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict
import yaml
import shutil
from datetime import datetime

from ..context import get_working_directory
from niamoto.common.i18n import I18nResolver

router = APIRouter()

_LANGUAGE_PREFIX_RE = re.compile(r"^[a-z]{2}(?:-[a-z]{2})?$", re.IGNORECASE)
_ROOT_INDEX_TEMPLATE = "index.html"
_ROOT_INDEX_OUTPUT = "index.html"


def _normalize_output_alias(output_file: str | None) -> str | None:
    if not output_file:
        return None
    return output_file.strip().lstrip("/")


def _is_root_index_page(page: dict[str, Any]) -> bool:
    return page.get("template") == _ROOT_INDEX_TEMPLATE


def _normalize_static_pages(
    static_pages: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    normalized_pages: list[dict[str, Any]] = []
    output_aliases: dict[str, str] = {}

    for page in static_pages:
        normalized_page = dict(page)
        current_output = _normalize_output_alias(
            str(normalized_page.get("output_file", ""))
        )

        if _is_root_index_page(normalized_page):
            normalized_page["output_file"] = _ROOT_INDEX_OUTPUT
            if current_output and current_output != _ROOT_INDEX_OUTPUT:
                output_aliases[current_output] = _ROOT_INDEX_OUTPUT
        elif current_output is not None:
            normalized_page["output_file"] = current_output

        normalized_pages.append(normalized_page)

    return normalized_pages, output_aliases


def _normalize_link_url(url: str | None, output_aliases: dict[str, str]) -> str | None:
    if not url:
        return url

    normalized = _normalize_output_alias(url)
    if not normalized:
        return url

    replacement = output_aliases.get(normalized)
    if not replacement:
        return url

    return f"/{replacement}" if url.startswith("/") else replacement


def _normalize_navigation_items(
    items: list[dict[str, Any]], output_aliases: dict[str, str]
) -> list[dict[str, Any]]:
    normalized_items: list[dict[str, Any]] = []

    for item in items:
        normalized_item = dict(item)
        normalized_item["url"] = _normalize_link_url(item.get("url"), output_aliases)

        children = item.get("children")
        if children:
            normalized_item["children"] = _normalize_navigation_items(
                children, output_aliases
            )

        normalized_items.append(normalized_item)

    return normalized_items


def _normalize_footer_sections(
    sections: list[dict[str, Any]], output_aliases: dict[str, str]
) -> list[dict[str, Any]]:
    normalized_sections: list[dict[str, Any]] = []

    for section in sections:
        normalized_section = dict(section)
        links = []
        for link in section.get("links", []):
            normalized_link = dict(link)
            normalized_link["url"] = _normalize_link_url(
                link.get("url"), output_aliases
            )
            links.append(normalized_link)
        normalized_section["links"] = links
        normalized_sections.append(normalized_section)

    return normalized_sections


def _validate_static_pages(static_pages: list[dict[str, Any]]) -> None:
    root_index_pages = [page for page in static_pages if _is_root_index_page(page)]
    if len(root_index_pages) > 1:
        raise HTTPException(
            status_code=422,
            detail=(
                "Only one page can use the index.html template. "
                "Update the existing home page or remove it first."
            ),
        )

    seen_outputs: set[str] = set()
    duplicates: set[str] = set()
    for page in static_pages:
        output_file = _normalize_output_alias(str(page.get("output_file", "")))
        if not output_file:
            continue
        if output_file in seen_outputs:
            duplicates.add(output_file)
        seen_outputs.add(output_file)

    if duplicates:
        duplicate_list = ", ".join(sorted(duplicates))
        raise HTTPException(
            status_code=422,
            detail=f"Duplicate output_file values are not allowed: {duplicate_list}",
        )


def _get_legacy_home_output_file() -> str | None:
    export_config = _get_export_config()
    exports = export_config.get("exports", [])
    web_pages = _find_web_pages_export(exports)
    if not web_pages:
        return None

    static_pages = web_pages.get("static_pages", [])
    for page in static_pages:
        if not _is_root_index_page(page):
            continue
        output_file = _normalize_output_alias(str(page.get("output_file", "")))
        if output_file and output_file != _ROOT_INDEX_OUTPUT:
            return output_file

    return None


def _fallback_legacy_home_page(exports_web_dir: Path, normalized: str) -> Path | None:
    legacy_home_output = _get_legacy_home_output_file()
    if not legacy_home_output:
        return None

    if not normalized or normalized == _ROOT_INDEX_OUTPUT:
        return exports_web_dir / legacy_home_output

    parts = normalized.split("/", 1)
    if (
        len(parts) == 2
        and _LANGUAGE_PREFIX_RE.match(parts[0])
        and parts[1] == _ROOT_INDEX_OUTPUT
    ):
        return exports_web_dir / parts[0] / legacy_home_output

    return None


def _candidate_exported_preview_path(
    exports_web_dir: Path, requested_path: str
) -> Path:
    normalized = requested_path.strip("/")

    if not normalized:
        return exports_web_dir / "index.html"

    candidate = exports_web_dir / normalized
    if candidate.is_dir() or requested_path.endswith("/"):
        candidate = candidate / "index.html"
    return candidate


def _fallback_without_language_prefix(
    exports_web_dir: Path, normalized: str
) -> Path | None:
    parts = normalized.split("/", 1)
    if len(parts) != 2:
        return None

    prefix, remainder = parts
    if not _LANGUAGE_PREFIX_RE.match(prefix):
        return None

    return _candidate_exported_preview_path(exports_web_dir, remainder)


def _resolve_exported_preview_path(requested_path: str = "") -> Path:
    """Resolve a file inside the current project's exported web directory."""
    work_dir = get_working_directory()
    exports_web_dir = (work_dir / "exports" / "web").resolve()
    normalized = requested_path.strip("/")

    candidate = _candidate_exported_preview_path(exports_web_dir, requested_path)
    if not candidate.exists():
        if normalized:
            fallback = _fallback_without_language_prefix(exports_web_dir, normalized)
            if fallback is not None and fallback.exists():
                candidate = fallback

        if not candidate.exists():
            legacy_home_fallback = _fallback_legacy_home_page(
                exports_web_dir, normalized
            )
            if legacy_home_fallback is not None and legacy_home_fallback.exists():
                candidate = legacy_home_fallback

    resolved = candidate.resolve()
    try:
        resolved.relative_to(exports_web_dir)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Invalid preview path") from exc

    if not resolved.exists() or not resolved.is_file():
        raise HTTPException(status_code=404, detail="Preview file not found")

    return resolved


# =============================================================================
# Pydantic Models
# =============================================================================


class SiteSettings(BaseModel):
    """Site-wide settings from export.yml params.site."""

    model_config = ConfigDict(extra="allow")

    title: str = "Niamoto"
    logo_header: Optional[str] = None
    logo_footer: Optional[str] = None
    lang: str = "fr"
    primary_color: str = "#228b22"
    nav_color: str = "#228b22"


class NavigationItem(BaseModel):
    """Navigation menu item with optional children for sub-menus.

    text can be a plain string or a localized dict like {fr: "Arbres", en: "Trees"}.
    """

    text: Union[str, Dict[str, str]]
    url: Optional[str] = None
    children: Optional[List["NavigationItem"]] = None


class FooterLink(BaseModel):
    """A single link in a footer section."""

    text: Union[str, Dict[str, str]]
    url: str
    external: bool = False


class FooterSection(BaseModel):
    """A footer section with a title and a list of links."""

    title: Union[str, Dict[str, str]]
    links: List[FooterLink] = []


class StaticPageContext(BaseModel):
    """Context for static page content."""

    model_config = ConfigDict(extra="allow")

    content_markdown: Optional[str] = None
    content_source: Optional[str] = None
    title: Optional[str] = None


class StaticPage(BaseModel):
    """Static page definition."""

    model_config = ConfigDict(extra="allow")

    name: str
    template: str
    output_file: str
    context: Optional[StaticPageContext] = None


class SiteConfigResponse(BaseModel):
    """Response model for site configuration."""

    site: SiteSettings
    navigation: List[NavigationItem]
    footer_navigation: List[FooterSection] = []
    static_pages: List[StaticPage]
    # Additional export params that aren't site-specific
    template_dir: str = "templates/"
    output_dir: str = "exports/web"
    copy_assets_from: List[str] = []


class SiteConfigUpdate(BaseModel):
    """Request model for updating site configuration."""

    site: SiteSettings
    navigation: List[NavigationItem]
    footer_navigation: List[FooterSection] = []
    static_pages: List[StaticPage]
    template_dir: Optional[str] = None
    output_dir: Optional[str] = None
    copy_assets_from: Optional[List[str]] = None


class TemplateInfo(BaseModel):
    """Information about a template."""

    name: str
    description: str
    icon: str = "📄"
    category: str = "general"


class TemplatesResponse(BaseModel):
    """Response model for available templates."""

    templates: List[TemplateInfo]
    default_templates: List[str]
    project_templates: List[str]


# Template descriptions for static pages
TEMPLATE_DESCRIPTIONS: Dict[str, TemplateInfo] = {
    "index.html": TemplateInfo(
        name="index.html",
        description="Page d'accueil avec hero, statistiques et navigation",
        icon="fas fa-home",
        category="accueil",
    ),
    "page.html": TemplateInfo(
        name="page.html",
        description="Page simple avec contenu centre",
        icon="fas fa-file-alt",
        category="contenu",
    ),
    "article.html": TemplateInfo(
        name="article.html",
        description="Article avec sidebar et table des matieres",
        icon="fas fa-newspaper",
        category="contenu",
    ),
    "documentation.html": TemplateInfo(
        name="documentation.html",
        description="Documentation technique avec navigation laterale",
        icon="fas fa-book",
        category="technique",
    ),
    "bibliography.html": TemplateInfo(
        name="bibliography.html",
        description="References bibliographiques avec citations formatees",
        icon="fas fa-quote-right",
        category="scientifique",
    ),
    "glossary.html": TemplateInfo(
        name="glossary.html",
        description="Glossaire des termes avec navigation alphabetique",
        icon="fas fa-spell-check",
        category="scientifique",
    ),
    "resources.html": TemplateInfo(
        name="resources.html",
        description="Ressources, telechargements et datasets",
        icon="fas fa-download",
        category="donnees",
    ),
    "team.html": TemplateInfo(
        name="team.html",
        description="Equipe, partenaires et financeurs",
        icon="fas fa-users",
        category="projet",
    ),
    "contact.html": TemplateInfo(
        name="contact.html",
        description="Page de contact avec informations",
        icon="fas fa-envelope",
        category="projet",
    ),
}


class FilesResponse(BaseModel):
    """Response model for project files listing."""

    files: List[Dict[str, Any]]
    folder: str


class MarkdownPreviewRequest(BaseModel):
    """Request model for markdown preview."""

    content: str


class MarkdownPreviewResponse(BaseModel):
    """Response model for markdown preview."""

    html: str


class TemplatePreviewRequest(BaseModel):
    """Request model for template preview."""

    template: str  # Template name (e.g., "team.html", "page.html")
    context: Dict[str, Any] = {}  # Page-specific context (team, references, etc.)
    site: Optional[Dict[str, Any]] = None  # Site settings override
    navigation: Optional[List[Dict[str, Any]]] = None  # Navigation override
    footer_navigation: Optional[List[Dict[str, Any]]] = None  # Footer sections
    output_file: Optional[str] = None  # Actual output filename (e.g., "resources.html")
    gui_lang: Optional[str] = None  # GUI language for resolving localized strings


class TemplatePreviewResponse(BaseModel):
    """Response model for template preview."""

    html: str
    template: str


class GroupIndexConfig(BaseModel):
    """Configuration for group index page generation."""

    model_config = ConfigDict(extra="allow")

    enabled: bool = False
    template: str = "group_index.html"
    page_config: Dict[str, Any] = {}
    filters: List[Dict[str, Any]] = []
    display_fields: List[Dict[str, Any]] = []
    views: List[Dict[str, Any]] = []


class GroupInfo(BaseModel):
    """Information about a group from export.yml."""

    name: str
    output_pattern: str
    index_output_pattern: Optional[str] = None
    index_generator: Optional[GroupIndexConfig] = None
    widgets_count: int = 0


class GroupsResponse(BaseModel):
    """Response model for groups listing."""

    groups: List[GroupInfo]


# =============================================================================
# Helper Functions
# =============================================================================


def _get_export_config() -> Dict[str, Any]:
    """Load export.yml configuration."""
    work_dir = get_working_directory()
    if not work_dir:
        raise HTTPException(status_code=500, detail="Working directory not set")

    export_path = work_dir / "config" / "export.yml"
    if not export_path.exists():
        # Return default structure
        return {"exports": []}

    try:
        with open(export_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {"exports": []}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error reading export.yml: {str(e)}"
        )


def _find_web_pages_export(exports: Optional[List[Dict]]) -> Optional[Dict]:
    """Find the web_pages export configuration."""
    if not exports:
        return None
    for export in exports:
        if (
            export.get("name") == "web_pages"
            and export.get("exporter") == "html_page_exporter"
        ):
            return export
    return None


def _create_backup(file_path: Path) -> Optional[Path]:
    """Create a backup of a file."""
    if not file_path.exists():
        return None

    backup_dir = file_path.parent / "backups"
    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{file_path.stem}_{timestamp}{file_path.suffix}"
    shutil.copy2(file_path, backup_path)
    return backup_path


def _save_export_config(config: Dict[str, Any]) -> Path:
    """Save export.yml configuration with backup."""
    work_dir = get_working_directory()
    if not work_dir:
        raise HTTPException(status_code=500, detail="Working directory not set")

    export_path = work_dir / "config" / "export.yml"

    # Create backup
    _create_backup(export_path)

    # Ensure config directory exists
    export_path.parent.mkdir(parents=True, exist_ok=True)

    # Write new configuration
    with open(export_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            config, f, default_flow_style=False, sort_keys=False, allow_unicode=True
        )

    return export_path


# =============================================================================
# API Endpoints
# =============================================================================


@router.get("/config", response_model=SiteConfigResponse)
async def get_site_config():
    """
    Get site configuration from export.yml.

    Extracts site settings, navigation, and static pages from the
    web_pages export configuration.
    """
    export_config = _get_export_config()
    exports = export_config.get("exports", [])

    web_pages = _find_web_pages_export(exports)

    if not web_pages:
        # Return default configuration
        return SiteConfigResponse(
            site=SiteSettings(),
            navigation=[],
            static_pages=[],
            template_dir="templates/",
            output_dir="exports/web",
            copy_assets_from=[],
        )

    params = web_pages.get("params", {})
    site_config = params.get("site", {})
    raw_navigation = params.get("navigation", [])
    raw_footer_navigation = params.get("footer_navigation", [])
    raw_static_pages = web_pages.get("static_pages", [])
    static_pages, output_aliases = _normalize_static_pages(raw_static_pages)
    _validate_static_pages(static_pages)
    navigation = _normalize_navigation_items(raw_navigation, output_aliases)
    footer_navigation = _normalize_footer_sections(
        raw_footer_navigation, output_aliases
    )

    # Convert raw dicts to models
    site = SiteSettings(**site_config) if site_config else SiteSettings()
    nav_items = [NavigationItem(**item) for item in navigation]
    footer_sections = [FooterSection(**s) for s in footer_navigation]

    pages = []
    for page in static_pages:
        context_data = page.get("context")
        context = StaticPageContext(**context_data) if context_data else None
        pages.append(
            StaticPage(
                name=page.get("name", ""),
                template=page.get("template", ""),
                output_file=page.get("output_file", ""),
                context=context,
            )
        )

    return SiteConfigResponse(
        site=site,
        navigation=nav_items,
        footer_navigation=footer_sections,
        static_pages=pages,
        template_dir=params.get("template_dir", "templates/"),
        output_dir=params.get("output_dir", "exports/web"),
        copy_assets_from=params.get("copy_assets_from", []),
    )


@router.put("/config")
async def update_site_config(update: SiteConfigUpdate):
    """
    Update site configuration in export.yml.

    Updates site settings, navigation, and static pages in the
    web_pages export configuration. Creates a backup before saving.
    """
    export_config = _get_export_config()
    exports = export_config.get("exports", [])

    web_pages = _find_web_pages_export(exports)

    if not web_pages:
        # Create new web_pages export
        web_pages = {
            "name": "web_pages",
            "enabled": True,
            "exporter": "html_page_exporter",
            "params": {
                "template_dir": "templates/",
                "output_dir": "exports/web",
            },
            "static_pages": [],
            "groups": [],
        }
        exports.append(web_pages)

    # Update params
    params = web_pages.setdefault("params", {})
    params.setdefault("template_dir", "templates/")
    params.setdefault("output_dir", "exports/web")
    params["site"] = update.site.model_dump(exclude_none=True)
    if update.template_dir:
        params["template_dir"] = update.template_dir
    if update.output_dir:
        params["output_dir"] = update.output_dir
    if update.copy_assets_from is not None:
        params["copy_assets_from"] = update.copy_assets_from

    # Update static pages
    raw_static_pages_data = []
    for page in update.static_pages:
        page_dict = {
            "name": page.name,
            "template": page.template,
            "output_file": page.output_file,
        }
        if page.context:
            context_dict = page.context.model_dump(exclude_none=True)
            if context_dict:
                page_dict["context"] = context_dict
        raw_static_pages_data.append(page_dict)

    static_pages_data, output_aliases = _normalize_static_pages(raw_static_pages_data)
    _validate_static_pages(static_pages_data)

    params["navigation"] = _normalize_navigation_items(
        [item.model_dump(exclude_none=True) for item in update.navigation],
        output_aliases,
    )
    params["footer_navigation"] = _normalize_footer_sections(
        [section.model_dump(exclude_none=True) for section in update.footer_navigation],
        output_aliases,
    )
    web_pages["static_pages"] = static_pages_data

    # Save configuration
    export_config["exports"] = exports
    saved_path = _save_export_config(export_config)

    return {
        "success": True,
        "message": "Site configuration updated successfully",
        "path": str(saved_path),
    }


@router.get("/groups", response_model=GroupsResponse)
async def get_groups():
    """
    Get groups configuration from export.yml.

    Returns all groups defined in the web_pages export, including
    their index_generator configuration and widget count.
    """
    export_config = _get_export_config()
    exports = export_config.get("exports", [])

    web_pages = _find_web_pages_export(exports)

    if not web_pages:
        return GroupsResponse(groups=[])

    groups_data = web_pages.get("groups", [])
    groups = []

    for g in groups_data:
        group_name = g.get("group_by", "")
        output_pattern = g.get("output_pattern") or (
            f"{group_name}/{{id}}.html" if group_name else ""
        )
        index_output_pattern = g.get("index_output_pattern")

        # Parse index_generator if present
        index_gen_data = g.get("index_generator")
        index_generator = None
        if index_gen_data:
            index_generator = GroupIndexConfig(
                enabled=index_gen_data.get("enabled", False),
                template=index_gen_data.get("template", "group_index.html"),
                page_config=index_gen_data.get("page_config", {}),
                filters=index_gen_data.get("filters", []),
                display_fields=index_gen_data.get("display_fields", []),
                views=index_gen_data.get("views", []),
            )
            if not index_output_pattern and group_name:
                index_output_pattern = f"{group_name}/index.html"

        groups.append(
            GroupInfo(
                name=group_name,
                output_pattern=output_pattern,
                index_output_pattern=index_output_pattern,
                index_generator=index_generator,
                widgets_count=len(g.get("widgets", [])),
            )
        )

    return GroupsResponse(groups=groups)


@router.get("/preview-exported", include_in_schema=False)
@router.get("/preview-exported/{requested_path:path}", include_in_schema=False)
async def preview_exported_site(requested_path: str = ""):
    """Serve exported preview files for the current instance."""
    preview_path = _resolve_exported_preview_path(requested_path)
    return FileResponse(preview_path)


@router.get("/templates", response_model=TemplatesResponse)
async def list_templates():
    """
    List available templates.

    Returns templates from both the project's templates/ directory
    and Niamoto's default templates.
    """
    work_dir = get_working_directory()
    project_templates = []
    default_templates = []

    # Project templates
    if work_dir:
        templates_dir = work_dir / "templates"
        if templates_dir.exists():
            for f in templates_dir.rglob("*.html"):
                # Get relative path from templates dir
                rel_path = f.relative_to(templates_dir)
                # Skip partials and layouts (files starting with _)
                if not str(rel_path).startswith("_"):
                    project_templates.append(str(rel_path))

    # Default templates from Niamoto package
    try:
        from niamoto.publish import templates as publish_templates

        if publish_templates.__file__:
            default_templates_dir = Path(publish_templates.__file__).parent
            if default_templates_dir.exists():
                for f in default_templates_dir.rglob("*.html"):
                    rel_path = f.relative_to(default_templates_dir)
                    if not str(rel_path).startswith("_"):
                        default_templates.append(str(rel_path))
    except (ImportError, AttributeError, TypeError):
        # Fallback: try to find templates relative to niamoto package
        try:
            import niamoto

            if niamoto.__file__:
                niamoto_dir = Path(niamoto.__file__).parent
                default_templates_dir = niamoto_dir / "publish" / "templates"
                if default_templates_dir.exists():
                    for f in default_templates_dir.rglob("*.html"):
                        rel_path = f.relative_to(default_templates_dir)
                        if not str(rel_path).startswith("_"):
                            default_templates.append(str(rel_path))
        except (ImportError, AttributeError, TypeError):
            pass

    # If still no templates found, provide essential defaults
    if not default_templates:
        default_templates = list(TEMPLATE_DESCRIPTIONS.keys())

    # Combine and deduplicate (project templates override defaults)
    all_template_names = list(set(project_templates + default_templates))
    all_template_names.sort()

    # Convert to TemplateInfo with descriptions
    templates_info = []
    for name in all_template_names:
        if name in TEMPLATE_DESCRIPTIONS:
            templates_info.append(TEMPLATE_DESCRIPTIONS[name])
        else:
            # Unknown template (project-specific)
            templates_info.append(
                TemplateInfo(
                    name=name,
                    description=f"Template personnalise: {name}",
                    icon="📁",
                    category="projet",
                )
            )

    # Sort by category then name for better UX
    category_order = [
        "accueil",
        "contenu",
        "scientifique",
        "technique",
        "donnees",
        "projet",
        "groupes",
        "general",
    ]
    templates_info.sort(
        key=lambda t: (
            category_order.index(t.category) if t.category in category_order else 99,
            t.name,
        )
    )

    return TemplatesResponse(
        templates=templates_info,
        default_templates=sorted(default_templates),
        project_templates=sorted(project_templates),
    )


@router.get("/files", response_model=FilesResponse)
async def list_project_files(folder: str = "files"):
    """
    List files in a project folder.

    Used for selecting logos, markdown sources, etc.

    Args:
        folder: Folder to list (relative to project root). Default: "files"
    """
    work_dir = get_working_directory()
    if not work_dir:
        return FilesResponse(files=[], folder=folder)

    target_dir = work_dir / folder
    files = []

    if target_dir.exists() and target_dir.is_dir():
        for f in target_dir.rglob("*"):
            if f.is_file():
                rel_path = f.relative_to(work_dir)
                stat = f.stat()
                files.append(
                    {
                        "name": f.name,
                        "path": str(rel_path),
                        "size": stat.st_size,
                        "extension": f.suffix.lower(),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    }
                )

    # Sort by name
    files.sort(key=lambda x: x["name"].lower())

    return FilesResponse(files=files, folder=folder)


def _resolve_localized(value: Any, lang: str = "fr") -> Any:
    """Resolve a localized value: {fr: "X", en: "Y"} -> "X" for lang=fr."""
    if isinstance(value, dict) and not any(
        k in value for k in ("name", "url", "logo", "icon")
    ):
        return value.get(lang) or next(iter(value.values()), value)
    return value


def _resolve_navigation(items: list, lang: str = "fr") -> list:
    """Recursively resolve localized strings in navigation items."""
    resolved = []
    for item in items:
        d = dict(item) if isinstance(item, dict) else {"text": str(item)}
        if "text" in d:
            d["text"] = _resolve_localized(d["text"], lang)
        if d.get("children"):
            d["children"] = _resolve_navigation(d["children"], lang)
        resolved.append(d)
    return resolved


def _resolve_footer_sections(sections: list, lang: str = "fr") -> list:
    """Resolve localized strings in footer sections."""
    resolved = []
    for section in sections:
        s = dict(section) if isinstance(section, dict) else {}
        if "title" in s:
            s["title"] = _resolve_localized(s["title"], lang)
        if s.get("links"):
            s["links"] = [
                {**link, "text": _resolve_localized(link.get("text", ""), lang)}
                for link in s["links"]
            ]
        resolved.append(s)
    return resolved


def _preprocess_markdown_images(content: str) -> str:
    """
    Preprocess markdown to handle custom image syntax.

    Converts:
    - ![alt|width](src) -> <img src="src" alt="alt" style="max-width: widthpx">
    - ![alt|center](src) -> <img src="src" alt="alt" style="display:block;margin:auto">
    - ![alt|width|center](src) -> combined styles
    - files/... paths -> /api/site/files/... for preview
    """
    import re

    def replace_image(match):
        alt_part = match.group(1)
        src = match.group(2)

        # Parse alt text parts: "alt", "alt|300", "alt|center", "alt|300|center"
        parts = alt_part.split("|")
        alt = parts[0]
        img_styles = []
        align = None
        for part in parts[1:]:
            p = part.strip()
            if re.match(r"^\d+$", p):
                img_styles.append(f"max-width:{p}px")
            elif p == "center":
                align = "center"
            elif p == "right":
                align = "right"

        # Convert relative paths to API URLs for preview
        if src.startswith("files/"):
            src = f"/api/site/{src}"

        img_style = f' style="{";".join(img_styles)}"' if img_styles else ""
        img_tag = f'<img src="{src}" alt="{alt}"{img_style}>'

        # Wrap in a flex div for alignment (works with Tailwind's display:block on img)
        if align == "center":
            return f'<div style="display:flex;justify-content:center;margin:1rem 0">{img_tag}</div>'
        elif align == "right":
            return f'<div style="display:flex;justify-content:flex-end;margin:1rem 0">{img_tag}</div>'
        return img_tag

    # Match markdown images: ![alt](src) or ![alt|width](src)
    pattern = r"!\[([^\]]*)\]\(([^)]+)\)"
    return re.sub(pattern, replace_image, content)


@router.post("/preview-markdown", response_model=MarkdownPreviewResponse)
async def preview_markdown(request: MarkdownPreviewRequest):
    """
    Convert markdown to HTML for preview.

    Uses the same markdown renderer as the export system.
    Supports custom image syntax: ![alt|width](src) for image sizing.
    """
    try:
        import markdown

        # Preprocess to handle custom image syntax with widths
        processed_content = _preprocess_markdown_images(request.content)

        html = markdown.markdown(
            processed_content,
            extensions=["tables", "fenced_code", "toc", "attr_list"],
        )
        return MarkdownPreviewResponse(html=html)
    except ImportError:
        # Fallback: basic conversion without markdown library
        import html as html_escape

        # First preprocess images (before escaping)
        processed = _preprocess_markdown_images(request.content)

        # Basic markdown conversion
        lines = processed.split("\n")
        html_lines = []
        for line in lines:
            # Skip if already an img tag (from preprocessing)
            if line.strip().startswith("<img"):
                html_lines.append(line)
                continue

            # Escape HTML in text
            line = html_escape.escape(line)

            # Headers
            if line.startswith("### "):
                html_lines.append(f"<h3>{line[4:]}</h3>")
            elif line.startswith("## "):
                html_lines.append(f"<h2>{line[3:]}</h2>")
            elif line.startswith("# "):
                html_lines.append(f"<h1>{line[2:]}</h1>")
            elif line.strip():
                html_lines.append(f"<p>{line}</p>")

        html = "\n".join(html_lines)
        return MarkdownPreviewResponse(html=html)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error converting markdown: {str(e)}"
        )


def _get_preview_api_base_url(http_request: Request | None) -> str:
    """Return the absolute /api/site base URL used inside preview HTML."""
    if http_request is None:
        return "/api/site"
    return f"{str(http_request.base_url).rstrip('/')}/api/site"


def _setup_jinja_environment():
    """
    Set up Jinja2 environment with project and default templates.

    Returns a tuple of (jinja_env, base_url) or raises HTTPException.
    """
    from jinja2 import Environment, FileSystemLoader, ChoiceLoader, select_autoescape
    import importlib.resources

    work_dir = get_working_directory()
    if not work_dir:
        raise HTTPException(status_code=500, detail="Working directory not set")

    # Project templates
    project_templates_dir = work_dir / "templates"

    # Default templates from Niamoto package
    try:
        default_templates_path = (
            importlib.resources.files("niamoto.publish") / "templates"
        )
    except Exception:
        raise HTTPException(
            status_code=500, detail="Could not locate default Niamoto templates"
        )

    # Build loader chain: project templates first, then defaults
    loaders = []
    if project_templates_dir.exists():
        loaders.append(FileSystemLoader(str(project_templates_dir)))
    loaders.append(FileSystemLoader(str(default_templates_path)))

    # Custom filter for relative URLs
    def relative_url_filter(url: str, depth: int = 0) -> str:
        """Convert URL to be relative based on page depth."""
        if url.startswith(("http://", "https://", "//")):
            return url
        prefix = "../" * depth if depth > 0 else ""
        return prefix + url.lstrip("/")

    jinja_env = Environment(
        loader=ChoiceLoader(loaders),
        autoescape=select_autoescape(["html", "xml"]),
    )
    jinja_env.filters["relative_url"] = relative_url_filter

    return jinja_env, work_dir


@router.post("/preview-template", response_model=TemplatePreviewResponse)
async def preview_template(request: TemplatePreviewRequest, http_request: Request):
    """
    Render a Jinja2 template with the provided context for preview.

    This allows previewing any template (page.html, team.html, etc.)
    with the current site configuration and page-specific context.
    """
    try:
        jinja_env, work_dir = _setup_jinja_environment()
        base_url = _get_preview_api_base_url(http_request)

        # Load the template
        try:
            template = jinja_env.get_template(request.template)
        except Exception:
            raise HTTPException(
                status_code=404, detail=f"Template not found: {request.template}"
            )

        # Build default site config if not provided
        site_config = request.site or {
            "title": "Niamoto",
            "lang": "fr",
            "primary_color": "#228b22",
            "nav_color": "#228b22",
        }

        # Resolve localized strings: GUI lang > site lang > fr
        site_lang = (
            site_config.get("lang", "fr") if isinstance(site_config, dict) else "fr"
        )
        lang = request.gui_lang or site_lang
        navigation = _resolve_navigation(request.navigation or [], lang)
        footer_navigation = _resolve_footer_sections(
            request.footer_navigation or [], lang
        )

        # Resolve localized title in site config
        if isinstance(site_config, dict) and "title" in site_config:
            site_config["title"] = _resolve_localized(site_config["title"], lang)

        # Prepare the page context
        page_context = dict(request.context)

        # Handle markdown content if present
        page_content_html = None
        if "content_markdown" in page_context and page_context["content_markdown"]:
            # Convert markdown to HTML
            content = page_context["content_markdown"]
            content = _preprocess_markdown_images(content)
            try:
                import markdown

                md = markdown.Markdown(extensions=["extra", "codehilite", "toc"])
                page_content_html = md.convert(content)
            except ImportError:
                # Fallback: basic conversion
                lines = content.split("\n")
                html_lines = []
                for line in lines:
                    if line.startswith("### "):
                        html_lines.append(f"<h3>{line[4:]}</h3>")
                    elif line.startswith("## "):
                        html_lines.append(f"<h2>{line[3:]}</h2>")
                    elif line.startswith("# "):
                        html_lines.append(f"<h1>{line[2:]}</h1>")
                    elif line.strip():
                        html_lines.append(f"<p>{line}</p>")
                page_content_html = "\n".join(html_lines)

        elif "content_source" in page_context and page_context["content_source"]:
            # Load content from file
            content_path = work_dir / page_context["content_source"]
            if content_path.is_file():
                try:
                    content = content_path.read_text(encoding="utf-8")
                    # Process markdown if needed
                    if content_path.suffix.lower() in [".md", ".markdown"]:
                        content = _preprocess_markdown_images(content)
                        try:
                            import markdown

                            md = markdown.Markdown(
                                extensions=["extra", "codehilite", "toc"]
                            )
                            page_content_html = md.convert(content)
                        except ImportError:
                            page_content_html = f"<pre>{content}</pre>"
                    else:
                        page_content_html = content
                except Exception as e:
                    page_content_html = f"<p><em>Error loading content: {e}</em></p>"
            else:
                page_content_html = f"<p><em>Content file not found: {page_context['content_source']}</em></p>"

        # Resolve *_source JSON files (team_source, references_source, etc.)
        for key in list(page_context.keys()):
            if (
                key.endswith("_source")
                and key != "content_source"
                and key != "bibtex_source"
            ):
                target_key = key[:-7]  # "team_source" → "team"
                json_path = work_dir / page_context[key]
                if json_path.is_file():
                    import json as json_mod

                    data = json_mod.loads(json_path.read_text(encoding="utf-8"))
                    page_context[target_key] = data

        # Build the full context for the template
        context = {
            "site": site_config,
            "navigation": navigation,
            "footer_navigation": footer_navigation,
            "languages": site_config.get("languages") or [site_lang],
            "current_lang": lang,
            "language_switcher": site_config.get("language_switcher", False),
            "preview_exported_base_url": f"{base_url}/preview-exported",
            "page": page_context,
            "depth": 0,  # For relative_url filter
            "output_file": request.output_file or "preview.html",
            **page_context,  # Spread page context at top level for templates that expect it
        }

        # Add page_content_html if we generated it
        if page_content_html:
            context["page_content_html"] = page_content_html

        # Add title from context if present (resolve if localized)
        if "title" in page_context:
            context["title"] = _resolve_localized(page_context["title"], lang)

        # Render the template
        rendered_html = template.render(context)

        # Post-process: fix asset URLs for preview
        # Replace relative paths with API paths

        # Project files (images, etc.) - src, href, and CSS url()
        rendered_html = rendered_html.replace('src="files/', f'src="{base_url}/files/')
        rendered_html = rendered_html.replace("src='files/", f"src='{base_url}/files/")
        rendered_html = rendered_html.replace(
            'href="files/', f'href="{base_url}/files/'
        )
        rendered_html = rendered_html.replace(
            "href='files/", f"href='{base_url}/files/"
        )
        # CSS background-image: url('files/...')
        rendered_html = rendered_html.replace("url('files/", f"url('{base_url}/files/")
        rendered_html = rendered_html.replace('url("files/', f'url("{base_url}/files/')

        # Niamoto assets (CSS, JS, fonts) - handle both /assets/ and assets/
        rendered_html = rendered_html.replace(
            'href="/assets/', f'href="{base_url}/assets/'
        )
        rendered_html = rendered_html.replace(
            "href='/assets/", f"href='{base_url}/assets/"
        )
        rendered_html = rendered_html.replace(
            'href="assets/', f'href="{base_url}/assets/'
        )
        rendered_html = rendered_html.replace(
            "href='assets/", f"href='{base_url}/assets/"
        )
        rendered_html = rendered_html.replace(
            'src="/assets/', f'src="{base_url}/assets/'
        )
        rendered_html = rendered_html.replace(
            "src='/assets/", f"src='{base_url}/assets/"
        )
        rendered_html = rendered_html.replace(
            'src="assets/', f'src="{base_url}/assets/'
        )
        rendered_html = rendered_html.replace(
            "src='assets/", f"src='{base_url}/assets/"
        )

        # Inject script to intercept link clicks and send to parent
        link_intercept_script = """
<script>
document.addEventListener('click', function(e) {
    const link = e.target.closest('a');
    if (link && link.href) {
        e.preventDefault();
        e.stopPropagation();
        // Extract the filename from the href
        const href = link.getAttribute('href');
        if (href && !href.startsWith('http://') && !href.startsWith('https://') && !href.startsWith('mailto:')) {
            // Send message to parent with the clicked link
            window.parent.postMessage({
                type: 'preview-link-click',
                href: href
            }, '*');
        } else if (href && (href.startsWith('http://') || href.startsWith('https://'))) {
            // External link - open in new tab
            window.open(href, '_blank');
        }
    }
}, true);
</script>
"""
        # Insert before </body> or at end
        if "</body>" in rendered_html:
            rendered_html = rendered_html.replace(
                "</body>", f"{link_intercept_script}</body>"
            )
        else:
            rendered_html += link_intercept_script

        return TemplatePreviewResponse(html=rendered_html, template=request.template)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error rendering template: {str(e)}"
        )


class GroupIndexPreviewRequest(BaseModel):
    """Request model for group index preview."""

    site: Optional[Dict[str, Any]] = None
    navigation: Optional[List[Dict[str, Any]]] = None
    gui_lang: Optional[str] = None
    index_config: Optional[GroupIndexConfig] = None


def _preview_group_label(group_name: Optional[str]) -> str:
    """Build a generic, dataset-agnostic label for preview cards."""
    if not group_name:
        return "Élément"

    normalized = re.sub(r"[_-]+", " ", group_name).strip()
    if not normalized:
        return "Élément"

    parts = normalized.split()
    last_part = parts[-1].lower()
    if last_part not in {"species", "series"}:
        if last_part.endswith("ies") and len(last_part) > 3:
            last_part = f"{last_part[:-3]}y"
        elif last_part.endswith(("ses", "xes", "zes", "ches", "shes")):
            last_part = last_part[:-2]
        elif last_part.endswith("s") and len(last_part) > 1:
            last_part = last_part[:-1]
    parts[-1] = last_part

    return " ".join(part.capitalize() for part in parts)


def _generate_mock_items(
    display_fields: List[Dict[str, Any]],
    count: int = 12,
    id_column: str = "id",
    group_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Generate mock items based on display_fields configuration.

    Creates realistic placeholder data for preview purposes.
    """
    import random

    mock_items = []
    preview_label = _preview_group_label(group_name)

    # Sample names for different field types
    sample_names = [
        "Araucaria columnaris",
        "Agathis lanceolata",
        "Dacrydium araucarioides",
        "Parasitaxus usta",
        "Retrophyllum comptonii",
        "Acacia spirorbis",
        "Alphitonia neocaledonica",
        "Baloghia lucida",
        "Canarium oleosum",
        "Deplanchea speciosa",
        "Elaeocarpus angustifolius",
        "Ficus habrophylla",
    ]

    sample_families = [
        "Araucariaceae",
        "Podocarpaceae",
        "Fabaceae",
        "Rhamnaceae",
        "Euphorbiaceae",
        "Burseraceae",
        "Bignoniaceae",
        "Elaeocarpaceae",
        "Moraceae",
    ]

    # Colors for placeholder images (nature-inspired)
    placeholder_colors = [
        "228b22",
        "2e8b57",
        "3cb371",
        "6b8e23",
        "556b2f",
        "8fbc8f",
        "90ee90",
        "98fb98",
        "00fa9a",
        "00ff7f",
    ]

    for i in range(min(count, len(sample_names))):
        item_id = i + 1
        item = {"id": item_id, id_column: item_id}

        for field in display_fields:
            field_name = field.get("name", "")
            field_type = field.get("type", "text")
            field_key = field_name.lower()
            is_title = field.get("is_title")

            if field_type == "boolean":
                item[field_name] = random.choice([True, False])
            elif field_type == "select":
                options = field.get("filter_options", [])
                if options:
                    item[field_name] = random.choice(options).get("value", "Option")
                elif field.get("mapping"):
                    item[field_name] = random.choice(list(field["mapping"].keys()))
                else:
                    item[field_name] = f"Option {random.randint(1, 3)}"
            elif "count" in field_key or "number" in field_key:
                item[field_name] = random.randint(10, 500)
            elif any(
                token in field_key
                for token in ("height", "dbh", "elevation", "altitude")
            ):
                item[field_name] = round(random.uniform(5.0, 800.0), 1)
            elif any(token in field_key for token in ("rainfall", "precip", "pluvio")):
                item[field_name] = random.randint(800, 3500)
            elif field.get("display") == "image_preview" or field_type == "json_array":
                # Generate mock image data with inline SVG placeholders (offline-safe)
                color = random.choice(placeholder_colors)
                num_images = random.randint(1, 3)
                images = []
                for img_idx in range(num_images):
                    label = f"{i + 1}-{img_idx + 1}"
                    name_label = sample_names[i].split()[0]

                    # Use data URI SVG placeholders instead of external service
                    def _svg_placeholder(w, h, bg, text):
                        return (
                            f"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
                            f"width='{w}' height='{h}'%3E%3Crect width='100%25' height='100%25' "
                            f"fill='%23{bg}'/%3E%3Ctext x='50%25' y='50%25' "
                            f"dominant-baseline='middle' text-anchor='middle' "
                            f"fill='white' font-family='sans-serif' font-size='14'%3E"
                            f"{text}%3C/text%3E%3C/svg%3E"
                        )

                    images.append(
                        {
                            "small_thumb": _svg_placeholder(150, 150, color, label),
                            "big_thumb": _svg_placeholder(400, 300, color, name_label),
                            "url": _svg_placeholder(
                                800, 600, color, sample_names[i].replace(" ", "+")
                            ),
                        }
                    )
                item[field_name] = images
            elif field_name == "family" or "family" in field_key:
                item[field_name] = random.choice(sample_families)
            elif is_title:
                item[field_name] = f"{preview_label} {i + 1}"
            elif field_name == "name" or field_name == "full_name":
                item[field_name] = sample_names[i]
            else:
                item[field_name] = f"Valeur {i + 1}"

        mock_items.append(item)

    return mock_items


@router.post(
    "/preview-group-index/{group_name}", response_model=TemplatePreviewResponse
)
async def preview_group_index(
    group_name: str,
    http_request: Request,
    request: GroupIndexPreviewRequest = None,
):
    """
    Generate a preview of a group index page with mock data.

    This allows previewing the group index layout and styling
    without requiring actual transformed data.
    """
    try:
        # Get the group configuration
        export_config = _get_export_config()
        exports = export_config.get("exports", [])
        web_pages = _find_web_pages_export(exports)

        if not web_pages:
            raise HTTPException(
                status_code=404, detail="No web_pages export configuration found"
            )

        # Find the group
        groups_data = web_pages.get("groups", [])
        group_config = None
        for g in groups_data:
            if g.get("group_by") == group_name:
                group_config = g
                break

        if not group_config:
            raise HTTPException(
                status_code=404, detail=f"Group '{group_name}' not found"
            )

        requested_index_gen = (
            request.index_config.model_dump(exclude_none=True)
            if request and request.index_config
            else None
        )
        index_gen = requested_index_gen or group_config.get("index_generator")
        if not index_gen or not index_gen.get("enabled", False):
            raise HTTPException(
                status_code=400,
                detail=f"Group '{group_name}' does not have index generation enabled",
            )

        # Setup Jinja environment
        jinja_env, work_dir = _setup_jinja_environment()
        base_url = _get_preview_api_base_url(http_request)

        # Load the template (default to _group_index.html)
        template_name = index_gen.get("template", "_group_index.html")
        # Ensure template name starts with underscore if not specified
        if not template_name.startswith("_") and template_name == "group_index.html":
            template_name = "_group_index.html"
        try:
            template = jinja_env.get_template(template_name)
        except Exception:
            raise HTTPException(
                status_code=404, detail=f"Template not found: {template_name}"
            )

        # Build site config
        site_config = request.site if request and request.site else {}
        if not site_config:
            # Load from export.yml params
            params = web_pages.get("params", {})
            site_config = params.get(
                "site",
                {
                    "title": "Niamoto",
                    "lang": "fr",
                    "primary_color": "#228b22",
                    "nav_color": "#228b22",
                },
            )

        # Resolve language
        site_lang = (
            site_config.get("lang", "fr") if isinstance(site_config, dict) else "fr"
        )
        lang = (request.gui_lang if request else None) or site_lang
        available_languages = (
            site_config.get("languages") if isinstance(site_config, dict) else None
        ) or [site_lang]
        i18n_resolver = I18nResolver(
            default_lang=site_lang,
            available_languages=list(available_languages),
        )
        if isinstance(site_config, dict):
            site_config = i18n_resolver.resolve_recursive(site_config, lang)

        # Navigation — resolve localized strings
        navigation = request.navigation if request and request.navigation else []
        if not navigation:
            params = web_pages.get("params", {})
            navigation = params.get("navigation", [])
        navigation = _resolve_navigation(navigation, lang)

        # Build index_config for the template
        display_fields = [
            i18n_resolver.resolve_recursive(field, lang)
            for field in index_gen.get("display_fields", [])
        ]
        page_config = i18n_resolver.resolve_recursive(
            index_gen.get("page_config", {}),
            lang,
        )

        # Get output_pattern from group config for correct link generation
        output_pattern = group_config.get("output_pattern", f"{group_name}/{{id}}.html")

        index_config = {
            "group_by": group_name,
            "id_column": f"{group_name}_id",
            "output_pattern": output_pattern,
            "page_config": {
                "title": page_config.get("title", f"Index des {group_name}"),
                "description": page_config.get("description", ""),
                "items_per_page": page_config.get("items_per_page", 20),
            },
            "display_fields": display_fields,
            "filters": index_gen.get("filters", []),
            "views": index_gen.get("views", [{"type": "grid", "default": True}]),
        }

        # Generate mock items
        mock_items = _generate_mock_items(
            display_fields,
            count=12,
            id_column=index_config["id_column"],
            group_name=group_name,
        )

        # Render the template
        rendered_html = template.render(
            site=site_config,
            navigation=navigation,
            footer_navigation=[],
            languages=site_config.get("languages") or [site_lang],
            current_lang=lang,
            language_switcher=site_config.get("language_switcher", False),
            preview_exported_base_url=f"{base_url}/preview-exported",
            index_config=index_config,
            items_data=mock_items,
            page_config=index_config["page_config"],
            group_by=group_name,
            depth=0,
        )

        # Fix asset URLs for preview
        # Project files (images, logo, etc.)
        rendered_html = rendered_html.replace('src="files/', f'src="{base_url}/files/')
        rendered_html = rendered_html.replace("src='files/", f"src='{base_url}/files/")
        rendered_html = rendered_html.replace(
            'href="files/', f'href="{base_url}/files/'
        )
        rendered_html = rendered_html.replace(
            "href='files/", f"href='{base_url}/files/"
        )
        rendered_html = rendered_html.replace("url('files/", f"url('{base_url}/files/")
        rendered_html = rendered_html.replace('url("files/', f'url("{base_url}/files/')
        # Niamoto assets (CSS, JS, fonts)
        rendered_html = rendered_html.replace(
            'href="/assets/', f'href="{base_url}/assets/'
        )
        rendered_html = rendered_html.replace(
            "href='/assets/", f"href='{base_url}/assets/"
        )
        rendered_html = rendered_html.replace(
            'src="/assets/', f'src="{base_url}/assets/'
        )
        rendered_html = rendered_html.replace(
            "src='/assets/", f"src='{base_url}/assets/"
        )
        rendered_html = rendered_html.replace(
            'href="assets/', f'href="{base_url}/assets/'
        )
        rendered_html = rendered_html.replace(
            "href='assets/", f"href='{base_url}/assets/"
        )
        rendered_html = rendered_html.replace(
            'src="assets/', f'src="{base_url}/assets/'
        )
        rendered_html = rendered_html.replace(
            "src='assets/", f"src='{base_url}/assets/"
        )

        # Add preview badge and link intercept script
        preview_badge = """
<div style="position: fixed; top: 70px; right: 20px; z-index: 9999; background: #f59e0b; color: white; padding: 8px 16px; border-radius: 8px; font-size: 14px; font-weight: 600; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
    Aperçu avec données fictives
</div>
"""
        link_intercept_script = """
<script>
document.addEventListener('click', function(e) {
    const link = e.target.closest('a');
    if (link && link.href) {
        e.preventDefault();
        e.stopPropagation();
        const href = link.getAttribute('href');
        if (href && !href.startsWith('http://') && !href.startsWith('https://') && !href.startsWith('mailto:')) {
            window.parent.postMessage({
                type: 'preview-link-click',
                href: href
            }, '*');
        } else if (href && (href.startsWith('http://') || href.startsWith('https://'))) {
            window.open(href, '_blank');
        }
    }
}, true);
</script>
"""
        if "</body>" in rendered_html:
            rendered_html = rendered_html.replace(
                "</body>", f"{preview_badge}{link_intercept_script}</body>"
            )
        else:
            rendered_html += preview_badge + link_intercept_script

        return TemplatePreviewResponse(html=rendered_html, template=template_name)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error rendering group index preview: {str(e)}"
        )


class FileUploadResponse(BaseModel):
    """Response model for file upload."""

    success: bool
    path: str
    filename: str


class FileContentResponse(BaseModel):
    """Response model for file content."""

    content: str
    path: str
    filename: str


class FileContentUpdate(BaseModel):
    """Request model for updating file content."""

    path: str
    content: str


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...), folder: str = "files"):
    """
    Upload a file to the project.

    Args:
        file: The file to upload
        folder: Target folder (relative to project root). Default: "files"
    """
    work_dir = get_working_directory()
    if not work_dir:
        raise HTTPException(status_code=500, detail="Working directory not set")

    # Validate file type based on target folder
    file_ext = Path(file.filename).suffix.lower()

    # Base extensions (images + markdown)
    base_extensions = {
        # Images
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".webp",
        ".ico",
        # Markdown/text content
        ".md",
        ".markdown",
        ".txt",
    }

    # Extended extensions for data folder
    data_extensions = {
        # Documents
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".odt",
        ".ods",
        ".odp",
        ".rtf",
        # Data formats
        ".csv",
        ".json",
        ".geojson",
        ".xml",
        ".yaml",
        ".yml",
        # Archives
        ".zip",
        ".tar",
        ".gz",
        ".7z",
        ".rar",
        # Geospatial
        ".shp",
        ".kml",
        ".kmz",
        ".gpx",
        ".tif",
        ".tiff",
        ".gpkg",
        # Code/scripts
        ".py",
        ".r",
        ".sql",
        ".sh",
        ".js",
        ".html",
        ".css",
    }

    # Allow extended types for files/data folder
    if folder.startswith("files/data"):
        allowed_extensions = base_extensions | data_extensions
    else:
        allowed_extensions = base_extensions

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed: {', '.join(sorted(allowed_extensions))}",
        )

    # Create target directory if it doesn't exist
    target_dir = work_dir / folder
    target_dir.mkdir(parents=True, exist_ok=True)

    # Generate safe filename (avoid overwriting)
    safe_filename = file.filename.replace(" ", "_")
    target_path = target_dir / safe_filename

    # If file exists, add a number suffix
    counter = 1
    original_stem = target_path.stem
    while target_path.exists():
        target_path = target_dir / f"{original_stem}_{counter}{file_ext}"
        counter += 1

    # Save the file
    try:
        content = await file.read()
        with open(target_path, "wb") as f:
            f.write(content)

        # Return path relative to project root
        rel_path = target_path.relative_to(work_dir)
        return FileUploadResponse(
            success=True,
            path=str(rel_path),
            filename=target_path.name,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")


@router.get("/file-content", response_model=FileContentResponse)
async def get_file_content(path: str):
    """
    Get the content of a file.

    Args:
        path: File path relative to project root
    """
    work_dir = get_working_directory()
    if not work_dir:
        raise HTTPException(status_code=500, detail="Working directory not set")

    # Security: ensure path doesn't escape project directory
    file_path = work_dir / path
    try:
        file_path = file_path.resolve()
        work_dir_resolved = work_dir.resolve()
        if not str(file_path).startswith(str(work_dir_resolved)):
            raise HTTPException(
                status_code=403, detail="Access denied: path outside project"
            )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    # Only allow text files
    allowed_extensions = {
        ".md",
        ".markdown",
        ".txt",
        ".html",
        ".css",
        ".js",
        ".json",
        ".yml",
        ".yaml",
    }
    if file_path.suffix.lower() not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type not supported for reading. Allowed: {', '.join(sorted(allowed_extensions))}",
        )

    try:
        content = file_path.read_text(encoding="utf-8")
        return FileContentResponse(
            content=content,
            path=path,
            filename=file_path.name,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


# =============================================================================
# Data File Endpoints (JSON for externalized lists)
# =============================================================================


class DataFileResponse(BaseModel):
    """Response model for JSON data file."""

    data: List[Dict[str, Any]]
    path: str
    count: int


class DataFileUpdate(BaseModel):
    """Request model for updating JSON data file."""

    path: str
    data: List[Dict[str, Any]]


@router.get("/data-content", response_model=DataFileResponse)
async def get_data_content(path: str):
    """
    Get the content of a JSON data file.

    Args:
        path: File path relative to project root (e.g., "data/bibliography-references.json")
    """
    import json

    work_dir = get_working_directory()
    if not work_dir:
        raise HTTPException(status_code=500, detail="Working directory not set")

    # Security: ensure path doesn't escape project directory
    file_path = work_dir / path
    try:
        file_path = file_path.resolve()
        work_dir_resolved = work_dir.resolve()
        if not str(file_path).startswith(str(work_dir_resolved)):
            raise HTTPException(
                status_code=403, detail="Access denied: path outside project"
            )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path")

    # Only allow JSON files
    if file_path.suffix.lower() != ".json":
        raise HTTPException(status_code=400, detail="Only JSON files are supported")

    if not file_path.exists():
        # Return empty array if file doesn't exist yet
        return DataFileResponse(data=[], path=path, count=0)

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    try:
        content = file_path.read_text(encoding="utf-8")
        data = json.loads(content)
        if not isinstance(data, list):
            raise HTTPException(
                status_code=400, detail="JSON file must contain an array"
            )
        return DataFileResponse(data=data, path=path, count=len(data))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


@router.put("/data-content")
async def update_data_content(update: DataFileUpdate):
    """
    Update the content of a JSON data file.

    Creates the file and parent directories if they don't exist.

    Args:
        update: Contains path and new data array
    """
    import json

    work_dir = get_working_directory()
    if not work_dir:
        raise HTTPException(status_code=500, detail="Working directory not set")

    # Security: ensure path doesn't escape project directory
    file_path = work_dir / update.path
    try:
        file_path = file_path.resolve()
        work_dir_resolved = work_dir.resolve()
        if not str(file_path).startswith(str(work_dir_resolved)):
            raise HTTPException(
                status_code=403, detail="Access denied: path outside project"
            )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path")

    # Only allow JSON files
    if file_path.suffix.lower() != ".json":
        raise HTTPException(status_code=400, detail="Only JSON files are supported")

    # Create backup before writing
    if file_path.exists():
        _create_backup(file_path)

    try:
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write JSON with nice formatting
        content = json.dumps(update.data, ensure_ascii=False, indent=2)
        file_path.write_text(content, encoding="utf-8")

        return {
            "success": True,
            "message": "Data file updated successfully",
            "path": update.path,
            "count": len(update.data),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error writing file: {str(e)}")


@router.put("/file-content")
async def update_file_content(update: FileContentUpdate):
    """
    Update the content of a file.

    Args:
        update: Contains path and new content
    """
    work_dir = get_working_directory()
    if not work_dir:
        raise HTTPException(status_code=500, detail="Working directory not set")

    # Security: ensure path doesn't escape project directory
    file_path = work_dir / update.path
    try:
        file_path = file_path.resolve()
        work_dir_resolved = work_dir.resolve()
        if not str(file_path).startswith(str(work_dir_resolved)):
            raise HTTPException(
                status_code=403, detail="Access denied: path outside project"
            )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path")

    # Only allow writing to text files (markdown, txt, json)
    allowed_extensions = {".md", ".markdown", ".txt", ".json"}
    if file_path.suffix.lower() not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type not supported for writing. Allowed: {', '.join(sorted(allowed_extensions))}",
        )

    # Create backup before writing
    if file_path.exists():
        _create_backup(file_path)

    try:
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(update.content, encoding="utf-8")
        return {
            "success": True,
            "message": "File updated successfully",
            "path": update.path,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error writing file: {str(e)}")


@router.get("/files/{filename:path}")
async def serve_file(filename: str):
    """
    Serve a file from the files/ folder.

    Used for previewing images in the GUI.

    Args:
        filename: File name (within files/ folder)
    """
    from fastapi.responses import FileResponse

    work_dir = get_working_directory()
    if not work_dir:
        raise HTTPException(status_code=500, detail="Working directory not set")

    # Build file path
    file_path = work_dir / "files" / filename

    # Security: ensure path doesn't escape files directory
    try:
        file_path = file_path.resolve()
        files_dir = (work_dir / "files").resolve()
        if not str(file_path).startswith(str(files_dir)):
            raise HTTPException(
                status_code=403, detail="Access denied: path outside files folder"
            )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    # Determine media type
    extension = file_path.suffix.lower()
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
        ".ico": "image/x-icon",
        ".pdf": "application/pdf",
        ".md": "text/markdown",
        ".txt": "text/plain",
    }
    media_type = media_types.get(extension, "application/octet-stream")

    return FileResponse(file_path, media_type=media_type)


@router.get("/assets/{filepath:path}")
async def serve_niamoto_assets(filepath: str):
    """
    Serve static assets (CSS, JS, fonts) from Niamoto's publish/assets folder.

    Used for template preview to load stylesheets and scripts.

    Args:
        filepath: Path within the assets folder (e.g., "css/niamoto.css")
    """
    from fastapi.responses import FileResponse
    import importlib.resources

    # Get the assets directory from Niamoto package
    try:
        assets_path = importlib.resources.files("niamoto.publish") / "assets"
    except Exception:
        raise HTTPException(status_code=500, detail="Could not locate Niamoto assets")

    # Build file path
    file_path = Path(str(assets_path)) / filepath

    # Security: ensure path doesn't escape assets directory
    try:
        file_path = file_path.resolve()
        assets_dir = Path(str(assets_path)).resolve()
        if not str(file_path).startswith(str(assets_dir)):
            raise HTTPException(
                status_code=403, detail="Access denied: path outside assets folder"
            )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Asset not found: {filepath}")

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    # Determine media type
    extension = file_path.suffix.lower()
    media_types = {
        ".css": "text/css",
        ".js": "application/javascript",
        ".woff": "font/woff",
        ".woff2": "font/woff2",
        ".ttf": "font/ttf",
        ".eot": "application/vnd.ms-fontobject",
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".ico": "image/x-icon",
    }
    media_type = media_types.get(extension, "application/octet-stream")

    # Versioned vendor bundles are immutable — cache aggressively.
    headers = {}
    if "/vendor/" in filepath and file_path.suffix == ".js":
        headers["Cache-Control"] = "public, max-age=31536000, immutable"

    # Preview iframes use srcdoc (origin: null), so vendor assets loaded from
    # /api/site/assets must opt into cross-origin use explicitly.
    if extension in (".js", ".css", ".woff", ".woff2", ".ttf", ".eot"):
        headers["Access-Control-Allow-Origin"] = "*"

    return FileResponse(file_path, media_type=media_type, headers=headers)


# =============================================================================
# Import Endpoints (BibTeX, CSV)
# =============================================================================


class ImportResponse(BaseModel):
    """Response model for import operations."""

    success: bool
    data: List[Dict[str, Any]]
    count: int
    errors: List[str] = []


def _parse_bibtex_entry(entry_text: str) -> Optional[Dict[str, Any]]:
    """
    Parse a single BibTeX entry into a reference dictionary.

    Handles common BibTeX fields and maps them to our reference format.
    """
    import re

    # Extract entry type and key: @article{key,
    entry_match = re.match(r"@(\w+)\s*\{\s*([^,]+)\s*,", entry_text, re.IGNORECASE)
    if not entry_match:
        return None

    entry_type = entry_match.group(1).lower()
    # entry_key = entry_match.group(2)

    # Map BibTeX types to our types
    type_mapping = {
        "article": "article",
        "book": "book",
        "inbook": "chapter",
        "incollection": "chapter",
        "phdthesis": "thesis",
        "mastersthesis": "thesis",
        "techreport": "report",
        "inproceedings": "conference",
        "conference": "conference",
        "misc": "other",
        "unpublished": "other",
    }

    ref_type = type_mapping.get(entry_type, "other")

    # Extract fields using regex
    # Matches: field = {value} or field = "value" or field = value
    field_pattern = (
        r"(\w+)\s*=\s*(?:\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}|\"([^\"]*)\"|(\d+))"
    )
    fields = {}
    for match in re.finditer(field_pattern, entry_text, re.IGNORECASE):
        field_name = match.group(1).lower()
        field_value = match.group(2) or match.group(3) or match.group(4) or ""
        # Clean up the value (remove extra braces, normalize whitespace)
        field_value = re.sub(r"\s+", " ", field_value.strip())
        fields[field_name] = field_value

    # Build reference object
    reference = {
        "type": ref_type,
        "title": fields.get("title", ""),
        "authors": fields.get("author", "").replace(" and ", ", "),
        "year": fields.get("year", ""),
    }

    # Add optional fields
    if "journal" in fields:
        reference["journal"] = fields["journal"]
    elif "booktitle" in fields:
        reference["journal"] = fields["booktitle"]
    elif "school" in fields:
        reference["journal"] = fields["school"]
    elif "institution" in fields:
        reference["journal"] = fields["institution"]
    elif "publisher" in fields:
        reference["journal"] = fields["publisher"]

    if "volume" in fields:
        vol = fields["volume"]
        if "number" in fields:
            vol += f"({fields['number']})"
        reference["volume"] = vol

    if "pages" in fields:
        reference["pages"] = fields["pages"].replace("--", "-")

    if "doi" in fields:
        reference["doi"] = fields["doi"]

    if "url" in fields:
        reference["url"] = fields["url"]

    if "note" in fields:
        # Append note to journal info for context (e.g., "Master 2", "HDR")
        if "journal" in reference:
            reference["journal"] += f" — {fields['note']}"
        else:
            reference["journal"] = fields["note"]

    return reference


@router.post("/import-bibtex", response_model=ImportResponse)
async def import_bibtex(file: UploadFile = File(...)):
    """
    Import references from a BibTeX file.

    Parses a .bib file and converts entries to our reference format.

    Returns:
        List of parsed references with any parsing errors.
    """
    import re

    # Validate file type
    if not file.filename or not file.filename.endswith(".bib"):
        raise HTTPException(
            status_code=400, detail="Invalid file type. Expected .bib file."
        )

    try:
        content = await file.read()
        text = content.decode("utf-8", errors="replace")

        # Split into entries (each starts with @)
        # This regex finds @type{...} blocks, handling nested braces
        entries = []
        errors = []

        # Find all entry starts
        entry_starts = [m.start() for m in re.finditer(r"@\w+\s*\{", text)]

        for i, start in enumerate(entry_starts):
            # Find the matching closing brace
            end = start
            brace_count = 0
            in_entry = False

            for j, char in enumerate(text[start:], start):
                if char == "{":
                    brace_count += 1
                    in_entry = True
                elif char == "}":
                    brace_count -= 1
                    if in_entry and brace_count == 0:
                        end = j + 1
                        break

            entry_text = text[start:end]

            # Try to parse the entry
            try:
                ref = _parse_bibtex_entry(entry_text)
                if ref and ref.get("title"):  # Valid entry with title
                    entries.append(ref)
            except Exception as e:
                # Extract entry key for error reporting
                key_match = re.match(r"@\w+\s*\{\s*([^,]+)", entry_text)
                key = key_match.group(1) if key_match else f"entry_{i + 1}"
                errors.append(f"Error parsing '{key}': {str(e)}")

        return ImportResponse(
            success=len(entries) > 0,
            data=entries,
            count=len(entries),
            errors=errors,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing BibTeX file: {str(e)}"
        )


def _references_to_bibtex(references: List[Dict[str, Any]]) -> str:
    """
    Convert a list of reference dicts to BibTeX format.
    """
    # Reverse type mapping
    type_mapping = {
        "article": "article",
        "book": "book",
        "chapter": "incollection",
        "thesis": "phdthesis",
        "report": "techreport",
        "conference": "inproceedings",
        "other": "misc",
    }

    def make_key(ref: Dict[str, Any]) -> str:
        authors = ref.get("authors", "unknown")
        first_author = authors.split(",")[0].strip().split()[-1].lower()
        year = ref.get("year", "0000")
        title_word = (
            ref.get("title", "untitled").split()[0].lower()
            if ref.get("title")
            else "untitled"
        )
        return f"{first_author}{year}{title_word}"

    lines = []
    for ref in references:
        bib_type = type_mapping.get(ref.get("type", "other"), "misc")
        key = make_key(ref)

        lines.append(f"@{bib_type}{{{key},")
        if ref.get("authors"):
            # Convert "A, B, C" back to "A and B and C"
            authors = ref["authors"].replace(", ", " and ")
            lines.append(f"  author    = {{{authors}}},")
        if ref.get("title"):
            lines.append(f"  title     = {{{ref['title']}}},")
        if ref.get("year"):
            lines.append(f"  year      = {{{ref['year']}}},")
        if ref.get("journal"):
            if bib_type in ("inproceedings", "incollection"):
                lines.append(f"  booktitle = {{{ref['journal']}}},")
            elif bib_type in ("phdthesis", "mastersthesis"):
                lines.append(f"  school    = {{{ref['journal']}}},")
            else:
                lines.append(f"  journal   = {{{ref['journal']}}},")
        if ref.get("volume"):
            lines.append(f"  volume    = {{{ref['volume']}}},")
        if ref.get("pages"):
            lines.append(f"  pages     = {{{ref['pages'].replace('-', '--')}}},")
        if ref.get("doi"):
            lines.append(f"  doi       = {{{ref['doi']}}},")
        if ref.get("url"):
            lines.append(f"  url       = {{{ref['url']}}},")
        lines.append("}")
        lines.append("")

    return "\n".join(lines)


@router.post("/export-bibtex")
async def export_bibtex(references: List[Dict[str, Any]]):
    """
    Export references as a BibTeX file.

    Accepts a list of reference objects and returns a downloadable .bib file.
    """
    from fastapi.responses import Response

    bibtex_content = _references_to_bibtex(references)
    return Response(
        content=bibtex_content,
        media_type="application/x-bibtex",
        headers={"Content-Disposition": 'attachment; filename="references.bib"'},
    )


@router.post("/import-csv", response_model=ImportResponse)
async def import_csv(
    file: UploadFile = File(...),
    delimiter: str = ",",
    has_header: bool = True,
):
    """
    Import data from a CSV file.

    Parses a CSV file and returns it as a list of dictionaries.

    Args:
        file: The CSV file to import
        delimiter: Column delimiter (default: comma)
        has_header: Whether the first row contains column names (default: True)

    Returns:
        List of parsed rows as dictionaries.
    """
    import csv
    import io

    # Validate file type
    valid_extensions = (".csv", ".tsv", ".txt")
    if not file.filename or not any(
        file.filename.endswith(ext) for ext in valid_extensions
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Expected one of: {', '.join(valid_extensions)}",
        )

    try:
        content = await file.read()
        text = content.decode("utf-8", errors="replace")

        # Parse CSV
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        rows = list(reader)

        if not rows:
            return ImportResponse(
                success=False, data=[], count=0, errors=["Empty file"]
            )

        entries = []
        errors = []

        if has_header:
            # Use first row as column names
            headers = [h.strip().lower().replace(" ", "_") for h in rows[0]]
            for i, row in enumerate(rows[1:], 2):
                if len(row) != len(headers):
                    errors.append(
                        f"Row {i}: expected {len(headers)} columns, got {len(row)}"
                    )
                    # Pad or truncate to match headers
                    while len(row) < len(headers):
                        row.append("")
                    row = row[: len(headers)]

                entry = {headers[j]: val.strip() for j, val in enumerate(row)}
                entries.append(entry)
        else:
            # Use generic column names
            for i, row in enumerate(rows, 1):
                entry = {f"col_{j + 1}": val.strip() for j, val in enumerate(row)}
                entries.append(entry)

        return ImportResponse(
            success=len(entries) > 0,
            data=entries,
            count=len(entries),
            errors=errors,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing CSV file: {str(e)}"
        )
