# 🚀 Roadmap Complet : Système d'Auto-détection ML et Pipeline Unifié

## Vue d'Ensemble

Ce document présente la roadmap complète pour transformer Niamoto en plateforme écologique intelligente avec détection automatique basée sur ML. L'objectif est de permettre aux utilisateurs de simplement déposer leurs fichiers et obtenir un pipeline fonctionnel en moins de 30 secondes.

**Vision** : Drop files → Get working pipeline → Refine if needed

## 📊 État Actuel - Décembre 2024

### ✅ Composants Implémentés

#### 1. ML Column Detector (85% complet)
**Fichier** : `src/niamoto/core/imports/ml_detector.py`
- **Architecture** : Random Forest avec 21 features statistiques
- **Types détectés** : 14 types écologiques (diameter, height, species_name, etc.)
- **Performance** : ~85% accuracy sur données synthétiques
- **État** : Modèle entraîné, manque données réelles

#### 2. Data Profiler (90% complet)
**Fichier** : `src/niamoto/core/imports/profiler.py`
- **Fonctionnalités** :
  - Analyse sémantique des colonnes
  - Détection pattern-based (noms) + ML-based (valeurs)
  - Support CSV, GeoJSON, Excel, Shapefile
- **État** : Fonctionnel, intègre le ML detector

#### 3. Auto Detector (80% complet)
**Fichier** : `src/niamoto/core/imports/auto_detector.py`
- **Rôle** : Orchestration de l'analyse multi-fichiers
- **Sortie** : Configuration import.yml auto-générée
- **Limitation** : Format encore rigide (taxonomy/plots/occurrences)

#### 4. Bootstrap System (70% complet)
**Fichier** : `src/niamoto/core/imports/bootstrap.py`
- **Pipeline** : Analyse → Config → Import → Transform → Export
- **Génération** : Les 3 fichiers YAML automatiquement
- **État** : Fonctionnel mais format ancien

#### 5. UI Bootstrap (60% complet)
**Fichiers** :
- `src/niamoto/gui/ui/src/components/pipeline/Bootstrap.tsx`
- `src/niamoto/gui/api/routers/bootstrap.py`
- **Interface** : Drag & drop, wizard 4 étapes
- **État** : Isolé, pas intégré au pipeline unifié

### ⚠️ Points de Blocage Actuels

1. **Format Rigide** : Import.yml impose taxonomy/plots/occurrences
2. **Manque de Données** : Modèle ML entraîné sur données synthétiques
3. **Transform Manuel** : Pas de génération auto via introspection
4. **UI Fragmentée** : Bootstrap séparé du pipeline principal
5. **Documentation Éparpillée** : Multiples docs sans organisation

## 🎯 Objectifs et Métriques

### Objectifs Principaux
- **Accuracy ML** : >90% sur 30+ types écologiques
- **Bootstrap Time** : <30 secondes pour datasets typiques
- **User Effort** : <3 modifications manuelles nécessaires
- **Success Rate** : >95% des configs générées fonctionnent

### Couverture Cible
- 30+ types sémantiques écologiques
- Support multi-langues (FR, EN, ES, DE)
- Formats : CSV, Excel, JSON, GeoJSON, Shapefile, GeoPackage

## 📅 Planning Détaillé

### Phase 1 : Consolidation et Format Générique (Semaines 1-2)

#### Semaine 1 : Migration Format Générique

**1.1 Nouveau Format import.yml**
```yaml
# Avant (rigide)
taxonomy:
  path: data.csv
  hierarchy:
    levels: [family, genus, species]

# Après (générique)
references:
  species:  # Nom libre
    source: data.csv
    type: hierarchical
    hierarchy: [family, genus, species]

data:
  observations:
    source: obs.csv
    links:
      - reference: species
        field: species_code
```

**Fichiers à modifier** :
- [ ] `auto_detector.py` : Méthode `_generate_config()`
- [ ] `bootstrap.py` : Support nouveau format
- [ ] `generic_importer.py` : Créer ce nouveau module

**Tests** :
- [ ] Migration configs existantes
- [ ] Bootstrap avec nouveau format
- [ ] Validation end-to-end

#### Semaine 2 : Entraînement ML sur Données Réelles

**2.1 Collecte de Données**

Script : `scripts/collect_training_data.py`

```python
# Sources de données
sources = {
    'GBIF': 'https://api.gbif.org/v1/',      # 2.2B occurrences
    'FIA': 'https://apps.fs.usda.gov/fia/',  # Forest inventory USA
    'TRY': 'https://www.try-db.org/',        # Plant traits
    'WorldClim': 'https://worldclim.org/',   # Climate data
    'BIEN': 'https://bien.nceas.ucsb.edu/',  # Botanical data
    'NC_Data': 'local/nouvelle_caledonie/'   # Données locales
}
```

**2.2 Pipeline d'Entraînement**
- [ ] Collecter 10,000+ exemples réels
- [ ] Augmentation données (unités, formats)
- [ ] Validation croisée 80/20
- [ ] Sauvegarde modèle production

**Métriques cibles** :
- Accuracy : >90%
- F1-score : >0.88
- Temps inférence : <100ms/colonne

### Phase 2 : Transform Generation via Introspection (Semaines 3-4)

#### Semaine 3 : Plugin Introspector

**Nouveau module** : `src/niamoto/core/transforms/introspector.py`

```python
class PluginIntrospector:
    """Introspection des schémas Pydantic pour auto-génération"""

    TYPE_TO_PLUGINS = {
        'diameter': ['binned_distribution', 'basic_stats', 'percentiles'],
        'height': ['binned_distribution', 'basic_stats'],
        'species_name': ['top_ranking', 'diversity_indices'],
        'coordinates': ['spatial_clustering', 'heatmap'],
        # ... 30+ mappings
    }

    def generate_params(self, plugin: str, data: pd.Series) -> Dict:
        """Génère paramètres intelligents"""
        # Auto-calcul bins (Sturges' rule)
        # Top-n adaptatif
        # Seuils basés sur distribution
```

**Intégration** :
- [ ] Analyser tous les plugins existants
- [ ] Extraire schémas Pydantic
- [ ] Créer mappings type→plugin
- [ ] Implémenter génération params

#### Semaine 4 : Transform Config Generator

**Module** : `src/niamoto/core/transforms/generator.py`

Fonctionnalités :
- [ ] Détection colonnes → plugins compatibles
- [ ] Paramètres auto-calculés
- [ ] Validation avec schémas
- [ ] Suggestions multiples avec scores

### Phase 3 : Pipeline Unifié UI (Semaines 5-6)

#### Semaine 5 : Interface ReactFlow

**Composants React** :

1. **ImportNode** : Upload + détection ML
2. **TransformNode** : Plugins auto-suggérés
3. **ExportNode** : Widgets 1:1
4. **LinkEdge** : Relations visuelles

**Process 6 étapes** :

```text
interface PipelineSteps {
  1: 'Upload files',        // Drag & drop
  2: 'Detect types',         // ML analysis
  3: 'Confirm links',        // Validate relationships
  4: 'Configure aggregations', // Group-by suggestions
  5: 'Design widgets',       // 1 type = 1 widget
  6: 'Preview & generate'    // Final validation
}
```

#### Semaine 6 : Intégration Complète

- [ ] API endpoints unifiés
- [ ] State management (Zustand)
- [ ] Preview en temps réel
- [ ] Export configuration

### Phase 4 : Production & Tests (Semaines 7-8)

#### Semaine 7 : Modèle Production

**Training final** :
- [ ] 50,000+ exemples
- [ ] Multi-langue support
- [ ] Cross-validation extensive
- [ ] Métriques détaillées

**Optimisations** :
- [ ] Quantization pour taille réduite
- [ ] Caching predictions
- [ ] Batch processing

#### Semaine 8 : Tests & Documentation

**Tests** :
- [ ] Unit tests (>90% coverage)
- [ ] Integration tests
- [ ] Performance benchmarks
- [ ] User acceptance tests

**Documentation** :
- [ ] Guide utilisateur
- [ ] API reference
- [ ] Tutoriels vidéo
- [ ] FAQ

## 🔧 Architecture Technique

### Flux de Données

```mermaid
graph LR
    Files[Data Files] --> Upload[File Upload]
    Upload --> Profiler[Data Profiler]
    Profiler --> ML[ML Detector]
    ML --> Config[Config Generator]
    Config --> UI[UI Preview]
    UI --> User[User Validation]
    User --> Pipeline[Niamoto Pipeline]
```

### Stack Technologique

- **ML** : scikit-learn, pandas, numpy
- **Backend** : FastAPI, SQLAlchemy
- **Frontend** : React 19, TypeScript, ReactFlow
- **UI** : Tailwind v4, shadcn/ui
- **Data** : CSV, JSON, GeoJSON, Shapefile

### Modules Clés

```
src/niamoto/
├── core/
│   ├── imports/
│   │   ├── ml_detector.py      # ML detection
│   │   ├── profiler.py         # Data profiling
│   │   ├── auto_detector.py    # Orchestration
│   │   └── bootstrap.py        # Bootstrap system
│   └── transforms/
│       ├── introspector.py     # NEW: Plugin introspection
│       └── generator.py        # NEW: Config generation
└── gui/
    ├── api/routers/
    │   └── bootstrap.py         # API endpoints
    └── ui/src/components/
        └── pipeline/
            └── Bootstrap.tsx    # UI components
```

## 📈 Plan de Collecte de Données

### Sources Prioritaires

1. **GBIF** (Global Biodiversity Information Facility)
   - 10,000 occurrences multi-espèces
   - Focus : Nouvelle-Calédonie + régions tropicales
   - Types : taxonomy, coordinates, dates

2. **FIA** (Forest Inventory Analysis - USA)
   - 5,000 plots forestiers
   - Types : DBH, height, biomass, mortality

3. **TRY** (Plant Trait Database)
   - 3,000 traits mesurés
   - Types : leaf_area, wood_density, SLA

4. **WorldClim**
   - 2,000 points climatiques
   - Types : temperature, rainfall, seasonality

5. **Données Locales NC**
   - AMAP, IRD, IAC
   - Focus : Espèces endémiques

### Augmentation Données

```python
# Stratégies d'augmentation
augmentations = {
    'units': {
        'DBH': ['cm', 'mm', 'inches'],
        'height': ['m', 'ft', 'cm'],
        'temperature': ['°C', '°F', 'K']
    },
    'formats': {
        'date': ['ISO', 'US', 'EU', 'timestamp'],
        'coordinates': ['decimal', 'DMS', 'UTM']
    },
    'quality': {
        'missing': [0.1, 0.2, 0.3],  # % NaN
        'noise': [0.01, 0.05, 0.1]   # Gaussian noise
    }
}
```

## 🎓 Formation du Modèle

### Architecture ML

```python
# Configuration Random Forest optimisée
model_config = {
    'n_estimators': 200,        # Plus d'arbres
    'max_depth': 15,            # Profondeur adaptée
    'min_samples_split': 5,
    'min_samples_leaf': 2,
    'max_features': 'sqrt',
    'class_weight': 'balanced',  # Gérer déséquilibre
    'n_jobs': -1                # Parallélisation
}

# Features groups (Total: 50+ features)
feature_groups = {
    'statistical': 20,   # mean, std, skew, kurtosis, etc.
    'distribution': 10,  # bins, percentiles
    'pattern': 10,      # regex matches
    'ecological': 15,   # domain-specific
    'contextual': 10    # table-level
}
```

### Pipeline d'Entraînement

```bash
# 1. Collecte données
python scripts/collect_training_data.py --sources all --limit 50000

# 2. Préparation
python scripts/prepare_dataset.py --augment --balance

# 3. Entraînement
python scripts/train_ml_detector.py --cv 5 --optimize

# 4. Évaluation
python scripts/evaluate_model.py --metrics all

# 5. Export production
python scripts/export_model.py --format pickle --compress
```

## 📊 Métriques de Suivi

### KPIs Hebdomadaires

| Métrique | Semaine 1 | Semaine 2 | ... | Semaine 8 | Cible |
|----------|-----------|-----------|-----|-----------|-------|
| ML Accuracy | 85% | 88% | ... | 92% | >90% |
| Types détectés | 14 | 20 | ... | 35 | 30+ |
| Bootstrap time | 45s | 40s | ... | 25s | <30s |
| Tests coverage | 60% | 70% | ... | 95% | >90% |
| Docs complétude | 40% | 50% | ... | 100% | 100% |

### Critères de Succès

✅ **Phase 1** : Format générique fonctionnel, ML >88% accuracy
✅ **Phase 2** : Transform auto-génération opérationnelle
✅ **Phase 3** : UI pipeline complet et intuitif
✅ **Phase 4** : Production-ready, docs complètes

## 🚀 Quick Wins Immédiats

### Cette Semaine

1. **Organiser documentation**
   - Créer structure claire dans `docs/`
   - Consolider docs éparpillées
   - README pour chaque module

2. **Script collecte GBIF**
   - API calls automatisés
   - 1000 exemples pour test
   - Validation format

3. **Fix format import.yml**
   - Support noms libres
   - Backward compatibility
   - Tests migration

4. **UI Bootstrap amélioration**
   - Afficher confidence ML
   - Edition inline
   - Export YAML

## 📝 Documentation à Créer

### Priorité Haute
- [ ] `docs/ml-detection/overview.md` - Vue d'ensemble système
- [ ] `docs/ml-detection/training-guide.md` - Guide entraînement
- [ ] `docs/bootstrap/quickstart.md` - Démarrage rapide

### Priorité Moyenne
- [ ] `docs/api/ml-detector.md` - API reference
- [ ] `docs/guides/custom-types.md` - Ajouter types custom
- [ ] `docs/troubleshooting/ml-issues.md` - Debug ML

### Priorité Basse
- [ ] Vidéos tutoriels
- [ ] Blog posts techniques
- [ ] Présentations

## 🎯 Prochaines Étapes

### Immédiat (Cette semaine)
1. ✅ Créer ce document roadmap
2. ⬜ Organiser documentation existante
3. ⬜ Script collecte données GBIF
4. ⬜ Fix format import.yml

### Court terme (2 semaines)
1. ⬜ Entraîner modèle v2 avec données réelles
2. ⬜ Implémenter introspection Pydantic
3. ⬜ Prototype UI pipeline unifié

### Moyen terme (1 mois)
1. ⬜ Pipeline complet fonctionnel
2. ⬜ Tests utilisateurs
3. ⬜ Documentation complète

### Long terme (2 mois)
1. ⬜ Release v1.0
2. ⬜ Formation utilisateurs
3. ⬜ Collecte feedback production

## 💡 Innovations Futures

### V2 Possibilities
- **LLM Integration** : GPT pour suggestions contextuelles
- **AutoML** : Optimisation automatique hyperparamètres
- **Transfer Learning** : Modèles pré-entraînés par domaine
- **Active Learning** : Amélioration continue avec feedback
- **Multi-modal** : Support images (herbarium scans)

## 📞 Contacts & Ressources

### Équipe
- **ML Lead** : À définir
- **UI/UX** : À définir
- **Data** : À définir

### Ressources Externes
- [GBIF API](https://www.gbif.org/developer)
- [scikit-learn Docs](https://scikit-learn.org)
- [ReactFlow Examples](https://reactflow.dev/examples)

### Références
- Sherlock (MIT, 2019) - Semantic type detection
- Pythagoras (2024) - GNN approach
- GitTables (2023) - Benchmark dataset

---

*Document maintenu par l'équipe Niamoto - Dernière mise à jour : Décembre 2024*
