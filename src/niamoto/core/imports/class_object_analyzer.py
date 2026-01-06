"""
Class Object Analyzer for Pre-calculated CSV Files

Analyzes CSV files containing pre-calculated statistics in the class_object format,
detects the structure and suggests appropriate transformer plugins.

Expected CSV format:
- class_object: Type of classification (e.g., "top10_family", "cover_forest")
- class_name: Category or axis value (e.g., "Sapindaceae", "100", "Forêt")
- class_value: Numeric value

The analyzer auto-detects CSV delimiter (comma or semicolon).
"""

import csv
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import duckdb


class ClassObjectCategory(str, Enum):
    """Fine-grained categorization of class_object types."""

    SCALAR = "scalar"  # Empty or single class_name (elevation_max, forest_area_ha)
    BINARY = "binary"  # Exactly 2 class_names (cover_forest: Forêt/Hors-forêt)
    TERNARY = (
        "ternary"  # Exactly 3 class_names (cover_foresttype: coeur/mature/secondaire)
    )
    MULTI_CATEGORY = "multi_category"  # 4-15 categorical class_names
    NUMERIC_BINS = "numeric_bins"  # Numeric class_names (elevation: 100, 200, 300...)
    LARGE_CATEGORY = "large_category"  # >15 categorical (top families, species)


# Generic binary mapping patterns (language-agnostic)
# Only truly universal patterns - domain-specific mappings should be configured by users
BINARY_MAPPING_PATTERNS = {
    # Boolean-like patterns
    "Oui": "positive",
    "Non": "negative",
    "Yes": "positive",
    "No": "negative",
    "True": "positive",
    "False": "negative",
    "Vrai": "positive",
    "Faux": "negative",
    "1": "positive",
    "0": "negative",
}


@dataclass
class ClassObjectStats:
    """Statistics for a single class_object type."""

    name: str
    cardinality: int  # Number of distinct class_names
    class_names: list[str] = field(default_factory=list)
    value_type: str = "categorical"  # "numeric" or "categorical"
    sample_values: list[float] = field(default_factory=list)
    suggested_plugin: Optional[str] = None
    confidence: float = 0.0
    # New fields for enhanced analysis
    category: ClassObjectCategory = ClassObjectCategory.SCALAR
    auto_config: dict[str, Any] = field(default_factory=dict)
    mapping_hints: dict[str, str] = field(default_factory=dict)
    related_class_objects: list[str] = field(default_factory=list)
    pattern_group: Optional[str] = None  # e.g., "cover_*", "forest_*_elevation"


@dataclass
class ClassObjectAnalysis:
    """Complete analysis of a class_object CSV file."""

    path: str
    delimiter: str
    row_count: int
    entity_column: Optional[str]
    entity_count: int
    columns: list[str]
    class_objects: list[ClassObjectStats]
    is_valid: bool
    validation_errors: list[str]
    # New field for grouping suggestions
    pattern_groups: dict[str, list[str]] = field(default_factory=dict)


class ClassObjectAnalyzer:
    """Analyzes pre-calculated CSV files and detects applicable plugins."""

    REQUIRED_COLUMNS = {"class_object", "class_name", "class_value"}
    ENTITY_COLUMN_CANDIDATES = [
        "plot_id",
        "shape_id",
        "taxon_id",
        "entity_id",
        "id",
    ]

    def __init__(self, csv_path: Path):
        self.csv_path = csv_path

    def detect_delimiter(self) -> str:
        """Auto-detect CSV delimiter (comma or semicolon)."""
        with open(self.csv_path, "r", encoding="utf-8") as f:
            first_line = f.readline()
            # Count occurrences of each delimiter
            comma_count = first_line.count(",")
            semicolon_count = first_line.count(";")
            return ";" if semicolon_count > comma_count else ","

    def analyze(self) -> ClassObjectAnalysis:
        """
        Analyze the CSV file and return complete analysis.

        Returns:
            ClassObjectAnalysis with structure info, class_objects stats,
            and suggested plugins for each class_object type.
        """
        errors: list[str] = []

        # Detect delimiter
        delimiter = self.detect_delimiter()

        # Read header to get columns
        with open(self.csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter=delimiter)
            columns = [c.strip().lower() for c in next(reader)]

        # Validate required columns
        missing = self.REQUIRED_COLUMNS - set(columns)
        if missing:
            errors.append(f"Colonnes requises manquantes: {', '.join(missing)}")

        # Find entity column
        entity_column = None
        for candidate in self.ENTITY_COLUMN_CANDIDATES:
            if candidate in columns:
                entity_column = candidate
                break

        if not entity_column:
            errors.append(
                f"Colonne d'entité manquante. Attendue: {', '.join(self.ENTITY_COLUMN_CANDIDATES)}"
            )

        # If validation failed, return early
        if errors:
            return ClassObjectAnalysis(
                path=str(self.csv_path),
                delimiter=delimiter,
                row_count=0,
                entity_column=entity_column,
                entity_count=0,
                columns=columns,
                class_objects=[],
                is_valid=False,
                validation_errors=errors,
            )

        # Use DuckDB for efficient analysis
        conn = duckdb.connect(":memory:")

        try:
            # Load CSV
            conn.execute(
                f"""
                CREATE TABLE data AS
                SELECT * FROM read_csv_auto(
                    '{self.csv_path}',
                    delim='{delimiter}',
                    header=true
                )
            """
            )

            # Get row count
            row_count = conn.execute("SELECT COUNT(*) FROM data").fetchone()[0]

            # Get entity count
            entity_count = conn.execute(
                f'SELECT COUNT(DISTINCT "{entity_column}") FROM data'
            ).fetchone()[0]

            # Validate class_value is numeric
            try:
                conn.execute(
                    "SELECT CAST(class_value AS DOUBLE) FROM data WHERE class_value IS NOT NULL LIMIT 1"
                )
            except Exception:
                errors.append(
                    "La colonne class_value doit contenir des valeurs numériques"
                )
                return ClassObjectAnalysis(
                    path=str(self.csv_path),
                    delimiter=delimiter,
                    row_count=row_count,
                    entity_column=entity_column,
                    entity_count=entity_count,
                    columns=columns,
                    class_objects=[],
                    is_valid=False,
                    validation_errors=errors,
                )

            # Analyze each class_object
            class_objects_stats = []
            class_object_names = conn.execute(
                "SELECT DISTINCT class_object FROM data ORDER BY class_object"
            ).fetchall()
            all_names = [name for (name,) in class_object_names]

            for class_object_name in all_names:
                stats = self._analyze_class_object(conn, class_object_name, all_names)
                class_objects_stats.append(stats)

            # Detect pattern groups for related class_objects
            pattern_groups = self._detect_pattern_groups(all_names)

            # Update related_class_objects based on pattern groups
            for stats in class_objects_stats:
                if stats.pattern_group and stats.pattern_group in pattern_groups:
                    stats.related_class_objects = [
                        name
                        for name in pattern_groups[stats.pattern_group]
                        if name != stats.name
                    ]

            return ClassObjectAnalysis(
                path=str(self.csv_path),
                delimiter=delimiter,
                row_count=row_count,
                entity_column=entity_column,
                entity_count=entity_count,
                columns=columns,
                class_objects=class_objects_stats,
                is_valid=True,
                validation_errors=[],
                pattern_groups=pattern_groups,
            )

        finally:
            conn.close()

    def _analyze_class_object(
        self,
        conn: duckdb.DuckDBPyConnection,
        class_object_name: str,
        all_class_objects: list[str],
    ) -> ClassObjectStats:
        """Analyze a single class_object type."""
        # Get distinct class_names
        class_names_result = conn.execute(
            """
            SELECT DISTINCT class_name
            FROM data
            WHERE class_object = ?
            ORDER BY class_name
        """,
            [class_object_name],
        ).fetchall()
        class_names = [
            r[0] for r in class_names_result if r[0] is not None and r[0] != ""
        ]

        # Determine if class_names are numeric
        value_type = self._detect_value_type(class_names)

        # Get sample values
        sample_values = conn.execute(
            """
            SELECT CAST(class_value AS DOUBLE)
            FROM data
            WHERE class_object = ?
            LIMIT 5
        """,
            [class_object_name],
        ).fetchall()
        sample_values = [r[0] for r in sample_values if r[0] is not None]

        # Determine category
        category = self._determine_category(len(class_names), value_type)

        # Suggest plugin and generate auto_config
        plugin, confidence = self._suggest_plugin(
            len(class_names), value_type, class_names
        )
        auto_config = self._generate_auto_config(
            plugin, class_object_name, class_names, value_type
        )

        # Generate mapping hints for binary patterns
        mapping_hints = self._generate_mapping_hints(class_names)

        # Detect pattern group
        pattern_group = self._detect_pattern_group(class_object_name, all_class_objects)

        return ClassObjectStats(
            name=class_object_name,
            cardinality=len(class_names),
            class_names=class_names[:10],  # Limit to first 10 for display
            value_type=value_type,
            sample_values=sample_values,
            suggested_plugin=plugin,
            confidence=confidence,
            category=category,
            auto_config=auto_config,
            mapping_hints=mapping_hints,
            pattern_group=pattern_group,
        )

    def _detect_value_type(self, class_names: list[str]) -> str:
        """Detect if class_names are numeric or categorical."""
        if not class_names:
            return "categorical"

        numeric_count = 0
        for name in class_names:
            if name is None or name == "":
                continue
            try:
                float(name)
                numeric_count += 1
            except (ValueError, TypeError):
                pass

        # If more than 80% are numeric, consider it numeric
        threshold = 0.8
        return (
            "numeric"
            if (numeric_count / len(class_names)) >= threshold
            else "categorical"
        )

    def _suggest_plugin(
        self, cardinality: int, value_type: str, class_names: list[str]
    ) -> tuple[str, float]:
        """
        Suggest the best class_object plugin based on data characteristics.

        Logic:
        - cardinality == 0 or 1 → field_aggregator (single scalar value)
        - cardinality == 2 → binary_aggregator (binary ratio like forest/non-forest)
        - cardinality 3-5 && categorical → series_extractor (small categorical, donut-friendly)
        - numeric class_names → series_extractor (numeric distribution by elevation, etc.)
        - cardinality > 5 && categorical → series_extractor (top10_family, etc.)

        Note: We use series_extractor for all multi-value data because it provides
        consistent output format (tops/counts) that works with bar_plot widgets.
        """
        # No class_name (scalar metric with empty class_name like elevation_max)
        if cardinality == 0:
            return "class_object_field_aggregator", 0.95

        # Single value (scalar metric)
        if cardinality == 1:
            return "class_object_field_aggregator", 0.95

        # Binary (exactly 2 categories)
        if cardinality == 2:
            return "class_object_binary_aggregator", 0.95

        # Numeric series (elevation distributions, etc.)
        if value_type == "numeric":
            return "class_object_series_extractor", 0.90

        # Small categorical set (3-5 categories, good for donut charts)
        if cardinality <= 5:
            return "class_object_series_extractor", 0.90

        # Medium categorical set (6-15 items)
        if cardinality <= 15:
            return "class_object_series_extractor", 0.85

        # Large categorical (like top10_family/species with >15 items)
        return "class_object_series_extractor", 0.80

    def _determine_category(
        self, cardinality: int, value_type: str
    ) -> ClassObjectCategory:
        """Determine the fine-grained category of a class_object."""
        if cardinality <= 1:
            return ClassObjectCategory.SCALAR
        if cardinality == 2:
            return ClassObjectCategory.BINARY
        if cardinality == 3:
            return ClassObjectCategory.TERNARY
        if value_type == "numeric":
            return ClassObjectCategory.NUMERIC_BINS
        if cardinality <= 15:
            return ClassObjectCategory.MULTI_CATEGORY
        return ClassObjectCategory.LARGE_CATEGORY

    def _generate_auto_config(
        self,
        plugin: str,
        class_object_name: str,
        class_names: list[str],
        value_type: str,
    ) -> dict[str, Any]:
        """Generate auto-configuration for the suggested plugin."""
        if plugin == "class_object_field_aggregator":
            return {
                "source": "shape_stats",  # Will be replaced by actual source name
                "fields": [
                    {"class_object": class_object_name, "target": class_object_name}
                ],
            }

        if plugin in ("series_extractor", "class_object_series_extractor"):
            # Use tops/counts output names for compatibility with bar_plot widget
            # For categorical data: don't sort (preserve value-based order from CSV)
            # For numeric data: sort by class_name (e.g., elevation bins)
            is_numeric = value_type == "numeric"
            return {
                "source": "shape_stats",
                "class_object": class_object_name,
                "size_field": {
                    "input": "class_name",
                    "output": "tops",
                    "numeric": is_numeric,
                    "sort": is_numeric,  # Sort only for numeric bins
                },
                "value_field": {
                    "input": "class_value",
                    "output": "counts",
                    "numeric": True,
                },
            }

        if plugin in ("categories_extractor", "class_object_categories_extractor"):
            return {
                "source": "shape_stats",
                "class_object": class_object_name,
                "categories_order": class_names,
            }

        if plugin in ("binary_aggregator", "class_object_binary_aggregator"):
            # Generate mapping from class_names to normalized keys
            mapping = self._generate_mapping_hints(class_names)
            classes = list(mapping.values()) if mapping else class_names
            return {
                "source": "shape_stats",
                "groups": [
                    {
                        "field": class_object_name,
                        "classes": classes,
                        "class_mapping": {
                            cn: mapping.get(cn, cn) for cn in class_names
                        },
                    }
                ],
            }

        return {}

    def _generate_mapping_hints(self, class_names: list) -> dict[str, str]:
        """Generate mapping hints for class_names.

        For known boolean patterns (yes/no, true/false), use standard mappings.
        For other values, generate normalized snake_case keys.
        """
        mapping = {}
        for name in class_names:
            # Convert to string in case of numeric class_names
            name_str = str(name)

            # Try known patterns first (case-insensitive)
            matched = False
            for pattern_key, pattern_value in BINARY_MAPPING_PATTERNS.items():
                if name_str.lower() == pattern_key.lower():
                    mapping[name_str] = pattern_value
                    matched = True
                    break

            if not matched:
                # Generate normalized key from the value itself
                # "Forêt dense" -> "foret_dense", "Non-forêt" -> "non_foret"
                normalized = self._normalize_to_key(name_str)
                mapping[name_str] = normalized

        return mapping

    def _normalize_to_key(self, value: str) -> str:
        """Convert a value to a normalized snake_case key."""
        import unicodedata

        # Normalize unicode (é -> e, etc.)
        normalized = unicodedata.normalize("NFD", value)
        normalized = "".join(c for c in normalized if unicodedata.category(c) != "Mn")

        # Convert to lowercase and replace special chars with underscore
        result = normalized.lower()
        result = re.sub(r"[^a-z0-9]+", "_", result)
        result = result.strip("_")

        return result or "value"

    def _detect_pattern_group(
        self, class_object_name: str, all_class_objects: list[str]
    ) -> Optional[str]:
        """Detect if class_object belongs to a pattern group using dynamic detection."""
        # Check all detected groups
        groups = self._detect_pattern_groups(all_class_objects)
        for group_name, members in groups.items():
            if class_object_name in members:
                return group_name
        return None

    def _detect_pattern_groups(
        self, all_class_objects: list[str]
    ) -> dict[str, list[str]]:
        """Dynamically detect pattern groups by finding common prefixes.

        Instead of hardcoded patterns, this analyzes the actual class_object
        names to find groups with common prefixes.
        """
        groups: dict[str, list[str]] = {}

        # Find common prefixes (minimum 3 chars, must end with _)
        prefix_counts: dict[str, list[str]] = {}

        for name in all_class_objects:
            # Extract prefix (everything before the last segment)
            if "_" in name:
                # Try different prefix lengths
                parts = name.split("_")
                for i in range(1, len(parts)):
                    prefix = "_".join(parts[:i]) + "_"
                    if len(prefix) >= 4:  # At least 3 chars + underscore
                        if prefix not in prefix_counts:
                            prefix_counts[prefix] = []
                        if name not in prefix_counts[prefix]:
                            prefix_counts[prefix].append(name)

        # Keep only prefixes with multiple class_objects (actual groups)
        for prefix, members in prefix_counts.items():
            if len(members) >= 2:
                group_name = prefix + "*"
                # Avoid duplicate groups (prefer more specific)
                # Check if this group is not a subset of another
                is_subset = False
                for existing_name, existing_members in groups.items():
                    if set(members).issubset(set(existing_members)) and len(
                        members
                    ) < len(existing_members):
                        is_subset = True
                        break
                if not is_subset:
                    groups[group_name] = members

        # Also detect common suffixes for patterns like *_elevation, *_ha
        suffix_counts: dict[str, list[str]] = {}
        for name in all_class_objects:
            if "_" in name:
                parts = name.split("_")
                for i in range(1, len(parts)):
                    suffix = "_" + "_".join(parts[-i:])
                    if len(suffix) >= 4:
                        if suffix not in suffix_counts:
                            suffix_counts[suffix] = []
                        if name not in suffix_counts[suffix]:
                            suffix_counts[suffix].append(name)

        for suffix, members in suffix_counts.items():
            if len(members) >= 2:
                group_name = "*" + suffix
                if group_name not in groups:
                    groups[group_name] = members

        return groups


def analyze_csv(csv_path: str | Path) -> ClassObjectAnalysis:
    """Convenience function to analyze a CSV file."""
    analyzer = ClassObjectAnalyzer(Path(csv_path))
    return analyzer.analyze()
