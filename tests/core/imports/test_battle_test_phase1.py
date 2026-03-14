"""
Phase 1: GBIF ingestion blockers — tests for I/O fixes.

Tests for: profile_dataframe, TSV/TXT support, encoding fallback, sampling.
"""

import pandas as pd

from niamoto.core.imports.profiler import DataProfiler


# ── Phase 1.1: Eliminate double pandas loading ─────────────────────────────


class TestProfileDataframe:
    """Verify profile_dataframe() produces same results as profile()."""

    def test_profile_dataframe_matches_profile(self, tmp_path):
        """profile_dataframe(df) should produce same result as profile(path)."""
        csv_path = tmp_path / "test.csv"
        df = pd.DataFrame(
            {
                "species": ["Araucaria", "Podocarpus", "Nothofagus"],
                "height": [15.2, 8.5, 12.0],
                "latitude": [-22.1, -22.2, -22.3],
            }
        )
        df.to_csv(csv_path, index=False)

        profiler = DataProfiler(ml_detector=None)

        profile_from_file = profiler.profile(csv_path)
        profile_from_df = profiler.profile_dataframe(df, csv_path)

        assert profile_from_file.record_count == profile_from_df.record_count
        assert len(profile_from_file.columns) == len(profile_from_df.columns)
        assert profile_from_file.detected_type == profile_from_df.detected_type

        # Column names should match
        file_cols = {c.name for c in profile_from_file.columns}
        df_cols = {c.name for c in profile_from_df.columns}
        assert file_cols == df_cols

    def test_profile_dataframe_with_total_count(self, tmp_path):
        """total_count parameter overrides len(df) for record_count."""
        csv_path = tmp_path / "test.csv"
        df = pd.DataFrame({"x": [1, 2, 3]})
        df.to_csv(csv_path, index=False)

        profiler = DataProfiler(ml_detector=None)
        profile = profiler.profile_dataframe(df, csv_path, total_count=1000000)

        assert profile.record_count == 1000000

    def test_profile_dataframe_without_total_count(self, tmp_path):
        """Without total_count, record_count = len(df)."""
        csv_path = tmp_path / "test.csv"
        df = pd.DataFrame({"x": [1, 2, 3, 4, 5]})
        df.to_csv(csv_path, index=False)

        profiler = DataProfiler(ml_detector=None)
        profile = profiler.profile_dataframe(df, csv_path)

        assert profile.record_count == 5

    def test_engine_uses_profile_dataframe(self, tmp_path):
        """engine._analyze_for_transformers uses profile_dataframe, not profile."""
        from niamoto.core.imports.engine import GenericImporter
        from niamoto.core.imports.data_analyzer import DataAnalyzer
        from niamoto.core.imports.transformer_suggester import TransformerSuggester
        from unittest.mock import patch

        csv_path = tmp_path / "test.csv"
        df = pd.DataFrame(
            {
                "species": ["A", "B", "C"],
                "value": [1.0, 2.0, 3.0],
            }
        )
        df.to_csv(csv_path, index=False)

        engine = GenericImporter.__new__(GenericImporter)
        engine.data_analyzer = DataAnalyzer()
        engine.transformer_suggester = TransformerSuggester()

        with patch.object(DataProfiler, "profile") as mock_profile:
            engine._analyze_for_transformers(
                df=df, csv_path=csv_path, entity_name="test"
            )
            # profile() should NOT be called — we use profile_dataframe() instead
            mock_profile.assert_not_called()


# ── Phase 1.2: TSV/TXT support ────────────────────────────────────────────


class TestTsvTxtSupport:
    """Verify profiler handles TSV and .txt files."""

    def test_profile_tsv_file(self, tmp_path):
        """Profiler should handle TSV files."""
        tsv_path = tmp_path / "data.tsv"
        df = pd.DataFrame(
            {
                "gbifID": [1, 2, 3],
                "scientificName": [
                    "Araucaria columnaris",
                    "Podocarpus sp.",
                    "Nothofagus",
                ],
                "decimalLatitude": [-22.1, -22.2, -22.3],
            }
        )
        df.to_csv(tsv_path, sep="\t", index=False)

        profiler = DataProfiler(ml_detector=None)
        profile = profiler.profile(tsv_path)

        assert profile is not None
        assert profile.record_count == 3
        assert len(profile.columns) == 3

    def test_profile_txt_file(self, tmp_path):
        """Profiler should handle .txt files (GBIF download format)."""
        txt_path = tmp_path / "occurrence.txt"
        df = pd.DataFrame(
            {
                "gbifID": [1, 2, 3],
                "scientificName": ["Sp1", "Sp2", "Sp3"],
                "decimalLatitude": [-22.1, -22.2, -22.3],
            }
        )
        df.to_csv(txt_path, sep="\t", index=False)

        profiler = DataProfiler(ml_detector=None)
        profile = profiler.profile(txt_path)

        assert profile is not None
        assert profile.record_count == 3

    def test_profile_csv_still_works(self, tmp_path):
        """CSV files should still work as before."""
        csv_path = tmp_path / "data.csv"
        df = pd.DataFrame({"x": [1, 2, 3]})
        df.to_csv(csv_path, index=False)

        profiler = DataProfiler(ml_detector=None)
        profile = profiler.profile(csv_path)

        assert profile is not None
        assert profile.record_count == 3


# ── Phase 1.3: Encoding fallback ──────────────────────────────────────────


class TestEncodingFallback:
    """Verify profiler handles non-UTF-8 encodings."""

    def test_profile_latin1_csv(self, tmp_path):
        """Profiler should handle latin-1 encoded CSV files."""
        csv_path = tmp_path / "latin1.csv"
        # Write CSV with latin-1 encoding and accented characters
        with open(csv_path, "w", encoding="latin-1") as f:
            f.write("espèce,localité,hauteur\n")
            f.write("Araucária,Nouméa,15.2\n")
            f.write("Podocàrpus,Côte,8.5\n")
            f.write("Nöthofagus,Île,12.0\n")

        profiler = DataProfiler(ml_detector=None)
        profile = profiler.profile(csv_path)

        assert profile is not None
        assert profile.record_count == 3
        assert len(profile.columns) == 3
