# Guide d'utilisation et modification du détecteur ML

## 🧪 Comment tester le détecteur

### 1. Test rapide avec le modèle existant

```bash
# Depuis le répertoire Niamoto
cd /Users/julienbarbe/Dev/Niamoto/Niamoto

# Test direct du détecteur
uv run python -c "
import pandas as pd
import numpy as np
from src.niamoto.core.imports.ml_detector import MLColumnDetector

# Charger le modèle
detector = MLColumnDetector()
detector.load_model('models/column_detector.pkl')

# Tester sur des données
dbh_data = pd.Series([15.5, 23.2, 45.1, 67.3])  # Valeurs DBH-like
print('DBH test:', detector.predict(dbh_data))

species_data = pd.Series(['Araucaria columnaris', 'Agathis montana'])
print('Species test:', detector.predict(species_data))
"
```

### 2. Test avec des CSV réels

```bash
# Créer un fichier test avec colonnes mal nommées
cat > test_data.csv << EOF
X1,toto,machin,truc
15.5,Araucaria columnaris,12.3,0.65
23.2,Agathis montana,18.5,0.72
45.1,Podocarpus minor,25.2,0.58
EOF

# Tester avec le profiler
uv run python -c "
from pathlib import Path
from src.niamoto.core.imports.profiler import DataProfiler
from src.niamoto.core.imports.ml_detector import MLColumnDetector

# Créer profiler avec ML
ml = MLColumnDetector()
ml.load_model('models/column_detector.pkl')
profiler = DataProfiler(ml_detector=ml)

# Analyser le fichier
profile = profiler.profile(Path('test_data.csv'))

# Afficher les résultats
for col in profile.columns:
    print(f'{col.name}: {col.semantic_type} (confiance: {col.confidence:.0%})')
"
```

### 3. Test dans une instance Niamoto

```bash
cd test-instance/niamoto-og

# Tester sur de vraies données
uv run python -c "
import pandas as pd
from pathlib import Path
import sys
sys.path.insert(0, '../../src')

from niamoto.core.imports.ml_detector import MLColumnDetector

# Charger vos données
df = pd.read_csv('imports/occurrences.csv')

# Tester le détecteur
detector = MLColumnDetector()
detector.load_model('../../models/column_detector.pkl')

for col in df.columns[:5]:  # Tester les 5 premières colonnes
    pred_type, confidence = detector.predict(df[col])
    print(f'{col}: {pred_type} ({confidence:.0%})')
"
```

### 4. Lancer les tests unitaires

```bash
# Tests du détecteur ML
uv run pytest tests/core/imports/test_ml_detector.py -v

# Tests d'intégration avec le profiler
uv run pytest tests/core/imports/test_profiler_ml.py -v

# Tous les tests imports
uv run pytest tests/core/imports/ -v
```

## 🔧 Comment modifier le détecteur

### 1. Ajouter un nouveau type de colonne

**Étape 1: Modifier la configuration** (`src/niamoto/core/imports/ml_detector.py`)

```python
@dataclass
class ColumnTypeConfig:
    TYPES = [
        'diameter',
        'height',
        # Ajouter votre nouveau type ici
        'basal_area',      # <-- NOUVEAU
        'crown_diameter',  # <-- NOUVEAU
        # ...
    ]
```

**Étape 2: Ajouter des données d'entraînement** (`scripts/train_column_detector.py`)

```python
def generate_synthetic_training_data():
    # ... code existant ...

    # Ajouter des exemples pour basal_area
    logger.info("Generating basal area examples...")
    for i in range(30):
        size = np.random.randint(50, 300)
        # Basal area en m² (généralement 0.001 à 10)
        basal_area = np.random.gamma(shape=2, scale=0.5, size=size)
        basal_area = np.clip(basal_area, 0.001, 10)
        training_data.append((pd.Series(basal_area), 'basal_area'))
```

**Étape 3: Mapper vers type sémantique** (`src/niamoto/core/imports/profiler.py`)

```python
ml_to_semantic_map = {
    # ... mappings existants ...
    'basal_area': 'measurement.basal_area',
    'crown_diameter': 'measurement.crown_diameter',
}
```

**Étape 4: Ré-entraîner le modèle**

```bash
uv run python scripts/train_column_detector.py
```

### 2. Améliorer la détection d'un type existant

**Option A: Ajouter plus de features**

```python
def _extract_numeric_features(self, series: pd.Series) -> List[float]:
    features = []

    # Features existantes...

    # NOUVELLES features pour améliorer la détection
    # Ex: coefficient de variation pour mieux détecter DBH
    cv = series.std() / series.mean() if series.mean() > 0 else 0
    features.append(cv)

    # Asymétrie log-normale (typique pour DBH)
    log_skew = np.log(series[series > 0]).skew() if (series > 0).any() else 0
    features.append(log_skew)

    # N'oubliez pas d'ajuster N_FEATURES dans ColumnTypeConfig !
```

**Option B: Améliorer les règles de fallback**

```python
def _rule_based_detection(self, series: pd.Series, return_all: bool = False):
    if pd.api.types.is_numeric_dtype(series):
        clean = series.dropna()

        # Améliorer la détection DBH
        if 5 < clean.mean() < 100 and clean.max() < 500:
            # Vérifier aussi la distribution log-normale
            log_data = np.log(clean[clean > 0])
            if abs(log_data.skew()) < 0.5:  # Log-normal typique
                result = ('diameter', 0.85)  # Confiance augmentée
```

### 3. Utiliser des données réelles pour l'entraînement

```python
# Modifier scripts/train_column_detector.py

def load_real_data_if_available():
    """Charger vos propres données annotées"""

    real_data = []

    # Charger un fichier avec colonnes connues
    your_file = Path("data/annotated_columns.csv")
    if your_file.exists():
        df = pd.read_csv(your_file)

        # Mapper les colonnes que vous connaissez
        column_mappings = {
            'dbh_cm': 'diameter',
            'hauteur_m': 'height',
            'nom_espece': 'species_name',
            'surface_foliaire': 'leaf_area',
            # ... vos colonnes
        }

        for col_name, col_type in column_mappings.items():
            if col_name in df.columns:
                real_data.append((df[col_name], col_type))

    return real_data
```

### 4. Ajuster les hyperparamètres du modèle

```python
# Dans ml_detector.py, ligne 76
self.model = RandomForestClassifier(
    n_estimators=200,      # Augmenter pour plus de précision (était 100)
    max_depth=15,          # Augmenter pour capturer plus de complexité (était 10)
    min_samples_split=3,   # Réduire pour plus de sensibilité (était 5)
    min_samples_leaf=1,    # Réduire pour plus de détail (était 2)
    random_state=42,
    n_jobs=-1
)
```

### 5. Tester vos modifications

```python
# Script de test personnalisé
cat > test_my_changes.py << 'EOF'
#!/usr/bin/env python
"""Tester mes modifications du détecteur"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
sys.path.insert(0, 'src')

from niamoto.core.imports.ml_detector import MLColumnDetector

# 1. Créer des données de test pour votre nouveau type
test_data = {
    'basal_area': pd.Series(np.random.gamma(2, 0.5, 100)),
    'crown_diameter': pd.Series(np.random.normal(5, 2, 100)),
}

# 2. Entraîner un nouveau modèle
detector = MLColumnDetector()
training_data = []

for col_type, data in test_data.items():
    # Créer plusieurs exemples
    for _ in range(10):
        sample = data.sample(50)
        training_data.append((sample, col_type))

# Ajouter des types existants
training_data.append((pd.Series(np.random.lognormal(3, 0.8, 50)), 'diameter'))

detector.train(training_data)

# 3. Tester la détection
print("Test de détection:")
for col_type, data in test_data.items():
    pred, conf = detector.predict(data)
    print(f"  {col_type}: détecté comme {pred} ({conf:.0%})")

# 4. Sauvegarder si satisfait
detector.save_model(Path('models/column_detector_custom.pkl'))
EOF

uv run python test_my_changes.py
```

## 📊 Analyser les performances

```python
# Script pour analyser les erreurs
cat > analyze_errors.py << 'EOF'
import pandas as pd
from sklearn.metrics import confusion_matrix
import seaborn as sns
import matplotlib.pyplot as plt

# Charger vos données de test
# ...

# Créer matrice de confusion
cm = confusion_matrix(y_true, y_pred)
sns.heatmap(cm, annot=True)
plt.show()

# Identifier les cas problématiques
errors = [(true, pred, data) for true, pred, data in zip(y_true, y_pred, X_test) if true != pred]
print(f"Erreurs: {len(errors)}/{len(y_true)}")
for true, pred, sample in errors[:5]:
    print(f"  Attendu: {true}, Prédit: {pred}")
    print(f"  Features: {sample[:5]}...")  # Premières features
EOF
```

## 🚀 Workflow complet de modification

1. **Backup du modèle existant**
   ```bash
   cp models/column_detector.pkl models/column_detector_backup.pkl
   ```

2. **Modifier le code** (voir sections ci-dessus)

3. **Ré-entraîner**
   ```bash
   uv run python scripts/train_column_detector.py
   ```

4. **Tester**
   ```bash
   uv run pytest tests/core/imports/test_ml_detector.py -v
   ```

5. **Valider sur données réelles**
   ```bash
   # Tester sur vos vraies données
   uv run python test_my_changes.py
   ```

6. **Commit si satisfait**
   ```bash
   git add -A
   git commit -m "feat: amélioration détection ML pour [votre changement]"
   ```

## 💡 Tips

- **Logs**: Activer les logs pour debug
  ```python
  import logging
  logging.basicConfig(level=logging.DEBUG)
  ```

- **Visualiser les features**:
  ```python
  features = detector.extract_features(your_series)
  print("Features:", features)
  print("Feature names:", detector._get_feature_names())
  ```

- **Tester sans ré-entraîner**:
  ```python
  # Utiliser le fallback rule-based
  detector = MLColumnDetector()  # Sans charger de modèle
  result = detector.predict(your_data)  # Utilisera les règles
  ```

- **Comparer avant/après**:
  ```python
  old_detector = MLColumnDetector()
  old_detector.load_model('models/column_detector_backup.pkl')

  new_detector = MLColumnDetector()
  new_detector.load_model('models/column_detector.pkl')

  # Comparer sur mêmes données
  old_pred = old_detector.predict(test_data)
  new_pred = new_detector.predict(test_data)
  print(f"Ancien: {old_pred}, Nouveau: {new_pred}")
  ```
