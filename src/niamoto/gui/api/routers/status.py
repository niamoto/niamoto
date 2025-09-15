"""Status API endpoints for pipeline state monitoring."""

from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import yaml
from sqlalchemy import create_engine, text, inspect

router = APIRouter()


class ImportStatus(BaseModel):
    """Import phase status information."""

    configured: bool
    executed: bool
    last_run: Optional[datetime] = None
    records_imported: int = 0
    config_file: Optional[str] = None
    data_sources: List[str] = []


class TransformStatus(BaseModel):
    """Transform phase status information."""

    configured: bool
    executed: bool
    last_run: Optional[datetime] = None
    groups: List[str] = []
    config_file: Optional[str] = None


class ExportStatus(BaseModel):
    """Export phase status information."""

    configured: bool
    executed: bool
    last_run: Optional[datetime] = None
    exports: List[str] = []
    config_file: Optional[str] = None
    static_site_exists: bool = False


class PipelineStatus(BaseModel):
    """Overall pipeline status."""

    import_status: ImportStatus
    transform: TransformStatus
    export: ExportStatus
    database_exists: bool
    database_path: Optional[str] = None
    project_name: Optional[str] = None


def check_config_exists(config_name: str) -> tuple[bool, Optional[Path]]:
    """Check if a configuration file exists."""
    # Check in config/ directory first
    config_dir_path = Path.cwd() / "config" / f"{config_name}.yml"
    if config_dir_path.exists():
        return True, config_dir_path

    # Fall back to root directory
    config_path = Path.cwd() / f"{config_name}.yml"
    if config_path.exists():
        return True, config_path

    return False, None


def parse_import_config(config_path: Path) -> Dict[str, Any]:
    """Parse import configuration file."""
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            data_sources = []
            if config:
                # Direct format (e.g., taxonomy, plots, occurrences, shapes)
                for key, value in config.items():
                    if isinstance(value, dict):
                        if "path" in value:
                            data_sources.append(value["path"])
                        elif "file" in value:
                            data_sources.append(value["file"])
                    elif isinstance(value, list):
                        # Handle lists like shapes
                        for item in value:
                            if isinstance(item, dict):
                                if "path" in item:
                                    data_sources.append(item["path"])
                                elif "file" in item:
                                    data_sources.append(item["file"])
            return {
                "configured": True,
                "config_file": str(config_path),
                "data_sources": data_sources,
            }
    except Exception:
        return {"configured": False}


def parse_transform_config(config_path: Path) -> Dict[str, Any]:
    """Parse transform configuration file."""
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            groups = []
            if config and "groups" in config:
                groups = list(config["groups"].keys())
            return {
                "configured": True,
                "config_file": str(config_path),
                "groups": groups,
            }
    except Exception:
        return {"configured": False}


def parse_export_config(config_path: Path) -> Dict[str, Any]:
    """Parse export configuration file."""
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            exports = []
            static_site_exists = False

            if config:
                if "static_pages" in config:
                    static_site_exists = True
                    if isinstance(config["static_pages"], list):
                        for page in config["static_pages"]:
                            if "name" in page:
                                exports.append(f"page:{page['name']}")

                if "exports" in config:
                    for export_item in config["exports"]:
                        if "name" in export_item:
                            exports.append(f"export:{export_item['name']}")

            return {
                "configured": True,
                "config_file": str(config_path),
                "exports": exports,
                "static_site_exists": static_site_exists,
            }
    except Exception:
        return {"configured": False}


def check_database_status() -> Dict[str, Any]:
    """Check SQLite database status."""
    # Try multiple possible database locations
    possible_paths = [
        Path.cwd() / "db" / "niamoto.db",  # Standard location from config
        Path.cwd() / "niamoto.db",  # Root directory
        Path.cwd() / "data" / "niamoto.db",  # Alternative data directory
    ]

    db_path = None
    for path in possible_paths:
        if path.exists():
            db_path = path
            break

    if not db_path:
        return {
            "database_exists": False,
            "database_path": None,
            "import_executed": False,
            "transform_executed": False,
            "records_imported": 0,
        }

    try:
        engine = create_engine(f"sqlite:///{db_path}")
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        import_executed = False
        transform_executed = False
        records_imported = 0

        # Check for import tables
        if tables:
            import_executed = True

            # Try to count records in main tables
            with engine.connect() as conn:
                for table in ["occurrences", "data", "imports"]:  # Common table names
                    if table in tables:
                        try:
                            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                            count = result.scalar()
                            if count:
                                records_imported += count
                        except Exception:
                            pass

                # Check for transform tables/views
                views = []
                try:
                    result = conn.execute(
                        text("SELECT name FROM sqlite_master WHERE type='view'")
                    )
                    views = [row[0] for row in result]
                except Exception:
                    pass

                if views or any("_aggregated" in table for table in tables):
                    transform_executed = True

        engine.dispose()

        return {
            "database_exists": True,
            "database_path": str(db_path),
            "import_executed": import_executed,
            "transform_executed": transform_executed,
            "records_imported": records_imported,
        }
    except Exception:
        return {
            "database_exists": True,
            "database_path": str(db_path),
            "import_executed": False,
            "transform_executed": False,
            "records_imported": 0,
        }


def get_project_info() -> Dict[str, Any]:
    """Get project information from config.yml if it exists."""
    # Try config/config.yml first
    config_path = Path.cwd() / "config" / "config.yml"

    if not config_path.exists():
        # Try niamoto.yml in root
        config_path = Path.cwd() / "niamoto.yml"

    if not config_path.exists():
        return {"project_name": None}

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            # Look for project.name in the config structure
            if config:
                if "project" in config and "name" in config["project"]:
                    return {"project_name": config["project"]["name"]}
                elif "name" in config:
                    return {"project_name": config["name"]}
    except Exception:
        pass

    return {"project_name": None}


@router.get("/", response_model=PipelineStatus)
async def get_pipeline_status():
    """
    Get the current status of the entire pipeline.

    Returns information about:
    - Import configuration and execution status
    - Transform configuration and execution status
    - Export configuration and execution status
    - Database existence and statistics
    - Project information
    """
    try:
        # Check configuration files
        import_configured, import_path = check_config_exists("import")
        transform_configured, transform_path = check_config_exists("transform")
        export_configured, export_path = check_config_exists("export")

        # Parse configurations if they exist
        import_info = parse_import_config(import_path) if import_path else {}
        transform_info = (
            parse_transform_config(transform_path) if transform_path else {}
        )
        export_info = parse_export_config(export_path) if export_path else {}

        # Check database status
        db_status = check_database_status()

        # Get project info
        project_info = get_project_info()

        # Build import status
        import_status = ImportStatus(
            configured=import_configured,
            executed=db_status.get("import_executed", False),
            last_run=None,  # TODO: Track this in metadata table
            records_imported=db_status.get("records_imported", 0),
            config_file=import_info.get("config_file"),
            data_sources=import_info.get("data_sources", []),
        )

        # Build transform status
        transform_status = TransformStatus(
            configured=transform_configured,
            executed=db_status.get("transform_executed", False),
            last_run=None,  # TODO: Track this in metadata table
            groups=transform_info.get("groups", []),
            config_file=transform_info.get("config_file"),
        )

        # Build export status
        export_status = ExportStatus(
            configured=export_configured,
            executed=Path.cwd()
            .joinpath("output")
            .exists(),  # Check if output directory exists
            last_run=None,  # TODO: Track this in metadata table
            exports=export_info.get("exports", []),
            config_file=export_info.get("config_file"),
            static_site_exists=export_info.get("static_site_exists", False),
        )

        # Build overall status
        status = PipelineStatus(
            import_status=import_status,
            transform=transform_status,
            export=export_status,
            database_exists=db_status.get("database_exists", False),
            database_path=db_status.get("database_path"),
            project_name=project_info.get("project_name"),
        )

        return status

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving pipeline status: {str(e)}"
        )


@router.get("/import")
async def get_import_status() -> ImportStatus:
    """Get detailed import phase status."""
    status = await get_pipeline_status()
    return status.import_status


@router.get("/transform")
async def get_transform_status() -> TransformStatus:
    """Get detailed transform phase status."""
    status = await get_pipeline_status()
    return status.transform


@router.get("/export")
async def get_export_status() -> ExportStatus:
    """Get detailed export phase status."""
    status = await get_pipeline_status()
    return status.export
