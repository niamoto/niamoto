# Système de Templates Hiérarchiques - Explication Concrète

## Le Problème Fondamental

Actuellement dans Niamoto, la détection automatique utilise des patterns codés en dur :

```python
# Dans profiler.py actuel
TAXONOMY_PATTERNS = {
    'family': ['family', 'famille', 'fam'],
    'genus': ['genus', 'genre', 'gen'],
    'species': ['species', 'espece', 'esp', 'sp']
}
```

C'est trop rigide : soit ça marche parfaitement, soit ça échoue complètement.

## Concept des Templates Hiérarchiques

### 1. Qu'est-ce qu'un Template ?

Un **template** est un modèle de configuration pré-défini qui "connaît" les patterns typiques d'un domaine spécifique.

```yaml
# template_forets_tropicales_nc.yml
name: "Forêts Tropicales Nouvelle-Calédonie"
domain: tropical_forest
region: pacific
confidence_boost: 1.5  # Boost si on détecte ces patterns

# Patterns spécifiques à ce contexte
expected_columns:
  taxonomy:
    - pattern: "id_taxonref|idtax.*|tax_id"
      maps_to: "taxon_id"
      confidence: 0.9

    - pattern: "famille|family|fam"
      maps_to: "family"
      confidence: 0.8

    - pattern: "espece|species|sp"
      maps_to: "species"
      confidence: 0.85

  spatial:
    - pattern: "province"
      maps_to: "administrative_division"
      expected_values: ["Province Sud", "Province Nord", "Province des Îles"]
      confidence: 0.95  # Très spécifique à NC !

    - pattern: "commune"
      maps_to: "municipality"
      expected_values: ["Nouméa", "Dumbéa", "Mont-Dore", ...]
      confidence: 0.95

  ecological:
    - pattern: "substrat|substrate"
      maps_to: "substrate_type"
      expected_values: ["ultramafique", "volcano-sédimentaire", "calcaire"]
      confidence: 0.9

    - pattern: "zone_vie|holdridge"
      maps_to: "life_zone"
      confidence: 0.8

# Espèces indicatrices (si on les voit, on est sûr d'être en NC)
indicator_species:
  - "Araucaria columnaris"  # Pin colonnaire, endémique NC
  - "Agathis lanceolata"     # Kaori, endémique NC
  - "Amborella trichopoda"   # Seule espèce de son ordre, endémique NC

# APIs d'enrichissement spécifiques
enrichment_apis:
  - name: "Endemia.nc"
    priority: 1
    base_url: "https://api.endemia.nc/v1"

  - name: "Herbier IRD Nouméa"
    priority: 2
    base_url: "https://herbier.ird.nc/api"

# Validations spécifiques
validations:
  - type: "coordinates"
    bounds:
      lat: [-23.0, -19.5]  # Limites géographiques NC
      lon: [163.5, 169.0]
    crs: "EPSG:3163"  # RGNC91-93
```

### 2. La Hiérarchie des Templates

Les templates s'organisent en arbre, du plus générique au plus spécifique :

```
📁 Templates Racine
│
├── 📄 template_generic.yml (niveau 0)
│   └── Patterns universels : id, name, date, coordinates
│
├── 📁 Écologie (niveau 1)
│   ├── 📄 template_ecology_base.yml
│   │   └── Patterns écologiques : species, habitat, observation
│   │
│   ├── 📁 Botanique (niveau 2)
│   │   ├── 📄 template_botany.yml
│   │   │   └── Patterns botaniques : DBH, height, phenology
│   │   │
│   │   ├── 📁 Forêts Tropicales (niveau 3)
│   │   │   ├── 📄 template_tropical_forest.yml
│   │   │   │   └── Patterns tropicaux : canopy, epiphytes, lianas
│   │   │   │
│   │   │   ├── 📄 template_forets_tropicales_nc.yml (niveau 4)
│   │   │   ├── 📄 template_forets_amazonie.yml
│   │   │   └── 📄 template_forets_asie_se.yml
│   │   │
│   │   └── 📁 Forêts Tempérées (niveau 3)
│   │       ├── 📄 template_temperate_forest.yml
│   │       └── 📄 template_forets_europe.yml
│   │
│   └── 📁 Zoologie (niveau 2)
│       └── 📄 template_zoology.yml
│
└── 📁 Sciences de la Terre (niveau 1)
    └── 📄 template_geology.yml
```

### 3. Héritage et Composition

Chaque template **hérite** des patterns de ses parents et peut les **surcharger** :

```yaml
# template_tropical_forest.yml
extends: "botany"  # Hérite de botanique

# Ajoute des patterns spécifiques
additional_patterns:
  canopy:
    - pattern: "strate|stratum|canopy_layer"
      maps_to: "forest_layer"
      expected_values: ["émergent", "canopée", "sous-bois", "herbacée"]

  tropical_metrics:
    - pattern: "dbh|diameter|diametre"
      maps_to: "diameter_breast_height"
      unit: "cm"
      valid_range: [1, 500]

# Surcharge un pattern parent
overrides:
  taxonomy.species:
    confidence: 0.9  # Plus confiant car nomenclature tropicale standardisée
```

## Comment ça Marche Concrètement

### Étape 1 : Détection du Contexte

```python
class TemplateDetector:
    def detect_best_template(self, data_sample: pd.DataFrame) -> Template:
        """Détecte automatiquement le meilleur template"""

        scores = {}

        # Teste chaque template
        for template in self.template_library:
            score = 0.0

            # Check patterns
            for expected_col in template.expected_columns:
                if self.matches_pattern(data_sample.columns, expected_col.pattern):
                    score += expected_col.confidence

            # Check indicator species (très discriminant)
            if template.indicator_species:
                species_found = data_sample['species'].isin(template.indicator_species).any()
                if species_found:
                    score *= 2  # Double le score !

            # Check geographic bounds
            if template.validations.coordinates:
                coords_valid = self.check_coordinates(data_sample, template.bounds)
                if coords_valid:
                    score *= 1.5

            scores[template.name] = score

        # Retourne le template avec le meilleur score
        best_template = max(scores, key=scores.get)
        confidence = scores[best_template]

        print(f"🎯 Template détecté : {best_template} (confiance: {confidence:.2f})")
        return self.templates[best_template]
```

### Étape 2 : Application du Template

```python
class TemplateApplier:
    def apply_template(self, data: pd.DataFrame, template: Template) -> Config:
        """Applique un template pour générer la configuration"""

        config = Config()

        # 1. Mapping des colonnes
        for col in data.columns:
            for pattern_def in template.expected_columns:
                if re.match(pattern_def.pattern, col, re.IGNORECASE):
                    config.add_mapping(
                        source_column=col,
                        target_field=pattern_def.maps_to,
                        confidence=pattern_def.confidence
                    )

        # 2. Configuration des enrichissements
        for api in template.enrichment_apis:
            config.add_enrichment(
                api_name=api.name,
                url=api.base_url,
                priority=api.priority
            )

        # 3. Validations spécifiques
        for validation in template.validations:
            config.add_validation(validation)

        return config
```

### Étape 3 : Validation Interactive

```python
class InteractiveValidator:
    def validate_with_user(self, config: Config, template: Template):
        """L'utilisateur peut corriger/valider"""

        print(f"📋 Configuration générée avec template '{template.name}':")
        print(f"   - {len(config.mappings)} colonnes détectées")
        print(f"   - {len(config.enrichments)} sources d'enrichissement")

        # Montre les mappings incertains
        uncertain = [m for m in config.mappings if m.confidence < 0.7]
        if uncertain:
            print(f"\n⚠️  {len(uncertain)} mappings incertains:")
            for mapping in uncertain:
                user_choice = input(f"   '{mapping.source}' → '{mapping.target}' ? [O/n]")
                if user_choice.lower() == 'n':
                    new_target = input(f"   Nouveau mapping pour '{mapping.source}': ")
                    mapping.target = new_target

        return config
```

## Exemple Concret : Données Nouvelle-Calédonie

### Données d'entrée
```csv
id,id_taxonref,plot_name,taxaname,famille,genre,espece,province,commune,substrat,dbh
1,2283,P01,Araucaria columnaris,Araucariaceae,Araucaria,columnaris,Province Sud,Mont-Dore,ultramafique,45
2,3467,P01,Agathis lanceolata,Araucariaceae,Agathis,lanceolata,Province Sud,Mont-Dore,ultramafique,120
```

### Processus de Détection

1. **Scan initial** : Le système détecte "province", "substrat", "Araucaria columnaris"
2. **Score templates** :
   - `template_generic.yml` : 0.3 (reconnaît id, espece)
   - `template_ecology.yml` : 0.5 (reconnaît espece, genre, famille)
   - `template_botany.yml` : 0.7 (reconnaît dbh)
   - `template_tropical_forest.yml` : 0.9 (reconnaît dbh + patterns tropicaux)
   - **`template_forets_tropicales_nc.yml` : 1.8** ✅ (espèces endémiques + province + substrat)

3. **Application** : Le template NC est appliqué automatiquement

### Configuration Générée
```yaml
# Auto-généré avec template 'Forêts Tropicales NC'
taxonomy:
  path: data.csv
  hierarchy:
    levels: [famille, genre, espece]
    taxon_id_column: id_taxonref
  api_enrichment:
    enabled: true
    plugin: endemia_nc_enricher  # Spécifique NC !

plots:
  identifier: plot_name
  administrative:
    province_field: province
    commune_field: commune

validations:
  - type: endemic_species_checker
    reference: "Endemia NC"
  - type: coordinate_bounds
    lat: [-23.0, -19.5]
    lon: [163.5, 169.0]
```

## Avantages du Système

### 1. Progressivité
- Un utilisateur novice peut utiliser les templates génériques
- Un expert peut créer des templates ultra-spécialisés
- La bibliothèque s'enrichit avec l'usage

### 2. Réutilisabilité
- Les templates sont partageable entre projets
- Une institution peut maintenir ses propres templates
- Versionning possible (Git)

### 3. Apprentissage
- Le système apprend des corrections utilisateur
- Les patterns validés enrichissent les templates
- Amélioration continue de la détection

### 4. Flexibilité
- Possibilité de mixer templates (multi-héritage)
- Templates conditionnels selon les données
- Surcharge locale possible

## Comparaison avec l'Approche DAG

| Aspect | Templates Hiérarchiques | Architecture DAG |
|--------|------------------------|------------------|
| **Complexité** | Simple (YAML + patterns) | Plus complexe (graphes) |
| **Flexibilité** | Moyenne (templates fixes) | Maximale (flux libre) |
| **Courbe d'apprentissage** | Faible | Moyenne |
| **Maintenance** | Facile (fichiers YAML) | Plus technique |
| **Évolutivité** | Limitée aux templates | Illimitée |
| **Cas d'usage** | Données standardisées | Pipelines complexes |

## Conclusion

Les templates hiérarchiques sont une solution **pragmatique** pour :
- Capitaliser sur l'expertise domaine
- Offrir une détection "qui marche" rapidement
- Permettre une montée en compétence progressive

Mais ils restent **limités** comparés au DAG pour des pipelines vraiment flexibles.

**Recommandation** : Commencer avec les templates pour valider le concept, puis migrer vers DAG pour les cas complexes.
