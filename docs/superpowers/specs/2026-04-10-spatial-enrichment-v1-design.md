# Spatial Enrichment v1 Design

## Summary

Add a first dedicated spatial enrichment workflow for `plots` and `shapes` in Niamoto.

This is not an extension of the taxonomic enrichment workspace. It is a separate product surface with its own source presets, preview model, and result summaries.

The first version focuses on two providers:

- `Open-Meteo Elevation`
- `GeoNames`

The user-facing model stays simple:

- `plots` are enriched from their point coordinates
- `shapes` are enriched from geometry-derived summaries
- one spatial workspace is exposed for spatial references
- one quick panel summarizes the most useful outputs

The design goal is to produce compact, reusable geographic summaries in `extra_data`, while keeping sampled-point detail and raw provider payloads available on demand in preview and detailed results.

## Problem Statement

Niamoto already has enrichment infrastructure and UI presets for `elevation` and `spatial` categories, but the current implementation stops short of a real spatial product workflow.

Today:

- `plots` and `shapes` exist as reference entities
- the frontend already exposes elevation and spatial presets
- the backend service can route to `api_elevation_enricher` and `api_spatial_enricher`
- but those enrichers do not actually exist yet, so the service falls back to taxonomy behavior

This creates three product problems:

- the current spatial presets look available but are not backed by real enrichment runtime
- `plots` and `shapes` would be forced into a taxonomic workspace that does not match their usage
- shape geometries need different treatment than point references, especially for elevation and reverse geocoding

Niamoto needs a first-class spatial enrichment workflow that is useful immediately, avoids fake GIS promises, and keeps the interaction model understandable to field users.

## Goals

- Add a dedicated spatial enrichment workflow for `plots` and `shapes`
- Support `Open-Meteo Elevation` as the default altitude provider
- Support `GeoNames` for administrative context and nearby places
- Enrich `plots` directly from point coordinates
- Enrich `shapes` from geometry-derived summaries using centroid and sampled points
- Store concise, reusable summaries in `extra_data`
- Keep sampled detail and raw provider payloads available in preview/results, not as permanent storage
- Reuse the multi-source enrichment framework where it helps, without forcing taxonomic UX on spatial references

## Non-Goals

- Build full zonal analysis over rasters or polygons in this iteration
- Replace GIS/statistical transformers that already compute shape statistics locally
- Store every sampled point permanently in `extra_data`
- Merge taxonomic and spatial enrichments into one workspace
- Add `OpenTopoData` in the first implementation pass
- Build polygon clipping, raster masking, or server-side spatial overlays in v1

## Design Principles

- Keep point and polygon workflows distinct
- Prefer simple, explainable summaries over pseudo-advanced GIS outputs
- Treat `shapes` as sampled summaries, not exact raster analyses
- Prefer partial success over all-or-nothing failure
- Store compact summaries permanently and keep heavy detail on demand
- Make provider limits and sampling behavior explicit

## Proposed Product Shape

### Separate Spatial Workspace

`plots` and `shapes` should not reuse the taxonomic workspace layout or terminology.

The UI should expose a dedicated `Spatial enrichment` workspace when the reference kind is:

- point-like reference (`plots`)
- spatial reference (`shapes`)

The workspace should still follow the quick-panel / full-workspace model, but with spatial sections instead of taxonomic ones.

### v1 Provider Set

Spatial enrichment v1 uses:

- `Open-Meteo Elevation` for altitude
- `GeoNames` for subdivision and nearby-place context

`OpenTopoData` remains a later extension or fallback provider.

### One Workflow, Two Output Shapes

The workflow is unified at product level, but the persisted summary differs by entity type:

- `plots` produce direct point summaries
- `shapes` produce sampled geometry summaries

## Data Model

Spatial enrichment summaries are stored under:

`extra_data.api_enrichment.sources.<source_id>.data`

### Plot Summary Shape

Recommended structure:

```json
{
  "location": {
    "latitude": -21.5321,
    "longitude": 165.4322
  },
  "elevation": {
    "value_m": 482.0,
    "source_dataset": "open-meteo-dem90"
  },
  "admin": {
    "country_code": "NC",
    "country_name": "New Caledonia",
    "admin1": "Province Nord",
    "admin2": "Koné",
    "nearest_place": "Koné"
  },
  "provenance": {
    "provider": "openmeteo+geonames",
    "enriched_at": "2026-04-10T00:00:00Z",
    "endpoints": [
      "open-meteo:elevation",
      "geonames:countrySubdivision",
      "geonames:findNearby"
    ]
  }
}
```

### Shape Summary Shape

Recommended structure:

```json
{
  "geometry_summary": {
    "centroid": {
      "latitude": -21.5321,
      "longitude": 165.4322
    },
    "bbox": {
      "min_lat": -21.81,
      "min_lng": 165.01,
      "max_lat": -21.29,
      "max_lng": 165.78
    },
    "sample_count": 9
  },
  "elevation_summary": {
    "centroid_elevation_m": 482.0,
    "min_elevation_m": 120.0,
    "max_elevation_m": 913.0,
    "mean_elevation_m": 441.8,
    "source_dataset": "open-meteo-dem90"
  },
  "admin_summary": {
    "countries": ["NC"],
    "admin1_values": ["Province Nord"],
    "admin2_values": ["Koné", "Pouembout"],
    "nearest_places": ["Koné", "Pouembout"]
  },
  "sampling": {
    "strategy": "bbox_grid",
    "sample_mode": "centroid+bbox",
    "sample_count": 9
  },
  "provenance": {
    "provider": "openmeteo+geonames",
    "enriched_at": "2026-04-10T00:00:00Z",
    "endpoints": [
      "open-meteo:elevation",
      "geonames:countrySubdivision",
      "geonames:findNearby"
    ]
  }
}
```

### What Is Stored Permanently

- plot coordinates used for enrichment
- shape centroid and bbox summary
- compact elevation summaries
- compact administrative summaries
- sampling metadata
- provider provenance

### What Is Not Stored Permanently

- every sampled point with full payload
- full raw reverse-geocoding responses
- long administrative candidate lists
- any output pretending to be exact zonal analysis

Sampled detail stays available in preview and raw results.

## Runtime Pipeline

Spatial enrichment v1 uses two execution paths.

### Plot Pipeline

#### Step 1: Coordinate Extraction

Read latitude/longitude from the entity geometry or point field.

#### Step 2: Elevation Lookup

Call `Open-Meteo Elevation` with the plot coordinates.

This produces:

- elevation in meters
- source dataset metadata when available

#### Step 3: Administrative Context

Call `GeoNames countrySubdivision` with the same coordinates.

This produces:

- country code/name
- admin level 1
- admin level 2

#### Step 4: Nearby Place

Call `GeoNames findNearby` with the same coordinates.

This produces:

- nearest named place
- optional distance/population fields for preview

#### Step 5: Summary Build

Construct a compact `location / elevation / admin` summary.

### Shape Pipeline

#### Step 1: Geometry Summary

Compute locally:

- centroid
- bbox
- sampled points

The sampling design for v1 is:

- always include centroid
- include bbox-derived sample points
- support bounded grid-style sampling inside bbox
- keep sampling count configurable and conservative

This is a sampled summary, not polygon zonal analysis.

#### Step 2: Elevation Sampling

Call `Open-Meteo Elevation` with the sampled coordinates.

Compute:

- centroid elevation
- min elevation
- max elevation
- mean elevation

#### Step 3: Administrative Sampling

Call `GeoNames countrySubdivision` and `findNearby` on:

- centroid
- selected sample points when enabled

Then deduplicate and summarize:

- countries
- admin1 values
- admin2 values
- nearby places

#### Step 4: Summary Build

Construct:

- `geometry_summary`
- `elevation_summary`
- `admin_summary`
- `sampling`

## Error and Partial-Success Model

Spatial enrichment should remain useful under partial provider failures.

Rules:

- if elevation succeeds and GeoNames fails, keep elevation summary and mark result partial
- if GeoNames succeeds and elevation fails, keep administrative summary and mark result partial
- if shape sampling succeeds but one provider returns sparse data, keep what is usable
- provider unavailability must not corrupt previously stored spatial summaries from other sources

## Provider Notes

### Open-Meteo Elevation

Open-Meteo accepts WGS84 latitude/longitude and supports multiple coordinates in one request.

This makes it suitable for:

- direct plot enrichment
- small sampled batches for shapes

### GeoNames

GeoNames is appropriate for:

- country/admin subdivision lookup
- nearby populated place lookup

It requires a user-provided username and has usage limits on the free service.

The UI must therefore treat GeoNames credentials as user-owned configuration, similar to other keyed sources.

### OpenTopoData

OpenTopoData is not part of v1, but the data model and UI should not prevent adding it later as:

- an alternative elevation provider
- a fallback where Open-Meteo is insufficient

## Configuration Model

Spatial presets should be exposed through the existing enrichment source editor, but with spatial-specific options.

### Plot-Oriented Defaults

- Open-Meteo enabled by default
- GeoNames optional but strongly suggested
- no sampling settings exposed

### Shape-Oriented Defaults

- Open-Meteo enabled by default
- GeoNames optional
- sampling settings exposed:
  - `sample_mode`
  - `sample_count`
  - `include_bbox_summary`
  - `include_nearby_places`

Example conceptual source:

```yaml
- id: spatial-context
  label: Spatial Context
  plugin: api_spatial_enricher
  enabled: true
  config:
    profile: spatial_context_v1
    elevation_provider: open_meteo
    geocoder_provider: geonames
    sample_mode: centroid_bbox_grid
    sample_count: 9
    include_bbox_summary: true
    include_nearby_places: true
```

## Interface Design

### Workspace Split

Taxonomic references keep the existing enrichment workspace.

Spatial references should open a separate workspace with spatial sections and language.

### Configuration View

The first visible presets should be:

- `Open-Meteo Elevation`
- `GeoNames`

Later:

- `OpenTopoData`

### Tester View

#### For Plots

Sections:

- `Location`
- `Elevation`
- `Administrative context`
- `Nearby place`
- `Raw API response`

#### For Shapes

Sections:

- `Geometry summary`
- `Elevation summary`
- `Administrative summary`
- `Sampled points`
- `Raw API response`

### Results View

#### For Plots

Show:

- altitude
- country/admin
- nearby place

#### For Shapes

Show:

- centroid
- bbox
- min/max/mean elevation
- primary admin values

Do not persist or foreground large sample lists here.

### Quick Panel

#### Plot Summary

- altitude
- primary admin value
- nearest place

#### Shape Summary

- mean elevation
- min/max elevation
- primary country/admin values

## Technical Implications

Spatial enrichment v1 is not a frontend-only change.

It requires:

- real implementation of `api_elevation_enricher`
- real implementation of `api_spatial_enricher`
- entity-geometry extraction logic for plots and shapes
- sampled-point generation for shapes
- spatial preview/result rendering distinct from taxonomic blocks

The current backend fallback from non-existent spatial enrichers to taxonomy behavior should be removed once the real plugins are present.

## Rollout Strategy

Recommended implementation order:

1. backend enrichers and geometry/sampling utilities
2. configuration transport and validation models
3. spatial workspace UI and quick-panel rendering
4. preview/result sections for plots and shapes
5. optional `OpenTopoData` later

## Success Criteria

- a plot can be enriched with altitude and administrative context
- a shape can be enriched with centroid+bbox sampled elevation summary
- the UI clearly separates taxonomic and spatial enrichment
- results stay readable and compact for domain users
- no fake zonal-analysis claims are implied by the product copy or data model

## Sources

- [Open-Meteo Elevation API](https://open-meteo.com/en/docs/elevation-api)
- [GeoNames Web Services](https://www.geonames.org/export/web-services.html)
- [GeoNames Export Services Overview](https://www.geonames.org/export/ws-overview.html)
- [OpenTopoData API](https://www.opentopodata.org/api/)
