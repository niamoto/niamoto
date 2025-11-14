"""Smart configuration endpoints for auto-detecting and configuring entities.

All endpoints in this router use get_working_directory() from GUI context
to ensure file operations happen in the correct project directory.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from pathlib import Path
import csv
import shutil
import zipfile

from niamoto.core.utils.column_detector import (
    ColumnDetector,
    GeoPackageAnalyzer,
)
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
            "uploaded_files": [f.dict() for f in uploaded_files],
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

        file_path = work_dir / request.filepath

        if not file_path.exists():
            raise HTTPException(
                status_code=404, detail=f"File not found: {request.filepath}"
            )

        # Read file based on type
        if file_path.suffix.lower() == ".csv":
            result = await _analyze_csv_file(file_path)
        else:
            raise HTTPException(
                status_code=400, detail=f"Unsupported file type: {file_path.suffix}"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing file: {str(e)}")


async def _analyze_csv_file(file_path: Path) -> Dict[str, Any]:
    """Analyze a CSV file with smart detection.

    Args:
        file_path: Path to CSV file

    Returns:
        Analysis results with detected patterns
    """
    try:
        # Performance optimization: Read max 1000 rows for analysis, count rest efficiently
        MAX_SAMPLE_ROWS = 1000
        ANALYSIS_SAMPLE = 100  # Use first 100 for pattern detection

        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            columns = reader.fieldnames or []

            # Read up to MAX_SAMPLE_ROWS rows, count the rest
            sample_rows = []
            row_count = 0

            for row in reader:
                row_count += 1
                if row_count <= MAX_SAMPLE_ROWS:
                    sample_rows.append(row)
                # Continue counting without storing rows after MAX_SAMPLE_ROWS

            # Use first 100 rows for analysis
            sample_data = sample_rows[:ANALYSIS_SAMPLE]

        # Use ColumnDetector to analyze
        analysis = ColumnDetector.analyze_file_columns(columns, sample_data)

        # Add file-specific info
        analysis["filename"] = file_path.name
        analysis["filepath"] = str(file_path)
        analysis["row_count"] = row_count  # Total row count
        analysis["sample_size"] = len(sample_rows)  # How many rows were sampled

        return analysis

    except Exception as e:
        raise Exception(f"Failed to analyze CSV: {str(e)}")


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

        file_path = work_dir / request.filepath

        if not file_path.exists():
            raise HTTPException(
                status_code=404, detail=f"File not found: {request.filepath}"
            )

        # Read CSV file
        if file_path.suffix.lower() != ".csv":
            raise HTTPException(
                status_code=400,
                detail="Only CSV files supported for hierarchy detection",
            )

        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            columns = reader.fieldnames or []

            # Read sample data (max 100 rows for performance)
            sample_data = []
            for i, row in enumerate(reader):
                if i >= 100:
                    break
                sample_data.append(row)

        # Detect hierarchy
        hierarchy_info = ColumnDetector.detect_hierarchy_columns(columns, sample_data)

        # Add statistics per level
        if hierarchy_info["detected"] and sample_data:
            stats_per_level = {}
            for level, col_name in hierarchy_info["column_mapping"].items():
                values = [row.get(col_name) for row in sample_data if row.get(col_name)]
                unique_values = set(values)

                stats_per_level[level] = {
                    "column": col_name,
                    "unique_count": len(unique_values),
                    "sample_values": list(unique_values)[:5],
                }

            hierarchy_info["stats_per_level"] = stats_per_level

        return hierarchy_info

    except HTTPException:
        raise
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

        source_path = work_dir / request.source_file

        if not source_path.exists():
            raise HTTPException(
                status_code=404, detail=f"Source file not found: {request.source_file}"
            )

        # Read source file
        with open(source_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            source_columns = reader.fieldnames or []
            source_sample = [row for i, row in enumerate(reader) if i < 100]

        # Check relationships with each target file
        all_relationships = []

        for target_file in request.target_files:
            target_path = work_dir / target_file

            if not target_path.exists():
                continue

            # Read target file
            with open(target_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                target_columns = reader.fieldnames or []
                target_sample = [row for i, row in enumerate(reader) if i < 100]

            # Detect relationships (with entity names for semantic detection)
            source_entity_name = Path(request.source_file).stem
            target_entity_name = Path(target_file).stem

            relationships = ColumnDetector.detect_relationships(
                source_columns,
                target_columns,
                source_sample,
                target_sample,
                source_entity_name,
                target_entity_name,
            )

            for rel in relationships:
                rel["target_file"] = target_file
                all_relationships.append(rel)

        return {"relationships": all_relationships}

    except HTTPException:
        raise
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

        work_dir = Path(work_dir_str)

        if not request.files:
            raise HTTPException(status_code=400, detail="No files provided")

        # Step 1: Analyze all files by type
        csv_analyses = {}
        gpkg_analyses = {}
        tif_files = []

        for filepath in request.files:
            file_path = work_dir / filepath

            if not file_path.exists():
                continue

            file_ext = file_path.suffix.lower()

            if file_ext == ".csv":
                analysis = await _analyze_csv_file(file_path)
                analysis["relative_path"] = filepath
                csv_analyses[filepath] = analysis

            elif file_ext in [".gpkg", ".geojson"]:
                analysis = GeoPackageAnalyzer.analyze_gpkg(file_path)
                if "error" not in analysis:
                    analysis["relative_path"] = filepath
                    gpkg_analyses[filepath] = analysis

            elif file_ext in [".tif", ".tiff"]:
                tif_files.append(filepath)

        if not csv_analyses and not gpkg_analyses and not tif_files:
            raise HTTPException(status_code=400, detail="No valid files to analyze")

        # Step 2: Detect FK relationships between CSV files to identify references
        # A CSV that is referenced by another should be a reference, not a dataset
        referenced_by = {}  # Track which CSVs are referenced by others

        for filepath, analysis in csv_analyses.items():
            entity_name = Path(filepath).stem

            # Check relationships with other CSV files
            for other_filepath, other_analysis in csv_analyses.items():
                if filepath == other_filepath:
                    continue

                other_name = Path(other_filepath).stem
                relationships = ColumnDetector.detect_relationships(
                    other_analysis["columns"],
                    analysis["columns"],
                    source_entity_name=other_name,
                    target_entity_name=entity_name,
                )

                # Filter high-confidence relationships and select the best one
                high_confidence_rels = [
                    rel for rel in relationships if rel["confidence"] >= 0.5
                ]

                if high_confidence_rels:
                    # Select best relationship (same logic as in link detection)
                    best_rel = None

                    # First, try to find an ID-based relationship
                    for rel in high_confidence_rels:
                        source_field_lower = rel["source_field"].lower()
                        target_field_lower = rel["target_field"].lower()

                        is_id_match = (
                            "id" in source_field_lower or "id" in target_field_lower
                        ) and (
                            entity_name.lower() in source_field_lower
                            or entity_name.lower() in target_field_lower
                        )

                        if is_id_match:
                            best_rel = rel
                            break

                    # If no ID match, prefer semantic_context
                    if not best_rel:
                        semantic_rels = [
                            r
                            for r in high_confidence_rels
                            if r.get("match_type") == "semantic_context"
                        ]
                        if semantic_rels:
                            best_rel = max(semantic_rels, key=lambda r: r["confidence"])
                        else:
                            best_rel = max(
                                high_confidence_rels, key=lambda r: r["confidence"]
                            )

                    # Add only the best relationship
                    if best_rel:
                        if entity_name not in referenced_by:
                            referenced_by[entity_name] = []
                        referenced_by[entity_name].append(
                            {
                                "from": other_name,
                                "field": best_rel["source_field"],
                                "confidence": best_rel["confidence"],
                            }
                        )

        # Step 3: Build references from CSV and GPKG
        references = {}
        datasets_to_create = {}

        # Handle CSV files
        for filepath, analysis in csv_analyses.items():
            entity_type = analysis["suggested_entity_type"]
            entity_name = Path(filepath).stem

            # Special case: Detect spatial references by row count ratio
            # If this file is referenced by another file with 10x more rows,
            # it's likely a reference (e.g., plots referenced by occurrences)
            # BUT: only if it doesn't have observation characteristics
            if entity_type == "dataset" and entity_name in referenced_by:
                # Check if this file has observation characteristics
                # (date columns, measurement columns, taxonomy hierarchy)
                has_observations = len(analysis.get("date_columns", [])) > 0 or any(
                    col.lower()
                    in [
                        "dbh",
                        "height",
                        "diameter",
                        "measurement",
                        "value",
                        "stem_diameter",
                    ]
                    for col in analysis.get("columns", [])
                )

                hierarchy = analysis.get("hierarchy", {})
                has_taxonomic_hierarchy = (
                    hierarchy.get("detected")
                    and hierarchy.get("hierarchy_type") == "taxonomic"
                )

                # If it has observations or taxonomic hierarchy, keep it as dataset
                if has_observations or has_taxonomic_hierarchy:
                    # Skip ratio check - this is clearly an observation dataset
                    pass
                else:
                    # Check ratio for potential spatial references
                    for ref_info in referenced_by[entity_name]:
                        source_name = ref_info["from"]
                        source_filepath = f"imports/{source_name}.csv"

                        if source_filepath in csv_analyses:
                            source_rows = csv_analyses[source_filepath].get(
                                "row_count", 0
                            )
                            target_rows = analysis.get("row_count", 0)

                            # If source has 10x more rows → target is a reference
                            if target_rows > 0 and (source_rows / target_rows) >= 10:
                                entity_type = "reference"
                                break

            if entity_type == "hierarchical_reference":
                references[entity_name] = _build_hierarchy_reference_config(
                    filepath, analysis, csv_analyses
                )
            elif entity_type == "reference":
                references[entity_name] = _build_simple_reference_config(
                    filepath, analysis
                )
            elif entity_type == "dataset":
                datasets_to_create[entity_name] = (filepath, analysis)

                # Extract derived hierarchy if detected
                if (
                    analysis.get("extract_hierarchy_as_reference", False)
                    and analysis["hierarchy"]["detected"]
                ):
                    ref_name = _infer_reference_name(entity_name, analysis)
                    references[ref_name] = _build_derived_hierarchy_reference(
                        entity_name, filepath, analysis
                    )

        # Handle GPKG files - build shapes reference if multiple shapes detected
        shapes_sources = []
        layers_info = []

        for filepath, analysis in gpkg_analyses.items():
            if analysis["classification"] == "shapes":
                # Add to shapes reference
                name_field = (
                    analysis["name_field_candidates"][0]
                    if analysis["name_field_candidates"]
                    else "name"
                )

                shapes_sources.append(
                    {
                        "name": Path(filepath).stem.replace("_", " ").title(),
                        "path": filepath,
                        "layer": analysis.get("layer_analyzed"),
                        "name_field": name_field,
                    }
                )
            else:
                # Add to metadata layers
                layers_info.append(
                    {
                        "name": Path(filepath).stem,
                        "type": "vector",
                        "format": "geopackage",
                        "path": filepath,
                        "description": f"{analysis['geometry_types'][0] if analysis.get('geometry_types') else 'Vector'} layer",
                    }
                )

        # Create shapes reference if we have multiple GPKG shapes
        if shapes_sources:
            references["shapes"] = _build_shapes_reference(shapes_sources)

        # Step 3: Build datasets (simplified - connector only)
        datasets = {}
        warnings = []

        for entity_name, (filepath, analysis) in datasets_to_create.items():
            datasets[entity_name] = _build_dataset_config(
                filepath, analysis, references, csv_analyses
            )

        # Step 4: Build metadata layers from TIF
        for tif_path in tif_files:
            layers_info.append(
                {
                    "name": Path(tif_path).stem,
                    "type": "raster",
                    "path": tif_path,
                    "description": f"Raster layer from {Path(tif_path).name}",
                }
            )

        # Step 5: Calculate confidence
        all_confidences = [a["confidence"] for a in csv_analyses.values()]
        all_confidences.extend([a["confidence"] for a in gpkg_analyses.values()])
        overall_confidence = (
            sum(all_confidences) / len(all_confidences) if all_confidences else 0.5
        )

        # Step 6: Build complete configuration
        config = {
            "datasets": datasets,
            "references": references,
        }

        # Add metadata if we have layers
        metadata = {}
        if layers_info:
            metadata["layers"] = layers_info

        # Step 7: Add additional warnings based on confidence and references
        if overall_confidence < 0.6:
            warnings.append(
                "Low confidence in auto-configuration. Please review carefully."
            )

        if not references:
            warnings.append("No references detected. Add taxonomy or lookup tables.")

        # Combine entities and metadata
        result_entities = config.copy()
        if metadata:
            result_entities["metadata"] = metadata

        return AutoConfigureResponse(
            success=True,
            entities=result_entities,
            confidence=overall_confidence,
            warnings=warnings,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error in auto-configuration: {str(e)}"
        )


def _build_hierarchy_reference_config(
    filepath: str, analysis: Dict[str, Any], all_analyses: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """Build configuration for a hierarchical reference (e.g., taxonomy).

    Args:
        filepath: Path to file
        analysis: Analysis results
        all_analyses: All file analyses (for detecting derived source)

    Returns:
        Reference configuration
    """
    hierarchy = analysis["hierarchy"]

    # Check if this should be derived from a dataset
    # (if the same columns exist in a dataset file)
    is_derived = False
    source_dataset = None

    for other_filepath, other_analysis in all_analyses.items():
        if other_filepath == filepath:
            continue

        # Check if hierarchy columns exist in other file
        other_columns = set(other_analysis.get("columns", []))
        hierarchy_columns = set(hierarchy["column_mapping"].values())

        if hierarchy_columns.issubset(other_columns):
            is_derived = True
            source_dataset = Path(other_filepath).stem
            break

    if is_derived and source_dataset:
        # Derived reference
        levels_config = []
        for level in hierarchy["levels"]:
            if level in hierarchy["column_mapping"]:
                levels_config.append(
                    {
                        "name": level,
                        "column": hierarchy["column_mapping"][level],
                    }
                )

        return {
            "kind": "hierarchical",
            "connector": {
                "type": "derived",
                "source": source_dataset,
                "extraction": {
                    "levels": levels_config,
                    "id_strategy": "hash",
                    "incomplete_rows": "skip",
                },
            },
            "hierarchy": {
                "strategy": "adjacency_list",
                "levels": hierarchy["levels"],
            },
            "schema": {
                "id_field": "id",
                "fields": [],
            },
        }
    else:
        # File-based reference
        id_column = analysis["id_columns"][0] if analysis["id_columns"] else "id"

        return {
            "kind": "hierarchical",
            "connector": {
                "type": "file",
                "format": "csv",
                "path": filepath,
            },
            "hierarchy": {
                "strategy": "adjacency_list",
                "levels": hierarchy["levels"],
            },
            "schema": {
                "id_field": id_column,
                "fields": [],
            },
        }


def _build_simple_reference_config(
    filepath: str, analysis: Dict[str, Any]
) -> Dict[str, Any]:
    """Build configuration for a simple reference (e.g., plots, sites).

    Args:
        filepath: Path to file
        analysis: Analysis results

    Returns:
        Reference configuration
    """
    id_column = analysis["id_columns"][0] if analysis["id_columns"] else "id"

    config = {
        "connector": {
            "type": "file",
            "format": "csv",
            "path": filepath,
        },
        "schema": {
            "id_field": id_column,
            "fields": [],
        },
    }

    # Add geometry if detected
    if analysis["geometry_columns"]:
        config["schema"]["fields"].append(
            {
                "name": analysis["geometry_columns"][0],
                "type": "geometry",
            }
        )

    return config


def _build_shapes_reference(sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build configuration for shapes reference (file_multi_feature).

    Args:
        sources: List of shape sources with name, path, name_field

    Returns:
        Shapes reference configuration
    """
    return {
        "kind": "spatial",
        "description": "Geographic reference features for spatial analysis",
        "connector": {
            "type": "file_multi_feature",
            "sources": sources,
        },
        "schema": {
            "fields": [
                {
                    "name": "name",
                    "type": "string",
                    "description": "Feature name from source file",
                },
                {
                    "name": "location",
                    "type": "geometry",
                    "description": "Geometry in WKT format",
                },
                {
                    "name": "entity_type",
                    "type": "string",
                    "description": "Source type",
                },
            ]
        },
    }


def _build_dataset_config(
    filepath: str,
    analysis: Dict[str, Any],
    references: Dict[str, Any],
    all_analyses: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Build simplified configuration for a dataset.

    Args:
        filepath: Path to file
        analysis: Analysis results (unused but kept for API compatibility)
        references: Configured references (unused but kept for API compatibility)
        all_analyses: All file analyses (unused but kept for API compatibility)

    Returns:
        Simplified dataset configuration with connector only
    """
    config = {
        "connector": {
            "type": "file",
            "format": "csv",
            "path": filepath,
        },
    }

    return config


def _infer_reference_name(dataset_name: str, analysis: Dict[str, Any]) -> str:
    """Infer a good name for a derived reference.

    Args:
        dataset_name: Name of the source dataset
        analysis: Analysis results

    Returns:
        Suggested reference name
    """
    hierarchy = analysis.get("hierarchy", {})
    levels = hierarchy.get("levels", [])

    # Common mappings
    if "occurrence" in dataset_name.lower():
        # If lowest level is species/genus -> taxonomy/taxons
        if "species" in levels or "genus" in levels:
            return "taxons"
        return "taxonomy"

    if "observation" in dataset_name.lower():
        return "taxa"

    # Default: dataset_name + "_hierarchy"
    return f"{dataset_name}_taxonomy"


def _build_derived_hierarchy_reference(
    source_dataset: str,
    source_filepath: str,
    analysis: Dict[str, Any],
) -> Dict[str, Any]:
    """Build configuration for a derived hierarchical reference.

    Args:
        source_dataset: Name of source dataset
        source_filepath: Path to source file
        analysis: Analysis results from source dataset

    Returns:
        Derived reference configuration
    """
    hierarchy = analysis["hierarchy"]

    # Build extraction levels config
    levels_config = []
    for level in hierarchy["levels"]:
        if level in hierarchy["column_mapping"]:
            levels_config.append(
                {
                    "name": level,
                    "column": hierarchy["column_mapping"][level],
                }
            )

    # Detect ID column for taxon reference
    id_col = None
    for col in analysis["columns"]:
        col_lower = col.lower()
        if "taxon" in col_lower and "id" in col_lower:
            id_col = col
            break

    # Detect name column - prefer taxon/scientific name
    name_col = None
    for col in analysis["columns"]:
        col_lower = col.lower()
        if any(
            pattern in col_lower
            for pattern in ["taxaname", "scientific_name", "taxon_name"]
        ):
            name_col = col
            break

    if not name_col and analysis["name_columns"]:
        # Fallback to generic name column
        name_col = analysis["name_columns"][0]

    return {
        "kind": "hierarchical",
        "description": f"Taxonomic hierarchy extracted from {source_dataset}",
        "connector": {
            "type": "derived",
            "source": source_dataset,
            "extraction": {
                "levels": levels_config,
                "id_column": id_col,
                "name_column": name_col,
                "id_strategy": "hash",
                "incomplete_rows": "skip",
            },
        },
        "hierarchy": {
            "strategy": "adjacency_list",
            "levels": hierarchy["levels"],
        },
        "schema": {
            "id_field": "id",
            "fields": [],
        },
    }


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
