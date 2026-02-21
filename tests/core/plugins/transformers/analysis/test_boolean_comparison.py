"""Tests pour le plugin BooleanComparison."""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock

from niamoto.core.plugins.transformers.analysis.boolean_comparison import (
    BooleanComparison,
)


@pytest.fixture
def boolean_plugin():
    """Fixture pour une instance BooleanComparison."""
    return BooleanComparison(db=MagicMock())


def _make_config(fields=None, true_label="Oui", false_label="Non"):
    return {
        "plugin": "boolean_comparison",
        "params": {
            "source": "occurrences",
            "fields": fields or ["a", "b"],
            "true_label": true_label,
            "false_label": false_label,
        },
    }


class TestBooleanComparisonValidation:
    """Tests de validation de la configuration."""

    def test_validate_config_valid(self, boolean_plugin):
        """Configuration valide ne lève pas d'erreur."""
        boolean_plugin.validate_config(_make_config())

    def test_validate_config_missing_fields(self, boolean_plugin):
        """Configuration sans fields lève une erreur."""
        config = {
            "plugin": "boolean_comparison",
            "params": {"source": "occurrences"},
        }
        with pytest.raises(ValueError, match="Configuration invalide"):
            boolean_plugin.validate_config(config)

    def test_validate_config_empty_fields(self, boolean_plugin):
        """Configuration avec fields vide lève une erreur."""
        config = {
            "plugin": "boolean_comparison",
            "params": {"source": "occurrences", "fields": []},
        }
        with pytest.raises(ValueError, match="Configuration invalide"):
            boolean_plugin.validate_config(config)


class TestBooleanComparisonTransform:
    """Tests de la méthode transform."""

    def test_transform_returns_dataframe(self, boolean_plugin):
        """Le résultat est un DataFrame avec les colonnes category, count, label."""
        data = pd.DataFrame({"a": [1, 0, 1], "b": [0, 0, 1]})
        result = boolean_plugin.transform(data, _make_config(fields=["a", "b"]))

        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ["category", "count", "label"]

    def test_transform_basic_numeric(self, boolean_plugin):
        """Transformation basique avec des valeurs 0/1."""
        data = pd.DataFrame({"a": [1, 0, 1, 1], "b": [0, 0, 1, 0]})
        result = boolean_plugin.transform(data, _make_config(fields=["a", "b"]))

        # 4 lignes : (a, Oui), (a, Non), (b, Oui), (b, Non)
        assert len(result) == 4
        a_oui = result[(result["category"] == "a") & (result["label"] == "Oui")]
        a_non = result[(result["category"] == "a") & (result["label"] == "Non")]
        b_oui = result[(result["category"] == "b") & (result["label"] == "Oui")]
        b_non = result[(result["category"] == "b") & (result["label"] == "Non")]
        assert a_oui["count"].iloc[0] == 3
        assert a_non["count"].iloc[0] == 1
        assert b_oui["count"].iloc[0] == 1
        assert b_non["count"].iloc[0] == 3

    def test_transform_boolean_dtype(self, boolean_plugin):
        """Transformation avec des vrais booléens Python."""
        data = pd.DataFrame(
            {"flag_a": [True, False, True], "flag_b": [False, False, True]}
        )
        result = boolean_plugin.transform(
            data, _make_config(fields=["flag_a", "flag_b"])
        )

        assert len(result) == 4
        fa_oui = result[(result["category"] == "flag_a") & (result["label"] == "Oui")]
        fb_non = result[(result["category"] == "flag_b") & (result["label"] == "Non")]
        assert fa_oui["count"].iloc[0] == 2
        assert fb_non["count"].iloc[0] == 2

    def test_transform_custom_labels(self, boolean_plugin):
        """Les labels personnalisés sont utilisés dans la colonne label."""
        data = pd.DataFrame({"x": [1, 0, 1]})
        result = boolean_plugin.transform(
            data, _make_config(fields=["x"], true_label="Actif", false_label="Inactif")
        )

        labels = result["label"].unique().tolist()
        assert "Actif" in labels
        assert "Inactif" in labels

    def test_transform_with_nan(self, boolean_plugin):
        """Les NaN sont ignorés dans le comptage."""
        data = pd.DataFrame({"a": [1, 0, np.nan, 1, np.nan]})
        result = boolean_plugin.transform(data, _make_config(fields=["a"]))

        # 3 valeurs non-NaN : 2 true, 1 false
        a_oui = result[(result["category"] == "a") & (result["label"] == "Oui")]
        a_non = result[(result["category"] == "a") & (result["label"] == "Non")]
        assert a_oui["count"].iloc[0] == 2
        assert a_non["count"].iloc[0] == 1

    def test_transform_missing_column_skipped(self, boolean_plugin):
        """Les colonnes absentes sont ignorées sans erreur."""
        data = pd.DataFrame({"a": [1, 0, 1]})
        result = boolean_plugin.transform(
            data, _make_config(fields=["a", "inexistant"])
        )

        # Seule "a" produit des lignes
        assert result["category"].unique().tolist() == ["a"]
        assert len(result) == 2

    def test_transform_empty_dataframe(self, boolean_plugin):
        """Un DataFrame vide avec colonne existante retourne 0/0."""
        data = pd.DataFrame({"a": pd.Series(dtype=float)})
        result = boolean_plugin.transform(data, _make_config(fields=["a"]))

        # La colonne existe mais est vide → dropna() vide → 0 true, 0 false
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert result["count"].sum() == 0

    def test_transform_all_true(self, boolean_plugin):
        """Toutes les valeurs à True."""
        data = pd.DataFrame({"a": [1, 1, 1, 1]})
        result = boolean_plugin.transform(data, _make_config(fields=["a"]))

        a_oui = result[(result["category"] == "a") & (result["label"] == "Oui")]
        a_non = result[(result["category"] == "a") & (result["label"] == "Non")]
        assert a_oui["count"].iloc[0] == 4
        assert a_non["count"].iloc[0] == 0

    def test_transform_all_false(self, boolean_plugin):
        """Toutes les valeurs à False."""
        data = pd.DataFrame({"a": [0, 0, 0]})
        result = boolean_plugin.transform(data, _make_config(fields=["a"]))

        a_oui = result[(result["category"] == "a") & (result["label"] == "Oui")]
        a_non = result[(result["category"] == "a") & (result["label"] == "Non")]
        assert a_oui["count"].iloc[0] == 0
        assert a_non["count"].iloc[0] == 3

    def test_transform_multiple_fields(self, boolean_plugin):
        """Trois champs booléens comparés ensemble."""
        data = pd.DataFrame({"f1": [1, 1, 0], "f2": [0, 0, 0], "f3": [1, 1, 1]})
        result = boolean_plugin.transform(data, _make_config(fields=["f1", "f2", "f3"]))

        # 6 lignes : 2 par champ (Oui + Non)
        assert len(result) == 6
        f1_oui = result[(result["category"] == "f1") & (result["label"] == "Oui")]
        f2_oui = result[(result["category"] == "f2") & (result["label"] == "Oui")]
        f3_non = result[(result["category"] == "f3") & (result["label"] == "Non")]
        assert f1_oui["count"].iloc[0] == 2
        assert f2_oui["count"].iloc[0] == 0
        assert f3_non["count"].iloc[0] == 0

    def test_transform_non_binary_numeric_treated_as_false(self, boolean_plugin):
        """Les valeurs numériques != 0 et != 1 sont comptées comme false."""
        data = pd.DataFrame({"a": [1, 0, 2, 3, 1]})
        result = boolean_plugin.transform(data, _make_config(fields=["a"]))

        # pd.to_numeric → 5 valeurs, (==1) → 2 true, reste → 3 false
        a_oui = result[(result["category"] == "a") & (result["label"] == "Oui")]
        a_non = result[(result["category"] == "a") & (result["label"] == "Non")]
        assert a_oui["count"].iloc[0] == 2
        assert a_non["count"].iloc[0] == 3

    def test_transform_bar_plot_compatible(self, boolean_plugin):
        """Le DataFrame est directement utilisable par bar_plot avec les bons axes."""
        data = pd.DataFrame({"a": [1, 0], "b": [1, 1]})
        result = boolean_plugin.transform(data, _make_config(fields=["a", "b"]))

        # Vérifier que le DataFrame a la structure attendue par bar_plot
        # x_axis="category", y_axis="count", color_field="label"
        assert "category" in result.columns
        assert "count" in result.columns
        assert "label" in result.columns
        assert result["count"].dtype in [np.int64, np.int32, int, np.intp]
