"""File management API endpoints."""

import csv
import json
from typing import Dict, Any, List
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
import pandas as pd

router = APIRouter()


@router.post("/analyze")
async def analyze_file(
    file: UploadFile = File(...), import_type: str = Form(...)
) -> Dict[str, Any]:
    """Analyze a file for import configuration."""
    try:
        # Read file content
        content = await file.read()

        # Basic analysis based on file type
        if file.filename.endswith(".csv"):
            result = await analyze_csv(content, file.filename)
        elif file.filename.endswith((".xls", ".xlsx")):
            result = await analyze_excel(content, file.filename)
        elif file.filename.endswith(".json"):
            result = await analyze_json(content, file.filename)
        elif file.filename.endswith(".geojson"):
            result = await analyze_geojson(content, file.filename)
        elif file.filename.endswith(".gpkg"):
            result = await analyze_geopackage(content, file.filename)
        elif file.filename.endswith(".shp"):
            return {
                "error": "Shapefile analysis requires all component files (.shp, .shx, .dbf)"
            }
        else:
            return {"error": f"Unsupported file type: {file.filename}"}

        # Add import-type specific analysis
        result["import_type"] = import_type
        result["suggestions"] = get_field_suggestions(result, import_type)

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
