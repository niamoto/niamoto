#!/usr/bin/env python3
"""
Script de collecte de données d'entraînement pour le ML Column Detector de Niamoto.

Collecte des données depuis diverses sources :
- GBIF : Données d'occurrences biodiversité
- Fichiers locaux : Données existantes Nouvelle-Calédonie
- Génération synthétique : Augmentation des données

Usage:
    python scripts/collect_training_data.py --source gbif --limit 1000
    python scripts/collect_training_data.py --source all --output data/training/
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from tqdm import tqdm

# Configuration logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Ajouter le path pour les imports Niamoto
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TrainingDataCollector:
    """Collecteur de données d'entraînement pour le ML detector."""

    def __init__(self, output_dir: Path = None):
        """
        Initialise le collecteur.

        Args:
            output_dir: Répertoire de sortie pour les données collectées
        """
        self.output_dir = output_dir or Path("data/ml_training")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.training_data = []
        self.stats = {"sources": {}, "types": {}, "total_examples": 0}

    def collect_all(self, limit: int = 10000) -> Tuple[List, Dict]:
        """
        Collecte données depuis toutes les sources.

        Args:
            limit: Nombre maximum d'exemples à collecter

        Returns:
            Tuple (training_data, statistics)
        """
        logger.info(f"Démarrage collecte de {limit} exemples d'entraînement...")

        # 1. GBIF - Données biodiversité
        gbif_data = self.collect_gbif_data(limit // 4)
        self.training_data.extend(gbif_data)
        self.stats["sources"]["gbif"] = len(gbif_data)

        # 2. Données locales Nouvelle-Calédonie
        local_data = self.collect_local_data(limit // 4)
        self.training_data.extend(local_data)
        self.stats["sources"]["local"] = len(local_data)

        # 3. Données synthétiques
        synthetic_data = self.generate_synthetic_data(limit // 4)
        self.training_data.extend(synthetic_data)
        self.stats["sources"]["synthetic"] = len(synthetic_data)

        # 4. Données augmentées
        augmented_data = self.augment_existing_data(limit // 4)
        self.training_data.extend(augmented_data)
        self.stats["sources"]["augmented"] = len(augmented_data)

        # Statistiques finales
        self._compute_statistics()

        logger.info(f"Collecte terminée : {len(self.training_data)} exemples")
        return self.training_data, self.stats

    def collect_gbif_data(self, limit: int = 1000) -> List[Tuple[pd.Series, str]]:
        """
        Collecte données depuis GBIF API.

        Args:
            limit: Nombre d'exemples à collecter

        Returns:
            Liste de tuples (Series, type_label)
        """
        logger.info("Collecte données GBIF...")
        examples = []

        # Liste d'espèces pour recherche
        species_list = [
            "Araucaria columnaris",
            "Agathis lanceolata",
            "Podocarpus polyspermus",
            "Dacrydium guillauminii",
            "Retrophyllum comptonii",
            "Metrosideros nitida",
            "Syzygium acre",
            "Nothofagus aequilateralis",
            "Codia spatulata",
            "Cunonia lenormandii",
        ]

        for species in tqdm(species_list, desc="Espèces GBIF"):
            try:
                # Recherche espèce
                species_key = self._get_gbif_species_key(species)
                if not species_key:
                    continue

                # Récupération occurrences
                occurrences = self._get_gbif_occurrences(species_key, limit=100)

                if occurrences.empty:
                    continue

                # Création exemples d'entraînement
                if "scientificName" in occurrences.columns:
                    examples.append((occurrences["scientificName"], "species_name"))

                if "family" in occurrences.columns:
                    examples.append((occurrences["family"], "family_name"))

                if "genus" in occurrences.columns:
                    examples.append((occurrences["genus"], "genus_name"))

                if "decimalLatitude" in occurrences.columns:
                    examples.append((occurrences["decimalLatitude"], "latitude"))

                if "decimalLongitude" in occurrences.columns:
                    examples.append((occurrences["decimalLongitude"], "longitude"))

                if "elevation" in occurrences.columns:
                    examples.append((occurrences["elevation"], "elevation"))

                if "eventDate" in occurrences.columns:
                    examples.append((occurrences["eventDate"], "date"))

                if "country" in occurrences.columns:
                    examples.append((occurrences["country"], "location"))

                if len(examples) >= limit:
                    break

            except Exception as e:
                logger.warning(f"Erreur collecte GBIF pour {species}: {e}")
                continue

        logger.info(f"  → {len(examples)} exemples GBIF collectés")
        return examples[:limit]

    def _get_gbif_species_key(self, species_name: str) -> Optional[int]:
        """Récupère la clé GBIF d'une espèce."""
        try:
            url = "https://api.gbif.org/v1/species/match"
            params = {"name": species_name}
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return data.get("usageKey")
        except Exception as e:
            logger.debug(f"Erreur recherche espèce {species_name}: {e}")

        return None

    def _get_gbif_occurrences(self, species_key: int, limit: int = 100) -> pd.DataFrame:
        """Récupère les occurrences GBIF pour une espèce."""
        try:
            url = "https://api.gbif.org/v1/occurrence/search"
            params = {
                "speciesKey": species_key,
                "limit": min(limit, 300),  # Max GBIF
                "hasCoordinate": True,
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])

                if results:
                    return pd.DataFrame(results)

        except Exception as e:
            logger.debug(f"Erreur récupération occurrences: {e}")

        return pd.DataFrame()

    def collect_local_data(self, limit: int = 1000) -> List[Tuple[pd.Series, str]]:
        """
        Collecte données depuis fichiers locaux.

        Args:
            limit: Nombre d'exemples à collecter

        Returns:
            Liste de tuples (Series, type_label)
        """
        logger.info("Collecte données locales...")
        examples = []

        # Chemins des données locales
        local_paths = [
            Path("test-instance/niamoto-og/imports/occurrences.csv"),
            Path("test-instance/niamoto-og/imports/plots.csv"),
            Path("test-instance/niamoto-og/imports/raw_plot_stats.csv"),
            Path("test-instance/niamoto-og/imports/raw_shape_stats.csv"),
        ]

        for path in local_paths:
            if not path.exists():
                logger.debug(f"Fichier non trouvé : {path}")
                continue

            try:
                # Chargement données
                if path.suffix == ".csv":
                    df = pd.read_csv(path, nrows=1000)
                else:
                    continue

                # Mapping colonnes connues
                column_mappings = {
                    "dbh": "diameter",
                    "dbh_cm": "diameter",
                    "diameter": "diameter",
                    "height": "height",
                    "height_m": "height",
                    "hauteur": "height",
                    "family": "family_name",
                    "famille": "family_name",
                    "genus": "genus_name",
                    "genre": "genus_name",
                    "species": "species_name",
                    "espece": "species_name",
                    "lat": "latitude",
                    "latitude": "latitude",
                    "lon": "longitude",
                    "lng": "longitude",
                    "longitude": "longitude",
                    "elevation": "elevation",
                    "altitude": "elevation",
                    "date": "date",
                    "year": "year",
                    "plot": "location",
                    "site": "location",
                    "locality": "location",
                    "commune": "location",
                }

                # Création exemples
                for col in df.columns:
                    col_lower = col.lower()

                    # Check mapping direct
                    if col_lower in column_mappings:
                        label = column_mappings[col_lower]
                        examples.append((df[col], label))

                    # Patterns additionnels
                    elif "count" in col_lower or "nombre" in col_lower:
                        examples.append((df[col], "count"))
                    elif "id" in col_lower or "code" in col_lower:
                        examples.append((df[col], "identifier"))
                    elif "note" in col_lower or "comment" in col_lower:
                        examples.append((df[col], "note"))

                if len(examples) >= limit:
                    break

            except Exception as e:
                logger.warning(f"Erreur lecture {path}: {e}")
                continue

        logger.info(f"  → {len(examples)} exemples locaux collectés")
        return examples[:limit]

    def generate_synthetic_data(self, limit: int = 2000) -> List[Tuple[pd.Series, str]]:
        """
        Génère données synthétiques pour augmentation.

        Args:
            limit: Nombre d'exemples à générer

        Returns:
            Liste de tuples (Series, type_label)
        """
        logger.info("Génération données synthétiques...")
        examples = []
        np.random.seed(42)

        # Génération par type
        generators = {
            "diameter": self._generate_diameter_data,
            "height": self._generate_height_data,
            "leaf_area": self._generate_leaf_area_data,
            "wood_density": self._generate_wood_density_data,
            "species_name": self._generate_species_names,
            "family_name": self._generate_family_names,
            "genus_name": self._generate_genus_names,
            "latitude": self._generate_latitude_data,
            "longitude": self._generate_longitude_data,
            "elevation": self._generate_elevation_data,
            "date": self._generate_date_data,
            "count": self._generate_count_data,
            "location": self._generate_location_data,
        }

        examples_per_type = limit // len(generators)

        for type_name, generator in generators.items():
            for _ in range(examples_per_type // 10):  # 10 variations par type
                data = generator(size=100)
                examples.append((pd.Series(data), type_name))

        logger.info(f"  → {len(examples)} exemples synthétiques générés")
        return examples[:limit]

    def _generate_diameter_data(self, size: int = 100) -> np.ndarray:
        """Génère données DBH réalistes."""
        # Distribution log-normale typique pour DBH
        dbh = np.random.lognormal(mean=3.0, sigma=0.8, size=size)
        dbh = np.clip(dbh, 5, 300)  # Limites réalistes en cm

        # Ajouter quelques NaN
        mask = np.random.random(size) < 0.05
        dbh[mask] = np.nan

        return dbh

    def _generate_height_data(self, size: int = 100) -> np.ndarray:
        """Génère données hauteur réalistes."""
        # Distribution normale pour hauteurs
        height = np.random.normal(loc=15, scale=5, size=size)
        height = np.clip(height, 1, 50)  # Limites en mètres

        # Ajouter variations
        if np.random.random() > 0.5:
            height = height * 100  # Parfois en cm

        return height

    def _generate_leaf_area_data(self, size: int = 100) -> np.ndarray:
        """Génère données surface foliaire."""
        # Distribution beta pour surface foliaire
        leaf_area = np.random.beta(2, 5, size=size) * 200
        leaf_area = np.clip(leaf_area, 5, 200)  # cm²

        return leaf_area

    def _generate_wood_density_data(self, size: int = 100) -> np.ndarray:
        """Génère données densité bois."""
        # Distribution beta pour densité
        wd = np.random.beta(5, 2, size=size)
        wd = wd * 0.8 + 0.2  # Scale to 0.2-1.0 g/cm³

        return wd

    def _generate_species_names(self, size: int = 100) -> List[str]:
        """Génère noms d'espèces binomiaux."""
        genera = [
            "Araucaria",
            "Agathis",
            "Podocarpus",
            "Dacrydium",
            "Retrophyllum",
            "Metrosideros",
            "Syzygium",
            "Nothofagus",
            "Codia",
            "Cunonia",
            "Acacia",
            "Eucalyptus",
            "Melaleuca",
        ]

        epithets = [
            "columnaris",
            "lanceolata",
            "minor",
            "guillauminii",
            "comptonii",
            "nitida",
            "acre",
            "aequilateralis",
            "spatulata",
            "lenormandii",
            "spirorbis",
            "montana",
            "vulgaris",
            "communis",
            "officinalis",
        ]

        species = []
        for _ in range(size):
            genus = np.random.choice(genera)
            epithet = np.random.choice(epithets)
            species.append(f"{genus} {epithet}")

        return species

    def _generate_family_names(self, size: int = 100) -> List[str]:
        """Génère noms de familles taxonomiques."""
        families = [
            "Araucariaceae",
            "Podocarpaceae",
            "Myrtaceae",
            "Nothofagaceae",
            "Cunoniaceae",
            "Fabaceae",
            "Rubiaceae",
            "Proteaceae",
            "Sapindaceae",
            "Lauraceae",
            "Euphorbiaceae",
            "Moraceae",
            "Apocynaceae",
            "Rutaceae",
            "Malvaceae",
        ]

        return np.random.choice(families, size=size).tolist()

    def _generate_genus_names(self, size: int = 100) -> List[str]:
        """Génère noms de genres."""
        genera = [
            "Araucaria",
            "Agathis",
            "Podocarpus",
            "Dacrydium",
            "Retrophyllum",
            "Metrosideros",
            "Syzygium",
            "Nothofagus",
            "Codia",
            "Cunonia",
            "Acacia",
            "Eucalyptus",
            "Melaleuca",
            "Ficus",
            "Diospyros",
            "Elaeocarpus",
            "Pandanus",
        ]

        return np.random.choice(genera, size=size).tolist()

    def _generate_latitude_data(self, size: int = 100) -> np.ndarray:
        """Génère latitudes Nouvelle-Calédonie."""
        # Latitudes NC : -20 à -23
        lat = np.random.uniform(-23, -20, size=size)

        # Ajouter du bruit
        lat += np.random.normal(0, 0.01, size=size)

        return lat

    def _generate_longitude_data(self, size: int = 100) -> np.ndarray:
        """Génère longitudes Nouvelle-Calédonie."""
        # Longitudes NC : 164 à 168
        lon = np.random.uniform(164, 168, size=size)

        # Ajouter du bruit
        lon += np.random.normal(0, 0.01, size=size)

        return lon

    def _generate_elevation_data(self, size: int = 100) -> np.ndarray:
        """Génère données altitude."""
        # Distribution bimodale (côte + montagne)
        coastal = np.random.normal(50, 30, size=size // 2)
        mountain = np.random.normal(800, 300, size=size // 2)
        elevation = np.concatenate([coastal, mountain])
        elevation = np.clip(elevation, 0, 1629)  # Max NC

        return elevation

    def _generate_date_data(self, size: int = 100) -> List[str]:
        """Génère dates aléatoires."""
        dates = []
        base = datetime.now()

        for _ in range(size):
            # Date aléatoire dans les 10 dernières années
            days_ago = np.random.randint(0, 3650)
            date = base - timedelta(days=days_ago)

            # Format aléatoire
            formats = [
                "%Y-%m-%d",  # ISO
                "%d/%m/%Y",  # European
                "%m/%d/%Y",  # US
                "%Y%m%d",  # Compact
                "%Y",  # Année seule
            ]

            fmt = np.random.choice(formats)
            dates.append(date.strftime(fmt))

        return dates

    def _generate_count_data(self, size: int = 100) -> np.ndarray:
        """Génère données de comptage."""
        # Distribution de Poisson pour comptages
        counts = np.random.poisson(lam=5, size=size)

        # Parfois des valeurs plus élevées
        if np.random.random() > 0.5:
            counts = np.random.poisson(lam=50, size=size)

        return counts

    def _generate_location_data(self, size: int = 100) -> List[str]:
        """Génère noms de lieux."""
        provinces = ["Province Sud", "Province Nord", "Province des Îles"]
        communes = [
            "Nouméa",
            "Dumbéa",
            "Mont-Dore",
            "Païta",
            "Koné",
            "Poindimié",
            "Lifou",
            "Maré",
            "Ouvéa",
            "Thio",
            "Yaté",
            "Hienghène",
            "Pouébo",
            "Koumac",
            "Voh",
        ]

        locations = []
        for _ in range(size):
            if np.random.random() > 0.5:
                locations.append(np.random.choice(provinces))
            else:
                locations.append(np.random.choice(communes))

        return locations

    def augment_existing_data(self, limit: int = 1000) -> List[Tuple[pd.Series, str]]:
        """
        Augmente données existantes avec variations.

        Args:
            limit: Nombre d'exemples augmentés

        Returns:
            Liste de tuples (Series, type_label)
        """
        logger.info("Augmentation données existantes...")

        if not self.training_data:
            logger.warning("Pas de données existantes à augmenter")
            return []

        augmented = []

        for series, label in self.training_data[: limit // 5]:
            # Variations numériques
            if pd.api.types.is_numeric_dtype(series):
                # Changement d'unités
                if label == "diameter":
                    # cm vers mm
                    augmented.append((series * 10, label))
                    # cm vers inches
                    augmented.append((series / 2.54, label))

                elif label == "height":
                    # m vers ft
                    augmented.append((series * 3.28084, label))
                    # m vers cm
                    augmented.append((series * 100, label))

                # Ajout de bruit
                noisy = series + np.random.normal(0, series.std() * 0.05, len(series))
                augmented.append((noisy, label))

                # Ajout de valeurs manquantes
                missing = series.copy()
                mask = np.random.random(len(series)) < 0.1
                missing[mask] = np.nan
                augmented.append((missing, label))

            # Variations texte
            else:
                # Casse différente
                if label in ["species_name", "genus_name", "family_name"]:
                    # Majuscules
                    augmented.append((series.str.upper(), label))
                    # Minuscules
                    augmented.append((series.str.lower(), label))
                    # Title case
                    augmented.append((series.str.title(), label))

            if len(augmented) >= limit:
                break

        logger.info(f"  → {len(augmented)} exemples augmentés créés")
        return augmented[:limit]

    def _compute_statistics(self):
        """Calcule statistiques sur les données collectées."""
        self.stats["total_examples"] = len(self.training_data)

        # Comptage par type
        for _, label in self.training_data:
            self.stats["types"][label] = self.stats["types"].get(label, 0) + 1

        # Proportions
        total = self.stats["total_examples"]
        if total > 0:
            self.stats["proportions"] = {
                type_: count / total for type_, count in self.stats["types"].items()
            }

    def save_training_data(self):
        """Sauvegarde les données d'entraînement."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Sauvegarde pickle pour chargement direct
        import pickle

        pickle_path = self.output_dir / f"training_data_{timestamp}.pkl"
        with open(pickle_path, "wb") as f:
            pickle.dump(self.training_data, f)
        logger.info(f"Données sauvegardées : {pickle_path}")

        # Sauvegarde statistiques JSON
        stats_path = self.output_dir / f"training_stats_{timestamp}.json"
        with open(stats_path, "w") as f:
            json.dump(self.stats, f, indent=2, default=str)
        logger.info(f"Statistiques sauvegardées : {stats_path}")

        # Génération rapport
        self._generate_report(timestamp)

    def _generate_report(self, timestamp: str):
        """Génère rapport de collecte."""
        report_path = self.output_dir / f"collection_report_{timestamp}.md"

        with open(report_path, "w") as f:
            f.write("# Rapport de Collecte de Données d'Entraînement\n\n")
            f.write(f"Date : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("## Résumé\n")
            f.write(f"- **Total exemples** : {self.stats['total_examples']}\n")
            f.write(f"- **Types détectés** : {len(self.stats['types'])}\n\n")

            f.write("## Sources\n")
            for source, count in self.stats["sources"].items():
                pct = (count / self.stats["total_examples"]) * 100
                f.write(f"- **{source}** : {count} exemples ({pct:.1f}%)\n")
            f.write("\n")

            f.write("## Distribution par Type\n")
            for type_name, count in sorted(
                self.stats["types"].items(), key=lambda x: x[1], reverse=True
            ):
                pct = (count / self.stats["total_examples"]) * 100
                f.write(f"- **{type_name}** : {count} exemples ({pct:.1f}%)\n")
            f.write("\n")

            f.write("## Fichiers Générés\n")
            f.write(f"- `training_data_{timestamp}.pkl` : Données pickle\n")
            f.write(f"- `training_stats_{timestamp}.json` : Statistiques\n")
            f.write(f"- `collection_report_{timestamp}.md` : Ce rapport\n")

        logger.info(f"Rapport généré : {report_path}")


def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(
        description="Collecte données d'entraînement pour ML Column Detector"
    )

    parser.add_argument(
        "--source",
        choices=["gbif", "local", "synthetic", "all"],
        default="all",
        help="Source de données à utiliser",
    )

    parser.add_argument(
        "--limit", type=int, default=1000, help="Nombre maximum d'exemples à collecter"
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/ml_training"),
        help="Répertoire de sortie",
    )

    parser.add_argument("--verbose", action="store_true", help="Mode verbose")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialisation collecteur
    collector = TrainingDataCollector(output_dir=args.output)

    # Collecte selon source
    if args.source == "all":
        training_data, stats = collector.collect_all(limit=args.limit)
    elif args.source == "gbif":
        training_data = collector.collect_gbif_data(limit=args.limit)
        collector.training_data = training_data
    elif args.source == "local":
        training_data = collector.collect_local_data(limit=args.limit)
        collector.training_data = training_data
    elif args.source == "synthetic":
        training_data = collector.generate_synthetic_data(limit=args.limit)
        collector.training_data = training_data

    # Calcul statistiques
    collector._compute_statistics()

    # Sauvegarde
    collector.save_training_data()

    # Affichage résumé
    print("\n" + "=" * 50)
    print("COLLECTE TERMINÉE")
    print("=" * 50)
    print(f"Total exemples : {collector.stats['total_examples']}")
    print(f"Types détectés : {len(collector.stats['types'])}")
    print(f"Fichiers sauvegardés dans : {collector.output_dir}")
    print("=" * 50)


if __name__ == "__main__":
    main()
