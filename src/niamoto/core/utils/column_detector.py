"""Smart column detection utilities for auto-configuration."""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple


class ColumnDetector:
    """Detect patterns in column names and data for smart configuration."""

    # Patterns for hierarchy detection
    HIERARCHY_PATTERNS = {
        # Taxonomic hierarchy
        "kingdom": ["kingdom", "regne", "regnum", "tax_kingdom"],
        "phylum": ["phylum", "embranchement", "division", "tax_phylum"],
        "class": ["class", "classe", "tax_class"],
        "order": ["order", "ordre", "ordo", "tax_order"],
        "family": ["family", "famille", "familia", "tax_fam", "tax_family"],
        "genus": ["genus", "genre", "tax_gen", "tax_genus"],
        "species": [
            "species",
            "espece",
            "epithet",
            "sp",
            "tax_sp",
            "tax_species",
            "tax_sp_level",
            "tax_esp",
        ],
        "subspecies": [
            "subspecies",
            "sous-espece",
            "infra",
            "var",
            "variety",
            "tax_infra",
            "tax_infra_level",
        ],
        "rank": ["rank", "rang", "level", "niveau", "tax_rank"],
        "parent": ["parent", "parent_id"],
        # Geographic hierarchy
        "country": ["country", "pays", "nation", "pais"],
        "region": ["region", "province", "state", "etat", "territorio"],
        "locality": [
            "locality",
            "locality_name",
            "site",
            "location",
            "lieu",
            "localite",
            "local",
        ],
        "sublocality": ["sublocality", "subsite", "sublocation", "zone"],
        "plot": [
            "plot",
            "plot_name",
            "parcelle",
            "quadrat",
            "relevé",
            "releve",
            "transect",
        ],
    }

    # Hierarchy type detection: order matters!
    TAXONOMIC_LEVELS = [
        "kingdom",
        "phylum",
        "class",
        "order",
        "family",
        "genus",
        "species",
        "subspecies",
    ]

    GEOGRAPHIC_LEVELS = ["country", "region", "locality", "sublocality", "plot"]

    # Patterns for ID columns
    ID_PATTERNS = [
        r"^id$",
        r"^.*_id$",
        r"^id_.*",
        r"^identifier$",
        r"^code$",
        r"^.*_code$",
    ]

    # Patterns for geometry columns
    GEOMETRY_PATTERNS = [
        "geometry",
        "geom",
        "wkt",
        "geo",
        "geo_pt",
        "geo_point",
        "location",
        "shape",
        "the_geom",
    ]

    # Patterns for name/label columns
    NAME_PATTERNS = [
        "name",
        "nom",
        "label",
        "title",
        "titre",
        "designation",
        "full_name",
        "scientific_name",
        "taxaname",
        "taxon_name",
    ]

    # Patterns for date columns
    DATE_PATTERNS = [
        "date",
        "time",
        "datetime",
        "timestamp",
        "created",
        "updated",
        "modified",
        "observed",
        "collected",
    ]

    @classmethod
    def detect_hierarchy_columns(
        cls, columns: List[str], sample_data: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Detect taxonomic or hierarchical columns.

        Args:
            columns: List of column names
            sample_data: Optional sample data for validation

        Returns:
            Dictionary with detected hierarchy information
        """
        detected_levels = []
        column_mapping = {}

        lower_columns = {col.lower(): col for col in columns}

        # Check for each hierarchy level
        for level, patterns in cls.HIERARCHY_PATTERNS.items():
            for pattern in patterns:
                if pattern in lower_columns:
                    original_col = lower_columns[pattern]
                    detected_levels.append(level)
                    column_mapping[level] = original_col
                    break

        # Determine hierarchy type and order levels accordingly
        hierarchy_type = cls._detect_hierarchy_type(detected_levels)

        # If mixed, filter out minority type to avoid pollution
        if hierarchy_type == "mixed":
            taxonomic_count = sum(
                1 for level in detected_levels if level in cls.TAXONOMIC_LEVELS
            )
            geographic_count = sum(
                1 for level in detected_levels if level in cls.GEOGRAPHIC_LEVELS
            )

            if taxonomic_count >= geographic_count * 2:
                # Strong taxonomic majority - filter out geographic
                detected_levels = [
                    level for level in detected_levels if level in cls.TAXONOMIC_LEVELS
                ]
                hierarchy_type = "taxonomic"
            elif geographic_count >= taxonomic_count * 2:
                # Strong geographic majority - filter out taxonomic
                detected_levels = [
                    level for level in detected_levels if level in cls.GEOGRAPHIC_LEVELS
                ]
                hierarchy_type = "geographic"

        if hierarchy_type == "taxonomic":
            standard_order = cls.TAXONOMIC_LEVELS
        elif hierarchy_type == "geographic":
            standard_order = cls.GEOGRAPHIC_LEVELS
        else:
            # Mixed or unknown - use detected order
            standard_order = []

        ordered_levels = [level for level in standard_order if level in detected_levels]

        # Add any extra levels not in standard order
        extra_levels = [
            level for level in detected_levels if level not in standard_order
        ]
        ordered_levels.extend(extra_levels)

        # Update column_mapping to only include retained levels
        column_mapping = {
            level: col
            for level, col in column_mapping.items()
            if level in ordered_levels
        }

        # If no pattern-based hierarchy detected, try generic cardinality detection
        if len(ordered_levels) == 0 and sample_data:
            generic_hierarchy = cls._detect_generic_hierarchy(columns, sample_data)
            if generic_hierarchy["detected"]:
                ordered_levels = generic_hierarchy["levels"]
                column_mapping = generic_hierarchy["column_mapping"]
                hierarchy_type = "generic"

        # Validate hierarchy using sample data if provided
        is_valid = False
        confidence = 0.0

        if sample_data and len(ordered_levels) >= 2:
            is_valid, confidence = cls._validate_hierarchy(
                sample_data, column_mapping, ordered_levels
            )

        return {
            "detected": len(ordered_levels) > 0,
            "levels": ordered_levels,
            "column_mapping": column_mapping,
            "hierarchy_type": hierarchy_type if len(ordered_levels) > 0 else None,
            "is_valid": is_valid,
            "confidence": confidence,
            "level_count": len(ordered_levels),
        }

    @classmethod
    def _validate_hierarchy(
        cls,
        sample_data: List[Dict[str, Any]],
        column_mapping: Dict[str, str],
        levels: List[str],
    ) -> Tuple[bool, float]:
        """Validate that columns actually form a hierarchy.

        Args:
            sample_data: Sample rows
            column_mapping: Map of level -> column name
            levels: Ordered levels

        Returns:
            Tuple of (is_valid, confidence_score)
        """
        if len(sample_data) < 5:
            return False, 0.5

        # Check that each level has fewer unique values than the next
        unique_counts = []
        for level in levels:
            if level not in column_mapping:
                continue

            col_name = column_mapping[level]
            values = [row.get(col_name) for row in sample_data if row.get(col_name)]

            if not values:
                return False, 0.0

            unique_counts.append((level, len(set(values))))

        # Validate that uniqueness increases down the hierarchy
        valid_hierarchy = True
        for i in range(len(unique_counts) - 1):
            if unique_counts[i][1] > unique_counts[i + 1][1]:
                valid_hierarchy = False
                break

        # Calculate confidence based on hierarchy structure
        confidence = 0.8 if valid_hierarchy else 0.3
        if len(levels) >= 3:
            confidence += 0.1
        if len(levels) >= 4:
            confidence += 0.1

        return valid_hierarchy, min(confidence, 1.0)

    @classmethod
    def detect_id_columns(cls, columns: List[str]) -> List[str]:
        """Detect ID columns.

        Args:
            columns: List of column names

        Returns:
            List of detected ID columns
        """
        id_columns = []

        for col in columns:
            col_lower = col.lower()

            for pattern in cls.ID_PATTERNS:
                if re.match(pattern, col_lower):
                    id_columns.append(col)
                    break

        return id_columns

    @classmethod
    def detect_geometry_columns(cls, columns: List[str]) -> List[str]:
        """Detect geometry/spatial columns.

        Args:
            columns: List of column names

        Returns:
            List of detected geometry columns
        """
        geom_columns = []

        for col in columns:
            col_lower = col.lower()

            for pattern in cls.GEOMETRY_PATTERNS:
                if pattern in col_lower:
                    geom_columns.append(col)
                    break

        return geom_columns

    @classmethod
    def detect_name_columns(cls, columns: List[str]) -> List[str]:
        """Detect name/label columns.

        Args:
            columns: List of column names

        Returns:
            List of detected name columns
        """
        name_columns = []

        for col in columns:
            col_lower = col.lower()

            for pattern in cls.NAME_PATTERNS:
                if pattern in col_lower:
                    name_columns.append(col)
                    break

        return name_columns

    @classmethod
    def detect_date_columns(cls, columns: List[str]) -> List[str]:
        """Detect date/time columns.

        Args:
            columns: List of column names

        Returns:
            List of detected date columns
        """
        date_columns = []

        for col in columns:
            col_lower = col.lower()

            for pattern in cls.DATE_PATTERNS:
                if pattern in col_lower:
                    date_columns.append(col)
                    break

        return date_columns

    @classmethod
    def _detect_hierarchy_type(cls, detected_levels: List[str]) -> str:
        """Determine if hierarchy is taxonomic, geographic, or mixed.

        Args:
            detected_levels: List of detected hierarchy levels

        Returns:
            "taxonomic", "geographic", "mixed", or "unknown"
        """
        if not detected_levels:
            return "unknown"

        taxonomic_count = sum(
            1 for level in detected_levels if level in cls.TAXONOMIC_LEVELS
        )
        geographic_count = sum(
            1 for level in detected_levels if level in cls.GEOGRAPHIC_LEVELS
        )

        if taxonomic_count > 0 and geographic_count == 0:
            return "taxonomic"
        elif geographic_count > 0 and taxonomic_count == 0:
            return "geographic"
        elif taxonomic_count > 0 and geographic_count > 0:
            return "mixed"
        else:
            return "unknown"

    @classmethod
    def _detect_generic_hierarchy(
        cls, columns: List[str], sample_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Detect hierarchy using generic cardinality analysis.

        This method detects potential hierarchies by analyzing unique value counts:
        - Columns with fewer unique values are higher in hierarchy
        - Validates that each level has strictly increasing cardinality

        Args:
            columns: List of column names
            sample_data: Sample data rows

        Returns:
            Dictionary with detected hierarchy info
        """
        if len(sample_data) < 10:
            return {"detected": False, "levels": [], "column_mapping": {}}

        # Analyze cardinality for each column (excluding ID, geometry, numeric columns)
        cardinalities = []

        for col in columns:
            col_lower = col.lower()

            # Skip obvious non-hierarchical columns
            if any(
                skip in col_lower
                for skip in [
                    "id",
                    "geo",
                    "wkt",
                    "lon",
                    "lat",
                    "ddlon",
                    "ddlat",
                    "date",
                    "time",
                ]
            ):
                continue

            # Get values for this column
            values = [row.get(col) for row in sample_data if row.get(col)]
            if not values:
                continue

            # Skip numeric columns
            try:
                float(values[0])
                continue
            except (ValueError, TypeError):
                pass

            unique_count = len(set(values))
            unique_ratio = unique_count / len(values)

            # Only consider columns with reasonable cardinality for hierarchy
            # (not too unique, not too repetitive)
            if 0.1 < unique_ratio < 0.95:
                cardinalities.append((col, unique_count, unique_ratio))

        # Sort by cardinality (ascending)
        cardinalities.sort(key=lambda x: x[1])

        # Build hierarchy if we have at least 2 levels with increasing cardinality
        if len(cardinalities) >= 2:
            # Verify strict increase in cardinality
            valid_hierarchy = True
            for i in range(len(cardinalities) - 1):
                if cardinalities[i][1] >= cardinalities[i + 1][1]:
                    valid_hierarchy = False
                    break

            if valid_hierarchy:
                levels = [f"level_{i + 1}" for i in range(len(cardinalities))]
                column_mapping = {
                    f"level_{i + 1}": cardinalities[i][0]
                    for i in range(len(cardinalities))
                }

                return {
                    "detected": True,
                    "levels": levels,
                    "column_mapping": column_mapping,
                }

        return {"detected": False, "levels": [], "column_mapping": {}}

    @classmethod
    def detect_relationships(
        cls,
        source_columns: List[str],
        target_columns: List[str],
        source_sample: Optional[List[Dict[str, Any]]] = None,
        target_sample: Optional[List[Dict[str, Any]]] = None,
        source_entity_name: Optional[str] = None,
        target_entity_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Detect potential foreign key relationships between two datasets.

        Args:
            source_columns: Columns from source dataset
            target_columns: Columns from target dataset
            source_sample: Sample data from source
            target_sample: Sample data from target
            source_entity_name: Name of source entity (e.g., "occurrences")
            target_entity_name: Name of target entity (e.g., "plots")

        Returns:
            List of detected relationships
        """
        relationships = []

        # Get ID columns from target (potential FK targets)
        target_id_columns = cls.detect_id_columns(target_columns)

        # Also consider name columns as potential targets
        target_name_columns = cls.detect_name_columns(target_columns)

        for source_col in source_columns:
            source_col_lower = source_col.lower()

            # Strategy 1: Exact or partial name match (but ONLY with ID/name columns for high selectivity)
            for target_col in target_id_columns + target_name_columns:
                target_col_lower = target_col.lower()

                # Direct exact match
                if source_col_lower == target_col_lower:
                    confidence = cls._calculate_relationship_confidence(
                        source_col, target_col, source_sample, target_sample
                    )

                    if confidence > 0.3:  # Threshold for suggesting relationship
                        relationships.append(
                            {
                                "source_field": source_col,
                                "target_field": target_col,
                                "confidence": confidence,
                                "match_type": "exact_match",
                            }
                        )
                        continue

                # Partial match only for ID columns (to avoid false positives)
                if target_col in target_id_columns:
                    if (
                        source_col_lower in target_col_lower
                        or target_col_lower in source_col_lower
                    ):
                        confidence = cls._calculate_relationship_confidence(
                            source_col, target_col, source_sample, target_sample
                        )

                        if confidence > 0.5:  # Higher threshold for partial matches
                            relationships.append(
                                {
                                    "source_field": source_col,
                                    "target_field": target_col,
                                    "confidence": confidence,
                                    "match_type": "name_similarity",
                                }
                            )
                            continue

            # Strategy 2: Semantic context-aware matching
            # Example: "plot_name" in source + target entity is "plots" → check "plot" or "plot_name" columns
            if target_entity_name:
                semantic_match = cls._detect_semantic_relationship(
                    source_col,
                    target_columns,
                    target_entity_name,
                    source_sample,
                    target_sample,
                )
                if semantic_match:
                    relationships.append(semantic_match)

        # Remove duplicates (same source_field + target_field)
        seen = set()
        unique_relationships = []
        for rel in relationships:
            key = (rel["source_field"], rel["target_field"])
            if key not in seen:
                seen.add(key)
                unique_relationships.append(rel)

        return unique_relationships

    @classmethod
    def _detect_semantic_relationship(
        cls,
        source_col: str,
        target_columns: List[str],
        target_entity_name: str,
        source_sample: Optional[List[Dict[str, Any]]],
        target_sample: Optional[List[Dict[str, Any]]],
    ) -> Optional[Dict[str, Any]]:
        """Detect relationships using semantic context.

        Examples:
        - source_col="plot_name" + target_entity="plots" → target_col="plot" or "plot_name"
        - source_col="taxon_id" + target_entity="taxons" → target_col="id" or "taxon_id"

        Args:
            source_col: Column from source dataset
            target_columns: Columns from target dataset
            target_entity_name: Name of target entity
            source_sample: Sample data from source
            target_sample: Sample data from target

        Returns:
            Relationship dict if found, None otherwise
        """
        source_col_lower = source_col.lower()
        target_entity_lower = target_entity_name.lower().rstrip(
            "s"
        )  # Remove plural 's'

        # Extract semantic keyword from source column
        # E.g., "plot_name" → "plot", "id_taxon" → "taxon", "taxon_id" → "taxon"
        semantic_keywords = []

        # Common patterns
        if "_" in source_col_lower:
            parts = source_col_lower.split("_")
            # Try removing common suffixes
            for i, part in enumerate(parts):
                if part not in ["id", "name", "code", "ref", "field"]:
                    semantic_keywords.append(part)

        # Check if any keyword relates to target entity
        for keyword in semantic_keywords:
            # Check similarity: keyword matches target entity (with some tolerance)
            if (
                keyword == target_entity_lower
                or keyword in target_entity_lower
                or target_entity_lower in keyword
            ):
                # Now find matching column in target
                # Priority: exact match > name column > id column
                candidates = []

                for target_col in target_columns:
                    target_col_lower = target_col.lower()

                    # Priority scoring
                    score = 0

                    # Exact match with source column
                    if target_col_lower == source_col_lower:
                        score = 100
                    # Match with keyword
                    elif keyword in target_col_lower:
                        score = 80
                    # Match with entity name
                    elif target_entity_lower in target_col_lower:
                        score = 60
                    # Just "name" or "id"
                    elif target_col_lower in [
                        "name",
                        "id",
                        f"{keyword}_name",
                        f"{keyword}_id",
                    ]:
                        score = 50

                    if score > 0:
                        candidates.append((target_col, score))

                if candidates:
                    # Take highest scoring candidate
                    candidates.sort(key=lambda x: x[1], reverse=True)
                    best_target_col = candidates[0][0]

                    # Validate with data if available
                    confidence = cls._calculate_relationship_confidence(
                        source_col, best_target_col, source_sample, target_sample
                    )

                    if confidence > 0.3:
                        return {
                            "source_field": source_col,
                            "target_field": best_target_col,
                            "confidence": confidence,
                            "match_type": "semantic_context",
                        }

        return None

    @classmethod
    def _calculate_relationship_confidence(
        cls,
        source_col: str,
        target_col: str,
        source_sample: Optional[List[Dict[str, Any]]],
        target_sample: Optional[List[Dict[str, Any]]],
    ) -> float:
        """Calculate confidence score for a relationship.

        Args:
            source_col: Source column name
            target_col: Target column name
            source_sample: Sample data from source
            target_sample: Sample data from target

        Returns:
            Confidence score 0-1
        """
        confidence = 0.5  # Base confidence from name matching

        if source_sample and target_sample:
            # Extract values
            source_values = {
                row.get(source_col) for row in source_sample if row.get(source_col)
            }
            target_values = {
                row.get(target_col) for row in target_sample if row.get(target_col)
            }

            if source_values and target_values:
                # Check overlap
                overlap = source_values & target_values
                overlap_ratio = len(overlap) / len(source_values)

                # Increase confidence based on overlap
                if overlap_ratio > 0.8:
                    confidence = 0.95
                elif overlap_ratio > 0.5:
                    confidence = 0.8
                elif overlap_ratio > 0.2:
                    confidence = 0.6

        return confidence

    @classmethod
    def analyze_file_columns(
        cls, columns: List[str], sample_data: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Comprehensive analysis of file columns.

        Args:
            columns: List of column names
            sample_data: Optional sample data

        Returns:
            Dictionary with all detected patterns
        """
        result = {
            "columns": columns,
            "column_count": len(columns),
        }

        # Detect patterns
        result["hierarchy"] = cls.detect_hierarchy_columns(columns, sample_data)
        result["id_columns"] = cls.detect_id_columns(columns)
        result["geometry_columns"] = cls.detect_geometry_columns(columns)
        result["name_columns"] = cls.detect_name_columns(columns)
        result["date_columns"] = cls.detect_date_columns(columns)

        # Determine likely entity type with improved logic
        has_hierarchy = (
            result["hierarchy"]["detected"] and result["hierarchy"]["level_count"] >= 2
        )
        has_geometry = len(result["geometry_columns"]) > 0
        has_many_columns = len(columns) > 10
        has_observation_columns = any(
            col.lower() in ["dbh", "height", "observed", "measurement", "value"]
            for col in columns
        )

        if (
            has_hierarchy
            and has_geometry
            and (has_many_columns or has_observation_columns)
        ):
            # File with hierarchy + geometry + many columns = dataset with hierarchy columns
            # The hierarchy should be extracted as a separate derived reference
            result["suggested_entity_type"] = "dataset"
            result["suggested_connector_type"] = "file"
            result["confidence"] = 0.9
            result["extract_hierarchy_as_reference"] = (
                True  # Flag to create derived reference
            )
        elif has_hierarchy and not has_geometry and not has_many_columns:
            # Pure hierarchy file (taxonomy, classification)
            result["suggested_entity_type"] = "hierarchical_reference"
            result["suggested_connector_type"] = "file"
            result["confidence"] = result["hierarchy"]["confidence"]
            result["extract_hierarchy_as_reference"] = False
        elif has_geometry:
            # Spatial data = dataset
            result["suggested_entity_type"] = "dataset"
            result["suggested_connector_type"] = "file"
            result["confidence"] = 0.8
            result["extract_hierarchy_as_reference"] = False
        elif len(result["id_columns"]) > 0 and len(columns) < 10:
            # Small table with ID = reference
            result["suggested_entity_type"] = "reference"
            result["suggested_connector_type"] = "file"
            result["confidence"] = 0.7
            result["extract_hierarchy_as_reference"] = False
        else:
            # Default to dataset
            result["suggested_entity_type"] = "dataset"
            result["suggested_connector_type"] = "file"
            result["confidence"] = 0.5
            result["extract_hierarchy_as_reference"] = False

        return result


class GeoPackageAnalyzer:
    """Analyzer for GeoPackage files with smart classification."""

    @classmethod
    def analyze_gpkg(cls, filepath: Path) -> Dict[str, Any]:
        """Analyze a GeoPackage file comprehensively.

        Args:
            filepath: Path to GPKG file

        Returns:
            Dictionary with analysis results including classification
        """
        import fiona
        import geopandas as gpd

        if not filepath.exists():
            raise FileNotFoundError(f"GPKG file not found: {filepath}")

        try:
            # List all layers in the GPKG
            layers = fiona.listlayers(str(filepath))

            if not layers:
                return {
                    "error": "No layers found in GeoPackage",
                    "classification": "unknown",
                }

            # Analyze first layer (most GPs have single layer)
            # For multi-layer support, we'd iterate
            layer_name = layers[0]

            # Load with geopandas
            gdf = gpd.read_file(filepath, layer=layer_name)

            # Basic info
            geom_types = list(gdf.geometry.geom_type.unique())
            row_count = len(gdf)
            columns = list(gdf.columns)
            columns_no_geom = [c for c in columns if c != "geometry"]

            # Extract attribute info
            attributes = {}
            name_field_candidates = []

            for col in columns_no_geom:
                dtype = str(gdf[col].dtype)
                unique_count = gdf[col].nunique()
                unique_ratio = unique_count / row_count if row_count > 0 else 0

                attributes[col] = {
                    "type": dtype,
                    "unique_count": unique_count,
                    "unique_ratio": round(unique_ratio, 2),
                    "sample_values": list(gdf[col].dropna().head(3).astype(str)),
                }

                # Candidate for name_field: string type with high uniqueness
                if dtype == "object" and unique_ratio > 0.5:
                    name_field_candidates.append(col)

            # Classify as shapes or layers
            classification, confidence, reason = cls._classify_gpkg(
                geom_types, row_count, attributes, name_field_candidates
            )

            return {
                "filename": filepath.name,
                "filepath": str(filepath),
                "layers": layers,
                "layer_analyzed": layer_name,
                "row_count": row_count,
                "columns": columns_no_geom,
                "column_count": len(columns_no_geom),
                "geometry_types": geom_types,
                "crs": str(gdf.crs) if gdf.crs else None,
                "bounds": gdf.total_bounds.tolist() if not gdf.empty else None,
                "attributes": attributes,
                "name_field_candidates": name_field_candidates,
                "classification": classification,
                "confidence": confidence,
                "classification_reason": reason,
            }

        except Exception as e:
            return {
                "error": f"Failed to analyze GPKG: {str(e)}",
                "filename": filepath.name,
                "classification": "unknown",
            }

    @classmethod
    def _classify_gpkg(
        cls,
        geom_types: List[str],
        row_count: int,
        attributes: Dict[str, Any],
        name_field_candidates: List[str],
    ) -> tuple[str, float, str]:
        """Classify GPKG as shapes (reference) or layers (metadata).

        Logic:
        - shapes: Polygon/MultiPolygon with distinct name field (e.g., provinces, substrates)
        - layers: Everything else (raster-like vectors, analysis layers)

        Returns:
            (classification, confidence, reason)
        """
        is_polygon = any(g in ["Polygon", "MultiPolygon"] for g in geom_types)
        has_name_field = len(name_field_candidates) > 0
        reasonable_count = 1 < row_count < 10000  # Not too few, not too many

        if is_polygon and has_name_field and reasonable_count:
            return (
                "shapes",
                0.9,
                f"Polygon geometry with name field(s): {', '.join(name_field_candidates[:2])}",
            )
        elif is_polygon and has_name_field:
            return (
                "shapes",
                0.7,
                f"Polygon geometry with name field but unusual count: {row_count}",
            )
        elif is_polygon and not has_name_field:
            return (
                "layers",
                0.6,
                "Polygon geometry but no distinct name field (analysis layer?)",
            )
        else:
            return (
                "layers",
                0.8,
                f"Geometry type {geom_types[0] if geom_types else 'unknown'} suggests metadata layer",
            )


class SpatialMatcher:
    """Match spatial data between CSV and GPKG files."""

    @classmethod
    def check_intersection(
        cls,
        csv_path: Path,
        geo_column: str,
        gpkg_path: Path,
        layer: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Check spatial intersection between CSV points and GPKG polygons.

        Args:
            csv_path: Path to CSV file with geometry column
            geo_column: Name of geometry column in CSV (WKT format)
            gpkg_path: Path to GPKG file
            layer: Optional layer name (uses first if not specified)

        Returns:
            Dictionary with intersection statistics and confidence
        """
        import pandas as pd
        import geopandas as gpd
        from shapely import wkt
        from shapely.errors import ShapelyError

        try:
            # Load CSV and parse WKT geometries
            df = pd.read_csv(csv_path, low_memory=False)

            if geo_column not in df.columns:
                return {
                    "error": f"Column {geo_column} not found in CSV",
                    "has_intersection": False,
                }

            # Parse WKT to shapely geometries
            geometries = []
            valid_indices = []

            for idx, row in df.iterrows():
                wkt_str = row[geo_column]
                if pd.isna(wkt_str):
                    continue

                try:
                    geom = wkt.loads(str(wkt_str))
                    if geom and geom.is_valid:
                        geometries.append(geom)
                        valid_indices.append(idx)
                except (ShapelyError, Exception):
                    continue

            if not geometries:
                return {
                    "error": "No valid geometries found in CSV",
                    "has_intersection": False,
                }

            # Create GeoDataFrame from CSV
            csv_gdf = gpd.GeoDataFrame(
                df.loc[valid_indices], geometry=geometries, crs="EPSG:4326"
            )

            # Load GPKG
            gpkg_gdf = gpd.read_file(gpkg_path, layer=layer)

            # Reproject if CRS mismatch
            if csv_gdf.crs != gpkg_gdf.crs:
                csv_gdf = csv_gdf.to_crs(gpkg_gdf.crs)

            # Perform spatial join (intersection)
            joined = gpd.sjoin(csv_gdf, gpkg_gdf, how="left", predicate="intersects")

            # Calculate statistics
            total_points = len(csv_gdf)
            matched_points = joined["index_right"].notna().sum()
            coverage_percent = (
                (matched_points / total_points * 100) if total_points > 0 else 0
            )

            # Confidence based on coverage
            if coverage_percent >= 80:
                confidence = 0.9
            elif coverage_percent >= 60:
                confidence = 0.7
            elif coverage_percent >= 40:
                confidence = 0.5
            else:
                confidence = 0.3

            return {
                "has_intersection": matched_points > 0,
                "total_points": int(total_points),
                "matched_points": int(matched_points),
                "coverage_percent": round(coverage_percent, 1),
                "confidence": confidence,
                "csv_crs": str(csv_gdf.crs),
                "gpkg_crs": str(gpkg_gdf.crs),
                "gpkg_feature_count": len(gpkg_gdf),
            }

        except Exception as e:
            return {
                "error": f"Spatial matching failed: {str(e)}",
                "has_intersection": False,
            }
