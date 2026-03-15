#!/usr/bin/env python
"""
Build the gold set of labeled columns for ML training.

Extracts labeled columns from known data sources:
- GUYADIV (Guyane) — trees + plots with data dictionary
- Afrique (Gabon/Cameroun) — occurrences + plots
- NC (niamoto-gb) — occurrences + plots
- Test fixtures — 8 synthetic datasets
- Synthetic global — multi-biome × multi-language generated columns

Output: data/gold_set.json — list of LabeledColumn records.
"""

import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Label mappings (column_name → concept) ────────────────────────

# GUYADIV trees (French Guiana forest inventory)
GUYADIV_TREES_LABELS = {
    "tree_label": ("identifier.record", "identifier"),
    "plot_label": ("identifier.plot", "identifier"),
    "rank": ("taxonomy.rank", "taxonomy"),
    "taxon": ("taxonomy.species", "taxonomy"),
    "species": ("taxonomy.species", "taxonomy"),
    "family": ("taxonomy.family", "taxonomy"),
    "x": ("location.x_coord", "location"),
    "y": ("location.y_coord", "location"),
    "dbh1": ("measurement.diameter", "measurement"),
    "dbh2": ("measurement.diameter", "measurement"),
    "date1": ("event.date", "time"),
    "date2": ("event.date", "time"),
    "dead2": ("category.mortality", "category"),
    "pheno1": ("category.phenology", "category"),
    "pheno2": ("category.phenology", "category"),
    "det_by": ("text.observer", "text"),
    "date_det": ("event.year", "time"),
    "vouchers": ("identifier.specimen", "identifier"),
    "det_uncertain": ("category.quality", "category"),
    "auth_sp": ("text.authority", "text"),
    "auth_inf_sp": ("text.authority", "text"),
    "subpl_label": ("identifier.plot", "identifier"),
    "subpl_type": ("category.method", "category"),
    "subpl_width": ("measurement.length", "measurement"),
    "subpl_length": ("measurement.length", "measurement"),
    "subpl_x_orig": ("location.x_coord", "location"),
    "subpl_y_orig": ("location.y_coord", "location"),
    "dbh_other1": ("measurement.diameter", "measurement"),
    "dbh_other2": ("measurement.diameter", "measurement"),
}

# GUYADIV plots
GUYADIV_PLOTS_LABELS = {
    "plot_label": ("identifier.plot", "identifier"),
    "site": ("location.locality", "location"),
    "elevation": ("location.elevation", "location"),
    "long_dd": ("location.longitude", "location"),
    "lat_dd": ("location.latitude", "location"),
    "X_UTM": ("location.x_coord", "location"),
    "Y_UTM": ("location.y_coord", "location"),
    "type": ("category.method", "category"),
    "dim": ("measurement.area", "measurement"),
    "area": ("measurement.area", "measurement"),
    "no_subpl": ("statistic.count", "statistic"),
    "date1": ("event.year", "time"),
    "date2": ("event.year", "time"),
    "authors1": ("text.observer", "text"),
    "authors2": ("text.observer", "text"),
    "comments": ("text.notes", "text"),
    "dbh10_inv1": ("statistic.count", "statistic"),
    "sp_dbh10_inv1": ("statistic.count", "statistic"),
    "fam_dbh10_inv1": ("statistic.count", "statistic"),
    "indet_dbh10_inv1": ("statistic.count", "statistic"),
    "dbh10_inv2": ("statistic.count", "statistic"),
    "sp_dbh10_inv2": ("statistic.count", "statistic"),
    "fam_dbh10_inv2": ("statistic.count", "statistic"),
    "indet_dbh10_inv2": ("statistic.count", "statistic"),
    "dbh2_10_inv1": ("statistic.count", "statistic"),
    "sp_dbh2_10_inv1": ("statistic.count", "statistic"),
    "fam_dbh2_10_inv1": ("statistic.count", "statistic"),
    "indet_dbh2_10_inv1": ("statistic.count", "statistic"),
    "dbh2-10_inv2": ("statistic.count", "statistic"),
    "sp_dbh2_10_inv2": ("statistic.count", "statistic"),
    "fam_dbh2_10_inv2": ("statistic.count", "statistic"),
    "indet_dbh2_10_inv2": ("statistic.count", "statistic"),
}

# Afrique occurrences
AFRIQUE_OCC_LABELS = {
    "tax_fam": ("taxonomy.family", "taxonomy"),
    "tax_gen": ("taxonomy.genus", "taxonomy"),
    "tax_esp": ("taxonomy.species", "taxonomy"),
    "tax_sp_level": ("taxonomy.rank", "taxonomy"),
    "tax_rank01": ("taxonomy.rank", "taxonomy"),
    "tax_infra_level": ("taxonomy.rank", "taxonomy"),
    "tax_infra_level_auth": ("text.authority", "text"),
    "plot_name": ("identifier.plot", "identifier"),
    "idtax_individual_f": ("identifier.taxon", "identifier"),
    "id_n": ("identifier.record", "identifier"),
    "id_table_liste_plots_n": ("identifier.plot", "identifier"),
    "idrb_n": ("identifier.record", "identifier"),
    "stem_diameter": ("measurement.diameter", "measurement"),
    "taxa_mean_wood_density": ("measurement.wood_density", "measurement"),
    "taxa_mean_leaf_N_content": ("measurement.leaf_area", "measurement"),
    "elev": ("location.elevation", "location"),
    "locality_name": ("location.locality", "location"),
    "ddlat": ("location.latitude", "location"),
    "ddlon": ("location.longitude", "location"),
    "geo_pt": ("location.geometry", "geometry"),
    "taxa_phenology": ("category.phenology", "category"),
    "light_observations": ("category.light", "category"),
    "taxa_bioclimatic_group": ("category.bioclimate", "category"),
    "taxa_bioclimatic_subgroup": ("category.bioclimate", "category"),
    "taxa_succession_guild": ("category.succession", "category"),
    "taxa_level_wood_density_mean": ("text.source", "text"),
    "taxa_level_phenology": ("text.source", "text"),
    "childdatabase": ("text.source", "text"),
    "data_src": ("text.source", "text"),
    "level_det": ("category.quality", "category"),
}

# Afrique plots
AFRIQUE_PLOTS_LABELS = {
    "id_liste_plots": ("identifier.plot", "identifier"),
    "plot_name": ("identifier.plot", "identifier"),
    "locality_name": ("location.locality", "location"),
    "country": ("location.country", "location"),
    "ddlat": ("location.latitude", "location"),
    "ddlon": ("location.longitude", "location"),
    "method": ("category.method", "category"),
    "date_y": ("event.year", "time"),
    "date_m": ("event.date", "time"),
    "data_provider": ("text.source", "text"),
    "nbe_stem": ("statistic.count", "statistic"),
    "sum_indet": ("statistic.count", "statistic"),
    "sum_indet_genus": ("statistic.count", "statistic"),
    "sum_indet_family": ("statistic.count", "statistic"),
    "locality": ("location.locality", "location"),
    "prop_det": ("statistic.ratio", "statistic"),
    "prop_det_genus": ("statistic.ratio", "statistic"),
    "prop_det_fam": ("statistic.ratio", "statistic"),
    "geo_pt": ("location.geometry", "geometry"),
}

# NC occurrences (niamoto-gb)
NC_OCC_LABELS = {
    "tax_fam": ("taxonomy.family", "taxonomy"),
    "tax_gen": ("taxonomy.genus", "taxonomy"),
    "tax_esp": ("taxonomy.species", "taxonomy"),
    "tax_sp_level": ("taxonomy.rank", "taxonomy"),
    "tax_infra_level": ("taxonomy.rank", "taxonomy"),
    "tax_infra_level_auth": ("text.authority", "text"),
    "plot_name": ("identifier.plot", "identifier"),
    "idtax_individual_f": ("identifier.taxon", "identifier"),
    "id_n": ("identifier.record", "identifier"),
    "id_table_liste_plots_n": ("identifier.plot", "identifier"),
    "stem_diameter": ("measurement.diameter", "measurement"),
    "light_observations": ("category.light", "category"),
    "taxa_level_wood_density_mean": ("text.source", "text"),
    "taxa_level_phenology": ("text.source", "text"),
    "elev": ("location.elevation", "location"),
    "ddlat": ("location.latitude", "location"),
    "ddlon": ("location.longitude", "location"),
    "locality_name": ("location.locality", "location"),
    "geo_pt": ("location.geometry", "geometry"),
}

# NC plots
NC_PLOTS_LABELS = {
    "locality_name": ("location.locality", "location"),
    "ddlat": ("location.latitude", "location"),
    "ddlon": ("location.longitude", "location"),
    "country": ("location.country", "location"),
    "nbe_stem": ("statistic.count", "statistic"),
    "nbe_plots": ("statistic.count", "statistic"),
    "id_loc": ("identifier.plot", "identifier"),
    "geo_pt": ("location.geometry", "geometry"),
}

# GBIF marine fixture (DwC)
GBIF_MARINE_LABELS = {
    "gbifID": ("identifier.record", "identifier"),
    "occurrenceID": ("identifier.record", "identifier"),
    "basisOfRecord": ("category.basis", "category"),
    "scientificName": ("taxonomy.species", "taxonomy"),
    "kingdom": ("taxonomy.kingdom", "taxonomy"),
    "family": ("taxonomy.family", "taxonomy"),
    "decimalLatitude": ("location.latitude", "location"),
    "decimalLongitude": ("location.longitude", "location"),
    "minimumDepthInMeters": ("location.depth", "location"),
    "maximumDepthInMeters": ("location.depth", "location"),
    "waterBody": ("location.locality", "location"),
    "eventDate": ("event.date", "time"),
}

# GBIF terrestrial fixture (DwC)
GBIF_TERRESTRIAL_LABELS = {
    "gbifID": ("identifier.record", "identifier"),
    "occurrenceID": ("identifier.record", "identifier"),
    "basisOfRecord": ("category.basis", "category"),
    "scientificName": ("taxonomy.species", "taxonomy"),
    "kingdom": ("taxonomy.kingdom", "taxonomy"),
    "phylum": ("taxonomy.phylum", "taxonomy"),
    "family": ("taxonomy.family", "taxonomy"),
    "genus": ("taxonomy.genus", "taxonomy"),
    "specificEpithet": ("taxonomy.species", "taxonomy"),
    "taxonRank": ("taxonomy.rank", "taxonomy"),
    "decimalLatitude": ("location.latitude", "location"),
    "decimalLongitude": ("location.longitude", "location"),
    "coordinateUncertaintyInMeters": ("measurement.uncertainty", "measurement"),
    "eventDate": ("event.date", "time"),
    "year": ("event.year", "time"),
    "countryCode": ("location.country", "location"),
    "elevation": ("location.elevation", "location"),
    "remarks": ("text.notes", "text"),
}

# Custom forest fixture (French headers)
CUSTOM_FOREST_LABELS = {
    "parcelle": ("identifier.plot", "identifier"),
    "espece": ("taxonomy.species", "taxonomy"),
    "diam": ("measurement.diameter", "measurement"),
    "haut": ("measurement.height", "measurement"),
    "substrat": ("category.habitat", "category"),
    "endemisme": ("category.endemism", "category"),
}

# Checklist fixture
CHECKLIST_LABELS = {
    "taxonID": ("identifier.taxon", "identifier"),
    "scientificName": ("taxonomy.species", "taxonomy"),
    "kingdom": ("taxonomy.kingdom", "taxonomy"),
    "phylum": ("taxonomy.phylum", "taxonomy"),
    "class": ("taxonomy.class", "taxonomy"),
    "order": ("taxonomy.order", "taxonomy"),
    "family": ("taxonomy.family", "taxonomy"),
}

# Minimal fixture
MINIMAL_LABELS = {
    "species": ("taxonomy.species", "taxonomy"),
    "latitude": ("location.latitude", "location"),
    "longitude": ("location.longitude", "location"),
}

# Adversarial fixture (French with encoding issues)
ADVERSARIAL_LABELS = {
    "espèce": ("taxonomy.species", "taxonomy"),
    "localité": ("location.locality", "location"),
    "null_col1": ("other", "other"),
    "null_col2": ("other", "other"),
    "mixed_types": ("other", "other"),
    "spaces": ("text.notes", "text"),
}


# ── Data source definitions ──────────────────────────────────────

ROOT = Path(__file__).parent.parent.parent  # niamoto/
NIAMOTO_DATA = ROOT.parent / "niamoto-data"

SOURCES = [
    {
        "name": "guyadiv_trees",
        "path": NIAMOTO_DATA / "Datas/Guyane/dataverse_files/GUYADIV_trees_v1.csv",
        "labels": GUYADIV_TREES_LABELS,
        "language": "en",
        "sample_rows": 1000,
    },
    {
        "name": "guyadiv_plots",
        "path": NIAMOTO_DATA / "Datas/Guyane/dataverse_files/GUYADIV_plots_v1.csv",
        "labels": GUYADIV_PLOTS_LABELS,
        "language": "en",
        "sample_rows": None,
    },
    {
        "name": "afrique_occ",
        "path": NIAMOTO_DATA / "Datas/Afrique/imports/occurrences.csv",
        "labels": AFRIQUE_OCC_LABELS,
        "language": "en",
        "sample_rows": 1000,
    },
    {
        "name": "afrique_plots",
        "path": NIAMOTO_DATA / "Datas/Afrique/imports/plots.csv",
        "labels": AFRIQUE_PLOTS_LABELS,
        "language": "en",
        "sample_rows": None,
    },
    {
        "name": "nc_occ",
        "path": ROOT / "test-instance/niamoto-gb/imports/occurrences.csv",
        "labels": NC_OCC_LABELS,
        "language": "en",
        "sample_rows": 1000,
    },
    {
        "name": "nc_plots",
        "path": ROOT / "test-instance/niamoto-gb/imports/plots.csv",
        "labels": NC_PLOTS_LABELS,
        "language": "en",
        "sample_rows": None,
    },
    {
        "name": "gbif_marine",
        "path": ROOT / "tests/fixtures/datasets/gbif_marine.tsv",
        "labels": GBIF_MARINE_LABELS,
        "language": "en",
        "sample_rows": None,
        "sep": "\t",
    },
    {
        "name": "gbif_terrestrial",
        "path": ROOT / "tests/fixtures/datasets/gbif_terrestrial.tsv",
        "labels": GBIF_TERRESTRIAL_LABELS,
        "language": "en",
        "sample_rows": None,
        "sep": "\t",
    },
    {
        "name": "custom_forest",
        "path": ROOT / "tests/fixtures/datasets/custom_forest.csv",
        "labels": CUSTOM_FOREST_LABELS,
        "language": "fr",
        "sample_rows": None,
    },
    {
        "name": "checklist",
        "path": ROOT / "tests/fixtures/datasets/checklist.csv",
        "labels": CHECKLIST_LABELS,
        "language": "en",
        "sample_rows": None,
    },
    {
        "name": "minimal",
        "path": ROOT / "tests/fixtures/datasets/minimal.csv",
        "labels": MINIMAL_LABELS,
        "language": "en",
        "sample_rows": None,
    },
    {
        "name": "adversarial",
        "path": ROOT / "tests/fixtures/datasets/adversarial.csv",
        "labels": ADVERSARIAL_LABELS,
        "language": "fr",
        "sample_rows": None,
    },
]


# ── Synthetic generation ─────────────────────────────────────────

BIOMES = {
    "tropical_rainforest": {
        "measurement.diameter": {
            "dist": "lognormal",
            "mean": 3.0,
            "sigma": 0.8,
            "clip": (5, 300),
        },
        "measurement.height": {"dist": "normal", "mean": 20, "std": 8, "clip": (2, 50)},
        "location.elevation": {"dist": "uniform", "low": 0, "high": 1500},
    },
    "temperate_forest": {
        "measurement.diameter": {
            "dist": "lognormal",
            "mean": 3.2,
            "sigma": 0.7,
            "clip": (5, 200),
        },
        "measurement.height": {"dist": "normal", "mean": 18, "std": 7, "clip": (2, 40)},
        "location.elevation": {"dist": "uniform", "low": 100, "high": 2500},
    },
    "boreal_forest": {
        "measurement.diameter": {
            "dist": "lognormal",
            "mean": 2.8,
            "sigma": 0.6,
            "clip": (5, 80),
        },
        "measurement.height": {"dist": "normal", "mean": 12, "std": 4, "clip": (2, 25)},
        "location.elevation": {"dist": "uniform", "low": 0, "high": 1000},
    },
    "mangrove": {
        "measurement.diameter": {
            "dist": "lognormal",
            "mean": 2.5,
            "sigma": 0.7,
            "clip": (2, 50),
        },
        "measurement.height": {"dist": "normal", "mean": 8, "std": 4, "clip": (1, 20)},
        "location.elevation": {"dist": "uniform", "low": -2, "high": 10},
    },
    "marine": {
        "location.depth": {"dist": "uniform", "low": -5000, "high": 0},
        "environment.salinity": {
            "dist": "normal",
            "mean": 35,
            "std": 2,
            "clip": (0, 40),
        },
        "environment.ph": {
            "dist": "normal",
            "mean": 8.1,
            "std": 0.15,
            "clip": (7.5, 8.5),
        },
        "environment.temperature": {
            "dist": "normal",
            "mean": 15,
            "std": 8,
            "clip": (-2, 35),
        },
    },
    "grassland": {
        "measurement.height": {"dist": "uniform", "low": 0.01, "high": 2},
        "measurement.cover": {"dist": "uniform", "low": 0, "high": 100},
    },
    "alpine": {
        "measurement.diameter": {
            "dist": "lognormal",
            "mean": 2.3,
            "sigma": 0.5,
            "clip": (3, 40),
        },
        "measurement.height": {"dist": "normal", "mean": 6, "std": 3, "clip": (1, 15)},
        "location.elevation": {"dist": "uniform", "low": 1500, "high": 4500},
    },
}

HEADER_VARIANTS = {
    "en": {
        "measurement.diameter": ["dbh", "diameter", "trunk_diameter", "stem_diam"],
        "measurement.height": ["height", "tree_height", "h_tot", "canopy_height"],
        "location.elevation": ["elevation", "altitude", "elev"],
        "location.depth": ["depth", "water_depth", "min_depth"],
        "location.latitude": ["latitude", "lat", "decimal_latitude"],
        "location.longitude": ["longitude", "lon", "decimal_longitude"],
        "environment.salinity": ["salinity", "sal"],
        "environment.ph": ["ph", "water_ph"],
        "environment.temperature": ["temperature", "temp", "water_temp"],
        "measurement.cover": ["cover", "cover_pct", "canopy_cover"],
        "taxonomy.species": ["species", "scientific_name", "taxon"],
        "taxonomy.family": ["family", "plant_family"],
        "statistic.count": ["count", "abundance", "n_individuals"],
        "event.date": ["date", "event_date", "collection_date"],
        "identifier.record": ["id", "record_id", "sample_id"],
    },
    "fr": {
        "measurement.diameter": ["diametre", "diam", "dhp"],
        "measurement.height": ["hauteur", "haut", "hauteur_arbre"],
        "location.elevation": ["altitude", "alt"],
        "location.depth": ["profondeur", "prof"],
        "location.latitude": ["latitude", "lat"],
        "location.longitude": ["longitude", "lon"],
        "environment.temperature": ["temperature", "temp"],
        "measurement.cover": ["couverture", "recouvrement"],
        "taxonomy.species": ["espece", "nom_scientifique"],
        "taxonomy.family": ["famille"],
        "statistic.count": ["nombre", "abondance", "effectif"],
        "event.date": ["date", "date_collecte"],
        "identifier.record": ["id", "identifiant"],
    },
    "es": {
        "measurement.diameter": ["diametro", "dap"],
        "measurement.height": ["altura", "alto"],
        "location.elevation": ["altitud", "elevacion"],
        "location.latitude": ["latitud", "lat"],
        "location.longitude": ["longitud", "lon"],
        "taxonomy.species": ["especie", "nombre_cientifico"],
        "taxonomy.family": ["familia"],
        "statistic.count": ["numero", "abundancia"],
        "event.date": ["fecha", "fecha_colecta"],
        "identifier.record": ["id", "identificador"],
    },
    "anonymous": {
        "measurement.diameter": ["X1", "col_1", "var_a"],
        "measurement.height": ["X2", "col_2", "var_b"],
        "location.latitude": ["X3", "col_3"],
        "location.longitude": ["X4", "col_4"],
        "taxonomy.species": ["X5", "col_5"],
        "taxonomy.family": ["X6", "col_6"],
        "statistic.count": ["X7", "col_7"],
    },
}

GENERA = [
    "Araucaria",
    "Agathis",
    "Podocarpus",
    "Metrosideros",
    "Syzygium",
    "Quercus",
    "Fagus",
    "Betula",
    "Picea",
    "Abies",
    "Pinus",
    "Acacia",
    "Eucalyptus",
    "Rhizophora",
    "Avicennia",
    "Shorea",
    "Dipterocarpus",
]
EPITHETS = [
    "columnaris",
    "lanceolata",
    "minor",
    "montana",
    "robusta",
    "alba",
    "nigra",
    "rubra",
    "latifolia",
    "angustifolia",
    "sylvestris",
    "orientalis",
    "japonica",
    "indica",
    "africana",
]
FAMILIES = [
    "Araucariaceae",
    "Podocarpaceae",
    "Cunoniaceae",
    "Myrtaceae",
    "Proteaceae",
    "Fagaceae",
    "Betulaceae",
    "Pinaceae",
    "Fabaceae",
    "Dipterocarpaceae",
    "Rhizophoraceae",
    "Euphorbiaceae",
    "Lauraceae",
    "Sapindaceae",
    "Rubiaceae",
    "Orchidaceae",
    "Arecaceae",
]


def _generate_series(spec: dict, n: int = 200) -> pd.Series:
    """Generate a synthetic series from a distribution spec."""
    dist = spec["dist"]
    if dist == "lognormal":
        vals = np.random.lognormal(spec["mean"], spec["sigma"], n)
    elif dist == "normal":
        vals = np.random.normal(spec["mean"], spec["std"], n)
    elif dist == "uniform":
        vals = np.random.uniform(spec["low"], spec["high"], n)
    else:
        vals = np.random.randn(n)
    if "clip" in spec:
        vals = np.clip(vals, *spec["clip"])
    # Add ~5% NaN
    mask = np.random.random(n) < 0.05
    vals = vals.astype(float)
    vals[mask] = np.nan
    return pd.Series(vals)


def generate_synthetic_columns(rng_seed: int = 42) -> list[dict]:
    """Generate synthetic labeled columns across biomes and languages."""
    np.random.seed(rng_seed)
    records = []

    for biome_name, biome_cols in BIOMES.items():
        for concept, spec in biome_cols.items():
            for lang, variants in HEADER_VARIANTS.items():
                if concept not in variants:
                    continue
                for header in variants[concept]:
                    series = _generate_series(spec)
                    records.append(
                        {
                            "column_name": header,
                            "values_sample": series.dropna().head(50).tolist(),
                            "values_stats": _series_stats(series),
                            "concept": concept,
                            "role": concept.split(".")[0],
                            "source_dataset": f"synthetic_{biome_name}",
                            "language": lang if lang != "anonymous" else "en",
                            "is_anonymous": lang == "anonymous",
                            "quality": "synthetic",
                        }
                    )

    # Taxonomy columns
    for lang, variants in HEADER_VARIANTS.items():
        for concept in ["taxonomy.species", "taxonomy.family"]:
            if concept not in variants:
                continue
            for header in variants[concept]:
                if concept == "taxonomy.species":
                    vals = [
                        f"{np.random.choice(GENERA)} {np.random.choice(EPITHETS)}"
                        for _ in range(200)
                    ]
                else:
                    vals = list(np.random.choice(FAMILIES, 200))
                series = pd.Series(vals)
                records.append(
                    {
                        "column_name": header,
                        "values_sample": series.head(50).tolist(),
                        "values_stats": _series_stats(series),
                        "concept": concept,
                        "role": "taxonomy",
                        "source_dataset": "synthetic_taxonomy",
                        "language": lang if lang != "anonymous" else "en",
                        "is_anonymous": lang == "anonymous",
                        "quality": "synthetic",
                    }
                )

    # Count/abundance columns
    for lang, variants in HEADER_VARIANTS.items():
        if "statistic.count" not in variants:
            continue
        for header in variants["statistic.count"]:
            vals = np.random.poisson(5, 200)
            series = pd.Series(vals)
            records.append(
                {
                    "column_name": header,
                    "values_sample": series.head(50).tolist(),
                    "values_stats": _series_stats(series),
                    "concept": "statistic.count",
                    "role": "statistic",
                    "source_dataset": "synthetic_count",
                    "language": lang if lang != "anonymous" else "en",
                    "is_anonymous": lang == "anonymous",
                    "quality": "synthetic",
                }
            )

    # Coordinate columns
    for lang, variants in HEADER_VARIANTS.items():
        for concept in ["location.latitude", "location.longitude"]:
            if concept not in variants:
                continue
            for header in variants[concept]:
                if concept == "location.latitude":
                    vals = np.random.uniform(-60, 70, 200)
                else:
                    vals = np.random.uniform(-170, 170, 200)
                series = pd.Series(vals)
                records.append(
                    {
                        "column_name": header,
                        "values_sample": series.head(50).tolist(),
                        "values_stats": _series_stats(series),
                        "concept": concept,
                        "role": "location",
                        "source_dataset": "synthetic_coords",
                        "language": lang if lang != "anonymous" else "en",
                        "is_anonymous": lang == "anonymous",
                        "quality": "synthetic",
                    }
                )

    # Date columns
    for lang, variants in HEADER_VARIANTS.items():
        if "event.date" not in variants:
            continue
        for header in variants["event.date"]:
            dates = pd.date_range("2000-01-01", periods=200, freq="D")
            series = pd.Series(dates.strftime("%Y-%m-%d"))
            records.append(
                {
                    "column_name": header,
                    "values_sample": series.head(50).tolist(),
                    "values_stats": _series_stats(series),
                    "concept": "event.date",
                    "role": "time",
                    "source_dataset": "synthetic_dates",
                    "language": lang if lang != "anonymous" else "en",
                    "is_anonymous": lang == "anonymous",
                    "quality": "synthetic",
                }
            )

    # ID columns
    for lang, variants in HEADER_VARIANTS.items():
        if "identifier.record" not in variants:
            continue
        for header in variants["identifier.record"]:
            ids = [f"REC_{i:05d}" for i in range(200)]
            series = pd.Series(ids)
            records.append(
                {
                    "column_name": header,
                    "values_sample": series.head(50).tolist(),
                    "values_stats": _series_stats(series),
                    "concept": "identifier.record",
                    "role": "identifier",
                    "source_dataset": "synthetic_ids",
                    "language": lang if lang != "anonymous" else "en",
                    "is_anonymous": lang == "anonymous",
                    "quality": "synthetic",
                }
            )

    logger.info(f"Generated {len(records)} synthetic columns")
    return records


def _series_stats(series: pd.Series) -> dict:
    """Compute summary stats for a series (for storage without raw data)."""
    stats = {
        "n": len(series),
        "null_ratio": float(series.isnull().mean()),
        "unique_ratio": float(series.nunique() / max(len(series), 1)),
        "dtype": str(series.dtype),
    }
    clean = series.dropna()
    if pd.api.types.is_numeric_dtype(clean) and len(clean) > 0:
        stats.update(
            {
                "mean": float(clean.mean()),
                "std": float(clean.std()) if len(clean) > 1 else 0.0,
                "min": float(clean.min()),
                "max": float(clean.max()),
            }
        )
    else:
        str_vals = clean.astype(str)
        stats["mean_length"] = (
            float(str_vals.str.len().mean()) if len(str_vals) > 0 else 0.0
        )
    return stats


# ── Extract from real sources ────────────────────────────────────


def extract_from_source(source: dict) -> list[dict]:
    """Extract labeled columns from a real data source."""
    path = source["path"]
    if not path.exists():
        logger.warning(f"Skipping {source['name']}: {path} not found")
        return []

    sep = source.get("sep", ",")
    nrows = source.get("sample_rows")

    try:
        df = pd.read_csv(path, sep=sep, nrows=nrows, low_memory=False)
    except UnicodeDecodeError:
        df = pd.read_csv(
            path, sep=sep, nrows=nrows, low_memory=False, encoding="latin-1"
        )

    records = []
    labels = source["labels"]

    for col_name in df.columns:
        if col_name not in labels:
            continue
        concept, role = labels[col_name]
        series = df[col_name]

        records.append(
            {
                "column_name": col_name,
                "values_sample": series.dropna().head(50).tolist(),
                "values_stats": _series_stats(series),
                "concept": concept,
                "role": role,
                "source_dataset": source["name"],
                "language": source["language"],
                "is_anonymous": False,
                "quality": "gold",
            }
        )

    logger.info(f"Extracted {len(records)} columns from {source['name']}")
    return records


# ── Main ─────────────────────────────────────────────────────────


def build_gold_set() -> list[dict]:
    """Build the complete gold set."""
    all_records = []

    # Extract from real sources
    for source in SOURCES:
        records = extract_from_source(source)
        all_records.extend(records)

    # Generate synthetic
    synthetic = generate_synthetic_columns()
    all_records.extend(synthetic)

    # Summary
    gold = [r for r in all_records if r["quality"] == "gold"]
    synthetic_count = [r for r in all_records if r["quality"] == "synthetic"]

    logger.info(f"\n{'=' * 50}")
    logger.info(f"Gold set built: {len(all_records)} total columns")
    logger.info(f"  Gold:      {len(gold)}")
    logger.info(f"  Synthetic: {len(synthetic_count)}")

    # Concept distribution
    from collections import Counter

    concept_counts = Counter(r["concept"] for r in all_records)
    logger.info(f"\nConcept distribution ({len(concept_counts)} concepts):")
    for concept, count in concept_counts.most_common():
        logger.info(f"  {concept:35s} {count:4d}")

    # Source distribution
    source_counts = Counter(r["source_dataset"] for r in all_records)
    logger.info(f"\nSource distribution ({len(source_counts)} sources):")
    for src, count in source_counts.most_common():
        logger.info(f"  {src:35s} {count:4d}")

    return all_records


def main():
    output_dir = ROOT / "data"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "gold_set.json"

    records = build_gold_set()

    # Serialize (convert numpy types for JSON)
    def _convert(obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, pd.Timestamp):
            return str(obj)
        return obj

    with open(output_path, "w") as f:
        json.dump(records, f, indent=2, default=_convert)

    logger.info(f"\nSaved to {output_path}")
    logger.info(f"Total: {len(records)} labeled columns")


if __name__ == "__main__":
    main()
