# Data Acquisition Plan for the ML Detection Benchmark

## Purpose

This document translates the candidate source shortlist into a concrete
acquisition plan:

- what to integrate first;
- where to store the data;
- how to connect it to the gold set;
- which benchmark tags to assign;
- which criteria to use when deciding whether a source is worth the effort.

The principle is simple:

- we are not looking for maximum volume;
- we are looking for the best **benchmark ROI** for the real product target.

## Retained Product Target

The declared priorities at this stage are:

1. datasets of the type:
   - New Caledonia
   - Gabon / Cameroon
   - Guyane
   - datasets from actually tested instances
   - datasets that are not necessarily highly standardised
2. GBIF as the second major priority

Consequence:

- `forest_inventory` must remain a useful guardrail;
- but it must not drive the acquisition roadmap alone.

## Recommended Target Structure

The current `ml/data/silver` structure contains mainly:

- `ifn_france/`
- `finland_sweden/`
- `pasoh/`
- flat files at the root

For new sources, I recommend a more explicit structure:

```text
ml/data/silver/
  instances/
    <instance_name>/
  guyane/
    paracou/
    trinite/
    tresor/
  africa_tropical/
    rainbio/
    lope/
    seosaw/
  gbif_targeted/
    new_caledonia/
    guyane/
    gabon/
    cameroon/
```

Goal:

- make provenance readable;
- simplify benchmark tags;
- avoid a `ml/data/silver/` root that is too flat.

## Batch 1 — Priority Acquisition

## 1. Datasets from Actually Tested Instances

### Why

- maximum benchmark value;
- closest proximity to the product;
- real headers, real anomalies, real expectations.

### Recommended Storage

```text
ml/data/silver/instances/<instance_name>/
```

### Recommended Benchmark Tags

- `instance_real`
- `priority_main`
- `schema_style=field`
- `region=<actual region if known>`

### build_gold_set Integration

Add each dataset as an explicit source in
[ml/scripts/data/build_gold_set.py](../../ml/scripts/data/build_gold_set.py)
with:

- `name`
- `path`
- `labels`
- `language`
- `sample_rows`
- and if possible a block of benchmark metadata in the future

### Success Criterion

After integration:

- we must be able to measure `instance_real` separately;
- this bucket must become a central component of the main benchmark.

## 2. Open Tropical Guyane

### Target Sources

- Paracou
- Guyafor / Trinité
- Guyafor / Trésor

### Why

- very close to tropical field needs;
- good chance of obtaining plot, tree, taxonomy, measurement, and environment
  columns;
- useful for enriching `tropical_field` with data better aligned to the
  product.

### Recommended Storage

```text
ml/data/silver/guyane/paracou/
ml/data/silver/guyane/trinite/
ml/data/silver/guyane/tresor/
```

### Recommended Benchmark Tags

- `tropical_field`
- `plot_inventory`
- `guyane`
- `priority_main`

### Success Criterion

- create a `guyane` sub-benchmark
- measure its results separately in evaluation runs

### Verified Current State

Dataverse verification performed:

- `Paracou / ForestScan`: main CSV publicly accessible
- `Trinité`: main CSV restricted, access on request
- `Trésor`: main CSV restricted, access on request
- `Tibourou`: main CSV restricted, access on request
- `Montagne Tortue`: main CSV restricted, access on request

Operational consequence:

- the first batch immediately integrable is `Paracou / ForestScan`
- other Guyane datasets remain in the acquisition queue with status
  `waiting_access`

### Batch 1 Progress

Already done:

- local retrieval of `FGPlotsCensusData2023.csv`
- retrieval of available Guyafor description files
- integration of `forestscan_paracou_census` into the gold set

Result:

- `34` gold columns added
- total gold set: `2265` columns

Recommended status:

- `Paracou / ForestScan`: `done`
- `Trinité / Trésor / Tibourou / Montagne Tortue`: `waiting_access`

## 3. Targeted GBIF by Region

### Regions to Take First

- New Caledonia
- French Guyane
- Gabon
- Cameroon

### Why

- GBIF remains a product priority;
- but it must be targeted geographically rather than taking a blind global
  corpus;
- this allows building a GBIF benchmark close to the areas of interest.

### Recommended Storage

```text
ml/data/silver/gbif_targeted/new_caledonia/
ml/data/silver/gbif_targeted/guyane/
ml/data/silver/gbif_targeted/gabon/
ml/data/silver/gbif_targeted/cameroon/
```

### Recommended Benchmark Tags

- `gbif`
- `gbif_core_standard`
- `gbif_extended`
- `priority_main`
- `region=<...>`

### Success Criterion

After integration:

- distinguish `gbif_core_standard` and `gbif_extended`;
- prioritise tracking GBIF from target regions rather than a too-easy global
  GBIF.

### Verified Current State

Two targeted GBIF sub-batches now exist:

1. `gbif_targeted/`
   - general regional batch
   - `5000` `Plantae` occurrences per region
   - integrated regions:
     - `new_caledonia`
     - `guyane`
     - `gabon`
     - `cameroon`

2. `gbif_targeted_institutional/`
   - institutional filtered batch
   - retained at this stage for:
     - `gabon`
     - `cameroon`
   - filter:
     - `PRESERVED_SPECIMEN`, `MATERIAL_SAMPLE`, `OCCURRENCE`
     - presence of institutional fields
     - exclusion of large observational datasets

### Progress

Already done:

- retrieval script
  [scripts/data/fetch_gbif_targeted.py](scripts/data/fetch_gbif_targeted.py)
- retrieval of general regional batch `NC/GF/GA/CM`
- retrieval of institutional batch `GA/CM`
- integration of the 6 new targeted GBIF sources into the gold set

Observed contribution to the gold set:

- general regional batch:
  - `new_caledonia`: `41`
  - `guyane`: `38`
  - `gabon`: `37`
  - `cameroon`: `39`
- institutional batch:
  - `gabon`: `36`
  - `cameroon`: `36`

### Recommended Status

- `gbif_targeted/new_caledonia`: `done`
- `gbif_targeted/guyane`: `done`
- `gbif_targeted/gabon`: `done`
- `gbif_targeted/cameroon`: `done`
- `gbif_targeted_institutional/gabon`: `done`
- `gbif_targeted_institutional/cameroon`: `done`
- `gbif_targeted_institutional/new_caledonia`: `deferred`
- `gbif_targeted_institutional/guyane`: `deferred`

## 4. Extended Tropical Africa

### Target Sources

- RAINBIO
- ForestPlots Lopé if access is possible

### Why

- provides directly useful tropical Africa coverage;
- complements Gabon/Cameroon even if not all of it is pure plot inventory;
- very useful for taxonomy, locality, habitat, and semi-structured fields.

### Recommended Storage

```text
ml/data/silver/africa_tropical/rainbio/
ml/data/silver/africa_tropical/lope/
```

### Recommended Benchmark Tags

- `africa_tropical`
- `tropical_field` or `occurrence` depending on the dataset
- `priority_main`

## Batch 2 — After Batch 1 Is Stabilised

## 5. ForestGEO

- useful for broadening forest inventories
- to integrate after regional priorities
- tags:
  - `plot_inventory`
  - `forest_network`
  - `priority_secondary`

## 6. sPlotOpen

- useful for vegetation plot diversity
- more of an expansion benchmark
- tags:
  - `vegetation_plot`
  - `priority_secondary`

## 7. SEOSAW

- useful if woodland / savanna coverage is needed
- tags:
  - `africa_tropical`
  - `savanna_plot`
  - `priority_secondary`

## Batch 3 — Only If Explicitly Needed

## 8. TRY

- mainly useful for traits;
- more relevant for enriching the ontology or affordances than for raw
  detection.

## 9. OBIS

- to integrate only if the marine/coastal component becomes important;
- potentially useful for marine New Caledonia.

## 10. AusPlots

- good robustness benchmark;
- not a priority given the current product target.

## Integration into build_gold_set.py

## Recommended Minimal Format per Source

Each new source should be added to the source list with at minimum:

```python
{
    "name": "...",
    "path": ML_ROOT / "data/silver/...",
    "labels": ...,
    "language": "...",
    "sample_rows": ...,
}
```

## Metadata to Prepare

The current script does not yet structure these tags explicitly, but I
recommend preparing the extension towards:

- `region`
- `source_family`
- `schema_style`
- `priority_tier`

Conceptual example:

```python
{
    "name": "paracou_trees",
    "path": ML_ROOT / "data/silver/guyane/paracou/trees.csv",
    "labels": PARACOU_TREE_LABELS,
    "language": "fr",
    "sample_rows": 1000,
    "benchmark_tags": {
        "region": "guyane",
        "source_family": "plot_inventory",
        "schema_style": "field",
        "priority_tier": "main",
    },
}
```

Even if `benchmark_tags` is not yet directly consumed, preparing this
structure will simplify the evolution of the evaluation protocol.

## Recommended Integration Pipeline

For each new source:

1. download / normalise into `ml/data/silver/...`
2. inspect columns and choose an annotable subset
3. write the `LABELS`
4. add the entry to `build_gold_set.py`
5. regenerate the gold set
6. verify its effect on:
   - `primary`
   - `tropical_field`
   - `gbif_core_standard`
   - `gbif_extended`
   - `instance_real`

## What Not to Do

- massively add non-targeted global GBIF without distinguishing `core` and
  `extended`
- integrate datasets distant from the product before instance data
- let new sources dilute the main benchmark
- integrate a source simply because it is large

## Selection Criteria Before Integration

A source is worth the effort if at least two criteria are true:

- close to a priority area or use case;
- non-trivial headers;
- realistic and exploitable values;
- useful variation compared to the existing gold set;
- strong probability of improving robustness on the product target.

## Recommended Execution Order

### Sprint 1

1. real instance datasets
2. Paracou
3. Trinité
4. Trésor

### Sprint 2

1. targeted GBIF New Caledonia
2. targeted GBIF Guyane
3. targeted GBIF Gabon
4. targeted GBIF Cameroon

### Sprint 3

1. RAINBIO
2. ForestPlots Lopé if access is possible
3. ForestGEO or sPlotOpen depending on availability

## Global Success Criterion

At the end of batch 1, the benchmark must be able to clearly answer:

- are we performing well on real instance datasets?
- are we performing well on tropical field datasets?
- are we performing well on targeted GBIF from the important regions?
- do regressions on `forest_inventory` remain contained?

## Recommended Decision

If we want to move forward efficiently:

1. integrate real instance data first
2. then enrich Guyane
3. build a targeted GBIF sub-benchmark
4. then expand to tropical Africa

The rest comes after.
