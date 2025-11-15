# Guide de Simplification Rapide - À Faire Cette Semaine

## Exemple Concret : Simplifier export.yml en 3 Étapes

### Étape 1 : Créer un fichier de templates (30 minutes)

```yaml
# config/widget-templates.yml
templates:
  # Template pour toutes les jauges
  gauge_template:
    plugin: radial_gauge
    params:
      value_field: value
      min_value: 0
      style_mode: contextual
      show_axis: false

  # Template pour distributions
  distribution_template:
    plugin: bar_plot
    params:
      transform: bins_to_df
      transform_params:
        use_percentages: true
        x_field: bin
        y_field: count
      orientation: v
      show_legend: false
      filter_zero_values: true
      gradient_mode: luminance
```

### Étape 2 : Modifier le loader Python (2 heures)

```python
# src/niamoto/config/enhanced_loader.py
import yaml
from pathlib import Path

class EnhancedConfigLoader:
    """Loader amélioré avec support des templates"""

    def __init__(self):
        # Charge les templates une fois
        template_path = Path("config/widget-templates.yml")
        if template_path.exists():
            with open(template_path) as f:
                self.templates = yaml.safe_load(f).get('templates', {})
        else:
            self.templates = {}

    def load_config(self, config_path: str) -> dict:
        """Charge une config et résout les templates"""
        with open(config_path) as f:
            config = yaml.safe_load(f)

        # Résout les widgets
        if 'widgets' in config:
            config['widgets'] = self._resolve_widgets(config['widgets'])

        return config

    def _resolve_widgets(self, widgets: list) -> list:
        """Résout les templates dans les widgets"""
        resolved = []

        for widget in widgets:
            if 'template' in widget:
                # Charge le template
                template_name = widget.pop('template')
                if template_name in self.templates:
                    # Fusionne template et overrides
                    resolved_widget = self.templates[template_name].copy()
                    self._deep_merge(resolved_widget, widget)
                    resolved.append(resolved_widget)
                else:
                    # Template non trouvé, garde l'original
                    widget['template'] = template_name
                    resolved.append(widget)
            else:
                resolved.append(widget)

        return resolved

    def _deep_merge(self, base: dict, override: dict):
        """Fusionne override dans base (in-place)"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
```

### Étape 3 : Simplifier export.yml (1 heure)

#### Avant : 50+ lignes par groupe de widgets similaires
```yaml
# Version originale
widgets:
  - plugin: radial_gauge
    data_source: height_max
    title: "Hauteur maximale"
    description: Hauteur maximale atteinte
    params:
      value_field: max
      min_value: 0
      max_value: 40
      units: "m"
      style_mode: "contextual"
      show_axis: false

  - plugin: radial_gauge
    data_source: dbh_max
    title: "Diamètre maximal (DBH)"
    description: Diamètre maximal atteint
    params:
      value_field: max
      min_value: 0
      max_value: 500
      units: "cm"
      style_mode: "contextual"
      show_axis: false

  # ... encore 10 jauges similaires
```

#### Après : 4 lignes par widget
```yaml
# Version simplifiée
widgets:
  - template: gauge_template
    data_source: height_max
    title: "Hauteur maximale"
    params:
      max_value: 40
      units: "m"

  - template: gauge_template
    data_source: dbh_max
    title: "Diamètre maximal (DBH)"
    params:
      max_value: 500
      units: "cm"

  # Réduction de 80% !
```

## Script de Migration Automatique (Bonus : 1 heure)

```python
# tools/migrate_config.py
#!/usr/bin/env python3
"""
Script pour migrer automatiquement vos configs vers le système de templates
Usage: python migrate_config.py export.yml export_new.yml
"""

import yaml
import sys
from collections import Counter

def extract_common_params(widgets_group):
    """Extrait les paramètres communs d'un groupe de widgets"""
    if not widgets_group:
        return {}

    # Trouve les clés présentes dans tous les widgets
    all_params = []
    for widget in widgets_group:
        params = widget.get('params', {})
        all_params.append(frozenset(params.items()))

    # Trouve les paramètres identiques
    common = {}
    first_params = widgets_group[0].get('params', {})

    for key, value in first_params.items():
        if all(widget.get('params', {}).get(key) == value for widget in widgets_group):
            common[key] = value

    return common

def create_template_from_group(plugin_name, widgets):
    """Crée un template à partir d'un groupe de widgets similaires"""
    common_params = extract_common_params(widgets)

    template = {
        'plugin': plugin_name,
        'params': common_params
    }

    return template

def migrate_config(input_file, output_file):
    """Migre une config vers le système de templates"""

    # Charge la config originale
    with open(input_file) as f:
        config = yaml.safe_load(f)

    # Groupe les widgets par plugin
    widgets_by_plugin = {}
    for widget in config.get('widgets', []):
        plugin = widget.get('plugin')
        if plugin:
            if plugin not in widgets_by_plugin:
                widgets_by_plugin[plugin] = []
            widgets_by_plugin[plugin].append(widget)

    # Crée les templates
    templates = {}
    new_widgets = []

    for plugin, widgets in widgets_by_plugin.items():
        if len(widgets) >= 3:  # Crée un template si 3+ widgets similaires
            template_name = f"{plugin}_template"
            templates[template_name] = create_template_from_group(plugin, widgets)

            # Réécrit les widgets pour utiliser le template
            for widget in widgets:
                new_widget = {
                    'template': template_name,
                    'data_source': widget.get('data_source'),
                    'title': widget.get('title')
                }

                # Garde seulement les params différents du template
                if 'params' in widget:
                    diff_params = {}
                    for key, value in widget['params'].items():
                        if templates[template_name]['params'].get(key) != value:
                            diff_params[key] = value
                    if diff_params:
                        new_widget['params'] = diff_params

                new_widgets.append(new_widget)
        else:
            # Garde tel quel si pas assez pour un template
            new_widgets.extend(widgets)

    # Crée la nouvelle config
    new_config = config.copy()
    new_config['widgets'] = new_widgets

    # Sauve les templates
    with open('config/widget-templates.yml', 'w') as f:
        yaml.dump({'templates': templates}, f, default_flow_style=False)

    # Sauve la nouvelle config
    with open(output_file, 'w') as f:
        yaml.dump(new_config, f, default_flow_style=False)

    # Stats
    original_lines = open(input_file).read().count('\n')
    new_lines = open(output_file).read().count('\n')
    template_lines = open('config/widget-templates.yml').read().count('\n')

    print(f"✅ Migration terminée!")
    print(f"📊 Réduction: {original_lines} → {new_lines + template_lines} lignes")
    print(f"📈 Gain: {100 * (1 - (new_lines + template_lines) / original_lines):.0f}%")
    print(f"📁 Templates créés: {len(templates)}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python migrate_config.py <input.yml> <output.yml>")
        sys.exit(1)

    migrate_config(sys.argv[1], sys.argv[2])
```

## Résultat Attendu

### Avant
- **export.yml** : 1600+ lignes
- **transform.yml** : 900+ lignes
- Duplication massive
- Difficile à maintenir

### Après (1 semaine de travail)
- **export.yml** : ~800 lignes (-50%)
- **transform.yml** : ~450 lignes (-50%)
- **widget-templates.yml** : ~100 lignes (nouveau)
- Templates réutilisables
- Plus facile à maintenir

## Prochaines Étapes (Optionnel)

### Semaine 2 : Presets par entité
```yaml
# config/presets/taxon-standard.yml
taxon_standard:
  widgets:
    - template: gauge_template
      presets:
        - {name: height_max, max: 40, unit: m}
        - {name: dbh_max, max: 500, unit: cm}
        - {name: wood_density, max: 1.2, unit: "g/cm³"}
```

### Semaine 3 : Validation automatique
```python
# Ajouter au loader
def validate_widget(self, widget: dict) -> bool:
    """Valide qu'un widget a tous les champs requis"""
    required = ['data_source', 'title']
    return all(field in widget for field in required)
```

### Semaine 4 : Documentation auto
```python
# tools/generate_docs.py
def document_templates():
    """Génère une doc markdown de tous les templates"""
    # ... génère docs/templates.md
```

## Commandes Pour Commencer

```bash
# 1. Créer la structure
mkdir -p config/templates
touch config/widget-templates.yml

# 2. Migrer votre config actuelle
python tools/migrate_config.py config/export.yml config/export_new.yml

# 3. Tester
niamoto transform --config config/export_new.yml

# 4. Si tout marche, remplacer
mv config/export.yml config/export_old.yml
mv config/export_new.yml config/export.yml
```

## Support

Si vous avez des questions pendant l'implémentation :

1. Les templates ne se résolvent pas ?
   → Vérifiez que `EnhancedConfigLoader` est bien utilisé dans votre pipeline

2. Erreur de fusion des configs ?
   → Le `_deep_merge` doit gérer les listes différemment des dicts

3. Performance dégradée ?
   → Les templates sont chargés une seule fois au démarrage, pas d'impact

## Conclusion

Cette approche :
- ✅ **Garde votre architecture** intacte
- ✅ **Réduit de 50%** le volume de config cette semaine
- ✅ **Reste accessible** aux non-codeurs
- ✅ **Peut être déployée** progressivement

**Commencez petit** avec les templates de widgets, puis étendez selon vos besoins.
