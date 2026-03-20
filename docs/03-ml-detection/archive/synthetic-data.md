# Guide pour créer des données synthétiques pour le ML Detector

## 📊 Principe des données synthétiques

Les données synthétiques simulent les distributions statistiques réelles des données écologiques.
Chaque type de colonne a des caractéristiques statistiques spécifiques :

- **DBH** : Distribution log-normale, asymétrie droite, valeurs 5-500 cm
- **Height** : Distribution normale, valeurs 1-60 m
- **Species** : Nomenclature binomiale (Genre espèce)
- **Wood density** : Distribution beta, valeurs 0.2-1.2 g/cm³
- **Coordinates** : Uniformes dans des plages géographiques

## 🎯 Créer vos propres données synthétiques

### 1. Structure de base

```python
import numpy as np
import pandas as pd
from typing import List, Tuple

def generate_custom_training_data() -> List[Tuple[pd.Series, str]]:
    """Génère des données d'entraînement synthétiques."""
    training_data = []
    np.random.seed(42)  # Pour reproductibilité

    # Générer différents types de données
    # ...

    return training_data
```

### 2. Exemples de génération par type

#### DBH (Diamètre à hauteur de poitrine)

```python
def generate_dbh_examples(n_examples=50):
    """Génère des exemples de DBH réalistes."""
    training_data = []

    for i in range(n_examples):
        size = np.random.randint(100, 500)  # Nombre d'arbres

        # Distribution log-normale (typique pour DBH)
        # mean=3.0 donne une médiane ~20cm
        # sigma=0.8 donne une bonne dispersion
        dbh = np.random.lognormal(mean=3.0, sigma=0.8, size=size)

        # Limiter aux valeurs réalistes
        dbh = np.clip(dbh, 5, 300)  # 5cm min, 300cm max

        # Ajouter du bruit et valeurs manquantes (réaliste)
        if i % 3 == 0:
            n_missing = int(size * 0.1)
            missing_idx = np.random.choice(size, size=n_missing, replace=False)
            dbh[missing_idx] = np.nan

        training_data.append((pd.Series(dbh), 'diameter'))

    return training_data
```

#### Hauteur d'arbres

```python
def generate_height_examples(n_examples=50):
    """Génère des hauteurs d'arbres réalistes."""
    training_data = []

    for i in range(n_examples):
        size = np.random.randint(100, 500)

        # Distribution normale (plus symétrique que DBH)
        height = np.random.normal(loc=15, scale=5, size=size)
        height = np.clip(height, 1, 45)  # 1-45 mètres

        # Parfois ajouter une corrélation avec DBH
        if i % 2 == 0:
            # Hauteur corrélée au DBH (relation allométrique)
            dbh = np.random.lognormal(3.0, 0.8, size=size)
            height = 1.3 + 0.8 * np.log(dbh) + np.random.normal(0, 2, size=size)
            height = np.clip(height, 1, 45)

        training_data.append((pd.Series(height), 'height'))

    return training_data
```

#### Noms d'espèces

```python
def generate_species_names(n_examples=40):
    """Génère des noms d'espèces réalistes (Nouvelle-Calédonie)."""

    # Genres typiques de Nouvelle-Calédonie
    genera = [
        'Araucaria', 'Agathis', 'Podocarpus', 'Dacrydium',
        'Metrosideros', 'Syzygium', 'Eugenia', 'Acacia',
        'Nothofagus', 'Cunonia', 'Weinmannia', 'Geissois'
    ]

    # Épithètes spécifiques communs
    epithets = [
        'columnaris', 'lanceolata', 'minor', 'montana',
        'vieillardii', 'balansae', 'deplanchei', 'guillauminii'
    ]

    training_data = []

    for i in range(n_examples):
        size = np.random.randint(50, 300)

        # Générer des noms binomiaux
        species = []
        for _ in range(size):
            genus = np.random.choice(genera)
            epithet = np.random.choice(epithets)
            species.append(f"{genus} {epithet}")

        # Ajouter de la variabilité
        if i % 4 == 0:
            # Ajouter des sous-espèces
            for j in range(0, size, 5):
                species[j] += " subsp. " + np.random.choice(['minor', 'major'])

        if i % 5 == 0:
            # Ajouter des variétés
            for j in range(1, size, 7):
                species[j] += " var. " + np.random.choice(['typica', 'robusta'])

        training_data.append((pd.Series(species), 'species_name'))

    return training_data
```

#### Densité du bois

```python
def generate_wood_density(n_examples=30):
    """Génère des densités de bois réalistes."""
    training_data = []

    for i in range(n_examples):
        size = np.random.randint(50, 300)

        # Distribution beta (bornée entre 0 et 1)
        # Paramètres a=5, b=2 donnent une distribution réaliste
        wood_density = np.random.beta(a=5, b=2, size=size)

        # Ajuster à la plage réelle (0.2 - 1.2 g/cm³)
        wood_density = wood_density * 1.0 + 0.2

        # Ajouter du bruit pour certains échantillons
        if i % 3 == 0:
            noise = np.random.normal(0, 0.05, size=size)
            wood_density += noise
            wood_density = np.clip(wood_density, 0.1, 1.5)

        training_data.append((pd.Series(wood_density), 'wood_density'))

    return training_data
```

#### Coordonnées géographiques

```python
def generate_coordinates(n_examples=20):
    """Génère des coordonnées GPS réalistes."""
    training_data = []

    # Nouvelle-Calédonie bounds
    nc_lat_range = (-23.0, -19.5)
    nc_lon_range = (163.5, 169.0)

    # Latitudes
    for i in range(n_examples):
        size = np.random.randint(100, 400)

        if i % 3 == 0:
            # Coordonnées globales (pour diversité)
            lat = np.random.uniform(-90, 90, size=size)
        else:
            # Coordonnées Nouvelle-Calédonie
            lat = np.random.uniform(*nc_lat_range, size=size)

            # Ajouter clustering (points groupés)
            if i % 2 == 0:
                n_clusters = 3
                for j in range(n_clusters):
                    cluster_center = np.random.uniform(*nc_lat_range)
                    cluster_size = size // n_clusters
                    start_idx = j * cluster_size
                    end_idx = start_idx + cluster_size
                    lat[start_idx:end_idx] = np.random.normal(
                        cluster_center, 0.1, cluster_size
                    )

        training_data.append((pd.Series(lat), 'latitude'))

    # Longitudes (similaire)
    for i in range(n_examples):
        size = np.random.randint(100, 400)

        if i % 3 == 0:
            lon = np.random.uniform(-180, 180, size=size)
        else:
            lon = np.random.uniform(*nc_lon_range, size=size)

        training_data.append((pd.Series(lon), 'longitude'))

    return training_data
```

### 3. Générer des données plus complexes

#### Données avec corrélations

```python
def generate_correlated_measurements(n_examples=20):
    """Génère des mesures corrélées (DBH, hauteur, surface foliaire)."""
    training_data = []

    for i in range(n_examples):
        size = np.random.randint(100, 300)

        # Base: DBH
        dbh = np.random.lognormal(3.0, 0.8, size=size)
        dbh = np.clip(dbh, 5, 200)

        # Hauteur corrélée au DBH (relation allométrique)
        # H = a * DBH^b + erreur
        height = 1.3 * dbh ** 0.7 + np.random.normal(0, 2, size=size)
        height = np.clip(height, 1, 45)

        # Surface foliaire corrélée au DBH²
        leaf_area = 0.05 * dbh ** 2 + np.random.gamma(2, 5, size=size)
        leaf_area = np.clip(leaf_area, 0.5, 500)

        training_data.extend([
            (pd.Series(dbh), 'diameter'),
            (pd.Series(height), 'height'),
            (pd.Series(leaf_area), 'leaf_area')
        ])

    return training_data
```

#### Données avec patterns temporels

```python
def generate_temporal_data(n_examples=10):
    """Génère des données avec patterns temporels."""
    training_data = []

    for i in range(n_examples):
        size = np.random.randint(200, 500)

        # Croissance sur plusieurs années
        years = 10
        dbh_initial = np.random.lognormal(2.5, 0.6, size=size)

        for year in range(years):
            # Croissance annuelle (mm/an)
            growth_rate = np.random.gamma(2, 2, size=size) / 10
            dbh_year = dbh_initial + growth_rate * year
            dbh_year = np.clip(dbh_year, 5, 300)

            # Mortalité (certains arbres disparaissent)
            if year > 5:
                mortality = np.random.random(size=size) < 0.02
                dbh_year[mortality] = np.nan

            training_data.append((pd.Series(dbh_year), 'diameter'))

    return training_data
```

### 4. Script complet d'entraînement personnalisé

```python
#!/usr/bin/env python
"""
Script personnalisé pour entraîner le ML detector avec vos données.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ajouter src au path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from niamoto.core.imports.ml_detector import MLColumnDetector

def generate_all_training_data():
    """Génère toutes les données d'entraînement."""

    logger.info("Génération des données synthétiques...")

    training_data = []

    # 1. Données de base
    training_data.extend(generate_dbh_examples(50))
    training_data.extend(generate_height_examples(50))
    training_data.extend(generate_species_names(40))
    training_data.extend(generate_wood_density(30))
    training_data.extend(generate_coordinates(40))

    # 2. Données complexes
    training_data.extend(generate_correlated_measurements(20))
    training_data.extend(generate_temporal_data(10))

    # 3. Ajouter vos propres types ici
    # training_data.extend(generate_your_custom_type(30))

    logger.info(f"Généré {len(training_data)} exemples")
    return training_data

def add_real_data(training_data):
    """Ajoute des données réelles si disponibles."""

    # Exemple: charger depuis un fichier annoté
    real_file = Path("data/annotated_examples.csv")
    if real_file.exists():
        logger.info(f"Chargement données réelles depuis {real_file}")
        df = pd.read_csv(real_file)

        # Mapper vos colonnes
        mappings = {
            'dbh_cm': 'diameter',
            'hauteur_m': 'height',
            'espece': 'species_name',
            # Ajouter vos mappings
        }

        for col, label in mappings.items():
            if col in df.columns:
                training_data.append((df[col], label))
                logger.info(f"  Ajouté {col} comme {label}")

    return training_data

def evaluate_on_real_data(detector):
    """Évalue le modèle sur des données réelles."""

    test_file = Path("test-instance/niamoto-og/imports/occurrences.csv")
    if test_file.exists():
        logger.info(f"\nTest sur données réelles: {test_file}")
        df = pd.read_csv(test_file, nrows=1000)

        results = []
        for col in df.columns[:10]:  # Tester 10 premières colonnes
            pred_type, confidence = detector.predict(df[col])
            results.append({
                'column': col,
                'predicted': pred_type,
                'confidence': confidence
            })
            logger.info(f"  {col:20} -> {pred_type:15} ({confidence:.1%})")

        return results
    return []

def main():
    """Script principal."""

    logger.info("=== Entraînement ML Column Detector ===\n")

    # 1. Générer données
    training_data = generate_all_training_data()
    training_data = add_real_data(training_data)

    # 2. Séparer train/test
    from sklearn.model_selection import train_test_split

    train_data, test_data = train_test_split(
        training_data,
        test_size=0.2,
        random_state=42,
        stratify=[label for _, label in training_data]
    )

    logger.info(f"Train: {len(train_data)}, Test: {len(test_data)}")

    # 3. Entraîner
    logger.info("\nEntraînement du modèle...")
    detector = MLColumnDetector()
    detector.train(train_data)

    # 4. Évaluer
    logger.info("\nÉvaluation sur test set...")
    correct = 0
    for series, true_label in test_data:
        pred_label, confidence = detector.predict(series)
        if pred_label == true_label:
            correct += 1

    accuracy = correct / len(test_data)
    logger.info(f"Accuracy: {accuracy:.1%}")

    # 5. Tester sur données réelles
    evaluate_on_real_data(detector)

    # 6. Sauvegarder
    model_path = Path("models/column_detector_custom.pkl")
    model_path.parent.mkdir(exist_ok=True, parents=True)
    detector.save_model(model_path)
    logger.info(f"\nModèle sauvé: {model_path}")

    # 7. Test final sur colonnes aléatoires
    logger.info("\nTest sur noms aléatoires:")
    test_random = pd.DataFrame({
        'X1': np.random.lognormal(3, 0.8, 100),
        'toto': ['Araucaria columnaris'] * 100,
        'machin': np.random.normal(15, 5, 100),
    })

    for col in test_random.columns:
        pred, conf = detector.predict(test_random[col])
        logger.info(f"  {col:10} -> {pred:15} ({conf:.1%})")

if __name__ == "__main__":
    main()
```

## 🎨 Techniques avancées

### 1. Augmentation de données

```python
def augment_data(series: pd.Series, augmentation_factor=3):
    """Augmente les données avec des transformations."""
    augmented = []

    for _ in range(augmentation_factor):
        s = series.copy()

        # Ajouter du bruit
        if pd.api.types.is_numeric_dtype(s):
            noise = np.random.normal(0, s.std() * 0.05, len(s))
            s += noise

        # Sous-échantillonnage
        if len(s) > 100:
            s = s.sample(n=int(len(s) * 0.8))

        # Ajouter valeurs manquantes
        if np.random.random() < 0.3:
            missing_idx = np.random.choice(len(s), int(len(s) * 0.1))
            s.iloc[missing_idx] = np.nan

        augmented.append(s)

    return augmented
```

### 2. Génération basée sur distributions empiriques

```python
def generate_from_empirical(real_data: pd.Series, n_synthetic=10):
    """Génère des données basées sur distribution empirique."""
    synthetic = []

    for _ in range(n_synthetic):
        if pd.api.types.is_numeric_dtype(real_data):
            # Utiliser KDE pour estimer distribution
            from scipy.stats import gaussian_kde

            clean_data = real_data.dropna()
            kde = gaussian_kde(clean_data)

            # Échantillonner depuis KDE
            size = np.random.randint(len(real_data) * 0.8, len(real_data) * 1.2)
            synthetic_values = kde.resample(size)[0]

            # Appliquer les mêmes bornes
            synthetic_values = np.clip(
                synthetic_values,
                real_data.min(),
                real_data.max()
            )

            synthetic.append(pd.Series(synthetic_values))

    return synthetic
```

## 📝 Bonnes pratiques

1. **Diversité** : Créer plusieurs variantes de chaque type
2. **Réalisme** : Respecter les distributions naturelles
3. **Bruit** : Ajouter des imperfections (NaN, outliers)
4. **Volume** : Au moins 30-50 exemples par type
5. **Validation** : Toujours tester sur données réelles

## 🚀 Commandes utiles

```bash
# Entraîner avec données personnalisées
uv run python scripts/train_custom_detector.py

# Tester le modèle
uv run python -c "
from src.niamoto.core.imports.ml_detector import MLColumnDetector
import pandas as pd
detector = MLColumnDetector()
detector.load_model('models/column_detector_custom.pkl')
test = pd.Series([15, 23, 45, 67])
print(detector.predict(test))
"

# Comparer modèles
uv run python scripts/compare_models.py
```

## 🔍 Debugging

Si le modèle ne détecte pas bien :

1. **Vérifier les features** :
```python
features = detector.extract_features(your_series)
print("Features:", features)
print("Names:", detector._get_feature_names())
```

2. **Analyser les erreurs** :
```python
# Voir quelles features sont importantes
importances = detector.model.feature_importances_
for i, imp in enumerate(importances):
    if imp > 0.05:
        print(f"Feature {i}: {imp:.3f}")
```

3. **Augmenter les données** :
- Plus d'exemples du type problématique
- Plus de variabilité dans les exemples
- Exemples edge cases
