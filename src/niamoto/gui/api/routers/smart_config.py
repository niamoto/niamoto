"""Smart configuration endpoints for auto-detecting and configuring entities.

All endpoints in this router use get_working_directory() from GUI context
to ensure file operations happen in the correct project directory.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from pathlib import Path
import shutil
import zipfile

from niamoto.core.imports.auto_config_service import AutoConfigService
from niamoto.gui.api.context import get_working_directory

router = APIRouter()


class FileInfo(BaseModel):
    """Information about a file to analyze."""

    filepath: str
    entity_name: Optional[str] = None


class AutoConfigureRequest(BaseModel):
    """Request for auto-configuration of all files."""

    files: List[str]  # List of file paths relative to imports/


class AutoConfigureResponse(BaseModel):
    """Response from auto-configuration."""

    success: bool
    entities: Dict[str, Any]
    detected_columns: Dict[str, List[str]] = {}  # Entity name -> columns
    ml_predictions: Dict[str, List[Dict[str, Any]]] = {}
    decision_summary: Dict[str, Dict[str, Any]] = {}
    semantic_evidence: Dict[str, Dict[str, Any]] = {}
    confidence: float
    warnings: List[str] = []


class DetectRelationshipsRequest(BaseModel):
    """Request for detecting relationships between files."""

    source_file: str
    target_files: List[str]


class UploadedFileInfo(BaseModel):
    """Information about an uploaded file."""

    filename: str
    path: str  # Relative path from working directory
    size: int  # Size in bytes
    size_mb: float
    type: str  # File extension
    category: str  # csv, gpkg, tif, other


@router.post("/upload-files")
async def upload_files(
    files: List[UploadFile] = File(...), overwrite: bool = False
) -> Dict[str, Any]:
    """Upload multiple files to the imports directory.

    All files are uploaded to imports/ at the root level for simplicity.

    Args:
        files: List of files to upload
        overwrite: If True, overwrite existing files. If False, skip and report existing files.

    Returns:
        Dict with uploaded file information, existing files, and any errors
    """
    try:
        work_dir = get_working_directory()
        if not work_dir:
            raise HTTPException(status_code=400, detail="Working directory not set")

        imports_dir = work_dir / "imports"

        # Ensure directory exists
        imports_dir.mkdir(exist_ok=True)

        uploaded_files: List[UploadedFileInfo] = []
        existing_files: List[str] = []  # Track files that already exist
        errors: List[str] = []

        for uploaded_file in files:
            try:
                filename = uploaded_file.filename
                if not filename:
                    errors.append("File without name skipped")
                    continue

                # Determine file type
                file_ext = Path(filename).suffix.lower()
                file_category = _categorize_file(file_ext)

                # All files go to imports/ root
                target_path = imports_dir / filename
                relative_path = f"imports/{filename}"

                # Check if file already exists BEFORE reading content (performance optimization)
                if target_path.exists():
                    if not overwrite:
                        # Don't overwrite - add to existing_files list
                        existing_files.append(filename)
                        continue
                    else:
                        # Overwrite - delete existing file first
                        target_path.unlink()

                # Save file - only read if file doesn't exist or we're overwriting
                content = await uploaded_file.read()
                file_size = len(content)

                # Handle ZIP extraction
                if file_ext == ".zip":
                    await _handle_zip_upload(
                        content, filename, imports_dir, uploaded_files, errors
                    )
                else:
                    # Write file to disk
                    with open(target_path, "wb") as f:
                        f.write(content)

                    uploaded_files.append(
                        UploadedFileInfo(
                            filename=filename,
                            path=relative_path,
                            size=file_size,
                            size_mb=round(file_size / (1024 * 1024), 2),
                            type=file_ext.lstrip("."),
                            category=file_category,
                        )
                    )

            except Exception as e:
                errors.append(f"Error uploading {uploaded_file.filename}: {str(e)}")

        return {
            "success": len(uploaded_files) > 0 or len(existing_files) > 0,
            "uploaded_files": [f.model_dump() for f in uploaded_files],
            "uploaded_count": len(uploaded_files),
            "existing_files": existing_files,  # List of files that already exist
            "existing_count": len(existing_files),
            "errors": errors,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


async def _handle_zip_upload(
    content: bytes,
    filename: str,
    target_dir: Path,
    uploaded_files: List[UploadedFileInfo],
    errors: List[str],
) -> None:
    """Handle ZIP file upload (typically shapefiles)."""
    import tempfile

    # Extract ZIP to temporary directory
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / filename
        with open(tmp_path, "wb") as f:
            f.write(content)

        # Extract
        try:
            with zipfile.ZipFile(tmp_path, "r") as zip_ref:
                zip_ref.extractall(tmp_dir)

            # Find extracted files
            extracted_files = list(Path(tmp_dir).glob("*"))
            extracted_files = [
                f for f in extracted_files if f.is_file() and f.name != filename
            ]

            if not extracted_files:
                errors.append(f"No files found in {filename}")
                return

            # Create subdirectory for shapefile components
            shapefile_name = Path(filename).stem
            shapefile_dir = target_dir / shapefile_name
            shapefile_dir.mkdir(exist_ok=True)

            # Copy extracted files
            for extracted_file in extracted_files:
                dest = shapefile_dir / extracted_file.name
                shutil.copy2(extracted_file, dest)

                uploaded_files.append(
                    UploadedFileInfo(
                        filename=extracted_file.name,
                        path=f"imports/shapes/{shapefile_name}/{extracted_file.name}",
                        size=extracted_file.stat().st_size,
                        size_mb=round(extracted_file.stat().st_size / (1024 * 1024), 2),
                        type=extracted_file.suffix.lstrip("."),
                        category="shapefile",
                    )
                )

        except zipfile.BadZipFile:
            errors.append(f"{filename} is not a valid ZIP file")


def _categorize_file(file_ext: str) -> str:
    """Categorize file by extension."""
    ext = file_ext.lower()
    if ext == ".csv":
        return "csv"
    elif ext in [".gpkg", ".geojson"]:
        return "gpkg"
    elif ext in [".tif", ".tiff"]:
        return "tif"
    elif ext == ".zip":
        return "shapefile"
    else:
        return "other"


@router.post("/analyze-file")
async def analyze_file_smart(request: FileInfo) -> Dict[str, Any]:
    """Analyze a single file with smart pattern detection.

    Args:
        request: File information

    Returns:
        Detailed analysis with detected patterns
    """
    try:
        work_dir = get_working_directory()
        if not work_dir:
            raise HTTPException(status_code=400, detail="Working directory not set")

        service = AutoConfigService(Path(work_dir))
        return service.analyze_file(request.filepath)

    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing file: {str(e)}")


@router.post("/detect-hierarchy")
async def detect_hierarchy(request: FileInfo) -> Dict[str, Any]:
    """Detect hierarchical patterns in a file.

    Args:
        request: File information

    Returns:
        Detected hierarchy information
    """
    try:
        work_dir = get_working_directory()
        if not work_dir:
            raise HTTPException(status_code=400, detail="Working directory not set")

        service = AutoConfigService(Path(work_dir))
        return service.detect_hierarchy(request.filepath)

    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error detecting hierarchy: {str(e)}"
        )


@router.post("/detect-relationships")
async def detect_relationships(
    request: DetectRelationshipsRequest,
) -> Dict[str, Any]:
    """Detect relationships between a source file and target files.

    Args:
        request: Request containing source_file and target_files

    Returns:
        Dictionary with detected relationships
    """
    try:
        work_dir = get_working_directory()
        if not work_dir:
            raise HTTPException(status_code=400, detail="Working directory not set")

        service = AutoConfigService(Path(work_dir))
        return service.detect_relationships(
            source_file=request.source_file,
            target_files=request.target_files,
        )

    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error detecting relationships: {str(e)}"
        )


@router.post("/auto-configure", response_model=AutoConfigureResponse)
async def auto_configure(request: AutoConfigureRequest) -> AutoConfigureResponse:
    """Auto-configure entities from multiple files (CSV, GPKG, TIF).

    This is the main "magic" endpoint that analyzes all files and generates
    a complete import.yml configuration including:
    - entities.datasets (CSV with data)
    - entities.references (taxonomies, plots, shapes from GPKG)
    - metadata.layers (raster/vector layers from GPKG/TIF)

    Args:
        request: List of files to configure

    Returns:
        Complete entity configuration with spatial matching
    """
    try:
        work_dir_str = get_working_directory()
        if not work_dir_str:
            raise HTTPException(status_code=400, detail="Working directory not set")

        service = AutoConfigService(Path(work_dir_str))
        result = service.auto_configure(request.files)
        return AutoConfigureResponse(**result)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error in auto-configuration: {str(e)}"
        )


class CreateEntitiesBulkRequest(BaseModel):
    """Request to create entities in bulk and save to import.yml."""

    entities: Dict[str, Any]  # Contains datasets, references, metadata


@router.post("/management/entities/bulk")
async def create_entities_bulk(request: CreateEntitiesBulkRequest):
    """
    Create entities in bulk by saving them to config/import.yml.

    This endpoint takes the auto-configured entities and writes them
    to the config/import.yml file.

    Args:
        request: Contains entities dict with datasets, references, metadata

    Returns:
        Success status and message
    """
    import yaml

    work_dir = get_working_directory()
    if not work_dir:
        raise HTTPException(status_code=500, detail="Working directory not set")

    work_dir_path = Path(work_dir)
    config_dir = work_dir_path / "config"
    import_yml_path = config_dir / "import.yml"

    # Ensure config directory exists
    config_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Build the import.yml structure
        import_config = {
            "version": "1.0",
            "entities": {
                "datasets": request.entities.get("datasets", {}),
                "references": request.entities.get("references", {}),
            },
        }

        # Add metadata if present
        if "metadata" in request.entities:
            import_config["metadata"] = request.entities["metadata"]

        # Write to import.yml
        with open(import_yml_path, "w", encoding="utf-8") as f:
            yaml.dump(
                import_config,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )

        dataset_count = len(request.entities.get("datasets", {}))
        reference_count = len(request.entities.get("references", {}))

        return {
            "success": True,
            "message": f"Successfully created {dataset_count} dataset(s) and {reference_count} reference(s)",
            "config_path": str(import_yml_path),
            "dataset_count": dataset_count,
            "reference_count": reference_count,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to save import configuration: {str(e)}"
        )
