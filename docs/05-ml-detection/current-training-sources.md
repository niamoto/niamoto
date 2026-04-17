# Current Training Sources

> Status: Active
> Audience: Team, AI agents
> Purpose: Reference list of the datasets currently wired into
> `ml/scripts/data/build_gold_set.py`

This document lists the sources that are **actually used by the code** when the
gold set is rebuilt.

Source of truth:

- `ml/scripts/data/build_gold_set.py`

If this document and the code disagree, the code wins.

## How to read this page

Each source below is currently registered in `SOURCES` in
`build_gold_set.py`. Some sources are active training sources, while a small
subset is explicitly excluded from training by name.

## Explicitly excluded from training

These sources are still known to the codebase but currently excluded from
training:

- `fia_or_tree`
- `fia_or_plot`

## Current source families

### Product and instance-close datasets

- `guyadiv_trees`
- `guyadiv_plots`
- `forestscan_paracou_census`
- `afrique_occ`
- `afrique_plots`
- `nc_occ`
- `nc_plots`
- `nc_full_occ`
- `nc_full_plots`

### Test and fixture datasets used by the build pipeline

- `gbif_marine`
- `gbif_terrestrial`
- `custom_forest`
- `checklist`
- `minimal`
- `adversarial`

### IFN France

- `ifn_arbre`
- `ifn_placette`
- `ifn_ecologie`
- `ifn_flore`
- `ifn_couvert`
- `ifn_bois_mort`
- `ifn_habitat`

### Standards-based acquisitions

- `taxref_v18`
- `ets_occurrence_ext`
- `ets_taxon_ext`
- `ets_measurement_ext`
- `splot_header`
- `splot_dt`
- `splot_cwm`
- `splot_metadata`

### FIA and inventory-style sources

- `fia_tree`
- `fia_plot`
- `fia_fl_tree`
- `fia_fl_plot`
- `fia_or_tree` (excluded from training)
- `fia_or_plot` (excluded from training)
- `finland_trees`
- `finland_plots`
- `iefc_catalonia`
- `berenty_madagascar`
- `afliber_species`

### Pasoh and research-field datasets

- `pasoh_crown`
- `pasoh_leaf`
- `pasoh_wood`

### Broad GBIF corpus

- `gbif_spain_ifn3`
- `gbif_france_ifn`
- `gbif_sweden_nfi`
- `gbif_norway_nfi`
- `gbif_benin_lama`
- `gbif_benin_wari_maro`
- `gbif_benin_socioeco`
- `gbif_tanzania_miombo`
- `gbif_madagascar_grasses`
- `gbif_uganda_savanna`
- `gbif_norway_veg`
- `gbif_wales_woodland`
- `gbif_poland_botanical`
- `gbif_berlin_botanical`
- `gbif_us_desert_herb`
- `gbif_canada_herbarium`
- `gbif_japan_plants`
- `gbif_fr_traits`
- `gbif_ethiopia_kafa`
- `gbif_colombia_wetland`
- `gbif_brazil_forest`
- `gbif_argentina_protected`
- `gbif_mexico_flora`
- `gbif_paramo_colombia`
- `gbif_china_herbarium`
- `gbif_china_south`
- `gbif_philippines_samar`
- `gbif_india_sundarbans`
- `gbif_thailand_atlas`
- `gbif_australia_carnarvon`
- `gbif_nz_pdd`
- `gbif_austria_herbarium`
- `gbif_bulgaria_herbolario`
- `gbif_kenya_mangrove`

### Targeted regional and institutional GBIF batches

- `gbif_targeted_new_caledonia`
- `gbif_targeted_guyane`
- `gbif_targeted_gabon`
- `gbif_targeted_cameroon`
- `gbif_targeted_institutional_gabon`
- `gbif_targeted_institutional_cameroon`

### Zenodo and research-oriented datasets

- `zenodo_bci_allometry`
- `zenodo_bci_traits`
- `zenodo_california_ferp`
- `zenodo_china_census`
- `zenodo_china_soil`
- `zenodo_forest_inventory_pub`
- `zenodo_leaf_traits`
- `zenodo_savanna_roots`

## Notes

- This page is intentionally grouped by source family, not by exact file path.
- The exact paths, labels, and sampling rules remain in `build_gold_set.py`.
- If a new source is integrated in code, update this page in the same change.
