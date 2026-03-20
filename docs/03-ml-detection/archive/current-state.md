# État Actuel du Système d'Auto-détection ML - Décembre 2024

## Résumé Exécutif

Le système d'auto-détection ML de Niamoto est actuellement implémenté à ~75% avec des composants fonctionnels mais nécessitant consolidation et intégration. Le modèle Random Forest détecte 14 types écologiques avec 85% de précision sur données synthétiques.

## 🔍 Vue d'Ensemble Technique

### Architecture Actuelle

```
Fichiers Data → Profiler → ML Detector → Auto Detector → Bootstrap → Config YAML
                    ↓           ↓             ↓              ↓
              Analyse Stats  Random Forest  Orchestration  Pipeline
```

## ✅ Composants Implémentés

### 1. ML Column Detector (`ml_detector.py`)

**Capacités** :
- Random Forest avec 100 arbres
- 21 features statistiques extraites
- Détection sans noms de colonnes
- Support données numériques et texte

**Types Détectés** (14 total) :
- **Mesures** : diameter, height, leaf_area, wood_density
- **Taxonomie** : species_name, family_name, genus_name
- **Localisation** : location, latitude, longitude
- **Temporel** : date
- **Autres** : count, identifier, other

**Performance** :
- Accuracy : ~85% sur données synthétiques
- Temps inférence : <10ms par colonne
- Taille modèle : ~5MB

**Code Exemple** :
```python
detector = MLColumnDetector()
col_type, confidence = detector.predict(df['column'])
# Returns: ('diameter', 0.92)
```

### 2. Data Profiler (`profiler.py`)

**Fonctionnalités** :
- Analyse multi-formats (CSV, Excel, GeoJSON, Shapefile)
- Détection sémantique hybride (patterns + ML)
- Profiling statistique complet
- Détection relations inter-tables

**Profil Généré** :
```python
DatasetProfile:
  - file_path: Path
  - record_count: int
  - columns: List[ColumnProfile]
  - detected_type: 'hierarchical' | 'spatial' | 'factual'
  - suggested_name: str
  - relationships: List[Dict]
  - confidence: float
```

**Patterns Détectés** :
- Taxonomie : 12 patterns (family, genus, species, etc.)
- Spatial : 8 patterns (geometry, lat/lon, coordinates)
- Identifiants : 6 patterns (id, reference, code)

### 3. Auto Detector (`auto_detector.py`)

**Rôle** : Orchestration de l'analyse complète

**Workflow** :
1. Découverte fichiers dans dossier
2. Profiling de chaque fichier
3. Détection type dataset
4. Génération configuration
5. Validation cohérence

**Configuration Générée** :
```yaml
references:
  taxonomy:  # Encore format rigide
    source: file.csv
    hierarchy: [...]
data:
  observations:
    source: data.csv
    links: [...]
```

**Limitations** :
- Format import.yml rigide (taxonomy/plots/occurrences)
- Pas de support multi-langues
- Relations simples uniquement

### 4. Bootstrap System (`bootstrap.py`)

**Pipeline Complet** :
```python
DataBootstrap:
  1. analyze_directory()    # Détection
  2. generate_config()       # Import.yml
  3. generate_transform()    # Transform.yml
  4. generate_export()       # Export.yml
  5. create_instance()       # Structure complète
```

**Capacités** :
- Bootstrap en ~45 secondes
- Génération 3 fichiers config
- Création structure instance
- Mode auto-confirm

### 5. Interface UI (`Bootstrap.tsx`)

**Composant React** :
- Wizard 4 étapes
- Drag & drop fichiers
- Affichage analyse
- Preview configuration
- Génération finale

**API Endpoints** :
- `POST /api/bootstrap/analyze` - Analyse fichiers
- `POST /api/bootstrap/generate-config` - Génération config
- `POST /api/bootstrap/save-config` - Sauvegarde

**État UI** :
- Interface fonctionnelle
- Pas intégrée au pipeline principal
- Manque feedback temps réel

## ⚠️ Points de Blocage

### 1. Format Rigide
```yaml
# Format actuel imposé
taxonomy:
  path: ...
plots:
  path: ...
occurrences:
  path: ...

# Format souhaité (libre)
references:
  [any_name]:
    source: ...
    type: ...
```

### 2. Manque Données Réelles
- Modèle entraîné sur 500 exemples synthétiques
- Pas de données GBIF/FIA/TRY
- Biais vers données Nouvelle-Calédonie

### 3. Transform Manuel
- Pas d'introspection Pydantic
- Paramètres plugins hardcodés
- Mappings type→widget simplistes

### 4. UI Fragmentée
- Bootstrap isolé du pipeline
- Pas de visualisation ReactFlow
- Preview limitée

## 📊 Métriques Actuelles

| Métrique | Valeur Actuelle | Cible | Écart |
|----------|----------------|-------|-------|
| **ML Accuracy** | 85% | >90% | -5% |
| **Types Détectés** | 14 | 30+ | -16 |
| **Bootstrap Time** | 45s | <30s | +15s |
| **Données Training** | 500 | 10,000+ | -9,500 |
| **Coverage Tests** | 60% | >90% | -30% |
| **Docs Complétude** | 40% | 100% | -60% |

## 🔧 Fichiers et Modules

### Structure Actuelle
```
src/niamoto/core/imports/
├── ml_detector.py       # ✅ 85% complet
├── profiler.py          # ✅ 90% complet
├── auto_detector.py     # ⚠️ 80% complet
├── bootstrap.py         # ⚠️ 70% complet
└── generic_importer.py  # ❌ À créer

gui/
├── api/routers/
│   └── bootstrap.py     # ✅ Fonctionnel
└── ui/src/components/
    └── pipeline/
        └── Bootstrap.tsx # ⚠️ Isolé
```

### Documentation
```
docs/
├── roadmaps/            # ✅ Multiples docs
├── architecture/        # ✅ Analyses détaillées
├── implementation/      # ⚠️ Guide ML partiel
└── references/          # ⚠️ Éparpillé
```

## 🎯 Prochaines Priorités

### Immédiat (Cette semaine)
1. **Organiser documentation** - Structure claire
2. **Collecter données GBIF** - 1000 exemples
3. **Fix format import.yml** - Support générique

### Court terme (2 semaines)
1. **Entraîner modèle v2** - Données réelles
2. **Introspection Pydantic** - Transform auto
3. **Intégrer UI pipeline** - ReactFlow

### Moyen terme (1 mois)
1. **Pipeline unifié complet**
2. **Tests coverage >90%**
3. **Documentation 100%**

## 📈 Évolution du Code

### Commits Récents
- `a581fb8` - feat: expose plugin param schemas
- `2946e7d` - feat: unified pipeline editor ReactFlow
- `81df5c6` - feat: improve Transform interface

### Branches Actives
- `feat/pipeline-editor-unified` - En cours
- `main` - Stable

### Fichiers Modifiés
- 42 fichiers changés
- +15 nouveaux modules ML
- +10 docs ajoutées

## 💼 Ressources Nécessaires

### Données
- [ ] Accès API GBIF
- [ ] Dataset FIA forestier
- [ ] TRY plant traits
- [ ] Données NC locales

### Outils
- [x] scikit-learn installé
- [x] pandas/numpy
- [ ] GPU pour training (optionnel)
- [ ] Serveur pour API enrichissement

### Temps Développeur
- Phase 1 : 2 semaines
- Phase 2 : 2 semaines
- Phase 3 : 2 semaines
- Phase 4 : 2 semaines
- **Total** : 2 mois

## 🚦 Statut Global

### Feu Vert ✅
- Architecture de base solide
- ML detector fonctionnel
- UI Bootstrap opérationnelle

### Feu Orange ⚠️
- Format configuration rigide
- Manque données training
- Documentation incomplète

### Feu Rouge ❌
- Pas d'introspection transform
- UI non unifiée
- Tests insuffisants

## 📝 Actions Critiques

1. **Migrer format générique** - Débloque tout
2. **Collecter vraies données** - Améliore accuracy
3. **Unifier UI pipeline** - UX cohérente
4. **Documenter complètement** - Adoption

---

*Synthèse générée le : Décembre 2024*
*Prochaine révision : Janvier 2025*
