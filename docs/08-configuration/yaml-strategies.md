# Stratégies de Simplification du Système YAML Actuel

## Introduction

Vous avez raison : votre système actuel a des **avantages importants** qu'il faut préserver :
- ✅ Accessible aux non-codeurs (écologistes, botanistes)
- ✅ Chaque transformation est simple isolément
- ✅ Déclaratif et compréhensible
- ✅ Pas de code = moins de bugs

Le problème n'est pas l'architecture mais la **duplication** et le **volume**. Voici des stratégies concrètes pour simplifier **sans tout casser**.

## 1. Templates et Presets YAML

### Problème Actuel
```yaml
# Répété 15+ fois avec variations minimes
- plugin: radial_gauge
  data_source: height_max
  title: "Hauteur maximale"
  params:
    value_field: max
    min_value: 0
    max_value: 40
    units: "m"
    style_mode: "contextual"
    show_axis: false

- plugin: radial_gauge
  data_source: dbh_max
  title: "Diamètre maximal"
  params:
    value_field: max
    min_value: 0
    max_value: 500
    units: "cm"
    style_mode: "contextual"
    show_axis: false
# ... encore 13 fois
```

### Solution : Système de Templates

#### Étape 1 : Créer des templates prédéfinis
```yaml
# config/templates/widgets.yml
templates:
  # Template pour jauge standard
  standard_gauge:
    plugin: radial_gauge
    params:
      value_field: value
      min_value: 0
      style_mode: "contextual"
      show_axis: false
      value_format: ".1f"

  # Template pour distribution
  standard_distribution:
    plugin: bar_plot
    params:
      transform: "bins_to_df"
      transform_params:
        use_percentages: true
      orientation: v
      show_legend: false
      filter_zero_values: true
      gradient_mode: "luminance"

  # Template pour top ranking
  top_species_template:
    plugin: bar_plot
    params:
      orientation: h
      sort_order: "descending"
      auto_color: true
      labels:
        x_axis: "Nombre d'occurrences"
```

#### Étape 2 : Utiliser les templates avec overrides minimaux
```yaml
# export.yml simplifié
widgets:
  # Utilise le template avec seulement les différences
  - use: standard_gauge
    data_source: height_max
    title: "Hauteur maximale"
    params:
      max_value: 40
      units: "m"

  - use: standard_gauge
    data_source: dbh_max
    title: "Diamètre maximal"
    params:
      max_value: 500
      units: "cm"

  # 3 lignes au lieu de 10+ !
```

### Implémentation Python
```python
# src/niamoto/config/template_loader.py
import yaml
from typing import Dict, Any

class TemplateLoader:
    """Charge et fusionne les templates YAML"""

    def __init__(self):
        with open('config/templates/widgets.yml') as f:
            self.templates = yaml.safe_load(f)['templates']

    def resolve_config(self, widget_config: Dict[str, Any]) -> Dict[str, Any]:
        """Résout une config en fusionnant avec le template"""

        if 'use' in widget_config:
            # Charge le template
            template_name = widget_config.pop('use')
            template = self.templates.get(template_name, {}).copy()

            # Fusionne avec les overrides
            return self.deep_merge(template, widget_config)

        return widget_config

    def deep_merge(self, base: dict, override: dict) -> dict:
        """Fusion récursive de dictionnaires"""
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self.deep_merge(result[key], value)
            else:
                result[key] = value

        return result
```

## 2. Presets par Type d'Entité

### Structure de Presets
```yaml
# config/presets/taxon.yml
taxon_widgets:
  # Preset complet pour un taxon standard
  standard:
    - general_info  # Référence à un widget prédéfini
    - distribution_map
    - top_species
    - dbh_distribution
    - phenology
    - elevation_distribution

  # Preset minimal
  minimal:
    - general_info
    - distribution_map

  # Preset pour espèces rares
  rare_species:
    - general_info
    - distribution_map
    - conservation_status
    - threats

# Définitions détaillées
widget_definitions:
  dbh_distribution:
    plugin: binned_distribution
    params:
      source: occurrences
      field: dbh
      bins: [10, 20, 30, 40, 50, 75, 100, 200, 300, 400, 500]
      include_percentages: true
```

### Utilisation Simple
```yaml
# transform.yml ultra-simplifié
- group_by: taxon
  use_preset: standard  # Une ligne !

  # Overrides spécifiques si besoin
  overrides:
    dbh_distribution:
      params:
        bins: [10, 25, 50, 100]  # Bins différents pour ce projet
```

## 3. Système d'Héritage de Configuration

### Configuration par Défaut Globale
```yaml
# config/defaults.yml
defaults:
  # Defaults pour TOUS les widgets radial_gauge
  radial_gauge:
    style_mode: "contextual"
    show_axis: false
    value_format: ".1f"

  # Defaults pour TOUS les bar_plot
  bar_plot:
    orientation: "h"
    show_legend: false
    filter_zero_values: true

  # Defaults par type de données
  distributions:
    include_percentages: true
    gradient_mode: "luminance"
```

### Héritage en Cascade
```yaml
# La config finale est la fusion de :
# 1. Defaults globaux
# 2. Defaults du plugin
# 3. Template utilisé
# 4. Configuration spécifique

widgets:
  - plugin: radial_gauge
    data_source: height_max
    # Hérite automatiquement : style_mode, show_axis, value_format
    # Doit spécifier seulement : max_value, units, title
    params:
      max_value: 40
      units: "m"
```

## 4. Générateur de Configuration avec Interface

### Interface Web pour Non-Codeurs

```python
# src/niamoto/gui/config_builder.py
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class WidgetBuilder:
    """API pour construire des configs visuellement"""

    @app.post("/api/config/widget/create")
    async def create_widget(self, widget_type: str, entity: str):
        """Crée un widget avec assistant"""

        # 1. Propose les templates disponibles
        templates = self.get_templates_for(widget_type, entity)

        # 2. Guide l'utilisateur
        wizard = {
            "steps": [
                {
                    "title": "Choisir un template",
                    "options": templates,
                    "help": "Ces templates sont optimisés pour votre type de données"
                },
                {
                    "title": "Personnaliser",
                    "fields": self.get_required_fields(widget_type),
                    "optional": self.get_optional_fields(widget_type)
                }
            ]
        }

        return wizard

    @app.get("/api/config/preview")
    async def preview_widget(self, config: dict):
        """Prévisualise le widget avant sauvegarde"""

        # Génère un aperçu avec données de test
        preview_data = self.load_sample_data(config['entity'])
        widget_html = self.render_widget(config, preview_data)

        return {"preview": widget_html}
```

### Interface Streamlit Simple
```python
# tools/config_builder.py
import streamlit as st
import yaml

st.title("🌿 Niamoto Config Builder")

# 1. Sélection du type
entity_type = st.selectbox(
    "Type d'entité",
    ["taxon", "plot", "shape"]
)

# 2. Choix du preset
preset = st.selectbox(
    "Partir d'un preset",
    ["standard", "minimal", "custom", "from_existing"]
)

# 3. Configuration des widgets
st.subheader("Widgets")

widgets = []
for i, widget_preset in enumerate(presets[entity_type][preset]):
    with st.expander(f"Widget {i+1}: {widget_preset['name']}"):
        # Formulaire pour personnaliser
        title = st.text_input("Titre", widget_preset.get('title', ''))

        if widget_preset['type'] == 'radial_gauge':
            max_val = st.number_input("Valeur max", value=100)
            units = st.text_input("Unités", value="")

        widgets.append({
            'use': widget_preset['template'],
            'title': title,
            'params': {'max_value': max_val, 'units': units}
        })

# 4. Export
if st.button("Générer Configuration"):
    config = {
        'group_by': entity_type,
        'widgets': widgets
    }

    st.code(yaml.dump(config), language='yaml')

    # Téléchargement
    st.download_button(
        "Télécharger",
        yaml.dump(config),
        f"{entity_type}_config.yml"
    )
```

## 5. Validation et Auto-complétion Améliorées

### JSON Schema pour Validation
```yaml
# config/schemas/widget_schema.yml
$schema: "http://json-schema.org/draft-07/schema#"
definitions:
  radial_gauge:
    type: object
    required: [plugin, data_source, title, params]
    properties:
      plugin:
        const: "radial_gauge"
      data_source:
        type: string
      title:
        type: string
      params:
        type: object
        required: [max_value, units]
        properties:
          max_value:
            type: number
            minimum: 0
          units:
            type: string
          # Props optionnelles avec defaults
          style_mode:
            type: string
            default: "contextual"
            enum: ["contextual", "minimal", "classic"]
```

### Extension VSCode pour Auto-complétion
```json
// .vscode/settings.json
{
  "yaml.schemas": {
    "./config/schemas/widget_schema.yml": ["config/*.yml"],
    "./config/schemas/transform_schema.yml": ["transform.yml"],
    "./config/schemas/export_schema.yml": ["export.yml"]
  },
  "yaml.customTags": [
    "!include",
    "!use",
    "!preset"
  ]
}
```

### Snippets VSCode
```json
// .vscode/niamoto.code-snippets
{
  "Radial Gauge Widget": {
    "prefix": "gauge",
    "body": [
      "- use: standard_gauge",
      "  data_source: ${1:metric_name}",
      "  title: \"${2:Title}\"",
      "  params:",
      "    max_value: ${3:100}",
      "    units: \"${4:unit}\""
    ],
    "description": "Insert a radial gauge widget"
  },

  "Distribution Plot": {
    "prefix": "dist",
    "body": [
      "- use: standard_distribution",
      "  data_source: ${1:field}_distribution",
      "  title: \"${2:Distribution Title}\"",
      "  params:",
      "    field: ${1:field}",
      "    bins: [${3:0, 10, 20, 50, 100}]"
    ]
  }
}
```

## 6. Documentation Automatique

### Générateur de Documentation
```python
# tools/doc_generator.py
class ConfigDocGenerator:
    """Génère une doc HTML de toutes les configs"""

    def generate_docs(self):
        """Génère une documentation navigable"""

        docs = {
            "taxon": self.document_entity_config("taxon"),
            "plot": self.document_entity_config("plot"),
            "shape": self.document_entity_config("shape")
        }

        # Génère un site statique avec MkDocs
        self.generate_mkdocs_site(docs)

    def document_entity_config(self, entity: str):
        """Documente une config d'entité"""

        config = load_config(f"{entity}.yml")

        doc = {
            "entity": entity,
            "widgets": [],
            "transformations": [],
            "exports": []
        }

        for widget in config['widgets']:
            doc['widgets'].append({
                "name": widget['title'],
                "type": widget['plugin'],
                "description": self.get_plugin_description(widget['plugin']),
                "params": widget['params'],
                "preview": self.generate_preview(widget)
            })

        return doc

    def generate_preview(self, widget_config):
        """Génère un aperçu visuel du widget"""

        # Utilise des données de test
        sample_data = self.get_sample_data(widget_config['data_source'])

        # Génère le widget
        plugin = self.load_plugin(widget_config['plugin'])
        preview_html = plugin.render(sample_data, widget_config['params'])

        return preview_html
```

### Documentation Auto-générée
```markdown
# Configuration Niamoto - Taxon

## Widgets Configurés

### 📊 Distribution DBH
**Type**: bar_plot
**Description**: Affiche la distribution des diamètres par classes

**Paramètres**:
- `bins`: [10, 20, 30, 50, 100]
- `units`: cm
- `include_percentages`: true

**Aperçu**:
![Preview](previews/dbh_distribution.png)

**Template utilisé**: `standard_distribution`

---

### 🌡️ Hauteur Maximale
**Type**: radial_gauge
...
```

## 7. Système de Macros YAML

### Macros pour Réduire la Répétition
```yaml
# config/macros.yml
macros:
  # Macro pour créer plusieurs jauges similaires
  create_gauges: !macro
    inputs: [metrics]
    output: |
      {% for metric in metrics %}
      - use: standard_gauge
        data_source: {{ metric.field }}
        title: "{{ metric.title }}"
        params:
          max_value: {{ metric.max }}
          units: "{{ metric.unit }}"
      {% endfor %}

# Utilisation
widgets:
  !create_gauges
    metrics:
      - {field: height_max, title: "Hauteur max", max: 40, unit: "m"}
      - {field: dbh_max, title: "DBH max", max: 500, unit: "cm"}
      - {field: wood_density, title: "Densité", max: 1.2, unit: "g/cm³"}
```

## 8. Convention et Détection Automatique

### Détection par Convention de Nommage
```python
# src/niamoto/config/conventions.py
class ConventionResolver:
    """Résout les configs par convention"""

    CONVENTIONS = {
        # Si le nom finit par _distribution -> bar_plot avec bins
        r'.*_distribution$': {
            'plugin': 'binned_distribution',
            'params': {
                'transform': 'bins_to_df',
                'include_percentages': True
            }
        },

        # Si le nom finit par _max -> radial_gauge
        r'.*_max$': {
            'plugin': 'radial_gauge',
            'params': {
                'value_field': 'max',
                'style_mode': 'contextual'
            }
        },

        # Si le nom commence par top_ -> bar_plot ranking
        r'^top_.*': {
            'plugin': 'bar_plot',
            'params': {
                'orientation': 'h',
                'sort_order': 'descending'
            }
        }
    }

    def resolve(self, widget_name: str, minimal_config: dict) -> dict:
        """Complète une config minimale par convention"""

        for pattern, convention in self.CONVENTIONS.items():
            if re.match(pattern, widget_name):
                # Fusionne convention et config minimale
                return deep_merge(convention, minimal_config)

        return minimal_config
```

### Utilisation Ultra-Minimale
```yaml
# Avec conventions, juste le strict nécessaire
widgets:
  height_max:  # Convention détecte : radial_gauge
    max_value: 40
    units: "m"

  dbh_distribution:  # Convention détecte : binned_distribution
    bins: [10, 20, 30, 50, 100]

  top_species:  # Convention détecte : bar_plot horizontal
    count: 10
```

## 9. Outil de Refactoring Automatique

### Script de Migration
```python
# tools/refactor_config.py
import yaml
import click

@click.command()
@click.option('--input', help='Fichier YAML à refactoriser')
@click.option('--output', help='Fichier de sortie')
def refactor_config(input, output):
    """Refactorise automatiquement une vieille config"""

    with open(input) as f:
        old_config = yaml.safe_load(f)

    refactorer = ConfigRefactorer()

    # 1. Détecte les patterns répétitifs
    patterns = refactorer.detect_patterns(old_config)
    print(f"Trouvé {len(patterns)} patterns répétitifs")

    # 2. Crée des templates
    templates = refactorer.create_templates(patterns)
    print(f"Créé {len(templates)} templates")

    # 3. Réécrit la config avec templates
    new_config = refactorer.apply_templates(old_config, templates)

    # 4. Applique les conventions
    new_config = refactorer.apply_conventions(new_config)

    # Stats
    old_lines = count_lines(old_config)
    new_lines = count_lines(new_config)
    print(f"Réduction : {old_lines} → {new_lines} lignes ({100*(1-new_lines/old_lines):.0f}%)")

    # Sauvegarde
    with open(output, 'w') as f:
        yaml.dump(new_config, f)

class ConfigRefactorer:
    def detect_patterns(self, config):
        """Détecte les structures répétitives"""

        patterns = []
        widgets = config.get('widgets', [])

        # Groupe par plugin type
        by_plugin = {}
        for widget in widgets:
            plugin = widget.get('plugin')
            if plugin not in by_plugin:
                by_plugin[plugin] = []
            by_plugin[plugin].append(widget)

        # Trouve les champs communs
        for plugin, instances in by_plugin.items():
            if len(instances) > 2:  # Pattern si 3+ instances
                common = self.find_common_fields(instances)
                patterns.append({
                    'plugin': plugin,
                    'common': common,
                    'instances': instances
                })

        return patterns
```

## 10. Exemple de Simplification Complète

### Avant : 1600+ lignes
```yaml
# export.yml original
widgets:
  - plugin: radial_gauge
    data_source: height_max
    title: "Hauteur maximale"
    description: "Hauteur maximale atteinte"
    params:
      value_field: max
      min_value: 0
      max_value: 40
      units: "m"
      style_mode: "contextual"
      show_axis: false
  # ... répété 50+ fois avec variations
```

### Après : 200 lignes
```yaml
# export.yml simplifié
defaults: !include defaults.yml
templates: !include templates.yml

taxon:
  preset: standard
  widgets:
    # Conventions + templates = minimal
    height_max: {max: 40, unit: "m"}
    dbh_max: {max: 500, unit: "cm"}

    # Override si nécessaire
    phenology:
      use: time_series
      custom_colors: ["#FFB74D", "#81C784"]
```

## Plan d'Implémentation Progressif

### Phase 1 : Quick Wins (1 semaine)
1. Extraire les valeurs par défaut dans `defaults.yml`
2. Créer 5-10 templates de base
3. Script pour détecter/factoriser les duplications

**Gain estimé : -30% de lignes**

### Phase 2 : Templates et Presets (2-3 semaines)
1. Système complet de templates
2. Presets par type d'entité
3. Loader Python pour résolution

**Gain estimé : -50% de lignes**

### Phase 3 : Outils et Interface (1 mois)
1. Config builder Streamlit
2. Extension VSCode
3. Documentation auto-générée

**Gain estimé : -70% de lignes + meilleure UX**

## Métriques de Succès

| Métrique | Avant | Après Phase 3 |
|----------|-------|---------------|
| Lignes totales | 1600+ | ~400 |
| Temps ajout widget | 10 min | 1 min |
| Erreurs de config | Fréquentes | Rares (validation) |
| Accessibilité non-dev | Difficile | Facile (UI) |
| Documentation | Manuelle | Auto-générée |

## Conclusion

Votre système actuel est **bon conceptuellement**. Les simplifications proposées :

1. **Préservent** l'accessibilité aux non-codeurs
2. **Réduisent** drastiquement la duplication
3. **Gardent** la flexibilité du YAML
4. **Ajoutent** des outils pour faciliter la vie

**Commencez par Phase 1** (templates basiques) pour un gain rapide, puis évoluez progressivement. Pas besoin de tout refaire !
