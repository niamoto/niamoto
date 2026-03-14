# Évaluation et Amélioration du Système ML de Détection de Colonnes

> **Statut**: En attente - Priorité actuelle aux templates
> **Date**: 2024-11
> **Contexte**: Le système de templates atteint 88.9% recall, l'amélioration ML est reportée

## Contexte

L'objectif est d'évaluer le système ML existant de détection sémantique des colonnes et de planifier son amélioration en se basant sur l'état de l'art.

---

## 1. Analyse du Système Actuel

### 1.1 Architecture Technique

| Composant | Implémentation | Fichier |
|-----------|----------------|---------|
| Algorithme | Random Forest (100 arbres, max_depth=10) | `ml_detector.py` |
| Features | 21 features statistiques/patterns | `ml_detector.py:126-227` |
| Entraînement | ~480 exemples synthétiques | `scripts/train_column_detector.py` |
| Modèle | `models/column_detector.pkl` (635 KB) | - |
| Intégration | Via `DataProfiler._detect_semantic_type()` | `profiler.py:244-273` |

### 1.2 Features Extraites (21 total)

**Numériques (14 + 7 padding):**
- Statistiques de base: mean, std, min, max, Q25, Q50, Q75, range
- Distribution: skewness, kurtosis, unique_ratio
- Patterns: proportion positive/integer/negative
- Flags: is_longitude, is_latitude, is_density
- Histogramme: 4 bins normalisés

**Texte (11 + 10 padding):**
- Statistiques: longueur moyenne, espaces, majuscules, chiffres
- Patterns: binomial (Genus species), famille (-aceae), localisation

### 1.3 Types Détectés (14 classes)

```
diameter, height, leaf_area, wood_density, species_name, family_name,
genus_name, location, latitude, longitude, date, count, identifier, other
```

### 1.4 Limitations Identifiées

| Limitation | Impact | Sévérité |
|------------|--------|----------|
| **Données synthétiques uniquement** | Pas de patterns réels | Critique |
| **21 features seulement** | vs 1,588 dans Sherlock | Majeur |
| **Pas de contexte table** | Ignore colonnes adjacentes | Majeur |
| **Hardcoding NC** | Lat -23/-19.5, Lon 163.5/169 | Moyen |
| **Seuil confiance fixe** | 0.6-0.7 pour tous les types | Mineur |
| **ML non intégré** | Templates API bypass le ML | Critique |

---

## 2. État de l'Art - Comparaison

### 2.1 Systèmes de Référence

| Système | Année | F1 Score | Features | Données | Approche |
|---------|-------|----------|----------|---------|----------|
| **Niamoto** | 2024 | ? | 21 | 480 synth | Random Forest |
| Sherlock | 2019 | 0.89 | 1,588 | 686K | Deep NN |
| Sato | 2020 | 0.925 | + LDA + CRF | 686K | Contexte table |
| DCoM | 2021 | 0.925 | Raw NLP | 686K | LSTM |
| AdaTyper | 2023 | Adaptatif | Hybrid | GitTables | Weak supervision |

### 2.2 Techniques Clés Manquantes

1. **Features caractère** - N-grams, fréquences de caractères spéciaux
2. **Word embeddings** - Représentation sémantique des valeurs
3. **Contexte table** - LDA topics, CRF entre colonnes
4. **Weak supervision** - Apprentissage continu des corrections

---

## 3. Plan d'Évaluation

### Phase 1: Benchmark du Système Actuel

**Script: `scripts/evaluate_ml_detector.py`**

```python
# 1. Charger les données réelles de test-instance/niamoto-nc
# 2. Créer un ground truth manuel (30-50 colonnes)
# 3. Comparer prédictions ML vs pattern-based vs ground truth
# 4. Calculer métriques: Precision, Recall, F1 par classe

Métriques à collecter:
- Accuracy globale
- F1 macro (moyenne non pondérée)
- F1 weighted (pondéré par fréquence)
- Matrice de confusion
- Temps d'inférence
```

**Datasets de test:**
- `test-instance/niamoto-nc/imports/occurrences.csv` (~30 colonnes)
- `test-instance/niamoto-nc/imports/plots.csv` (~10 colonnes)
- `test-instance/niamoto-test/` (si disponible)

### Phase 2: Analyse des Erreurs

```python
# Pour chaque erreur de classification:
# - Type attendu vs prédit
# - Features extraites
# - Confiance du modèle
# - Raison probable (feature manquante, confusion de classe)
```

### Phase 3: Comparaison ML vs Templates

```
Comparer sur les mêmes données:
1. Détection ML seule (ml_detector.py)
2. Détection patterns seule (profiler.py)
3. Détection templates (template_suggester.py)
4. Combinaison optimale
```

---

## 4. Options d'Amélioration

### Option A: Amélioration Incrémentale (Recommandé pour MVP)

**Effort: 2-3 jours**

1. **Intégrer ML dans le flux actuel**
   - Modifier `templates.py` pour utiliser `DataProfiler._profile_column()`
   - Propager `semantic_type` et `confidence` du ML

2. **Enrichir les features (21 → 50)**
   - Ajouter character-level features (fréquences ponctuation)
   - Ajouter entropy de la distribution
   - Ajouter pattern regex spécifiques domaine

3. **Créer un dataset d'entraînement réel**
   - Labelliser manuellement 200-300 colonnes de données écologiques
   - Mixer 70% réel + 30% synthétique
   - Stratifier par type

4. **Améliorer les seuils**
   - Seuil adaptatif par type (0.5 pour `other`, 0.8 pour `latitude`)
   - Log des prédictions pour analyse continue

### Option B: Refonte avec Sherlock-lite

**Effort: 1-2 semaines**

1. **Implémenter ~200 features Sherlock**
   - Character distributions (26 features)
   - Word embeddings (100 features via sentence-transformers)
   - Statistical features (50 features)
   - Domain-specific patterns (20 features)

2. **Utiliser un modèle plus robuste**
   - Gradient Boosting (XGBoost/LightGBM)
   - Ou MLP simple (3 couches)

3. **Ajouter contexte table (Sato-style)**
   - LDA pour capturer le "sujet" de la table
   - Features de colonnes adjacentes

### Option C: Approche LLM/Embeddings (Futur)

**Effort: 2-4 semaines**

1. **Utiliser embeddings pré-entraînés**
   - Sentence-transformers pour valeurs textuelles
   - Classification par similarité cosinus

2. **Few-shot avec LLM**
   - Prompt engineering pour classification
   - Utile pour types rares

---

## 5. Données Nécessaires

### 5.1 Données Réelles Disponibles

| Source | Colonnes | Usage |
|--------|----------|-------|
| `niamoto-nc/occurrences.csv` | ~30 | Test principal |
| `niamoto-nc/plots.csv` | ~10 | Test plots |
| `niamoto-nc/shapes.csv` | ~8 | Test shapes |
| `niamoto-test/` | Variable | Validation |

### 5.2 Données à Créer

**Ground Truth Manuel (prioritaire):**
- 50-100 colonnes labellisées manuellement
- Format: `{column_name, source_file, true_type, notes}`
- Types: diameter, height, elevation, species, coordinates, etc.

**Données Synthétiques Améliorées:**
- Plus de diversité dans les distributions
- Patterns de données réelles observés
- Bruitage réaliste (valeurs manquantes, outliers)

### 5.3 Sources Externes Potentielles

- **GBIF Darwin Core** - Standards de noms de colonnes
- **TRY Plant Trait Database** - Types de traits écologiques
- **VizNet** (Sherlock) - Corpus générique (686K colonnes)

---

## 6. Métriques de Succès

### Court terme
- [ ] Benchmark établi avec scores de base
- [ ] ML intégré dans le flux Smart Setup V2
- [ ] F1 weighted > 0.75 sur données réelles NC

### Moyen terme
- [ ] Dataset réel labellisé (200+ colonnes)
- [ ] F1 weighted > 0.85
- [ ] Feedback loop: corrections utilisateur → réentraînement

### Long terme
- [ ] F1 weighted > 0.90
- [ ] Support multi-domaines (pas seulement NC)
- [ ] Contexte table intégré

---

## 7. Fichiers à Modifier/Créer

### Évaluation
- `scripts/evaluate_ml_detector.py` - **Créer** - Benchmark complet
- `scripts/create_ground_truth.py` - **Créer** - Helper labellisation
- `tests/core/imports/test_ml_benchmark.py` - **Créer** - Tests de régression

### Amélioration ML
- `src/niamoto/core/imports/ml_detector.py` - **Modifier** - Nouvelles features
- `scripts/train_column_detector.py` - **Modifier** - Données réelles
- `data/training/ground_truth.json` - **Créer** - Labels manuels

### Intégration
- `src/niamoto/gui/api/routes/templates.py` - **Modifier** - Utiliser ML
- `src/niamoto/core/imports/template_suggester.py` - **Modifier** - Combiner ML + templates

---

## 8. Questions à Résoudre (Avant Implémentation)

1. **Effort d'annotation acceptable?**
   - 50 colonnes (1-2h) - minimum viable
   - 200 colonnes (1 jour) - robuste
   - 500+ colonnes (multi-jours) - optimal

2. **Scope géographique?**
   - Nouvelle-Calédonie uniquement?
   - Généralisation mondiale?

3. **Dépendances ML acceptables?**
   - scikit-learn (actuel) - léger
   - sentence-transformers - plus lourd (~400MB)
   - LLM API - dépendance externe

---

## Références

- [Sherlock Paper (2019)](https://arxiv.org/abs/1905.10688) - A Deep Learning Approach to Semantic Data Type Detection
- [Sato Paper (2020)](https://arxiv.org/abs/2004.02430) - Context-Aware Semantic Type Detection in Tables
- [VizNet Dataset](https://github.com/mitmedialab/viznet) - 31M+ columns for training
- [GitTables](https://gittables.github.io/) - 1M+ tables from GitHub
