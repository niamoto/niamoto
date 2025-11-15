"""
Unit tests for ML column detector.
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path
import tempfile

from niamoto.core.imports.ml_detector import (
    MLColumnDetector,
    ColumnTypeConfig,
    HAS_SKLEARN,
)


class TestMLColumnDetector:
    """Test the ML column detector."""

    def test_initialization(self):
        """Test detector initialization."""
        if not HAS_SKLEARN:
            pytest.skip("scikit-learn not available")

        detector = MLColumnDetector()
        assert detector.enabled is True
        assert detector.is_trained is False
        assert detector.config.CONFIDENCE_THRESHOLD == 0.7
        assert detector.config.N_FEATURES == 21

    def test_feature_extraction_numeric(self):
        """Test feature extraction for numeric columns."""
        if not HAS_SKLEARN:
            pytest.skip("scikit-learn not available")

        detector = MLColumnDetector()

        # Test DBH-like data
        dbh_data = pd.Series(np.random.lognormal(3.0, 0.8, 100))
        dbh_data = np.clip(dbh_data, 5, 200)
        features = detector.extract_features(dbh_data)

        assert len(features) == 21
        assert features[0] > 0  # Mean should be positive
        assert features[1] > 0  # Std should be positive
        assert features[2] >= 5  # Min should be >= 5

    def test_feature_extraction_text(self):
        """Test feature extraction for text columns."""
        if not HAS_SKLEARN:
            pytest.skip("scikit-learn not available")

        detector = MLColumnDetector()

        # Test species name data
        species_data = pd.Series(
            [
                "Araucaria columnaris",
                "Agathis lanceolata",
                "Podocarpus minor",
                "Metrosideros robusta",
            ]
        )
        features = detector.extract_features(species_data)

        assert len(features) == 21
        assert features[0] > 0  # Average string length

    def test_binomial_pattern_detection(self):
        """Test detection of binomial nomenclature pattern."""
        if not HAS_SKLEARN:
            pytest.skip("scikit-learn not available")

        detector = MLColumnDetector()

        # Valid binomial names
        species = pd.Series(
            ["Araucaria columnaris", "Agathis montana", "Podocarpus minor"]
        )
        score = detector._detect_binomial_pattern(species)
        assert score == 1.0  # All are valid binomial names

        # Invalid names
        invalid = pd.Series(["ARAUCARIACEAE", "Tree1", "Sample"])
        score = detector._detect_binomial_pattern(invalid)
        assert score == 0.0  # None are binomial names

    def test_family_pattern_detection(self):
        """Test detection of family name pattern."""
        if not HAS_SKLEARN:
            pytest.skip("scikit-learn not available")

        detector = MLColumnDetector()

        # Valid family names
        families = pd.Series(["Araucariaceae", "Podocarpaceae", "Myrtaceae"])
        score = detector._detect_family_pattern(families)
        assert score == 1.0  # All end with -aceae

        # Mixed data
        mixed = pd.Series(["Araucariaceae", "Araucaria", "Tree"])
        score = detector._detect_family_pattern(mixed)
        assert 0.3 < score < 0.4  # Only 1/3 is a family

    def test_training(self):
        """Test model training."""
        if not HAS_SKLEARN:
            pytest.skip("scikit-learn not available")

        detector = MLColumnDetector()

        # Create simple training data
        training_data = []

        # Add DBH examples
        for _ in range(5):
            dbh = pd.Series(np.random.lognormal(3.0, 0.8, 50))
            dbh = np.clip(dbh, 5, 200)
            training_data.append((dbh, "diameter"))

        # Add height examples
        for _ in range(5):
            height = pd.Series(np.random.normal(15, 5, 50))
            height = np.clip(height, 1, 45)
            training_data.append((height, "height"))

        # Add species examples
        species_names = ["Araucaria columnaris", "Agathis montana", "Podocarpus minor"]
        for _ in range(5):
            species = pd.Series(np.random.choice(species_names, 50))
            training_data.append((species, "species_name"))

        # Train the model
        detector.train(training_data)
        assert detector.is_trained is True

    def test_prediction(self):
        """Test prediction on new data."""
        if not HAS_SKLEARN:
            pytest.skip("scikit-learn not available")

        detector = MLColumnDetector()

        # Test rule-based fallback when not trained
        dbh = pd.Series(np.random.lognormal(3.0, 0.8, 100))
        dbh = np.clip(dbh, 5, 200)

        pred_type, confidence = detector.predict(dbh)
        assert pred_type == "diameter"
        assert 0.6 <= confidence <= 0.8

    def test_predict_all_probabilities(self):
        """Test getting all class probabilities."""
        if not HAS_SKLEARN:
            pytest.skip("scikit-learn not available")

        detector = MLColumnDetector()

        # Test with rule-based fallback
        height = pd.Series(np.random.normal(15, 5, 100))
        height = np.clip(height, 1, 45)

        all_probs = detector.predict(height, return_all=True)
        assert isinstance(all_probs, dict)
        assert "height" in all_probs
        assert all_probs["height"] >= 0.5

    def test_save_load_model(self):
        """Test saving and loading a trained model."""
        if not HAS_SKLEARN:
            pytest.skip("scikit-learn not available")

        detector = MLColumnDetector()

        # Create and train with minimal data
        training_data = [
            (pd.Series(np.random.lognormal(3.0, 0.8, 30)), "diameter"),
            (pd.Series(np.random.normal(15, 5, 30)), "height"),
        ]
        detector.train(training_data)

        # Save model
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "test_model.pkl"
            detector.save_model(model_path)
            assert model_path.exists()

            # Load model in new detector
            detector2 = MLColumnDetector()
            detector2.load_model(model_path)
            assert detector2.is_trained is True

            # Test predictions are the same
            test_data = pd.Series(np.random.lognormal(3.0, 0.8, 50))
            pred1 = detector.predict(test_data)
            pred2 = detector2.predict(test_data)
            assert pred1[0] == pred2[0]  # Same prediction

    def test_load_or_none(self):
        """Test the class method load_or_none."""
        if not HAS_SKLEARN:
            pytest.skip("scikit-learn not available")

        # Test with non-existent path
        detector = MLColumnDetector.load_or_none(Path("nonexistent.pkl"))
        assert detector is None

        # Test with valid model
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "test_model.pkl"

            # Create and save a model
            detector1 = MLColumnDetector()
            training_data = [
                (pd.Series(np.random.normal(15, 5, 30)), "height"),
            ]
            detector1.train(training_data)
            detector1.save_model(model_path)

            # Load with class method
            detector2 = MLColumnDetector.load_or_none(model_path)
            assert detector2 is not None
            assert detector2.is_trained is True

    def test_empty_series(self):
        """Test handling of empty series."""
        if not HAS_SKLEARN:
            pytest.skip("scikit-learn not available")

        detector = MLColumnDetector()

        # Empty series
        empty_series = pd.Series([])
        features = detector.extract_features(empty_series)
        assert len(features) == 21
        assert all(f == 0 for f in features)

        # Series with only NaN
        nan_series = pd.Series([np.nan, np.nan, np.nan])
        features = detector.extract_features(nan_series)
        assert len(features) == 21

    def test_coordinate_detection(self):
        """Test detection of coordinate columns."""
        if not HAS_SKLEARN:
            pytest.skip("scikit-learn not available")

        detector = MLColumnDetector()

        # Latitude-like data
        lat_data = pd.Series(np.random.uniform(-23, -19.5, 100))
        features = detector.extract_features(lat_data)
        assert features[15] == 1  # is_latitude flag

        # Longitude-like data
        lon_data = pd.Series(np.random.uniform(163.5, 169, 100))
        features = detector.extract_features(lon_data)
        assert features[14] == 1  # is_longitude flag

    def test_wood_density_detection(self):
        """Test detection of wood density values."""
        if not HAS_SKLEARN:
            pytest.skip("scikit-learn not available")

        detector = MLColumnDetector()

        # Wood density data
        wd_data = pd.Series(np.random.beta(5, 2, 100) * 0.8 + 0.2)
        features = detector.extract_features(wd_data)
        assert features[16] == 1  # is_density flag

    def test_location_pattern_detection(self):
        """Test detection of location names."""
        if not HAS_SKLEARN:
            pytest.skip("scikit-learn not available")

        detector = MLColumnDetector()

        # Location names
        locations = pd.Series(["Province Sud", "Province Nord", "Commune de Yaté"])
        score = detector._detect_location_pattern(locations)
        assert score > 0.6  # Most contain location keywords

    def test_disabled_sklearn(self):
        """Test behavior when scikit-learn is not available."""
        if HAS_SKLEARN:
            pytest.skip("scikit-learn is available")

        detector = MLColumnDetector()
        assert detector.enabled is False

        # Predict should return default
        series = pd.Series([1, 2, 3])
        pred_type, confidence = detector.predict(series)
        assert pred_type == "other"
        assert confidence == 0.0

    def test_column_type_config(self):
        """Test ColumnTypeConfig dataclass."""
        config = ColumnTypeConfig()

        assert "diameter" in config.TYPES
        assert "species_name" in config.TYPES
        assert "other" in config.TYPES
        assert config.CONFIDENCE_THRESHOLD == 0.7
        assert config.N_FEATURES == 21

    def test_unknown_label_in_training(self):
        """Test handling of unknown labels during training."""
        if not HAS_SKLEARN:
            pytest.skip("scikit-learn not available")

        detector = MLColumnDetector()

        # Include unknown label
        training_data = [
            (pd.Series(np.random.normal(15, 5, 30)), "height"),
            (pd.Series(np.random.normal(10, 2, 30)), "unknown_type"),  # Invalid
        ]

        # Should train with valid data only
        detector.train(training_data)
        assert detector.is_trained is True

    def test_numeric_feature_details(self):
        """Test detailed numeric feature extraction."""
        if not HAS_SKLEARN:
            pytest.skip("scikit-learn not available")

        detector = MLColumnDetector()

        # Create specific distribution
        data = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        features = detector.extract_features(data)

        # Check specific features
        assert features[0] == 5.5  # Mean
        assert features[2] == 1.0  # Min
        assert features[3] == 10.0  # Max
        assert features[10] > 0.9  # High unique ratio

    def test_text_feature_details(self):
        """Test detailed text feature extraction."""
        if not HAS_SKLEARN:
            pytest.skip("scikit-learn not available")

        detector = MLColumnDetector()

        # Create specific text data
        data = pd.Series(["ABC 123", "DEF 456", "GHI 789"])
        features = detector._extract_text_features(data)

        # Check features
        assert features[0] == 7.0  # Average length
        assert features[2] == 1.0  # One space per string
        assert features[5] == 3.0  # Three digits per string
