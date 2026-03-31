---
title: "feat: Simplify API export UX for non-technical users"
type: feat
date: 2026-03-31
brainstorm: docs/brainstorms/2026-03-31-api-export-ux-simplification-brainstorm.md
---

# feat: Simplify API export UX for non-technical users

## Overview

Refactor the API export tab in GroupPanel to make it accessible to field botanists and ecologists, while preserving full power for advanced users. Replace the current single long scrollable card with a **card-based list** (compact summaries + collapsible sections) and add a **wizard dialog** for creating/activating exports.

## Problem Statement

The current API export tab exposes all configuration at once: data source, pass-through toggle, field mappings with source/generator modes, Darwin Core mapping with 20+ generators, JSON overrides, and transformer params. A botanist who just wants to publish data sees the same interface as a developer fine-tuning JSON output.

## Proposed Solution

Two-mode UX based on user intent:

- **Adding a format** → 3-step wizard in a Dialog modal (type → content → confirm)
- **Editing an existing format** → compact card with natural language summary + collapsible sections

Key design decisions (from brainstorm):
- **Dialog modal** for wizard — consistent with `AddSourceDialog`, `AddWidgetModal`
- **`enabled: false` flag** instead of deleting group data on toggle OFF — prevents accidental data loss
- **Wizard supports both** activating existing targets AND creating new ones
- **i18n templates** for natural language summaries — no dynamic generation

## Technical Approach

### Phase 1: Backend — `enabled: false` behavior + create target endpoint

**Files:**
- `src/niamoto/gui/api/routers/config.py` (lines 2186-2202)
- `src/niamoto/core/plugins/exporters/json_api_exporter.py`

**1.1 — Change toggle OFF behavior**

Currently `update_api_export_group_config` removes the group entry from export.yml when `enabled=false`. Change to keep the entry with `enabled: false` flag.

```python
# config.py — update_api_export_group_config
# BEFORE (line 2196-2202): removes group from target["groups"]
# AFTER: set enabled=false on the group entry, keep all params
```

Update `json_api_exporter.py` to skip groups with `enabled: false` during export execution.

Update `GroupConfig` Pydantic model to add `enabled: bool = True`.

**1.1b — Wire up `data_source` in the exporter (Codex P1)**

`JsonApiExporter._fetch_group_data()` currently hard-codes `table_name = group_name` and ignores the `data_source` override saved via the UI. Fix the exporter to use `group_config.data_source` when present, falling back to `group_name`. Without this fix the data-source field in the advanced section is a no-op — users save a config the exporter silently ignores.

**1.2 — POST endpoint for creating new targets**

```
POST /api/config/export/api-targets
Body: { name: string, template: "simple" | "dwc" | "manual", params?: {} }
```

- Validates name: `^[a-z][a-z0-9_]{2,30}$`
- Checks uniqueness against existing targets
- Creates entry in export.yml with sensible defaults per template:
  - `simple`: `json_api_exporter` with `pass_through: true`
  - `dwc`: `json_api_exporter` with `transformer_plugin: niamoto_to_dwc_occurrence` + default mapping
  - `manual`: bare `json_api_exporter` with empty groups
- Returns created target summary

**1.3 — Update list endpoint to include `enabled` per group**

`GET /api/config/export/api-targets` already returns `group_names[]`. Extend to return `groups: [{ group_by, enabled }]` so the frontend can distinguish active vs disabled groups.

### Phase 2: ExportCard component

**New file:** `src/niamoto/gui/ui/src/features/groups/components/api/ExportCard.tsx`

Extract and redesign `ApiExportGroupCard` (currently inline in `ApiExportsTab.tsx:58-385`) as a standalone component.

**Structure:**
```
ExportCard
├── Header: target name + Badge (active/inactive/modified) + Switch toggle
├── Summary: i18n template with interpolated values (entity count, field count, format)
├── Collapsible sections (Accordion):
│   ├── [main] Index fields → ApiFieldMappingsEditor
│   ├── [main] Detail / pass-through → toggle + field selector
│   ├── [main] DwC mapping → DwcMappingEditor (conditional)
│   └── [dimmed] Advanced options → data source, JSON overrides, transformer params
├── Inline help banner at top of each expanded section
└── Save / Cancel (visible only when isDirty)
```

**Summary generation** — i18n templates in `sources.json`:
```json
"exportSummary": {
  "simplePassThrough": "Simple JSON export — all transformed data. {{count}} {{entityName}}.",
  "simpleFields": "JSON export — {{fieldCount}} selected fields. {{count}} {{entityName}}.",
  "dwc": "Darwin Core (GBIF) — {{termCount}} mapped terms. {{count}} {{entityName}}.",
  "disabled": "This export is disabled for this group."
}
```

**Section badges** on collapsed Accordion items showing config state:
- "pass-through" or "{{n}} fields" for detail section
- "{{n}} terms" for DwC mapping
- "default" when nothing customized

**Reuse:** `ApiFieldMappingsEditor`, `DwcMappingEditor`, `JsonSchemaForm` used as-is inside sections.

**JsonSchemaForm reset fix (Codex P2):** `JsonSchemaForm` only hydrates its internal `formData` on first mount. When the user clicks Reset, passing new `initialValues` does not actually reset the visible inputs — the form re-emits stale pre-reset values. Fix: add a `key={resetCounter}` prop on `JsonSchemaForm` to force remount on reset. Apply this in both `ExportCard` (transformer params) and `ApiSettingsPanel` (global params).

### Phase 3: AddExportWizard component

**New file:** `src/niamoto/gui/ui/src/features/groups/components/api/AddExportWizard.tsx`

Dialog modal with 3 steps. Uses local state for wizard progression, no server calls until step 3 confirm.

**Step 1 — Type selection:**
```
┌─────────────────────────────────────────────┐
│  Add an export format                    ✕  │
│                                             │
│  ● ━━━━━ ○ ━━━━━ ○                         │
│  Type     Content   Confirm                 │
│                                             │
│  EXISTING TARGETS (not yet active)          │
│  ┌─ stats_api ─────────────────────────┐    │
│  │  Existing JSON export — activate    │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  CREATE A NEW FORMAT                        │
│  ┌─ Simple JSON export ───────────────┐    │
│  │  Publish transformed data as-is     │    │
│  ├─ Darwin Core (GBIF) ──────────────┤    │
│  │  International biodiversity standard│    │
│  ├─ Manual configuration ────────────┤    │
│  │  Full control over fields & format  │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  [Cancel]                      [Next →]     │
└─────────────────────────────────────────────┘
```

- "Existing targets" section: filter `useApiExportTargets()` to exclude targets already active for this `groupBy`. If empty, hide section.
- Clicking an existing target → activate with defaults → skip to step 3.
- Clicking "create new" option → proceed to step 2.

**Step 2 — Content (varies by template):**

| Template | Fields shown |
|----------|-------------|
| Simple | Target name input + optional index field selection (from suggestions) |
| DwC | Target name input + pre-filled mapping summary ("23 terms auto-mapped") + optional adjustment |
| Manual | Target name input + full form (reuse current `ApiExportGroupCard` internals) |

- Target name validation: `^[a-z][a-z0-9_]{2,30}$`, check uniqueness client-side against loaded targets
- For DwC: call `_default_dwc_transformer_params()` logic to pre-fill (already exists in backend)

**Step 3 — Confirm:**

Natural language summary of what will be created. Two actions depending on flow:
- Existing target: `PUT /api-targets/{name}/groups/{groupBy}` with `enabled: true`
- New target: `POST /api-targets` then `PUT .../groups/{groupBy}`

On success: close dialog, invalidate queries, toast confirmation.

**Stepper UI:** Custom 3-dot stepper (no shadcn stepper component exists). Simple flexbox with numbered circles + connecting lines, similar to pattern in `AddWidgetModal.tsx`.

### Phase 4: ApiExportsTab refactor

**File:** `src/niamoto/gui/ui/src/features/groups/components/api/ApiExportsTab.tsx` (442 lines → major refactor)

Replace the current single-card-per-target layout with:

```tsx
function ApiExportsTab({ groupBy }: { groupBy: string }) {
  const { data: targets } = useApiExportTargets()
  const [wizardOpen, setWizardOpen] = useState(false)

  // Filter targets that have this group (active OR enabled:false)
  const groupTargets = targets?.filter(t =>
    t.groups.some(g => g.group_by === groupBy)
  )

  return (
    <div className="space-y-4">
      {/* Description */}
      <p className="text-sm text-muted-foreground">
        {t('groupPanel.api.description', { groupBy })}
      </p>

      {/* Export cards */}
      {groupTargets?.map(target => (
        <ExportCard
          key={target.name}
          exportName={target.name}
          groupBy={groupBy}
        />
      ))}

      {/* Empty state */}
      {groupTargets?.length === 0 && (
        <EmptyState onAdd={() => setWizardOpen(true)} />
      )}

      {/* Add button */}
      <AddExportButton onClick={() => setWizardOpen(true)} />

      {/* Wizard dialog */}
      <AddExportWizard
        open={wizardOpen}
        onOpenChange={setWizardOpen}
        groupBy={groupBy}
      />
    </div>
  )
}
```

**Dirty state protection:** Add `useBlocker` from react-router-dom to warn before navigation when any card has unsaved changes. Also add `window.beforeunload` listener.

### Phase 5: API Settings improvements

**File:** `src/niamoto/gui/ui/src/features/groups/components/api/ApiSettingsPanel.tsx` (206 lines)

Apply same treatment to `ApiTargetSettingsCard`:
- Add summary line: "Exports to `/api/data/`, {{n}} active groups"
- Wrap `JsonSchemaForm` sections in `Accordion` with clear labels:
  - "Output directory" (always expanded — essential field)
  - "JSON options" (collapsed)
  - "Error handling" (collapsed, dimmed)
  - "Metadata" (collapsed, dimmed)
- Add list of groups using this target with links back to GroupPanel

### Phase 6: i18n + domain vocabulary

**Files:**
- `src/niamoto/gui/ui/src/i18n/locales/en/sources.json`
- `src/niamoto/gui/ui/src/i18n/locales/fr/sources.json`

**6.1 — New wizard keys:**
```json
"wizard": {
  "title": "Add an export format",
  "stepType": "Type",
  "stepContent": "Content",
  "stepConfirm": "Confirm",
  "existingTargets": "Existing targets (not yet active for this group)",
  "createNew": "Create a new format",
  "simpleTitle": "Simple JSON export",
  "simpleDescription": "Publish all your transformed data as-is",
  "dwcTitle": "Darwin Core (GBIF)",
  "dwcDescription": "International biodiversity data sharing standard",
  "manualTitle": "Manual configuration",
  "manualDescription": "Full control over fields and format",
  "targetName": "Export name",
  "targetNamePlaceholder": "my_export",
  "targetNameHelp": "Lowercase letters, numbers and underscores only",
  "confirmSummary": "This will create a {{format}} export for the \"{{groupBy}}\" group.",
  "create": "Create export",
  "activate": "Activate"
}
```

**6.2 — Relabel existing keys (domain vocabulary):**

| Current key | Current label (en) | New label (en) |
|---|---|---|
| `passThrough` | `Export all transformed data` | `Export all data as-is` |
| `detailFields` | `Detail JSON fields` | `Individual record content` |
| `indexFields` | `Index JSON fields` | `Fields shown in the listing` |
| `jsonOverrides` | `Per-group JSON overrides` | `Advanced format options` |
| `dataSource` | `Data source` | `Data source` (keep) |
| `transformerParams` | `Transformer parameters` | `Processing settings` |

**6.3 — Inline help messages:**
```json
"sectionHelp": {
  "indexFields": "These fields appear in the {{fileName}} file — the listing of all your {{entityName}}.",
  "detailFields": "Each {{entityName}} gets its own JSON file with this data.",
  "dwcMapping": "Darwin Core is the international standard for sharing biodiversity data with GBIF and other networks.",
  "advancedOptions": "JSON formatting, data source override, and other technical settings."
}
```

**6.4 — Translate hardcoded strings in `ApiFieldMappingsEditor.tsx`:**

Replace all hardcoded English strings ("Output field", "Mode", "Source field", etc.) with i18n keys. Add missing `aria-label` attributes on reorder buttons (copy pattern from `DwcMappingEditor.tsx`).

### Phase 7: Polish

- **Accessibility:** Add `aria-label` to reorder buttons in `ApiFieldMappingsEditor` (missing, present in `DwcMappingEditor`)
- **Error messages:** Catch Pydantic 400 errors in mutations and display user-friendly messages instead of raw validation errors
- **Empty states:** Design empty state for first-visit (no exports configured) with clear CTA pointing to wizard

## Acceptance Criteria

### Functional Requirements

- [ ] API tab shows compact cards with natural language summary for each configured export
- [ ] Cards have collapsible sections organized in two tiers (main + advanced dimmed)
- [ ] Status badges on collapsed sections show current config without expanding
- [ ] Wizard (Dialog modal) allows adding exports: activate existing OR create new (simple/DwC/manual)
- [ ] Wizard validates target name uniqueness and format
- [ ] Toggle OFF sets `enabled: false` instead of deleting group data
- [ ] Toggle OFF → ON restores previous configuration
- [ ] Dirty state warning when navigating away with unsaved changes
- [ ] API Settings page has summaries and collapsible sections
- [ ] Bidirectional links between group cards and API Settings
- [ ] All UI labels use domain vocabulary (not technical jargon)
- [ ] Inline help at top of each expanded section
- [ ] All strings in i18n (en + fr), including ApiFieldMappingsEditor
- [ ] `data_source` override is wired in `json_api_exporter.py` (not a no-op)
- [ ] `JsonSchemaForm` correctly resets visible inputs when Reset is clicked (key-based remount)

### Non-Functional Requirements

- [ ] No regression on existing save/load/toggle functionality
- [ ] Existing `ApiFieldMappingsEditor` and `DwcMappingEditor` work correctly inside Accordion sections
- [ ] `JsonSchemaForm` works correctly in advanced options section

## Dependencies & Risks

| Risk | Mitigation |
|------|-----------|
| `enabled: false` flag changes export pipeline behavior | Update `json_api_exporter.py` to skip disabled groups; add test |
| Wizard POST endpoint adds write path to export.yml | Reuse existing `_save_export_config` with backup; validate via `ExportConfigModel` |
| Dirty state `useBlocker` may conflict with GroupsModule URL sync | Test navigation between groups, tabs, and sidebar with dirty state |
| Accordion inside Card may have z-index/overflow issues with existing editors | Test `DwcMappingEditor` (tall component) inside Accordion; may need `overflow-visible` |
| `data_source` field is a no-op in the exporter (Codex P1) | Wire up `data_source` in `_fetch_group_data()` before exposing it in the new UI |
| `JsonSchemaForm` doesn't reset on prop change (Codex P2) | Use `key={resetCounter}` to force remount on Reset; applies to ExportCard + ApiSettingsPanel |

## Implementation Order

| Phase | Effort | Dependencies |
|-------|--------|-------------|
| Phase 1: Backend changes | Small | None |
| Phase 6.4: Translate ApiFieldMappingsEditor | Small | None |
| Phase 2: ExportCard component | Medium | Phase 1 (enabled flag) |
| Phase 3: AddExportWizard | Medium | Phase 1 (POST endpoint) |
| Phase 4: ApiExportsTab refactor | Medium | Phase 2 + 3 |
| Phase 5: API Settings improvements | Small | None (independent) |
| Phase 6.1-6.3: i18n wizard + relabeling | Small | Phase 3 + 4 |
| Phase 7: Polish | Small | All |

Phases 1, 5, and 6.4 can run in parallel. Phases 2 and 3 can run in parallel after Phase 1.

## References

### Internal

- Brainstorm: `docs/brainstorms/2026-03-31-api-export-ux-simplification-brainstorm.md`
- Original API tab brainstorm: `docs/brainstorms/2026-03-30-api-export-gui-brainstorm.md`
- Current API tab: `src/niamoto/gui/ui/src/features/groups/components/api/ApiExportsTab.tsx`
- Wizard pattern: `src/niamoto/gui/ui/src/features/groups/components/sources/AddSourceDialog.tsx`
- Accordion pattern: `src/niamoto/gui/ui/src/components/index-config/DisplayFieldEditorPanel.tsx:187-570`
- Dirty state pattern: `src/niamoto/gui/ui/src/features/groups/components/api/ApiExportsTab.tsx:74-131`
- Backend endpoints: `src/niamoto/gui/api/routers/config.py:2065-2298`
- Plugin models: `src/niamoto/core/plugins/exporters/json_api_exporter.py`
