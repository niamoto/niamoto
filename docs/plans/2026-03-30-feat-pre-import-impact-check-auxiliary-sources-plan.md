---
title: "feat: Pre-Import Impact Check V1.1 for Auxiliary Transform Sources"
type: feat
date: 2026-03-30
brainstorm: docs/brainstorms/2026-03-30-data-compatibility-check-brainstorm.md
related:
  - docs/plans/2026-03-30-feat-pre-import-impact-check-plan.md
---

# feat: Pre-Import Impact Check V1.1 for Auxiliary Transform Sources

## Overview

Follow-up to V1 of the pre-import impact check.

V1 works well for imported entities backed by `EntityRegistry` metadata (`occurrences`,
`plots`, etc.), but it is not a good fit for raw auxiliary CSV sources used only
during transform execution (`raw_plot_stats.csv`, `raw_shape_stats.csv`, similar
class-object/statistics inputs).

This plan introduces a small V1.1 extension that keeps the existing V1 behavior
for imported entities while adding a separate, quieter, transform-oriented model
for auxiliary sources.

## Problem Statement

Auxiliary transform sources are currently treated too much like imported entities,
even though they are not imported into the database as first-class entities.

That creates three problems:

1. **No stable baseline**
   - Imported entities can compare against `EntityRegistry`.
   - Auxiliary transform sources usually cannot.
   - Result: re-uploading the exact same file can produce a long list of `"new column"`
     opportunities because the old schema is effectively unknown.

2. **Wrong severity model**
   - For `occurrences.csv`, a missing required column can block import.
   - For `raw_plot_stats.csv`, the real consequence is different: the transform
     pipeline breaks, but import itself is not the issue.

3. **Reference coverage gap**
   - V1 relation-key coverage is not enough for these files.
   - Their columns are commonly consumed through transformer params such as:
     - `direct_attribute.params.field`
     - `field_aggregator.params.fields[*].field`
   - Join-related config such as `match_field` is also important for these sources.

## Goals

- Preserve V1 behavior for imported entities.
- Introduce an explicit `transform_source` target kind for raw auxiliary sources.
- Add a dedicated persisted schema baseline for transform sources.
- Cover the minimum high-value transform references for these sources.
- Reduce noisy `"opportunity"` findings when no baseline exists yet.
- Keep all logic in the compatibility/preflight layer, not in normal import runtime.

## Non-Goals

- Full plugin-aware scanning across all transformers and widgets.
- GPKG support.
- `FILE_MULTI_FEATURE` support.
- Fuzzy filename matching.
- Downstream widget severity analysis.
- Refactoring `GenericImporter` or changing import execution semantics.

## Proposed Solution

Split the compatibility domain into two kinds of checked targets:

1. **`import_entity`**
   - Current V1 behavior.
   - Baseline comes from `EntityRegistry`.
   - Uses `BLOCKS_IMPORT`, `BREAKS_TRANSFORM`, `WARNING`, `OPPORTUNITY`.

2. **`transform_source`**
   - New V1.1 behavior for auxiliary CSV sources referenced by transforms.
   - Baseline comes from a new persisted source-schema registry, not `EntityRegistry`.
   - Main severities are `BREAKS_TRANSFORM` and `WARNING`.
   - `"opportunity"` findings are suppressed or downgraded unless a baseline exists.

## Scope Rules

### What counts as a `transform_source`

A file should be treated as `transform_source` when it is configured as a raw
transform input rather than an imported entity. Initial scope:

- `import.yml > auxiliary_sources[*]`
- `transform.yml > sources[*].data` when `data` is a file path and the source is
  not also a normal imported entity

### Baseline behavior

- `import_entity` baseline: `EntityRegistry`
- `transform_source` baseline: new `TransformSourceRegistry`
- If a `transform_source` has **no baseline yet**:
  - run a required-columns check only
  - suppress `"new column"` opportunities
  - show a quiet informational UX state

## Target Architecture

```text
CompatibilityService
├── TargetResolver
│   ├── import_entity (existing)
│   └── transform_source (new)
├── BaselineLoader
│   ├── EntityRegistryBaselineLoader
│   └── TransformSourceBaselineLoader
├── RefsProviders
│   ├── ImportRefsProvider
│   ├── TransformRelationRefsProvider
│   └── TransformPluginRefsProviderV1_1
└── ImpactAnalyzer
```

## Key Design Decisions

### 1. Separate baseline store for transform sources

Do **not** force raw auxiliary sources into `EntityRegistry`.

Introduce a dedicated persisted store, for example:

- new module: `src/niamoto/core/imports/source_registry.py`
- new table: `niamoto_metadata_transform_sources`

Suggested stored fields:

- `source_name`
- `path`
- `group_by`
- `source_kind` (`transform_source`)
- `schema_json`
- `updated_at`

Key choice should be stable enough to survive re-uploads:

- primary lookup key: `source_name`
- secondary validation data: `path`, `group_by`

### 2. Minimal plugin-aware coverage in V1.1

Do **not** jump directly to full V2 plugin-aware scanning.

Only support the most important plugins for auxiliary sources:

- `direct_attribute`
- `field_aggregator`

And add one missing relation field:

- `relation.match_field`

That gives immediate value for `raw_plot_stats.csv` / `raw_shape_stats.csv`
without requiring changes across the full plugin ecosystem.

### 3. Different finding policy for transform sources

For `transform_source`, prioritize transform breakage detection over schema
inventory reporting.

Default behavior:

- missing referenced column -> `BREAKS_TRANSFORM`
- changed type on referenced column -> `WARNING`
- extra column with baseline -> optional `OPPORTUNITY`
- extra column without baseline -> no finding

## Files to Create / Modify

| File | Action | Purpose |
|------|--------|---------|
| `src/niamoto/core/services/compatibility.py` | Modify | Add target-kind split, baseline strategy, `match_field`, auxiliary-source rules |
| `src/niamoto/core/imports/source_registry.py` | Create | Persist schema baselines for transform-only sources |
| `src/niamoto/core/services/transformer.py` | Modify | Persist/update transform-source baseline after successful transform run |
| `src/niamoto/gui/api/routers/imports.py` | Modify | Expose target kind / quieter transform-source semantics if needed |
| `src/niamoto/gui/ui/src/features/import/components/CompatibilityPanel.tsx` | Modify | Render informational state for transform-source first baseline |
| `tests/core/services/test_compatibility.py` | Modify | Add transform-source baseline and no-noise regression coverage |
| `tests/core/imports/test_source_registry.py` | Create | Unit tests for persisted transform-source baselines |
| `tests/gui/api/routers/test_imports.py` | Modify | API regression coverage for transform-source reports |

## Implementation Phases

### Phase 1: Introduce target kind split

Extend the resolver/service flow so a matched file returns a structured target,
not just an entity name.

Suggested shape:

```python
@dataclass
class ResolvedTarget:
    kind: Literal["import_entity", "transform_source"]
    name: str
    file_path: str
    group_by: Optional[str] = None
```

Rules:

- imported entities in `import.yml` -> `import_entity`
- auxiliary/raw transform file source -> `transform_source`
- ambiguous match -> `None`

**Acceptance criteria**

- `occurrences.csv` resolves to `import_entity`
- `raw_plot_stats.csv` resolves to `transform_source`
- duplicate basename still returns `None`

### Phase 2: Add `TransformSourceRegistry`

Create a dedicated metadata store for transform-source schemas.

Minimal API:

```python
class TransformSourceRegistry:
    def get(self, source_name: str) -> TransformSourceMetadata | None: ...
    def upsert(self, source_name: str, path: str, group_by: str | None, schema: dict) -> None: ...
```

**Persistence timing**

Primary path:
- after a successful transform run

Optional backstop:
- after explicit source configuration save if that flow already validates the file

Do **not** update baseline during a failed compatibility check.

**Acceptance criteria**

- source baseline can be created in DuckDB metadata
- re-reading the same source returns the previous schema
- missing baseline returns `None`, not an error

### Phase 3: Extend reference collection for transform sources

Add the minimum missing coverage:

1. `relation.match_field`
2. `direct_attribute.params.field` when `params.source` matches the source name
3. `field_aggregator.params.fields[*].field` when nested `source` matches the source name

Implementation approach:

- keep it explicit and limited
- do not introduce generic recursive heuristics yet
- build a small `TransformPluginRefsProviderV1_1`

**Acceptance criteria**

- `raw_plot_stats.csv` checks `match_field=plot_id`
- `raw_shape_stats.csv` checks `match_field=label`
- a `direct_attribute` referencing auxiliary source contributes a required field
- a `field_aggregator` referencing auxiliary source contributes required fields

### Phase 4: Add transform-source comparison semantics

Update `ImpactAnalyzer` so the logic depends on target kind.

For `transform_source`:

- without baseline:
  - report only missing referenced columns / unreadable file / path errors
  - suppress opportunities
- with baseline:
  - compare referenced columns against old/new schema
  - allow warnings on type drift
  - keep opportunities optional and low-noise

**Acceptance criteria**

- identical re-upload of a known auxiliary source -> `0 impacts`
- first-ever check of auxiliary source -> no spammy opportunities
- missing `match_field` or plugin field -> `BREAKS_TRANSFORM`

### Phase 5: Persist baseline after successful transform lifecycle

Hook baseline persistence into the transform lifecycle.

Preferred place:
- `TransformerService`, after successful use/validation of a transform source

Reason:
- this keeps baseline aligned with a known-good pipeline state
- avoids persisting speculative schemas from failed checks

**Acceptance criteria**

- successful transform run updates source baseline
- failed transform run does not overwrite baseline

### Phase 6: UI / CLI messaging adjustments

Refine user-facing messages for transform sources:

- `import_entity`: keep existing V1 language
- `transform_source` with no baseline:
  - "Required columns validated"
  - "No previous baseline yet, so new-column opportunities are suppressed"

This is important to avoid the impression that the check is inconsistent.

**Acceptance criteria**

- no long noisy opportunity list on first auxiliary-source check
- user still sees missing required transform fields clearly

## Testing Strategy

### Unit tests

- target resolution for `import_entity` vs `transform_source`
- `TransformSourceRegistry` persistence
- `match_field` collection
- `direct_attribute` field collection
- `field_aggregator` nested field collection
- no-baseline suppression of opportunities

### Integration tests

Use real instance-style fixtures modeled on:

- `test-instance/niamoto-subset`
- `test-instance/niamoto-test2`

Key regression cases:

1. Re-upload identical `occurrences.csv` -> `0 impacts`
2. Re-upload identical `plots.csv` -> `0 impacts`
3. Re-upload identical `raw_plot_stats.csv` with baseline -> `0 impacts`
4. First check of `raw_shape_stats.csv` without baseline -> no opportunity spam
5. Remove `plot_id` from `raw_plot_stats.csv` -> `BREAKS_TRANSFORM`
6. Remove `label` from `raw_shape_stats.csv` -> `BREAKS_TRANSFORM`

## Risks and Guardrails

- Keep all new logic in the compatibility/preflight layer.
- Do not add special cases inside normal import execution for auxiliary sources.
- Do not generalize plugin scanning beyond the two explicitly supported plugins in V1.1.
- Do not emit `"opportunity"` findings for transform sources unless a baseline is known.
- Treat this as a focused V1.1 hardening step, not as the full V2 plugin-aware system.

## Success Criteria

This plan is successful when:

- imported entities still behave exactly like V1
- auxiliary transform sources stop producing noisy false positives on identical re-upload
- transform-critical missing fields are still reported
- no changes are required to unrelated plugins
- the design remains compatible with future V2 plugin-aware scanning

## Recommended Delivery Order

1. Phase 1 + Phase 2
2. Phase 3 (`match_field`, `direct_attribute`, `field_aggregator`)
3. Phase 4 comparison semantics
4. Phase 5 persistence hook
5. Phase 6 UX wording cleanup

## References

- [Brainstorm](/Users/julienbarbe/Dev/clients/niamoto/docs/brainstorms/2026-03-30-data-compatibility-check-brainstorm.md)
- [V1 plan](/Users/julienbarbe/Dev/clients/niamoto/docs/plans/2026-03-30-feat-pre-import-impact-check-plan.md)
- [Compatibility service](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/core/services/compatibility.py)
- [DirectAttribute plugin](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/core/plugins/transformers/extraction/direct_attribute.py)
- [FieldAggregator plugin](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/core/plugins/transformers/aggregation/field_aggregator.py)
