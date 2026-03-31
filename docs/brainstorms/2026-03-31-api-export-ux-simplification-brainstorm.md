# API Export UX Simplification

**Date**: 2026-03-31
**Status**: Ready for planning
**Scope**: Simplify the API export configuration for non-technical users (botanists, ecologists)
**Builds on**: `2026-03-30-api-export-gui-brainstorm.md` (initial API tab implementation)

## What We're Building

A UX overhaul of the API export tab in GroupPanel to make it accessible to non-technical users (field botanists, ecologists) while preserving full power for advanced users.

The current implementation exposes all configuration options in a single long scrollable card per export target — data source, pass-through toggle, field mappings with source/generator modes, Darwin Core mapping with 20+ generators, JSON overrides, transformer params. This is overwhelming for a botanist who just wants to publish their data.

## Why This Approach

The hybrid **Wizard + Cards with progressive disclosure** approach was chosen because:

- **Different intents need different UIs**: Adding a new export format is a guided, one-time decision (→ wizard). Editing an existing export is a targeted, repeat action (→ compact card with collapsible sections).
- **Multiple formats per group**: A group can have both a simple JSON export and a DwC export. The card-based list naturally supports this.
- **Progressive disclosure over hiding**: Non-technical users see summaries and can stop there. Power users unfold sections to access everything. Nothing is removed.

Alternatives considered:
- **Presets only** (no wizard) — rejected because activating a preset still dumps the user into the full form
- **Wizard only** — rejected because editing an existing export via a wizard is cumbersome for power users
- **Separate simple/advanced modes** — rejected because it fragments the interface and requires maintaining two UIs

## Key Decisions

### 1. Card-based list view (default state of API tab)

Each export target configured for the group is shown as a **compact card**:
- Header: target name, active/inactive badge, on/off toggle
- Summary: one sentence in natural language describing what the export does (e.g., "Export JSON simple — toutes les données transformées. 127 taxons.")
- Collapsible sections as chips, organized in two tiers:
  - **Main sections** (visible): Index fields, Detail fields, DwC mapping (when applicable)
  - **Advanced options** (dimmed): JSON overrides, data source, transformer params
- Save/Cancel buttons appear only when the card has unsaved changes (dirty state)
- A **"+ Add an export format"** button at the bottom launches the wizard

### 2. Wizard for adding a new format

Triggered by the "+" button. Three steps:

**Step 1 — Type**:
- "Existing targets" section: targets already defined in export.yml but not yet activated for this group. One click activates with defaults → skip to step 3.
- "Create a new format" section: three options:
  - **Simple JSON export** — pass-through, minimal config
  - **Darwin Core (GBIF)** — pre-filled DwC mapping with smart defaults
  - **Manual configuration** — full form (current UI, within wizard context)

**Step 2 — Content** (varies by type):
- *Simple*: target name + optional index field selection from suggestions
- *Darwin Core*: target name + pre-filled mapping with readable summary ("23 terms auto-mapped"). User can adjust if needed.
- *Manual*: target name + full form

**Step 3 — Confirm**: Natural language summary of what will be created/activated. "Create export" button.

The wizard is a modal dialog or inline panel replacing the list view temporarily. Cancellable at any point.

### 3. Contextual help and domain vocabulary

The most impactful change for the botanist is the **language used** throughout.

**Relabeled fields** (technical → domain):
| Current | Proposed |
|---------|----------|
| pass_through | Exporter toutes les données transformées |
| Detail JSON fields | Contenu de chaque fiche individuelle |
| Index JSON fields | Quelles infos apparaissent dans la liste |
| JSON overrides | Options de format avancées |
| data_source | Source de données |
| transformer_params | Paramètres du traitement |

**Inline help** at the top of each opened section:
- Index fields: "Ces champs seront visibles dans le fichier `all_taxon.json` — la liste de tous vos taxons."
- Detail fields: "Chaque taxon aura un fichier JSON individuel avec ces données."
- DwC mapping: "Le standard Darwin Core permet de partager vos données avec GBIF et d'autres réseaux de biodiversité."

**Status badges** on collapsed sections showing current config without expanding:
- "Toutes les données (pass-through)" or "5 champs sélectionnés"
- "23 termes mappés" for DwC
- "par défaut" when nothing has been customized

### 4. API Settings page (global params)

Same treatment as group cards:
- Readable summary at the top of each target card ("Exporte vers `/api/data/`, 2 groupes actifs")
- Collapsible sections: "Output directory" (always visible, essential), "JSON options" (collapsed), "Error handling" (collapsed), "Metadata" (collapsed)
- Rarely-used sections visually dimmed
- No wizard here — this page is for users who know what they're doing
- Bidirectional links: group card → "View global settings", API Settings → list of groups using each target

## UI Structure

```
GroupPanel > API tab
├── Export Card 1 (e.g., json_api)
│   ├── Header: name + badge + toggle
│   ├── Summary: "Export JSON simple — toutes les données transformées"
│   ├── Collapsible chips:
│   │   ├── [main] Champs de l'index (badge: "3 champs")
│   │   ├── [main] Fiches détail (badge: "pass-through")
│   │   └── [dimmed] Options avancées
│   └── [if dirty] Save / Cancel
│
├── Export Card 2 (e.g., dwc_export)
│   ├── Header: name + badge + toggle
│   ├── Summary: "Darwin Core (GBIF) — 23 termes mappés"
│   ├── Collapsible chips:
│   │   ├── [main] Mapping Darwin Core (badge: "23 termes")
│   │   ├── [main] Champs de l'index
│   │   └── [dimmed] Options avancées
│   └── [if dirty] Save / Cancel
│
└── [+ Ajouter un format d'export]
        └── Opens wizard (modal/inline)

Wizard flow:
Step 1: Type  ──→  Step 2: Content  ──→  Step 3: Confirm
 ├ Existing target → activate → skip to 3
 ├ Simple JSON → name + index fields
 ├ Darwin Core → name + pre-filled mapping
 └ Manual → name + full form
```

## Components Impact

| Component | Change |
|-----------|--------|
| `ApiExportsTab.tsx` (442 lines) | Major refactor → card list + wizard trigger |
| `ApiExportGroupCard` (inline) | Extract to own file, redesign as compact card with collapsible sections |
| `ApiSettingsPanel.tsx` (206 lines) | Add summaries, collapsible sections |
| `ApiFieldMappingsEditor.tsx` (358 lines) | Keep as-is, used inside expanded sections |
| `DwcMappingEditor.tsx` (447 lines) | Keep as-is, used inside expanded sections |
| `JsonSchemaForm.tsx` (689 lines) | Keep as-is, used in advanced sections |
| New: `AddExportWizard.tsx` | Wizard component (3 steps) |
| New: `ExportCard.tsx` | Compact card with summary + collapsible sections |
| i18n `sources.json` (en + fr) | Add wizard labels, update existing labels to domain vocabulary |

## Backend Impact

Minimal. The existing endpoints support all needed operations:
- `GET /api/config/export/api-targets` — list targets (wizard step 1: existing targets)
- `PUT /api/config/export/api-targets/{name}/groups/{group}` — activate/configure (wizard completion)
- `GET /api/config/export/api-targets/{name}/groups/{group}/suggestions` — field suggestions (wizard step 2)

**One potential addition**: a `POST /api/config/export/api-targets` endpoint to create a brand new target from the wizard (currently targets must exist in export.yml). This could also be handled by writing to export.yml directly from the existing update infrastructure.

## Open Questions

1. **Wizard as modal or inline panel?** Modal is simpler to implement and clearly separates the creation flow. Inline feels more integrated but requires managing two states in the same view.
2. **Should the wizard pre-create the target in export.yml on step 3, or only when the user first saves?** Pre-creating is simpler but adds entries even if the user never configures them.
3. **How to generate the natural language summary?** Static templates per export type, or dynamic from the actual config? Static is simpler and more predictable.

## Scope

**In scope:**
- Card-based list view with summaries and collapsible sections
- Wizard for adding exports (activate existing + create new)
- Relabeled fields and inline help
- Status badges on collapsed sections
- API Settings page improvements
- i18n updates (en + fr)

**Out of scope (future):**
- Visual preview of JSON output
- Drag-and-drop reordering of exports
- Export validation/test run from the GUI
- Preset templates beyond Simple/DwC/Manual
