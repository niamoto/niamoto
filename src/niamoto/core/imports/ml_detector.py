"""
ML-based column type detector using Random Forest.
Detects column types based on statistical features rather than column names.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Union
import pickle
import logging
from dataclasses import dataclass

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler

    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    logging.warning("scikit-learn not installed. ML detection will be disabled.")

logger = logging.getLogger(__name__)


@dataclass
class ColumnTypeConfig:
    """Configuration for column type detection."""

    # Column types to detect
    TYPES = [
        "diameter",  # DBH, circumference
        "height",  # Tree/plant height
        "leaf_area",  # Leaf surface area
        "wood_density",  # Wood specific gravity
        "species_name",  # Scientific species names
        "family_name",  # Taxonomic family
        "genus_name",  # Taxonomic genus
        "location",  # Location names
        "latitude",  # Geographic latitude
        "longitude",  # Geographic longitude
        "date",  # Temporal data
        "count",  # Count/abundance data
        "identifier",  # IDs and codes
        "other",  # Unknown/other
    ]

    # Confidence threshold for predictions
    CONFIDENCE_THRESHOLD = 0.7

    # Number of features to extract
    N_FEATURES = 21


class MLColumnDetector:
    """
    Machine Learning column type detector using Random Forest.
    Analyzes column values to detect semantic type without relying on column names.
    """

    def __init__(self, model_path: Optional[Path] = None):
        """
        Initialize the ML detector.

        Args:
            model_path: Path to pre-trained model, if available
        """
        if not HAS_SKLEARN:
            self.enabled = False
            logger.warning("ML detection disabled - scikit-learn not available")
            return

        self.enabled = True
        self.config = ColumnTypeConfig()
        self.scaler = StandardScaler()
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        )

        self.is_trained = False

        if model_path and Path(model_path).exists():
            try:
                self.load_model(model_path)
                logger.info(f"Loaded ML model from {model_path}")
            except Exception as e:
                logger.warning(f"Failed to load model: {e}")

    @classmethod
    def load_or_none(
        cls, model_path: Optional[Path] = None
    ) -> Optional["MLColumnDetector"]:
        """
        Load detector if model exists, otherwise return None.

        Args:
            model_path: Path to model file

        Returns:
            MLColumnDetector instance or None
        """
        if not HAS_SKLEARN:
            return None

        if model_path is None:
            # Default model location - works in both source and frozen modes
            from niamoto.common.bundle import get_resource_path

            model_path = get_resource_path("models/column_detector.pkl")

        if model_path.exists():
            try:
                detector = cls()
                detector.load_model(model_path)
                return detector
            except Exception as e:
                logger.warning(f"Could not load ML detector: {e}")

        return None

    def extract_features(self, series: pd.Series) -> np.ndarray:
        """
        Extract statistical features from a column without using its name.

        Args:
            series: Pandas series to analyze

        Returns:
            Array of 21 statistical features
        """
        features = []

        # Handle empty series
        clean_series = series.dropna()
        if len(clean_series) == 0:
            return np.zeros(self.config.N_FEATURES)

        # Numeric features
        if pd.api.types.is_numeric_dtype(series):
            features.extend(self._extract_numeric_features(clean_series))
        # Text features
        else:
            features.extend(self._extract_text_features(series))

        # Ensure exactly N_FEATURES
        features = features[: self.config.N_FEATURES]
        while len(features) < self.config.N_FEATURES:
            features.append(0)

        return np.array(features)

    def _extract_numeric_features(self, series: pd.Series) -> List[float]:
        """Extract features from numeric data."""
        features = []

        # Basic statistics (8 features)
        features.append(float(series.mean()))
        features.append(float(series.std()) if len(series) > 1 else 0)
        features.append(float(series.min()))
        features.append(float(series.max()))
        features.append(float(series.quantile(0.25)))
        features.append(float(series.quantile(0.50)))
        features.append(float(series.quantile(0.75)))
        features.append(float(series.max() - series.min()))  # Range

        # Distribution characteristics (3 features)
        features.append(float(series.skew()))
        features.append(float(series.kurtosis()))
        features.append(len(series.unique()) / len(series))  # Unique ratio

        # Value patterns (3 features)
        features.append((series > 0).mean())  # Proportion positive
        features.append((series % 1 == 0).mean())  # Proportion integers
        features.append((series < 0).mean())  # Proportion negative

        # Range indicators (3 features)
        # Check if values could be coordinates
        is_longitude = 1 if -180 <= series.min() and series.max() <= 180 else 0
        is_latitude = 1 if -90 <= series.min() and series.max() <= 90 else 0
        is_density = 1 if 0 <= series.min() and series.max() <= 2 else 0
        features.extend([is_longitude, is_latitude, is_density])

        # Distribution histogram (4 features)
        hist, _ = np.histogram(series, bins=4)
        hist_norm = hist / hist.sum() if hist.sum() > 0 else hist
        features.extend(hist_norm.tolist())

        return features

    def _extract_text_features(self, series: pd.Series) -> List[float]:
        """Extract features from text data."""
        features = []
        str_series = series.astype(str)
        clean_series = series.dropna()

        # Text statistics (8 features)
        features.append(str_series.str.len().mean())
        features.append(str_series.str.len().std() if len(str_series) > 1 else 0)
        features.append(str_series.str.count(" ").mean())  # Words
        features.append(str_series.str.count("[A-Z]").mean())  # Uppercase
        features.append(str_series.str.count("[a-z]").mean())  # Lowercase
        features.append(str_series.str.count("[0-9]").mean())  # Digits
        features.append(series.nunique() / len(series))  # Unique ratio
        features.append(str_series.str.count("-").mean())  # Hyphens

        # Pattern detection (3 features)
        # Binomial nomenclature pattern
        binomial_score = self._detect_binomial_pattern(clean_series)
        features.append(binomial_score)

        # Family name pattern
        family_score = self._detect_family_pattern(clean_series)
        features.append(family_score)

        # Location pattern
        location_score = self._detect_location_pattern(clean_series)
        features.append(location_score)

        # Padding to match numeric feature count (10 features)
        features.extend([0] * 10)

        return features

    def _detect_binomial_pattern(self, series: pd.Series) -> float:
        """Detect scientific binomial nomenclature pattern."""
        count = 0
        sample_size = min(50, len(series))

        for val in series.head(sample_size):
            if isinstance(val, str):
                parts = val.strip().split()
                if len(parts) == 2:
                    if parts[0] and parts[1]:
                        if parts[0][0].isupper() and parts[1][0].islower():
                            count += 1

        return count / sample_size if sample_size > 0 else 0

    def _detect_family_pattern(self, series: pd.Series) -> float:
        """Detect taxonomic family name pattern."""
        family_endings = ["aceae", "idae", "ales", "ineae"]
        count = 0
        sample_size = min(50, len(series))

        for val in series.head(sample_size):
            if isinstance(val, str):
                val_lower = val.lower()
                if any(val_lower.endswith(ending) for ending in family_endings):
                    count += 1

        return count / sample_size if sample_size > 0 else 0

    def _detect_location_pattern(self, series: pd.Series) -> float:
        """Detect location/place name pattern."""
        location_words = ["province", "commune", "district", "region", "city", "town"]
        count = 0
        sample_size = min(50, len(series))

        for val in series.head(sample_size):
            if isinstance(val, str):
                val_lower = val.lower()
                if any(word in val_lower for word in location_words):
                    count += 1

        return count / sample_size if sample_size > 0 else 0

    def train(self, training_data: List[Tuple[pd.Series, str]]):
        """
        Train the Random Forest model on labeled examples.

        Args:
            training_data: List of (series, label) tuples
        """
        if not self.enabled:
            logger.warning("Cannot train - ML detection is disabled")
            return

        logger.info(f"Training on {len(training_data)} examples")

        X = []
        y = []

        for series, label in training_data:
            if label not in self.config.TYPES:
                logger.warning(f"Unknown label: {label}, skipping")
                continue

            features = self.extract_features(series)
            X.append(features)
            y.append(label)

        if not X:
            logger.error("No valid training data")
            return

        X = np.array(X)

        # Normalize features
        X_scaled = self.scaler.fit_transform(X)

        # Train Random Forest
        self.model.fit(X_scaled, y)
        self.is_trained = True

        # Log feature importances
        importances = self.model.feature_importances_
        important_features = [
            (i, imp) for i, imp in enumerate(importances) if imp > 0.05
        ]
        logger.info(f"Important features: {important_features}")

        # Training accuracy
        train_score = self.model.score(X_scaled, y)
        logger.info(f"Training accuracy: {train_score:.2%}")

    def predict(
        self, series: pd.Series, return_all: bool = False
    ) -> Union[Tuple[str, float], Dict[str, float]]:
        """
        Predict column type from values.

        Args:
            series: Column to analyze
            return_all: Return all class probabilities

        Returns:
            Tuple of (predicted_type, confidence) or dict of all probabilities
        """
        if not self.enabled:
            return ("other", 0.0) if not return_all else {"other": 1.0}

        if not self.is_trained:
            # Fallback to rule-based detection
            return self._rule_based_detection(series, return_all)

        # Extract features
        features = self.extract_features(series).reshape(1, -1)

        # Scale features
        features_scaled = self.scaler.transform(features)

        # Predict
        if return_all:
            probas = self.model.predict_proba(features_scaled)[0]
            return {cls: float(prob) for cls, prob in zip(self.model.classes_, probas)}
        else:
            prediction = self.model.predict(features_scaled)[0]
            probas = self.model.predict_proba(features_scaled)[0]
            max_prob = probas.max()
            return (prediction, float(max_prob))

    def _rule_based_detection(
        self, series: pd.Series, return_all: bool = False
    ) -> Union[Tuple[str, float], Dict[str, float]]:
        """
        Simple rule-based fallback when model is not available.
        """
        if pd.api.types.is_numeric_dtype(series):
            clean = series.dropna()

            # Check for typical ecological measurements
            mean_val = clean.mean()
            max_val = clean.max()
            min_val = clean.min()
            skewness = clean.skew()

            # DBH pattern
            if 5 < mean_val < 100 and max_val < 500 and skewness > 1:
                result = ("diameter", 0.7)
            # Height pattern
            elif 1 < mean_val < 30 and max_val < 60:
                result = ("height", 0.6)
            # Wood density pattern
            elif 0.1 < mean_val < 1 and max_val < 1.5:
                result = ("wood_density", 0.7)
            # Latitude
            elif -90 <= min_val and max_val <= 90:
                result = ("latitude", 0.6)
            # Longitude
            elif -180 <= min_val and max_val <= 180:
                result = ("longitude", 0.6)
            else:
                result = ("other", 0.3)
        else:
            # Check text patterns
            if self._detect_binomial_pattern(series) > 0.3:
                result = ("species_name", 0.7)
            elif self._detect_family_pattern(series) > 0.3:
                result = ("family_name", 0.7)
            else:
                result = ("other", 0.3)

        if return_all:
            # Create probability dict with main prediction
            probs = {t: 0.1 for t in self.config.TYPES}
            probs[result[0]] = result[1]
            return probs
        else:
            return result

    def save_model(self, path: Path):
        """Save trained model and scaler."""
        if not self.is_trained:
            logger.warning("Model not trained, nothing to save")
            return

        model_data = {
            "model": self.model,
            "scaler": self.scaler,
            "config": self.config,
            "feature_names": self._get_feature_names(),
        }

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(model_data, f)

        logger.info(f"Model saved to {path}")

    def load_model(self, path: Path):
        """Load trained model and scaler."""
        if not Path(path).exists():
            raise FileNotFoundError(f"Model file not found: {path}")

        with open(path, "rb") as f:
            model_data = pickle.load(f)

        self.model = model_data["model"]
        self.scaler = model_data["scaler"]
        self.config = model_data.get("config", ColumnTypeConfig())
        self.is_trained = True

        logger.info(f"Model loaded from {path}")

    def _get_feature_names(self) -> List[str]:
        """Get names for the extracted features (for interpretability)."""
        return [
            "mean",
            "std",
            "min",
            "max",
            "q25",
            "q50",
            "q75",
            "range",
            "skew",
            "kurtosis",
            "unique_ratio",
            "positive_ratio",
            "integer_ratio",
            "negative_ratio",
            "is_longitude",
            "is_latitude",
            "is_density",
            "hist_bin1",
            "hist_bin2",
            "hist_bin3",
            "hist_bin4",
        ]
