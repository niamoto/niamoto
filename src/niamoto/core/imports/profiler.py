"""
Data profiler for automatic dataset analysis and semantic detection.
This module analyzes data files to detect their structure and suggest entity types.
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

# Import ML detector for value-based detection
try:
    from niamoto.core.imports.ml_detector import MLColumnDetector

    HAS_ML_DETECTOR = True
except ImportError:
    HAS_ML_DETECTOR = False
    logging.debug("ML detector not available, falling back to pattern-based detection")

logger = logging.getLogger(__name__)


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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "dtype": self.dtype,
            "semantic_type": self.semantic_type,
            "unique_ratio": round(self.unique_ratio, 4),
            "null_ratio": round(self.null_ratio, 4),
            "confidence": round(self.confidence, 2),
            "sample_values": self.sample_values[:5],  # Limit samples
        }


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
    """Analyzes datasets to detect structure and semantics."""

    # Simple patterns for Phase 1 - will be enhanced in Phase 2
    TAXONOMY_PATTERNS = {
        "family": ["family", "famille", "fam"],
        "genus": ["genus", "genre", "gen"],
        "species": ["species", "espece", "esp", "sp"],
        "rank": ["rank", "rang", "rank_name", "level"],
        "scientific_name": [
            "taxaname",
            "scientific_name",
            "nom_scientifique",
            "taxonref",
        ],
        "taxon_id": ["id_taxonref", "taxon_id", "id_taxon"],
    }

    SPATIAL_PATTERNS = {
        "geometry": ["geometry", "geom", "shape", "polygon", "geo_pt"],
        "latitude": ["lat", "latitude", "y", "lat_y"],
        "longitude": ["lon", "longitude", "long", "x", "lon_x"],
        "coordinates": ["coordinates", "coords", "xy", "location"],
        "plot": ["plot", "site", "parcelle", "plot_name"],
        "locality": ["locality", "localite", "lieu", "place"],
    }

    IDENTIFIER_PATTERNS = {
        "id": ["id", "identifier", "code"],
        "reference": ["_ref", "_id", "_code", "_num"],
    }

    def __init__(self, ml_detector: Optional[MLColumnDetector] = None):
        """Initialize the profiler.

        Args:
            ml_detector: Optional ML detector instance for value-based detection.
                        If not provided, will try to load default model.
        """
        self.ml_detector = ml_detector

        # Try to load default ML detector if available and not provided
        if self.ml_detector is None and HAS_ML_DETECTOR:
            try:
                self.ml_detector = MLColumnDetector.load_or_none()
                if self.ml_detector:
                    logger.info("Loaded ML detector for value-based column detection")
            except Exception as e:
                logger.debug(f"Could not load default ML detector: {e}")

    def profile(self, file_path: Path) -> DatasetProfile:
        """Generate complete profile of a dataset."""
        # Load data
        data = self._load_data(file_path)

        if data is None:
            raise ValueError(f"Could not load data from {file_path}")

        # Store file path in data attributes for detection
        data.attrs["file_path"] = file_path

        # Profile columns
        columns = []
        for col_name in data.columns:
            col_profile = self._profile_column(data[col_name], col_name)
            columns.append(col_profile)

        # Detect dataset type based on column profiles
        dataset_type = self._detect_dataset_type(columns, data)

        # Suggest entity name
        suggested_name = self._suggest_entity_name(file_path, dataset_type)

        # Detect relationships
        relationships = self._detect_relationships(columns)

        # Calculate overall confidence
        confidence = self._calculate_confidence(columns)

        # Check for geometry if geopandas
        geometry_type = None
        if hasattr(data, "geometry"):
            geometry_type = self._detect_geometry_type(data)

        return DatasetProfile(
            file_path=file_path,
            record_count=len(data),
            columns=columns,
            detected_type=dataset_type,
            suggested_name=suggested_name,
            relationships=relationships,
            geometry_type=geometry_type,
            confidence=confidence,
        )

    def _load_data(self, file_path: Path) -> Optional[pd.DataFrame]:
        """Load data from various file formats."""
        file_str = str(file_path)

        try:
            if file_path.suffix.lower() == ".csv":
                return pd.read_csv(file_str)
            elif file_path.suffix.lower() in [".geojson", ".json"]:
                if HAS_GEOPANDAS:
                    return gpd.read_file(file_str)
                else:
                    return pd.read_json(file_str)
            elif file_path.suffix.lower() in [".shp", ".gpkg"]:
                if HAS_GEOPANDAS:
                    return gpd.read_file(file_str)
            elif file_path.suffix.lower() in [".xlsx", ".xls"]:
                return pd.read_excel(file_str)
        except Exception as e:
            print(f"Error loading {file_path}: {e}")

        return None

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

        # Detect semantic type
        semantic_type, confidence = self._detect_semantic_type(col_name, series)
        profile.semantic_type = semantic_type
        profile.confidence = confidence

        return profile

    def _detect_semantic_type(
        self, col_name: str, series: pd.Series
    ) -> Tuple[Optional[str], float]:
        """Detect the semantic type of a column.

        First tries ML-based detection on column values if available,
        then falls back to pattern-based detection on column names.
        """
        # Try ML detection first if available (value-based)
        if self.ml_detector and self.ml_detector.is_trained:
            try:
                ml_type, ml_confidence = self.ml_detector.predict(series)

                # Map ML types to semantic types
                ml_to_semantic_map = {
                    "diameter": "measurement.diameter",
                    "height": "measurement.height",
                    "leaf_area": "measurement.leaf_area",
                    "wood_density": "measurement.wood_density",
                    "species_name": "taxonomy.species",
                    "family_name": "taxonomy.family",
                    "genus_name": "taxonomy.genus",
                    "location": "location.name",
                    "latitude": "location.latitude",
                    "longitude": "location.longitude",
                    "date": "temporal.date",
                    "count": "statistic.count",
                    "identifier": "identifier",
                    "other": None,
                }

                semantic_type = ml_to_semantic_map.get(ml_type)

                # Accept ML prediction if confidence is high enough
                if semantic_type and ml_confidence >= 0.6:
                    logger.debug(
                        f"ML detected {col_name} as {ml_type} (confidence: {ml_confidence:.2f})"
                    )
                    return semantic_type, ml_confidence

            except Exception as e:
                logger.debug(f"ML detection failed for {col_name}: {e}")

        # Fallback to pattern-based detection (name-based)
        col_lower = col_name.lower()

        # Check taxonomy patterns
        for tax_type, patterns in self.TAXONOMY_PATTERNS.items():
            for pattern in patterns:
                if pattern in col_lower:
                    return f"taxonomy.{tax_type}", 0.8

        # Check spatial patterns
        for spatial_type, patterns in self.SPATIAL_PATTERNS.items():
            for pattern in patterns:
                if pattern in col_lower:
                    # Special handling for coordinates
                    if spatial_type in ["latitude", "longitude"]:
                        # Verify it contains numeric coordinates
                        if pd.api.types.is_numeric_dtype(series):
                            return f"location.{spatial_type}", 0.9
                    elif spatial_type == "geometry":
                        # Check if it looks like WKT
                        sample = series.dropna().head(5).astype(str)
                        if sample.str.contains("POINT|POLYGON|LINESTRING").any():
                            return "geometry", 0.95
                    else:
                        return f"location.{spatial_type}", 0.7

        # Check identifier patterns
        if col_lower.startswith("id") or col_lower.endswith("_id"):
            # Check if it's likely a foreign key
            if "taxon" in col_lower or "taxonref" in col_lower:
                return "reference.taxon", 0.8
            elif "plot" in col_lower or "site" in col_lower:
                return "reference.plot", 0.8
            else:
                return "identifier", 0.7

        # Check for name references (like plot_name)
        if "plot_name" in col_lower:
            return "reference.plot", 0.7

        # Check for numeric measures
        if pd.api.types.is_numeric_dtype(series):
            # Common ecological measurements
            if any(
                term in col_lower for term in ["dbh", "height", "elevation", "rainfall"]
            ):
                return "measurement", 0.8
            elif any(term in col_lower for term in ["count", "nb_", "total_"]):
                return "statistic", 0.7

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
