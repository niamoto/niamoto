"""Shared helpers for spatial API enrichment loaders."""

from __future__ import annotations

import json
import math
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from shapely import wkb, wkt
from shapely.geometry import Point, shape
from shapely.geometry.base import BaseGeometry


def coerce_geometry(value: Any) -> Optional[BaseGeometry]:
    """Convert a row value into a Shapely geometry when possible."""

    if value is None:
        return None

    if isinstance(value, BaseGeometry):
        return value

    if isinstance(value, (bytes, bytearray)):
        try:
            return wkb.loads(bytes(value))
        except Exception:
            return None

    if isinstance(value, dict) and value.get("type"):
        try:
            return shape(value)
        except Exception:
            return None

    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None

        try:
            return wkt.loads(raw)
        except Exception:
            pass

        if raw.startswith("{") and raw.endswith("}"):
            try:
                return shape(json.loads(raw))
            except Exception:
                pass

        parsed_point = _coerce_latlon_pair(raw)
        if parsed_point is not None:
            return parsed_point

    return None


def resolve_geometry_from_row(
    row: Dict[str, Any],
    preferred_fields: Optional[Sequence[str]] = None,
) -> Tuple[Optional[str], Optional[BaseGeometry]]:
    """Find the first usable geometry-like value in an enrichment row."""

    candidates: List[str] = []
    if preferred_fields:
        candidates.extend([field for field in preferred_fields if field])
    candidates.extend(
        [
            "geo_pt",
            "location",
            "geometry",
            "geo_pt_geom",
            "geom",
            "wkt",
            "shape",
        ]
    )

    seen: set[str] = set()
    for field in candidates:
        if field in seen:
            continue
        seen.add(field)
        geometry = coerce_geometry(row.get(field))
        if geometry is not None and not geometry.is_empty:
            return field, geometry

    return None, None


def summarize_geometry(
    geometry: BaseGeometry,
    *,
    sample_mode: str,
    sample_count: int,
    include_bbox_summary: bool,
) -> Dict[str, Any]:
    """Build a compact geometry summary suitable for persisted enrichment."""

    centroid = geometry.centroid
    summary: Dict[str, Any] = {
        "geometry_type": geometry.geom_type,
        "centroid": point_to_latlon_dict(centroid),
        "sample_count": max(int(sample_count), 1),
        "sample_mode": sample_mode,
    }

    if include_bbox_summary:
        minx, miny, maxx, maxy = geometry.bounds
        summary["bbox"] = {
            "min_longitude": minx,
            "min_latitude": miny,
            "max_longitude": maxx,
            "max_latitude": maxy,
        }

    return summary


def sample_geometry_points(
    geometry: BaseGeometry,
    *,
    sample_count: int,
    sample_mode: str = "bbox_grid",
) -> List[Point]:
    """Return representative sample points for a geometry."""

    if geometry.is_empty:
        return []

    target = max(int(sample_count), 1)
    if geometry.geom_type == "Point":
        return [Point(geometry.x, geometry.y)]

    points: List[Point] = []
    _append_unique_point(points, geometry.centroid)
    _append_unique_point(points, geometry.representative_point())

    if target <= len(points):
        return points[:target]

    if sample_mode == "bbox_grid":
        grid_points = _sample_bbox_grid_points(geometry, target)
        for point in grid_points:
            _append_unique_point(points, point)
            if len(points) >= target:
                break

    if len(points) < target:
        for point in _sample_boundary_points(geometry, target):
            _append_unique_point(points, point)
            if len(points) >= target:
                break

    return points[:target]


def point_to_latlon_dict(point: Point) -> Dict[str, float]:
    """Serialize a point into API-friendly latitude/longitude keys."""

    return {
        "latitude": point.y,
        "longitude": point.x,
    }


def mean(values: Iterable[float]) -> Optional[float]:
    """Return the arithmetic mean of non-empty float collections."""

    numeric_values = list(values)
    if not numeric_values:
        return None
    return sum(numeric_values) / len(numeric_values)


def _coerce_latlon_pair(value: str) -> Optional[Point]:
    """Parse `lat,lng` or `lng,lat` text into a point."""

    pieces = [part.strip() for part in value.split(",")]
    if len(pieces) != 2:
        return None

    try:
        first = float(pieces[0])
        second = float(pieces[1])
    except ValueError:
        return None

    if abs(first) <= 90 and abs(second) <= 180:
        return Point(second, first)
    if abs(first) <= 180 and abs(second) <= 90:
        return Point(first, second)
    return None


def _append_unique_point(points: List[Point], point: Point) -> None:
    """Append a point only once, using rounded coordinates for dedupe."""

    key = (round(point.x, 8), round(point.y, 8))
    if any((round(existing.x, 8), round(existing.y, 8)) == key for existing in points):
        return
    points.append(Point(point.x, point.y))


def _sample_bbox_grid_points(geometry: BaseGeometry, target: int) -> List[Point]:
    """Generate sample points from a bbox-aligned grid."""

    minx, miny, maxx, maxy = geometry.bounds
    if minx == maxx and miny == maxy:
        return [Point(minx, miny)]

    max_grid_size = max(3, min(12, int(math.ceil(math.sqrt(target * 4)))))
    sampled: List[Point] = []

    for grid_size in range(3, max_grid_size + 1):
        candidates: List[Point] = []
        step_x = (maxx - minx) / grid_size if maxx != minx else 0
        step_y = (maxy - miny) / grid_size if maxy != miny else 0

        for ix in range(grid_size):
            x = minx + (ix + 0.5) * step_x if step_x else minx
            for iy in range(grid_size):
                y = miny + (iy + 0.5) * step_y if step_y else miny
                point = Point(x, y)
                if geometry.covers(point):
                    candidates.append(point)

        if len(candidates) >= target:
            return _downsample_points(candidates, target)
        if len(candidates) > len(sampled):
            sampled = candidates

    return sampled


def _sample_boundary_points(geometry: BaseGeometry, target: int) -> List[Point]:
    """Fallback sampling along the boundary/interior of a geometry."""

    if geometry.geom_type == "Point":
        return [Point(geometry.x, geometry.y)]

    boundary = geometry.boundary
    if boundary.is_empty:
        return [geometry.representative_point()]

    samples: List[Point] = []
    steps = max(target * 2, 4)
    for index in range(steps + 1):
        point = boundary.interpolate(index / steps, normalized=True)
        if geometry.covers(point):
            _append_unique_point(samples, point)
        if len(samples) >= target:
            break

    if not samples:
        samples.append(geometry.representative_point())

    return samples


def _downsample_points(points: Sequence[Point], target: int) -> List[Point]:
    """Keep representative points without preserving the full dense grid."""

    if len(points) <= target:
        return list(points)

    result: List[Point] = []
    if target <= 1:
        return [points[0]]

    for index in range(target):
        raw_index = round(index * (len(points) - 1) / (target - 1))
        result.append(points[raw_index])
    return result
