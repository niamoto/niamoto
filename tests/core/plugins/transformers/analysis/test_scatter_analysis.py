"""Tests pour le plugin ScatterAnalysis."""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock

from niamoto.core.plugins.transformers.analysis.scatter_analysis import ScatterAnalysis


@pytest.fixture
def scatter_plugin():
    """Fixture pour une instance ScatterAnalysis."""
    return ScatterAnalysis(db=MagicMock())


def _make_config(x_field="x", y_field="y", max_points=5000):
    return {
        "plugin": "scatter_analysis",
        "params": {
            "source": "occurrences",
            "x_field": x_field,
            "y_field": y_field,
            "max_points": max_points,
        },
    }


class TestScatterAnalysisValidation:
    """Tests de validation de la configuration."""

    def test_validate_config_valid(self, scatter_plugin):
        """Configuration valide ne lève pas d'erreur."""
        scatter_plugin.validate_config(_make_config())

    def test_validate_config_missing_x_field(self, scatter_plugin):
        """Configuration sans x_field lève une erreur."""
        config = {
            "plugin": "scatter_analysis",
            "params": {"source": "occurrences", "y_field": "y"},
        }
        with pytest.raises(ValueError, match="Configuration invalide"):
            scatter_plugin.validate_config(config)

    def test_validate_config_missing_y_field(self, scatter_plugin):
        """Configuration sans y_field lève une erreur."""
        config = {
            "plugin": "scatter_analysis",
            "params": {"source": "occurrences", "x_field": "x"},
        }
        with pytest.raises(ValueError, match="Configuration invalide"):
            scatter_plugin.validate_config(config)


class TestScatterAnalysisTransform:
    """Tests de la méthode transform."""

    def test_transform_basic(self, scatter_plugin):
        """Transformation basique retourne un DataFrame avec 2 colonnes."""
        data = pd.DataFrame({"x": [1, 2, 3, 4, 5], "y": [10, 20, 30, 40, 50]})
        result = scatter_plugin.transform(data, _make_config())

        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ["x", "y"]
        assert len(result) == 5

    def test_transform_drops_nan(self, scatter_plugin):
        """Les lignes avec NaN sont supprimées."""
        data = pd.DataFrame(
            {"x": [1, np.nan, 3, 4, np.nan], "y": [10, 20, np.nan, 40, 50]}
        )
        result = scatter_plugin.transform(data, _make_config())

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2  # seules les lignes (1,10) et (4,40) survivent

    def test_transform_coerces_non_numeric(self, scatter_plugin):
        """Les valeurs non numériques sont converties en NaN puis supprimées."""
        data = pd.DataFrame({"x": [1, "abc", 3], "y": [10, 20, "xyz"]})
        result = scatter_plugin.transform(data, _make_config())

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1  # seule la ligne (1, 10) survit

    def test_transform_samples_when_too_many_points(self, scatter_plugin):
        """L'échantillonnage réduit le nombre de points si > max_points."""
        n = 500
        data = pd.DataFrame({"x": range(n), "y": range(n)})
        config = _make_config(max_points=100)

        result = scatter_plugin.transform(data, config)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 100

    def test_transform_no_sampling_when_under_limit(self, scatter_plugin):
        """Pas d'échantillonnage si le nombre de points est sous la limite."""
        data = pd.DataFrame({"x": range(10), "y": range(10)})
        config = _make_config(max_points=100)

        result = scatter_plugin.transform(data, config)
        assert len(result) == 10

    def test_transform_empty_dataframe(self, scatter_plugin):
        """Un DataFrame vide retourne un DataFrame vide."""
        data = pd.DataFrame({"x": pd.Series(dtype=float), "y": pd.Series(dtype=float)})
        result = scatter_plugin.transform(data, _make_config())

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_transform_all_nan(self, scatter_plugin):
        """Toutes les valeurs NaN retournent un DataFrame vide."""
        data = pd.DataFrame({"x": [np.nan, np.nan], "y": [np.nan, np.nan]})
        result = scatter_plugin.transform(data, _make_config())

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_transform_missing_column_raises(self, scatter_plugin):
        """Une colonne manquante lève une erreur."""
        data = pd.DataFrame({"x": [1, 2], "other": [10, 20]})

        with pytest.raises(ValueError, match="Colonne 'y' absente"):
            scatter_plugin.transform(data, _make_config())

    def test_transform_sampling_is_reproducible(self, scatter_plugin):
        """L'échantillonnage avec random_state est reproductible."""
        data = pd.DataFrame({"x": range(500), "y": range(500)})
        config = _make_config(max_points=100)

        result1 = scatter_plugin.transform(data.copy(), config)
        result2 = scatter_plugin.transform(data.copy(), config)

        pd.testing.assert_frame_equal(result1.reset_index(drop=True), result2.reset_index(drop=True))

    def test_transform_preserves_numeric_values(self, scatter_plugin):
        """Les valeurs numériques sont préservées correctement."""
        data = pd.DataFrame({"x": [1.5, 2.7, 3.1], "y": [10.2, 20.4, 30.6]})
        result = scatter_plugin.transform(data, _make_config())

        assert result["x"].tolist() == [1.5, 2.7, 3.1]
        assert result["y"].tolist() == [10.2, 20.4, 30.6]
