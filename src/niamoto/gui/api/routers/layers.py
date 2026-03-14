# src/niamoto/gui/api/routers/layers.py

"""
API endpoints for geographic layer management.

Lists raster and vector files in the imports/ directory with their metadata
(CRS, extent, columns for vector, bands for raster).
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from niamoto.gui.api.context import get_working_directory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/layers", tags=["layers"])


# File type extensions
RASTER_EXTENSIONS = {".tif", ".tiff", ".asc", ".img", ".vrt", ".nc"}
VECTOR_EXTENSIONS = {".gpkg", ".shp", ".geojson", ".json", ".kml", ".gml"}


class RasterMetadata(BaseModel):
    """Metadata for a raster layer."""

    type: Literal["raster"] = "raster"
    path: str
    name: str
    size_bytes: int
    crs: Optional[str] = None
    extent: Optional[Dict[str, float]] = None  # minx, miny, maxx, maxy
    width: Optional[int] = None
    height: Optional[int] = None
    bands: Optional[int] = None
    dtype: Optional[str] = None
    nodata: Optional[float] = None


class VectorMetadata(BaseModel):
    """Metadata for a vector layer."""

    type: Literal["vector"] = "vector"
    path: str
    name: str
    size_bytes: int
    crs: Optional[str] = None
    extent: Optional[Dict[str, float]] = None
    feature_count: Optional[int] = None
    geometry_type: Optional[str] = None
    columns: Optional[List[str]] = None


class LayersListResponse(BaseModel):
    """Response for layers listing."""

    raster: List[RasterMetadata]
    vector: List[VectorMetadata]
    base_path: str


def get_raster_metadata(file_path: Path) -> RasterMetadata:
    """Extract metadata from a raster file."""
    metadata = RasterMetadata(
        path=str(file_path),
        name=file_path.name,
        size_bytes=file_path.stat().st_size,
    )

    try:
        # Try to use rasterio if available
        import rasterio

        with rasterio.open(file_path) as src:
            metadata.crs = str(src.crs) if src.crs else None
            metadata.width = src.width
            metadata.height = src.height
            metadata.bands = src.count
            metadata.dtype = str(src.dtypes[0]) if src.dtypes else None
            metadata.nodata = src.nodata

            if src.bounds:
                metadata.extent = {
                    "minx": src.bounds.left,
                    "miny": src.bounds.bottom,
                    "maxx": src.bounds.right,
                    "maxy": src.bounds.top,
                }
    except ImportError:
        logger.debug("rasterio not available, skipping raster metadata extraction")
    except Exception as e:
        logger.warning(f"Could not read raster metadata for {file_path}: {e}")

    return metadata


def get_vector_metadata(file_path: Path) -> VectorMetadata:
    """Extract metadata from a vector file."""
    metadata = VectorMetadata(
        path=str(file_path),
        name=file_path.name,
        size_bytes=file_path.stat().st_size,
    )

    try:
        # Try to use geopandas/fiona if available
        import geopandas as gpd

        gdf = gpd.read_file(file_path, rows=0)  # Read only schema, not data

        metadata.crs = str(gdf.crs) if gdf.crs else None
        metadata.columns = [col for col in gdf.columns if col != "geometry"]

        # Get geometry type from first feature
        gdf_sample = gpd.read_file(file_path, rows=1)
        if len(gdf_sample) > 0 and gdf_sample.geometry is not None:
            geom = gdf_sample.geometry.iloc[0]
            if geom is not None:
                metadata.geometry_type = geom.geom_type

        # Get feature count (may be slow for large files)
        try:
            import fiona

            with fiona.open(file_path) as src:
                metadata.feature_count = len(src)
                if src.bounds:
                    metadata.extent = {
                        "minx": src.bounds[0],
                        "miny": src.bounds[1],
                        "maxx": src.bounds[2],
                        "maxy": src.bounds[3],
                    }
        except Exception:
            # Fallback: count from geopandas (slower)
            gdf_full = gpd.read_file(file_path)
            metadata.feature_count = len(gdf_full)
            if not gdf_full.empty and gdf_full.total_bounds is not None:
                bounds = gdf_full.total_bounds
                metadata.extent = {
                    "minx": bounds[0],
                    "miny": bounds[1],
                    "maxx": bounds[2],
                    "maxy": bounds[3],
                }

    except ImportError:
        logger.debug("geopandas not available, skipping vector metadata extraction")
    except Exception as e:
        logger.warning(f"Could not read vector metadata for {file_path}: {e}")

    return metadata


@router.get("", response_model=LayersListResponse)
async def list_layers(
    type: Optional[Literal["raster", "vector", "all"]] = "all",
    include_metadata: bool = True,
) -> LayersListResponse:
    """
    List all geographic layers in the imports/ directory.

    Args:
        type: Filter by layer type ("raster", "vector", or "all")
        include_metadata: Whether to extract detailed metadata (slower)

    Returns:
        List of raster and vector layers with their metadata
    """
    work_dir = get_working_directory()
    if not work_dir:
        raise HTTPException(status_code=500, detail="Working directory not configured")

    imports_dir = Path(work_dir) / "imports"
    if not imports_dir.exists():
        return LayersListResponse(raster=[], vector=[], base_path=str(imports_dir))

    raster_layers: List[RasterMetadata] = []
    vector_layers: List[VectorMetadata] = []

    # Scan imports directory recursively
    for file_path in imports_dir.rglob("*"):
        if not file_path.is_file():
            continue

        ext = file_path.suffix.lower()
        relative_path = file_path.relative_to(Path(work_dir))

        if ext in RASTER_EXTENSIONS and type in ("raster", "all"):
            if include_metadata:
                metadata = get_raster_metadata(file_path)
                metadata.path = str(relative_path)
            else:
                metadata = RasterMetadata(
                    path=str(relative_path),
                    name=file_path.name,
                    size_bytes=file_path.stat().st_size,
                )
            raster_layers.append(metadata)

        elif ext in VECTOR_EXTENSIONS and type in ("vector", "all"):
            # Skip .shp auxiliary files
            if ext == ".shp":
                # Only include main .shp file
                pass
            elif ext in (".dbf", ".shx", ".prj", ".cpg"):
                continue

            if include_metadata:
                metadata = get_vector_metadata(file_path)
                metadata.path = str(relative_path)
            else:
                metadata = VectorMetadata(
                    path=str(relative_path),
                    name=file_path.name,
                    size_bytes=file_path.stat().st_size,
                )
            vector_layers.append(metadata)

    # Sort by name
    raster_layers.sort(key=lambda x: x.name.lower())
    vector_layers.sort(key=lambda x: x.name.lower())

    return LayersListResponse(
        raster=raster_layers,
        vector=vector_layers,
        base_path=str(imports_dir),
    )


@router.get("/{layer_path:path}")
async def get_layer_info(layer_path: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific layer.

    Args:
        layer_path: Path to the layer file (relative to working directory)

    Returns:
        Detailed layer metadata including sample data preview
    """
    work_dir = get_working_directory()
    if not work_dir:
        raise HTTPException(status_code=500, detail="Working directory not configured")

    file_path = Path(work_dir) / layer_path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Layer not found: {layer_path}")

    ext = file_path.suffix.lower()

    if ext in RASTER_EXTENSIONS:
        metadata = get_raster_metadata(file_path)
        return {
            "type": "raster",
            "metadata": metadata.model_dump(),
            "preview": None,  # Could add histogram or thumbnail
        }

    elif ext in VECTOR_EXTENSIONS:
        metadata = get_vector_metadata(file_path)

        # Get sample data
        sample_data = None
        try:
            import geopandas as gpd

            gdf = gpd.read_file(file_path, rows=5)
            # Convert to dict, excluding geometry for JSON serialization
            sample_data = gdf.drop(columns=["geometry"], errors="ignore").to_dict(
                orient="records"
            )
        except Exception as e:
            logger.warning(f"Could not read sample data: {e}")

        return {
            "type": "vector",
            "metadata": metadata.model_dump(),
            "sample_data": sample_data,
        }

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")
