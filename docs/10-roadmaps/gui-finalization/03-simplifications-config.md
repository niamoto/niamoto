# Simplifications de configuration identifiées

**Date** : 2026-02-05
**Phase** : 3.2 du plan de finalisation GUI Transform/Export
**Instance de référence** : `test-instance/niamoto-test/`

## Résumé

L'analyse de l'instance de référence révèle 6 axes de simplification. Aucun ne nécessite de changement cassant — chaque simplification est rétro-compatible et activable progressivement.

| # | Simplification | Impact | Effort | Priorité |
|---|----------------|--------|--------|----------|
| 1 | Raccourci `field_aggregator` quand source = field = target | -30% lignes YAML | Faible | P1 |
| 2 | Convention `stats_loader` : auto-discovery CSV par nom | Zéro config source CSV | Moyen | P1 |
| 3 | Template `statistical_summary` : batch de gauges | -80 lignes (8→1 bloc) | Moyen | P2 |
| 4 | Palette couleurs centralisée dans `export.yml` | -8 doublons hex | Faible | P2 |
| 5 | `class_object` inféré depuis le nom du widget | -5 params explicites | Faible | P3 |
| 6 | Normalisation noms de champs loaders | Cohérence API | Élevé | P3 |

---

## 1. Raccourci field_aggregator — source implicite quand identique

### Constat

Dans `field_aggregator`, quand `source`, `field` et `target` sont identiques (cas fréquent), la config est très verbeuse :

```yaml
# Actuel — 28 lignes pour 7 champs (taxons)
fields:
  - source: taxons
    field: rank_name
    target: rank_name
  - source: taxons
    field: rank_value
    target: rank_value
  - source: taxons
    field: full_name
    target: full_name
  # ...
```

### Simplification proposée

Ajouter un raccourci quand `field == target` et une source par défaut au niveau du plugin :

```yaml
# Simplifié — 10 lignes pour 7 champs
default_source: taxons
fields:
  - rank_name
  - rank_value
  - full_name
  - full_path
  - field: extra_data.enriched_at
    target: enriched_at
  - field: extra_data.api_enrichment.image_small_thumb
    target: image_url
    format: url
```

### Impact mesuré

| Groupe | Champs field=target | Total champs | Lignes économisées |
|--------|--------------------|--------------|--------------------|
| taxons | 5/8 | 8 | ~15 lignes |
| plots  | 6/7 | 7 | ~18 lignes |
| shapes | 4/5 | 5 | ~12 lignes |

### Implémentation

- Modifier `FieldAggregatorParams` pour accepter `str` en plus de `FieldConfig`
- Ajouter `default_source: Optional[str]` au niveau params
- La forme longue reste supportée (rétro-compatible)

---

## 2. Convention stats_loader — auto-discovery CSV

### Constat

Les 2 sources CSV suivent un pattern prévisible :

```yaml
# plots — 8 lignes de config
- name: plot_stats
  data: imports/raw_plot_stats.csv
  grouping: plots
  relation:
    plugin: stats_loader
    key: id
    ref_field: id_plot
    match_field: plot_id

# shapes — 8 lignes de config
- name: shape_stats
  data: imports/raw_shape_stats.csv
  grouping: shapes
  relation:
    plugin: stats_loader
    key: id
    ref_field: name
    match_field: label
```

Le code `stats_loader.py` a **déjà** un default pour `ref_field` :
```python
ref_field = params.ref_field or f"{group_name}_id"  # ligne 148
```

### Simplification proposée

Convention de nommage : si un fichier `imports/raw_{source_name}.csv` existe, le configurer automatiquement comme source CSV :

```yaml
# Simplifié — 3 lignes
- name: plot_stats
  grouping: plots
  # data: auto-découvert → imports/raw_plot_stats.csv
  # relation.plugin: auto → stats_loader
  # relation.key: auto → id
  # relation.ref_field: auto → plot_id (via {group}_id)
```

Seul `match_field` non-standard (`label` pour shapes) nécessiterait d'être explicité.

### Implémentation

- Ajouter logique auto-discovery dans `save-config` endpoint
- Quand `data` est absent et `imports/raw_{name}.csv` existe → l'utiliser
- Quand `relation` est absente → inférer `stats_loader` avec defaults
- Tout reste explicitable pour cas non-standard

---

## 3. Template statistical_summary — batch de gauges

### Constat

8 widgets `statistical_summary` identiques (lignes 119-206), seuls 3 paramètres varient :

```yaml
# 88 lignes pour 8 gauges quasi-identiques
dbh_statistical_summary_radial_gauge:
  plugin: statistical_summary
  params:
    source: occurrences
    field: dbh
    stats: [max, mean, min]
    units: cm
    max_value: 500

height_statistical_summary_radial_gauge:
  plugin: statistical_summary
  params:
    source: occurrences
    field: height
    stats: [max, mean, min]
    units: m
    max_value: 100
# ... 6 de plus, identiques sauf field/units/max_value
```

### Simplification proposée

Nouveau mode `batch` dans le GUI qui expanse un template :

```yaml
# Simplifié — 16 lignes au lieu de 88
_batch_statistical_summary:
  plugin: statistical_summary
  source: occurrences
  stats: [max, mean, min]
  variants:
    - { field: dbh, units: cm, max_value: 500 }
    - { field: height, units: m, max_value: 100 }
    - { field: bark_thickness, units: mm, max_value: 50 }
    - { field: wood_density, units: "g/cm³", max_value: 2 }
    - { field: leaf_sla, units: "", max_value: 500 }
    - { field: leaf_area, units: "m²", max_value: 2000 }
    - { field: leaf_ldmc, units: "", max_value: 1000 }
    - { field: leaf_thickness, units: mm, max_value: 2000 }
```

### Impact

- **-72 lignes** pour les gauges taxons seules
- Pattern réutilisable pour tout plugin avec variantes simples
- Le GUI peut proposer un mode "ajouter en batch" pour `statistical_summary`

### Implémentation

- Expansion côté GUI (`save-config` expand les templates avant écriture)
- Le `transform.yml` final reste inchangé (forme longue)
- Donc **zéro changement backend**, uniquement UX du GUI

---

## 4. Palette couleurs centralisée

### Constat

Doublons de couleurs dans `export.yml` :

| Couleur | Occurrences | Widgets |
|---------|-------------|---------|
| `#0c4a6e` | 3× | nav_color, text_color, footer_bg_color |
| `#10b981` | 5× | 5 gradient_color (distributions) |
| `#00716b` | 1× | map fillColor |
| `#8B4513` | 1× | dbh gradient (dans transform.yml !) |

### Simplification proposée

Section `color_schemes` au niveau site dans `export.yml` :

```yaml
site:
  color_schemes:
    distribution_default: '#10b981'
    distribution_brown: '#8B4513'
    map_marker: '#00716b'
    phenology:
      fleur: '#FFB74D'
      fruit: '#81C784'
```

Les widgets référencent par nom au lieu de hex :

```yaml
gradient_color: $distribution_default   # au lieu de '#10b981'
```

### Impact

- Changement de thème en modifiant 4 lignes au lieu de 13
- Cohérence visuelle garantie
- Le GUI peut proposer un color picker au niveau site

### Implémentation

- Ajouter `color_schemes` au modèle `SiteConfig`
- Résolution `$nom` → valeur hex dans le moteur de rendu export
- Rétro-compatible : les valeurs hex directes restent supportées

---

## 5. class_object inféré depuis le nom du widget

### Constat

Le nom du widget encode déjà le `class_object` :

| Widget name | class_object | Plugin |
|-------------|-------------|--------|
| `dbh_series_extractor_bar_plot` | `dbh` | `class_object_series_extractor` |
| `top10_family_series_extractor_bar_plot` | `top10_family` | `class_object_series_extractor` |
| `cover_forest_binary_aggregator_donut_chart` | `cover_forest` | `binary_aggregator` |

Pattern : `{class_object}_{plugin_suffix}_{widget_type}`

### Simplification proposée

Si `params.class_object` est absent, l'inférer depuis le nom du widget :

```python
# Dans le plugin base
def _infer_class_object(self, widget_name: str, plugin_name: str) -> str:
    """Extrait le class_object du nom du widget."""
    suffix = plugin_name.replace("class_object_", "")
    if widget_name.endswith(suffix):
        return widget_name[:widget_name.index(suffix)].rstrip("_")
    return widget_name.split("_")[0]
```

### Impact

- 5 paramètres `class_object:` en moins dans l'instance de test
- Conventions de nommage rendues explicites
- Le GUI peut auto-générer le nom du widget

### Implémentation

- Modifier les plugins `class_object_*` pour accepter `class_object: Optional[str]`
- Fallback sur inférence depuis widget_name si absent
- Rétro-compatible : le param explicite a toujours priorité

---

## 6. Normalisation des noms de champs loaders

### Constat

Les loaders utilisent des noms incohérents pour le même concept :

| Concept | nested_set | direct_reference | stats_loader |
|---------|-----------|-----------------|--------------|
| Clé dans les données | `key` | `key` | `key` |
| Champ de jointure référence | `ref_key` | _(implicite)_ | `ref_field` |
| Champ de correspondance | _(via fields)_ | _(implicite)_ | `match_field` |

### Simplification proposée

Standardiser sur 3 noms cohérents :

```yaml
relation:
  plugin: stats_loader
  source_key: id            # Ancien: key
  reference_key: plot_id    # Ancien: ref_field / ref_key
  match_key: plot_id        # Ancien: match_field (souvent = source_key)
```

### Impact

- API plus intuitive pour les utilisateurs
- Documentation simplifiée
- Le GUI peut afficher des labels cohérents

### Implémentation

- **Breaking change** si on supprime les anciens noms
- Recommandation : supporter les deux formes pendant 1 version, log warning sur anciens noms
- Phase ultérieure (P3) car nécessite migration des configs existantes

---

## Synthèse des gains

### Sur l'instance de test (transform.yml — 484 lignes)

| Simplification | Lignes actuelles | Lignes après | Gain |
|---------------|-----------------|-------------|------|
| field_aggregator raccourcis | ~75 | ~30 | -45 |
| stats_loader convention | ~16 | ~6 | -10 |
| statistical_summary batch | ~88 | ~16 | -72 |
| **Total** | ~179 | ~52 | **-127 lignes (-71%)** |

### Sur export.yml (couleurs)

| Simplification | Valeurs dupliquées | Après | Gain |
|---------------|-------------------|-------|------|
| Palette centralisée | 13 hex values | 4 tokens | -9 doublons |

### Priorité d'implémentation recommandée

```
Sprint 1 (P1) — Gains immédiats, faible risque
├── #1 field_aggregator raccourci (backend seul, rétro-compatible)
└── #2 stats_loader convention (backend + GUI, rétro-compatible)

Sprint 2 (P2) — UX améliorée
├── #3 Batch statistical_summary (GUI seul, zéro changement backend)
└── #4 Palette couleurs (backend + export engine)

Sprint 3 (P3) — Cohérence long terme
├── #5 class_object inférence (plugins, rétro-compatible)
└── #6 Normalisation loaders (breaking, nécessite migration)
```
