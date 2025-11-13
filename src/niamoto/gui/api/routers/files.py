"""File management API endpoints."""

import csv
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
import pandas as pd
import httpx
from pydantic import BaseModel
import tempfile
import zipfile
import geopandas as gpd

from ..context import get_working_directory

router = APIRouter()


class ApiTestRequest(BaseModel):
    """Request model for API testing."""

    url: str
    headers: Dict[str, str] = {}
    params: Dict[str, str] = {}


class ApiTestResponse(BaseModel):
    """Response model for API testing."""

    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None


@router.post("/analyze")
async def analyze_file(
    file: UploadFile = File(...), entity_type: str = Form(...)
) -> Dict[str, Any]:
    """Analyze a file for import configuration."""
    try:
        # Read file content
        content = await file.read()

        # Basic analysis based on file type
        # Check if it's a spatial file for shapes/spatial reference import
        is_spatial = entity_type == "reference" and file.filename.lower().endswith(
            (".zip", ".shp", ".geojson", ".gpkg")
        )

        if is_spatial:
            result = await analyze_shape(content, file.filename)
        elif file.filename.endswith(".csv"):
            result = await analyze_csv(content, file.filename)
        elif file.filename.endswith((".xls", ".xlsx")):
            result = await analyze_excel(content, file.filename)
        elif file.filename.lower().endswith(".shp"):
            return {
                "error": "Shapefile analysis requires all component files (.shp, .shx, .dbf). Please upload a ZIP file containing all shapefile components."
            }
        else:
            return {"error": f"Unsupported file type: {file.filename}"}

        # Add entity_type for compatibility
        result["entity_type"] = entity_type
        # Keep suggestions generic - specific field mapping done in frontend
        result["suggestions"] = {}

        return result

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


async def analyze_geopackage(content: bytes, filename: str) -> Dict[str, Any]:
    """Analyze GeoPackage file content."""
    try:
        import tempfile
        import geopandas as gpd

        # Write to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".gpkg") as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # Read with geopandas
            gdf = gpd.read_file(tmp_path)

            return {
                "filename": filename,
                "type": "geopackage",
                "feature_count": len(gdf),
                "columns": list(gdf.columns),
                "column_types": {col: str(gdf[col].dtype) for col in gdf.columns},
                "geometry_types": list(gdf.geometry.geom_type.unique()),
                "crs": str(gdf.crs) if gdf.crs else None,
                "bounds": gdf.total_bounds.tolist() if not gdf.is_empty.all() else None,
                "sample_data": gdf.drop(columns="geometry").head(5).to_dict("records"),
            }
        finally:
            import os

            os.unlink(tmp_path)

    except Exception as e:
        return {"error": f"Failed to analyze GeoPackage: {str(e)}"}


def get_field_suggestions(
    analysis: Dict[str, Any], import_type: str
) -> Dict[str, List[str]]:
    """Get field mapping suggestions based on import type and file analysis."""
    suggestions = {}
    columns = analysis.get("columns", [])

    if not columns:
        return suggestions

    # Lowercase columns for matching
    lower_columns = {col.lower(): col for col in columns}

    if import_type == "taxonomy":
        # Suggest taxonomy fields
        suggestions["taxon_id"] = find_matching_columns(
            lower_columns, ["id", "taxon_id", "tax_id"]
        )
        suggestions["full_name"] = find_matching_columns(
            lower_columns, ["full_name", "name", "scientific_name"]
        )
        suggestions["authors"] = find_matching_columns(
            lower_columns, ["authors", "author", "authority"]
        )
        suggestions["family"] = find_matching_columns(
            lower_columns, ["family", "famille"]
        )
        suggestions["genus"] = find_matching_columns(lower_columns, ["genus", "genre"])
        suggestions["species"] = find_matching_columns(
            lower_columns, ["species", "espece"]
        )

    elif import_type == "plots":
        suggestions["identifier"] = find_matching_columns(
            lower_columns, ["id", "plot_id", "id_plot"]
        )
        suggestions["locality"] = find_matching_columns(
            lower_columns, ["locality", "plot", "name", "nom"]
        )
        suggestions["location"] = find_matching_columns(
            lower_columns, ["geo_pt", "geometry", "wkt", "geom"]
        )

    elif import_type == "occurrences":
        suggestions["taxon_id"] = find_matching_columns(
            lower_columns, ["id_taxonref", "taxon_id", "tax_id"]
        )
        suggestions["location"] = find_matching_columns(
            lower_columns, ["geo_pt", "geometry", "coordinates"]
        )
        suggestions["plot_name"] = find_matching_columns(
            lower_columns, ["plot_name", "plot", "locality"]
        )

    elif import_type == "shapes":
        suggestions["name"] = find_matching_columns(
            lower_columns, ["name", "nom", "label"]
        )
        suggestions["id"] = find_matching_columns(
            lower_columns, ["id", "gid", "objectid"]
        )

    return suggestions


def find_matching_columns(
    lower_columns: Dict[str, str], patterns: List[str]
) -> List[str]:
    """Find columns that match any of the given patterns."""
    matches = []
    for pattern in patterns:
        if pattern in lower_columns:
            matches.append(lower_columns[pattern])
        else:
            # Partial match
            for col_lower, col_original in lower_columns.items():
                if pattern in col_lower and col_original not in matches:
                    matches.append(col_original)
    return matches


@router.post("/test-api", response_model=ApiTestResponse)
async def test_api_connection(request: ApiTestRequest) -> ApiTestResponse:
    """Test an API connection with provided configuration."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                request.url, headers=request.headers, params=request.params
            )

            if response.status_code == 200:
                try:
                    data = response.json()
                    return ApiTestResponse(success=True, data=data)
                except json.JSONDecodeError:
                    return ApiTestResponse(
                        success=False, error="Invalid JSON response from API"
                    )
            else:
                return ApiTestResponse(
                    success=False,
                    error=f"API returned status code {response.status_code}: {response.text[:200]}",
                )

    except httpx.TimeoutException:
        return ApiTestResponse(success=False, error="Request timeout")
    except httpx.RequestError as e:
        return ApiTestResponse(success=False, error=f"Connection error: {str(e)}")
    except Exception as e:
        return ApiTestResponse(success=False, error=f"Unexpected error: {str(e)}")


def suggest_shape_mappings(columns: List[str]) -> Dict[str, List[str]]:
    """Suggest mappings for shape attributes."""
    suggestions = {}

    # Common patterns for shape name fields
    name_patterns = ["name", "nom", "label", "title", "designation", "appellation"]
    id_patterns = ["id", "gid", "fid", "objectid", "code", "identifier"]
    type_patterns = ["type", "category", "class", "kind"]

    for col in columns:
        col_lower = col.lower()

        # Suggest for name field
        if any(pattern in col_lower for pattern in name_patterns):
            suggestions.setdefault("name", []).append(col)

        # Suggest for id field
        if any(pattern in col_lower for pattern in id_patterns):
            suggestions.setdefault("id", []).append(col)

        # Suggest for type field
        if any(pattern in col_lower for pattern in type_patterns):
            suggestions.setdefault("type", []).append(col)

    return suggestions


async def analyze_shape(content: bytes, filename: str) -> Dict[str, Any]:
    """Analyze shapefile or other spatial file content."""

    try:
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Handle different file types
            if filename.lower().endswith(".zip"):
                # Extract zip file (common for shapefiles)
                zip_path = temp_path / "shape.zip"
                with open(zip_path, "wb") as f:
                    f.write(content)

                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    zip_ref.extractall(temp_path)

                # Find the .shp file (search recursively, excluding macOS hidden files)
                shp_files = [
                    f
                    for f in temp_path.glob("**/*.shp")
                    if not any(
                        part.startswith("__MACOSX") or part.startswith("._")
                        for part in f.parts
                    )
                ]
                if not shp_files:
                    return {"error": "No shapefile found in zip"}

                # If multiple shapefiles, prefer the one at the shallowest depth
                shp_files.sort(key=lambda p: len(p.parts))
                file_path = shp_files[0]

                # Check if required files exist
                shp_base = file_path.with_suffix("")
                required_files = [".shp", ".shx", ".dbf"]
                missing_files = []
                for ext in required_files:
                    if not (
                        shp_base.with_suffix(ext).exists()
                        or shp_base.with_suffix(ext.upper()).exists()
                    ):
                        missing_files.append(ext)

                if missing_files:
                    return {
                        "error": f"Missing required shapefile components: {', '.join(missing_files)}. Found files: {[f.name for f in file_path.parent.glob(f'{file_path.stem}.*')]}"
                    }

            elif filename.lower().endswith((".shp", ".geojson", ".gpkg")):
                # Save the file directly
                file_path = temp_path / filename
                with open(file_path, "wb") as f:
                    f.write(content)
            else:
                return {"error": f"Unsupported file type: {filename}"}

            # Read with geopandas to get attributes
            # Try different encodings if no .cpg file is present
            try:
                gdf = gpd.read_file(file_path)
            except UnicodeDecodeError:
                # Try common encodings for shapefiles
                for encoding in ["latin1", "cp1252", "iso-8859-1"]:
                    try:
                        gdf = gpd.read_file(file_path, encoding=encoding)
                        break
                    except Exception:
                        continue
                else:
                    # If all encodings fail, try with errors='ignore'
                    gdf = gpd.read_file(file_path, encoding="utf-8", errors="ignore")

            # Get attribute columns (exclude geometry column)
            attribute_columns = [col for col in gdf.columns if col != "geometry"]

            # Get sample data
            sample_data = []
            for idx, row in gdf.head(5).iterrows():
                row_dict = row.to_dict()
                # Convert geometry to WKT for display
                if "geometry" in row_dict and row_dict["geometry"] is not None:
                    row_dict["geometry"] = (
                        row_dict["geometry"].wkt[:50] + "..."
                        if len(row_dict["geometry"].wkt) > 50
                        else row_dict["geometry"].wkt
                    )
                sample_data.append(row_dict)

            # Analyze column types
            column_types = {}
            for col in attribute_columns:
                dtype = str(gdf[col].dtype)
                if "int" in dtype:
                    column_types[col] = "integer"
                elif "float" in dtype:
                    column_types[col] = "numeric"
                else:
                    column_types[col] = "text"

            # Get geometry type
            if not gdf.empty:
                geom_types = gdf.geometry.geom_type.unique()
                geometry_type = ", ".join(geom_types)
            else:
                geometry_type = "Unknown"

            result = {
                "filename": filename,
                "type": "shape",
                "columns": attribute_columns,  # These are the shape attributes
                "column_types": column_types,
                "feature_count": len(gdf),
                "geometry_type": geometry_type,
                "crs": str(gdf.crs) if gdf.crs else "Unknown",
                "sample_data": sample_data,
                "analysis": {
                    "has_geometry": True,
                    "attribute_count": len(attribute_columns),
                    "bounds": list(gdf.total_bounds) if not gdf.empty else None,
                },
                "suggestions": suggest_shape_mappings(attribute_columns),
            }

            return result

    except Exception as e:
        # Check if it's an encoding issue
        if "codec" in str(e).lower() or "decode" in str(e).lower():
            return {
                "error": f"Encoding error: {str(e)}. The shapefile might be using a non-UTF8 encoding. Try including a .cpg file in your ZIP to specify the encoding."
            }
        return {"error": f"Failed to analyze shape file: {str(e)}"}


async def analyze_csv(content: bytes, filename: str) -> Dict[str, Any]:
    """Analyze CSV file content."""
    try:
        # Decode content
        text = content.decode("utf-8")
        lines = text.strip().split("\n")

        if not lines:
            return {"error": "Empty CSV file"}

        # Parse CSV
        reader = csv.DictReader(lines)
        columns = reader.fieldnames or []

        # Count rows
        rows = list(reader)
        row_count = len(rows)

        # Get sample data (first 5 rows)
        sample_data = rows[:5]

        # Analyze column types
        column_types = {}
        for col in columns:
            sample_values = [row.get(col, "") for row in rows[:100]]
            column_types[col] = infer_column_type(sample_values)

        return {
            "filename": filename,
            "type": "csv",
            "columns": columns,
            "column_types": column_types,
            "row_count": row_count,
            "sample_data": sample_data,
            "analysis": {
                "has_lat_lon": any(
                    "lat" in col.lower() or "lon" in col.lower() for col in columns
                ),
                "has_geometry": any(
                    "geom" in col.lower() or "wkt" in col.lower() for col in columns
                ),
                "potential_id_columns": [col for col in columns if "id" in col.lower()],
                "potential_name_columns": [
                    col
                    for col in columns
                    if "name" in col.lower() or "nom" in col.lower()
                ],
            },
        }

    except Exception as e:
        return {"error": f"Failed to analyze CSV: {str(e)}"}


async def analyze_excel(content: bytes, filename: str) -> Dict[str, Any]:
    """Analyze Excel file content."""
    try:
        import io

        # Read Excel file
        df = pd.read_excel(io.BytesIO(content))

        return {
            "filename": filename,
            "type": "excel",
            "columns": df.columns.tolist(),
            "column_types": {col: str(df[col].dtype) for col in df.columns},
            "row_count": len(df),
            "sample_data": df.head(5).to_dict("records"),
            "sheets": ["Sheet1"],  # Could be extended to handle multiple sheets
        }

    except Exception as e:
        return {"error": f"Failed to analyze Excel: {str(e)}"}


async def analyze_json(content: bytes, filename: str) -> Dict[str, Any]:
    """Analyze JSON file content."""
    try:
        data = json.loads(content)

        # Determine JSON structure
        if isinstance(data, list):
            structure = "array"
            item_count = len(data)
            sample_data = data[:5]
        elif isinstance(data, dict):
            structure = "object"
            item_count = len(data)
            sample_data = dict(list(data.items())[:5])
        else:
            structure = "primitive"
            item_count = 1
            sample_data = data

        return {
            "filename": filename,
            "type": "json",
            "structure": structure,
            "item_count": item_count,
            "sample_data": sample_data,
        }

    except Exception as e:
        return {"error": f"Failed to analyze JSON: {str(e)}"}


async def analyze_geojson(content: bytes, filename: str) -> Dict[str, Any]:
    """Analyze GeoJSON file content."""
    try:
        data = json.loads(content)

        features = data.get("features", [])
        feature_count = len(features)

        # Get geometry types
        geometry_types = set()
        properties = set()

        for feature in features[:100]:  # Sample first 100 features
            if "geometry" in feature:
                geometry_types.add(feature["geometry"]["type"])
            if "properties" in feature:
                properties.update(feature["properties"].keys())

        return {
            "filename": filename,
            "type": "geojson",
            "feature_count": feature_count,
            "geometry_types": list(geometry_types),
            "properties": list(properties),
            "sample_features": features[:5],
            "crs": data.get("crs", None),
        }

    except Exception as e:
        return {"error": f"Failed to analyze GeoJSON: {str(e)}"}


def infer_column_type(values: List[str]) -> str:
    """Infer the data type of a column from sample values."""
    non_empty = [v for v in values if v]

    if not non_empty:
        return "empty"

    # Check for numeric
    try:
        numeric_values = [float(v) for v in non_empty]
        if all(v.is_integer() for v in numeric_values):
            return "integer"
        return "float"
    except ValueError:
        pass

    # Check for boolean
    bool_values = {"true", "false", "1", "0", "yes", "no", "oui", "non"}
    if all(v.lower() in bool_values for v in non_empty):
        return "boolean"

    # Check for date/time patterns
    # This could be expanded with more sophisticated date detection

    return "string"


@router.get("/browse")
async def browse_files(path: str = ".") -> Dict[str, Any]:
    """Browse files in the filesystem."""
    try:
        p = Path(path).resolve()

        # Security check - ensure we're not going outside project directory
        # In production, this should be more restrictive

        if not p.exists():
            raise HTTPException(status_code=404, detail="Path not found")

        if p.is_file():
            return {
                "type": "file",
                "path": str(p),
                "name": p.name,
                "size": p.stat().st_size,
            }

        # List directory contents
        items = []
        for item in p.iterdir():
            items.append(
                {
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "path": str(item),
                    "size": item.stat().st_size if item.is_file() else None,
                }
            )

        return {
            "type": "directory",
            "path": str(p),
            "items": sorted(items, key=lambda x: (x["type"] != "directory", x["name"])),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/exports/list")
async def list_exports() -> Dict[str, Any]:
    """List all exported files organized by type."""
    try:
        # Get current working directory
        cwd = get_working_directory()
        exports_dir = cwd / "exports"

        if not exports_dir.exists():
            return {
                "exists": False,
                "path": str(exports_dir),
                "web": [],
                "api": [],
                "dwc": [],
            }

        result = {
            "exists": True,
            "path": str(exports_dir),
            "web": [],
            "api": [],
            "dwc": [],
        }

        # List web exports (HTML)
        web_dir = exports_dir / "web"
        if web_dir.exists():
            for item in web_dir.rglob("*.html"):
                rel_path = item.relative_to(exports_dir)
                result["web"].append(
                    {
                        "name": item.name,
                        "path": str(rel_path),
                        "full_path": str(item),
                        "size": item.stat().st_size,
                        "modified": item.stat().st_mtime,
                    }
                )

        # List API exports (JSON)
        api_dir = exports_dir / "api"
        if api_dir.exists():
            for item in api_dir.rglob("*.json"):
                rel_path = item.relative_to(exports_dir)
                result["api"].append(
                    {
                        "name": item.name,
                        "path": str(rel_path),
                        "full_path": str(item),
                        "size": item.stat().st_size,
                        "modified": item.stat().st_mtime,
                    }
                )

        # List Darwin Core exports
        dwc_dir = exports_dir / "dwc"
        if dwc_dir.exists():
            for item in dwc_dir.rglob("*.json"):
                rel_path = item.relative_to(exports_dir)
                result["dwc"].append(
                    {
                        "name": item.name,
                        "path": str(rel_path),
                        "full_path": str(item),
                        "size": item.stat().st_size,
                        "modified": item.stat().st_mtime,
                    }
                )

        # Sort by name
        for key in ["web", "api", "dwc"]:
            result[key].sort(key=lambda x: x["name"])

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing exports: {str(e)}")


@router.get("/exports/read")
async def read_export_file(file_path: str) -> Dict[str, Any]:
    """Read content of an exported file."""
    try:
        cwd = get_working_directory()
        exports_dir = cwd / "exports"

        # Construct full path
        full_path = exports_dir / file_path

        # Security check: ensure the file is within exports directory
        if not str(full_path.resolve()).startswith(str(exports_dir.resolve())):
            raise HTTPException(
                status_code=403, detail="Access denied: file outside exports directory"
            )

        # Check if file exists
        if not full_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

        # Read file content
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse JSON if it's a JSON file
        if file_path.endswith(".json"):
            try:
                import json

                parsed_content = json.loads(content)
                return {
                    "path": file_path,
                    "content": content,
                    "parsed": parsed_content,
                    "size": full_path.stat().st_size,
                }
            except json.JSONDecodeError:
                # If JSON parsing fails, return raw content
                return {
                    "path": file_path,
                    "content": content,
                    "size": full_path.stat().st_size,
                    "error": "Invalid JSON format",
                }

        # For non-JSON files, return raw content
        return {
            "path": file_path,
            "content": content,
            "size": full_path.stat().st_size,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


@router.get("/exports/structure")
async def get_exports_structure() -> Dict[str, Any]:
    """Get the directory structure of exports folder."""
    try:
        cwd = get_working_directory()
        exports_dir = cwd / "exports"

        if not exports_dir.exists():
            return {"exists": False, "path": str(exports_dir), "tree": []}

        def build_tree(
            path: Path, max_depth: int = 3, current_depth: int = 0
        ) -> List[Dict[str, Any]]:
            """Recursively build directory tree."""
            if current_depth >= max_depth:
                return []

            items = []
            try:
                for item in sorted(
                    path.iterdir(), key=lambda x: (not x.is_dir(), x.name)
                ):
                    item_data = {
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file",
                        "path": str(item.relative_to(exports_dir)),
                    }

                    if item.is_file():
                        item_data["size"] = item.stat().st_size
                        item_data["extension"] = item.suffix
                    elif item.is_dir():
                        # Count items in directory
                        try:
                            item_data["count"] = len(list(item.iterdir()))
                            # Recursively build children
                            children = build_tree(item, max_depth, current_depth + 1)
                            if children:
                                item_data["children"] = children
                        except PermissionError:
                            item_data["count"] = 0

                    items.append(item_data)
            except PermissionError:
                pass

            return items

        tree = build_tree(exports_dir)

        return {"exists": True, "path": str(exports_dir), "tree": tree}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting exports structure: {str(e)}"
        )
