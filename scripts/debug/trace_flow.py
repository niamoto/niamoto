#!/usr/bin/env python3
"""
Script de traçage du flow: données -> transformer -> widget
Pour comprendre le pipeline et identifier le mécanisme d'auto-discovery optimal
"""

import sys
import json
from pathlib import Path
from typing import Any

# Ajouter src au path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text

from niamoto.common.database import Database
from niamoto.core.plugins.transformers.distribution.binned_distribution import (
    BinnedDistribution,
)
from niamoto.core.plugins.widgets.bar_plot import BarPlotWidget
from niamoto.common.utils.data_access import transform_data


def print_section(title: str):
    """Affiche un titre de section."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_data_structure(data: Any, name: str):
    """Affiche la structure d'un objet de données."""
    print(f"\n📊 Structure de {name}:")
    print(f"   Type: {type(data).__name__}")

    if isinstance(data, dict):
        print(f"   Clés: {list(data.keys())}")
        print("\n   Contenu détaillé:")
        print(json.dumps(data, indent=2, default=str))
    elif hasattr(data, "model_dump"):
        print("   ✓ Instance Pydantic")
        print("\n   Contenu:")
        print(json.dumps(data.model_dump(), indent=2, default=str))
    else:
        print(f"\n   Contenu: {data}")


def main():
    """Trace le flow complet dbh_distribution -> bar_plot."""

    print_section("TRAÇAGE DU FLOW: dbh_distribution -> bar_plot")

    # Configuration
    db_path = Path("test-instance/niamoto-test/db/niamoto.duckdb")

    if not db_path.exists():
        print(f"❌ Base de données introuvable: {db_path}")
        return

    print(f"\n📁 Base de données: {db_path}")

    # =========================================================================
    # ÉTAPE 1: Charger les données brutes depuis la DB
    # =========================================================================
    print_section("ÉTAPE 1: Données brutes depuis DuckDB")

    db = Database(str(db_path), read_only=True)

    # Requête pour obtenir les DBH des occurrences
    query = "SELECT dbh FROM dataset_occurrences_mini WHERE dbh IS NOT NULL LIMIT 100"

    session = db.get_new_session()
    result = session.execute(text(query))
    raw_data = [row[0] for row in result.fetchall()]
    session.close()

    print(f"\n✓ {len(raw_data)} enregistrements chargés")
    print(f"  Premiers DBH: {raw_data[:10]}")
    print(f"  Min: {min(raw_data):.2f}, Max: {max(raw_data):.2f}")

    # =========================================================================
    # ÉTAPE 2: Exécuter le transformer binned_distribution
    # =========================================================================
    print_section("ÉTAPE 2: Exécution du transformer binned_distribution")

    # Config du transformer (inspirée de transform.yml de niamoto-nc)
    # NOTE: Si source="occurrences", le transformer utilise le DataFrame passé en paramètre
    # Si source != "occurrences", il charge depuis la DB (ligne 176-183)
    transformer_config = {
        "params": {
            "source": "occurrences",  # Utilise le DataFrame qu'on passe
            "field": "dbh",
            "bins": [10, 20, 30, 40, 50, 75, 100, 200, 300, 400, 500],
            "include_percentages": True,
        }
    }

    print("\n📋 Configuration du transformer:")
    print(json.dumps(transformer_config, indent=2))

    # Instancier et exécuter le transformer
    transformer = BinnedDistribution(db)

    # Créer un DataFrame avec les données qu'on a chargées
    import pandas as pd

    df = pd.DataFrame({"dbh": raw_data})

    print(f"\n📊 DataFrame d'entrée: {len(df)} lignes, colonnes: {list(df.columns)}")

    # Exécuter la transformation
    transformer_output = transformer.transform(df, transformer_config)

    print_data_structure(transformer_output, "transformer_output")

    # =========================================================================
    # ÉTAPE 3: Transformation bins_to_df (comme le widget le fait)
    # =========================================================================
    print_section("ÉTAPE 3: Transformation bins_to_df")

    # Config de la transformation (inspirée de export.yml)
    transform_params = {
        "bin_field": "bins",
        "count_field": "counts",
        "use_percentages": True,
        "percentage_field": "percentages",
        "x_field": "bin",
        "y_field": "count",
    }

    print("\n📋 Paramètres de transformation:")
    print(json.dumps(transform_params, indent=2))

    # Appliquer la transformation
    transformed_data = transform_data(
        transformer_output, "bins_to_df", transform_params
    )

    print_data_structure(transformed_data, "transformed_data (après bins_to_df)")

    # =========================================================================
    # ÉTAPE 4: Widget rendering (simulé)
    # =========================================================================
    print_section("ÉTAPE 4: Widget bar_plot - rendering")

    # Config du widget (inspirée de export.yml)
    widget_config = {
        "transform": "bins_to_df",
        "transform_params": transform_params,
        "orientation": "v",
        "x_axis": "bin",
        "y_axis": "count",
        "show_legend": False,
        "labels": {
            "x_axis": "Classe de diamètre (cm)",
            "y_axis": "Fréquence (%)",
        },
        "filter_zero_values": True,
        "gradient_color": "#8B4513",
        "gradient_mode": "luminance",
    }

    print("\n📋 Configuration du widget:")
    print(json.dumps(widget_config, indent=2))

    # Instancier le widget
    widget = BarPlotWidget(db)

    # Le widget attend transformer_output (dict), pas transformed_data (DataFrame)
    # Il fait lui-même la transformation bins_to_df en interne

    print("\n🎨 Le widget BarPlot va:")
    print("   1. Recevoir le dict transformer_output")
    print("   2. Appliquer transform_data(data, 'bins_to_df', params)")
    print("   3. Générer une figure Plotly")

    try:
        # Simuler le render (sans générer vraiment le Plotly pour l'instant)
        figure_config = widget.render(transformer_output, widget_config)
        print("\n✓ Widget rendu avec succès")
        print(f"   Type de sortie: {type(figure_config)}")
    except Exception as e:
        print(f"\n⚠️  Erreur lors du render: {e}")
        import traceback

        traceback.print_exc()

    # =========================================================================
    # ANALYSE: Qu'avons-nous appris ?
    # =========================================================================
    print_section("ANALYSE: Structure des données à chaque étape")

    print("""
┌─────────────────────────────────────────────────────────────────────┐
│ ÉTAPE 1: Données brutes (DB)                                        │
├─────────────────────────────────────────────────────────────────────┤
│ Type: List[float]                                                   │
│ Exemple: [12.5, 34.8, 56.2, ...]                                   │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ ÉTAPE 2: Transformer output (binned_distribution)                   │
├─────────────────────────────────────────────────────────────────────┤
│ Type: dict                                                          │
│ Structure:                                                          │
│   {                                                                 │
│     "bins": [10, 20, 30, 40, ...],                                 │
│     "counts": [45, 78, 92, ...],                                   │
│     "percentages": [16.13, 27.96, ...]                             │
│   }                                                                 │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ ÉTAPE 3: Après bins_to_df                                           │
├─────────────────────────────────────────────────────────────────────┤
│ Type: pandas.DataFrame                                              │
│ Structure:                                                          │
│   | bin        | count |                                           │
│   |------------|-------|                                           │
│   | 10-20      | 45    |                                           │
│   | 20-30      | 78    |                                           │
│   | ...        | ...   |                                           │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ ÉTAPE 4: Widget render                                              │
├─────────────────────────────────────────────────────────────────────┤
│ Type: plotly.graph_objects.Figure                                   │
│ → Visualisation HTML/JSON                                          │
└─────────────────────────────────────────────────────────────────────┘
    """)

    print_section("CONCLUSION")
    print("""
Questions clés pour l'auto-discovery:

1. 🔍 MATCHING: Comment le widget sait-il qu'il peut consommer ce transformer ?

   Options:
   A) Structure du dict: {"bins": list, "counts": list} → pattern matching
   B) Metadata tag: {"_type": "binned_distribution", ...} → explicit matching
   C) Pydantic schema: BinnedDistributionOutput instance → type checking

2. 🔧 TRANSFORMATION: Qui est responsable de bins_to_df ?

   Actuellement: Le widget appelle transform_data() depuis data_access.py

   Options:
   A) Garder comme ça: widget gère ses transformations
   B) Transformer intègre: transformer retourne déjà le DataFrame
   C) Couche adapter: système intermédiaire qui transforme

3. 📦 PLUGIN CUSTOM: Comment un utilisateur crée un nouveau plugin ?

   Options:
   A) Retourner un dict avec structure standard → simple, flexible
   B) Créer un Pydantic schema → type-safe, mais plus complexe
   C) Juste déclarer compatible_types = [...] → déclaratif

Prochaine étape: Décider quelle approche on valide dans le prototype.
    """)


if __name__ == "__main__":
    main()
