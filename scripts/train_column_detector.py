#!/usr/bin/env python
"""
Script to train the ML column detector for Niamoto.
Generates synthetic training data and trains a Random Forest model.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import logging
from typing import List, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from niamoto.core.imports.ml_detector import MLColumnDetector

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def generate_synthetic_training_data() -> List[Tuple[pd.Series, str]]:
    """
    Generate synthetic training examples for ecological data types.

    Returns:
        List of (series, label) tuples
    """
    training_data = []
    np.random.seed(42)

    # 1. Generate DBH (diameter) examples
    logger.info("Generating DBH examples...")
    for i in range(50):
        # DBH typically has right-skewed distribution
        size = np.random.randint(100, 500)
        dbh = np.random.lognormal(mean=3.0, sigma=0.8, size=size)
        dbh = np.clip(dbh, 5, 300)  # Realistic range 5-300 cm

        # Add some noise and missing values
        if i % 3 == 0:
            dbh[np.random.choice(size, size=int(size * 0.1))] = np.nan

        training_data.append((pd.Series(dbh), "diameter"))

    # 2. Generate height examples
    logger.info("Generating height examples...")
    for i in range(50):
        size = np.random.randint(100, 500)
        # Height typically more normally distributed
        height = np.random.normal(loc=15, scale=5, size=size)
        height = np.clip(height, 1, 45)  # Realistic range 1-45 m

        if i % 3 == 0:
            height[np.random.choice(size, size=int(size * 0.1))] = np.nan

        training_data.append((pd.Series(height), "height"))

    # 3. Generate leaf area examples
    logger.info("Generating leaf area examples...")
    for i in range(30):
        size = np.random.randint(50, 300)
        # Leaf area varies widely
        leaf_area = np.random.gamma(shape=2, scale=10, size=size)
        leaf_area = np.clip(leaf_area, 0.5, 200)

        training_data.append((pd.Series(leaf_area), "leaf_area"))

    # 4. Generate wood density examples
    logger.info("Generating wood density examples...")
    for i in range(30):
        size = np.random.randint(50, 300)
        # Wood density typically 0.2-1.2 g/cm³
        wood_density = np.random.beta(a=5, b=2, size=size)
        wood_density = wood_density * 0.8 + 0.2

        training_data.append((pd.Series(wood_density), "wood_density"))

    # 5. Generate species name examples
    logger.info("Generating species name examples...")
    genera = [
        "Araucaria",
        "Agathis",
        "Podocarpus",
        "Dacrydium",
        "Retrophyllum",
        "Metrosideros",
        "Syzygium",
        "Eugenia",
        "Acacia",
        "Melaleuca",
        "Nothofagus",
        "Cunonia",
        "Weinmannia",
        "Geissois",
        "Codia",
    ]
    epithets = [
        "columnaris",
        "lanceolata",
        "minor",
        "guillauminii",
        "comptonii",
        "montana",
        "littoralis",
        "robusta",
        "spiralis",
        "vitiensis",
        "balansae",
        "deplanchei",
        "vieillardii",
        "mackeeana",
        "albicans",
    ]

    for i in range(40):
        size = np.random.randint(50, 300)
        species = [
            f"{np.random.choice(genera)} {np.random.choice(epithets)}"
            for _ in range(size)
        ]
        # Add some variation
        if i % 4 == 0:
            # Add some with subspecies
            for j in range(0, size, 5):
                species[j] = (
                    species[j] + " subsp. " + np.random.choice(["minor", "major"])
                )

        training_data.append((pd.Series(species), "species_name"))

    # 6. Generate family name examples
    logger.info("Generating family name examples...")
    families = [
        "Araucariaceae",
        "Podocarpaceae",
        "Cunoniaceae",
        "Myrtaceae",
        "Proteaceae",
        "Rubiaceae",
        "Sapindaceae",
        "Lauraceae",
        "Euphorbiaceae",
        "Fabaceae",
        "Apocynaceae",
        "Rutaceae",
        "Arecaceae",
        "Cyperaceae",
        "Orchidaceae",
    ]

    for i in range(30):
        size = np.random.randint(50, 300)
        family_data = np.random.choice(families, size=size)
        training_data.append((pd.Series(family_data), "family_name"))

    # 7. Generate genus name examples
    logger.info("Generating genus name examples...")
    for i in range(30):
        size = np.random.randint(50, 300)
        genus_data = np.random.choice(genera, size=size)
        training_data.append((pd.Series(genus_data), "genus_name"))

    # 8. Generate location examples
    logger.info("Generating location examples...")
    locations_nc = [
        "Province Sud",
        "Province Nord",
        "Province des Îles",
        "Nouméa",
        "Mont-Dore",
        "Dumbéa",
        "Païta",
        "Bourail",
        "Koné",
        "Pouembout",
        "Koumac",
        "Poindimié",
        "Lifou",
        "Maré",
        "Ouvéa",
        "Commune de Thio",
        "Commune de Yaté",
    ]

    for i in range(30):
        size = np.random.randint(50, 300)
        location_data = np.random.choice(locations_nc, size=size)
        training_data.append((pd.Series(location_data), "location"))

    # 9. Generate latitude examples
    logger.info("Generating latitude examples...")
    for i in range(20):
        size = np.random.randint(100, 400)
        # New Caledonia latitudes roughly -19.5 to -23
        lat = np.random.uniform(low=-23, high=-19.5, size=size)

        # Add some global examples too
        if i % 3 == 0:
            lat = np.random.uniform(low=-90, high=90, size=size)

        training_data.append((pd.Series(lat), "latitude"))

    # 10. Generate longitude examples
    logger.info("Generating longitude examples...")
    for i in range(20):
        size = np.random.randint(100, 400)
        # New Caledonia longitudes roughly 163.5 to 169
        lon = np.random.uniform(low=163.5, high=169, size=size)

        # Add some global examples
        if i % 3 == 0:
            lon = np.random.uniform(low=-180, high=180, size=size)

        training_data.append((pd.Series(lon), "longitude"))

    # 11. Generate count/abundance examples
    logger.info("Generating count examples...")
    for i in range(20):
        size = np.random.randint(50, 300)
        # Count data - often Poisson-like
        counts = np.random.poisson(lam=5, size=size)
        counts = np.clip(counts, 0, 100)
        training_data.append((pd.Series(counts), "count"))

    # 12. Generate identifier examples
    logger.info("Generating identifier examples...")
    for i in range(20):
        size = np.random.randint(50, 300)
        # Mix of patterns
        if i % 3 == 0:
            ids = [f"NC{np.random.randint(1000, 9999)}" for _ in range(size)]
        elif i % 3 == 1:
            ids = [f"PLOT_{np.random.randint(1, 999)}" for _ in range(size)]
        else:
            ids = np.random.randint(100000, 999999, size=size).astype(str)

        training_data.append((pd.Series(ids), "identifier"))

    # 13. Generate "other" examples (random data)
    logger.info("Generating 'other' examples...")
    for i in range(30):
        size = np.random.randint(50, 300)
        if i % 2 == 0:
            # Random numeric
            other = np.random.randn(size) * 100
        else:
            # Random text
            other = [f"Random_{np.random.randint(1000)}" for _ in range(size)]

        training_data.append((pd.Series(other), "other"))

    logger.info(f"Generated {len(training_data)} training examples")
    return training_data


def load_real_data_if_available() -> List[Tuple[pd.Series, str]]:
    """
    Try to load real data from test instances if available.

    Returns:
        List of (series, label) tuples from real data
    """
    real_data = []

    # Try to load niamoto-og occurrences
    test_file = Path("test-instance/niamoto-og/imports/occurrences.csv")
    if test_file.exists():
        logger.info(f"Loading real data from {test_file}")
        try:
            df = pd.read_csv(test_file, nrows=1000)

            # Add known columns
            if "dbh" in df.columns:
                real_data.append((df["dbh"], "diameter"))
            if "height" in df.columns:
                real_data.append((df["height"], "height"))
            if "family" in df.columns:
                real_data.append((df["family"], "family_name"))
            if "genus" in df.columns:
                real_data.append((df["genus"], "genus_name"))
            if "species" in df.columns:
                real_data.append((df["species"], "species_name"))

            # Try renamed versions
            for col in df.columns:
                col_lower = col.lower()
                if "lat" in col_lower and "latitude" not in col_lower:
                    real_data.append((df[col], "latitude"))
                elif "lon" in col_lower and "longitude" not in col_lower:
                    real_data.append((df[col], "longitude"))

            logger.info(f"Loaded {len(real_data)} examples from real data")

        except Exception as e:
            logger.warning(f"Could not load real data: {e}")

    return real_data


def evaluate_model(detector: MLColumnDetector, test_data: List[Tuple[pd.Series, str]]):
    """
    Evaluate model performance on test data.

    Args:
        detector: Trained detector
        test_data: Test examples
    """
    from sklearn.metrics import classification_report

    y_true = []
    y_pred = []
    confidences = []

    for series, true_label in test_data:
        predicted, confidence = detector.predict(series)
        y_true.append(true_label)
        y_pred.append(predicted)
        confidences.append(confidence)

    # Calculate metrics
    accuracy = sum(1 for t, p in zip(y_true, y_pred) if t == p) / len(y_true)
    avg_confidence = np.mean(confidences)

    logger.info(f"\n{'=' * 50}")
    logger.info("Model Evaluation Results")
    logger.info(f"{'=' * 50}")
    logger.info(f"Accuracy: {accuracy:.2%}")
    logger.info(f"Average confidence: {avg_confidence:.2%}")

    # Classification report
    logger.info("\nClassification Report:")
    print(classification_report(y_true, y_pred))

    # Show some misclassifications
    errors = [(t, p, c) for t, p, c in zip(y_true, y_pred, confidences) if t != p]
    if errors:
        logger.info("\nSample misclassifications (showing first 5):")
        for true, pred, conf in errors[:5]:
            logger.info(
                f"  True: {true:15} Predicted: {pred:15} Confidence: {conf:.2%}"
            )


def test_on_unnamed_columns(detector: MLColumnDetector):
    """
    Test the detector on columns with random names.

    Args:
        detector: Trained detector
    """
    logger.info("\n" + "=" * 50)
    logger.info("Testing on columns with random names")
    logger.info("=" * 50)

    # Create test data with meaningless column names
    test_df = pd.DataFrame(
        {
            "X1": np.random.lognormal(3, 0.8, 100),  # DBH-like
            "toto": [
                f"Araucaria {np.random.choice(['columnaris', 'montana'])}"
                for _ in range(100)
            ],
            "machin": np.random.normal(15, 5, 100),  # Height-like
            "truc": np.random.beta(5, 2, 100) * 0.8 + 0.2,  # Wood density-like
            "bidule": np.random.uniform(-22, -20, 100),  # Latitude NC
            "chose": ["Province Sud", "Province Nord"][np.random.randint(0, 2)] * 100,
        }
    )

    # Adjust first column to be more DBH-like
    test_df["X1"] = np.clip(test_df["X1"], 5, 200)

    for col in test_df.columns:
        pred_type, confidence = detector.predict(test_df[col])

        # Get all probabilities for more insight
        all_probs = detector.predict(test_df[col], return_all=True)
        top_3 = sorted(all_probs.items(), key=lambda x: x[1], reverse=True)[:3]

        logger.info(f"\nColumn '{col}':")
        logger.info(f"  Predicted: {pred_type} (confidence: {confidence:.2%})")
        logger.info("  Top 3 predictions:")
        for pred, prob in top_3:
            logger.info(f"    - {pred:15}: {prob:.2%}")


def main():
    """Main training script."""
    logger.info("Starting ML Column Detector training")

    # 1. Generate training data
    logger.info("\n1. Generating training data...")
    synthetic_data = generate_synthetic_training_data()
    real_data = load_real_data_if_available()

    all_data = synthetic_data + real_data
    logger.info(f"Total examples: {len(all_data)}")

    # 2. Split train/test
    from sklearn.model_selection import train_test_split

    train_data, test_data = train_test_split(
        all_data,
        test_size=0.2,
        random_state=42,
        stratify=[label for _, label in all_data],
    )
    logger.info(f"Train examples: {len(train_data)}")
    logger.info(f"Test examples: {len(test_data)}")

    # 3. Create and train detector
    logger.info("\n2. Training Random Forest model...")
    detector = MLColumnDetector()
    detector.train(train_data)

    # 4. Evaluate on test set
    logger.info("\n3. Evaluating model...")
    evaluate_model(detector, test_data)

    # 5. Test on unnamed columns
    test_on_unnamed_columns(detector)

    # 6. Save model
    logger.info("\n4. Saving model...")
    model_dir = Path(__file__).parent.parent / "models"
    model_dir.mkdir(exist_ok=True, parents=True)
    model_path = model_dir / "column_detector.pkl"

    detector.save_model(model_path)
    logger.info(f"Model saved to {model_path}")

    # 7. Test loading
    logger.info("\n5. Testing model loading...")
    detector2 = MLColumnDetector()
    detector2.load_model(model_path)

    # Quick verification
    test_series = pd.Series(np.random.lognormal(3, 0.8, 100))
    pred1 = detector.predict(test_series)
    pred2 = detector2.predict(test_series)
    assert pred1 == pred2, "Loaded model produces different predictions!"
    logger.info("✓ Model loading successful")

    logger.info("\n" + "=" * 50)
    logger.info("Training complete!")
    logger.info(f"Model ready at: {model_path}")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
