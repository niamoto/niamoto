"""Site configuration API endpoints for managing export.yml site settings."""

from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, ConfigDict
import yaml
import shutil
from datetime import datetime

from ..context import get_working_directory

router = APIRouter()


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
    github_url: Optional[str] = None


class NavigationItem(BaseModel):
    """Navigation menu item."""

    text: str
    url: str


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
    static_pages: List[StaticPage]
    # Additional export params that aren't site-specific
    template_dir: str = "templates/"
    output_dir: str = "exports/web"
    copy_assets_from: List[str] = []


class SiteConfigUpdate(BaseModel):
    """Request model for updating site configuration."""

    site: SiteSettings
    navigation: List[NavigationItem]
    static_pages: List[StaticPage]
    template_dir: Optional[str] = None
    output_dir: Optional[str] = None
    copy_assets_from: Optional[List[str]] = None


class TemplatesResponse(BaseModel):
    """Response model for available templates."""

    templates: List[str]
    default_templates: List[str]
    project_templates: List[str]


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
    navigation = params.get("navigation", [])
    static_pages = web_pages.get("static_pages", [])

    # Convert raw dicts to models
    site = SiteSettings(**site_config) if site_config else SiteSettings()
    nav_items = [NavigationItem(**item) for item in navigation]

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
            "params": {},
            "static_pages": [],
            "groups": [],
        }
        exports.append(web_pages)

    # Update params
    params = web_pages.setdefault("params", {})
    params["site"] = update.site.model_dump(exclude_none=True)
    params["navigation"] = [item.model_dump() for item in update.navigation]

    if update.template_dir:
        params["template_dir"] = update.template_dir
    if update.output_dir:
        params["output_dir"] = update.output_dir
    if update.copy_assets_from is not None:
        params["copy_assets_from"] = update.copy_assets_from

    # Update static pages
    static_pages_data = []
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
        static_pages_data.append(page_dict)

    web_pages["static_pages"] = static_pages_data

    # Save configuration
    export_config["exports"] = exports
    saved_path = _save_export_config(export_config)

    return {
        "success": True,
        "message": "Site configuration updated successfully",
        "path": str(saved_path),
    }


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
                # Skip partials and layouts
                if not str(rel_path).startswith("_"):
                    project_templates.append(str(rel_path))

    # Default templates from Niamoto
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
        pass

    # Combine and deduplicate (project templates override defaults)
    all_templates = list(set(project_templates + default_templates))
    all_templates.sort()

    return TemplatesResponse(
        templates=all_templates,
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


@router.post("/preview-markdown", response_model=MarkdownPreviewResponse)
async def preview_markdown(request: MarkdownPreviewRequest):
    """
    Convert markdown to HTML for preview.

    Uses the same markdown renderer as the export system.
    """
    try:
        import markdown

        html = markdown.markdown(
            request.content,
            extensions=["tables", "fenced_code", "toc", "attr_list"],
        )
        return MarkdownPreviewResponse(html=html)
    except ImportError:
        # Fallback: basic conversion
        import html as html_escape

        escaped = html_escape.escape(request.content)
        # Very basic markdown-ish conversion
        html = escaped.replace("\n\n", "</p><p>").replace("\n", "<br>")
        html = f"<p>{html}</p>"
        return MarkdownPreviewResponse(html=html)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error converting markdown: {str(e)}"
        )


class FileUploadResponse(BaseModel):
    """Response model for file upload."""

    success: bool
    path: str
    filename: str


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

    # Validate file type for images
    allowed_extensions = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico"}
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed: {', '.join(allowed_extensions)}",
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
