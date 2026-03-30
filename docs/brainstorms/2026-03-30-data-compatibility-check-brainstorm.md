---
title: Pre-Import Impact Check
topic: Config-first impact analysis on source data re-upload
date: 2026-03-30
status: approved
---

# Pre-Import Impact Check

## What We're Building

A **pre-import impact check** that analyzes new source files against the existing pipeline configuration when a user re-uploads data. Not a simple schema diff — the check tells the user the **business impact** of their data changes on the import/transform pipeline.

**Framing:** The configuration (import.yml + transform.yml relation keys) is the **source of truth**. The EntityRegistry provides context (what changed since last import), not ground truth. The UX shows pipeline impact, not just technical differences.

### User Story

A field botanist has already set up their Niamoto instance — data imported, groups configured, pages generated and published. Months later, they come back with updated data (new occurrences, new plots, expanded geography). They go to the Sources page, upload their new files via the ImportWizard, and **before the import runs**, they see a clear report: what's compatible, what's missing, what's new.

### Phasing

**V1 (this plan):** CSV only, coarse type inference, compare against import.yml + relation keys in transform.yml, rendered in ImportWizard.

**V2 (future):** GPKG support (native schema metadata), plugin-aware transform.yml reference collection (scan `params` recursively per plugin type).

### Scope (V1)

- **UI**: Compatibility panel in ImportWizard, between upload step and import step
- **CLI**: Subcommand `niamoto import check`
- **Backend**: Shared service in `src/niamoto/core/services/`
- **Non-blocking**: Warnings only, user decides whether to proceed
- **CSV only**: GPKG and other formats deferred to V2

## Why This Approach

### Chosen: Lightweight header + sample comparison (Approach A)

Read CSV headers and a small sample (~100 rows) to infer column names and coarse types. Compare against the current EntityRegistry metadata and column references in import.yml + transform.yml relation keys.

**Why not DuckDB DESCRIBE (Approach B)?** Accurate types are nice but overkill — the user mainly cares about missing columns and obvious type shifts (numeric → text). A Python-only approach is simpler, faster, doesn't need a DB connection, and is easier to test.

**Why not full profiling (Approach C)?** Way too complex for the stated need. The user wants a quick sanity check, not a data quality audit.

**Why CSV-only for V1?** The AutoConfigService currently only processes CSV. The types stored in the engine are coarse. Starting with CSV covers the most common use case and lets us validate the UX before adding format-specific complexity.

## Key Decisions

1. **Trigger**: Automatic on file re-upload in ImportWizard — no extra clicks needed
2. **Scope V1**: CSV only, coarse types, import.yml + relation keys
3. **Behavior**: Non-blocking warning with clear actionable info
4. **CLI**: Subcommand `niamoto import check` (under the import group)
5. **UI**: Panel in ImportWizard, after upload step, before import step
6. **Architecture**: Core service shared between CLI and API
7. **API**: `POST /api/imports/impact-check` (single endpoint: resolve + check)
8. **DERIVED entities**: Excluded from check with message pointing to source dataset
9. **File-to-entity mapping**: Resolver matches uploaded filename against import.yml `connector.path` (exact match, first wins)
10. **First import (no config)**: Skip check silently — nothing to compare against
11. **CLI exit code**: Non-zero (1) when issues found — useful for CI/CD
12. **transform.yml**: V1 checks only relation keys (`key`, `ref_key`, `ref_field`). V2 adds plugin-aware `params` scanning

## Design

### Service Layer

New `CompatibilityService` in `src/niamoto/core/services/compatibility.py`:

```python
@dataclass
class ColumnMatch:
    name: str
    old_type: str
    new_type: str

class ImpactLevel(str, Enum):
    BLOCKS_IMPORT = "blocks_import"         # missing column in import.yml schema/links
    BREAKS_TRANSFORM = "breaks_transform"   # missing column in transform.yml relation keys
    WARNING = "warning"                     # type change, may cause downstream issues
    OPPORTUNITY = "opportunity"             # new column, not yet in config

@dataclass
class ImpactItem:
    column: str
    level: ImpactLevel
    detail: str           # human-readable explanation
    referenced_in: list[str]
    # e.g. ["import.yml > occurrences > links > field",
    #        "transform.yml > group forest > relation > key"]
    old_type: str | None = None  # for type changes
    new_type: str | None = None

@dataclass
class ImpactReport:
    entity_name: str
    file_path: str
    matched_columns: list[ColumnMatch]  # columns present in both, no issue
    impacts: list[ImpactItem]           # all issues and opportunities, sorted by severity
    error: str | None = None            # read error (corrupt file, bad encoding, etc.)
    skipped_reason: str | None = None   # why check was skipped (DERIVED, no config, etc.)

    @property
    def has_blockers(self) -> bool:
        return any(i.level == ImpactLevel.BLOCKS_IMPORT for i in self.impacts)

    @property
    def has_warnings(self) -> bool:
        return any(i.level in (ImpactLevel.BREAKS_TRANSFORM, ImpactLevel.WARNING)
                   for i in self.impacts)

    @property
    def has_opportunities(self) -> bool:
        return any(i.level == ImpactLevel.OPPORTUNITY for i in self.impacts)
```

The service (V1):
1. **Read new file schema**: Reads CSV using the same logic as `GenericImporter._import_csv()` in `engine.py` but with `LIMIT` — reuses DuckDB's `read_csv_auto()` or the engine's separator/encoding detection to avoid check/import divergence. Extracts column names and the coarse types the engine actually persists (aligned with `FieldType` enum).
   - Unreadable/corrupt files: return report with `error` field set
2. **Build config reference map (source of truth)**: Parses import.yml → entity schema fields, links, hierarchy columns, extraction columns. Parses transform.yml → relation keys only (`key`, `ref_key`, `ref_field`, `fields` mapping). Builds `{column_name: [(reference_path, impact_level)]}`.
3. **Enrich with registry context**: Loads EntityRegistry metadata `config["schema"]["fields"]` to compare current vs new types and detect what changed since last import.
4. **Produce impact report**: For each referenced column, classify the impact:
   - Missing column in import.yml schema/links → `BLOCKS_IMPORT`
   - Missing column in transform.yml relation keys → `BREAKS_TRANSFORM`
   - Type change on referenced column → `WARNING`
   - New column not in config → `OPPORTUNITY`

**Connector-specific behavior:**
- **FILE / DUCKDB_CSV**: Normal check against CSV source file
- **VECTOR**: Skipped in V1, supported in V2 (GPKG native schema)
- **DERIVED**: Skip with `skipped_reason = "Derived from {source} — check {source} instead"`
- **FILE_MULTI_FEATURE**: Skipped in V1, supported in V2
- **API / PLUGIN**: Skip with `skipped_reason = "External connector — cannot check locally"`

### Entity Resolver

New `EntityResolver` (part of CompatibilityService or standalone utility):

```python
def resolve_entity(filename: str, import_config: dict) -> str | None:
    """Match an uploaded filename to an entity via import.yml connector.path.

    Returns:
      - entity_name (str) if exact basename match found (first wins)
      - None if no match found
    """
```

Matching strategy — conservative, exact-match only:
1. Compare `filename` against each entity's `connector.path` basename (e.g. `imports/occurrences.csv` → `occurrences.csv`)
2. If exact basename match → return entity name
3. If no exact match → return None, no check triggered (normal auto-configure flow)

No fuzzy/stem matching in V1. False positives from loose matching would be worse than no check at all. If the user renames their file, the resolver simply doesn't match and the normal auto-configure flow handles it.

### Config Reference Collection (V1)

V1 focuses on import.yml and relation keys in transform.yml:

| Config file | Path | What it references |
|---|---|---|
| import.yml | `entities.datasets.{name}.schema.fields` | Declared columns |
| import.yml | `entities.datasets.{name}.schema.id_field` | Primary key column |
| import.yml | `entities.datasets.{name}.links[].field` | Link source column |
| import.yml | `entities.datasets.{name}.links[].target_field` | Link target column |
| import.yml | `entities.references.{name}.hierarchy.levels[].column` | Hierarchy column |
| import.yml | `entities.references.{name}.connector.extraction.id_column` | Extraction ID column |
| import.yml | `entities.references.{name}.connector.extraction.name_column` | Extraction name column |
| import.yml | `entities.references.{name}.connector.extraction.levels[].column` | Extraction level columns |
| import.yml | `entities.references.{name}.connector.extraction.additional_columns` | Extra extraction columns |
| transform.yml | `sources[].relation.key` | Join key in source |
| transform.yml | `sources[].relation.ref_key` / `ref_field` | Join key in reference |
| transform.yml | `sources[].relation.fields` | Field mapping values (e.g. `parent: parent_id` → checks `parent_id`) |

**V2 addition:** Plugin-aware scanning of `widgets_data.{w}.params` — requires knowing which param keys are column references per plugin type (`field`, `fields[].field`, `columns`, `referential_data`, etc.). This needs a plugin metadata registry or convention.

**Note:** export.yml is out of scope — it references widget outputs, not source columns.

### API Endpoint

Single endpoint — resolves entity internally then runs check. Simpler frontend orchestration:

```
POST /api/imports/impact-check
Body: { "file_path": "imports/occurrences.csv" }
Response: { entity_name: str|null, matched_columns: [...], impacts: [...], ... }
```

If `entity_name` is null, no match was found and the frontend skips the panel. Added to existing router `src/niamoto/gui/api/routers/imports.py`.

### CLI Command

```bash
niamoto import check                    # check all entities
niamoto import check --entity taxons    # check one entity
```

Subcommand of the `import` group in `src/niamoto/cli/commands/imports.py`. Iterates over import.yml entities, checks each source file, outputs a color-coded terminal report (green/orange/red). Exit code 0 = all compatible, exit code 1 = issues found.

### Frontend Component

`CompatibilityPanel` in `src/niamoto/gui/ui/src/features/import/components/`:

- Lives in the **ImportWizard** flow, as a step between upload and import execution
- After file upload completes, if an existing entity is detected (via EntityResolver):
  - Call `POST /api/imports/compatibility`
  - Show the CompatibilityPanel with results
- Impact-oriented categories (not just schema diff):
  - Red: **Blocks import** — missing columns referenced in import.yml (schema, links)
  - Orange: **Breaks transform** — missing columns referenced in transform.yml relations
  - Yellow: **Warning** — type changes on referenced columns
  - Blue: **Opportunity** — new columns not yet in config
  - Green: matched columns (count only, collapsed by default)
- Two actions: **"Continue anyway"** (proceeds to import step) / **"Fix data"** (goes back to upload step)

### Integration Points

**Entity resolution — integrated in single endpoint:**
The EntityResolver lives in the backend as part of `CompatibilityService`. The single `POST /api/imports/impact-check` endpoint resolves the entity internally from the `file_path` basename, then runs the check. No separate resolve call needed.

After `POST /api/smart/upload-files` returns successfully, the frontend calls `/impact-check` for each uploaded file. If `entity_name` is null in the response, no match was found and the file proceeds to normal auto-configure flow.

**First import detection:**
If the EntityRegistry is empty or import.yml doesn't exist, skip the check entirely — there's nothing to compare against. No panel is shown.

**Import flow**: The check is informational only — it does NOT gate the import. The user can always proceed.

## Edge Cases Addressed

| Case | Behavior |
|---|---|
| DERIVED entity (no source file) | Skip with message: "Derived from {source} — check {source}" |
| FILE_MULTI_FEATURE (multiple files) | Skipped in V1, supported in V2 |
| API / PLUGIN connector | Skip with message: "External connector — cannot check locally" |
| VECTOR / GPKG | Skipped in V1, supported in V2 (native schema) |
| First import (no config) | Skip silently — no panel shown |
| File doesn't match any entity | No check triggered, normal auto-configure flow |
| File matches multiple entities | V1: return None + log warning (avoid false positive). V2: disambiguation dropdown |
| Empty file (0 rows, header only) | Columns match, types shown as "unknown" |
| Corrupt/unreadable file | Report with `error` field, panel shows error message |
| Renamed file | Falls through to auto-configure (exact match only, no fuzzy) |

## V2 Roadmap

Three independent workstreams, ordered by priority:

### Critical guardrails

- Keep V2 logic in the **pre-import impact check service**, not in the normal
  import runtime. Extending the compatibility layer is acceptable; pushing V2
  behavior into the import engine would increase fragility.
- Do **not** deliver V2 as one large milestone. Ship `V2a`, `V2b`, and `V2c`
  independently to contain complexity and keep regressions attributable.
- Avoid heuristic "magic" for plugin params. If a param is treated as a source
  column reference, that contract must be explicit in plugin metadata or a
  dedicated hook.
- Prefer additive extension points over more branching in one service:
  composable reference providers, schema readers, and a small resolver/reader
  registry.

- **V2a — Plugin-aware param scanning** (highest priority): Explicit contract via
  plugin `config_model` Pydantic fields or `collect_column_refs()` hook. No heuristic
  name scanning. Refactor collectors into composable providers. This is the
  highest complexity / fragility risk in V2 because it increases coupling with
  the plugin ecosystem. Keep it read-only and preflight-only: no plugin
  execution to determine references.
- **V2b — GPKG reader**: Native schema from SQLite metadata. Then FILE_MULTI_FEATURE
  with sub-report aggregation. Reader selection by connector type. Moderate risk
  if isolated behind reader interfaces; high risk if implemented as special
  cases spread through the core service.
- **V2c — Disambiguation UI**: Dropdown when multiple entities share same filename.
  No fuzzy/stem matching (too risky). Low technical risk if kept conservative.
- **V3+ — Downstream widget severity**: Requires solid reference coverage first.

## Open Questions

None — all critical gaps resolved during spec review and user feedback.
