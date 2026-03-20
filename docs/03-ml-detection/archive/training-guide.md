# Guide d'Entraînement du Modèle ML Column Detector

## Vue d'Ensemble

Ce guide détaille le processus complet d'entraînement du modèle de détection automatique de types de colonnes pour Niamoto. Le modèle utilise un Random Forest pour classifier 30+ types écologiques avec une précision cible >90%.

## Prérequis

### Dépendances
```bash
pip install scikit-learn pandas numpy scipy requests tqdm
```

### Données Nécessaires
- Minimum 10,000 exemples étiquetés
- Distribution équilibrée entre types
- Sources variées (GBIF, FIA, données locales)

## 📊 Pipeline d'Entraînement Complet

### Étape 1 : Collecte de Données

#### 1.1 Collecte Automatique
```bash
# Collecter 10,000 exemples depuis toutes sources
python scripts/collect_training_data.py --source all --limit 10000

# Collecter uniquement depuis GBIF
python scripts/collect_training_data.py --source gbif --limit 2000

# Collecter données locales
python scripts/collect_training_data.py --source local --limit 2000
```

#### 1.2 Sources de Données

| Source | Type | Volume | Commande |
|--------|------|--------|----------|
| **GBIF** | API | 10M+ | `--source gbif` |
| **Local** | CSV | Variable | `--source local` |
| **Synthetic** | Généré | Illimité | `--source synthetic` |
| **Augmented** | Dérivé | 5x existant | Automatique |

#### 1.3 Validation Données
```python
# Vérifier la qualité des données collectées
import pickle
import pandas as pd

# Charger données
with open('data/ml_training/training_data_20241215_120000.pkl', 'rb') as f:
    training_data = pickle.load(f)

# Analyser distribution
type_counts = {}
for series, label in training_data:
    type_counts[label] = type_counts.get(label, 0) + 1

# Afficher statistiques
for type_name, count in sorted(type_counts.items()):
    print(f"{type_name:20} : {count:5} exemples")
```

### Étape 2 : Préparation des Données

#### 2.1 Script de Préparation
```python
# scripts/prepare_training_data.py

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import pickle

def prepare_dataset(training_data_path):
    """Prépare le dataset pour l'entraînement."""

    # Charger données
    with open(training_data_path, 'rb') as f:
        training_data = pickle.load(f)

    # Extraire features
    X = []
    y = []

    from niamoto.core.imports.ml_detector import MLColumnDetector
    detector = MLColumnDetector()

    for series, label in training_data:
        features = detector.extract_features(series)
        X.append(features)
        y.append(label)

    X = np.array(X)
    y = np.array(y)

    # Split train/validation/test
    X_temp, X_test, y_temp, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp, test_size=0.2, random_state=42, stratify=y_temp
    )

    # Normalisation
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_val = scaler.transform(X_val)
    X_test = scaler.transform(X_test)

    return {
        'X_train': X_train, 'y_train': y_train,
        'X_val': X_val, 'y_val': y_val,
        'X_test': X_test, 'y_test': y_test,
        'scaler': scaler
    }
```

#### 2.2 Features Extraites (21 total)

**Features Numériques** :
1. Moyenne
2. Écart-type
3. Minimum
4. Maximum
5. Quartile 25%
6. Médiane
7. Quartile 75%
8. Range
9. Skewness
10. Kurtosis
11. Ratio valeurs uniques
12. % positifs
13. % entiers
14. % négatifs
15. Est longitude possible
16. Est latitude possible
17. Est densité possible
18-21. Histogram bins (4 bins)

**Features Texte** :
1. Longueur moyenne
2. Écart-type longueur
3. Nombre mots moyens
4. Majuscules moyennes
5. Minuscules moyennes
6. Chiffres moyens
7. Ratio unique
8. Tirets moyens
9. Pattern binomial
10. Pattern famille
11. Pattern localisation
12-21. Padding zéros

### Étape 3 : Entraînement du Modèle

#### 3.1 Configuration Optimale
```python
# Configuration Random Forest optimisée
from sklearn.ensemble import RandomForestClassifier

model_config = {
    'n_estimators': 200,        # Nombre d'arbres
    'max_depth': 15,            # Profondeur max
    'min_samples_split': 5,     # Split minimum
    'min_samples_leaf': 2,      # Feuilles minimum
    'max_features': 'sqrt',     # Features par split
    'class_weight': 'balanced', # Gérer déséquilibre
    'random_state': 42,
    'n_jobs': -1,              # Parallélisation
    'verbose': 1
}

model = RandomForestClassifier(**model_config)
```

#### 3.2 Script d'Entraînement Complet
```python
# scripts/train_ml_model.py

import pickle
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, classification_report,
    confusion_matrix, f1_score
)
import matplotlib.pyplot as plt
import seaborn as sns

def train_model(data_dict):
    """Entraîne le modèle Random Forest."""

    # Configuration
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        max_features='sqrt',
        class_weight='balanced',
        random_state=42,
        n_jobs=-1,
        verbose=1
    )

    # Entraînement
    print("Entraînement du modèle...")
    model.fit(data_dict['X_train'], data_dict['y_train'])

    # Validation
    y_val_pred = model.predict(data_dict['X_val'])
    val_accuracy = accuracy_score(data_dict['y_val'], y_val_pred)
    val_f1 = f1_score(data_dict['y_val'], y_val_pred, average='weighted')

    print(f"Validation Accuracy: {val_accuracy:.3f}")
    print(f"Validation F1-Score: {val_f1:.3f}")

    # Test final
    y_test_pred = model.predict(data_dict['X_test'])
    test_accuracy = accuracy_score(data_dict['y_test'], y_test_pred)
    test_f1 = f1_score(data_dict['y_test'], y_test_pred, average='weighted')

    print(f"Test Accuracy: {test_accuracy:.3f}")
    print(f"Test F1-Score: {test_f1:.3f}")

    # Rapport détaillé
    print("\nClassification Report:")
    print(classification_report(data_dict['y_test'], y_test_pred))

    return model

def save_model(model, scaler, path='models/ml_detector_v2.pkl'):
    """Sauvegarde le modèle entraîné."""
    with open(path, 'wb') as f:
        pickle.dump({
            'model': model,
            'scaler': scaler,
            'version': '2.0',
            'features': 21,
            'types': model.classes_.tolist()
        }, f)
    print(f"Modèle sauvegardé : {path}")
```

### Étape 4 : Optimisation des Hyperparamètres

#### 4.1 Grid Search
```python
from sklearn.model_selection import GridSearchCV

param_grid = {
    'n_estimators': [100, 200, 300],
    'max_depth': [10, 15, 20, None],
    'min_samples_split': [2, 5, 10],
    'min_samples_leaf': [1, 2, 4],
    'max_features': ['sqrt', 'log2', None]
}

grid_search = GridSearchCV(
    RandomForestClassifier(random_state=42),
    param_grid,
    cv=5,
    scoring='f1_weighted',
    n_jobs=-1,
    verbose=2
)

grid_search.fit(X_train, y_train)
best_params = grid_search.best_params_
```

#### 4.2 Random Search (Plus Rapide)
```python
from sklearn.model_selection import RandomizedSearchCV
from scipy.stats import randint

param_dist = {
    'n_estimators': randint(100, 500),
    'max_depth': [10, 15, 20, 25, None],
    'min_samples_split': randint(2, 20),
    'min_samples_leaf': randint(1, 10),
    'max_features': ['sqrt', 'log2', None],
    'bootstrap': [True, False]
}

random_search = RandomizedSearchCV(
    RandomForestClassifier(random_state=42),
    param_dist,
    n_iter=100,
    cv=5,
    scoring='f1_weighted',
    n_jobs=-1,
    verbose=2
)
```

### Étape 5 : Évaluation et Métriques

#### 5.1 Métriques Clés
```python
def evaluate_model(model, X_test, y_test):
    """Évaluation complète du modèle."""

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)

    metrics = {
        'accuracy': accuracy_score(y_test, y_pred),
        'f1_macro': f1_score(y_test, y_pred, average='macro'),
        'f1_weighted': f1_score(y_test, y_pred, average='weighted'),
        'precision': precision_score(y_test, y_pred, average='weighted'),
        'recall': recall_score(y_test, y_pred, average='weighted')
    }

    return metrics, y_pred, y_proba
```

#### 5.2 Matrice de Confusion
```python
def plot_confusion_matrix(y_true, y_pred, classes):
    """Affiche matrice de confusion."""

    cm = confusion_matrix(y_true, y_pred, labels=classes)

    plt.figure(figsize=(15, 12))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=classes, yticklabels=classes)
    plt.title('Matrice de Confusion')
    plt.ylabel('Vrais Labels')
    plt.xlabel('Prédictions')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('confusion_matrix.png')
    plt.show()
```

#### 5.3 Importance des Features
```python
def plot_feature_importance(model, feature_names):
    """Affiche importance des features."""

    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1][:15]  # Top 15

    plt.figure(figsize=(10, 6))
    plt.title("Importance des Features")
    plt.bar(range(15), importances[indices])
    plt.xticks(range(15), [feature_names[i] for i in indices], rotation=45)
    plt.tight_layout()
    plt.savefig('feature_importance.png')
    plt.show()
```

### Étape 6 : Validation Croisée

#### 6.1 K-Fold Cross-Validation
```python
from sklearn.model_selection import cross_val_score, StratifiedKFold

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

cv_scores = cross_val_score(
    model, X_train, y_train,
    cv=skf,
    scoring='f1_weighted',
    n_jobs=-1
)

print(f"CV F1-Scores: {cv_scores}")
print(f"Mean CV F1: {cv_scores.mean():.3f} (+/- {cv_scores.std() * 2:.3f})")
```

#### 6.2 Learning Curves
```python
from sklearn.model_selection import learning_curve

train_sizes, train_scores, val_scores = learning_curve(
    model, X_train, y_train,
    cv=5,
    train_sizes=np.linspace(0.1, 1.0, 10),
    scoring='f1_weighted',
    n_jobs=-1
)

plt.figure(figsize=(10, 6))
plt.plot(train_sizes, train_scores.mean(axis=1), label='Train')
plt.plot(train_sizes, val_scores.mean(axis=1), label='Validation')
plt.xlabel('Training Set Size')
plt.ylabel('F1 Score')
plt.legend()
plt.title('Learning Curves')
plt.savefig('learning_curves.png')
```

## 📈 Workflow Complet

### Script Master
```bash
#!/bin/bash
# train_pipeline.sh

# 1. Collecte données
echo "=== Collecte de données ==="
python scripts/collect_training_data.py --source all --limit 10000

# 2. Préparation
echo "=== Préparation dataset ==="
python scripts/prepare_training_data.py

# 3. Entraînement
echo "=== Entraînement modèle ==="
python scripts/train_ml_model.py

# 4. Évaluation
echo "=== Évaluation ==="
python scripts/evaluate_model.py

# 5. Export production
echo "=== Export production ==="
python scripts/export_production_model.py

echo "=== Pipeline terminé ==="
```

## 🎯 Objectifs de Performance

| Métrique | Minimum | Cible | Excellence |
|----------|---------|-------|------------|
| **Accuracy** | 85% | 90% | 95%+ |
| **F1-Score** | 0.83 | 0.88 | 0.93+ |
| **Precision** | 0.85 | 0.90 | 0.95+ |
| **Recall** | 0.85 | 0.90 | 0.95+ |
| **Temps inférence** | <200ms | <100ms | <50ms |
| **Taille modèle** | <10MB | <5MB | <2MB |

## 🔧 Optimisations Avancées

### 1. Feature Engineering
```python
# Ajout de features dérivées
def add_derived_features(features):
    """Ajoute features calculées."""
    # Ratio mean/std
    features.append(features[0] / (features[1] + 1e-6))

    # Log transformations
    features.append(np.log1p(features[0]))

    # Polynomiales
    features.append(features[0] ** 2)

    return features
```

### 2. Ensemble Methods
```python
from sklearn.ensemble import VotingClassifier
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

# Créer ensemble
ensemble = VotingClassifier([
    ('rf', RandomForestClassifier()),
    ('xgb', XGBClassifier()),
    ('lgbm', LGBMClassifier())
], voting='soft')
```

### 3. Active Learning
```python
def select_uncertain_samples(model, X_unlabeled, n_samples=100):
    """Sélectionne échantillons incertains pour annotation."""
    probas = model.predict_proba(X_unlabeled)

    # Entropie des prédictions
    entropy = -np.sum(probas * np.log(probas + 1e-6), axis=1)

    # Sélectionner top incertains
    uncertain_idx = np.argsort(entropy)[-n_samples:]

    return uncertain_idx
```

## 🚨 Problèmes Courants

### Problème 1 : Déséquilibre Classes
**Solution** :
```python
# Utiliser class_weight
model = RandomForestClassifier(class_weight='balanced')

# Ou SMOTE
from imblearn.over_sampling import SMOTE
smote = SMOTE(random_state=42)
X_balanced, y_balanced = smote.fit_resample(X_train, y_train)
```

### Problème 2 : Overfitting
**Solution** :
- Réduire `max_depth`
- Augmenter `min_samples_split`
- Plus de données
- Cross-validation

### Problème 3 : Features Corrélées
**Solution** :
```python
# Supprimer features corrélées
from sklearn.feature_selection import SelectKBest, f_classif

selector = SelectKBest(f_classif, k=15)
X_selected = selector.fit_transform(X_train, y_train)
```

## 📊 Monitoring Production

### Métriques à Surveiller
```python
def monitor_predictions(model, X_new, threshold=0.7):
    """Monitore qualité prédictions."""
    probas = model.predict_proba(X_new)
    max_probas = probas.max(axis=1)

    metrics = {
        'avg_confidence': max_probas.mean(),
        'low_confidence_pct': (max_probas < threshold).mean(),
        'predictions': model.predict(X_new)
    }

    # Alert si trop de prédictions incertaines
    if metrics['low_confidence_pct'] > 0.3:
        logger.warning("Trop de prédictions incertaines!")

    return metrics
```

## 🎓 Ressources Complémentaires

### Documentation
- [scikit-learn RandomForest](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html)
- [Feature Engineering Guide](https://feature-engine.readthedocs.io/)
- [Imbalanced-learn](https://imbalanced-learn.org/)

### Papers
- Breiman, L. (2001). Random Forests
- Sherlock (MIT, 2019). Semantic Type Detection
- Pythagoras (2024). GNN Approach

### Datasets Publics
- [GBIF](https://www.gbif.org/developer)
- [FIA](https://www.fia.fs.fed.us/)
- [TRY](https://www.try-db.org/)

---

*Guide créé : Décembre 2024*
*Dernière mise à jour : Décembre 2024*
*Auteur : Équipe Niamoto ML*
