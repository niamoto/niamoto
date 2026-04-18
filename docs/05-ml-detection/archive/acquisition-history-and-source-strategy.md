# Acquisition History and Source Strategy

> Status: Archive
> Audience: Team, AI agents
> Purpose: Preserve the earlier acquisition strategy and candidate-source
> reasoning that informed the current ML dataset expansion work
> Canonical current plans: `docs/plans/`

## Why this document is archived

This document merges two earlier files:

- the historical acquisition plan
- the earlier candidate-source shortlist

It is kept for context because it explains the original reasoning behind:

- targeted regional GBIF batches
- tropical field priorities
- the distinction between product-close data and broader robustness data
- the desired long-term shape of `ml/data/silver/`

For current planning decisions, use `docs/plans/`. For the source list actually
used by the code today, use [../current-training-sources.md](../current-training-sources.md).

## Historical acquisition principles

The original acquisition logic was:

- do **not** optimize for raw volume
- optimize for **benchmark ROI**
- prioritize data that resembles Niamoto’s real product targets

At that stage, the preferred order was:

1. real tested instance data
2. tropical field datasets
3. targeted regional GBIF
4. broader neighboring datasets for robustness

## Historical target profile

The main target families were:

- New Caledonia
- Gabon / Cameroon
- French Guiana / tropical field datasets
- datasets from actually tested instances
- useful GBIF corpora, but not GBIF volume for its own sake

Consequence:

- `forest_inventory` should remain a guardrail
- but it should not drive the acquisition roadmap by itself

## Historical storage direction

The desired direction for `ml/data/silver/` was to move away from a flat
directory and toward provenance-oriented grouping such as:

```text
ml/data/silver/
  instances/
  guyane/
  africa_tropical/
  gbif_targeted/
```

That principle still makes sense conceptually, even if the actual storage
evolved incrementally.

## Historical source prioritization

### Priority A — very close to the product

- real datasets from tested instances
- tropical forest datasets from Guyane, Gabon, Cameroon, New Caledonia
- targeted GBIF exports by region and style

### Priority B — useful neighboring datasets

- large tropical forest networks
- vegetation plot networks
- African and pan-tropical occurrence or plot databases

### Priority C — controlled expansion

- plant trait datasets
- ecologically more distant but still compatible datasets
- broader robustness sources

## Examples from the original shortlist

The original shortlist explicitly highlighted:

- tested instance datasets
- Paracou / ForestScan
- Guyafor network datasets such as Trinité and Trésor
- ForestPlots.net / Lopé
- RAINBIO
- targeted GBIF regional downloads
- targeted institutional GBIF subsets

Some of these became concrete acquisition work; others remained strategic
options.

## What this archive is still useful for

Keep this document when you need:

- the historical why behind acquisition choices
- the original source-selection logic
- the reasoning that separated product-close datasets from broader robustness data

Do not use this document as the source of truth for:

- current plans
- the exact source list used by training
- the exact current benchmark setup
