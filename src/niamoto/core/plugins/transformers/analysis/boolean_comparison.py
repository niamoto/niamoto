"""
Plugin pour la comparaison de champs booléens.

Retourne un DataFrame en format long (category, count, label),
directement consommable par bar_plot groupé.
"""

from typing import Any, Dict, List, Union

import pandas as pd
from pydantic import Field, field_validator

from niamoto.core.plugins.base import PluginType, TransformerPlugin, register
from niamoto.core.plugins.models import BasePluginParams, PluginConfig
from niamoto.core.imports.registry import EntityRegistry


class BooleanComparisonParams(BasePluginParams):
    """Paramètres pour le plugin boolean_comparison."""

    source: str = Field(
        default="occurrences",
        description="Nom de l'entité source",
        json_schema_extra={
            "ui:widget": "entity-select",
        },
    )

    fields: List[str] = Field(
        ...,
        description="Liste des champs booléens à comparer",
        min_length=1,
        json_schema_extra={
            "ui:widget": "array",
            "ui:item-widget": "field-select",
            "ui:depends": "source",
        },
    )

    true_label: str = Field(
        default="Oui",
        description="Label pour les valeurs vraies",
        json_schema_extra={"ui:widget": "text"},
    )

    false_label: str = Field(
        default="Non",
        description="Label pour les valeurs fausses",
        json_schema_extra={"ui:widget": "text"},
    )


class BooleanComparisonConfig(PluginConfig):
    """Configuration pour le plugin boolean_comparison."""

    plugin: str = "boolean_comparison"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "source": "",
            "fields": [],
            "true_label": "Oui",
            "false_label": "Non",
        },
        description="Paramètres pour la comparaison booléenne",
    )

    @field_validator("params")
    @classmethod
    def validate_params(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Valide les paramètres via le modèle typé."""
        BooleanComparisonParams(**v)
        return v


@register("boolean_comparison", PluginType.TRANSFORMER)
class BooleanComparison(TransformerPlugin):
    """Plugin de comparaison de champs booléens."""

    config_model = BooleanComparisonConfig
    param_schema = BooleanComparisonParams

    output_structure = {
        "_type": "dataframe",
        "columns": ["category", "count", "label"],
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
            BooleanComparisonParams(**validated_config.params)
        except Exception as e:
            raise ValueError(f"Configuration invalide : {e}")

    def transform(
        self, data: pd.DataFrame, config: Dict[str, Any]
    ) -> Union[pd.DataFrame, Dict[str, Any]]:
        """Compte True/False par champ booléen, retourne un DataFrame long pour bar_plot."""
        try:
            validated_config = self.config_model(**config)
            params = BooleanComparisonParams(**validated_config.params)

            rows: List[Dict[str, Any]] = []

            for field_name in params.fields:
                if field_name not in data.columns:
                    continue

                col = data[field_name].dropna()

                # Gérer booléens et numériques (0/1)
                if col.dtype == bool:
                    true_count = int(col.sum())
                else:
                    col = pd.to_numeric(col, errors="coerce").dropna()
                    true_count = int((col == 1).sum())

                false_count = len(col) - true_count

                rows.append(
                    {"category": field_name, "count": true_count, "label": params.true_label}
                )
                rows.append(
                    {"category": field_name, "count": false_count, "label": params.false_label}
                )

            return pd.DataFrame(rows, columns=["category", "count", "label"])

        except Exception as e:
            raise ValueError(f"Erreur boolean_comparison : {e}")
