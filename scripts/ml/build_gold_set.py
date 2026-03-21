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

import copy
import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Add src and repo root to path so the script works both as
# `python scripts/ml/build_gold_set.py` and `python -m scripts.ml.build_gold_set`.
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

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

# Niamoto NC occurrences (Nouvelle-Calédonie — full instance)
NC_FULL_OCC_LABELS = {
    "id": ("identifier.record", "identifier"),
    "id_taxonref": ("identifier.taxon", "identifier"),
    "plot_name": ("location.locality", "location"),
    "taxaname": ("taxonomy.species", "taxonomy"),
    "taxonref": ("taxonomy.species", "taxonomy"),
    "family": ("taxonomy.family", "taxonomy"),
    "genus": ("taxonomy.genus", "taxonomy"),
    "species": ("taxonomy.species", "taxonomy"),
    "infra": ("taxonomy.rank", "taxonomy"),
    "id_rank": ("taxonomy.rank", "taxonomy"),
    "dbh": ("measurement.diameter", "measurement"),
    "height": ("measurement.height", "measurement"),
    "strata": ("category.stratum", "category"),
    "flower": ("category.phenology", "category"),
    "fruit": ("category.phenology", "category"),
    "month_obs": ("event.date", "time"),
    "bark_thickness": ("measurement.trait", "measurement"),
    "leaf_area": ("measurement.leaf_area", "measurement"),
    "leaf_ldmc": ("measurement.trait", "measurement"),
    "leaf_sla": ("measurement.trait", "measurement"),
    "leaf_thickness": ("measurement.trait", "measurement"),
    "wood_density": ("measurement.wood_density", "measurement"),
    "elevation": ("location.elevation", "location"),
    "rainfall": ("environment.precipitation", "environment"),
    "holdridge": ("category.bioclimate", "category"),
    "province": ("location.admin_area", "location"),
    "in_forest": ("category.ecology", "category"),
    "in_um": ("category.status", "category"),
    "geo_pt": ("location.geometry", "geometry"),
}

# Niamoto NC plots (Nouvelle-Calédonie — full instance)
NC_FULL_PLOTS_LABELS = {
    "id_plot": ("identifier.record", "identifier"),
    "plot": ("identifier.plot", "identifier"),
    "elevation": ("location.elevation", "location"),
    "rainfall": ("environment.precipitation", "environment"),
    "holdridge": ("category.bioclimate", "category"),
    "in_um": ("category.status", "category"),
    "species_level": ("measurement.trait", "measurement"),
    "total_stems": ("statistic.count", "statistic"),
    "living_stems": ("statistic.count", "statistic"),
    "nb_families": ("statistic.count", "statistic"),
    "nb_species": ("statistic.count", "statistic"),
    "shannon": ("measurement.trait", "measurement"),
    "pielou": ("measurement.trait", "measurement"),
    "simpson": ("measurement.trait", "measurement"),
    "basal_area": ("measurement.basal_area", "measurement"),
    "h_mean": ("measurement.height", "measurement"),
    "dbh_median": ("measurement.diameter", "measurement"),
    "biomass": ("measurement.biomass", "measurement"),
    "wood_density_mean": ("measurement.wood_density", "measurement"),
    "pteridophytes": ("statistic.count", "statistic"),
    "gymnospermae": ("statistic.count", "statistic"),
    "monocotyledonae": ("statistic.count", "statistic"),
    "dicotyledonae": ("statistic.count", "statistic"),
    "emergent": ("statistic.count", "statistic"),
    "canopy": ("statistic.count", "statistic"),
    "undercanopy": ("statistic.count", "statistic"),
    "understorey": ("statistic.count", "statistic"),
    "geo_pt": ("location.geometry", "geometry"),
}

# NC occurrences (niamoto-gb / Gabon)
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

# ForestScan Paracou census (French Guiana, Guyafor/ForestScan)
FORESTSCAN_PARACOU_LABELS = {
    "Forest": ("location.locality", "location"),
    "Plot": ("identifier.plot", "identifier"),
    "PlotArea": ("measurement.area", "measurement"),
    "GeolPlot": ("location.locality", "location"),
    "SubPlot": ("identifier.plot", "identifier"),
    "TreeFieldNum": ("identifier.record", "identifier"),
    "idTree": ("identifier.record", "identifier"),
    "Xfield": ("location.x_coord", "location"),
    "Yfield": ("location.y_coord", "location"),
    "Xutm": ("location.x_coord", "location"),
    "Yutm": ("location.y_coord", "location"),
    "Lat": ("location.latitude", "location"),
    "Lon": ("location.longitude", "location"),
    "Family": ("taxonomy.family", "taxonomy"),
    "Genus": ("taxonomy.genus", "taxonomy"),
    "Species": ("taxonomy.species", "taxonomy"),
    "Author": ("text.authority", "text"),
    "Botanist": ("text.observer", "text"),
    "IdentYear": ("event.year", "time"),
    "FamilyFilled": ("taxonomy.family", "taxonomy"),
    "GenusFilled": ("taxonomy.genus", "taxonomy"),
    "SpeciesFilled": ("taxonomy.species", "taxonomy"),
    "AuthorFilled": ("text.authority", "text"),
    "BotaSource": ("text.source", "text"),
    "BotaCertainty": ("category.quality", "category"),
    "VernName": ("taxonomy.vernacular_name", "taxonomy"),
    "CensusYear": ("event.year", "time"),
    "CensusDate": ("event.date", "time"),
    "CensusDateCertainty": ("category.quality", "category"),
    "CodeAlive": ("category.status", "category"),
    "Circ": ("measurement.circumference", "measurement"),
    "CircCorr": ("measurement.circumference", "measurement"),
    "POM": ("measurement.height", "measurement"),
    "POMCertainty": ("category.quality", "category"),
}

# ── Silver sources ───────────────────────────────────────────────

# IFN France — ARBRE (trees) — French headers
IFN_ARBRE_LABELS = {
    "CAMPAGNE": ("event.year", "time"),
    "IDP": ("identifier.plot", "identifier"),
    "A": ("identifier.record", "identifier"),
    "ESPAR": ("taxonomy.species", "taxonomy"),
    "VEGET": ("category.vegetation", "category"),
    "VEGET5": ("category.vegetation", "category"),
    "ORI": ("category.origin", "category"),
    "TIGE": ("category.stem_type", "category"),
    "FORME": ("category.form", "category"),
    "TETARD": ("category.pollard", "category"),
    "QUALITE": ("category.quality", "category"),
    "CIBLE": ("category.target", "category"),
    "LIB": ("measurement.cover", "measurement"),
    "AGE13": ("measurement.age", "measurement"),
    "AGE": ("measurement.age", "measurement"),
    "SIMPLIF": ("category.method", "category"),
    "ACCI": ("category.damage", "category"),
    "C13": ("measurement.circumference", "measurement"),
    "HTOT": ("measurement.height", "measurement"),
    "HDEC": ("measurement.height", "measurement"),
    "DECOUPE": ("category.cutting", "category"),
    "LFSD": ("measurement.length", "measurement"),
    "V": ("measurement.volume", "measurement"),
    "W": ("measurement.biomass", "measurement"),
    "IR5": ("measurement.increment", "measurement"),
    "IR1": ("measurement.increment", "measurement"),
    "MORTB": ("category.mortality", "category"),
    "SFCOEUR": ("category.damage", "category"),
    "SFGUI": ("category.damage", "category"),
    "SFGELIV": ("category.damage", "category"),
    "SFDORGE": ("category.damage", "category"),
    "SFPIED": ("category.damage", "category"),
    "DATEMORT": ("event.date", "time"),
}

# IFN France — PLACETTE (plots)
IFN_PLACETTE_LABELS = {
    "CAMPAGNE": ("event.year", "time"),
    "IDP": ("identifier.plot", "identifier"),
    "XL": ("location.longitude", "location"),
    "YL": ("location.latitude", "location"),
    "DATEPOINT": ("event.date", "time"),
    "DEP": ("location.admin_area", "location"),
    "GRECO": ("location.ecoregion", "location"),
    "SER": ("location.ecoregion", "location"),
    "PENTEXP": ("measurement.slope", "measurement"),
    "GEST": ("category.management", "category"),
    "ELAG": ("category.pruning", "category"),
    "CSA": ("category.forest_type", "category"),
    "BOIS": ("category.forest_type", "category"),
    "PEUPNR": ("category.stand_type", "category"),
    "PLISI": ("category.edge", "category"),
    "BORD": ("category.edge", "category"),
    "TM2": ("measurement.area", "measurement"),
    "DC": ("measurement.distance", "measurement"),
}

# IFN France — ECOLOGIE
IFN_ECOLOGIE_LABELS = {
    "CAMPAGNE": ("event.year", "time"),
    "IDP": ("identifier.plot", "identifier"),
    "TOPO": ("category.topography", "category"),
    "EXPO": ("measurement.aspect", "measurement"),
    "PENT2": ("measurement.slope", "measurement"),
    "HUMUS": ("category.humus", "category"),
    "TSOL": ("category.soil_type", "category"),
    "PROF1": ("measurement.depth", "measurement"),
    "PROF2": ("measurement.depth", "measurement"),
    "TEXT1": ("category.soil_texture", "category"),
    "TEXT2": ("category.soil_texture", "category"),
    "ROCHE": ("category.rock_type", "category"),
    "AFFROC": ("measurement.rock_cover", "measurement"),
    "CAILLOUX": ("category.stone_size", "category"),
    "LIGN1": ("measurement.cover", "measurement"),
    "LIGN2": ("measurement.cover", "measurement"),
    "HERB": ("measurement.cover", "measurement"),
    "MOUSSE": ("measurement.cover", "measurement"),
    "PCALC": ("category.calcareous", "category"),
    "PGLEY": ("category.gley", "category"),
}

# IFN France — FLORE
IFN_FLORE_LABELS = {
    "CAMPAGNE": ("event.year", "time"),
    "IDP": ("identifier.plot", "identifier"),
    "CD_REF": ("identifier.taxon", "identifier"),
    "ABOND": ("statistic.count", "statistic"),
}

# IFN France — COUVERT (canopy cover)
IFN_COUVERT_LABELS = {
    "CAMPAGNE": ("event.year", "time"),
    "IDP": ("identifier.plot", "identifier"),
    "STRATE": ("category.stratum", "category"),
    "ESPAR_C": ("taxonomy.species", "taxonomy"),
    "TCA": ("measurement.cover", "measurement"),
    "TCL": ("measurement.cover", "measurement"),
    "P1525": ("measurement.cover", "measurement"),
    "P7ARES": ("measurement.cover", "measurement"),
}

# IFN France — BOIS_MORT (dead wood)
IFN_BOIS_MORT_LABELS = {
    "CAMPAGNE": ("event.year", "time"),
    "IDP": ("identifier.plot", "identifier"),
    "A": ("identifier.record", "identifier"),
    "ESPAR_BM": ("taxonomy.species", "taxonomy"),
    "FREPLI": ("statistic.count", "statistic"),
    "DBM": ("measurement.diameter", "measurement"),
    "DECOMP": ("category.decay_stage", "category"),
}

# IFN France — HABITAT
IFN_HABITAT_LABELS = {
    "CAMPAGNE": ("event.year", "time"),
    "IDP": ("identifier.plot", "identifier"),
    "HAB": ("category.habitat", "category"),
    "QUALHAB": ("category.quality", "category"),
    "ASSOCIATION": ("category.vegetation", "category"),
    "ALLIANCE": ("category.vegetation", "category"),
    "ORDRE": ("taxonomy.order", "taxonomy"),
    "CLASSE": ("taxonomy.class", "taxonomy"),
    "CB_IFN": ("identifier.habitat", "identifier"),
    "CD_HAB": ("identifier.habitat", "identifier"),
    "HIC": ("category.habitat", "category"),
    "EUNIS": ("category.habitat", "category"),
}

# AFLIBER — Iberian vascular flora species list
AFLIBER_LABELS = {
    "Taxon": ("taxonomy.species", "taxonomy"),
    "Scientific_Name": ("taxonomy.species", "taxonomy"),
    "Endemic": ("category.endemism", "category"),
    "Genus": ("taxonomy.genus", "taxonomy"),
    "Species": ("taxonomy.species", "taxonomy"),
    "Subspecies": ("taxonomy.rank", "taxonomy"),
    "Class": ("taxonomy.class", "taxonomy"),
    "Order": ("taxonomy.order", "taxonomy"),
    "Family": ("taxonomy.family", "taxonomy"),
    "GBIF_id": ("identifier.taxon", "identifier"),
    "POW_Name": ("taxonomy.species", "taxonomy"),
}

# IEFC Catalonia — Spanish/Mediterranean forest traits
IEFC_CATALONIA_LABELS = {
    "Idutm": ("identifier.plot", "identifier"),
    "Species": ("taxonomy.species", "taxonomy"),
    "Samp_year": ("event.year", "time"),
    "Samp_month": ("event.date", "time"),
    "X_utm31N_m": ("location.x_coord", "location"),
    "Y_utm31N_m": ("location.y_coord", "location"),
    "County": ("location.admin_area", "location"),
    "Elevation_m": ("location.elevation", "location"),
    "Slope_deg": ("measurement.slope", "measurement"),
    "Aspect": ("measurement.aspect", "measurement"),
    "Prec_mm": ("environment.precipitation", "environment"),
    "Tair": ("environment.temperature", "environment"),
    "Tair_max": ("environment.temperature", "environment"),
    "Tair_min": ("environment.temperature", "environment"),
    "Density_stems_ha": ("statistic.density", "statistic"),
    "Biomass_t_ha": ("measurement.biomass", "measurement"),
    "Lithology": ("category.rock_type", "category"),
    "Nmass_percent": ("measurement.leaf_area", "measurement"),
    "LMA_mg_cm2": ("measurement.leaf_area", "measurement"),
    "Hmax_m": ("measurement.height", "measurement"),
    "WD_g_cm3": ("measurement.wood_density", "measurement"),
}

# FIA Vermont — TREE table (US forest inventory, abbreviated EN headers)
FIA_TREE_LABELS = {
    "CN": ("identifier.record", "identifier"),
    "PLT_CN": ("identifier.plot", "identifier"),
    "INVYR": ("event.year", "time"),
    "STATECD": ("location.admin_area", "location"),
    "COUNTYCD": ("location.admin_area", "location"),
    "PLOT": ("identifier.plot", "identifier"),
    "SUBP": ("identifier.plot", "identifier"),
    "TREE": ("identifier.record", "identifier"),
    "STATUSCD": ("category.status", "category"),
    "SPCD": ("taxonomy.species", "taxonomy"),
    "SPGRPCD": ("taxonomy.group", "taxonomy"),
    "DIA": ("measurement.diameter", "measurement"),
    "HT": ("measurement.height", "measurement"),
    "ACTUALHT": ("measurement.height", "measurement"),
    "CR": ("measurement.crown_ratio", "measurement"),
    "CCLCD": ("category.crown_class", "category"),
    "AGENTCD": ("category.damage", "category"),
    "CULL": ("measurement.defect", "measurement"),
    "TREECLCD": ("category.tree_class", "category"),
    "TREEGRCD": ("category.tree_grade", "category"),
    "CARBON_AG": ("measurement.biomass", "measurement"),
    "CARBON_BG": ("measurement.biomass", "measurement"),
    "DRYBIO_AG": ("measurement.biomass", "measurement"),
    "VOLCFNET": ("measurement.volume", "measurement"),
    "VOLCFGRS": ("measurement.volume", "measurement"),
}

# FIA Vermont — PLOT table
FIA_PLOT_LABELS = {
    "CN": ("identifier.record", "identifier"),
    "INVYR": ("event.year", "time"),
    "STATECD": ("location.admin_area", "location"),
    "COUNTYCD": ("location.admin_area", "location"),
    "PLOT": ("identifier.plot", "identifier"),
    "PLOT_STATUS_CD": ("category.status", "category"),
    "MEASYEAR": ("event.year", "time"),
    "MEASMON": ("event.date", "time"),
    "MEASDAY": ("event.date", "time"),
    "LAT": ("location.latitude", "location"),
    "LON": ("location.longitude", "location"),
    "ELEV": ("location.elevation", "location"),
    "DESIGNCD": ("category.method", "category"),
    "MANUAL": ("text.source", "text"),
    "CYCLE": ("event.year", "time"),
}

# Madagascar Berenty Reserve (Dryad)
BERENTY_LABELS = {
    "Forest_type": ("category.forest_type", "category"),
    "Forest": ("location.locality", "location"),
    "Plot": ("identifier.plot", "identifier"),
    "Decimal Latitude": ("location.latitude", "location"),
    "Decimal Longitude": ("location.longitude", "location"),
    "Elevation (m)": ("location.elevation", "location"),
    "Number": ("identifier.record", "identifier"),
    "Family": ("taxonomy.family", "taxonomy"),
    "Genus": ("taxonomy.genus", "taxonomy"),
    "Specific_epithet": ("taxonomy.species", "taxonomy"),
    "Author": ("text.authority", "text"),
    "Vernacular_name": ("taxonomy.vernacular_name", "taxonomy"),
    "Height_m": ("measurement.height", "measurement"),
    "Crown_a_m": ("measurement.crown", "measurement"),
    "Crown_b_m": ("measurement.crown", "measurement"),
    "CBH_cm": ("measurement.circumference", "measurement"),
    "Diameter_mm": ("measurement.diameter", "measurement"),
    "DBH_branch_cm": ("measurement.diameter", "measurement"),
    "DBH_individual_cm": ("measurement.diameter", "measurement"),
    "Basal_area": ("measurement.basal_area", "measurement"),
}

# Finland/Sweden — trees
FINLAND_TREES_LABELS = {
    "treecode": ("identifier.record", "identifier"),
    "plotcode": ("identifier.plot", "identifier"),
    "treestatus": ("category.status", "category"),
    "dbh1": ("measurement.diameter", "measurement"),
    "dbh2": ("measurement.diameter", "measurement"),
    "weight1": ("measurement.biomass", "measurement"),
    "weight2": ("measurement.biomass", "measurement"),
    "country": ("location.country", "location"),
    "taxonname": ("taxonomy.species", "taxonomy"),
}

# Finland/Sweden — plots
FINLAND_PLOTS_LABELS = {
    "plotcode": ("identifier.plot", "identifier"),
    "country": ("location.country", "location"),
    "surveydate1": ("event.date", "time"),
    "surveydate2": ("event.date", "time"),
    "longitude_generalised": ("location.longitude", "location"),
    "latitude_generalised": ("location.latitude", "location"),
    "management2": ("category.management", "category"),
}

# Pasoh Malaysia — crown traits
PASOH_CROWN_LABELS = {
    "sp": ("taxonomy.species", "taxonomy"),
    "family": ("taxonomy.family", "taxonomy"),
    "genus": ("taxonomy.genus", "taxonomy"),
    "species": ("taxonomy.species", "taxonomy"),
    "variety": ("taxonomy.rank", "taxonomy"),
    "growth.form": ("category.growth_form", "category"),
    "tag": ("identifier.record", "identifier"),
    "dbh": ("measurement.diameter", "measurement"),
    "exposure": ("category.light", "category"),
    "diameter": ("measurement.crown", "measurement"),
    "height": ("measurement.height", "measurement"),
}

# Pasoh Malaysia — leaf traits
PASOH_LEAF_LABELS = {
    "sp": ("taxonomy.species", "taxonomy"),
    "family": ("taxonomy.family", "taxonomy"),
    "genus": ("taxonomy.genus", "taxonomy"),
    "species": ("taxonomy.species", "taxonomy"),
    "variety": ("taxonomy.rank", "taxonomy"),
    "growth.form": ("category.growth_form", "category"),
    "tag": ("identifier.record", "identifier"),
    "dbh": ("measurement.diameter", "measurement"),
    "exposure": ("category.light", "category"),
    "leaflets": ("statistic.count", "statistic"),
    "leaf.area": ("measurement.leaf_area", "measurement"),
    "leaflet.area": ("measurement.leaf_area", "measurement"),
    "mass.fresh": ("measurement.biomass", "measurement"),
    "mass.dry": ("measurement.biomass", "measurement"),
    "LDMC": ("measurement.leaf_area", "measurement"),
    "LMA": ("measurement.leaf_area", "measurement"),
    "lamina.thickness": ("measurement.leaf_area", "measurement"),
    "lamina.density": ("measurement.wood_density", "measurement"),
}

# Pasoh Malaysia — wood density
PASOH_WOOD_LABELS = {
    "sp": ("taxonomy.species", "taxonomy"),
    "family": ("taxonomy.family", "taxonomy"),
    "genus": ("taxonomy.genus", "taxonomy"),
    "species": ("taxonomy.species", "taxonomy"),
    "variety": ("taxonomy.rank", "taxonomy"),
    "growth.form": ("category.growth_form", "category"),
    "numero": ("identifier.record", "identifier"),
    "dbh": ("measurement.diameter", "measurement"),
    "exposure": ("category.light", "category"),
    "wood.density": ("measurement.wood_density", "measurement"),
}


# GBIF DwC standard field mapping (shared across all GBIF datasets)
GBIF_DWC_LABELS = {
    "acceptedScientificName": ("taxonomy.species", "taxonomy"),
    "scientificName": ("taxonomy.species", "taxonomy"),
    "species": ("taxonomy.species", "taxonomy"),
    "specificEpithet": ("taxonomy.species", "taxonomy"),
    "kingdom": ("taxonomy.kingdom", "taxonomy"),
    "phylum": ("taxonomy.phylum", "taxonomy"),
    "class": ("taxonomy.class", "taxonomy"),
    "order": ("taxonomy.order", "taxonomy"),
    "family": ("taxonomy.family", "taxonomy"),
    "genus": ("taxonomy.genus", "taxonomy"),
    "taxonRank": ("taxonomy.rank", "taxonomy"),
    "vernacularName": ("taxonomy.vernacular_name", "taxonomy"),
    "decimalLatitude": ("location.latitude", "location"),
    "decimalLongitude": ("location.longitude", "location"),
    "coordinateUncertaintyInMeters": ("measurement.uncertainty", "measurement"),
    "country": ("location.country", "location"),
    "countryCode": ("location.country", "location"),
    "county": ("location.admin_area", "location"),
    "stateProvince": ("location.admin_area", "location"),
    "locality": ("location.locality", "location"),
    "continent": ("location.continent", "location"),
    "elevation": ("location.elevation", "location"),
    "depth": ("location.depth", "location"),
    "minimumElevationInMeters": ("location.elevation", "location"),
    "maximumElevationInMeters": ("location.elevation", "location"),
    "minimumDepthInMeters": ("location.depth", "location"),
    "maximumDepthInMeters": ("location.depth", "location"),
    "eventDate": ("event.date", "time"),
    "year": ("event.year", "time"),
    "month": ("event.date", "time"),
    "day": ("event.date", "time"),
    "basisOfRecord": ("category.basis", "category"),
    "occurrenceStatus": ("category.status", "category"),
    "catalogNumber": ("identifier.record", "identifier"),
    "occurrenceID": ("identifier.record", "identifier"),
    "gbifID": ("identifier.record", "identifier"),
    "recordNumber": ("identifier.record", "identifier"),
    "recordedBy": ("text.observer", "text"),
    "identifiedBy": ("text.observer", "text"),
    "habitat": ("category.habitat", "category"),
    "lifeStage": ("category.life_stage", "category"),
    "sex": ("category.sex", "category"),
    "individualCount": ("statistic.count", "statistic"),
    "organismQuantity": ("statistic.count", "statistic"),
    "waterBody": ("location.locality", "location"),
    "collectionCode": ("identifier.collection", "identifier"),
    "institutionCode": ("identifier.institution", "identifier"),
    "datasetName": ("text.source", "text"),
    "license": ("text.license", "text"),
    "establishmentMeans": ("category.origin", "category"),
    "associatedReferences": ("text.reference", "text"),
}


# ── Data source definitions ──────────────────────────────────────

SOURCES = [
    {
        "name": "guyadiv_trees",
        "path": ROOT / "data/silver/guyane/GUYADIV_trees_v1.csv",
        "labels": GUYADIV_TREES_LABELS,
        "language": "en",
        "sample_rows": 1000,
    },
    {
        "name": "guyadiv_plots",
        "path": ROOT / "data/silver/guyane/GUYADIV_plots_v1.csv",
        "labels": GUYADIV_PLOTS_LABELS,
        "language": "en",
        "sample_rows": None,
    },
    {
        "name": "forestscan_paracou_census",
        "path": ROOT / "data/silver/guyane/paracou/FGPlotsCensusData2023.csv",
        "labels": FORESTSCAN_PARACOU_LABELS,
        "language": "en",
        "sample_rows": 1000,
    },
    {
        "name": "afrique_occ",
        "path": ROOT / "data/silver/afrique/occurrences.csv",
        "labels": AFRIQUE_OCC_LABELS,
        "language": "en",
        "sample_rows": 1000,
    },
    {
        "name": "afrique_plots",
        "path": ROOT / "data/silver/afrique/plots.csv",
        "labels": AFRIQUE_PLOTS_LABELS,
        "language": "en",
        "sample_rows": None,
    },
    {
        "name": "nc_occ",
        "path": ROOT / "data/silver/nc_niamoto/occurrences.csv",
        "labels": NC_OCC_LABELS,
        "language": "en",
        "sample_rows": 1000,
    },
    {
        "name": "nc_plots",
        "path": ROOT / "data/silver/nc_niamoto/plots.csv",
        "labels": NC_PLOTS_LABELS,
        "language": "en",
        "sample_rows": None,
    },
    {
        "name": "nc_full_occ",
        "path": ROOT / "test-instance/niamoto-nc/imports/occurrences.csv",
        "labels": NC_FULL_OCC_LABELS,
        "language": "en",
        "sample_rows": 1000,
    },
    {
        "name": "nc_full_plots",
        "path": ROOT / "test-instance/niamoto-nc/imports/plots.csv",
        "labels": NC_FULL_PLOTS_LABELS,
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
    # ── Silver sources ──
    {
        "name": "ifn_arbre",
        "path": ROOT / "data/silver/ifn_france/ARBRE.csv",
        "labels": IFN_ARBRE_LABELS,
        "language": "fr",
        "sample_rows": 1000,
        "sep": ";",
    },
    {
        "name": "ifn_placette",
        "path": ROOT / "data/silver/ifn_france/PLACETTE.csv",
        "labels": IFN_PLACETTE_LABELS,
        "language": "fr",
        "sample_rows": 1000,
        "sep": ";",
    },
    {
        "name": "ifn_ecologie",
        "path": ROOT / "data/silver/ifn_france/ECOLOGIE.csv",
        "labels": IFN_ECOLOGIE_LABELS,
        "language": "fr",
        "sample_rows": None,
        "sep": ";",
    },
    {
        "name": "ifn_flore",
        "path": ROOT / "data/silver/ifn_france/FLORE.csv",
        "labels": IFN_FLORE_LABELS,
        "language": "fr",
        "sample_rows": 1000,
        "sep": ";",
    },
    {
        "name": "ifn_couvert",
        "path": ROOT / "data/silver/ifn_france/COUVERT.csv",
        "labels": IFN_COUVERT_LABELS,
        "language": "fr",
        "sample_rows": 1000,
        "sep": ";",
    },
    {
        "name": "ifn_bois_mort",
        "path": ROOT / "data/silver/ifn_france/BOIS_MORT.csv",
        "labels": IFN_BOIS_MORT_LABELS,
        "language": "fr",
        "sample_rows": 1000,
        "sep": ";",
    },
    {
        "name": "afliber_species",
        "path": ROOT / "data/silver/afliber_species.csv",
        "labels": AFLIBER_LABELS,
        "language": "en",
        "sample_rows": 1000,
    },
    {
        "name": "ifn_habitat",
        "path": ROOT / "data/silver/ifn_france/HABITAT.csv",
        "labels": IFN_HABITAT_LABELS,
        "language": "fr",
        "sample_rows": None,
        "sep": ";",
    },
    {
        "name": "iefc_catalonia",
        "path": ROOT / "data/silver/iefc_catalonia.csv",
        "labels": IEFC_CATALONIA_LABELS,
        "language": "en",
        "sample_rows": None,
    },
    {
        "name": "fia_tree",
        "path": ROOT / "data/silver/fia_vt_tree.csv",
        "labels": FIA_TREE_LABELS,
        "language": "en",
        "sample_rows": 1000,
    },
    {
        "name": "fia_plot",
        "path": ROOT / "data/silver/fia_vt_plot.csv",
        "labels": FIA_PLOT_LABELS,
        "language": "en",
        "sample_rows": 1000,
    },
    {
        "name": "fia_fl_tree",
        "path": ROOT / "data/silver/fia_fl_tree.csv",
        "labels": FIA_TREE_LABELS,
        "language": "en",
        "sample_rows": 1000,
    },
    {
        "name": "fia_fl_plot",
        "path": ROOT / "data/silver/fia_fl_plot.csv",
        "labels": FIA_PLOT_LABELS,
        "language": "en",
        "sample_rows": 1000,
    },
    {
        "name": "fia_or_tree",
        "path": ROOT / "data/silver/fia_or_tree.csv",
        "labels": FIA_TREE_LABELS,
        "language": "en",
        "sample_rows": 1000,
    },
    {
        "name": "fia_or_plot",
        "path": ROOT / "data/silver/fia_or_plot.csv",
        "labels": FIA_PLOT_LABELS,
        "language": "en",
        "sample_rows": 1000,
    },
    # ── Dryad sources ──
    {
        "name": "berenty_madagascar",
        "path": ROOT / "data/silver/Forest_Data_Berenty_Reserve.csv",
        "labels": BERENTY_LABELS,
        "language": "en",
        "sample_rows": 1000,
    },
    {
        "name": "finland_trees",
        "path": ROOT / "data/silver/finland_sweden/trees_finland_and_sweden.csv",
        "labels": FINLAND_TREES_LABELS,
        "language": "en",
        "sample_rows": 1000,
    },
    {
        "name": "finland_plots",
        "path": ROOT / "data/silver/finland_sweden/plots_finland_and_sweden.csv",
        "labels": FINLAND_PLOTS_LABELS,
        "language": "en",
        "sample_rows": 1000,
    },
    {
        "name": "pasoh_crown",
        "path": ROOT / "data/silver/pasoh/Pasoh_crown_by_ind.txt",
        "labels": PASOH_CROWN_LABELS,
        "language": "en",
        "sample_rows": None,
        "sep": "\t",
    },
    {
        "name": "pasoh_leaf",
        "path": ROOT / "data/silver/pasoh/Pasoh_leaf_traits_by_leaf.txt",
        "labels": PASOH_LEAF_LABELS,
        "language": "en",
        "sample_rows": None,
        "sep": "\t",
    },
    {
        "name": "pasoh_wood",
        "path": ROOT / "data/silver/pasoh/Pasoh_Wood_Density.txt",
        "labels": PASOH_WOOD_LABELS,
        "language": "en",
        "sample_rows": None,
        "sep": "\t",
    },
    # ── GBIF DwC datasets ──
    {
        "name": "gbif_spain_ifn3",
        "path": ROOT / "data/silver/gbif_spain_ifn3.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "es",
        "sample_rows": None,
    },
    {
        "name": "gbif_france_ifn",
        "path": ROOT / "data/silver/gbif_france_ifn.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "fr",
        "sample_rows": None,
    },
    {
        "name": "gbif_sweden_nfi",
        "path": ROOT / "data/silver/gbif_sweden_nfi.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "en",
        "sample_rows": None,
    },
    {
        "name": "gbif_norway_nfi",
        "path": ROOT / "data/silver/gbif_norway_nfi.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "en",
        "sample_rows": None,
    },
    {
        "name": "gbif_benin_lama",
        "path": ROOT / "data/silver/gbif_benin_lama.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "fr",
        "sample_rows": None,
    },
    {
        "name": "gbif_benin_wari_maro",
        "path": ROOT / "data/silver/gbif_benin_wari_maro.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "fr",
        "sample_rows": None,
    },
    {
        "name": "gbif_benin_socioeco",
        "path": ROOT / "data/silver/gbif_benin_socioeco.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "fr",
        "sample_rows": None,
    },
    # ── GBIF DwC datasets — wave 2 (global diversity) ──
    {
        "name": "gbif_tanzania_miombo",
        "path": ROOT / "data/silver/gbif_tanzania_miombo.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "en",
        "sample_rows": None,
    },
    {
        "name": "gbif_madagascar_grasses",
        "path": ROOT / "data/silver/gbif_madagascar_grasses.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "en",
        "sample_rows": None,
    },
    {
        "name": "gbif_uganda_savanna",
        "path": ROOT / "data/silver/gbif_uganda_savanna.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "en",
        "sample_rows": None,
    },
    {
        "name": "gbif_norway_veg",
        "path": ROOT / "data/silver/gbif_norway_veg.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "en",
        "sample_rows": None,
    },
    {
        "name": "gbif_wales_woodland",
        "path": ROOT / "data/silver/gbif_wales_woodland.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "en",
        "sample_rows": None,
    },
    {
        "name": "gbif_poland_botanical",
        "path": ROOT / "data/silver/gbif_poland_botanical.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "en",
        "sample_rows": None,
    },
    {
        "name": "gbif_berlin_botanical",
        "path": ROOT / "data/silver/gbif_berlin_botanical.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "de",
        "sample_rows": None,
    },
    {
        "name": "gbif_us_desert_herb",
        "path": ROOT / "data/silver/gbif_us_desert_herb.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "en",
        "sample_rows": None,
    },
    {
        "name": "gbif_canada_herbarium",
        "path": ROOT / "data/silver/gbif_canada_herbarium.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "en",
        "sample_rows": None,
    },
    {
        "name": "gbif_japan_plants",
        "path": ROOT / "data/silver/gbif_japan_bee_plants.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "en",
        "sample_rows": None,
    },
    {
        "name": "gbif_fr_traits",
        "path": ROOT / "data/silver/gbif_fr_traits.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "fr",
        "sample_rows": None,
    },
    {
        "name": "gbif_ethiopia_kafa",
        "path": ROOT / "data/silver/gbif_ethiopia_kafa.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "en",
        "sample_rows": None,
    },
    # ── GBIF DwC datasets — wave 3 (global gaps) ──
    {
        "name": "gbif_colombia_wetland",
        "path": ROOT / "data/silver/gbif_colombia_wetland.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "es",
        "sample_rows": None,
    },
    {
        "name": "gbif_brazil_forest",
        "path": ROOT / "data/silver/gbif_brazil_forest.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "pt",
        "sample_rows": None,
    },
    {
        "name": "gbif_argentina_protected",
        "path": ROOT / "data/silver/gbif_argentina_protected.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "es",
        "sample_rows": None,
    },
    {
        "name": "gbif_mexico_flora",
        "path": ROOT / "data/silver/gbif_mexico_flora.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "es",
        "sample_rows": None,
    },
    {
        "name": "gbif_paramo_colombia",
        "path": ROOT / "data/silver/gbif_paramo_colombia.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "es",
        "sample_rows": None,
    },
    {
        "name": "gbif_china_herbarium",
        "path": ROOT / "data/silver/gbif_china_herbarium.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "zh",
        "sample_rows": None,
    },
    {
        "name": "gbif_china_south",
        "path": ROOT / "data/silver/gbif_china_south.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "zh",
        "sample_rows": None,
    },
    {
        "name": "gbif_philippines_samar",
        "path": ROOT / "data/silver/gbif_philippines_samar.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "en",
        "sample_rows": None,
    },
    {
        "name": "gbif_india_sundarbans",
        "path": ROOT / "data/silver/gbif_india_sundarbans.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "en",
        "sample_rows": None,
    },
    {
        "name": "gbif_thailand_atlas",
        "path": ROOT / "data/silver/gbif_thailand_atlas.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "en",
        "sample_rows": None,
    },
    {
        "name": "gbif_australia_carnarvon",
        "path": ROOT / "data/silver/gbif_australia_carnarvon.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "en",
        "sample_rows": None,
    },
    {
        "name": "gbif_nz_pdd",
        "path": ROOT / "data/silver/gbif_nz_pdd.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "en",
        "sample_rows": None,
    },
    {
        "name": "gbif_austria_herbarium",
        "path": ROOT / "data/silver/gbif_austria_herbarium.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "de",
        "sample_rows": None,
    },
    {
        "name": "gbif_bulgaria_herbolario",
        "path": ROOT / "data/silver/gbif_bulgaria_herbolario.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "en",
        "sample_rows": None,
    },
    {
        "name": "gbif_kenya_mangrove",
        "path": ROOT / "data/silver/gbif_kenya_mangrove.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "en",
        "sample_rows": None,
    },
    {
        "name": "gbif_targeted_new_caledonia",
        "path": ROOT / "data/silver/gbif_targeted/new_caledonia/occurrences.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "en",
        "sample_rows": 1000,
    },
    {
        "name": "gbif_targeted_guyane",
        "path": ROOT / "data/silver/gbif_targeted/guyane/occurrences.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "en",
        "sample_rows": 1000,
    },
    {
        "name": "gbif_targeted_gabon",
        "path": ROOT / "data/silver/gbif_targeted/gabon/occurrences.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "en",
        "sample_rows": 1000,
    },
    {
        "name": "gbif_targeted_cameroon",
        "path": ROOT / "data/silver/gbif_targeted/cameroon/occurrences.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "en",
        "sample_rows": 1000,
    },
    {
        "name": "gbif_targeted_institutional_gabon",
        "path": ROOT / "data/silver/gbif_targeted_institutional/gabon/occurrences.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "en",
        "sample_rows": 1000,
    },
    {
        "name": "gbif_targeted_institutional_cameroon",
        "path": ROOT
        / "data/silver/gbif_targeted_institutional/cameroon/occurrences.csv",
        "labels": GBIF_DWC_LABELS,
        "language": "en",
        "sample_rows": 1000,
    },
    # ── Zenodo datasets (unique schemas) ──
    {
        "name": "zenodo_bci_allometry",
        "path": ROOT / "data/silver/zenodo_bci_allometry.csv",
        "labels": {
            "Mnemonic": ("taxonomy.species", "taxonomy"),
            "SpeciesName": ("taxonomy.species", "taxonomy"),
            "Site": ("location.locality", "location"),
            "Date": ("event.date", "time"),
            "Tag": ("identifier.record", "identifier"),
            "HeightOfMeasurement": ("measurement.height", "measurement"),
            "Diameter": ("measurement.diameter", "measurement"),
            "Height": ("measurement.height", "measurement"),
            "CrownArea": ("measurement.crown", "measurement"),
        },
        "language": "en",
        "sample_rows": None,
    },
    {
        "name": "zenodo_bci_traits",
        "path": ROOT / "data/silver/zenodo_bci_traits.csv",
        "labels": {
            "Mnemonic": ("taxonomy.species", "taxonomy"),
            "SpeciesName": ("taxonomy.species", "taxonomy"),
            "SG100C_AVG": ("measurement.wood_density", "measurement"),
        },
        "language": "en",
        "sample_rows": None,
    },
    {
        "name": "zenodo_california_ferp",
        "path": ROOT / "data/silver/zenodo_california_ferp.csv",
        "labels": {
            "quadrat": ("identifier.plot", "identifier"),
            "tag": ("identifier.record", "identifier"),
            "stemtag": ("identifier.record", "identifier"),
            "code6": ("taxonomy.species", "taxonomy"),
            "east_m": ("location.x_coord", "location"),
            "north_m": ("location.y_coord", "location"),
            "east_UTM": ("location.x_coord", "location"),
            "north_UTM": ("location.y_coord", "location"),
            "dsh1_mm": ("measurement.diameter", "measurement"),
            "dsh2_mm": ("measurement.diameter", "measurement"),
            "dsh3_mm": ("measurement.diameter", "measurement"),
            "date1": ("event.date", "time"),
            "date2": ("event.date", "time"),
            "date3": ("event.date", "time"),
        },
        "language": "en",
        "sample_rows": 1000,
    },
    {
        "name": "zenodo_china_census",
        "path": ROOT / "data/silver/zenodo_china_census.csv",
        "labels": {
            "Qudrat": ("identifier.plot", "identifier"),
            "latin": ("taxonomy.species", "taxonomy"),
            "lifeform": ("category.growth_form", "category"),
            "gx": ("location.x_coord", "location"),
            "gy": ("location.y_coord", "location"),
            "status1": ("category.status", "category"),
            "status2": ("category.status", "category"),
            "dbh1": ("measurement.diameter", "measurement"),
            "dbh2": ("measurement.diameter", "measurement"),
            "H": ("measurement.height", "measurement"),
        },
        "language": "en",
        "sample_rows": 1000,
    },
    {
        "name": "zenodo_china_soil",
        "path": ROOT / "data/silver/zenodo_china_soil.csv",
        "labels": {
            "GX": ("location.x_coord", "location"),
            "GY": ("location.y_coord", "location"),
            "pH": ("environment.ph", "environment"),
            "SOM": ("measurement.soil_organic", "measurement"),
        },
        "language": "en",
        "sample_rows": None,
    },
    {
        "name": "zenodo_forest_inventory_pub",
        "path": ROOT / "data/silver/zenodo_forest_inventory_pub.csv",
        "labels": {
            "ID": ("identifier.record", "identifier"),
            "Plot_ID": ("identifier.plot", "identifier"),
            "Forest_type": ("category.forest_type", "category"),
            "Date": ("event.date", "time"),
            "Village": ("location.locality", "location"),
            "Commune": ("location.admin_area", "location"),
            "District": ("location.admin_area", "location"),
            "Province": ("location.admin_area", "location"),
            "Species": ("taxonomy.species", "taxonomy"),
            "DBH": ("measurement.diameter", "measurement"),
            "Bole_height": ("measurement.height", "measurement"),
        },
        "language": "en",
        "sample_rows": 1000,
        "sep": "\t",
    },
    {
        "name": "zenodo_leaf_traits",
        "path": ROOT / "data/silver/zenodo_leaf_traits.csv",
        "labels": {
            "Species": ("taxonomy.species", "taxonomy"),
            "Spad_mean": ("measurement.chlorophyll", "measurement"),
            "Dry_wght_mean": ("measurement.biomass", "measurement"),
            "Leaf_lenght_mean": ("measurement.leaf_area", "measurement"),
            "Leaf_area_mean": ("measurement.leaf_area", "measurement"),
        },
        "language": "en",
        "sample_rows": None,
        "sep": "\t",
    },
    {
        "name": "zenodo_savanna_roots",
        "path": ROOT / "data/silver/zenodo_savanna_roots.csv",
        "labels": {
            "Species": ("taxonomy.species", "taxonomy"),
            "Functional_Type": ("category.growth_form", "category"),
            "RGR": ("measurement.growth_rate", "measurement"),
            "Dmax": ("measurement.diameter", "measurement"),
            "SRL": ("measurement.root_trait", "measurement"),
            "RD": ("measurement.root_trait", "measurement"),
        },
        "language": "en",
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
    # Biomes ajoutés pour couvrir les concepts sous-représentés
    "forest_with_traits": {
        "measurement.diameter": {
            "dist": "lognormal",
            "mean": 3.0,
            "sigma": 0.8,
            "clip": (5, 200),
        },
        "measurement.height": {"dist": "normal", "mean": 15, "std": 6, "clip": (2, 40)},
        "measurement.biomass": {
            "dist": "lognormal",
            "mean": 2.5,
            "sigma": 1.0,
            "clip": (0.1, 500),
        },
        "measurement.wood_density": {
            "dist": "normal",
            "mean": 0.55,
            "std": 0.15,
            "clip": (0.15, 1.2),
        },
        "measurement.leaf_area": {
            "dist": "lognormal",
            "mean": 2.0,
            "sigma": 1.0,
            "clip": (1, 500),
        },
        "measurement.canopy": {
            "dist": "normal",
            "mean": 6,
            "std": 3,
            "clip": (0.5, 25),
        },
        "measurement.growth": {
            "dist": "normal",
            "mean": 2,
            "std": 1.5,
            "clip": (0, 15),
        },
    },
    "terrain_soil": {
        "measurement.terrain": {"dist": "uniform", "low": 0, "high": 45},
        "measurement.soil": {"dist": "normal", "mean": 3, "std": 2, "clip": (0, 20)},
        "measurement.dimension": {"dist": "uniform", "low": 0.01, "high": 10},
        "environment.temperature": {
            "dist": "normal",
            "mean": 15,
            "std": 10,
            "clip": (-30, 45),
        },
        "environment.precipitation": {
            "dist": "lognormal",
            "mean": 6.5,
            "sigma": 0.8,
            "clip": (50, 5000),
        },
        "environment.water": {"dist": "normal", "mean": 7.0, "std": 1, "clip": (3, 9)},
    },
}

HEADER_VARIANTS = {
    "en": {
        "measurement.diameter": [
            "dbh",
            "diameter",
            "trunk_diameter",
            "stem_diam",
            "girth",
            "circumference",
        ],
        "measurement.height": [
            "height",
            "tree_height",
            "h_tot",
            "canopy_height",
            "total_height",
        ],
        "measurement.biomass": ["biomass", "agb", "dry_weight", "carbon_ag", "drybio"],
        "measurement.wood_density": ["wood_density", "specific_gravity", "wd", "sg"],
        "measurement.leaf_area": ["leaf_area", "sla", "lma", "leaf_surface", "lai"],
        "measurement.cover": ["cover", "cover_pct", "canopy_cover", "crown_cover"],
        "measurement.canopy": ["crown_diameter", "crown_area", "crown_ratio", "cr"],
        "measurement.growth": [
            "increment",
            "growth_rate",
            "rgr",
            "annual_growth",
            "age",
        ],
        "measurement.terrain": ["slope", "aspect", "slope_deg", "slope_pct"],
        "measurement.dimension": ["length", "area", "plot_area", "width"],
        "measurement.uncertainty": ["uncertainty", "precision", "error", "accuracy"],
        "measurement.trait": [
            "srl",
            "root_length",
            "leaf_thickness",
            "ldmc",
            "chlorophyll",
        ],
        "measurement.soil": ["som", "organic_matter", "soil_carbon", "soil_nitrogen"],
        "location.elevation": ["elevation", "altitude", "elev", "alt", "height_asl"],
        "location.depth": ["depth", "water_depth", "min_depth", "max_depth"],
        "location.latitude": ["latitude", "lat", "decimal_latitude", "y"],
        "location.longitude": ["longitude", "lon", "decimal_longitude", "x"],
        "location.coordinate": [
            "x_coord",
            "y_coord",
            "easting",
            "northing",
            "utm_x",
            "utm_y",
        ],
        "location.locality": ["locality", "site", "station", "plot_name", "location"],
        "location.country": ["country", "country_code", "nation"],
        "location.admin_area": [
            "state",
            "province",
            "county",
            "district",
            "region",
            "department",
        ],
        "location.continent": ["continent"],
        "environment.temperature": [
            "temperature",
            "temp",
            "air_temp",
            "water_temp",
            "sst",
        ],
        "environment.precipitation": ["precipitation", "rainfall", "rain", "precip"],
        "environment.water": ["salinity", "sal", "ph", "water_ph", "conductivity"],
        "taxonomy.species": ["species", "scientific_name", "taxon", "accepted_name"],
        "taxonomy.family": ["family", "plant_family", "taxon_family"],
        "taxonomy.genus": ["genus", "plant_genus"],
        "taxonomy.rank": ["rank", "taxon_rank", "taxonomic_rank"],
        "taxonomy.name": ["common_name", "vernacular_name", "local_name"],
        "taxonomy.kingdom": ["kingdom"],
        "taxonomy.phylum": ["phylum", "division"],
        "taxonomy.class": ["class", "taxon_class"],
        "taxonomy.order": ["order", "taxon_order"],
        "statistic.count": [
            "count",
            "abundance",
            "n_individuals",
            "frequency",
            "total",
        ],
        "event.date": ["date", "event_date", "collection_date", "observation_date"],
        "event.year": ["year", "obs_year", "survey_year", "campaign"],
        "identifier.record": ["id", "record_id", "sample_id", "tag", "tree_id"],
        "identifier.plot": ["plot_id", "site_id", "quadrat", "subplot", "transect_id"],
        "identifier.collection": ["collection_code", "herbarium", "collection"],
        "identifier.institution": ["institution", "institution_code", "museum"],
        "category.status": ["status", "tree_status", "occurrence_status"],
        "category.basis": ["basis_of_record", "record_type", "observation_type"],
        "category.habitat": ["habitat", "vegetation_type", "ecosystem", "biome"],
        "category.vegetation": ["forest_type", "stand_type", "stratum", "layer"],
        "category.tree_condition": [
            "condition",
            "health",
            "damage",
            "mortality",
            "decay",
        ],
        "category.management": ["management", "treatment", "silviculture", "land_use"],
        "category.ecology": [
            "phenology",
            "life_stage",
            "succession",
            "endemism",
            "origin",
        ],
        "category.growth_form": [
            "growth_form",
            "life_form",
            "habit",
            "functional_type",
        ],
        "category.soil": ["soil_type", "texture", "humus", "rock_type", "lithology"],
        "category.light": ["light", "exposure", "shade", "canopy_openness"],
        "category.quality": ["quality", "reliability", "confidence", "flag"],
        "text.observer": ["recorded_by", "collector", "observer", "identified_by"],
        "text.source": ["source", "dataset", "reference", "data_provider"],
        "text.metadata": ["notes", "remarks", "comments", "license", "authority"],
    },
    "fr": {
        "measurement.diameter": ["diametre", "diam", "dhp", "circonference"],
        "measurement.height": ["hauteur", "haut", "hauteur_arbre", "h_tot"],
        "measurement.biomass": ["biomasse", "poids_sec", "carbone"],
        "measurement.wood_density": ["densite_bois", "densite"],
        "measurement.leaf_area": ["surface_foliaire", "sla"],
        "measurement.cover": ["couverture", "recouvrement", "taux_couverture"],
        "measurement.canopy": ["diametre_houppier", "rayon_houppier"],
        "measurement.growth": ["accroissement", "age", "croissance"],
        "measurement.terrain": ["pente", "exposition", "orientation"],
        "location.elevation": ["altitude", "alt", "elevation"],
        "location.depth": ["profondeur", "prof"],
        "location.latitude": ["latitude", "lat"],
        "location.longitude": ["longitude", "lon"],
        "location.locality": ["localite", "lieu", "site", "parcelle", "station"],
        "location.country": ["pays", "code_pays"],
        "location.admin_area": [
            "departement",
            "region",
            "commune",
            "district",
            "province",
        ],
        "environment.temperature": ["temperature", "temp"],
        "environment.precipitation": ["precipitation", "pluie", "pluviometrie"],
        "taxonomy.species": ["espece", "nom_scientifique", "taxon"],
        "taxonomy.family": ["famille", "nom_famille"],
        "taxonomy.genus": ["genre"],
        "taxonomy.name": ["nom_commun", "nom_vernaculaire"],
        "statistic.count": ["nombre", "abondance", "effectif", "frequence"],
        "event.date": ["date", "date_collecte", "date_observation"],
        "event.year": ["annee", "campagne"],
        "identifier.record": ["id", "identifiant", "numero", "etiquette"],
        "identifier.plot": ["id_parcelle", "id_site", "id_placette"],
        "category.status": ["statut", "etat"],
        "category.habitat": ["habitat", "milieu", "ecosysteme"],
        "category.vegetation": ["type_foret", "strate", "formation"],
        "category.soil": ["type_sol", "texture", "humus", "roche"],
        "text.observer": ["observateur", "collecteur", "determinateur"],
    },
    "es": {
        "measurement.diameter": ["diametro", "dap", "circunferencia"],
        "measurement.height": ["altura", "alto", "altura_total"],
        "measurement.biomass": ["biomasa", "peso_seco"],
        "location.elevation": ["altitud", "elevacion"],
        "location.latitude": ["latitud", "lat"],
        "location.longitude": ["longitud", "lon"],
        "location.locality": ["localidad", "sitio", "parcela"],
        "location.country": ["pais", "codigo_pais"],
        "location.admin_area": ["estado", "provincia", "municipio", "departamento"],
        "taxonomy.species": ["especie", "nombre_cientifico"],
        "taxonomy.family": ["familia"],
        "taxonomy.genus": ["genero"],
        "taxonomy.name": ["nombre_comun", "nombre_vernacular"],
        "statistic.count": ["numero", "abundancia", "conteo"],
        "event.date": ["fecha", "fecha_colecta", "fecha_observacion"],
        "event.year": ["anio", "ano"],
        "identifier.record": ["id", "identificador", "numero_registro"],
        "identifier.plot": ["id_parcela", "id_sitio"],
        "category.habitat": ["habitat", "ecosistema", "bioma"],
    },
    "pt": {
        "measurement.diameter": ["diametro", "dap"],
        "measurement.height": ["altura", "alt_total"],
        "location.elevation": ["altitude", "elevacao"],
        "location.latitude": ["latitude", "lat"],
        "location.longitude": ["longitude", "lon"],
        "taxonomy.species": ["especie", "nome_cientifico"],
        "taxonomy.family": ["familia"],
        "statistic.count": ["numero", "abundancia", "contagem"],
        "event.date": ["data", "data_coleta"],
        "identifier.record": ["id", "identificador"],
        "location.locality": ["localidade", "local", "parcela"],
    },
    "de": {
        "measurement.diameter": ["durchmesser", "bhd"],
        "measurement.height": ["hoehe", "baumhoehe"],
        "location.elevation": ["hoehe_ueber_nn", "seehöhe"],
        "location.latitude": ["breitengrad", "lat"],
        "location.longitude": ["laengengrad", "lon"],
        "taxonomy.species": ["art", "wissenschaftlicher_name"],
        "taxonomy.family": ["familie"],
        "event.date": ["datum", "sammeldatum"],
        "identifier.record": ["id", "nummer"],
        "location.locality": ["standort", "lokalitaet"],
    },
    "id": {
        "measurement.diameter": ["diameter", "dbh"],
        "measurement.height": ["tinggi", "tinggi_pohon"],
        "location.elevation": ["ketinggian", "elevasi"],
        "taxonomy.species": ["spesies", "nama_ilmiah"],
        "taxonomy.family": ["famili"],
        "location.latitude": ["lintang", "lat"],
        "location.longitude": ["bujur", "lon"],
        "identifier.record": ["id", "nomor"],
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
                            "language": lang,
                            "is_anonymous": False,
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
                        "language": lang,
                        "is_anonymous": False,
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
                    "language": lang,
                    "is_anonymous": False,
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
                        "language": lang,
                        "is_anonymous": False,
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
                    "language": lang,
                    "is_anonymous": False,
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
                    "language": lang,
                    "is_anonymous": False,
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


# ── Anonymous holdout ────────────────────────────────────────────

_ANONYMOUS_NAME_POOL = (
    [f"col_{i}" for i in range(1, 100)]
    + [f"X{i}" for i in range(1, 100)]
    + [f"V{i}" for i in range(1, 100)]
    + [f"var_{chr(c)}" for c in range(ord("a"), ord("z") + 1)]
    + [f"field_{i}" for i in range(1, 26)]
)


def _build_anonymous_holdout(
    records: list[dict],
    target_total: int = 100,
    min_per_concept: int = 2,
    seed: int = 42,
) -> list[dict]:
    """Build a diversified anonymous holdout from real gold set columns.

    Samples real columns stratified by concept_coarse and duplicates them
    with generic column names to test values-only detection.
    """
    rng = np.random.RandomState(seed)

    # Only sample from non-anonymous entries
    candidates = [r for r in records if not r.get("is_anonymous")]
    if not candidates:
        logger.warning("No non-anonymous records to build holdout from")
        return []

    # Group by concept_coarse
    from collections import defaultdict

    groups: dict[str, list[dict]] = defaultdict(list)
    for r in candidates:
        groups[r["concept_coarse"]].append(r)

    # Calculate samples per group: proportional with a floor
    total_candidates = len(candidates)
    samples_per_group: dict[str, int] = {}
    for concept, group in groups.items():
        proportional = max(
            min_per_concept,
            round(target_total * len(group) / total_candidates),
        )
        samples_per_group[concept] = min(proportional, len(group))

    # Adjust to get close to target_total
    current_total = sum(samples_per_group.values())
    if current_total > target_total:
        # Trim proportionally from largest groups
        excess = current_total - target_total
        sorted_concepts = sorted(
            samples_per_group, key=lambda c: samples_per_group[c], reverse=True
        )
        for concept in sorted_concepts:
            if excess <= 0:
                break
            can_trim = samples_per_group[concept] - min_per_concept
            trim = min(can_trim, excess)
            if trim > 0:
                samples_per_group[concept] -= trim
                excess -= trim

    # Sample and anonymize
    available_names = list(_ANONYMOUS_NAME_POOL)
    rng.shuffle(available_names)
    name_idx = 0
    holdout = []

    for concept in sorted(groups.keys()):
        group = groups[concept]
        n = samples_per_group[concept]
        indices = rng.choice(len(group), size=n, replace=False)
        for idx in indices:
            entry = copy.deepcopy(group[idx])
            entry["column_name"] = available_names[name_idx]
            entry["is_anonymous"] = True
            entry["quality"] = "gold_anonymous"
            entry["language"] = "en"
            name_idx += 1
            holdout.append(entry)

    logger.info(
        f"Built anonymous holdout: {len(holdout)} entries "
        f"across {len(samples_per_group)} concepts"
    )
    return holdout


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

    # Add coarsened concept to each record
    from scripts.ml.concept_taxonomy import coarsen

    for r in all_records:
        r["concept_coarse"] = coarsen(r["concept"])
        r["role_coarse"] = (
            r["concept_coarse"].split(".")[0]
            if "." in r["concept_coarse"]
            else r["concept_coarse"]
        )

    # Build diversified anonymous holdout from real columns
    anon_holdout = _build_anonymous_holdout(all_records)
    all_records.extend(anon_holdout)

    # Summary
    gold = [r for r in all_records if r["quality"] == "gold"]
    synthetic_count = [r for r in all_records if r["quality"] == "synthetic"]
    anon_count = [r for r in all_records if r.get("is_anonymous")]

    logger.info(f"\n{'=' * 50}")
    logger.info(f"Gold set built: {len(all_records)} total columns")
    logger.info(f"  Gold:      {len(gold)}")
    logger.info(f"  Synthetic: {len(synthetic_count)}")
    logger.info(f"  Anonymous: {len(anon_count)}")

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
