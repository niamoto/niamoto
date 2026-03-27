"""
Test profiler semantic detection via AliasRegistry.

These tests verify that DataProfiler correctly detects semantic types
using the AliasRegistry (name-based) + value-based high-precision rules.
"""

import tempfile
from pathlib import Path

import pytest

from niamoto.core.imports.profiler import DataProfiler


class TestProfilerAliasRegistryDetection:
    """Test semantic detection through AliasRegistry in DataProfiler."""

    def test_profiler_detects_known_columns(self):
        """Profiler detects common ecological column names."""
        profiler = DataProfiler()

        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
            f.write("dbh,height,family\n")
            f.write("15.5,12.3,Araucariaceae\n")
            f.write("23.2,18.5,Podocarpaceae\n")
            f.write("45.1,25.2,Myrtaceae\n")
            temp_path = Path(f.name)

        try:
            profile = profiler.profile(temp_path)
            assert profile.record_count == 3
            assert len(profile.columns) == 3

            # dbh should be detected (measurement.diameter via AliasRegistry)
            dbh_col = next((c for c in profile.columns if c.name == "dbh"), None)
            assert dbh_col is not None
            assert dbh_col.semantic_type is not None
            assert "measurement" in dbh_col.semantic_type

            # family should be detected as taxonomy
            family_col = next((c for c in profile.columns if c.name == "family"), None)
            assert family_col is not None
            assert family_col.semantic_type is not None
            assert "taxonomy" in family_col.semantic_type
        finally:
            temp_path.unlink()

    def test_coordinate_detection_with_value_boost(self):
        """Lat/lon columns get boosted confidence when values confirm."""
        profiler = DataProfiler()

        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
            f.write("lat,lon,species\n")
            f.write("-22.1,166.5,Araucaria columnaris\n")
            f.write("-21.5,167.2,Agathis montana\n")
            temp_path = Path(f.name)

        try:
            profile = profiler.profile(temp_path)

            lat_col = next((c for c in profile.columns if c.name == "lat"), None)
            assert lat_col is not None
            assert lat_col.semantic_type == "location.latitude"
            assert lat_col.confidence >= 0.9

            lon_col = next((c for c in profile.columns if c.name == "lon"), None)
            assert lon_col is not None
            assert lon_col.semantic_type == "location.longitude"
            assert lon_col.confidence >= 0.9
        finally:
            temp_path.unlink()

    def test_profile_column_confidence(self):
        """Confidence scores are properly propagated."""
        profiler = DataProfiler()

        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
            f.write("family,dbh,unknown_col\n")
            f.write("Araucariaceae,15.5,abc\n")
            f.write("Podocarpaceae,23.2,def\n")
            temp_path = Path(f.name)

        try:
            profile = profiler.profile(temp_path)

            # Known patterns should have high confidence
            family_col = next((c for c in profile.columns if c.name == "family"), None)
            assert family_col.confidence >= 0.7

            dbh_col = next((c for c in profile.columns if c.name == "dbh"), None)
            assert dbh_col.confidence >= 0.7

            # Unknown should have low/no confidence
            unknown_col = next(
                (c for c in profile.columns if c.name == "unknown_col"), None
            )
            assert unknown_col.confidence == 0.0
        finally:
            temp_path.unlink()

    def test_dataset_type_detection(self):
        """Dataset type detection works with AliasRegistry semantic types."""
        profiler = DataProfiler()

        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
            f.write("lat,lon,species,dbh\n")
            f.write("-22.1,166.5,Araucaria columnaris,15.5\n")
            f.write("-21.5,167.2,Agathis montana,23.2\n")
            temp_path = Path(f.name)

        try:
            profile = profiler.profile(temp_path)
            # Should detect as spatial due to coordinates
            assert profile.detected_type == "spatial"
        finally:
            temp_path.unlink()

    def test_relationships_detection(self):
        """Relationship detection with AliasRegistry-detected types."""
        profiler = DataProfiler()

        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
            f.write("id,plot_id,taxon_id,value\n")
            f.write("1,101,201,15.5\n")
            f.write("2,102,202,23.2\n")
            temp_path = Path(f.name)

        try:
            profile = profiler.profile(temp_path)

            # taxon_id should be detected as reference.taxon
            taxon_col = next((c for c in profile.columns if c.name == "taxon_id"), None)
            assert taxon_col is not None
            assert taxon_col.semantic_type is not None
        finally:
            temp_path.unlink()

    @pytest.mark.parametrize(
        ("column_name", "values", "expected_fragment"),
        [
            (
                "scientificName",
                ["Araucaria columnaris", "Agathis montana"],
                "taxonomy",
            ),
            ("decimalLatitude", [-22.1, -21.5], "location"),
            ("decimalLongitude", [166.5, 167.2], "location"),
            ("kingdom", ["Plantae", "Animalia"], "taxonomy"),
            ("eventDate", ["2024-01-15", "2024-02-20"], "event"),
        ],
    )
    def test_darwin_core_columns(self, column_name, values, expected_fragment):
        """Darwin Core standard column names are recognized."""
        profiler = DataProfiler()

        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
            f.write(f"{column_name}\n")
            for value in values:
                f.write(f"{value}\n")
            temp_path = Path(f.name)

        try:
            profile = profiler.profile(temp_path)
            col = next((c for c in profile.columns if c.name == column_name), None)
            assert col is not None
            assert col.semantic_type is not None
            assert expected_fragment in col.semantic_type
        finally:
            temp_path.unlink()

    def test_semantic_profile_populated(self):
        """Both semantic_type and semantic_profile are populated."""
        profiler = DataProfiler()

        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
            f.write("species,height\n")
            f.write("Araucaria,15.2\n")
            f.write("Podocarpus,8.5\n")
            temp_path = Path(f.name)

        try:
            profile = profiler.profile(temp_path)

            for col in profile.columns:
                if col.semantic_type:
                    assert col.semantic_profile is not None
                    assert col.semantic_profile.role is not None
        finally:
            temp_path.unlink()
