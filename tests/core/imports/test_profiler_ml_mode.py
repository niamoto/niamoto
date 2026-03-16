"""Tests for DataProfiler backward-compat with legacy ml_mode/ml_detector kwargs."""

import tempfile
from pathlib import Path

from niamoto.core.imports.profiler import DataProfiler


class TestLegacyKwargsBackwardCompat:
    """Verify that old ml_mode/ml_detector kwargs are accepted without error."""

    def test_default_constructor(self):
        profiler = DataProfiler()
        assert profiler is not None

    def test_ml_mode_auto_accepted(self):
        profiler = DataProfiler(ml_mode="auto")
        assert profiler is not None

    def test_ml_mode_off_accepted(self):
        profiler = DataProfiler(ml_mode="off")
        assert profiler is not None

    def test_ml_mode_force_accepted(self):
        profiler = DataProfiler(ml_mode="force")
        assert profiler is not None

    def test_ml_detector_none_accepted(self):
        """Passing ml_detector=None should work without warning."""
        profiler = DataProfiler(ml_detector=None)
        assert profiler is not None

    def test_ml_detector_false_accepted(self):
        """Passing ml_detector=False should work (legacy sentinel)."""
        profiler = DataProfiler(ml_detector=False)
        assert profiler is not None

    def test_profiles_correctly_with_any_kwargs(self):
        """Profiling works regardless of legacy kwargs."""
        for kwargs in [
            {},
            {"ml_mode": "auto"},
            {"ml_mode": "off"},
            {"ml_detector": None},
        ]:
            profiler = DataProfiler(**kwargs)
            with tempfile.NamedTemporaryFile(
                suffix=".csv", mode="w", delete=False
            ) as f:
                f.write("dbh,height,family\n")
                f.write("15.5,12.3,Araucariaceae\n")
                f.write("23.2,18.5,Podocarpaceae\n")
                temp_path = Path(f.name)
            try:
                profile = profiler.profile(temp_path)
                assert profile.record_count == 2
                # Pattern detection via AliasRegistry should still work
                dbh_col = next((c for c in profile.columns if c.name == "dbh"), None)
                assert dbh_col is not None
                assert dbh_col.semantic_type is not None
            finally:
                temp_path.unlink()
