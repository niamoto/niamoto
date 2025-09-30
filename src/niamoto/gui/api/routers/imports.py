"""Import API endpoints for validating and executing imports."""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks, Form
from pydantic import BaseModel, Field
from pathlib import Path
import tempfile
import uuid
import json
from datetime import datetime
from niamoto.common.config import Config
from niamoto.common.database import Database
from niamoto.common.exceptions import ConfigurationError, ValidationError, FileError
from niamoto.core.services.importer import ImporterService
from niamoto.gui.api.utils.import_fields import (
    get_required_fields_for_import_type,
    get_all_import_types_info,
)
from niamoto.gui.api.utils.config_updater import (
    update_import_config,
    clean_unused_config,
)
from niamoto.core.plugins.registry import PluginRegistry
from niamoto.core.plugins.base import PluginType

router = APIRouter()

# Import status tracking (in production, use a database)
import_jobs: Dict[str, Dict[str, Any]] = {}


def parse_import_metrics(result_text: str) -> dict:
    """Parse import result text into structured metrics."""
    import re

    metrics = {"taxonomy": 0, "occurrences": 0, "plots": 0, "shapes": 0}

    # Parse taxonomy
    taxon_match = re.search(
        r"(\d+)\s+taxons?\s+(?:extracted|imported)", result_text, re.IGNORECASE
    )
    if taxon_match:
        metrics["taxonomy"] = int(taxon_match.group(1))

    # Parse occurrences
    occ_match = re.search(
        r"(\d+)\s+occurrences?\s+imported", result_text, re.IGNORECASE
    )
    if occ_match:
        metrics["occurrences"] = int(occ_match.group(1))

    # Parse plots
    plot_match = re.search(r"(\d+)\s+plots?\s+imported", result_text, re.IGNORECASE)
    if plot_match:
        metrics["plots"] = int(plot_match.group(1))

    # Parse shapes
    shape_match = re.search(
        r"(\d+)\s+processed(?:,\s+\d+\s+added)?", result_text, re.IGNORECASE
    )
    if shape_match:
        metrics["shapes"] = int(shape_match.group(1))

    return metrics


class ImportStatus(BaseModel):
    """Status of a particular import type."""

    import_type: str
    is_imported: bool
    row_count: int = 0
    dependencies_met: bool = True
    missing_dependencies: List[str] = Field(default_factory=list)


class ImportStatusResponse(BaseModel):
    """Response containing status of all imports."""

    taxonomy: ImportStatus
    occurrences: ImportStatus
    plots: ImportStatus
    shapes: ImportStatus


class ImportValidationRequest(BaseModel):
    """Request model for import validation."""

    import_type: str = Field(
        ..., description="Type of import: taxonomy, plots, occurrences, shapes"
    )
    file_name: str = Field(..., description="Name of the file to import")
    field_mappings: Dict[str, str] = Field(
        ..., description="Mapping of database fields to file columns"
    )
    advanced_options: Optional[Dict[str, Any]] = Field(
        default=None, description="Advanced import options"
    )


class ImportExecutionRequest(BaseModel):
    """Request model for import execution."""

    import_type: str
    file_name: str
    field_mappings: Dict[str, str]
    advanced_options: Optional[Dict[str, Any]] = None
    validate_only: bool = Field(
        default=False, description="Only validate without executing"
    )


class ImportValidationResponse(BaseModel):
    """Response model for import validation."""

    valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    summary: Dict[str, Any] = {}


class ImportJobResponse(BaseModel):
    """Response model for import job creation."""

    job_id: str
    status: str
    created_at: str
    message: str


@router.post("/validate", response_model=ImportValidationResponse)
async def validate_import(
    file: UploadFile = File(...),
    import_type: str = Form(...),
    file_name: str = Form(...),
    field_mappings: str = Form(...),
    advanced_options: Optional[str] = Form(None),
) -> ImportValidationResponse:
    """Validate an import configuration without executing it."""

    # Parse JSON fields
    try:
        field_mappings_dict = json.loads(field_mappings) if field_mappings else {}
        advanced_options_dict = json.loads(advanced_options) if advanced_options else {}
    except json.JSONDecodeError:
        return ImportValidationResponse(
            valid=False,
            errors=["Invalid JSON in field mappings or advanced options"],
            summary={},
        )

    errors = []
    warnings = []
    summary = {
        "import_type": import_type,
        "file_name": file_name,
        "mapped_fields": len(field_mappings_dict),
    }

    # Validate import type
    valid_types = ["taxonomy", "plots", "occurrences", "shapes"]
    if import_type not in valid_types:
        errors.append(f"Invalid import type: {import_type}")

    # Validate required fields are mapped
    required_fields = get_required_fields(import_type)
    missing_fields = []

    for field in required_fields:
        if field not in field_mappings_dict:
            missing_fields.append(field)

    if missing_fields:
        errors.append(f"Missing required field mappings: {', '.join(missing_fields)}")

    # Validate file
    if file.size == 0:
        errors.append("File is empty")
    elif file.size > 100 * 1024 * 1024:  # 100MB limit
        warnings.append(
            f"Large file size ({file.size / 1024 / 1024:.1f}MB) may take time to process"
        )

    # Type-specific validation
    if import_type == "taxonomy":
        validate_taxonomy_options(advanced_options_dict, errors, warnings)
    elif import_type == "plots":
        validate_plots_options(advanced_options_dict, errors, warnings)
    elif import_type == "occurrences":
        validate_occurrences_options(advanced_options_dict, errors, warnings)
    elif import_type == "shapes":
        validate_shapes_options(advanced_options_dict, errors, warnings)

    # Add summary statistics
    summary["validation_errors"] = len(errors)
    summary["validation_warnings"] = len(warnings)

    return ImportValidationResponse(
        valid=len(errors) == 0, errors=errors, warnings=warnings, summary=summary
    )


@router.post("/execute", response_model=ImportJobResponse)
async def execute_import(
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(None),
    import_type: str = Form(...),
    file_name: str = Form(...),
    field_mappings: str = Form(...),
    advanced_options: Optional[str] = Form(None),
    validate_only: bool = Form(False),
    use_config_file: Optional[str] = Form(None),
) -> ImportJobResponse:
    """Execute an import job asynchronously."""

    # Parse JSON fields
    try:
        field_mappings_dict = json.loads(field_mappings) if field_mappings else {}
        advanced_options_dict = json.loads(advanced_options) if advanced_options else {}
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400, detail="Invalid JSON in field mappings or advanced options"
        )

    # Generate job ID
    job_id = str(uuid.uuid4())

    # Get the project imports directory
    project_dir = Path(Config.get_niamoto_home())
    imports_dir = project_dir / "imports"
    imports_dir.mkdir(exist_ok=True)

    # Create job record first (needed for both paths)
    job = {
        "id": job_id,
        "status": "pending",
        "import_type": import_type,
        "file_name": file_name,
        "file_path": "",  # Will be set later
        "field_mappings": field_mappings_dict,
        "advanced_options": advanced_options_dict,
        "created_at": datetime.utcnow().isoformat(),
        "started_at": None,
        "completed_at": None,
        "progress": 0,
        "total_records": 0,
        "processed_records": 0,
        "errors": [],
        "warnings": [],
    }

    import_jobs[job_id] = job

    # Handle file path based on whether we have an upload or use existing config
    if use_config_file == "true" and import_type == "all":
        # Special case: run full import using the ImporterService directly
        import asyncio

        async def run_full_import():
            """Run the full import using ImporterService directly."""
            import os

            print(f"Starting full import for job {job_id}")

            try:
                # Update job status
                import_jobs[job_id]["status"] = "running"
                import_jobs[job_id]["started_at"] = datetime.utcnow().isoformat()
                import_jobs[job_id]["progress"] = 10
                import_jobs[job_id]["message"] = "Starting full data import..."

                # Get configuration
                config = Config()
                imports_config = config.imports

                # Create a single ImporterService instance to reuse
                importer = ImporterService(config.database_path)

                # Collect all import results for summary
                import_results = []
                total_records = 0

                # Helper function to reset table
                def reset_table(db_path: str, table_name: str) -> None:
                    """Reset a single table and recreate it."""
                    from niamoto.core.models import Base
                    from sqlalchemy import create_engine

                    db = Database(db_path)
                    try:
                        # Drop the table
                        db.execute_sql(f"DROP TABLE IF EXISTS {table_name}")

                        # Recreate the table using SQLAlchemy models
                        engine = create_engine(f"sqlite:///{db_path}")
                        # Create all tables if needed (they will be created only if they don't exist)
                        if table_name in Base.metadata.tables:
                            Base.metadata.tables[table_name].create(
                                engine, checkfirst=True
                            )
                        else:
                            # For tables not in metadata, create them all
                            Base.metadata.create_all(engine)
                    except Exception as e:
                        print(f"Failed to reset table {table_name}: {str(e)}")

                # Helper function to validate source config
                def validate_source_config(sources, source_name, required_fields):
                    """Validate source configuration."""
                    source = sources.get(source_name)
                    if not source:
                        raise ConfigurationError(
                            config_key=f"imports.{source_name}",
                            message=f"Missing {source_name} configuration",
                        )

                    missing_fields = [f for f in required_fields if f not in source]
                    if missing_fields:
                        raise ValidationError(
                            field=source_name,
                            message=f"Missing required fields: {missing_fields}",
                        )

                    return source

                # Import taxonomy
                import_jobs[job_id]["progress"] = 15
                import_jobs[job_id]["message"] = "Preparing taxonomy import..."
                print(f"Job {job_id}: Starting taxonomy import")

                source_def = validate_source_config(
                    imports_config, "taxonomy", ["path", "hierarchy"]
                )
                file_path = source_def.get("path")
                hierarchy_config = source_def.get("hierarchy")

                # Validate file path
                if not os.path.exists(file_path):
                    raise FileError(
                        file_path=file_path,
                        message="File not found",
                        details={"path": file_path},
                    )

                api_config = None
                if source_def.get("api_enrichment", {}).get("enabled", False):
                    api_config = source_def.get("api_enrichment", {})
                    api_config["enabled"] = True

                import_jobs[job_id]["progress"] = 20
                import_jobs[job_id]["message"] = "Resetting taxonomy table..."
                await asyncio.to_thread(reset_table, config.database_path, "taxon_ref")

                import_jobs[job_id]["progress"] = 25
                import_jobs[job_id]["message"] = "Importing taxonomy data..."
                result = await asyncio.to_thread(
                    importer.import_taxonomy, file_path, hierarchy_config, api_config
                )

                # Parse taxonomy result
                import re

                taxon_match = re.search(r"(\d+) taxa imported", result)
                taxon_count = 0
                if taxon_match:
                    taxon_count = int(taxon_match.group(1))
                    total_records += taxon_count
                    import_jobs[job_id]["message"] = f"Imported {taxon_count} taxa"

                import_jobs[job_id]["progress"] = 30
                import_results.append(result)
                print(f"Job {job_id}: Taxonomy import completed - {taxon_count} taxa")

                # Import occurrences
                import_jobs[job_id]["progress"] = 35
                import_jobs[job_id]["message"] = "Preparing occurrences import..."
                print(f"Job {job_id}: Starting occurrences import")

                source_def = validate_source_config(
                    imports_config,
                    "occurrences",
                    ["path", "identifier", "location_field"],
                )
                file_path = source_def.get("path")
                taxon_id = source_def.get("identifier")
                location_field = source_def.get("location_field")

                import_jobs[job_id]["progress"] = 40
                import_jobs[job_id]["message"] = "Resetting occurrences table..."
                await asyncio.to_thread(
                    reset_table, config.database_path, "occurrences"
                )

                import_jobs[job_id]["progress"] = 45
                import_jobs[job_id]["message"] = "Importing occurrences data..."
                result = await asyncio.to_thread(
                    importer.import_occurrences, file_path, taxon_id, location_field
                )

                # Parse occurrences result
                occ_match = re.search(r"(\d+) occurrences imported", result)
                occ_count = 0
                if occ_match:
                    occ_count = int(occ_match.group(1))
                    total_records += occ_count
                    import_jobs[job_id]["message"] = f"Imported {occ_count} occurrences"

                import_jobs[job_id]["progress"] = 55
                import_results.append(result)
                print(
                    f"Job {job_id}: Occurrences import completed - {occ_count} occurrences"
                )

                # Import plots
                import_jobs[job_id]["progress"] = 60
                import_jobs[job_id]["message"] = "Preparing plots import..."
                print(f"Job {job_id}: Starting plots import")

                source_def = validate_source_config(
                    imports_config,
                    "plots",
                    ["path", "identifier", "location_field", "locality_field"],
                )
                file_path = source_def.get("path")
                id_field = source_def.get("identifier")
                location_field = source_def.get("location_field")
                locality_field = source_def.get("locality_field")
                link_field = source_def.get("link_field")
                occurrence_link_field = source_def.get("occurrence_link_field")
                hierarchy_config = source_def.get("hierarchy")

                import_jobs[job_id]["progress"] = 65
                import_jobs[job_id]["message"] = "Resetting plots table..."
                await asyncio.to_thread(reset_table, config.database_path, "plot_ref")

                import_jobs[job_id]["progress"] = 70
                import_jobs[job_id]["message"] = "Importing plots data..."
                result = await asyncio.to_thread(
                    importer.import_plots,
                    file_path,
                    id_field,
                    location_field,
                    locality_field,
                    link_field=link_field,
                    occurrence_link_field=occurrence_link_field,
                    hierarchy_config=hierarchy_config,
                )

                # Parse plots result
                plot_match = re.search(r"(\d+) plots imported", result)
                plot_count = 0
                if plot_match:
                    plot_count = int(plot_match.group(1))
                    total_records += plot_count
                    import_jobs[job_id]["message"] = f"Imported {plot_count} plots"

                import_jobs[job_id]["progress"] = 75
                import_results.append(result)
                print(f"Job {job_id}: Plots import completed - {plot_count} plots")

                # Import shapes
                import_jobs[job_id]["progress"] = 80
                import_jobs[job_id]["message"] = "Preparing shapes import..."
                print(f"Job {job_id}: Starting shapes import")

                shapes_config = imports_config.get("shapes", [])
                if shapes_config and isinstance(shapes_config, list):
                    import_jobs[job_id]["progress"] = 85
                    import_jobs[job_id]["message"] = (
                        f"Importing {len(shapes_config)} shape layers..."
                    )
                    print(
                        f"Job {job_id}: Found {len(shapes_config)} shape layers to import"
                    )

                    # Reset shape table first
                    try:
                        await asyncio.to_thread(
                            reset_table, config.database_path, "shape_ref"
                        )
                    except Exception as e:
                        print(f"Warning: Could not reset shape_ref table: {e}")

                    import_jobs[job_id]["progress"] = 87
                    import_jobs[job_id]["message"] = "Processing shape files..."

                    try:
                        # Import shapes with a timeout
                        result = await asyncio.wait_for(
                            asyncio.to_thread(importer.import_shapes, shapes_config),
                            timeout=300,  # 5 minutes timeout
                        )

                        # Parse shapes result
                        shape_match = re.search(r"(\d+) shapes imported", result)
                        shape_count = 0
                        if shape_match:
                            shape_count = int(shape_match.group(1))
                            total_records += shape_count

                        import_jobs[job_id]["message"] = (
                            f"Imported {shape_count} shapes from {len(shapes_config)} layers"
                        )
                        import_results.append(result)
                        print(
                            f"Job {job_id}: Shapes import completed - {shape_count} shapes from {len(shapes_config)} layers"
                        )

                    except asyncio.TimeoutError:
                        print(f"Job {job_id}: Shapes import timed out after 5 minutes")
                        import_jobs[job_id]["message"] = "Shapes import timed out"
                        import_results.append("Shapes import timed out after 5 minutes")
                    except Exception as e:
                        print(f"Job {job_id}: Error importing shapes: {e}")
                        import_jobs[job_id]["message"] = (
                            f"Error importing shapes: {str(e)}"
                        )
                        import_results.append(f"Shapes import error: {str(e)}")

                    import_jobs[job_id]["progress"] = 95
                else:
                    import_jobs[job_id]["progress"] = 95
                    import_jobs[job_id]["message"] = "No shapes to import"
                    print(f"Job {job_id}: No shapes configuration found")

                # Mark as completed
                import_jobs[job_id]["status"] = "completed"
                import_jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
                import_jobs[job_id]["progress"] = 100

                # Parse results into structured format
                result_summary = "\n".join(import_results)
                import_jobs[job_id]["result"] = {
                    "metrics": parse_import_metrics(result_summary),
                    "summary": result_summary,
                }

                import_jobs[job_id]["processed_records"] = total_records
                import_jobs[job_id]["total_records"] = total_records
                import_jobs[job_id]["message"] = (
                    f"Import completed successfully. {total_records} records imported."
                )

                print(f"Import completed successfully. Total records: {total_records}")

            except Exception as e:
                import_jobs[job_id]["status"] = "failed"
                import_jobs[job_id]["errors"].append(str(e))
                import_jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
                import_jobs[job_id]["message"] = f"Import failed: {str(e)}"
                print(f"Import failed: {str(e)}")

        # Queue the full import task
        background_tasks.add_task(run_full_import)

        return ImportJobResponse(
            job_id=job_id,
            status="pending",
            created_at=job["created_at"],
            message=f"Import job {job_id} created successfully (full pipeline mode)",
        )

    elif use_config_file == "true":
        # Use the file from config
        # Remove 'imports/' prefix if present as we're already in the imports directory
        clean_file_name = (
            file_name.replace("imports/", "")
            if file_name.startswith("imports/")
            else file_name
        )
        file_path = imports_dir / clean_file_name

        # Check if the file exists
        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Configuration file not found: {clean_file_name}",
            )

        # Create a temp copy for the job
        temp_dir = Path(tempfile.gettempdir()) / "niamoto_imports"
        temp_dir.mkdir(exist_ok=True)
        temp_file_path = temp_dir / f"{job_id}_{clean_file_name}"

        # Copy existing file to temp
        import shutil

        shutil.copy(file_path, temp_file_path)

    else:
        # Handle uploaded file
        if not file:
            raise HTTPException(
                status_code=400,
                detail="File is required when not using configuration file",
            )

        # Save uploaded file to imports directory
        file_path = imports_dir / file.filename
        content = await file.read()

        with open(file_path, "wb") as f:
            f.write(content)

        # Also keep a temp copy for the job
        temp_dir = Path(tempfile.gettempdir()) / "niamoto_imports"
        temp_dir.mkdir(exist_ok=True)
        temp_file_path = temp_dir / f"{job_id}_{file.filename}"

        with open(temp_file_path, "wb") as f:
            f.write(content)

    # Update import.yml configuration
    import_config_path = project_dir / "config" / "import.yml"
    try:
        # Only update config for new uploads, not when using existing config
        if use_config_file != "true":
            # Clean unused config when starting a new import session (occurrences is always first)
            if import_type == "occurrences":
                clean_unused_config(import_config_path)

            update_import_config(
                import_config_path,
                import_type,
                file.filename if file else file_name,
                field_mappings_dict,
                advanced_options_dict,
            )
    except Exception:
        # Log error but don't fail the import
        pass  # Log error but don't fail the import

    # Update job with file_path (job already created above)
    job["file_path"] = str(file_path)

    # Queue background import task
    background_tasks.add_task(
        process_import,
        job_id,
        import_type,
        str(file_path),
        field_mappings_dict,
        advanced_options_dict,
        str(temp_file_path),  # Pass temp file path for cleanup
    )

    return ImportJobResponse(
        job_id=job_id,
        status="pending",
        created_at=job["created_at"],
        message=f"Import job {job_id} created successfully",
    )


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str) -> Dict[str, Any]:
    """Get the status of an import job."""

    if job_id not in import_jobs:
        raise HTTPException(status_code=404, detail=f"Import job {job_id} not found")

    return import_jobs[job_id]


@router.get("/jobs")
async def list_import_jobs(
    limit: int = 10, offset: int = 0, status: Optional[str] = None
) -> Dict[str, Any]:
    """List all import jobs with optional filtering."""

    jobs = list(import_jobs.values())

    # Filter by status if provided
    if status:
        jobs = [j for j in jobs if j["status"] == status]

    # Sort by created_at descending
    jobs.sort(key=lambda x: x["created_at"], reverse=True)

    # Apply pagination
    total = len(jobs)
    jobs = jobs[offset : offset + limit]

    return {"total": total, "limit": limit, "offset": offset, "jobs": jobs}


@router.get("/required-fields/{import_type}")
async def get_required_fields_api(import_type: str) -> Dict[str, Any]:
    """Get required fields for a specific import type dynamically from Niamoto."""

    valid_types = ["taxonomy", "plots", "occurrences", "shapes"]
    if import_type not in valid_types:
        raise HTTPException(
            status_code=400, detail=f"Invalid import type: {import_type}"
        )

    return get_required_fields_for_import_type(import_type)


@router.get("/required-fields")
async def get_all_required_fields() -> Dict[str, Any]:
    """Get required fields for all import types."""
    return get_all_import_types_info()


@router.get("/table-fields/{table_name}")
async def get_table_fields(table_name: str) -> Dict[str, Any]:
    """Get fields from a specific table in the database."""

    valid_tables = ["occurrences", "plot_ref", "taxon_ref", "shape_ref"]
    if table_name not in valid_tables:
        raise HTTPException(status_code=400, detail=f"Invalid table name: {table_name}")

    try:
        config = Config()
        db = Database(config.database_path)

        # Check if table exists
        table_check = db.execute_sql(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'",
            fetch=True,
        )

        if not table_check:
            return {"exists": False, "fields": []}

        # Get table schema
        schema_query = f"PRAGMA table_info({table_name})"
        schema = db.execute_sql(schema_query, fetch=True)

        fields = []
        for row in schema:
            # row format: (cid, name, type, notnull, dflt_value, pk)
            if hasattr(row, "_asdict"):
                field_info = row._asdict()
                field_name = field_info.get("name")
                field_type = field_info.get("type")
            else:
                field_name = row[1] if len(row) > 1 else None
                field_type = row[2] if len(row) > 2 else None

            if field_name:
                fields.append(
                    {
                        "name": field_name,
                        "type": field_type,
                    }
                )

        return {"exists": True, "fields": fields}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error reading table schema: {str(e)}"
        )


@router.get("/status", response_model=ImportStatusResponse)
async def get_import_status() -> ImportStatusResponse:
    """Check which imports have been completed and their dependencies."""

    try:
        # Get database configuration
        config = Config()
        db = Database(config.database_path)

        # Check each table's existence and row count
        tables_info = {}

        # Define table names and their dependencies
        table_config = {
            "taxon_ref": {"name": "taxonomy", "dependencies": []},
            "occurrences": {"name": "occurrences", "dependencies": ["taxon_ref"]},
            "plot_ref": {"name": "plots", "dependencies": []},
            "shape_ref": {"name": "shapes", "dependencies": []},
        }

        for table_name, config_info in table_config.items():
            try:
                # First check if table exists using sqlite_master
                table_check = db.execute_sql(
                    f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'",
                    fetch=True,
                )

                if table_check:
                    # Table exists, get row count
                    result = db.execute_sql(
                        f"SELECT COUNT(*) FROM {table_name}", fetch=True
                    )
                    tables_info[config_info["name"]] = {
                        "exists": True,
                        "row_count": result[0] if result else 0,
                    }
                else:
                    # Table doesn't exist
                    tables_info[config_info["name"]] = {"exists": False, "row_count": 0}
            except Exception:
                # Fallback in case of any other error
                tables_info[config_info["name"]] = {"exists": False, "row_count": 0}

        # Build response with dependency checking
        response = ImportStatusResponse(
            taxonomy=ImportStatus(
                import_type="taxonomy",
                is_imported=tables_info["taxonomy"]["exists"]
                and tables_info["taxonomy"]["row_count"] > 0,
                row_count=tables_info["taxonomy"]["row_count"],
                dependencies_met=True,
                missing_dependencies=[],
            ),
            occurrences=ImportStatus(
                import_type="occurrences",
                is_imported=tables_info["occurrences"]["exists"]
                and tables_info["occurrences"]["row_count"] > 0,
                row_count=tables_info["occurrences"]["row_count"],
                dependencies_met=tables_info["taxonomy"]["exists"]
                and tables_info["taxonomy"]["row_count"] > 0,
                missing_dependencies=[]
                if (
                    tables_info["taxonomy"]["exists"]
                    and tables_info["taxonomy"]["row_count"] > 0
                )
                else ["taxonomy"],
            ),
            plots=ImportStatus(
                import_type="plots",
                is_imported=tables_info["plots"]["exists"]
                and tables_info["plots"]["row_count"] > 0,
                row_count=tables_info["plots"]["row_count"],
                dependencies_met=True,  # Plots can be imported independently
                missing_dependencies=[],
            ),
            shapes=ImportStatus(
                import_type="shapes",
                is_imported=tables_info["shapes"]["exists"]
                and tables_info["shapes"]["row_count"] > 0,
                row_count=tables_info["shapes"]["row_count"],
                dependencies_met=True,  # Shapes are independent
                missing_dependencies=[],
            ),
        )

        return response

    except Exception:
        # Return empty status on error
        return ImportStatusResponse(
            taxonomy=ImportStatus(import_type="taxonomy", is_imported=False),
            occurrences=ImportStatus(
                import_type="occurrences",
                is_imported=False,
                dependencies_met=False,
                missing_dependencies=["taxonomy"],
            ),
            plots=ImportStatus(import_type="plots", is_imported=False),
            shapes=ImportStatus(import_type="shapes", is_imported=False),
        )


def get_required_fields(import_type: str) -> List[str]:
    """Get required fields for each import type dynamically."""

    # Use the dynamic field extraction
    field_info = get_required_fields_for_import_type(import_type)
    required_fields = []

    for field in field_info.get("fields", []):
        if field.get("required", False):
            required_fields.append(field["key"])

    return required_fields


def validate_taxonomy_options(
    options: Optional[Dict[str, Any]], errors: List[str], warnings: List[str]
):
    """Validate taxonomy-specific options."""

    # If no options or empty options, that's OK - we'll use defaults
    if not options:
        return

    # Validate ranks only if they are provided
    ranks = options.get("ranks", [])
    if ranks and len(ranks) < 1:
        errors.append(
            "At least 1 taxonomic rank must be specified when ranks are provided"
        )
    elif ranks and len(ranks) < 2:
        warnings.append(
            "Consider using at least 2 taxonomic ranks for a proper hierarchy"
        )

    # Validate API enrichment if present
    api_config = options.get("apiEnrichment", {})
    if api_config.get("enabled"):
        # Check required fields
        if not api_config.get("api_url"):
            errors.append("API URL is required when API enrichment is enabled")

        if not api_config.get("query_field"):
            errors.append("Query field is required for API enrichment")

        # Validate auth method
        auth_method = api_config.get("auth_method", "none")
        if auth_method == "api_key":
            auth_params = api_config.get("auth_params", {})
            if not auth_params.get("key"):
                errors.append("API key is required for API key authentication")

        # Check rate limit
        rate_limit = api_config.get("rate_limit", 2.0)
        if rate_limit > 10:
            warnings.append("High API rate limit may cause rate limiting from provider")


def validate_plots_options(
    options: Optional[Dict[str, Any]], errors: List[str], warnings: List[str]
):
    """Validate plots-specific options."""

    if not options:
        return

    # Validate hierarchy configuration
    hierarchy = options.get("hierarchy", {})
    if hierarchy.get("enabled"):
        levels = hierarchy.get("levels", [])
        if not levels:
            errors.append("At least one hierarchy level must be specified")
        elif len(levels) < 2:
            warnings.append(
                "Hierarchy typically requires at least 2 levels (e.g., plot and locality)"
            )

    # Validate linking fields
    link_field = options.get("linkField")
    occurrence_link_field = options.get("occurrenceLinkField")

    if link_field and not occurrence_link_field:
        warnings.append(
            "Consider specifying occurrence_link_field for automatic occurrence linking"
        )
    elif occurrence_link_field and not link_field:
        warnings.append(
            "link_field should be specified when using occurrence_link_field"
        )


def validate_occurrences_options(
    options: Optional[Dict[str, Any]], errors: List[str], warnings: List[str]
):
    """Validate occurrences-specific options."""

    if not options:
        return

    duplicate_strategy = options.get("duplicateStrategy", "skip")
    if duplicate_strategy not in ["skip", "update", "error"]:
        errors.append(f"Invalid duplicate strategy: {duplicate_strategy}")


def validate_shapes_options(
    options: Optional[Dict[str, Any]], errors: List[str], warnings: List[str]
):
    """Validate shapes-specific options."""

    if not options:
        return

    if options.get("simplifyGeometry"):
        tolerance = options.get("toleranceMeters", 10)
        if tolerance > 100:
            warnings.append(
                "High simplification tolerance may result in loss of detail"
            )


async def process_import(
    job_id: str,
    import_type: str,
    file_path: str,
    field_mappings: Dict[str, str],
    advanced_options: Optional[Dict[str, Any]],
    temp_file_path: Optional[str] = None,
):
    """Process import in background."""
    from niamoto.common.config import Config
    from niamoto.core.services.importer import ImporterService
    from niamoto.common.progress import set_progress_mode
    import asyncio

    # Disable progress bars in API mode to avoid Rich display conflicts
    set_progress_mode(use_progress_bar=False)

    job = import_jobs[job_id]

    try:
        # Update job status
        job["status"] = "running"
        job["started_at"] = datetime.utcnow().isoformat()

        # Get config and create importer
        config = Config()
        importer = ImporterService(config.database_path)

        # Process based on import type
        if import_type == "taxonomy":
            # Build hierarchy configuration from field mappings and advanced options
            hierarchy_config = {"levels": []}

            # Extract ranks from advanced options
            if advanced_options:
                ranks = advanced_options.get(
                    "ranks", ["family", "genus", "species", "infra"]
                )
                api_config = advanced_options.get("apiEnrichment")
            else:
                ranks = ["family", "genus", "species", "infra"]
                api_config = None

            # Build levels from ranks and field mappings
            for rank in ranks:
                if rank in field_mappings:
                    hierarchy_config["levels"].append(
                        {"name": rank, "column": field_mappings[rank]}
                    )

            # Add special columns if mapped
            if "taxon_id" in field_mappings:
                hierarchy_config["taxon_id_column"] = field_mappings["taxon_id"]
            if "authors" in field_mappings:
                hierarchy_config["authors_column"] = field_mappings["authors"]

            # Use new import_taxonomy method
            result = await asyncio.to_thread(
                importer.import_taxonomy,
                file_path,
                hierarchy_config,
                api_config if api_config and api_config.get("enabled") else None,
            )

            # Parse result for record count
            import re

            match = re.search(r"(\d+) taxons", result)
            if match:
                job["processed_records"] = int(match.group(1))
                job["total_records"] = int(match.group(1))

        elif import_type == "occurrences":
            # Handle occurrences import
            result = await asyncio.to_thread(
                importer.import_occurrences,
                file_path,
                field_mappings.get("taxon_id", "taxon_id"),
                field_mappings.get("location", "location"),
            )

            # Parse result for record count
            import re

            match = re.search(r"(\d+) occurrences imported", result)
            if match:
                job["processed_records"] = int(match.group(1))
                job["total_records"] = int(match.group(1))

        elif import_type == "plots":
            # Handle plots import
            # Convert GUI hierarchy config to Niamoto format
            hierarchy_config = None
            if advanced_options:
                gui_hierarchy = advanced_options.get("hierarchy", {})
                if gui_hierarchy.get("enabled") and gui_hierarchy.get("levels"):
                    hierarchy_config = {
                        "enabled": True,
                        "levels": gui_hierarchy["levels"],
                        "aggregate_geometry": gui_hierarchy.get(
                            "aggregate_geometry", True
                        ),
                    }

            result = await asyncio.to_thread(
                importer.import_plots,
                file_path,
                field_mappings.get("identifier", "id"),
                field_mappings.get("location", "location"),
                field_mappings.get("locality", "locality"),
                advanced_options.get("linkField") if advanced_options else None,
                advanced_options.get("occurrenceLinkField")
                if advanced_options
                else None,
                hierarchy_config,
            )

            # Parse result for record count
            import re

            match = re.search(r"(\d+) plots imported", result)
            if match:
                job["processed_records"] = int(match.group(1))
                job["total_records"] = int(match.group(1))

        elif import_type == "shapes":
            # Handle shapes import
            # Get shape type from advanced_options.shape_type (sent by GUI)
            shape_type = "default"
            if advanced_options:
                shape_type = advanced_options.get("shape_type", "default")

            shape_config = {
                "type": shape_type,
                "path": file_path,
                "name_field": field_mappings.get("name", "name"),
            }

            # Add id field if mapped
            if "id" in field_mappings:
                shape_config["id_field"] = field_mappings["id"]

            # Add properties if specified
            if advanced_options and advanced_options.get("properties"):
                properties = advanced_options["properties"]
                # Ensure properties is a list
                if isinstance(properties, str):
                    # If it's a comma-separated string, split it
                    properties = [p.strip() for p in properties.split(",") if p.strip()]
                elif not isinstance(properties, list):
                    properties = []
                shape_config["properties"] = properties

            shapes_config = [shape_config]
            result = await asyncio.to_thread(importer.import_shapes, shapes_config)

            # Parse result for record count
            import re

            match = re.search(r"(\d+) processed", result)
            if not match:
                match = re.search(r"(\d+) features imported", result)
            if not match:
                match = re.search(r"Imported (\d+) shapes", result)
            if match:
                job["processed_records"] = int(match.group(1))
                job["total_records"] = int(match.group(1))

        # Mark as completed
        job["status"] = "completed"
        job["completed_at"] = datetime.utcnow().isoformat()
        job["progress"] = 100
        job["result"] = {
            "metrics": parse_import_metrics(result),
            "summary": result,  # Keep original text for reference
        }

    except Exception as e:
        # Mark as failed
        job["status"] = "failed"
        job["completed_at"] = datetime.utcnow().isoformat()

        # Capture detailed error information
        from niamoto.common.exceptions import DataValidationError

        if isinstance(e, DataValidationError):
            error_info = {
                "message": str(e),
                "details": e.details if hasattr(e, "details") else [],
            }
            job["errors"].append(json.dumps(error_info))
        else:
            job["errors"].append(str(e))
        job["progress"] = 0

        # Also log the error with details for debugging
        import traceback

        print(f"Import failed: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")

    finally:
        # Clean up temporary file only (not the file in imports directory)
        if temp_file_path:
            try:
                Path(temp_file_path).unlink()
                print(f"Cleaned up temporary file: {temp_file_path}")
            except OSError:
                pass


@router.get("/plugins/{plugin_name}/config-schema")
async def get_plugin_config_schema(plugin_name: str):
    """Get the configuration schema for a specific plugin."""
    try:
        # Load core plugins
        from niamoto.core.plugins.plugin_loader import PluginLoader

        loader = PluginLoader()
        loader.load_core_plugins()

        # Get the plugin class
        plugin_class = PluginRegistry.get_plugin(plugin_name, PluginType.LOADER)

        # Get the config model
        if hasattr(plugin_class, "config_model"):
            config_model = plugin_class.config_model
            # Convert Pydantic model to JSON schema
            schema = config_model.model_json_schema()

            # Extract required fields
            required_fields = schema.get("required", [])
            properties = schema.get("properties", {})

            # Build simplified schema with field info
            fields = {}
            for field_name, field_info in properties.items():
                fields[field_name] = {
                    "type": field_info.get("type", "string"),
                    "description": field_info.get("description", ""),
                    "required": field_name in required_fields,
                    "default": field_info.get("default"),
                }

                # Handle special cases
                if field_name == "plugin" and "const" in field_info:
                    fields[field_name]["value"] = field_info["const"]

            return {
                "plugin_name": plugin_name,
                "fields": fields,
                "title": schema.get("title", plugin_name),
                "description": schema.get("description", ""),
            }
        else:
            raise HTTPException(
                status_code=404, detail=f"Plugin {plugin_name} has no config model"
            )

    except KeyError:
        raise HTTPException(status_code=404, detail=f"Plugin {plugin_name} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
