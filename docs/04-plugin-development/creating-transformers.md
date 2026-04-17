# Guide de développement de plugins

Ce guide explique comment créer des plugins pour la plateforme Niamoto. Les plugins permettent d'étendre les fonctionnalités sans modifier le code principal.

## Table des matières

- [Prérequis](#prérequis)
- [Structure des fichiers](#structure-des-fichiers)
- [Créer un plugin Transformer](#créer-un-plugin-transformer)
  - [Étape 1 : Définir le modèle de paramètres](#étape-1--définir-le-modèle-de-paramètres)
  - [Étape 2 : Définir le modèle de configuration](#étape-2--définir-le-modèle-de-configuration)
  - [Étape 3 : Implémenter la classe du plugin](#étape-3--implémenter-la-classe-du-plugin)
  - [Étape 4 : Configurer en YAML](#étape-4--configurer-en-yaml)
- [Modèles de configuration en détail](#modèles-de-configuration-en-détail)
  - [BasePluginParams — paramètres typés](#basepluginparams--paramètres-typés)
  - [PluginConfig — enveloppe YAML](#pluginconfig--enveloppe-yaml)
  - [param_schema vs config_model](#param_schema-vs-config_model)
- [Indices GUI (json_schema_extra)](#indices-gui-json_schema_extra)
- [Sujets avancés](#sujets-avancés)
  - [Chaînes de plugins](#chaînes-de-plugins)
  - [Gestion des erreurs](#gestion-des-erreurs)
  - [Tester un plugin](#tester-un-plugin)

## Prérequis

1. Une installation Niamoto fonctionnelle
2. Connaissance de Python et Pydantic v2
3. Familiarité avec les fichiers YAML (`transform.yml`, `export.yml`)
4. Connaissance des données à traiter

## Structure des fichiers

Les plugins personnalisés se placent dans le répertoire `plugins/` du projet :

```bash
project/
  plugins/
    transformers/
      my_transformer.py
    loaders/
      my_loader.py
    exporters/
      my_exporter.py
    widgets/
      my_widget.py
```

Les plugins internes sont dans `src/niamoto/core/plugins/transformers/`.

## Créer un plugin Transformer

### Étape 1 : Définir le modèle de paramètres

Le modèle de paramètres hérite de `BasePluginParams` et déclare chaque paramètre avec un type, une valeur par défaut, une description, et des indices pour le GUI :

```python
# plugins/transformers/threshold_analysis.py
from typing import List, Literal, Optional, Union
from pydantic import Field, field_validator
from niamoto.core.plugins.models import BasePluginParams


class ThresholdAnalysisParams(BasePluginParams):
    """Parametres types pour le plugin threshold_analysis."""

    source: str = Field(
        default="occurrences",
        description="Entite source des donnees",
        json_schema_extra={"ui:widget": "entity-select"},
    )

    field: str = Field(
        ...,  # requis, pas de valeur par defaut
        description="Champ numerique a analyser",
        json_schema_extra={
            "examples": ["dbh", "height", "elevation"],
            "ui_component": "field_selector",
        },
    )

    threshold: float = Field(
        default=0.5,
        ge=0,
        description="Seuil de comparaison",
        json_schema_extra={
            "ui_component": "number",
            "ui:quick_edit": True,
        },
    )

    stats: List[Literal["count", "percent", "mean"]] = Field(
        default=["count", "percent"],
        description="Statistiques a calculer",
        json_schema_extra={
            "ui_component": "multi_select",
            "ui_options": [
                {"value": "count", "label": "Nombre au-dessus"},
                {"value": "percent", "label": "Pourcentage"},
                {"value": "mean", "label": "Moyenne au-dessus"},
            ],
        },
    )

    units: str = Field(
        default="",
        description="Unite de mesure",
        json_schema_extra={"ui:widget": "text", "ui:quick_edit": True},
    )

    @field_validator("threshold")
    @classmethod
    def validate_threshold_positive(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Le seuil doit etre positif")
        return v
```

Points importants :

- **`BasePluginParams`** a `extra="allow"` — les champs supplémentaires dans le YAML sont acceptés
- **`Field(...)`** (sans valeur) rend le champ requis
- **`Field(default=...)`** définit une valeur par défaut
- **`ge=0`**, **`min_length=2`** etc. ajoutent des contraintes Pydantic natives
- **`json_schema_extra`** fournit des indices au GUI (voir [section dédiée](#indices-gui-json_schema_extra))

### Étape 2 : Définir le modèle de configuration

Le `PluginConfig` est l'enveloppe qui correspond à la structure YAML (`plugin` + `params`) :

```python
from typing import Dict, Any
from pydantic import Field, field_validator
from niamoto.core.plugins.models import PluginConfig


class ThresholdAnalysisConfig(PluginConfig):
    """Configuration YAML pour threshold_analysis."""

    plugin: str = "threshold_analysis"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "source": "occurrences",
            "field": "",
            "threshold": 0.5,
        },
    )

    @field_validator("params")
    @classmethod
    def validate_params(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Valide params via le modele type."""
        ThresholdAnalysisParams(**v)
        return v
```

Le validateur `validate_params` instancie `ThresholdAnalysisParams` pour bénéficier de toutes les validations Pydantic avant de stocker les params en dict.

### Étape 3 : Implémenter la classe du plugin

```python
import pandas as pd
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
from niamoto.core.imports.registry import EntityRegistry


@register("threshold_analysis", PluginType.TRANSFORMER)
class ThresholdAnalysis(TransformerPlugin):
    """Plugin d'analyse par seuil."""

    config_model = ThresholdAnalysisConfig
    param_schema = ThresholdAnalysisParams  # Expose les parametres types au GUI

    # Structure de sortie (pour pattern matching et suggestions)
    output_structure = {
        "threshold": "float",
        "count_above": "int",
        "percent_above": "float",
        "mean_above": "float",
        "units": "str",
    }

    def __init__(self, db, registry=None):
        super().__init__(db)
        self.registry = registry or EntityRegistry(db)

    def validate_config(self, config):
        """Valide la configuration."""
        validated = self.config_model(**config)
        ThresholdAnalysisParams(**validated.params)

    def transform(self, data: pd.DataFrame, config: dict) -> dict:
        """Transforme les donnees selon la configuration."""
        validated = self.config_model(**config)
        params = ThresholdAnalysisParams(**validated.params)

        # Acces type aux parametres (pas de .get() ni de cast)
        field_data = data[params.field].dropna()

        if field_data.empty:
            return {"threshold": params.threshold, "count_above": 0}

        above = field_data[field_data > params.threshold]
        result = {"threshold": params.threshold, "units": params.units}

        if "count" in params.stats:
            result["count_above"] = len(above)
        if "percent" in params.stats:
            total = len(field_data)
            result["percent_above"] = round((len(above) / total) * 100, 2) if total else 0
        if "mean" in params.stats:
            result["mean_above"] = round(float(above.mean()), 2) if not above.empty else None

        return result
```

Points importants :

- **`config_model`** : valide la structure YAML globale (`plugin` + `params`)
- **`param_schema`** : expose les champs typés au GUI pour générer les formulaires
- **`output_structure`** : déclare la structure de sortie pour le pattern matching
- **`params.field`** : accès typé direct, pas de `params.get("field")` ni de cast manuel
- Le service se charge de charger les données — le transformer est une fonction pure

### Étape 4 : Configurer en YAML

```yaml
# config/transform.yml
- group_by: taxon
  widgets_data:
    threshold_analysis:
      plugin: threshold_analysis
      params:
        source: occurrences
        field: dbh
        threshold: 30.0
        stats: [count, percent]
        units: cm
```

## Modèles de configuration en détail

### BasePluginParams — paramètres typés

Classe de base pour les paramètres de tous les plugins. Hérite de `BaseModel` avec `extra="allow"`.

```python
from pydantic import BaseModel, ConfigDict

class BasePluginParams(BaseModel):
    model_config = ConfigDict(extra="allow")
```

`extra="allow"` signifie que les champs non déclarés dans le modèle sont acceptés sans erreur. C'est utile pour la rétrocompatibilité quand de nouveaux paramètres sont ajoutés au YAML.

Pour un plugin strict, surcharger dans la sous-classe :

```python
class StrictParams(BasePluginParams):
    model_config = ConfigDict(extra="forbid")  # Rejette les champs inconnus
    field: str = Field(...)
```

### PluginConfig — enveloppe YAML

Représente la structure YAML complète d'un widget dans `transform.yml` :

```python
class PluginConfig(BaseModel):
    plugin: str = Field(..., description="Nom du plugin enregistre")
    source: Optional[str] = Field(None)
    params: Dict[str, Any] = Field(default_factory=dict)
```

### param_schema vs config_model

Chaque plugin définit deux attributs de classe :

| Attribut | Type | Rôle |
|----------|------|------|
| `config_model` | `PluginConfig` subclass | Valide la structure YAML (`plugin` + `params` dict) |
| `param_schema` | `BasePluginParams` subclass | Expose les paramètres typés avec leur schéma JSON |

Le GUI utilise `param_schema` pour :
- Générer les formulaires automatiquement (`param_schema.model_json_schema()`)
- Détecter les types de champs (texte, nombre, checkbox, select...)
- Afficher les descriptions et exemples
- Appliquer les widgets spécifiques (`entity-select`, `layer-select`, `tags`...)

Le backend utilise `config_model` pour valider le YAML au chargement et `param_schema` pour la validation fine dans `transform()`.

## Indices GUI (json_schema_extra)

Le `json_schema_extra` de chaque `Field` contrôle le rendu dans le GUI :

### Widgets de formulaire

| Valeur `ui:widget` | Composant GUI | Utilisation |
|---------------------|---------------|-------------|
| `text` | Champ texte | Titres, labels, unités |
| `number` | Champ numérique | Bornes, seuils |
| `checkbox` | Case à cocher | Booléens |
| `select` | Liste déroulante | Valeurs enum |
| `entity-select` | Sélecteur d'entité | Sources de données |
| `transform-source-select` | Sélecteur de source | Sources configurées |
| `layer-select` | Sélecteur de layer | Fichiers raster/vector |
| `tags` | Liste de tags | Catégories, statistiques |
| `key-value-pairs` | Paires clé-valeur | Mappings |
| `json` | Éditeur JSON | Structures complexes |
| `array` | Liste éditable | Champs répétés |

### Autres indices

```python
json_schema_extra={
    "ui:widget": "text",        # Type de composant
    "ui:quick_edit": True,      # Apparait dans l'edition rapide
    "ui:placeholder": "...",    # Placeholder du champ
    "ui:help": "...",           # Texte d'aide sous le champ
    "ui_options": [...],        # Options pour multi_select
    "examples": [...],          # Exemples de valeurs
}
```

### Exemple réel : raster_stats

```python
class RasterStatsParams(BasePluginParams):
    raster_path: str = Field(
        ...,
        description="Chemin du fichier raster (.tif)",
        json_schema_extra={
            "ui:widget": "layer-select",
            "ui:layer_type": "raster",
        },
    )

    stats: List[str] = Field(
        default=["min", "max", "mean"],
        json_schema_extra={
            "ui:widget": "tags",
            "ui:allowed_values": ["min", "max", "mean", "median", "sum", "count", "std"],
        },
    )

    units: str = Field(
        default="",
        json_schema_extra={"ui:widget": "text", "ui:quick_edit": True},
    )
```

Le GUI génère automatiquement :
- Un sélecteur de fichier filtré sur `.tif` pour `raster_path`
- Un champ de tags avec auto-complétion pour `stats`
- Un champ texte inline pour `units`

## Sujets avancés

### Chaînes de plugins

Pour des analyses complexes, chaînage de transformations via `transform_chain` :

```yaml
phenology:
  plugin: "transform_chain"
  params:
    steps:
      - plugin: "time_series_analysis"
        params:
          source: occurrences
          fields:
            fleur: flower
            fruit: fruit
          time_field: month_obs
        output_key: "phenology_raw"

      - plugin: "threshold_analysis"
        params:
          operation: "peak_detection"
          time_series: "@phenology_raw.month_data"
        output_key: "phenology_peaks"
```

La syntaxe `@step.field` référence la sortie d'une étape précédente.

### Gestion des erreurs

Utiliser les exceptions Niamoto pour des messages cohérents :

```python
from niamoto.common.exceptions import DataTransformError

def transform(self, data, config):
    try:
        validated = self.config_model(**config)
        params = ThresholdAnalysisParams(**validated.params)
        # ... logique du plugin
    except ValueError as e:
        raise DataTransformError(
            f"Erreur de configuration : {e}",
            details={"config": config},
        )
    except KeyError as e:
        raise DataTransformError(
            f"Champ manquant dans les donnees : {e}",
            details={"plugin": "threshold_analysis"},
        )
```

### Tester un plugin

```python
import pytest
import pandas as pd
from niamoto.core.plugins.registry import PluginRegistry
from niamoto.core.plugins.base import PluginType


def test_threshold_analysis():
    plugin_class = PluginRegistry.get_plugin(
        "threshold_analysis", PluginType.TRANSFORMER
    )
    plugin = plugin_class(db=None)

    data = pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "dbh": [10.5, 25.3, 32.1, 18.7, 45.9],
    })

    config = {
        "plugin": "threshold_analysis",
        "params": {
            "field": "dbh",
            "threshold": 30.0,
            "stats": ["count", "percent"],
        },
    }

    result = plugin.transform(data, config)

    assert result["count_above"] == 2
    assert result["percent_above"] == 40.0
    assert result["threshold"] == 30.0


def test_threshold_analysis_params_validation():
    """Teste que la validation Pydantic fonctionne."""
    from plugins.transformers.threshold_analysis import ThresholdAnalysisParams

    # Valide
    params = ThresholdAnalysisParams(field="dbh", threshold=30.0)
    assert params.source == "occurrences"  # valeur par defaut

    # Invalide : champ requis manquant
    with pytest.raises(Exception):
        ThresholdAnalysisParams(threshold=10.0)  # field est requis

    # Invalide : seuil negatif
    with pytest.raises(Exception):
        ThresholdAnalysisParams(field="dbh", threshold=-1.0)
```

Run the relevant transformer tests:

```bash
uv run pytest tests/core/plugins/transformers/ -v
```
