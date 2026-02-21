"""
Plugin pour l'analyse de dispersion entre deux champs numériques.

Retourne un DataFrame avec les deux colonnes, prêt pour le widget scatter_plot.
"""

from typing import Any, Dict, Union

import pandas as pd
from pydantic import Field, field_validator

from niamoto.core.plugins.base import PluginType, TransformerPlugin, register
from niamoto.core.plugins.models import BasePluginParams, PluginConfig
from niamoto.core.imports.registry import EntityRegistry


class ScatterAnalysisParams(BasePluginParams):
    """Paramètres pour le plugin scatter_analysis."""

    source: str = Field(
        default="occurrences",
        description="Nom de l'entité source",
        json_schema_extra={
            "ui:widget": "entity-select",
        },
    )

    x_field: str = Field(
        ...,
        description="Champ numérique pour l'axe X",
        json_schema_extra={
            "ui:widget": "field-select",
            "ui:depends": "source",
        },
    )

    y_field: str = Field(
        ...,
        description="Champ numérique pour l'axe Y",
        json_schema_extra={
            "ui:widget": "field-select",
            "ui:depends": "source",
        },
    )

    max_points: int = Field(
        default=5000,
        description="Nombre maximum de points (échantillonnage aléatoire si dépassé)",
        ge=100,
        le=50000,
        json_schema_extra={
            "ui:widget": "number",
            "ui:step": 500,
        },
    )


class ScatterAnalysisConfig(PluginConfig):
    """Configuration pour le plugin scatter_analysis."""

    plugin: str = "scatter_analysis"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "source": "",
            "x_field": "",
            "y_field": "",
            "max_points": 5000,
        },
        description="Paramètres pour l'analyse de dispersion",
    )

    @field_validator("params")
    @classmethod
    def validate_params(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Valide les paramètres via le modèle typé."""
        ScatterAnalysisParams(**v)
        return v


@register("scatter_analysis", PluginType.TRANSFORMER)
class ScatterAnalysis(TransformerPlugin):
    """Plugin d'analyse de dispersion entre deux champs numériques."""

    config_model = ScatterAnalysisConfig
    param_schema = ScatterAnalysisParams

    output_structure = {
        "_type": "dataframe",
        "columns": ["x_field", "y_field"],
    }

    def __init__(self, db, registry=None):
        """Initialise avec la base de données et un EntityRegistry optionnel."""
        super().__init__(db)
        self.registry = registry or EntityRegistry(db)

    def _resolve_table_name(self, logical_name: str) -> str:
        """Résout le nom logique en nom physique de table."""
        try:
            metadata = self.registry.get(logical_name)
            return metadata.table_name
        except Exception:
            return logical_name

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Valide la configuration."""
        try:
            validated_config = self.config_model(**config)
            ScatterAnalysisParams(**validated_config.params)
        except Exception as e:
            raise ValueError(f"Configuration invalide : {e}")

    def transform(
        self, data: pd.DataFrame, config: Dict[str, Any]
    ) -> Union[pd.DataFrame, Dict[str, Any]]:
        """Extrait deux colonnes numériques et retourne un DataFrame pour scatter_plot."""
        try:
            validated_config = self.config_model(**config)
            params = ScatterAnalysisParams(**validated_config.params)

            for col in (params.x_field, params.y_field):
                if col not in data.columns:
                    raise ValueError(f"Colonne '{col}' absente du DataFrame")

            # Extraire et convertir en numérique
            df = data[[params.x_field, params.y_field]].copy()
            df[params.x_field] = pd.to_numeric(df[params.x_field], errors="coerce")
            df[params.y_field] = pd.to_numeric(df[params.y_field], errors="coerce")
            df = df.dropna()

            if df.empty:
                return df

            # Échantillonner si trop de points
            if len(df) > params.max_points:
                df = df.sample(n=params.max_points, random_state=42)

            return df

        except Exception as e:
            raise ValueError(f"Erreur scatter_analysis : {e}")
