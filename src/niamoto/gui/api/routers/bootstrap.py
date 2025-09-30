"""
API endpoints for data bootstrap functionality.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import List, Dict, Any, Optional
from pathlib import Path
import tempfile
import shutil
import yaml
import json
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from niamoto.core.imports.auto_detector import AutoDetector
from niamoto.core.imports.bootstrap import DataBootstrap
from niamoto.gui.api.context import get_working_directory, get_database_path

router = APIRouter(prefix="/bootstrap", tags=["bootstrap"])


@router.post("/analyze")
async def analyze_files(files: List[UploadFile] = File(...)):
    """
    Analyze uploaded files and return configuration suggestions.

    This endpoint receives files, saves them temporarily, analyzes them,
    and returns the detected structure and suggested configuration.
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="niamoto_analyze_"))

    try:
        # Save uploaded files
        saved_files = []
        for file in files:
            file_path = temp_dir / file.filename

            # Create subdirectory for shapes if needed
            if "shapes/" in file.filename:
                file_path = temp_dir / file.filename
                file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            saved_files.append(file_path)

        # Analyze with auto-detector
        detector = AutoDetector()
        analysis = detector.analyze_directory(temp_dir)

        # Format response
        response = {
            "success": True,
            "analysis": {
                "config": analysis["config"],
                "summary": analysis["summary"],
                "confidence": analysis["confidence"],
                "validation": analysis["validation"],
                "profiles": [
                    {
                        "filename": Path(p["file_path"]).name,
                        "type": p["detected_type"],
                        "name": p["suggested_name"],
                        "records": p["record_count"],
                        "columns": len(p["columns"]),
                        "confidence": p["confidence"],
                    }
                    for p in analysis["profiles"]
                ],
            },
        }

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Clean up temp directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


@router.post("/generate-config")
async def generate_config(
    files: List[UploadFile] = File(...), config_adjustments: Optional[str] = Form(None)
):
    """
    Generate complete configuration from files with optional adjustments.

    This endpoint analyzes files and generates all three configuration files
    (import.yml, transform.yml, export.yml) with optional user adjustments.
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="niamoto_generate_"))

    try:
        # Save uploaded files
        for file in files:
            file_path = temp_dir / file.filename

            # Handle subdirectories
            if "/" in file.filename:
                file_path = temp_dir / file.filename
                file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)

        # Run bootstrap
        bootstrap = DataBootstrap()
        results = bootstrap.run(data_dir=temp_dir, auto_confirm=True, interactive=False)

        # Apply user adjustments if provided
        if config_adjustments:
            adjustments = json.loads(config_adjustments)
            # Merge adjustments into generated config
            if "import" in adjustments:
                results["configs"]["import.yml"].update(adjustments["import"])

        # Return generated configurations
        response = {
            "success": True,
            "configs": {
                "import": results["configs"]["import.yml"],
                "transform": results["configs"]["transform.yml"],
                "export": results["configs"]["export.yml"],
            },
            "summary": results.get("summary", {}),
        }

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Clean up
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


@router.post("/save-config")
async def save_config(config: Dict[str, Any]):
    """
    Save the generated configuration to the instance.

    This endpoint receives the final configuration and saves it
    to the appropriate location in the Niamoto instance.
    """
    try:
        # Get instance path from environment or config
        instance_path = Path.cwd()  # Use current directory as default
        config_dir = instance_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Save each configuration file
        saved_files = []

        for config_type in ["import", "transform", "export"]:
            if config_type in config:
                file_path = config_dir / f"{config_type}.yml"

                # Backup existing file if it exists
                if file_path.exists():
                    backup_path = file_path.with_suffix(".yml.backup")
                    shutil.copy(file_path, backup_path)

                # Save new configuration
                with open(file_path, "w") as f:
                    yaml.dump(
                        config[config_type],
                        f,
                        default_flow_style=False,
                        sort_keys=False,
                    )

                saved_files.append(str(file_path))

        return {
            "success": True,
            "message": "Configuration saved successfully",
            "files": saved_files,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sample-data")
async def get_sample_data():
    """
    Get information about available sample data for testing.

    This endpoint returns information about sample datasets that can be
    used to test the bootstrap functionality.
    """
    sample_dir = (
        Path(__file__).parent.parent.parent.parent.parent.parent
        / "test-instance"
        / "niamoto-og"
        / "imports"
    )

    if not sample_dir.exists():
        return {"available": False, "message": "No sample data found"}

    # List available files
    files = []
    for file_path in sample_dir.glob("**/*"):
        if file_path.is_file() and not file_path.name.startswith("."):
            rel_path = file_path.relative_to(sample_dir)
            files.append(
                {
                    "name": file_path.name,
                    "path": str(rel_path),
                    "size": file_path.stat().st_size,
                }
            )

    return {"available": True, "path": str(sample_dir), "files": files}


@router.get("/diagnostic")
async def get_diagnostic():
    """
    Get diagnostic information about the Niamoto GUI context.

    This endpoint returns information about the working directory,
    database path, and configuration files.
    """
    work_dir = get_working_directory()
    db_path = get_database_path()

    # Check for configuration files
    config_dir = work_dir / "config"
    config_files = {}
    for config_file in ["config.yml", "import.yml", "transform.yml", "export.yml"]:
        file_path = config_dir / config_file
        config_files[config_file] = {
            "exists": file_path.exists(),
            "path": str(file_path),
        }

    # Check database tables if database exists
    db_tables = []
    if db_path and db_path.exists():
        try:
            from sqlalchemy import create_engine, inspect

            engine = create_engine(f"sqlite:///{db_path}")
            inspector = inspect(engine)
            db_tables = inspector.get_table_names()
            engine.dispose()
        except Exception as e:
            db_tables = [f"Error reading tables: {str(e)}"]

    return {
        "working_directory": str(work_dir),
        "database": {
            "path": str(db_path) if db_path else None,
            "exists": db_path.exists() if db_path else False,
            "tables": db_tables,
        },
        "config_files": config_files,
    }
