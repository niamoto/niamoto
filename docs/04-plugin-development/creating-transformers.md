# Guide de developpement de plugins

Ce guide explique comment creer des plugins pour la plateforme Niamoto. Les plugins permettent d'etendre les fonctionnalites sans modifier le code principal.

## Table des matieres

- [Pre-requis](#pre-requis)
- [Structure des fichiers](#structure-des-fichiers)
- [Creer un plugin Transformer](#creer-un-plugin-transformer)
  - [Etape 1 : Definir le modele de parametres](#etape-1--definir-le-modele-de-parametres)
  - [Etape 2 : Definir le modele de configuration](#etape-2--definir-le-modele-de-configuration)
  - [Etape 3 : Implementer la classe du plugin](#etape-3--implementer-la-classe-du-plugin)
  - [Etape 4 : Configurer en YAML](#etape-4--configurer-en-yaml)
- [Modeles de configuration en detail](#modeles-de-configuration-en-detail)
  - [BasePluginParams — parametres types](#basepluginparams--parametres-types)
  - [PluginConfig — enveloppe YAML](#pluginconfig--enveloppe-yaml)
  - [param_schema vs config_model](#param_schema-vs-config_model)
- [Indices GUI (json_schema_extra)](#indices-gui-json_schema_extra)
- [Sujets avances](#sujets-avances)
  - [Chaines de plugins](#chaines-de-plugins)
  - [Gestion des erreurs](#gestion-des-erreurs)
  - [Tester un plugin](#tester-un-plugin)

## Pre-requis

1. Une installation Niamoto fonctionnelle
2. Connaissance de Python et Pydantic v2
3. Familiarite avec les fichiers YAML (`transform.yml`, `export.yml`)
4. Connaissance des donnees a traiter

## Structure des fichiers

Les plugins personnalises se placent dans le repertoire `plugins/` du projet :

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

## Creer un plugin Transformer

### Etape 1 : Definir le modele de parametres

Le modele de parametres herite de `BasePluginParams` et declare chaque parametre avec un type, une valeur par defaut, une description, et des indices pour le GUI :

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

- **`BasePluginParams`** a `extra="allow"` — les champs supplementaires dans le YAML sont acceptes
- **`Field(...)`** (sans valeur) rend le champ requis
- **`Field(default=...)`** definit une valeur par defaut
- **`ge=0`**, **`min_length=2`** etc. ajoutent des contraintes Pydantic natives
- **`json_schema_extra`** fournit des indices au GUI (voir [section dediee](#indices-gui-json_schema_extra))

### Etape 2 : Definir le modele de configuration

Le `PluginConfig` est l'enveloppe qui correspond a la structure YAML (`plugin` + `params`) :

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

Le validateur `validate_params` instancie `ThresholdAnalysisParams` pour beneficier de toutes les validations Pydantic avant de stocker les params en dict.

### Etape 3 : Implementer la classe du plugin

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
- **`param_schema`** : expose les champs types au GUI pour generer les formulaires
- **`output_structure`** : declare la structure de sortie pour le pattern matching
- **`params.field`** : acces type direct, pas de `params.get("field")` ni de cast manuel
- Le service se charge de charger les donnees — le transformer est une fonction pure

### Etape 4 : Configurer en YAML

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

## Modeles de configuration en detail

### BasePluginParams — parametres types

Classe de base pour les parametres de tous les plugins. Herite de `BaseModel` avec `extra="allow"`.

```python
from pydantic import BaseModel, ConfigDict

class BasePluginParams(BaseModel):
    model_config = ConfigDict(extra="allow")
```

`extra="allow"` signifie que les champs non declares dans le modele sont acceptes sans erreur. C'est utile pour la retrocompatibilite quand de nouveaux parametres sont ajoutes au YAML.

Pour un plugin strict, surcharger dans la sous-classe :

```python
class StrictParams(BasePluginParams):
    model_config = ConfigDict(extra="forbid")  # Rejette les champs inconnus
    field: str = Field(...)
```

### PluginConfig — enveloppe YAML

Represente la structure YAML complete d'un widget dans `transform.yml` :

```python
class PluginConfig(BaseModel):
    plugin: str = Field(..., description="Nom du plugin enregistre")
    source: Optional[str] = Field(None)
    params: Dict[str, Any] = Field(default_factory=dict)
```

### param_schema vs config_model

Chaque plugin definit deux attributs de classe :

| Attribut | Type | Role |
|----------|------|------|
| `config_model` | `PluginConfig` subclass | Valide la structure YAML (`plugin` + `params` dict) |
| `param_schema` | `BasePluginParams` subclass | Expose les parametres types avec leur schema JSON |

Le GUI utilise `param_schema` pour :
- Generer les formulaires automatiquement (`param_schema.model_json_schema()`)
- Detecter les types de champs (texte, nombre, checkbox, select...)
- Afficher les descriptions et exemples
- Appliquer les widgets specifiques (`entity-select`, `layer-select`, `tags`...)

Le backend utilise `config_model` pour valider le YAML au chargement et `param_schema` pour la validation fine dans `transform()`.

## Indices GUI (json_schema_extra)

Le `json_schema_extra` de chaque `Field` controle le rendu dans le GUI :

### Widgets de formulaire

| Valeur `ui:widget` | Composant GUI | Utilisation |
|---------------------|---------------|-------------|
| `text` | Champ texte | Titres, labels, unites |
| `number` | Champ numerique | Bornes, seuils |
| `checkbox` | Case a cocher | Booleens |
| `select` | Liste deroulante | Valeurs enum |
| `entity-select` | Selecteur d'entite | Sources de donnees |
| `transform-source-select` | Selecteur de source | Sources configurees |
| `layer-select` | Selecteur de layer | Fichiers raster/vector |
| `tags` | Liste de tags | Categories, statistiques |
| `key-value-pairs` | Paires cle-valeur | Mappings |
| `json` | Editeur JSON | Structures complexes |
| `array` | Liste editable | Champs repetes |

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

### Exemple reel : raster_stats

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

Le GUI genere automatiquement :
- Un selecteur de fichier filtre sur `.tif` pour `raster_path`
- Un champ de tags avec auto-completion pour `stats`
- Un champ texte inline pour `units`

## Sujets avances

### Chaines de plugins

Pour des analyses complexes, chainage de transformations via `transform_chain` :

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

La syntaxe `@step.field` reference la sortie d'une etape precedente.

### Gestion des erreurs

Utiliser les exceptions Niamoto pour des messages coherents :

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

Lancer les tests :

```bash
uv run pytest plugins/tests/ -v
```
