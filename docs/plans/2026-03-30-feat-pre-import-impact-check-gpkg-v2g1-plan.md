# GPKG V2-G1 Implementation Plan

## Goal

Add **pre-import impact check support for simple `VECTOR` / GPKG connectors** in the
preflight service, while keeping `FILE_MULTI_FEATURE` explicitly out of scope.

This plan is a **small, isolated V2b slice**:

- support `connector.type: vector`
- keep `connector.type: file_multi_feature` as a skip
- do not change runtime import behavior
- do not mix GPKG work with plugin-aware reference work

## Why This Is Separate

The current impact-check service already has two independent complexity axes:

1. **Reference coverage**: which columns are referenced by `transform.yml`
2. **Schema readers**: how a source file schema is observed before import

GPKG belongs to the second axis. It should be delivered independently from
plugin-aware scanning so regressions remain attributable and the core service
does not become a single large branching module.

## Scope

### In Scope

- `VECTOR` connectors backed by a single `.gpkg` file
- exact-match filename resolution for those connectors
- native schema reading from SQLite / GeoPackage metadata
- comparison of:
  - attribute columns
  - geometry column presence
  - geometry type metadata
- CLI and API returning a normal impact report instead of a skip

### Out of Scope

- `FILE_MULTI_FEATURE`
- layer aggregation across multiple source files
- CRS compatibility rules beyond lightweight metadata reporting
- fuzzy resolver behavior
- UI disambiguation
- plugin-aware scanning changes

## Current Behavior

Today the compatibility service skips vector connectors in
`src/niamoto/core/services/compatibility.py` with:

- `VECTOR` → `"Not supported in V1 (GPKG)"`
- `FILE_MULTI_FEATURE` → `"Not supported in V1 (multi-feature)"`

This is correct for V1, but it prevents impact-check from helping on a normal
single-file GeoPackage dataset or reference.

## Product Behavior After V2-G1

### Supported

If the uploaded file matches a configured `VECTOR` connector:

- the service resolves the entity
- reads the GeoPackage schema
- compares it with config references and registry context
- returns a standard report with:
  - missing required columns
  - type changes on referenced fields
  - geometry metadata warnings
  - new columns as opportunities

### Still Skipped

If the uploaded file matches a `FILE_MULTI_FEATURE` connector:

- keep returning a skip report
- explicit message: `Not supported in V2-G1 (multi-feature)`

This keeps the first GPKG slice small and avoids modeling a many-source entity
as if it were one table.

## Design

### 1. Add a Schema Reader Abstraction

Refactor the service toward a small reader registry:

- `CSVSchemaReader`
- `GPKGSchemaReader`

Selection is based on connector type, not on file extension alone.

Do not introduce a deep framework. A small internal dispatch method in the
service is enough for V2-G1.

### 2. GPKGSchemaReader

Implement a reader that inspects the GeoPackage directly via SQLite metadata.

Recommended sources:

- `gpkg_contents`
- `gpkg_geometry_columns`
- `pragma table_info(<table>)`

The reader should return an observed schema structure containing:

- `fields`: list of `{name, type}`
- `geometry_column`: optional string
- `geometry_type`: optional string
- `layer_name`: optional string

### 3. Layer Resolution

For V2-G1, layer resolution must stay conservative:

1. If the connector explicitly provides a layer/table name, use it
2. Otherwise:
   - if the file contains exactly one feature table, use it
   - if multiple feature tables exist, return an error asking for explicit layer configuration

Do not guess between multiple layers.

### 4. Comparison Semantics

Extend the comparison model without changing its current spirit.

#### Attribute columns

Use the same rules as CSV:

- missing referenced column → highest referenced severity
- referenced type change → `WARNING`
- new unreferenced column → `OPPORTUNITY`

#### Geometry column

Rules:

- missing expected geometry column → `BLOCKS_IMPORT`
- geometry column present but metadata differs from previous import → `WARNING`
- geometry column present and unchanged → no issue

#### Geometry type

For V2-G1, geometry type differences should be a `WARNING`, not a blocker.

Reason:

- the preflight check can detect a change
- but import/runtime compatibility depends on downstream behavior and is not yet
  modeled precisely enough to justify a hard blocker

### 5. Baseline / Registry Context

For simple `VECTOR` entities, keep using `EntityRegistry` as the historical
context source.

Expected registry shape:

- existing `schema.fields` for attribute columns
- additive metadata for geometry information, for example:
  - `schema.geometry_column`
  - `schema.geometry_type`
  - `schema.layer_name`

This must be backward-compatible:

- if old registry entries do not contain geometry metadata, comparison still works
- only attribute comparison is enriched from the old schema

### 6. Resolver

Extend entity resolution to match `VECTOR` connector paths:

- `connector.path` basename exact match

Do not resolve `FILE_MULTI_FEATURE` source paths in this slice.

## Implementation Phases

### Phase 1: Reader + Data Model

Files likely touched:

- `src/niamoto/core/services/compatibility.py`

Tasks:

1. Introduce a light reader dispatch by connector type
2. Add `GPKGSchemaReader`
3. Extend observed schema shape to carry geometry metadata

### Phase 2: Connector-Aware Resolution and Skip Rules

Files likely touched:

- `src/niamoto/core/services/compatibility.py`

Tasks:

1. Stop skipping `VECTOR`
2. Keep skipping `FILE_MULTI_FEATURE`
3. Extend resolver to match vector connector paths

### Phase 3: Comparison Logic

Files likely touched:

- `src/niamoto/core/services/compatibility.py`

Tasks:

1. Compare attribute columns like CSV
2. Add geometry column comparison
3. Add geometry type warning logic

### Phase 4: Tests

Files likely touched:

- `tests/core/services/test_compatibility.py`
- optionally a dedicated fixture folder under `tests/data/`

Tasks:

1. Reader tests:
   - single-layer GPKG
   - multi-layer GPKG without explicit layer
   - missing geometry metadata handling
2. Service tests:
   - vector entity identical file
   - missing geometry column
   - missing referenced attribute field
   - geometry type changed → warning
   - `FILE_MULTI_FEATURE` still skipped

### Phase 5: Real-Instance Regression

Use at least one real instance with single-file vector connectors to validate:

- CLI `niamoto import check`
- GUI/API `/imports/impact-check`

## Acceptance Criteria

### Functional

- A simple `VECTOR` connector no longer returns a skip report
- A `FILE_MULTI_FEATURE` connector still returns a skip report
- Missing geometry column is detected
- Missing referenced attribute columns are detected
- Geometry type differences produce warnings, not blockers

### Architectural

- No runtime import logic is executed during preflight
- No GPKG special cases are spread through unrelated service methods
- Reader selection remains connector-driven and additive

### UX

- Existing CSV behavior is unchanged
- Error message for ambiguous multi-layer GPKG is explicit
- `FILE_MULTI_FEATURE` message remains clear that support is deferred

## Risks

### Main Risk

Treating a GeoPackage as if it were always a single-table file.

Mitigation:

- explicit V2-G1 support only for simple `VECTOR`
- explicit error when multiple feature tables exist and no layer is configured

### Secondary Risk

Mixing geometry metadata into the old CSV-centric schema shape too early.

Mitigation:

- keep geometry metadata additive and optional
- do not force registry migration for existing entities

## Follow-Up: V2-G2

Once V2-G1 is stable, the next slice is:

- `FILE_MULTI_FEATURE`
- sub-report aggregation by source file / layer
- optional per-source schema baseline

That work should remain a separate plan and PR.

## References

- Main impact-check plan: `docs/plans/2026-03-30-feat-pre-import-impact-check-plan.md`
- Brainstorm: `docs/brainstorms/2026-03-30-data-compatibility-check-brainstorm.md`
- Compatibility service: `src/niamoto/core/services/compatibility.py`
- Import config models: `src/niamoto/core/imports/config_models.py`
- Existing vector/file-multi-feature examples:
  - `test-instance/niamoto-test/config/import.yml`
