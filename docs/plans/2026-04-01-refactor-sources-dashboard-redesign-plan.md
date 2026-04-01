---
title: "refactor: Redesign sources overview as a data readiness dashboard"
type: refactor
date: 2026-04-01
brainstorm: docs/brainstorms/2026-04-01-sources-dashboard-redesign-brainstorm.md
---

# refactor: Redesign sources overview as a data readiness dashboard

## Overview

Replace the oversized mission-card layout on `/sources` with a compact, sidebar-based readiness dashboard. The sidebar becomes always-visible (like Collections and Site), navigation items are added above the data tree, and the content panel uses compact metric cards + structured lists instead of large mission cards.

## Problem Statement

The current `/sources` overview is visually heavy: three large mission cards dominate the viewport, collections appear twice, raw datasets are buried at the bottom, and the sidebar is hidden on the overview. This breaks consistency with the recently refactored Collections and Site modules and presents a misleading quality framing.

## Proposed Solution

Adopt the sidebar + content pattern already established in Collections and Site. Add 4 navigation items to the sidebar (Overview, Import, Verification, Enrichment). Replace the 3 mission cards with 3 compact stat cards. Replace the collection overview and supporting sources with structured lists ordered by data hierarchy: datasets first, then layers, then references, then a one-line collection summary.

## Technical Approach

### Architecture

The redesign touches the `features/import/` feature directory. No backend changes are required. Most data comes from existing hooks (`useDatasets`, `useReferences`) plus the existing `/api/stats/summary` endpoint, which also remains the source of truth for imported layers and lightweight structural alerts.

**Key files to modify:**

| File | Change | Lines |
|------|--------|-------|
| `DataModule.tsx` | Always show sidebar, expand selection types, add routes | ~230 |
| `DataTree.tsx` | Add navigation items above accordion, add Overview button | ~207 |
| `ImportDashboard.tsx` | Complete rewrite → new `SourcesOverview.tsx` | ~996 |
| `navigationStore.ts` | Add route labels for `/sources/verification`, `/sources/enrichment` | ~184 |

**New files:**

| File | Purpose |
|------|---------|
| `SourcesOverview.tsx` | New overview with metrics + structured lists |
| `VerificationView.tsx` | Dedicated view for the 4 analysis tools |
| `EnrichmentView.tsx` | Dedicated view listing enrichable references |
| `SourceRow.tsx` | Reusable row component for datasets/references/layers |
| `MetricCard.tsx` | Compact stat card (may reuse/adapt Collections `CounterBox`) |

**Files to delete after migration:**

| File | Reason |
|------|--------|
| `ImportDashboard.tsx` | Replaced by `SourcesOverview.tsx` |
| `SupportingSourceCard.tsx` | Replaced by `SourceRow.tsx` inline rows |
| `AggregationGroupCard.tsx` | Already unused |
| `AnalysisToolSheet.tsx` | Analysis tools move to `VerificationView.tsx` |
| `DashboardConfigEditorSheet.tsx` | Can be deleted once its loading/error/sheet shell is either reused or fully absorbed by `SourcesOverview` |

### Implementation Phases

#### Phase 1: Sidebar always visible + navigation items

**Goal**: Get the sidebar showing on the overview with the 4 new navigation items. No content changes yet.

**Tasks:**

- [ ] **Expand `DataSelection` type** in `DataTree.tsx`
  ```typescript
  export type DataSelection =
    | { type: 'overview' }
    | { type: 'verification' }
    | { type: 'enrichment' }
    | { type: 'dataset'; name: string }
    | { type: 'reference'; name: string }
    | { type: 'import' }
  ```

- [ ] **Update `DataModule.tsx`** — Remove `showSidebar` conditional
  - Current: `const showSidebar = selection.type !== 'overview'` → Remove this
  - Always wrap content in `ModuleLayout` with `DataTree` as sidebar
  - Add `selectionFromLocation` cases for `/sources/verification` and `/sources/enrichment`
  - Add `handleSelect` navigate cases for new types
  - Update breadcrumb `useEffect` to handle new selection types
  - Add non-blank temporary `renderContent()` cases for `verification` and `enrichment` until the dedicated views are implemented, so direct URLs and sidebar clicks never land on empty content

- [ ] **Update `DataTree.tsx`** — Add navigation items above accordion
  - Add "Overview" button at top (following `CollectionsTree` pattern: icon `LayoutDashboard`, highlight when `selection.type === 'overview'`)
  - Add "Import data" button (icon `Upload`)
  - Add "Verification" button (icon `ShieldCheck`)
  - Add "Enrichment" button (icon `Sparkles`)
  - Add separator (`<div className="mx-4 my-2 h-px bg-border" />`) between nav items and data tree
  - Move import from accordion section to nav item
  - Keep Datasets and References accordion sections as-is
  - **Empty state behavior**: When no data is imported, hide or disable "Verification" and "Enrichment" nav items (only show Overview + Import)

- [ ] **Update `navigationStore.ts`** — Add route labels
  ```typescript
  '/sources/verification': 'Verification',
  '/sources/enrichment': 'Enrichment',
  ```

- [ ] **Verify** sidebar appears on `/sources` overview, all 4 nav items highlight correctly, URL sync works bidirectionally

#### Phase 2: New overview content (metrics + lists)

**Goal**: Replace `ImportDashboard` with the new `SourcesOverview` component.

**Tasks:**

- [ ] **Create `MetricCard.tsx`** — Compact stat card component
  - Props: `{ value: number | string; label: string; sublabel?: string; onClick?: () => void; variant?: 'default' | 'success' | 'warning' }`
  - Style: Adapt `CounterBox` from Collections — `bg-muted/50 p-3 rounded-lg text-center`, large bold number, small label below
  - Clickable cards get `cursor-pointer hover:bg-muted/70` + ring on focus

- [ ] **Create `SourceRow.tsx`** — Reusable row for any data source
  - Props: `{ icon: LucideIcon; name: string; typeBadge: string; metrics: string; statusBadge?: { label: string; variant: string }; actions: { label: string; icon?: LucideIcon; onClick: () => void }[]; onNameClick?: () => void }`
  - Layout: `flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-muted/30 border border-transparent hover:border-border/50`
  - Name is a button when clickable (navigates to detail)
  - Actions rendered as ghost buttons at the right end

- [ ] **Create `SourcesOverview.tsx`** — Main overview component
  - Props: same as current `ImportDashboard` props + `onOpenVerification`, `onOpenEnrichment`
  - Fetch `ImportSummary` from `/api/stats/summary` (reuse existing pattern from `ImportDashboard.fetchSummary`)
  - **Layer extraction**: Filter `ImportSummary.entities` by `entity_type` — datasets vs layers are distinguished by this field
  - **Refresh button**: Refetch `/api/stats/summary` + invalidate `useDatasets` and `useReferences` tanstack-query caches (same as current `ImportDashboard` behavior)
  - **Re-import button**: Navigate to `/sources/import` (same as today)
  - **Non-empty gating**: The overview should render when any dataset, reference, or layer is present. Do not keep the current `datasets.length > 0 || references.length > 0` gate unchanged.
  - Layout (vertical `space-y-6`):
    1. **Header**: Title "Imported data" + `[Refresh]` `[Re-import]` buttons
    2. **Metric cards row** (`grid grid-cols-3 gap-3`):
       - Card 1: total rows / "across N sources"
       - Card 2: known alerts count / "none detected" or "N detected" / clickable → `onOpenVerification()`
       - Card 3: enrichment count / "N available" or "N configured" / clickable → `onOpenEnrichment()`
    3. **Caption**: `<p className="text-xs text-muted-foreground">` — disclaimer about structural signals
    4. **Section "Datasets"**: header with badge count + `SourceRow` per dataset. Actions: Explore (→ dataset detail or Data Explorer, matching current product behavior), Config (→ opens config editor Sheet), Update (→ re-import workflow, not a new file-picker workflow)
    5. **Section "Layers"** (if any layers exist): header with badge count + `SourceRow` per layer. Actions: Update (→ re-import workflow, same scope as current `SupportingSourceCard` behavior)
    6. **Section "References"**: header with badge count + `SourceRow` per reference with status badge. Actions depend on status: Configure enrichment (→ opens `EnrichmentWorkspaceSheet` inline), Open collection (→ navigate to `/groups/:name`), Review (→ navigate to detail)
    7. **Section "Collections"** (compact): one-line summary + "Open Collections" link
  - Section headers: `<h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">` + badge count
  - **Config editing**: Dataset `[Config]` action opens a Sheet containing `EntityConfigEditor`. Reuse the loading/error/sheet behavior already encapsulated by `DashboardConfigEditorSheet` or absorb that behavior explicitly before deleting it.
  - **Dual interaction on references**: Inline `[Configure]` button opens `EnrichmentWorkspaceSheet` as overlay (not navigating to the enrichment view). This preserves the brainstorm's dual pattern: sidebar → full view, inline button → contextual sheet.

- [ ] **Compute reference status badges** — Implement priority logic
  - Priority order: `structural_alert` > `enrichment_available` > `enrichment_configured` > `imported`
  - Derive from: `ImportSummary.alerts` for structural alerts, `reference.can_enrich` + `reference.enrichment_enabled` for enrichment state, default to `imported`
  - Badge variants: `destructive` for alerts, `default` for enrichment available, `secondary` for enrichment configured, `outline` for imported

- [ ] **Wire into `DataModule.tsx`** — Replace `ImportDashboard` with `SourcesOverview` in `renderContent()`
  - Pass `onOpenVerification={() => handleSelect({ type: 'verification' })}` etc.

- [ ] **Preserve empty state** — When no data imported, render `SourcesEmptyState` as today
  - Update the "has data" condition so imported layers also prevent the empty state from rendering

- [ ] **Add i18n keys** in `sources` namespace (EN + FR) for new labels

**Phase ordering note**: Do not ship or merge a state where `/sources/verification` or `/sources/enrichment` render blank content. Either keep the Phase 1 placeholders until Phase 3 lands, or wire the metric-card navigation only once the dedicated views exist.

#### Phase 3: Verification and Enrichment dedicated views

**Goal**: Create the two new content views accessible from the sidebar.

**Tasks:**

- [ ] **Create `VerificationView.tsx`** — Dedicated verification workspace
  - Layout: title + description + 4 tool selector buttons (tabs or cards) + selected tool content below
  - Reuse existing components: `DataCompletenessView`, `ValueValidationView`, `TaxonomicConsistencyView`, `GeoCoverageView`
  - These components are currently rendered inside `AnalysisToolSheet` — extract them to render directly in the content panel
  - Tool selector: 4 buttons in a row, active one highlighted (`bg-primary/10 text-primary`)
  - Pass `entities` prop from parent datasets/references for completeness and validation views
  - Disclaimer text under title: "These tools are diagnostics, not a single global quality score."
  - Audit the reused views for hardcoded copy and move that text into the `sources` namespace where needed. "Reuse" here means preserving behavior and layout where practical, not forbidding targeted i18n cleanup.

- [ ] **Create `EnrichmentView.tsx`** — Dedicated enrichment workspace
  - Fetch references via `useReferences()`
  - Filter to enrichable references
  - Each enrichable reference = a card with: name, kind, entity count, enrichment status, "Configure" button
  - "Configure" button opens existing `EnrichmentWorkspaceSheet` as sheet overlay (same component, same pattern)
  - On `EnrichmentWorkspaceSheet` save, invalidate `references` and refresh the overview summary so badges and metric cards stay in sync
  - Non-enrichable references listed below as "No enrichment available for: plots, shapes"

- [ ] **Wire into `DataModule.tsx`** — Add cases in `renderContent()`
  ```typescript
  case 'verification': return <VerificationView ... />
  case 'enrichment': return <EnrichmentView ... />
  ```

- [ ] **Update sidebar badge behavior** (optional, from open questions)
  - If structural alerts > 0: show amber dot next to "Verification" in sidebar
  - If enrichment available: show blue dot next to "Enrichment" in sidebar

#### Phase 4: Cleanup and polish

**Goal**: Remove deprecated components, verify consistency, add missing i18n.

**Tasks:**

- [ ] **Delete deprecated components**: `ImportDashboard.tsx`, `SupportingSourceCard.tsx`, `AggregationGroupCard.tsx`, `AnalysisToolSheet.tsx`
- [ ] **Delete `DashboardConfigEditorSheet.tsx` only if fully replaced** by an equivalent shell in `SourcesOverview`
- [ ] **Remove unused imports** across modified files
- [ ] **Verify all routes** work with browser back/forward and direct URL access
- [ ] **Verify empty state** displays correctly when no data imported
- [ ] **Verify layers-only instances** render the overview and do not fall back to `SourcesEmptyState`
- [ ] **Verify sidebar highlight** matches current selection on all routes
- [ ] **Test with all 5 themes** — neutral, field, herbarium, laboratory, forest
- [ ] **Test responsive behavior** — sidebar collapses at narrow viewports via existing `useResponsiveSidebar()`
- [ ] **Run frontend lint**: `cd src/niamoto/gui/ui && pnpm lint`
- [ ] **Run frontend build**: `cd src/niamoto/gui/ui && pnpm build`
- [ ] **Run frontend tests**: `cd src/niamoto/gui/ui && pnpm test`
- [ ] **Run targeted Python tests only if backend-adjacent code was touched**

## Acceptance Criteria

### Functional Requirements

- [ ] Sidebar is visible on the `/sources` overview (no longer hidden)
- [ ] 4 navigation items (Overview, Import, Verification, Enrichment) appear above the data tree in the sidebar
- [ ] Overview shows 3 compact metric cards (rows, alerts, enrichment)
- [ ] Overview lists datasets first, then layers, then references in structured rows
- [ ] Each reference row shows a contextual status badge with the correct priority
- [ ] Collections summary is a one-line compact section with a link to `/groups`
- [ ] Clicking "Verification" in sidebar navigates to `/sources/verification` and shows the 4 analysis tools
- [ ] Clicking "Enrichment" in sidebar navigates to `/sources/enrichment` and lists enrichable references
- [ ] Inline "Configure" button on a reference row opens `EnrichmentWorkspaceSheet` as an overlay
- [ ] Empty state (`SourcesEmptyState`) still renders when no data is imported
- [ ] Browser back/forward and direct URL access work for all routes
- [ ] Breadcrumbs update correctly for all selection types
- [ ] A workspace containing only imported layers still renders the overview, not the empty state

### Non-Functional Requirements

- [ ] No new backend endpoints needed
- [ ] Existing analysis view components reused with only targeted adaptations required for i18n, copy cleanup, or embedding outside the old sheet
- [ ] All text uses `sources` i18n namespace with EN + FR translations
- [ ] Frontend builds without warnings (`pnpm build`)
- [ ] Frontend lint and tests pass (`pnpm lint`, `pnpm test`)
- [ ] Consistent with Collections and Site visual patterns

## Dependencies & Risks

**No blocking backend dependencies.** All required endpoints and layout primitives exist.

**Risk: ImportDashboard complexity.** The current file is ~996 lines with interleaved state for sheets, config editing, and analysis tools. The rewrite should NOT try to preserve all of this — the new components each own their specific concern.

**Risk: Sheet overlay stacking.** The enrichment sheet currently opens from the dashboard. In the new design it opens from both `SourcesOverview` (inline button) and `EnrichmentView` (dedicated view). Ensure the sheet portal renders correctly in both contexts.

**Risk: Layers-only edge case.** The current Data module decides whether to show `SourcesEmptyState` using datasets + references only. The redesign introduces layers into the overview source model, so the empty-state gate must be updated deliberately.

**Risk: Action scope drift.** The current "Update" action is effectively a path back into the re-import workflow, not a dedicated contextual file-replacement UI. Keep that scope explicit unless a separate product decision expands it.

## References

### Internal

- Brainstorm: `docs/brainstorms/2026-04-01-sources-dashboard-redesign-brainstorm.md`
- Collections module (reference pattern): `src/niamoto/gui/ui/src/features/collections/`
- Site module sidebar pattern: `src/niamoto/gui/ui/src/features/site/components/UnifiedSiteTree.tsx`
- Current Data module: `src/niamoto/gui/ui/src/features/import/module/DataModule.tsx`
- ModuleLayout: `src/niamoto/gui/ui/src/components/layout/ModuleLayout.tsx`
- Navigation store: `src/niamoto/gui/ui/src/stores/navigationStore.ts`

### Patterns to Follow

- `DataSelection` discriminated union (same as `CollectionsSelection`)
- Bidirectional URL sync via `selectionFromLocation()` + `handleSelect()` + `useEffect`
- Breadcrumb via `useNavigationStore` setter in `useEffect` with cleanup
- Highlight: `bg-primary/10 text-primary` for active, `hover:bg-muted/50` for inactive
- Stat cards: adapt `CounterBox` from CollectionsOverview (`bg-muted/50 p-2 text-center`)
- i18n: `useTranslation(['sources', 'common'])`
