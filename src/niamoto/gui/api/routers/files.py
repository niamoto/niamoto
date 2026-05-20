"""File management API endpoints."""

import csv
import errno
import ipaddress
import json
import os
import socket
import stat
import threading
from typing import Dict, Any, List, Optional
from pathlib import Path
from urllib.parse import urljoin, urlparse
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
import pandas as pd
import requests
from pydantic import BaseModel
import tempfile
import zipfile
import geopandas as gpd
from starlette.concurrency import run_in_threadpool

from ..context import get_working_directory
from ..url_security import validate_public_http_url

router = APIRouter()
_PINNED_DNS_REQUEST_LOCK = threading.Lock()

SERVE_FILE_IMAGE_EXTENSIONS = {
    ".bmp",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".png",
    ".svg",
    ".tif",
    ".tiff",
    ".webp",
}

SPATIAL_IMPORT_ENTITY_TYPES = {"reference", "references", "shape", "shapes", "spatial"}
SPATIAL_ARCHIVE_EXTENSIONS = (".zip", ".geojson", ".gpkg")
MAX_ANALYZE_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024
ANALYZE_UPLOAD_CHUNK_SIZE_BYTES = 1024 * 1024
MAX_ANALYZE_ZIP_MEMBERS = 256
MAX_ANALYZE_ZIP_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
CSV_ANALYSIS_SAMPLE_ROWS = 100


def _resolve_path_under_root(root_dir: Path, path: str, *, detail: str) -> Path:
    """Resolve a path below root_dir and reject sibling-prefix escapes."""
    try:
        root_dir_resolved = root_dir.resolve()
        resolved_path = (root_dir / path).resolve()
        resolved_path.relative_to(root_dir_resolved)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=detail) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid path") from exc

    return resolved_path


def _open_regular_file_under_root(
    root_dir: Path, relative_path: str
) -> tuple[int, int]:
    """Open a regular file below root_dir without following path symlinks."""
    if root_dir.is_symlink():
        raise HTTPException(status_code=400, detail="Symlinks are not allowed")

    requested_path = Path(relative_path)
    if requested_path.is_absolute():
        raise HTTPException(
            status_code=403, detail="Access denied: file outside exports directory"
        )

    parts = requested_path.parts
    if ".." in parts:
        try:
            (root_dir / relative_path).resolve(strict=False).relative_to(
                root_dir.resolve()
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=403,
                detail="Access denied: file outside exports directory",
            ) from exc

    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise HTTPException(status_code=400, detail="Invalid path")

    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory_flag = getattr(os, "O_DIRECTORY", 0)
    root_fd: int | None = None
    current_fd: int | None = None

    try:
        root_fd = os.open(root_dir, os.O_RDONLY | directory_flag | nofollow)
        current_fd = root_fd
        root_fd = None

        for part in parts[:-1]:
            next_fd = os.open(
                part,
                os.O_RDONLY | directory_flag | nofollow,
                dir_fd=current_fd,
            )
            os.close(current_fd)
            current_fd = next_fd

        file_fd = os.open(parts[-1], os.O_RDONLY | nofollow, dir_fd=current_fd)
        file_stat = os.fstat(file_fd)
        if not stat.S_ISREG(file_stat.st_mode):
            os.close(file_fd)
            raise HTTPException(status_code=400, detail="Path is not a file")
        return file_fd, file_stat.st_size
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {relative_path}")
    except OSError as e:
        if e.errno == errno.ELOOP:
            raise HTTPException(status_code=400, detail="Symlinks are not allowed")
        if e.errno in {errno.ENOTDIR, errno.EISDIR}:
            raise HTTPException(status_code=400, detail="Path is not a file")
        raise
    finally:
        if current_fd is not None:
            os.close(current_fd)
        if root_fd is not None:
            os.close(root_fd)


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


def _is_disallowed_api_address(address: str) -> bool:
    """Return True when an API test target points at a non-public address."""
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return True

    return not ip.is_global


def _resolve_api_test_url_addresses(url: str) -> tuple[Optional[str], list[str]]:
    """Validate a URL and return public addresses to pin during the request."""
    try:
        validate_public_http_url(url, detail="API URL host is not allowed")
    except HTTPException as exc:
        detail = str(exc.detail)
        if detail == "Invalid URL.":
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"}:
                return "Only http and https API URLs are allowed", []
            if not parsed.hostname:
                return "API URL must include a hostname", []
        return detail, []

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return "Only http and https API URLs are allowed", []
    if not parsed.hostname:
        return "API URL must include a hostname", []

    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith(".localhost"):
        return "API URL host is not allowed", []

    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        try:
            resolved = socket.getaddrinfo(
                hostname,
                parsed.port,
                type=socket.SOCK_STREAM,
            )
        except socket.gaierror:
            return "API URL host could not be resolved", []

        addresses = {info[4][0] for info in resolved}
    else:
        addresses = {str(ip)}

    if any(_is_disallowed_api_address(address) for address in addresses):
        return "API URL host is not allowed", []

    return None, sorted(addresses)


def _validate_api_test_url(url: str) -> Optional[str]:
    """Validate user-provided API test URLs before server-side requests."""
    error, _addresses = _resolve_api_test_url_addresses(url)
    return error


def _get_with_pinned_public_dns(
    url: str,
    *,
    headers: Dict[str, str],
    params: Dict[str, str],
    timeout: float,
) -> requests.Response:
    """Perform a request while pinning DNS to the public addresses we validated."""
    validation_error, addresses = _resolve_api_test_url_addresses(url)
    if validation_error:
        raise ValueError(validation_error)

    parsed = urlparse(url)
    hostname = parsed.hostname.rstrip(".").lower() if parsed.hostname else ""
    original_getaddrinfo = socket.getaddrinfo

    def pinned_getaddrinfo(host, port, *args, **kwargs):
        requested_host = str(host).rstrip(".").lower()
        if requested_host == hostname:
            return [
                (
                    socket.AF_INET6 if ":" in address else socket.AF_INET,
                    socket.SOCK_STREAM,
                    0,
                    "",
                    (address, port, 0, 0) if ":" in address else (address, port),
                )
                for address in addresses
            ]
        return original_getaddrinfo(host, port, *args, **kwargs)

    with _PINNED_DNS_REQUEST_LOCK:
        socket.getaddrinfo = pinned_getaddrinfo
        try:
            return requests.get(
                url,
                headers=headers,
                params=params,
                timeout=timeout,
                allow_redirects=False,
                stream=True,
            )
        finally:
            socket.getaddrinfo = original_getaddrinfo


def _iter_response_peer_addresses(response: requests.Response) -> list[str]:
    """Best-effort extraction of the actual connected peer IP from urllib3."""
    candidates = [
        ("raw", "_connection", "sock"),
        ("raw", "connection", "sock"),
        ("raw", "_fp", "fp", "raw", "_sock"),
    ]
    addresses: list[str] = []
    for chain in candidates:
        current: Any = response
        for attr in chain:
            current = getattr(current, attr, None)
            if current is None:
                break
        if current is None:
            continue
        try:
            peer = current.getpeername()
        except OSError:
            continue
        if isinstance(peer, tuple) and peer and isinstance(peer[0], str) and peer[0]:
            addresses.append(peer[0])
    return addresses


def _validate_api_response_peer(response: requests.Response) -> str | None:
    for address in _iter_response_peer_addresses(response):
        if _is_disallowed_api_address(address):
            return "API URL host is not allowed"
    return None


async def _read_upload_content_limited(file: UploadFile) -> bytes:
    """Read an upload with an explicit size cap for analysis endpoints."""
    chunks: list[bytes] = []
    total_size = 0
    while chunk := await file.read(ANALYZE_UPLOAD_CHUNK_SIZE_BYTES):
        total_size += len(chunk)
        if total_size > MAX_ANALYZE_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=(
                    "Uploaded file exceeds the maximum allowed analysis size "
                    f"of {MAX_ANALYZE_UPLOAD_SIZE_BYTES} bytes"
                ),
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _validate_zip_member_path(member_name: str) -> Path:
    member_path = Path(member_name)
    if member_path.is_absolute() or any(
        part in {"", ".", ".."} for part in member_path.parts
    ):
        raise ValueError(f"Invalid ZIP member path: {member_name}")
    return member_path


def _extract_zip_safely(zip_ref: zipfile.ZipFile, target_dir: Path) -> None:
    """Extract a ZIP archive with member count, expanded size, and path limits."""
    members = zip_ref.infolist()
    if len(members) > MAX_ANALYZE_ZIP_MEMBERS:
        raise ValueError(
            f"Archive contains too many files ({len(members)} > {MAX_ANALYZE_ZIP_MEMBERS})"
        )

    total_size = 0
    target_root = target_dir.resolve()
    for member in members:
        total_size += member.file_size
        if total_size > MAX_ANALYZE_ZIP_UNCOMPRESSED_BYTES:
            raise ValueError(
                "Archive exceeds maximum uncompressed analysis size "
                f"of {MAX_ANALYZE_ZIP_UNCOMPRESSED_BYTES} bytes"
            )

        member_path = _validate_zip_member_path(member.filename)
        destination = (target_dir / member_path).resolve()
        try:
            destination.relative_to(target_root)
        except ValueError as exc:
            raise ValueError(f"Invalid ZIP member path: {member.filename}") from exc

        if member.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        with zip_ref.open(member, "r") as source, destination.open("wb") as dest:
            while chunk := source.read(1024 * 1024):
                dest.write(chunk)


@router.post("/analyze")
async def analyze_file(
    file: UploadFile = File(...), entity_type: str = Form(...)
) -> Dict[str, Any]:
    """Analyze a file for import configuration."""
    try:
        # Read file content
        content = await _read_upload_content_limited(file)

        # Basic analysis based on file type
        filename_lower = file.filename.lower()
        is_spatial_entity = entity_type in SPATIAL_IMPORT_ENTITY_TYPES

        if is_spatial_entity and filename_lower.endswith(SPATIAL_ARCHIVE_EXTENSIONS):
            result = await analyze_shape(content, file.filename)
        elif filename_lower.endswith(".csv"):
            result = await analyze_csv(content, file.filename)
        elif filename_lower.endswith((".xls", ".xlsx")):
            result = await analyze_excel(content, file.filename)
        elif is_spatial_entity and filename_lower.endswith(".shp"):
            return {
                "error": "Shapefile analysis requires all component files (.shp, .shx, .dbf). Please upload a ZIP file containing all shapefile components."
            }
        else:
            return {"error": f"Unsupported file type: {file.filename}"}

        # Add entity_type for compatibility
        result["entity_type"] = entity_type
        # Keep suggestions generic - specific field mapping done in frontend
        result.setdefault("suggestions", {})

        return result

    except HTTPException:
        raise
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
            gdf = gpd.read_file(tmp_path, engine="pyogrio")

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
        validation_error = _validate_api_test_url(request.url)
        if validation_error:
            return ApiTestResponse(success=False, error=validation_error)

        response = await run_in_threadpool(
            _get_with_pinned_public_dns,
            request.url,
            headers=request.headers,
            params=request.params,
            timeout=10.0,
        )
        peer_error = _validate_api_response_peer(response)
        if peer_error:
            response.close()
            return ApiTestResponse(success=False, error=peer_error)

        if 300 <= response.status_code < 400:
            redirect_target = response.headers.get("Location")
            if redirect_target:
                redirect_url = urljoin(request.url, redirect_target)
                redirect_error = _validate_api_test_url(redirect_url)
                if redirect_error:
                    return ApiTestResponse(success=False, error=redirect_error)

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

    except requests.exceptions.Timeout:
        return ApiTestResponse(success=False, error="Request timeout")
    except requests.exceptions.RequestException as e:
        return ApiTestResponse(success=False, error=f"Connection error: {str(e)}")
    except ValueError as e:
        return ApiTestResponse(success=False, error=str(e))
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
                    _extract_zip_safely(zip_ref, temp_path)

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
                gdf = gpd.read_file(file_path, engine="pyogrio")
            except UnicodeDecodeError:
                # Try common encodings for shapefiles
                for encoding in ["latin1", "cp1252", "iso-8859-1"]:
                    try:
                        gdf = gpd.read_file(
                            file_path, encoding=encoding, engine="pyogrio"
                        )
                        break
                    except Exception:
                        continue
                else:
                    # If all encodings fail, try with errors='ignore'
                    gdf = gpd.read_file(
                        file_path,
                        encoding="utf-8",
                        errors="ignore",
                        engine="pyogrio",
                    )

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
        lines = text.strip().splitlines()

        if not lines:
            return {"error": "Empty CSV file"}

        # Parse CSV
        reader = csv.DictReader(lines)
        columns = reader.fieldnames or []

        # Count rows while retaining only the rows needed for preview/type inference.
        sampled_rows = []
        row_count = 0
        for row in reader:
            row_count += 1
            if len(sampled_rows) < CSV_ANALYSIS_SAMPLE_ROWS:
                sampled_rows.append(row)

        # Get sample data (first 5 rows)
        sample_data = sampled_rows[:5]

        # Analyze column types
        column_types = {}
        for col in columns:
            sample_values = [row.get(col, "") for row in sampled_rows]
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
        p = _resolve_path_under_root(
            get_working_directory(),
            path,
            detail="Access denied: path outside project directory",
        )

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

    except HTTPException:
        raise
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
                "path": "exports",
                "web": [],
                "api": [],
                "dwc": [],
            }

        result = {
            "exists": True,
            "path": "exports",
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

        fd: int | None = None
        try:
            fd, file_size = _open_regular_file_under_root(exports_dir, file_path)
            with os.fdopen(fd, "r", encoding="utf-8") as f:
                fd = None
                content = f.read()
        finally:
            if fd is not None:
                os.close(fd)

        # Parse JSON if it's a JSON file
        if file_path.endswith(".json"):
            try:
                import json

                parsed_content = json.loads(content)
                return {
                    "path": file_path,
                    "content": content,
                    "parsed": parsed_content,
                    "size": file_size,
                }
            except json.JSONDecodeError:
                # If JSON parsing fails, return raw content
                return {
                    "path": file_path,
                    "content": content,
                    "size": file_size,
                    "error": "Invalid JSON format",
                }

        # For non-JSON files, return raw content
        return {
            "path": file_path,
            "content": content,
            "size": file_size,
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
        if exports_dir.is_symlink():
            raise HTTPException(status_code=400, detail="Symlinks are not allowed")

        exports_dir_resolved = exports_dir.resolve(strict=True)

        def build_tree(
            path: Path, max_depth: int = 3, current_depth: int = 0
        ) -> List[Dict[str, Any]]:
            """Recursively build directory tree."""
            if current_depth >= max_depth:
                return []

            def sort_key(item: Path) -> tuple[bool, str]:
                try:
                    item_mode = item.stat(follow_symlinks=False).st_mode
                    is_dir = stat.S_ISDIR(item_mode)
                except OSError:
                    is_dir = False
                return (not is_dir, item.name)

            items = []
            try:
                for item in sorted(path.iterdir(), key=sort_key):
                    if item.is_symlink():
                        continue

                    try:
                        resolved_item = item.resolve(strict=True)
                        resolved_item.relative_to(exports_dir_resolved)
                    except (OSError, ValueError):
                        continue

                    item_stat = item.stat(follow_symlinks=False)
                    is_file = stat.S_ISREG(item_stat.st_mode)
                    is_dir = stat.S_ISDIR(item_stat.st_mode)
                    item_data = {
                        "name": item.name,
                        "type": "directory" if is_dir else "file",
                        "path": str(item.relative_to(exports_dir)),
                    }

                    if is_file:
                        item_data["size"] = item_stat.st_size
                        item_data["extension"] = item.suffix
                    elif is_dir:
                        # Count items in directory
                        try:
                            item_data["count"] = len(
                                [
                                    child
                                    for child in item.iterdir()
                                    if not child.is_symlink()
                                ]
                            )
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


@router.get("/serve/{file_path:path}")
async def serve_file(file_path: str):
    """
    Serve a file from the project directory.

    Used for displaying images like logos in the UI.
    """
    from fastapi.responses import FileResponse

    work_dir = get_working_directory()
    if not work_dir:
        raise HTTPException(status_code=500, detail="Working directory not set")

    full_path = _resolve_path_under_root(
        work_dir,
        file_path,
        detail="Access denied",
    )
    files_dir = (work_dir / "files").resolve()
    try:
        full_path.relative_to(files_dir)
    except ValueError as exc:
        raise HTTPException(
            status_code=403, detail="Access denied: file outside files directory"
        ) from exc

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not full_path.is_file():
        raise HTTPException(status_code=400, detail="Not a file")

    if full_path.suffix.lower() not in SERVE_FILE_IMAGE_EXTENSIONS:
        raise HTTPException(status_code=403, detail="Unsupported file type")

    # Determine content type
    import mimetypes

    content_type, _ = mimetypes.guess_type(str(full_path))

    return FileResponse(
        full_path,
        media_type=content_type or "application/octet-stream",
        filename=full_path.name,
    )
