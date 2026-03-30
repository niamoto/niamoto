---
title: "feat: Pre-Import Impact Check V1"
type: feat
date: 2026-03-30
brainstorm: docs/brainstorms/2026-03-30-data-compatibility-check-brainstorm.md
---

# feat: Pre-Import Impact Check V1

## Overview

When a user re-uploads source data (CSV), automatically analyze the new file against the existing pipeline configuration and show the **business impact** before importing. Not a schema diff — an impact check that tells the user what will break, what might break, and what's new.

Design decisions are captured in the [approved brainstorm](../brainstorms/2026-03-30-data-compatibility-check-brainstorm.md). This plan covers V1 implementation only (CSV, coarse types, import.yml + transform.yml relation keys).

## Problem Statement

A user returns months later with updated data. They drop their new CSV on the Sources page and hit Import. If a column was renamed, removed, or changed type, the import succeeds but the transform pipeline silently breaks — bad charts, missing data, confusing errors downstream. There is no pre-flight check to warn them.

## Proposed Solution

A shared **CompatibilityService** (core layer) that:
1. Reads the new CSV schema (reusing engine.py's CSV reading logic)
2. Builds a config reference map from import.yml + transform.yml relation keys
3. Compares against EntityRegistry metadata
4. Produces an `ImpactReport` with severity-classified items

Exposed via:
- **CLI**: `niamoto import check` subcommand
- **API**: `POST /api/imports/impact-check` (single endpoint: resolves entity + runs check)
- **UI**: `CompatibilityPanel` in ImportWizard (between upload and import steps)

## Technical Approach

### Architecture

```
                    CompatibilityService (core)
                   /           |            \
          EntityResolver  ConfigRefCollector  CSVSchemaReader
               |               |                    |
         import.yml      import.yml +          engine._read_csv
         connector.path  transform.yml          (reused logic)
                         relation keys
                               |
                         ImpactReport
                        /      |       \
                    CLI       API      Frontend
              (import check) (/impact-check) (CompatibilityPanel)
```

**Source of truth**: import.yml + transform.yml relation keys (config-first).
**Context enrichment**: EntityRegistry `config["schema"]["fields"]` (what changed since last import).

### Key Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `src/niamoto/core/services/compatibility.py` | **Create** | Core service: EntityResolver, ConfigRefCollector, CSVSchemaReader, ImpactAnalyzer |
| `src/niamoto/cli/commands/imports.py` | Modify | Add `check` subcommand |
| `src/niamoto/gui/api/routers/imports.py` | Modify | Add `/impact-check` endpoint |
| `src/niamoto/gui/ui/src/features/import/components/CompatibilityPanel.tsx` | **Create** | Impact report UI component |
| `src/niamoto/gui/ui/src/features/import/components/ImportWizard.tsx` | Modify | Add `checking` phase |
| `src/niamoto/gui/ui/src/features/import/api/compatibility.ts` | **Create** | API client for compatibility endpoints |
| `src/niamoto/gui/ui/src/features/import/hooks/useCompatibilityCheck.ts` | **Create** | Hook to trigger check after upload |
| `tests/core/services/test_compatibility.py` | **Create** | Unit tests |
| `tests/core/services/test_compatibility_integration.py` | **Create** | Integration tests with real CSV + config |
| `tests/gui/api/routers/test_imports_compatibility.py` | **Create** | API endpoint tests |

## Implementation Phases

### Phase 1: Core Service — Config Reference Collector

Build the module that parses import.yml and transform.yml to extract all column references with their impact levels.

**`src/niamoto/core/services/compatibility.py`** — data models + config collector:

```python
# src/niamoto/core/services/compatibility.py

from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import yaml

from niamoto.core.imports.config_models import (
    GenericImportConfig, ConnectorType, DatasetEntityConfig, ReferenceEntityConfig
)
from niamoto.common.transform_config_models import TransformGroupConfig


class ImpactLevel(str, Enum):
    BLOCKS_IMPORT = "blocks_import"
    BREAKS_TRANSFORM = "breaks_transform"
    WARNING = "warning"
    OPPORTUNITY = "opportunity"


@dataclass
class ColumnMatch:
    name: str
    old_type: str
    new_type: str


@dataclass
class ImpactItem:
    column: str
    level: ImpactLevel
    detail: str
    referenced_in: list[str] = field(default_factory=list)
    old_type: Optional[str] = None
    new_type: Optional[str] = None


@dataclass
class ImpactReport:
    entity_name: str
    file_path: str
    matched_columns: list[ColumnMatch] = field(default_factory=list)
    impacts: list[ImpactItem] = field(default_factory=list)
    error: Optional[str] = None
    skipped_reason: Optional[str] = None

    @property
    def has_blockers(self) -> bool:
        return any(i.level == ImpactLevel.BLOCKS_IMPORT for i in self.impacts)

    @property
    def has_warnings(self) -> bool:
        return any(
            i.level in (ImpactLevel.BREAKS_TRANSFORM, ImpactLevel.WARNING)
            for i in self.impacts
        )

    @property
    def has_opportunities(self) -> bool:
        return any(i.level == ImpactLevel.OPPORTUNITY for i in self.impacts)
```

```python
# ConfigRefCollector — part of compatibility.py

class ConfigRefCollector:
    """Collect all column references from import.yml + transform.yml."""

    def collect(
        self, entity_name: str, import_config: dict, transform_config: list[dict]
    ) -> dict[str, list[tuple[str, ImpactLevel]]]:
        """Return {column_name: [(reference_path, impact_level), ...]}."""
        refs: dict[str, list[tuple[str, ImpactLevel]]] = {}
        self._collect_import_refs(entity_name, import_config, refs)
        self._collect_transform_refs(entity_name, transform_config, refs)
        return refs
```

**What `_collect_import_refs` scans** (all `BLOCKS_IMPORT` level):
- `entities.datasets.{name}.schema.id_field`
- `entities.datasets.{name}.schema.fields[].name`
- `entities.datasets.{name}.links[].field` and `.target_field`
- `entities.references.{name}.hierarchy.levels[].column`
- `entities.references.{name}.connector.extraction.id_column`
- `entities.references.{name}.connector.extraction.name_column`
- `entities.references.{name}.connector.extraction.levels[].column`
- `entities.references.{name}.connector.extraction.additional_columns`

**What `_collect_transform_refs` scans** (all `BREAKS_TRANSFORM` level):

Column attribution is **entity-aware** — each relation field references a column in a specific entity:
- `sources[].relation.key` → column in the **data** entity (`sources[].data`)
- `sources[].relation.ref_key` / `.ref_field` → column in the **grouping** entity (`sources[].grouping`)
- `sources[].relation.fields` values → columns in the **grouping** entity

So when checking entity `occurrences` (a dataset):
- Scan groups where `sources[].data == "occurrences"` → collect `relation.key` (e.g. `id_taxonref`)
- Do NOT collect `relation.ref_key` from those same sources (it belongs to the grouping entity)

When checking entity `taxons` (a reference):
- Scan groups where `sources[].grouping == "taxons"` → collect `relation.ref_key` (e.g. `taxons_id`), `relation.fields` values (e.g. `parent_id`, `lft`, `rght`)
- Do NOT collect `relation.key` from those same sources (it belongs to the data entity)

**Tests**: `tests/core/services/test_compatibility.py::TestConfigRefCollector`
- [ ] Collects all import.yml column references for a dataset entity
- [ ] Collects all import.yml column references for a reference entity (hierarchy + extraction)
- [ ] Collects transform.yml relation keys for the correct entity
- [ ] Handles missing import.yml gracefully (empty refs)
- [ ] Handles missing transform.yml gracefully (empty refs)
- [ ] Collects `relation.fields` mapping values (e.g. `parent_id`, `lft`, `rght`) as column references
- [ ] Attributes `relation.key` to the data entity (not the grouping entity)
- [ ] Attributes `relation.ref_key`/`ref_field`/`fields` to the grouping entity (not the data entity)
- [ ] Does not scan transform.yml params (V2 scope)

**Success criteria**: Given a real `import.yml` + `transform.yml` from `test-instance/niamoto-test/config/`, produce a complete reference map for `occurrences`.

---

### Phase 2: Core Service — CSV Schema Reader + Entity Resolver

**CSV Schema Reader** — reuses `GenericImporter._read_csv` logic:

```python
# CSVSchemaReader — part of compatibility.py

class CSVSchemaReader:
    """Read CSV headers + sample, extract column names and coarse types."""

    def read_schema(self, file_path: Path) -> tuple[list[dict], Optional[str]]:
        """Return (fields: [{"name": str, "type": str}], error: Optional[str]).

        Types align with engine.py _dtype_to_string: integer, float, boolean, datetime, string.
        Reuses GenericImporter._read_csv for separator/encoding detection.
        """
```

Key implementation detail: call `GenericImporter._read_csv(str(file_path), nrows=100)` to get a DataFrame, then iterate `df.dtypes` using the same `_dtype_to_string` mapping from `engine.py` (lines 777-786).

**Entity Resolver** — conservative exact-match:

```python
# EntityResolver — part of compatibility.py

class EntityResolver:
    """Match uploaded filename to entity via import.yml connector.path."""

    def resolve(self, filename: str, import_config: dict) -> Optional[str]:
        """Return entity_name if exact basename match, None otherwise."""
```

Iterates over `import_config["entities"]["datasets"]` and `["references"]`, compares `Path(connector["path"]).name == filename`. If exactly one match → return entity name. If multiple matches (duplicate basename) → log a warning and return None (avoid silent false positive on the wrong entity). If no match → return None.

**Tests**: `tests/core/services/test_compatibility.py::TestCSVSchemaReader`
- [ ] Reads a simple CSV and returns correct column names and types
- [ ] Handles semicolon separator (European CSV)
- [ ] Handles latin-1 encoding
- [ ] Returns error string for corrupt/unreadable file
- [ ] Returns error string for empty file (0 bytes)
- [ ] Returns columns with "string" types for header-only file (0 data rows — pandas infers `object`, mapped to `"string"` by `_dtype_to_string`)

**Tests**: `tests/core/services/test_compatibility.py::TestEntityResolver`
- [ ] Matches exact filename to dataset entity
- [ ] Matches exact filename to reference entity
- [ ] Returns None for non-matching filename
- [ ] Returns None for empty import config
- [ ] Skips DERIVED connector entities (no path to match)
- [ ] Returns None and logs warning when multiple entities share the same basename (avoids false positive)

---

### Phase 3: Core Service — Impact Analyzer (orchestrator)

The main `CompatibilityService` that orchestrates everything:

```python
# CompatibilityService — main orchestrator in compatibility.py

class CompatibilityService:
    """Pre-import impact check: analyze new CSV against existing pipeline config."""

    def __init__(self, working_directory: Path):
        self.working_directory = Path(working_directory)
        self._resolver = EntityResolver()
        self._collector = ConfigRefCollector()
        self._reader = CSVSchemaReader()

    def resolve_entity(self, filename: str) -> Optional[str]:
        """Resolve filename to entity name via import.yml."""
        import_config = self._load_import_config()
        return self._resolver.resolve(filename, import_config)

    def check_compatibility(self, entity_name: str, file_path: str) -> ImpactReport:
        """Run full impact check for an entity against a new file."""
```

**`check_compatibility` flow** (called with a validated file path and a known FILE/DUCKDB_CSV entity):
1. Resolve file path relative to working directory (security: reject paths outside project)
2. Load import.yml + transform.yml configs
3. Read new CSV schema via `CSVSchemaReader`
4. Load existing schema from EntityRegistry `config["schema"]["fields"]` (opened with `read_only=True` to avoid contention with concurrent GUI operations)
5. Collect config references via `ConfigRefCollector`
6. Compare: for each referenced column, check if it exists in new schema → if not, create `ImpactItem` with appropriate level
7. Compare types: for matched columns, check if type changed → create `WARNING` items
8. Detect new columns: columns in new file not in config references or old schema → `OPPORTUNITY` items
9. Return `ImpactReport`

`check_compatibility` does NOT handle connector-type skipping — it assumes the caller has already filtered. This avoids the ambiguity of validating a file path that may not exist for non-file connectors.

**`check_all` for CLI**:
```python
    def check_all(self, entity_filter: Optional[str] = None) -> list[ImpactReport]:
        """Check all entities (or one) from import.yml against their source files."""
```

`check_all` short-circuits skipped connectors **before** calling `check_compatibility`:
1. Load import.yml, iterate entities (filtered by `entity_filter` if set)
2. For each entity, read `connector.type`:
   - DERIVED → append skipped report ("Derived from {source} — check {source} instead")
   - API/PLUGIN → append skipped report ("External connector — cannot check locally")
   - VECTOR/FILE_MULTI_FEATURE → append skipped report ("Not supported in V1")
   - FILE/DUCKDB_CSV → resolve `connector.path`, call `check_compatibility(entity_name, path)`
3. Return all reports

**Tests**: `tests/core/services/test_compatibility.py::TestCompatibilityService`
- [ ] Produces correct ImpactReport for a CSV with all columns present (no issues)
- [ ] Detects missing column referenced in import.yml → BLOCKS_IMPORT
- [ ] Detects missing column referenced in transform.yml relation → BREAKS_TRANSFORM
- [ ] Detects type change on existing column → WARNING
- [ ] Detects new columns → OPPORTUNITY
- [ ] Skips DERIVED entities with appropriate skipped_reason
- [ ] Skips VECTOR entities (V2 scope)
- [ ] Skips FILE_MULTI_FEATURE entities (V2 scope)
- [ ] Skips API/PLUGIN entities with appropriate skipped_reason
- [ ] Returns error report for unreadable file
- [ ] Returns empty report when no config exists (first import)
- [ ] Path validation: rejects paths outside working directory

**Integration test**: `tests/core/services/test_compatibility_integration.py`
- [ ] Run against `test-instance/niamoto-test/` with a modified CSV (removed column, added column, changed type)

---

### Phase 4: CLI Command

Add `check` subcommand to the `import` group in `src/niamoto/cli/commands/imports.py`:

```python
# src/niamoto/cli/commands/imports.py — add after existing commands

@import_commands.command(name="check")
@click.option("--entity", "-e", default=None, help="Check a specific entity only")
@error_handler(log=True, raise_error=True)
def import_check(entity: str | None) -> None:
    """Check compatibility between source files and current configuration."""
    set_progress_mode(use_progress_bar=True)
    config = Config()
    project_root = Path(config.config_dir).parent  # config_dir = .../config/, parent = project root
    service = CompatibilityService(project_root)
    reports = service.check_all(entity_filter=entity)
    _print_impact_reports(reports)
    # Exit code 1 if any blockers or warnings
    if any(r.has_blockers or r.has_warnings for r in reports):
        raise SystemExit(1)
```

`_print_impact_reports` uses Click's `click.style()` for color-coded output:
- Red: BLOCKS_IMPORT items
- Yellow/orange: BREAKS_TRANSFORM items
- Yellow: WARNING items
- Cyan: OPPORTUNITY items
- Green: entity with no issues
- Gray: skipped entities (DERIVED, etc.)

**Tests**: `tests/cli/commands/test_imports.py` (extend existing)
- [ ] `niamoto import check` runs without error on test instance
- [ ] `niamoto import check --entity occurrences` checks single entity
- [ ] Exit code 0 when no issues
- [ ] Exit code 1 when issues found

---

### Phase 5: API Endpoint

Single endpoint in `src/niamoto/gui/api/routers/imports.py` — resolves entity internally then runs check. Simpler frontend orchestration (one call instead of two):

```python
# Pydantic models — add to imports.py

class ImpactCheckRequest(BaseModel):
    file_path: str  # relative to project root, e.g. "imports/occurrences.csv"

class ImpactItemResponse(BaseModel):
    column: str
    level: str  # ImpactLevel value
    detail: str
    referenced_in: list[str]
    old_type: Optional[str] = None
    new_type: Optional[str] = None

class ColumnMatchResponse(BaseModel):
    name: str
    old_type: str
    new_type: str

class ImpactCheckResponse(BaseModel):
    # Entity resolution result
    entity_name: Optional[str] = None  # None if no match
    # Impact report (only present if entity matched)
    matched_columns: list[ColumnMatchResponse] = []
    impacts: list[ImpactItemResponse] = []
    error: Optional[str] = None
    skipped_reason: Optional[str] = None
    has_blockers: bool = False
    has_warnings: bool = False
    has_opportunities: bool = False
```

**`POST /api/imports/impact-check`**:
```python
@router.post("/impact-check", response_model=ImpactCheckResponse)
async def impact_check(request: ImpactCheckRequest):
    work_dir = get_working_directory()
    # Path validation FIRST — reject paths outside project before any processing
    resolved = (work_dir / request.file_path).resolve()
    if not resolved.is_relative_to(work_dir.resolve()):
        raise HTTPException(status_code=400, detail="Path outside project directory")
    service = CompatibilityService(work_dir)
    filename = Path(request.file_path).name
    entity_name = service.resolve_entity(filename)
    if entity_name is None:
        return ImpactCheckResponse()  # no match, all defaults
    report = service.check_compatibility(entity_name, request.file_path)
    return ImpactCheckResponse(
        entity_name=report.entity_name,
        matched_columns=[...],
        impacts=[...],
        error=report.error,
        skipped_reason=report.skipped_reason,
        has_blockers=report.has_blockers,
        has_warnings=report.has_warnings,
        has_opportunities=report.has_opportunities,
    )
```

**Tests**: `tests/gui/api/routers/test_imports_compatibility.py`
- [ ] POST `/impact-check` resolves entity and returns ImpactReport for known file
- [ ] POST `/impact-check` returns empty response (entity_name=null) for unknown file
- [ ] POST `/impact-check` handles missing entity gracefully
- [ ] POST `/impact-check` rejects paths outside project with 400 (security — validated before any processing)
- [ ] POST `/impact-check` returns entity_name=null when filename does not match any FILE/DUCKDB_CSV entity

---

### Phase 6: Frontend — CompatibilityPanel + ImportWizard Integration

#### 6a. API Client

**`src/niamoto/gui/ui/src/features/import/api/compatibility.ts`**:

```typescript
import { apiClient } from '@/shared/lib/api/client';

export interface ImpactItem {
  column: string;
  level: 'blocks_import' | 'breaks_transform' | 'warning' | 'opportunity';
  detail: string;
  referenced_in: string[];
  old_type?: string;
  new_type?: string;
}

export interface ImpactCheckResult {
  entity_name: string | null;
  matched_columns: { name: string; old_type: string; new_type: string }[];
  impacts: ImpactItem[];
  error?: string;
  skipped_reason?: string;
  has_blockers: boolean;
  has_warnings: boolean;
  has_opportunities: boolean;
}

export async function impactCheck(filePath: string): Promise<ImpactCheckResult> {
  const { data } = await apiClient.post('/imports/impact-check', { file_path: filePath });
  return data;
}
```

#### 6b. Hook

**`src/niamoto/gui/ui/src/features/import/hooks/useCompatibilityCheck.ts`**:

React Query mutation hook. After upload completes:
1. For each uploaded file, call `impactCheck(filePath)` — single API call per file
2. Backend resolves entity internally and runs check
3. Filter results: only keep reports where `entity_name` is not null (matched files)
4. Return `{ matched: ImpactCheckResult[], unmatched: string[] }`

#### 6c. CompatibilityPanel Component

**`src/niamoto/gui/ui/src/features/import/components/CompatibilityPanel.tsx`**:

- Receives `reports: ImpactCheckResult[]` as prop (same type defined in `compatibility.ts`)
- Groups impacts by level (blockers first, then breaks, then warnings, then opportunities)
- Color scheme: red / orange / yellow / blue
- Each impact shows: column name, detail text, where it's referenced
- Matched columns shown as a collapsed summary ("12 columns OK")
- No DERIVED entities shown in UI (they have no source file to upload — DERIVED skips are only relevant in CLI's `check_all`)
- Actions: **"Continue anyway"** button + **"Fix data"** link (back to upload)

#### 6d. ImportWizard Integration

**`src/niamoto/gui/ui/src/features/import/components/ImportWizard.tsx`**:

**Critical flow decision**: The compatibility check runs **BEFORE** auto-configure, not after. Auto-configure generates a new config from the uploaded files, so checking after would compare the file against its own freshly-generated config (meaningless). The check only makes sense against the **pre-existing** config.

**New flow for re-upload scenario** (existing entities detected):
```
upload complete
  → POST /impact-check for each file (single call per file)
  → files where entity_name != null: have impact reports → phase 'checking' → CompatibilityPanel
  → files where entity_name == null: queued for auto-configure
  → user clicks "Continue anyway"
  → proceed to auto-configure (phase 'configuring') for all files → 'reviewing'
```

**New flow for first-time upload** (no match):
```
upload complete
  → POST /impact-check returns entity_name=null for all files
  → skip check entirely
  → proceed to auto-configure (phase 'configuring') → 'reviewing' (unchanged)
```

Implementation steps:
1. Add `'checking'` to `ImportPhase` type union
2. After upload completes (`handleFilesReady`), call the compatibility check hook **before** calling `runAutoConfigure`
3. Hook calls `POST /impact-check` for each uploaded file (single API call per file, backend resolves entity internally)
4. If any results have `entity_name` != null → set phase to `'checking'`, render CompatibilityPanel
5. If all results have `entity_name` == null → skip directly to `runAutoConfigure` (existing flow)
6. "Continue anyway" → proceed to `runAutoConfigure` then `'configuring'` → `'reviewing'`
7. "Fix data" → keep uploaded files in state, return to upload zone so user can replace specific files (do NOT reset everything with `resetToIdle()`)

**Multi-file behavior**: When some files match entities and others don't:
- CompatibilityPanel shows one report per matched file
- Unmatched files are listed separately ("New files — will be auto-configured")
- "Continue anyway" proceeds with ALL files (matched + unmatched)

**Loading state**: While `/impact-check` calls are in progress, show a "Checking compatibility..." message with spinner (similar to `configuring` phase animation).

**Error handling**: If `/impact-check` API calls fail, silently skip the check and proceed to auto-configure (non-blocking philosophy).

**DB access**: CompatibilityService opens EntityRegistry in `read_only=True` mode to avoid contention with concurrent operations in the long-running FastAPI process.

**UI acceptance criteria**:
- [ ] Panel appears automatically after re-upload when entity is recognized
- [ ] Panel does NOT appear on first-time upload (no existing config)
- [ ] Check runs BEFORE auto-configure, not after
- [ ] Impact items are grouped and color-coded by severity
- [ ] Matched columns shown collapsed
- [ ] "Continue anyway" proceeds to auto-configure then review/import flow
- [ ] "Fix data" returns to upload zone (keeps file list, does not reset everything)
- [ ] DERIVED entities never appear in UI (no file to match — only shown in CLI `check_all`)
- [ ] Multi-file: shows reports for matched files, lists unmatched files separately
- [ ] Loading spinner shown while checking
- [ ] API errors silently skip the check (non-blocking)

---

## Acceptance Criteria

### Functional

- [ ] `niamoto import check` CLI command works and reports impact for all entities
- [ ] `niamoto import check --entity occurrences` works for single entity
- [ ] CLI exit code 0 when clean, 1 when issues found
- [ ] `POST /api/imports/impact-check` resolves entity + returns ImpactReport JSON in one call
- [ ] ImportWizard shows CompatibilityPanel after re-upload with impact data
- [ ] DERIVED entities: skipped with info message in CLI `check_all`, not surfaced in UI (no file to match)
- [ ] First import (no config) does not show panel
- [ ] Missing columns classified as BLOCKS_IMPORT or BREAKS_TRANSFORM
- [ ] Type changes classified as WARNING
- [ ] New columns classified as OPPORTUNITY
- [ ] Non-blocking: user can always proceed to import

### Non-Functional

- [ ] Check completes in < 2 seconds for typical CSV (< 50 columns, < 100k rows sampled)
- [ ] No hardcoded entity or field names (genericity rule)
- [ ] Path validation rejects files outside project directory
- [ ] CSV reading uses same logic as engine.py (no check/import divergence)

### Quality Gates

- [ ] Unit tests for ConfigRefCollector, CSVSchemaReader, EntityResolver, CompatibilityService
- [ ] Integration test against test-instance config
- [ ] API endpoint tests
- [ ] `uvx ruff check src/` passes
- [ ] `uvx ruff format src/` passes
- [ ] `uv run pytest` passes
- [ ] `cd src/niamoto/gui/ui && pnpm build` passes (required for any GUI work)

## Dependencies & Risks

| Risk | Mitigation |
|------|------------|
| `_read_csv` is not easily callable from outside engine.py (may be tightly coupled) | Extract separator/encoding detection into a shared utility, or call `_read_csv` as a static method |
| transform.yml `params` contains column references not covered by V1 | Documented as V2 scope — V1 checks relation keys only |
| EntityRegistry may not have `schema.fields` for old imports (pre-feature) | Fall back to empty old schema — all columns show as "new" |
| YAML `!include` directives in config files | V1 limitation: parse raw YAML only, document the gap |

## V2 Roadmap (out of scope)

Three independent workstreams, ordered by priority:

### Critical guardrails

- Keep V2 logic in the **preflight compatibility service**, not in the import
  runtime. Extending `CompatibilityService` is acceptable; pushing V2 logic into
  `GenericImporter` or normal import execution paths is not.
- Do **not** deliver V2 as one large milestone or PR. Ship `V2a`, `V2b`, and
  `V2c` independently to contain risk and keep regressions attributable.
- Avoid heuristic "magic" in reference detection. If a plugin param is treated as
  a column reference, that contract must be explicit in plugin metadata or a
  dedicated hook.
- Prefer additive extension points over more branching in the core service:
  new `RefsProvider`s, new `SchemaReader`s, and a small reader/provider registry.

### V2a: Extensible reference coverage (highest priority)

Closes the main logic gap — transform.yml `params` column references are not checked.
This is the **highest complexity / fragility risk** in V2 because it increases
coupling with the plugin ecosystem.

1. **Plugin-aware param scanning** via explicit contract: each plugin's Pydantic
   `config_model` declares which fields are column references (metadata on fields
   or a `collect_column_refs(config)` hook). No heuristic name scanning.
   Leverage existing `config_model` in `base.py` and per-plugin models like
   `stats_loader.py`.
2. Refactor collectors into composable providers:
   - `ImportRefsProvider` (already implemented)
   - `TransformRelationRefsProvider` (already implemented)
   - `PluginParamRefsProvider` (new)
3. Keep plugin-aware scanning read-only and preflight-only. It must not require
   loading or executing transformer/widget logic to determine references.

### V2b: Extensible schema readers

Moderate risk if isolated behind a reader interface; high risk if implemented as
special cases scattered through the core service.

1. **GPKGSchemaReader** — native schema from SQLite metadata (`pragma table_info`)
2. **MultiFeatureSchemaReader** — check each source file, aggregate sub-reports
3. Reader selection by connector type (registry pattern)

For the first bounded delivery of this track, see:
`docs/plans/2026-03-30-feat-pre-import-impact-check-gpkg-v2g1-plan.md`

### V2c: Resolver UX

Low technical risk. Keep the resolver conservative: exact-match resolution plus
explicit disambiguation UI.

1. **Disambiguation UI** — dropdown when multiple entities share the same filename
2. No fuzzy/stem matching (too risky for false positives)

### Future (V3+)

- Impact severity based on downstream widget usage (requires solid reference
  coverage first)

## References

- **Brainstorm**: `docs/brainstorms/2026-03-30-data-compatibility-check-brainstorm.md`
- **Import engine**: `src/niamoto/core/imports/engine.py` (CSV reading: lines 506-558, type mapping: lines 777-786, metadata: lines 576-607)
- **EntityRegistry**: `src/niamoto/core/imports/registry.py` (EntityMetadata: line 23, config JSON structure)
- **Import config models**: `src/niamoto/core/imports/config_models.py` (ConnectorConfig: line 43, LinkConfig: line 215, ExtractionConfig: line 133)
- **Transform config models**: `src/niamoto/common/transform_config_models.py` (TransformRelationConfig: line 10, TransformSourceConfig: line 22)
- **CLI imports group**: `src/niamoto/cli/commands/imports.py` (Click group: line 26)
- **API imports router**: `src/niamoto/gui/api/routers/imports.py` (router registration in app.py: line 86)
- **ImportWizard**: `src/niamoto/gui/ui/src/features/import/components/ImportWizard.tsx` (phases: line 39, upload flow: line 477)
- **Service pattern**: `src/niamoto/core/services/importer.py` (constructor: lines 37-41)
- **API context**: `src/niamoto/gui/api/context.py` (`get_working_directory()`)
