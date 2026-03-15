"""Tests for DataProfiler ml_mode parameter."""

import warnings
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from niamoto.core.imports.profiler import DataProfiler, ML_MODES


class TestMlModeParameter:
    """Test the ml_mode API on DataProfiler."""

    def test_default_is_auto(self):
        profiler = DataProfiler()
        assert profiler.ml_mode == "auto"

    def test_mode_off(self):
        profiler = DataProfiler(ml_mode="off")
        assert profiler.ml_mode == "off"
        assert profiler.ml_detector is None

    def test_mode_off_profiles_without_ml(self):
        profiler = DataProfiler(ml_mode="off")
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
            f.write("dbh,height,family\n")
            f.write("15.5,12.3,Araucariaceae\n")
            f.write("23.2,18.5,Podocarpaceae\n")
            temp_path = Path(f.name)
        try:
            profile = profiler.profile(temp_path)
            assert profile.record_count == 2
            # Pattern-based detection should still work
            dbh_col = next((c for c in profile.columns if c.name == "dbh"), None)
            assert dbh_col is not None
            assert dbh_col.semantic_type == "measurement"
        finally:
            temp_path.unlink()

    def test_mode_auto_loads_model_if_available(self):
        """auto mode should try to load model but not fail if absent."""
        profiler = DataProfiler(ml_mode="auto")
        # Should not raise, regardless of model availability
        assert profiler.ml_mode == "auto"

    def test_mode_force_raises_if_no_model(self):
        """force mode should raise if no model is found."""
        with patch(
            "niamoto.core.imports.profiler.MLColumnDetector.load_or_none",
            return_value=None,
        ):
            with pytest.raises(RuntimeError, match="ml_mode='force'"):
                DataProfiler(ml_mode="force")

    def test_invalid_mode_raises(self):
        with pytest.raises(ValueError, match="Invalid ml_mode"):
            DataProfiler(ml_mode="invalid")

    def test_legacy_ml_detector_param_warns(self):
        """Passing ml_detector= should emit deprecation warning."""
        from niamoto.core.imports.ml_detector import MLColumnDetector

        detector = MLColumnDetector()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            profiler = DataProfiler(ml_detector=detector)
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "deprecated" in str(w[0].message).lower()
        assert profiler.ml_detector is detector

    def test_legacy_ml_detector_none_no_warning(self):
        """Passing ml_detector=None should NOT emit deprecation warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            DataProfiler(ml_detector=None)
            # Filter for our specific deprecation
            relevant = [x for x in w if "DataProfiler" in str(x.message)]
            assert len(relevant) == 0

    def test_ml_modes_constant(self):
        assert ML_MODES == ("auto", "off", "force")
