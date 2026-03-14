# Contrat de Configuration v1 — Niamoto

Date : 19/02/2026
Statut : **ACTIF** — source de vérité pour le format des fichiers de configuration

---

## Principes fondamentaux

1. **Configuration over code** — Aucun nom d'entité, de table, de colonne ou de valeur métier ne doit être hardcodé dans le code. Tout vient de la configuration.
2. **Généricité** — Le format fonctionne pour n'importe quel jeu de données écologique (forêt tropicale, récif corallien, inventaire faunistique).
3. **UI-first** — La GUI génère et lit ces fichiers. Le format doit être parsable sans ambiguïté et validable avec des modèles Pydantic.
4. **Pas d'alias implicites** — Un nom = une signification. Pas de résolution magique (`"occurrences"` ne doit pas être deviné si non déclaré).

---

## 1. import.yml — Format canonique

### Structure

```yaml
version: '1.0'

entities:
  datasets:
    <nom_dataset>:
      description: <string optionnel>
      connector:
        type: file | duckdb_csv | vector | api | derived | file_multi_feature
        format: csv | excel | json | geojson    # si type=file
        path: <chemin relatif>                   # si type=file
        source: <nom_entité>                     # si type=derived
        extraction: { ... }                      # si type=derived
        sources: [ ... ]                         # si type=file_multi_feature
      schema:
        id_field: <nom_colonne>
        fields:
          - name: <nom>
            type: string | integer | float | date | datetime | boolean | geometry
            description: <string optionnel>
      links:
        - entity: <nom_référence>
          field: <clé étrangère dans ce dataset>
          target_field: <clé primaire dans la référence>
      options:
        mode: replace | append | upsert
        chunk_size: <int>

  references:
    <nom_référence>:
      kind: hierarchical | spatial | categorical | generic
      description: <string optionnel>
      connector: { ... }           # même structure que datasets
      schema: { ... }              # même structure que datasets
      hierarchy:                   # obligatoire si kind=hierarchical
        strategy: adjacency_list | nested_set | hybrid
        levels: [<string>, ...]
      relation:                    # optionnel, lien vers un dataset
        dataset: <nom_dataset>
        foreign_key: <colonne dans le dataset>
        reference_key: <colonne dans la référence>
      enrichment:                  # optionnel
        - plugin: <nom_plugin>
          enabled: true | false
          config: { ... }

metadata:                          # optionnel
  layers:
    - name: <nom>
      type: vector | raster
      path: <chemin>
      description: <string>
```

### Invariants

| Règle | Description |
|---|---|
| `entities` est obligatoire | Même vide, la clé doit exister |
| `datasets` et `references` sont des objets (`{}`) ou absents | `null` est toléré en lecture (robustesse) mais interdit dans le format canonique écrit par la GUI |
| Les noms d'entités sont libres | `occurrences`, `mes_observations`, `coral_surveys` — tout est valide |
| `version: '1.0'` est obligatoire | Permet la migration future |
| Les chemins `path` sont relatifs et confinés au projet | Pas de chemins absolus, pas de traversée (`..`) hors racine projet |

### Anti-patterns interdits

```yaml
# INTERDIT (format canonique UI) — pas de valeur null implicite
entities:
  references:     # ← YAML parse comme null, pas comme {}

# CORRECT — soit absent, soit explicitement vide
entities:
  references: {}

# CORRECT — ou simplement ne pas déclarer la clé
entities:
  datasets:
    my_data: { ... }
```

---

## 2. transform.yml — Format canonique

### Structure

Le format canonique est une **liste YAML** (pas un dict).

```yaml
# Liste de groupes de transformation
- group_by: <nom_entité>       # doit correspondre à une entité dans import.yml
  sources:
    - name: <identifiant_local>
      data: <nom_entité_ou_chemin_csv>
      grouping: <nom_entité>
      relation:
        plugin: nested_set | direct_reference | join_table | spatial | stats_loader
        key: <colonne clé>
        ref_key: <colonne référence>         # optionnel selon le plugin
        ref_field: <champ de la référence>   # optionnel selon le plugin
        fields: { ... }                      # optionnel (nested_set)

  widgets_data:
    <widget_id>:
      plugin: <nom_plugin_transformer>
      params:
        source: <identifiant_local>          # réfère au name dans sources
        field: <colonne>
        # ... paramètres spécifiques au plugin
```

### Validation Pydantic (backend)

```python
# Modèle canonique — src/niamoto/common/transform_config_models.py
TransformConfigAdapter = TypeAdapter(List[TransformGroupConfig])

# Usage
groups = TransformConfigAdapter.validate_python(yaml_data)
```

### Invariants

| Règle | Description |
|---|---|
| Format **liste** uniquement | Pas de dict à la racine |
| `group_by` correspond à une entité de `import.yml` | Pas de noms inventés |
| `sources[].name` est un identifiant local au groupe | Réutilisable entre groupes |
| `widgets_data` keys sont les identifiants de widgets | Deviennent les clés JSON exportées |
| `yaml.safe_load()` peut retourner `None` si tout est commenté | Le backend doit gérer `None` → `[]` |
| Chaque widget déclare son `plugin` | Pas de plugin par défaut |

### Plugins de relation disponibles

| Plugin | Usage | Clés requises |
|---|---|---|
| `nested_set` | Données hiérarchiques (taxonomie) | `key`, `ref_key`, `fields.left`, `fields.right`, `fields.parent` |
| `direct_reference` | Clé étrangère simple | `key`, `ref_key` |
| `join_table` | Jointure via table d'association | `key`, `ref_key`, `join_table`, `join_left_key`, `join_right_key` |
| `stats_loader` | Statistiques pré-calculées (CSV) | `key`, `ref_field`, `match_field` |
| `spatial` | Jointure spatiale | `geometry_field`, `ref_geometry_field` |

### Registre de schémas plugins (obligatoire)

Pour éviter les divergences UI/backend, chaque plugin de relation et de widget doit exposer un schéma de paramètres (clés requises, types, valeurs par défaut, contraintes).

Contrat :

1. Le backend valide les paramètres à partir de ce registre (pas de validation ad hoc dispersée).
2. La GUI génère les formulaires à partir de ce registre.
3. Toute nouvelle clé plugin est un changement explicite de contrat (et documenté).

### Anti-patterns interdits

```yaml
# INTERDIT — format dict à la racine
taxons:
  sources: [...]
  widgets_data: { ... }

# CORRECT — format liste
- group_by: taxons
  sources: [...]
  widgets_data: { ... }
```

---

## 3. Contrat de robustesse backend

### Normalisation obligatoire

Le backend **DOIT** normaliser les valeurs `None` issues du parsing YAML :

```python
# Pattern obligatoire pour toute lecture de config
entities = config.get("entities", {}) or {}
datasets = entities.get("datasets", {}) or {}
references = entities.get("references", {}) or {}
```

Le `or {}` est nécessaire car `.get("key", {})` retourne `None` (pas `{}`) quand la clé YAML existe avec valeur `null`.

### Validation pré-exécution

Avant tout traitement (import, transform, export) :

1. Charger le YAML
2. Normaliser les `None` → `{}` / `[]`
3. Valider via les modèles Pydantic (`TransformConfigAdapter` pour transform.yml)
4. Valider la sécurité des chemins (`path`) : relatif + résolution dans la racine projet
5. Valider les identifiants logiques (entités/sources/widgets/groupes)
6. Retourner des erreurs explicites si la validation échoue

### Résolution d'entités

```
# Flux de résolution
import.yml → entities.datasets.<nom> → table en base (via EntityRegistry)
import.yml → entities.references.<nom> → table en base (via EntityRegistry)
transform.yml → group_by:<nom> → correspondance avec import.yml
transform.yml → sources[].data:<nom> → correspondance avec import.yml OU chemin CSV
```

Le backend ne doit JAMAIS deviner un nom d'entité. Si `group_by: taxons` est déclaré mais `taxons` n'existe pas dans import.yml, c'est une erreur explicite.

### Contrat de nommage (identifiants logiques)

Les identifiants logiques suivants doivent respecter un format stable :

- `entities.datasets.<name>`
- `entities.references.<name>`
- `transform[].group_by`
- `transform[].sources[].name`
- `widgets_data.<widget_id>`

Règle proposée : `^[A-Za-z][A-Za-z0-9_-]{1,62}$`

Objectif : éviter les ambiguïtés de résolution, faciliter la génération UI, et prévenir les bugs SQL liés aux identifiants libres.

---

## 4. Contrat GUI (frontend)

### Templates UI

La GUI peut proposer des **templates pré-remplis** pour aider l'utilisateur :

```typescript
// Acceptable — ce sont des suggestions, pas des defaults imposés
ENTITY_TEMPLATES = [
  { id: 'occurrences', defaultName: 'occurrences', ... },
  { id: 'taxonomy',    defaultName: 'taxonomy', ... },
  { id: 'plots',       defaultName: 'plots', ... },
  { id: 'shapes',      defaultName: 'shapes', ... },
]
```

L'utilisateur peut renommer ces entités librement. Le backend ne doit pas dépendre de ces noms.

### Génération de config

La GUI génère le YAML via `import-config-generator.ts`. Le format généré **DOIT** correspondre exactement au format canonique ci-dessus.

### Round-trip canonique (obligatoire)

Le cycle `load -> edit UI -> save -> reload` ne doit pas altérer sémantiquement la config.

Exigences :

1. Ordre de sortie stable (canonical serialization).
2. Suppression des `null` non utiles (`{}` / `[]` explicites ou clé absente selon le contrat).
3. Aucune insertion d'alias implicites.
4. Deux sauvegardes successives sans modification utilisateur produisent le même contenu.

### Feedback de validation

La GUI affiche les erreurs de validation côté client (TypeScript) ET relaie les erreurs du backend (Pydantic). Les messages d'erreur doivent être explicites :

```
✗ "Entité 'taxons' référencée dans transform.yml mais non déclarée dans import.yml"
✓ (pas de message cryptique ou d'erreur technique brute)
```

---

## 5. Politique de version et migration

### Version de contrat

- `version: '1.0'` est le contrat canonique actif.
- Toute évolution incompatible doit incrémenter la version du contrat.

### Règles de compatibilité

1. **Patch/minor** : ajout non-bloquant (champs optionnels, nouveaux plugins optionnels) sans casser le parsing v1.
2. **Major de contrat** : changement de structure, renommage obligatoire, ou suppression de champ.

### Source de vérité

Ordre de priorité :
1. Modèles Pydantic backend
2. Schéma UI généré depuis le registre plugin
3. Ce document de contrat

### Migration

- Si un format non canonique est toléré en lecture, il ne doit jamais être réécrit tel quel.
- Toute réécriture doit converger vers le format canonique v1.

---

## 6. Violations connues à corriger

L'inventaire du 19/02/2026 a identifié **60 violations** du principe configuration-over-code :

| Sévérité | Nombre | Impact |
|---|---|---|
| S1 (critique — SQL/logique cassée si noms changent) | 8 | Bloquant release |
| S2 (important — defaults hardcodés, logique fragile) | 29 | À planifier |
| S3 (mineur — messages, UI, logs) | 23 | Cosmétique |

### S1 prioritaires pour la release

1. **layout.py:620** — SQL avec `o.id_taxonref = e.taxons_id` hardcodé
2. **data_loader.py:46** — `resolve_dataset_table(db, "occurrences")` hardcodé
3. **stats.py:330** — `"entity_occurrences"` hardcodé
4. **enrichment.py:153** — `"occurrences"` hardcodé comme dataset par défaut
5. **config_loader.py:25** — Premier dataset = default implicite
6. **entity_finder.py** — Détection nested_set avec colonnes `lft/rght/parent_id` hardcodées
7. **suggestion_service.py:89** — `"occurrences"` comme fallback
8. **preview_service.py:232** — `"occurrences"` comme fallback

### Principe de remédiation

Pour chaque violation S1 :
1. Identifier d'où l'information devrait venir (import.yml, transform.yml, ou EntityRegistry)
2. Remplacer le hardcode par une lecture de config
3. Ajouter un message d'erreur explicite si la config ne contient pas l'information attendue
4. Tester avec un jeu de données utilisant des noms non-standard

---

## 7. Checklist de conformité

Pour valider qu'une modification respecte ce contrat :

- [ ] Aucun nom d'entité hardcodé (`occurrences`, `taxons`, `plots`, `shapes`)
- [ ] Aucun nom de colonne hardcodé (`id_taxonref`, `dbh`, `height`, `lft`, `rght`)
- [ ] Aucune table hardcodée (`entity_occurrences`, `dataset_occurrences`)
- [ ] Les `None` YAML sont normalisés (`or {}`)
- [ ] Le YAML écrit par la GUI n'émet pas de `null` pour `datasets` / `references`
- [ ] Les chemins `path` sont relatifs et ne sortent jamais de la racine projet
- [ ] Les identifiants logiques respectent le regex de contrat
- [ ] Les erreurs de config sont des messages explicites, pas des crashs
- [ ] Le format transform.yml est une liste, pas un dict
- [ ] Les noms de `group_by` sont validés contre import.yml
- [ ] Les paramètres plugin sont validés via un registre unique de schémas
- [ ] Le round-trip UI est canonique et stable (pas de diff parasite)
