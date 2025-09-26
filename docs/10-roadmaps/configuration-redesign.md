# 🧩 Refonte du Système de Configuration Niamoto

## 1. Objectifs & Problèmes Actuels

### 1.1 Constat du système existant
- Configuration principale regroupée dans `config/transform.yml` et `config/export.yml`.
- Clés implicites partageant le même nom entre transform et export (ex. `top_species`).
- Mélange de logique métier (concepts) et implémentation technique (plugins, paramètres détaillés).
- Difficile à manipuler via l'UI : la moindre modification implique de relire un gros fichier pour trouver la bonne section.
- Rendu visuel (widgets, templates) couplé au pipeline de transformation.

### 1.2 Enjeux de la refonte
- Séparer **intention métier** et **implémentation technique**.
- Offrir une API claire pour l’UI (mode express ↔ mode avancé).
- Préserver la traçabilité (lineage, versionning) et la reproductibilité des pipelines.
- Réduire la friction pour créer/modifier des visualisations.
- Permettre une automatisation (concept binding, recommandations de plugins) sans dériver vers une configuration opaque.

## 2. Vision de la Nouvelle Architecture

### 2.1 Principes directeurs
1. **Déclaratif modulaire** : chaque intention (source, transformation, widget, export) vit dans un bloc court et typé.
2. **Compilation déterministe** : la CLI/serveur compile les blocs en fichiers d’exécution (YAML/Polars) versionnables.
3. **Dualité UX** : l’UI manipule des concepts et widgets, tandis que les utilisateurs avancés peuvent toujours éditer le code généré ou étendre via Python.
4. **Observabilité native** : chaque bloc porte lineage, validations, métadonnées, facilitant l’audit.
5. **Extensibilité** : inclusion de bundles, macros, domain packs pour éviter la duplication.

### 2.2 Structure des dossiers
```
project.yml
sources/
  occurrences.yaml
  taxonomy.yaml
models/
  taxon_general_info.yaml
  taxon_top_species.yaml
widgets/
  taxon_info_panel.yaml
  taxon_top_species_chart.yaml
pipelines/
  taxon_dashboard.yaml
exports/
  static_site.yaml
recipes/
  ecology_bundle.yaml
artifacts/
  manifest.json
  compiled/
```

- `project.yml` : métadonnées globales (version, locale, options CLI).
- `sources/` : définition des connecteurs et validations d’entrée.
- `models/` : concepts dérivés (aggrégations, ratios, temps forts…).
- `widgets/` : composants de rendu (bar plot, métrique, carte…).
- `pipelines/` : assemblage de widgets/concepts pour un contexte (dashboard taxon, pipeline import/export).
- `exports/` : exportateurs finaux (HTML statique, API, fichiers).
- `recipes/` : bundles prêts à l'emploi (domain packs, templates).
- `artifacts/` : outputs générés (`manifest.json`, YAML compilés, snapshots).

## 3. Spécification des Blocs

### 3.1 Sources (`sources/*.yaml`)
```yaml
source: occurrences
format: duckdb
path: data/occurrences.parquet
schema:
  - name: taxon_ref_id
    type: int
validations:
  - not_null: taxon_ref_id
  - spatial_valid: geo_pt
caching:
  policy: snapshot
  anchor: occurrences_snapshot
```
- Définit comment charger et valider les données brutes.
- Peut inclure des options de cache/ancrage (Execution Anchors).

### 3.2 Models / Concepts (`models/*.yaml`)
```yaml
model: taxon_top_species
label: "Sous-taxons principaux"
depends_on: [occurrences, taxonomy]
transform:
  plugin: taxonomy.top_ranking
  params:
    source: occurrences
    hierarchy:
      table: taxonomy
      id: id
      parent_id: parent_id
      name: full_name
      rank: rank_name
    filter_ranks: ["species", "infra"]
    limit: 10
validations:
  - not_empty
  - schema:
      tops: array<string>
      counts: array<int>
lineage:
  tags: [taxon, ranking]
  owner: team-ecology
```
- Représente un concept manipulé par l’analyste.
- Rassemble plugin, paramètres, validations, métadonnées.

### 3.3 Widgets (`widgets/*.yaml`)
```yaml
widget: taxon_top_species_chart
type: bar_plot
model: taxon_top_species
params:
  orientation: horizontal
  x_axis: counts
  y_axis: tops
  sort_order: descending
  labels:
    x_axis: "Nombre d'observations"
    y_axis: "Taxon"
layout:
  width: 6
  height: 4
```
- Décrit un composant UI en se basant sur un ou plusieurs concepts.
- Spécifie la configuration visuelle (axes, labels, layout).

### 3.4 Pipelines (`pipelines/*.yaml`)
```yaml
pipeline: taxon_dashboard
context:
  group_by: taxon
  primary_key: taxon_id
includes:
  - widget: taxon_info_panel
  - widget: taxon_top_species_chart
  - widget: taxon_distribution_map
schedule:
  refresh: daily
  anchor: taxon_snapshot
tests:
  - pipeline_status: success
```
- Assemble des widgets et définit le contexte d’exécution.
- Peut spécifier le scheduling ou la gestion des snapshots.

### 3.5 Exports (`exports/*.yaml`)
```yaml
export: static_site
type: html_site
inputs:
  - pipeline: taxon_dashboard
  - pipeline: plot_dashboard
params:
  template_dir: templates/
  output_dir: exports/web/
  navigation_include: templates/nav.yaml
assets:
  copy:
    - templates/assets/
```
- Décrit les sorties finales en s’appuyant sur les pipelines compilés.

## 4. Outils & API CLI

### 4.1 Commandes clés
- `niamoto init` : initialise structure (dossiers, templates).
- `niamoto add-model <nom> --from recipe` : génère un concept depuis un modèle de recette.
- `niamoto compile` : compile les blocs en YAML exécutable (dans `artifacts/compiled`).
- `niamoto run <pipeline>` : exécute un pipeline avec tracking lineage.
- `niamoto test` : lance validations sur sources, modèles, pipelines.
- `niamoto diff --against <branch>` : compare manifest/compilation entre deux versions.

### 4.2 Manifest & Observabilité
- `artifacts/manifest.json` : graph complet (sources → modèles → widgets → pipelines → exports) avec versions, hashes, anchors.
- `artifacts/compiled/` : fichiers YAML générés (ex. `transforms/taxon_top_species.yml`).
- Logs normalisés pour l’audit (`logs/pipeline_runs/*.jsonl`).

## 5. Intégration UI & Concept Binding

### 5.1 Flux UX
1. **Découverte** : l’UI liste les concepts disponibles (`models/`) et les widgets (`widgets/`).
2. **Création** : l’utilisateur peut créer un concept à partir d’une recette ou partir de zéro ; l’UI remplit le fichier YAML avec métadonnées et params par défaut.
3. **Shelves** : drag & drop d’un concept dans une zone visuelle → création d’un widget configuré automatiquement.
4. **Preview** : le pipeline est compilé à la volée (via API) pour afficher un aperçu du rendu.
5. **Anchoring** : l’utilisateur peut "figer" un état (snapshot) ; l’UI persiste l’anchor dans `sources/` ou `pipelines/`.

### 5.2 Mode express vs avancé
- **Express** : l’utilisateur manipule des concepts, l’UI gère la génération des fichiers.
- **Avancé** : l’utilisateur ouvre un bloc spécifique (ex. `models/taxon_top_species.yaml`) pour ajuster un plugin ou ajouter une validation.
- L’UI montre les validations, lineage et tests rattachés à chaque bloc pour éviter les erreurs silencieuses.

## 6. Gestion du Volume de Fichiers

### 6.1 Bundles & Recettes
- Support d’un fichier composite :
  - `recipes/ecology_bundle.yaml` contenant plusieurs modèles/widgets pré-définis.
  - Possibilité de les "déplier" (`niamoto unbundle ecology_bundle`) si besoin de personnalisation fine.

### 6.2 CLI & UI Helpers
- `niamoto list models` : inventaire rapide avec tags et owners.
- `niamoto bundle models --into models.yaml` : regroupement temporaire pour édition bulk.
- UI propose filtres par tag/domain et n’expose que les éléments pertinents.
- Convention `*_generated.yaml` pour les fichiers auto-générés à ignorer/re-générer.

## 7. Migration & Implémentation

### 7.1 Phases
| Phase | Livrables | Détails |
| --- | --- | --- |
| P1 (2-3 semaines) | Spec & prototypes | Définition schemas Pydantic, PoC compilation → `artifacts/compiled` |
| P2 (3-4 semaines) | CLI + manifest | Implémentation `niamoto compile`, `niamoto run`, gestion manifest |
| P3 (4 semaines) | UI intégration | API concept/widget, mode express, prévisualisation |
| P4 (4 semaines) | Migration pilote | Scripts conversion `transform.yml` → blocs, tests automatisés |
| P5 (2 semaines) | Documentation & recettes | Guides utilisateurs, domain packs, bundling |

### 7.2 Scripts de migration
- `scripts/migrate_config_to_blocks.py`
  - Parse `transform.yml` pour générer `models/` + `widgets/` + `pipelines/`.
  - Convertir `export.yml` → `exports/*.yaml`.
- Génération d’un rapport de diff (avant/après) pour audit.
- Rollout via feature flag `settings.project.use_modular_config = true`.

### 7.3 Tests & Qualité
- Tests unitaires pour chaque parser/compilateur (sources, models, widgets…).
- Tests d’intégration : exécution pipeline sur instance de test (`test-instance/niamoto-og`).
- Validation que les artefacts compilés reproduisent les mêmes sorties (hashs, snapshots).

## 8. Bénéfices Attendus
- **Fluidité UX** : interaction directe avec concepts/widgets, rafraîchissement ciblé.
- **Traçabilité accrue** : lineage, validations, owners par bloc.
- **Maintainability** : fichiers courts, typés, isolés ; facile à relire et reviewer.
- **Automatisation** : recommandation de plugins, concept binding, bundling.
- **DevOps-friendly** : manifest déterministe, commandes CLI standardisées, environnement prêt pour CI/CD.
- **Extensibilité** : ajout de nouveaux domaines via recettes/bundles sans complexifier la base.

## 9. Risques & Mitigations
| Risque | Impact | Mitigation |
| --- | --- | --- |
| Explosion du nombre de fichiers | Fatigue maintenance | Bundles, CLI helpers, UI filtrée |
| Courbe d’apprentissage | Adoption lente | Guides, templates, formation, mode express |
| Divergence généré vs manuel | Bugs pipeline | Compilation unique (source of truth), tests en CI |
| Coût migration | Projet retardé | Scripts automatiques + feature flag + double run temporaire |

## 10. Prochaines Étapes
1. Valider ce design avec produit/engineering (atelier de cadrage).
2. Définir les schemas Pydantic pour chaque bloc (`sources`, `models`, `widgets`, `pipelines`, `exports`).
3. Prototyper `niamoto compile` pour un sous-ensemble (ex. pipeline taxon) et mesurer l’effort de migration.
4. Planifier la cohabitation temporaire (ancien système ↔ nouveau) via un feature flag et un manifest commun.
5. Préparer la communication (docs, ateliers) pour accompagner la transition.
