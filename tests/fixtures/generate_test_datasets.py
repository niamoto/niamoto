"""Generate test fixture datasets for pipeline integration tests.

Each dataset targets a specific dimension of data heterogeneity.
Run once to create fixtures, then commit them to the repo.
Uses fixed random seed for deterministic output.

Usage:
    python tests/fixtures/generate_test_datasets.py
"""

import random
import csv
from pathlib import Path

random.seed(42)

OUTPUT_DIR = Path(__file__).parent / "datasets"
OUTPUT_DIR.mkdir(exist_ok=True)


def generate_gbif_terrestrial():
    """Dataset 1: GBIF SIMPLE_CSV format (TSV, ~50 DwC columns)."""
    path = OUTPUT_DIR / "gbif_terrestrial.tsv"
    species = [
        "Araucaria columnaris",
        "Podocarpus novae-caledoniae",
        "Nothofagus aequilateralis",
        "Agathis lanceolata",
        "Dacrydium guillauminii",
        "Callitris sulcata",
        "Parasitaxus usta",
        "Retrophyllum comptonii",
        "Acmopyle pancheri",
        "Falcatifolium taxoides",
    ]
    kingdoms = ["Plantae"] * 10
    phyla = ["Tracheophyta"] * 10
    families = [
        "Araucariaceae",
        "Podocarpaceae",
        "Nothofagaceae",
        "Araucariaceae",
        "Podocarpaceae",
        "Cupressaceae",
        "Podocarpaceae",
        "Podocarpaceae",
        "Podocarpaceae",
        "Podocarpaceae",
    ]
    basis = [
        "PRESERVED_SPECIMEN",
        "HUMAN_OBSERVATION",
        "PRESERVED_SPECIMEN",
        "HUMAN_OBSERVATION",
        "MACHINE_OBSERVATION",
    ]

    rows = []
    for i in range(100):
        sp_idx = i % len(species)
        rows.append(
            {
                "gbifID": 1000000 + i,
                "occurrenceID": f"urn:catalog:MNHN:{i:05d}",
                "basisOfRecord": basis[i % len(basis)],
                "scientificName": species[sp_idx],
                "kingdom": kingdoms[sp_idx],
                "phylum": phyla[sp_idx],
                "family": families[sp_idx],
                "genus": species[sp_idx].split()[0],
                "specificEpithet": species[sp_idx].split()[-1],
                "taxonRank": "SPECIES",
                "decimalLatitude": round(-22.0 + random.uniform(-0.5, 0.5), 6),
                "decimalLongitude": round(166.5 + random.uniform(-0.5, 0.5), 6),
                "coordinateUncertaintyInMeters": random.choice(
                    [10, 50, 100, 500, None]
                ),
                "eventDate": f"202{random.randint(0, 4)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
                "year": random.randint(2020, 2024),
                "countryCode": "NC",
                "elevation": random.randint(50, 1200)
                if random.random() > 0.3
                else None,
                "remarks": random.choice(
                    [None, "Collected near river", "On ultramafic substrate", ""]
                ),
            }
        )

    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {path} ({len(rows)} rows, {len(fieldnames)} columns)")


def generate_gbif_marine():
    """Dataset 2: OBIS marine occurrences."""
    path = OUTPUT_DIR / "gbif_marine.tsv"
    species = [
        "Carcharodon carcharias",
        "Tursiops truncatus",
        "Chelonia mydas",
        "Acropora millepora",
        "Tridacna gigas",
        "Dugong dugon",
        "Hippocampus kuda",
        "Manta birostris",
    ]
    families = [
        "Lamnidae",
        "Delphinidae",
        "Cheloniidae",
        "Acroporidae",
        "Cardiidae",
        "Dugongidae",
        "Syngnathidae",
        "Mobulidae",
    ]

    rows = []
    for i in range(100):
        sp_idx = i % len(species)
        rows.append(
            {
                "gbifID": 2000000 + i,
                "occurrenceID": f"urn:obis:{i:05d}",
                "basisOfRecord": "HUMAN_OBSERVATION",
                "scientificName": species[sp_idx],
                "kingdom": "Animalia",
                "family": families[sp_idx],
                "decimalLatitude": round(-20.0 + random.uniform(-10, 10), 6),
                "decimalLongitude": round(165.0 + random.uniform(-5, 5), 6),
                "minimumDepthInMeters": round(random.uniform(-200, 0), 1),
                "maximumDepthInMeters": round(random.uniform(-11000, -100), 1),
                "waterBody": random.choice(
                    ["Pacific Ocean", "Coral Sea", "Tasman Sea"]
                ),
                "eventDate": f"202{random.randint(0, 4)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
            }
        )

    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {path} ({len(rows)} rows)")


def generate_minimal():
    """Dataset 3: Ultra-minimal 3-column CSV."""
    path = OUTPUT_DIR / "minimal.csv"
    rows = []
    for i in range(30):
        rows.append(
            {
                "species": random.choice(
                    ["Araucaria", "Podocarpus", "Nothofagus", "Agathis"]
                ),
                "latitude": round(-22.0 + random.uniform(-1, 1), 6),
                "longitude": round(166.5 + random.uniform(-1, 1), 6),
            }
        )

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["species", "latitude", "longitude"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {path} ({len(rows)} rows)")


def generate_adversarial():
    """Dataset 4: Worst-case data quality."""
    path = OUTPUT_DIR / "adversarial.csv"

    # Write with latin-1 encoding, accented headers, mixed types
    with open(path, "w", newline="", encoding="latin-1") as f:
        writer = csv.writer(f)
        # Headers with accents and special chars
        writer.writerow(
            ["espèce", "localité", "null_col1", "null_col2", "mixed_types", "spaces"]
        )
        for i in range(100):
            writer.writerow(
                [
                    random.choice(["Araucária", "Podocàrpus", "Nöthofagus", ""]),
                    random.choice(["Nouméa", "Côte", "Île des Pins", ""]),
                    None,  # Always null
                    "",  # Always empty string
                    random.choice([str(i), "text", "3.14", "", None]),
                    "   ",  # Only spaces
                ]
            )

    print(f"Generated {path} (100 rows, latin-1 encoded)")


# ── Extended corpus (Phase 4+) ────────────────────────────────────────────


def generate_checklist():
    """Dataset 5: Taxonomic checklist (narrow schema, no coordinates)."""
    path = OUTPUT_DIR / "checklist.csv"
    kingdoms = ["Plantae", "Animalia", "Fungi"]
    phyla = {
        "Plantae": "Tracheophyta",
        "Animalia": "Chordata",
        "Fungi": "Basidiomycota",
    }
    families = [
        "Araucariaceae",
        "Podocarpaceae",
        "Nothofagaceae",
        "Cupressaceae",
        "Myrtaceae",
        "Proteaceae",
        "Lauraceae",
        "Sapindaceae",
    ]
    genera = [
        "Araucaria",
        "Podocarpus",
        "Nothofagus",
        "Callitris",
        "Syzygium",
        "Stenocarpus",
        "Cryptocarya",
        "Cupaniopsis",
    ]
    rows = []
    for i in range(200):
        kingdom = kingdoms[i % len(kingdoms)]
        rows.append(
            {
                "taxonID": f"TAX-{i:05d}",
                "scientificName": f"{genera[i % len(genera)]} sp{i}",
                "kingdom": kingdom,
                "phylum": phyla[kingdom],
                "class": "Magnoliopsida" if kingdom == "Plantae" else "Mammalia",
                "order": f"Order_{i % 10}",
                "family": families[i % len(families)],
            }
        )

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {path} ({len(rows)} rows)")


def generate_custom_forest():
    """Dataset 6: French-language custom forest inventory (non-DwC names)."""
    path = OUTPUT_DIR / "custom_forest.csv"
    especes = ["Araucaria", "Podocarpus", "Nothofagus", "Agathis", "Callitris"]
    rows = []
    for i in range(150):
        rows.append(
            {
                "parcelle": f"P{(i // 10) + 1:02d}",
                "espece": random.choice(especes),
                "diam": round(random.uniform(5, 80), 1),
                "haut": round(random.uniform(2, 25), 1),
                "substrat": random.choice(["UM", "non-UM"]),
                "endemisme": random.choice(["endemique", "non-endemique"]),
            }
        )

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {path} ({len(rows)} rows)")


def generate_geojson_inventory():
    """Dataset 7: GeoJSON with polygon geometries and attributes."""
    import json

    path = OUTPUT_DIR / "inventory.geojson"
    features = []
    for i in range(50):
        lat = -22.0 + random.uniform(-0.5, 0.5)
        lon = 166.5 + random.uniform(-0.5, 0.5)
        # Simple square polygon
        d = 0.01
        coords = [
            [lon - d, lat - d],
            [lon + d, lat - d],
            [lon + d, lat + d],
            [lon - d, lat + d],
            [lon - d, lat - d],
        ]
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [coords]},
                "properties": {
                    "plot_id": f"PLOT-{i:03d}",
                    "species_count": random.randint(5, 50),
                    "dominant_species": random.choice(
                        ["Araucaria", "Podocarpus", "Nothofagus"]
                    ),
                    "area_ha": round(random.uniform(0.5, 10.0), 2),
                },
            }
        )

    geojson = {"type": "FeatureCollection", "features": features}
    with open(path, "w") as f:
        json.dump(geojson, f)

    print(f"Generated {path} ({len(features)} features)")


def generate_xlsx_mixed():
    """Dataset 8: Excel file with mixed types."""
    try:
        import importlib.util

        if importlib.util.find_spec("openpyxl") is None:
            raise ImportError("openpyxl not found")
    except ImportError:
        print("SKIP: openpyxl not installed, skipping XLSX fixture")
        return

    path = OUTPUT_DIR / "mixed_types.xlsx"
    import pandas as pd

    data = {
        "id": list(range(1, 81)),
        "name": [f"Sample_{i}" for i in range(80)],
        "value_str": [
            str(random.uniform(0, 100)) if random.random() > 0.2 else "N/A"
            for _ in range(80)
        ],
        "date_mixed": [
            random.choice(["2024-01-15", "15/01/2024", "Jan 2024", "", None])
            for _ in range(80)
        ],
        "numeric": [
            random.uniform(0, 100) if random.random() > 0.1 else None for _ in range(80)
        ],
        "category": [random.choice(["A", "B", "C", None]) for _ in range(80)],
    }
    df = pd.DataFrame(data)
    df.to_excel(path, index=False)

    print(f"Generated {path} ({len(df)} rows)")


if __name__ == "__main__":
    generate_gbif_terrestrial()
    generate_gbif_marine()
    generate_minimal()
    generate_adversarial()
    generate_checklist()
    generate_custom_forest()
    generate_geojson_inventory()
    generate_xlsx_mixed()
    print("\nAll fixtures generated!")
