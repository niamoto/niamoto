"""Tests for ClassObjectAnalyzer."""

import csv
import pytest

from niamoto.core.imports.class_object_analyzer import ClassObjectAnalyzer, analyze_csv


@pytest.fixture
def valid_csv_comma(tmp_path):
    """Create a valid CSV with comma delimiter."""
    csv_path = tmp_path / "test_comma.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f, delimiter=",")
        writer.writerow(["id", "class_object", "class_name", "class_value", "plot_id"])
        writer.writerow([1, "top10_family", "Sapindaceae", 206.0, 2])
        writer.writerow([2, "top10_family", "Malvaceae", 188.0, 2])
        writer.writerow([3, "cover_forest", "Foret", 0.34, 2])
        writer.writerow([4, "cover_forest", "Hors-foret", 0.66, 2])
        writer.writerow([5, "elevation_max", "", 1622.0, 2])
    return csv_path


@pytest.fixture
def valid_csv_semicolon(tmp_path):
    """Create a valid CSV with semicolon delimiter."""
    csv_path = tmp_path / "test_semicolon.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["id", "class_object", "class_name", "class_value", "shape_id"])
        writer.writerow([1, "forest_elevation", "100", 24476.99, "prov_1"])
        writer.writerow([2, "forest_elevation", "200", 42749.64, "prov_1"])
        writer.writerow([3, "forest_elevation", "300", 51243.96, "prov_1"])
    return csv_path


@pytest.fixture
def invalid_csv_missing_columns(tmp_path):
    """Create a CSV missing required columns."""
    csv_path = tmp_path / "test_invalid.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f, delimiter=",")
        writer.writerow(
            ["id", "name", "value"]
        )  # Missing class_object, class_name, class_value
        writer.writerow([1, "test", 100])
    return csv_path


class TestClassObjectAnalyzer:
    def test_detect_comma_delimiter(self, valid_csv_comma):
        """Test auto-detection of comma delimiter."""
        analyzer = ClassObjectAnalyzer(valid_csv_comma)
        assert analyzer.detect_delimiter() == ","

    def test_detect_semicolon_delimiter(self, valid_csv_semicolon):
        """Test auto-detection of semicolon delimiter."""
        analyzer = ClassObjectAnalyzer(valid_csv_semicolon)
        assert analyzer.detect_delimiter() == ";"

    def test_analyze_valid_csv(self, valid_csv_comma):
        """Test analysis of valid CSV with comma delimiter."""
        analysis = analyze_csv(valid_csv_comma)

        assert analysis.is_valid is True
        assert analysis.delimiter == ","
        assert analysis.row_count == 5
        assert analysis.entity_column == "plot_id"
        assert analysis.entity_count == 1
        assert len(analysis.class_objects) == 3

    def test_class_object_detection(self, valid_csv_comma):
        """Test correct detection of class_objects and their properties."""
        analysis = analyze_csv(valid_csv_comma)

        # Find class_objects by name
        class_objects = {co.name: co for co in analysis.class_objects}

        # top10_family has 2 distinct class_names
        assert "top10_family" in class_objects
        assert class_objects["top10_family"].cardinality == 2
        assert class_objects["top10_family"].value_type == "categorical"
        assert class_objects["top10_family"].suggested_plugin == "binary_aggregator"

        # cover_forest has 2 distinct class_names (binary)
        assert "cover_forest" in class_objects
        assert class_objects["cover_forest"].cardinality == 2
        assert class_objects["cover_forest"].suggested_plugin == "binary_aggregator"

        # elevation_max has 0 class_names (scalar)
        assert "elevation_max" in class_objects
        assert class_objects["elevation_max"].cardinality == 0
        assert class_objects["elevation_max"].suggested_plugin == "field_aggregator"

    def test_numeric_class_names(self, valid_csv_semicolon):
        """Test detection of numeric class_names for series_extractor."""
        analysis = analyze_csv(valid_csv_semicolon)

        class_objects = {co.name: co for co in analysis.class_objects}
        assert "forest_elevation" in class_objects
        assert class_objects["forest_elevation"].value_type == "numeric"
        assert class_objects["forest_elevation"].suggested_plugin == "series_extractor"

    def test_invalid_csv_validation(self, invalid_csv_missing_columns):
        """Test validation failure for missing columns."""
        analysis = analyze_csv(invalid_csv_missing_columns)

        assert analysis.is_valid is False
        assert len(analysis.validation_errors) > 0
        assert any("manquantes" in err for err in analysis.validation_errors)

    def test_entity_column_detection(self, valid_csv_comma, valid_csv_semicolon):
        """Test detection of entity column with different naming conventions."""
        # plot_id detection
        analysis1 = analyze_csv(valid_csv_comma)
        assert analysis1.entity_column == "plot_id"

        # shape_id detection
        analysis2 = analyze_csv(valid_csv_semicolon)
        assert analysis2.entity_column == "shape_id"


class TestPluginSuggestion:
    """Test plugin suggestion logic."""

    def test_scalar_suggestion(self, valid_csv_comma):
        """Scalar values (cardinality=0) should suggest field_aggregator."""
        analysis = analyze_csv(valid_csv_comma)
        scalar = next(co for co in analysis.class_objects if co.name == "elevation_max")
        assert scalar.suggested_plugin == "field_aggregator"
        assert scalar.confidence >= 0.9

    def test_binary_suggestion(self, valid_csv_comma):
        """Binary values (cardinality=2) should suggest binary_aggregator."""
        analysis = analyze_csv(valid_csv_comma)
        binary = next(co for co in analysis.class_objects if co.name == "cover_forest")
        assert binary.suggested_plugin == "binary_aggregator"
        assert binary.confidence >= 0.9

    def test_numeric_series_suggestion(self, valid_csv_semicolon):
        """Numeric class_names should suggest series_extractor."""
        analysis = analyze_csv(valid_csv_semicolon)
        series = next(
            co for co in analysis.class_objects if co.name == "forest_elevation"
        )
        assert series.suggested_plugin == "series_extractor"
        assert series.confidence >= 0.8
