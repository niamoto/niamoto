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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import duckdb


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

            for (class_object_name,) in class_object_names:
                stats = self._analyze_class_object(conn, class_object_name)
                class_objects_stats.append(stats)

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
            )

        finally:
            conn.close()

    def _analyze_class_object(
        self, conn: duckdb.DuckDBPyConnection, class_object_name: str
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

        # Suggest plugin
        plugin, confidence = self._suggest_plugin(
            len(class_names), value_type, class_names
        )

        return ClassObjectStats(
            name=class_object_name,
            cardinality=len(class_names),
            class_names=class_names[:10],  # Limit to first 10 for display
            value_type=value_type,
            sample_values=sample_values,
            suggested_plugin=plugin,
            confidence=confidence,
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
        - cardinality == 1 → field_aggregator (single scalar value)
        - cardinality == 2 → binary_aggregator (binary ratio like forest/non-forest)
        - cardinality <= 5 && categorical → categories_extractor (categorical distribution)
        - numeric class_names → series_extractor (numeric distribution by elevation, etc.)
        - cardinality > 5 && categorical → categories_extractor (but lower confidence)
        """
        # No class_name (scalar metric with empty class_name like elevation_max)
        if cardinality == 0:
            return "field_aggregator", 0.95

        # Single value (scalar metric)
        if cardinality == 1:
            return "field_aggregator", 0.95

        # Binary (exactly 2 categories)
        if cardinality == 2:
            return "binary_aggregator", 0.95

        # Numeric series (elevation distributions, etc.)
        if value_type == "numeric":
            return "series_extractor", 0.90

        # Small categorical set (good for pie/bar charts)
        if cardinality <= 5:
            return "categories_extractor", 0.90

        # Large categorical set (still works but may be cluttered)
        if cardinality <= 15:
            return "categories_extractor", 0.75

        # Very large categorical (like top10_family/species with >10 items)
        return "categories_extractor", 0.60


def analyze_csv(csv_path: str | Path) -> ClassObjectAnalysis:
    """Convenience function to analyze a CSV file."""
    analyzer = ClassObjectAnalyzer(Path(csv_path))
    return analyzer.analyze()
