# Candidate Data Sources for Strengthening the ML Benchmark

## Purpose

This document lists data sources that could strengthen the benchmark and
training set for Niamoto's ML detection.

The goal is not to accumulate data "at random". The goal is to broaden the
benchmark with data that resembles the cases Niamoto must actually serve well:

- tropical or subtropical inventories and surveys;
- semi-standard or non-standardised datasets;
- real ecological tabular exports;
- GBIF datasets, particularly in their standard core and useful extensions;
- data from actually tested instances.

## What We Are Looking for First

The most useful sources for ML detection are those that provide:

- **real field headers**;
- **non-trivial** columns;
- **tabular** formats (CSV, TSV, DWC-A, portal exports);
- **business** or **local** vocabularies;
- realistic values;
- a diversity of conventions without falling into schemas that are too exotic
  or too distant from the product.

On the other hand, purely cartographic derived datasets, rasters, or products
that are already heavily aggregated are generally of low value for the column
detection benchmark.

## Selection Strategy

I recommend classifying sources into three groups:

### Priority A — Very Close to the Product Target

To integrate first:

- real tropical forest datasets;
- surveys from Guyane, Gabon, Cameroon, New Caledonia if available;
- data from actually tested instances;
- GBIF exports targeted by region and style.

### Priority B — Very Useful Neighbours

To integrate next:

- large tropical forest networks;
- vegetation plot networks;
- African and pan-tropical databases with occurrence or plot data.

### Priority C — Controlled Expansion

Useful for robustness, but secondary:

- plant trait datasets;
- marine / coastal if it becomes a real need;
- regions that are ecologically more distant but still compatible with the
  product.

## Recommended Shortlist

## 1. Local and Real Instance Data

### 1. Datasets from Currently Tested Instances

- **Type**: real tabular exports, potentially non-standardised
- **Access**: internal
- **ML Value**: maximum
- **Why**: these are the cases closest to the product, with real column
  conventions, real quality issues, and real user expectations
- **Priority**: A+

Recommendation:

- integrate them explicitly into the gold set where possible;
- tag them as the main sub-benchmark;
- track results separately per instance.

## 2. Guyane / French Amazonia

### 2. Paracou / ForestScan (CIRAD Dataverse)

- **Region**: French Guyane
- **Type**: tree census data, forest structure, tropical plots
- **Access**: open data via Dataverse
- **Expected format**: CSV + metadata
- **Why**: very close to tropical field needs; excellent candidate for
  enriching the non-standard tropical part of the benchmark
- **Priority**: A
- **Sources**:
  - [Paracou Dataverse](https://dataverse.cirad.fr/dataverse/paracou)
  - [ForestScan data paper (ESSD 2026)](https://essd.copernicus.org/articles/18/1243/2026/essd-18-1243-2026.html)

### 3. Guyafor network — Trinité

- **Region**: French Guyane
- **Type**: forest censuses
- **Access**: public metadata and description; main census CSV restricted,
  access on request
- **Why**: useful for varying plot conventions and tropical variables while
  staying in an ecosystem close to Paracou
- **Priority**: A
- **Source**:
  - [Guyafor / Trinite Forest Censuses](https://dataverse.cirad.fr/dataverse/guyafor)

### 4. Guyafor network — Trésor

- **Region**: French Guyane
- **Type**: tree census in permanent forest plots
- **Access**: public metadata and description; main census CSV restricted,
  access on request
- **Why**: complements Paracou/Trinité with another tropical Guyane forest
  context
- **Priority**: A
- **Source**:
  - [Tresor Forest Censuses (Guyafor)](https://dataverse.cirad.fr/dataverse/ecofog)

## 3. Central and Tropical Africa

### 5. ForestPlots.net — Lopé, Gabon

- **Region**: Gabon
- **Type**: tree census tropical forest plots
- **Access**: supervised access, request/collaboration
- **Why**: very close to the product target; useful for plot, tree, biomass,
  diameter, mortality columns, etc.
- **Priority**: A
- **Sources**:
  - [ForestPlots.net - Working with data](https://forestplots.net/en/join-forestplots/working-with-data)
  - [ForestScan data paper (Lopé section)](https://essd.copernicus.org/articles/18/1243/2026/essd-18-1243-2026.html)

### 6. RAINBIO

- **Region**: Tropical Africa, including Gabon/Cameroon
- **Type**: vascular plant occurrences in tropical Africa
- **Access**: published database; publicly documented access
- **Why**: excellent candidate for strengthening tropical Africa coverage,
  particularly for enriching taxonomy, locality, habitat, and associated
  fields
- **Priority**: A
- **Sources**:
  - [RAINBIO data paper via GBIF](https://www.gbif.org/en/data-use/83286)
  - [RAINBIO official site](https://gdauby.github.io/rainbio/)

### 7. SEOSAW plot network

- **Region**: Sub-Saharan Africa
- **Type**: tree and stem measurements in woodland / savanna plots
- **Access**: access on request; sample available
- **Why**: useful if you want to expand beyond dense tropical forest while
  staying on vegetation/woodland field data
- **Priority**: B
- **Source**:
  - [SEOSAW data access](https://seosaw.github.io/data)

## 4. GBIF Targeted by Region and Style

### 8. GBIF regional occurrence downloads

- **Region**: New Caledonia, Guyane, Gabon, Cameroon, then other regions
- **Type**: Darwin Core standardised occurrences
- **Access**: via portal + API + snapshots
- **Why**: GBIF remains a product priority, but it must be treated as
  several sub-corpora:
  - standard core (`gbif_core_standard`)
  - extended columns (`gbif_extended`)
  - priority regional selections
- **Priority**: A
- **Sources**:
  - [GBIF API Downloads](https://techdocs.gbif.org/en/data-use/api-downloads)
  - [GBIF download formats](https://techdocs.gbif.org/en/data-use/download-formats)
  - [GBIF open data on AWS](https://registry.opendata.aws/gbif/)

Current state:

- a first `gbif_targeted/` batch was retrieved for `NC`, `GF`, `GA`, `CM`
- this batch is useful but remains highly observational
- it must not be confused with institutional GBIF

### 9. GBIF — Targeted New Caledonia

- **Region**: New Caledonia
- **Type**: regional GBIF occurrences
- **Access**: via targeted GBIF queries
- **Why**: allows adding a mass of standardised data close to the geographic
  priority, even if it does not replace non-standard field datasets
- **Priority**: A
- **Indicative source**:
  - [GBIF country report New Caledonia](https://analytics-files.gbif.org/country/NC/GBIF_CountryReport_NC.pdf)

### 10. GBIF — French Overseas Territories

- **Region**: French Guyane, New Caledonia, other overseas territories
- **Type**: multi-country/territory occurrence downloads
- **Access**: via GBIF download queries
- **Why**: useful for building targeted sub-corpora by territory and testing
  pipeline robustness on areas of interest
- **Priority**: B
- **GBIF download example**:
  - [Example occurrence download with French overseas territories](https://www.gbif.org/occurrence/download/0025173-250802193616735)

### 10bis. Institutional Targeted GBIF

- **Region**: Gabon and Cameroon as a priority at this stage
- **Type**: GBIF occurrences closer to collections and herbaria
- **Access**: via public API + local filtering
- **Why**: complements the general regional batch with a signal closer to
  real institutional exports
- **Recommended filter**:
  - `basisOfRecord in {PRESERVED_SPECIMEN, MATERIAL_SAMPLE, OCCURRENCE}`
  - presence of at least one institutional field (`institutionCode`,
    `collectionCode`, `institutionID`, `collectionKey`)
  - exclusion of large observational datasets (`iNaturalist`, `observation.org`,
    `Pl@ntNet`, etc.)
- **Current state**:
  - `gabon`: good yield
  - `cameroon`: good yield
  - `new_caledonia`: very low yield in first results
  - `guyane`: very low yield in first results

## 5. Broader Forest and Vegetation Networks

### 11. ForestGEO Data Portal

- **Region**: global network of forest plots
- **Type**: forest plots, standardised inventories
- **Access**: request portal; data sometimes public, sometimes on approval
- **Why**: very high value for enriching the benchmark with comparable
  forest inventories across regions
- **Priority**: B
- **Source**:
  - [ForestGEO Data Portal](https://ctfs.si.edu/datarequest/)

### 12. sPlotOpen

- **Region**: global
- **Type**: vegetation plots, species co-occurrence, plot metadata
- **Access**: open access
- **Why**: good source for broadening the benchmark with vegetation plots and
  environmental metadata, useful if Niamoto needs to serve more than raw
  occurrences
- **Priority**: B
- **Source**:
  - [sPlotOpen](https://www.idiv.de/research/projects/splot/splotopen-splot/)

### 13. AusPlots / TERN

- **Region**: Australia
- **Type**: vegetation plots / rangelands / survey protocols
- **Access**: open data / TERN portal depending on dataset
- **Why**: less close to priority regions, but very useful for testing
  structured vegetation surveys outside humid tropics
- **Priority**: C
- **Source**:
  - [TERN / AusPlots context](https://www.tern.org.au/auscribe-ausplots-field-survey-app/)

## 6. Trait Data and Semantic Enrichment

### 14. TRY Plant Trait Database

- **Region**: global
- **Type**: plant traits
- **Access**: dedicated portal, now very open on a large portion of data
- **Why**: less useful for the raw column detection benchmark than for
  enriching concepts and affordances around traits
- **Priority**: B/C
- **Sources**:
  - [TRY Home](https://www.try-db.org/TryWeb/Home.php)
  - [TRY data portal](https://www.try-db.org/TryWeb/Database.php)
  - [TRY access / openness](https://www.try-db.org/TryWeb/About.php)

## 7. Marine / Coastal if Future Need

### 15. OBIS

- **Region**: global, including New Caledonia
- **Type**: marine occurrences, sometimes eDNA, eMoF extensions
- **Access**: open access, full exports and API
- **Why**: relevant if the product must also handle coastal, lagoon, or
  marine/reef datasets from New Caledonia
- **Priority**: B/C depending on need
- **Sources**:
  - [OBIS data access](https://obis.org/data/access)
  - [OBIS manual / downloads](https://manual.obis.org/access)
  - [New Caledonia eDNA example dataset](https://obis.org/dataset/33926ad1-6fb9-4299-ad94-1ce5c23773d3)

## Prioritisation Recommendation

## Batch 1 — To Do First

- data from actually tested instances
- Paracou / Guyafor (Guyane)
- Trinité / Trésor (Guyane)
- targeted GBIF New Caledonia / Guyane / Gabon / Cameroon
- ForestPlots Lopé (if access is possible)
- RAINBIO

## Batch 2 — To Do Right After

- regional GBIF split `core_standard` / `extended`
- ForestGEO
- SEOSAW
- sPlotOpen

## Batch 3 — To Integrate Only If Useful

- TRY
- OBIS
- AusPlots

## How to Use Them in the Benchmark

I recommend not mixing everything into a single score.

### Main Benchmark

Must reflect the product target:

- tested instance datasets
- tropical data close to actual usage
- Guyane / Tropical Africa / New Caledonia
- targeted GBIF

### Guardrails

To monitor without giving them the full weight of the main score:

- heavily coded forest inventories
- rare or small sub-benchmarks
- regions distant from the product core

### Diagnostics

To use for understanding, not for deciding alone:

- highly standardised datasets
- small homogeneous splits
- highly specialised corpora

## Selection Criteria Before Integration

Before integrating a new source, verify:

- is the format tabular and quickly exploitable?
- do the headers bring genuine variation?
- are the values realistic and sufficiently clean?
- does the licence allow use in the local benchmark?
- is the dataset close to the product target or merely "interesting"?

## Recommended Decision

If we want to be efficient, we must start with sources that genuinely change
the benchmark quality on the product target.

My clear recommendation:

1. **Formalise real instance datasets**
2. **Add open tropical Guyane (Paracou / Guyafor)**
3. **Add tropical Africa close to usage (RAINBIO + ForestPlots if possible)**
4. **Build targeted GBIF downloads by region**
5. **Expand only after that**

## References

- [Paracou Dataverse](https://dataverse.cirad.fr/dataverse/paracou)
- [ForestScan ESSD 2026](https://essd.copernicus.org/articles/18/1243/2026/essd-18-1243-2026.html)
- [Guyafor Dataverse](https://dataverse.cirad.fr/dataverse/guyafor)
- [ForestPlots.net](https://forestplots.net/en/join-forestplots/working-with-data)
- [RAINBIO official site](https://gdauby.github.io/rainbio/)
- [RAINBIO via GBIF](https://www.gbif.org/en/data-use/83286)
- [ForestGEO Data Portal](https://ctfs.si.edu/datarequest/)
- [sPlotOpen](https://www.idiv.de/research/projects/splot/splotopen-splot/)
- [TRY Database](https://www.try-db.org/TryWeb/Home.php)
- [OBIS data access](https://obis.org/data/access)
- [GBIF API downloads](https://techdocs.gbif.org/en/data-use/api-downloads)
- [GBIF download formats](https://techdocs.gbif.org/en/data-use/download-formats)
- [GBIF open data](https://registry.opendata.aws/gbif/)
