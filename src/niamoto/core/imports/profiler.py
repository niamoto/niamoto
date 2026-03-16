"""
Data profiler for automatic dataset analysis and semantic detection.
This module analyzes data files to detect their structure and suggest entity types.

Semantic detection uses AliasRegistry (header-based fuzzy matching) as the primary
name-based detector, supplemented by value-based high-precision rules for coordinates,
WKT geometry, and dates.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
import pandas as pd
import logging

try:
    import geopandas as gpd

    HAS_GEOPANDAS = True
except ImportError:
    HAS_GEOPANDAS = False

from niamoto.core.imports.ml.alias_registry import AliasRegistry

logger = logging.getLogger(__name__)

# Shared AliasRegistry instance (loaded once, thread-safe read-only)
_alias_registry: Optional[AliasRegistry] = None


def _get_alias_registry() -> AliasRegistry:
    """Return the module-level AliasRegistry singleton."""
    global _alias_registry
    if _alias_registry is None:
        _alias_registry = AliasRegistry()
    return _alias_registry


@dataclass
class ColumnProfile:
    """Profile of a single column in a dataset."""

    name: str
    dtype: str
    semantic_type: Optional[str] = None
    unique_ratio: float = 0.0
    null_ratio: float = 0.0
    sample_values: List[Any] = field(default_factory=list)
    confidence: float = 0.0
    semantic_profile: Optional[Any] = None  # ColumnSemanticProfile at runtime
    anomalies: Optional[Dict[str, Any]] = None  # anomaly detection summary

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "name": self.name,
            "dtype": self.dtype,
            "semantic_type": self.semantic_type,
            "unique_ratio": round(self.unique_ratio, 4),
            "null_ratio": round(self.null_ratio, 4),
            "confidence": round(self.confidence, 2),
            "sample_values": self.sample_values[:5],  # Limit samples
        }
        if self.semantic_profile:
            result["semantic_profile"] = self.semantic_profile.to_dict()
        if self.anomalies:
            result["anomalies"] = self.anomalies
        return result


@dataclass
class DatasetProfile:
    """Complete profile of a dataset."""

    file_path: Path
    record_count: int
    columns: List[ColumnProfile]
    detected_type: str  # 'hierarchical', 'spatial', 'factual', 'statistical'
    suggested_name: str
    relationships: List[Dict[str, str]] = field(default_factory=list)
    geometry_type: Optional[str] = None
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "file_path": str(self.file_path),
            "record_count": self.record_count,
            "columns": [col.to_dict() for col in self.columns],
            "detected_type": self.detected_type,
            "suggested_name": self.suggested_name,
            "relationships": self.relationships,
            "geometry_type": self.geometry_type,
            "confidence": round(self.confidence, 2),
        }

    def has_taxonomy_columns(self) -> bool:
        """Check if dataset has taxonomic columns."""
        taxonomy_types = {"taxonomy.family", "taxonomy.genus", "taxonomy.species"}
        return any(col.semantic_type in taxonomy_types for col in self.columns)

    def has_spatial_columns(self) -> bool:
        """Check if dataset has spatial columns."""
        spatial_types = {"geometry", "coordinates", "location.point"}
        return (
            any(col.semantic_type in spatial_types for col in self.columns)
            or self.geometry_type is not None
        )


class DataProfiler:
    """Analyzes datasets to detect structure and semantics.

    Uses AliasRegistry for name-based detection (fuzzy header matching)
    and value-based high-precision rules for coordinates, WKT, and dates.
    """

    def __init__(self, **kwargs):
        """Initialize the profiler.

        Accepts (and ignores) legacy keyword arguments ``ml_mode`` and
        ``ml_detector`` for backward compatibility. All semantic detection
        now goes through ``AliasRegistry`` + value-based rules.
        """
        # Silently accept legacy kwargs for backward compat (no-op)
        if "ml_detector" in kwargs or "ml_mode" in kwargs:
            logger.debug(
                "ml_mode/ml_detector parameters are ignored — "
                "detection uses AliasRegistry"
            )
        self._alias_registry = _get_alias_registry()

    # Maximum rows to load for profiling (statistical accuracy ±0.5% at 99% confidence)
    PROFILING_SAMPLE_SIZE = 50_000

    def profile(self, file_path: Path) -> DatasetProfile:
        """Generate complete profile of a dataset by loading from file.

        For large files, loads only a sample (PROFILING_SAMPLE_SIZE rows).
        The full row count is preserved as total_count.
        """
        # Load data (may be sampled for large files)
        data = self._load_data(file_path)

        if data is None:
            raise ValueError(f"Could not load data from {file_path}")

        # total_count = actual rows loaded (no sampling in _load_data for non-CSV)
        # For the standalone profile() path, total_count = len(data)
        return self.profile_dataframe(data, file_path)

    def profile_dataframe(
        self,
        df: pd.DataFrame,
        file_path: Path,
        total_count: Optional[int] = None,
    ) -> DatasetProfile:
        """Generate complete profile from an already-loaded DataFrame.

        Avoids redundant file I/O when the DataFrame is already in memory.

        Args:
            df: DataFrame to profile
            file_path: Original file path (for name suggestion and metadata)
            total_count: Actual row count if df is a sample (e.g. from DuckDB COUNT).
                        If None, uses len(df).
        """
        # Store file path in data attributes for detection
        df.attrs["file_path"] = file_path

        # Profile columns
        columns = []
        for col_name in df.columns:
            col_profile = self._profile_column(df[col_name], col_name)
            columns.append(col_profile)

        # Detect dataset type based on column profiles
        dataset_type = self._detect_dataset_type(columns, df)

        # Suggest entity name
        suggested_name = self._suggest_entity_name(file_path, dataset_type)

        # Detect relationships
        relationships = self._detect_relationships(columns)

        # Calculate overall confidence
        confidence = self._calculate_confidence(columns)

        # Check for geometry if geopandas
        geometry_type = None
        if hasattr(df, "geometry"):
            geometry_type = self._detect_geometry_type(df)

        return DatasetProfile(
            file_path=file_path,
            record_count=total_count if total_count is not None else len(df),
            columns=columns,
            detected_type=dataset_type,
            suggested_name=suggested_name,
            relationships=relationships,
            geometry_type=geometry_type,
            confidence=confidence,
        )

    def _load_data(self, file_path: Path) -> Optional[pd.DataFrame]:
        """Load data from various file formats.

        Supports CSV, TSV, TXT (with delimiter sniffing), GeoJSON, SHP, GPKG, XLSX.
        Falls back to latin-1 encoding on UnicodeDecodeError.
        """
        file_str = str(file_path)
        suffix = file_path.suffix.lower()

        try:
            if suffix in (".csv", ".tsv", ".txt"):
                return self._load_csv_like(file_str, nrows=self.PROFILING_SAMPLE_SIZE)
            elif suffix in (".geojson", ".json"):
                if HAS_GEOPANDAS:
                    return gpd.read_file(file_str)
                else:
                    return pd.read_json(file_str)
            elif suffix in (".shp", ".gpkg"):
                if HAS_GEOPANDAS:
                    return gpd.read_file(file_str)
            elif suffix in (".xlsx", ".xls"):
                return pd.read_excel(file_str)
        except Exception as e:
            logger.warning(f"Error loading {file_path}: {e}")

        return None

    def _load_csv_like(
        self, file_path: str, nrows: Optional[int] = None
    ) -> pd.DataFrame:
        """Load CSV/TSV/TXT with delimiter sniffing and encoding fallback."""
        import csv as csv_module

        # Sniff delimiter from first 8KB
        sep = ","
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                sample = f.read(8192)
                dialect = csv_module.Sniffer().sniff(sample, delimiters=",\t;|")
                sep = dialect.delimiter
        except Exception:
            # If sniffing fails, try tab (common for GBIF), then comma
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    first_line = f.readline()
                    if "\t" in first_line:
                        sep = "\t"
            except Exception:
                pass

        # Try UTF-8 first, fallback to latin-1
        try:
            return pd.read_csv(file_path, sep=sep, low_memory=False, nrows=nrows)
        except UnicodeDecodeError:
            return pd.read_csv(
                file_path, sep=sep, low_memory=False, encoding="latin-1", nrows=nrows
            )

    def _profile_column(self, series: pd.Series, col_name: str) -> ColumnProfile:
        """Profile a single column."""
        profile = ColumnProfile(name=col_name, dtype=str(series.dtype))

        # Calculate basic statistics
        total_count = len(series)
        if total_count > 0:
            profile.unique_ratio = series.nunique() / total_count
            profile.null_ratio = series.isnull().sum() / total_count

        # Get sample values
        non_null = series.dropna()
        if len(non_null) > 0:
            profile.sample_values = non_null.head(10).tolist()

        # Detect semantic type (legacy flat string)
        semantic_type, confidence = self._detect_semantic_type(col_name, series)
        profile.semantic_type = semantic_type
        profile.confidence = confidence

        # Build rich semantic profile
        profile.semantic_profile = self._build_semantic_profile(
            semantic_type, confidence
        )

        # Run anomaly detection if concept is known
        if semantic_type and len(non_null) > 0:
            from niamoto.core.imports.ml.anomaly_rules import summarize_anomalies

            anomaly_summary = summarize_anomalies(series, semantic_type)
            if anomaly_summary:
                profile.anomalies = anomaly_summary

        return profile

    def _build_semantic_profile(self, semantic_type: Optional[str], confidence: float):
        """Build a ColumnSemanticProfile from a flat semantic_type string."""
        from niamoto.core.imports.ml.semantic_profile import (
            ColumnSemanticProfile,
            get_affordances,
        )

        if not semantic_type:
            return ColumnSemanticProfile(role="other", confidence=confidence)

        # Extract role from "taxonomy.species" → "taxonomy"
        parts = semantic_type.split(".")
        role = parts[0]
        concept = semantic_type if len(parts) > 1 else None

        return ColumnSemanticProfile(
            role=role,
            concept=concept,
            affordances=get_affordances(concept, role),
            confidence=confidence,
        )

    def _detect_semantic_type(
        self, col_name: str, series: pd.Series
    ) -> Tuple[Optional[str], float]:
        """Detect the semantic type of a column.

        Strategy:
        1. AliasRegistry match on column name (exact + fuzzy).
        2. Value-based high-precision rules (lat/lon range, WKT, foreign keys).
        """
        # ── 1. Name-based: AliasRegistry ──────────────────────────────
        concept, score = self._alias_registry.match(col_name)
        if concept and score > 0:
            # Boost confidence for coordinate columns if values confirm
            if concept == "location.latitude" and pd.api.types.is_numeric_dtype(series):
                clean = series.dropna()
                if len(clean) > 0 and -90 <= clean.min() and clean.max() <= 90:
                    return concept, max(score, 0.9)
            if concept == "location.longitude" and pd.api.types.is_numeric_dtype(
                series
            ):
                clean = series.dropna()
                if len(clean) > 0 and -180 <= clean.min() and clean.max() <= 180:
                    return concept, max(score, 0.9)
            return concept, score

        # ── 2. Value-based rules (high-precision fallback) ────────────
        col_lower = col_name.lower()

        # Foreign key heuristics (id prefix/suffix not covered by alias registry)
        if col_lower.startswith("id") or col_lower.endswith("_id"):
            if "taxon" in col_lower or "taxonref" in col_lower:
                return "identifier.taxon", 0.8
            elif "plot" in col_lower or "site" in col_lower:
                return "identifier.plot", 0.8
            else:
                return "identifier.record", 0.7

        # WKT geometry detection on values
        sample = series.dropna().head(5).astype(str)
        if sample.str.contains("POINT|POLYGON|LINESTRING").any():
            return "geometry", 0.95

        return None, 0.0

    def _detect_dataset_type(
        self, columns: List[ColumnProfile], data: pd.DataFrame
    ) -> str:
        """Determine the type of dataset based on column profiles."""
        semantic_types = [col.semantic_type for col in columns if col.semantic_type]

        # Special case: occurrences/observations files are always factual
        file_name_lower = str(getattr(data, "attrs", {}).get("file_path", "")).lower()
        if "occurrence" in file_name_lower or "observation" in file_name_lower:
            return "factual"

        # Check for spatial data first (geometry takes precedence)
        if hasattr(data, "geometry") or any(
            "geometry" in t for t in semantic_types if t
        ):
            return "spatial"

        # Check for location/plot data with coordinates
        location_count = sum(
            1 for t in semantic_types if t and t.startswith("location.")
        )
        if location_count >= 1:
            # If it has coordinates or geometry, it's spatial
            has_coords = any(
                "location.latitude" in t or "location.longitude" in t or "geometry" in t
                for t in semantic_types
                if t
            )
            if has_coords:
                return "spatial"

        # Check for hierarchical (taxonomy) data
        # But only if it's a small dataset (likely a reference)
        taxonomy_count = sum(
            1 for t in semantic_types if t and t.startswith("taxonomy.")
        )
        if (
            taxonomy_count >= 2 and len(data) < 10000
        ):  # Small dataset with taxonomy = reference
            return "hierarchical"

        # Check for statistical data (many numeric columns)
        numeric_cols = sum(
            1 for col in columns if "float" in col.dtype or "int" in col.dtype
        )
        if numeric_cols > len(columns) * 0.6:  # More than 60% numeric
            return "statistical"

        # Large datasets with mixed content are factual
        if len(data) > 1000:
            return "factual"

        # Default to factual data (occurrences, observations)
        return "factual"

    def _suggest_entity_name(self, file_path: Path, dataset_type: str) -> str:
        """Suggest an entity name based on file name and type."""
        base_name = file_path.stem.lower()

        # Clean up common prefixes/suffixes
        for prefix in ["raw_", "data_", "export_"]:
            if base_name.startswith(prefix):
                base_name = base_name[len(prefix) :]

        for suffix in ["_data", "_export", "_raw"]:
            if base_name.endswith(suffix):
                base_name = base_name[: -len(suffix)]

        # Handle known patterns
        if "occurrence" in base_name or "observation" in base_name:
            return "observations"
        elif "plot" in base_name or "site" in base_name:
            return "locations"
        elif "shape" in base_name:
            return base_name.replace("_stats", "")
        elif "taxon" in base_name or "species" in base_name:
            return "species"

        return base_name

    def _detect_relationships(
        self, columns: List[ColumnProfile]
    ) -> List[Dict[str, str]]:
        """Detect potential relationships between tables."""
        relationships = []

        for col in columns:
            if col.semantic_type and col.semantic_type.startswith("reference."):
                ref_type = col.semantic_type.split(".")[1]
                relationships.append(
                    {
                        "field": col.name,
                        "references": ref_type,
                        "confidence": col.confidence,
                    }
                )

        return relationships

    def _calculate_confidence(self, columns: List[ColumnProfile]) -> float:
        """Calculate overall confidence score."""
        if not columns:
            return 0.0

        # Average of column confidences for detected types
        detected_cols = [col for col in columns if col.semantic_type]
        if not detected_cols:
            return 0.3  # Low confidence if no semantic types detected

        avg_confidence = sum(col.confidence for col in detected_cols) / len(
            detected_cols
        )

        # Boost confidence if we detected multiple related columns
        semantic_groups = {}
        for col in detected_cols:
            if col.semantic_type:
                group = col.semantic_type.split(".")[0]
                semantic_groups[group] = semantic_groups.get(group, 0) + 1

        # Bonus for coherent groups
        if any(count >= 2 for count in semantic_groups.values()):
            avg_confidence = min(1.0, avg_confidence * 1.2)

        return avg_confidence

    def _detect_geometry_type(self, gdf) -> Optional[str]:
        """Detect the type of geometry in a GeoDataFrame."""
        if not hasattr(gdf, "geometry"):
            return None

        try:
            geom_types = gdf.geometry.geom_type.unique()
            if len(geom_types) == 1:
                return geom_types[0]
            else:
                return "Mixed"
        except Exception:
            return None
