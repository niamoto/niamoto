# Sources Dashboard Redesign

**Date:** 2026-04-01
**Status:** Brainstorm validated
**Module:** Data (`/sources`)

## Context

The Data module overview (`/sources`) is the post-import landing page. After recent UX revamps of the Collections and Site modules, the Sources page now feels visually heavy, structurally inconsistent, and too ambitious in what it implies about data quality.

### Current problems

1. **Hierarchy inversion** — Raw datasets are buried late in the page, while derived collections dominate the first screen
2. **Redundancy** — Collections appear twice: in the "Prepare static pages" mission card and again in the "Collections overview" section
3. **Oversized mission cards** — Three large cards consume much of the viewport for information that could be summarized more compactly
4. **Missing sidebar in overview** — The Data module breaks the layout consistency already established in Collections and Site
5. **Misleading quality framing** — The overview currently suggests a broad "health" judgment, while the real checks are tool-specific and not synthesized into a reliable global score
6. **Layers are easy to forget** — Imported spatial layers still matter operationally, but they disappear from the redesign if the overview only focuses on datasets and references

## What We're Building

A redesigned `/sources` overview that functions as a **data readiness dashboard**: at a glance, the botanist sees what was imported, whether any **known structural alerts** need attention, and what useful next steps are available. The layout adopts the same sidebar + content pattern as Collections and Site.

This overview does **not** claim that the data is globally "good" or "validated". Detailed checks remain available in dedicated verification tools.

### Key user stories

- "I just imported data. Did the expected sources arrive?"
- "Is there anything clearly blocking me before I continue?"
- "Which verification tool should I run next?"
- "Where can I configure enrichment for my taxonomy?"
- "How do I inspect the raw datasets and imported layers?"

## Design

### Layout: Sidebar + Content

The sidebar (`DataTree`) is **always visible**, including on the overview page. Today it only appears when navigating to a dataset or reference detail; now it stays permanent, matching Collections and Site.

```
┌─────────────────────────────────────────────────────────────┐
│ Sidebar (resizable)  │  Content panel (scrollable)          │
│                      │                                      │
│  Navigation items    │  Header + Metrics + Lists            │
│  ──────────────      │                                      │
│  Data tree           │                                      │
└──────────────────────┴──────────────────────────────────────┘
```

### Sidebar structure

Inspired by the Site module sidebar pattern: lightweight navigation items above, data tree below.

```
┌──────────────────────────┐
│  ◉ Overview              │  ← Dashboard view (default)
│  ↑ Import data           │  ← Import wizard
│  🛡 Verification          │  ← Dedicated verification view
│  ✦ Enrichment            │  ← Dedicated enrichment view
│──────────────────────────│
│  Datasets  1             │
│    occurrences     1000  │
│  References  3           │
│    plots    generic   22 │
│    taxons   hier.     35 │
│    shapes   spatial   22 │
└──────────────────────────┘
```

**Navigation behavior:**
- **Overview**: Default selection. Shows the readiness dashboard in the content panel
- **Import data**: Opens the import wizard
- **Verification**: Dedicated content view with the 4 existing analysis tools
- **Enrichment**: Dedicated content view listing enrichable references with their current configuration status
- **Data tree items**: Clicking a dataset or reference loads its detail panel

**Dual interaction pattern:**
- Sidebar click → **full view** in the content panel
- Inline button in a row → **contextual action**, either direct navigation or a sheet overlay when the action is reference-specific

Imported layers remain visible in the overview content, even though this redesign does not add a new dedicated layer detail route.

### Content panel: Overview (default view)

#### Header

```
Imported data                                    [Refresh] [Re-import]
```

Minimal header: title + action buttons. No subtitle paragraph.

#### Metric cards (3 compact cards in a row)

```
┌──────────────┐  ┌─────────────────┐  ┌─────────────────┐
│    1,057     │  │        0        │  │       1         │
│    rows      │  │  known alerts   │  │  enrichment     │
│  across 4    │  │  none detected  │  │   available     │
│  sources     │  │                 │  │                 │
└──────────────┘  └─────────────────┘  └─────────────────┘
```

**Card 1 — Rows imported**: Total row count across imported datasets, references, and layers. Shows source count below.

**Card 2 — Known alerts**: Lightweight structural alerts only, for example empty imported tables or other import-level blockers surfaced automatically by the backend. This card must **not** say "All good" or imply comprehensive validation. Clickable → opens Verification view.

**Card 3 — Enrichment opportunities**: "N available" or "N configured". Clickable → opens Enrichment view.

Small caption below the cards:

> Detailed checks live in Verification. The overview only summarizes automatically computed structural signals.

Style: same compact proportions as the stat cards already used in Collections. Large number, small supporting label, no oversized mission-card layout.

#### Structured list: Raw sources

Raw sources are explicit again. Datasets and imported layers should not be hidden behind collection-oriented content.

##### Datasets

```
Datasets  1
─────────────────────────────────────────────────────────────
■ occurrences   Dataset   1,000 rows · 31 fields   [Explore] [Config] [Update]
```

Each dataset row:
- Database icon
- Name (clickable → detail view)
- Type badge (`Dataset`)
- Inline metrics: row count · field count
- Action buttons: Explore, Edit config, Update file

##### Layers

```
Layers  1
─────────────────────────────────────────────────────────────
▦ elevation   Layer   1 table · geometry detected   [Update]
```

Each layer row:
- Layer icon
- Name
- Type badge (`Layer`)
- Lightweight technical summary, for example geometry availability or imported feature count
- Action button: Update

No new detail panel is added for layers in this iteration.

#### Structured list: References

```
References  3
─────────────────────────────────────────────────────────────
🌿 plots     Generic       22 rows · 30 fields   Imported              [Open collection]
🌿 taxons    Hierarchical  35 rows · 11 fields   Enrichment available  [Configure]
🗺 shapes    Spatial       22 rows · 13 fields   Structural alert      [Review]
```

Each reference row:
- Kind-appropriate icon
- Name (clickable → detail view)
- Kind badge
- Inline metrics
- **Status badge** with a narrow meaning: either a blocking structural alert or the most useful next-step cue
- Primary action button, contextual to the current status

Recommended row statuses:
- `Structural alert`
- `Enrichment available`
- `Enrichment configured`
- `Imported`

Avoid labels such as `All good`, `Healthy`, or `Ready for pages`, which overstate what the product actually knows.

#### Collections summary (compact)

Collections still matter, but they already have a dedicated module.

```
Collections · 3 detected                              [Open Collections →]
  plots (imported) · taxons (enrichment available) · shapes (imported)
```

One-line summary with a link to `/groups`.

### Content panel: Verification view

When clicking `Verification` in the sidebar:

```
Verification tools
Run focused checks on imported data before building pages.

┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│ Field          │ │ Validation     │ │ Taxonomy       │ │ Spatial        │
│ availability   │ │                │ │ checks         │ │ coverage       │
└────────────────┘ └────────────────┘ └────────────────┘ └────────────────┘

[Selected tool content renders below]
```

The 4 existing analysis tools are shown as tabs or clickable cards:
- Field availability
- Value validation
- Taxonomy checks
- Spatial coverage

Important wording:

> These tools are diagnostics, not a single global quality score.

The verification view should help the user answer focused questions:
- Are important fields sparsely filled?
- Are some numeric values atypical?
- Is the taxonomic hierarchy coherent?
- Is geographic coverage analyzable?

### Content panel: Enrichment view

When clicking `Enrichment` in the sidebar:

```
API enrichment
Configure external enrichment for compatible references.

┌─────────────────────────────────────────────────────────────┐
│ taxons   Hierarchical  35 entities   ● Available            │
│ Enrich your taxonomy with external data (GBIF, POWO...)     │
│                                             [Configure →]   │
└─────────────────────────────────────────────────────────────┘

No other references currently support enrichment.
```

This view lists enrichable references and their current status. If configuration remains reference-specific, the existing `EnrichmentWorkspaceSheet` can still open as a sheet overlay from this view.

## Key Decisions

1. **Sidebar always visible** — Consistency with Collections and Site modules
2. **Overview is a readiness dashboard, not a quality score** — The screen summarizes what is imported and what needs attention, without pretending to certify the data
3. **Known alerts only** — The overview surfaces only lightweight structural signals that are automatically computed and easy to explain
4. **Verification remains tool-based** — Detailed diagnostics stay inside the dedicated verification tools
5. **No mission cards** — Status and actions are integrated into compact cards and rows
6. **Raw sources remain explicit** — Datasets and imported layers are visible in the overview, not buried under collection-oriented content
7. **Reference badges describe next action, not certification** — Status labels remain narrow and operational
8. **Collections stay compact** — One-line summary only, because the full workflow already lives in `/groups`

## Technical considerations

### URL routing

Routes needed to support sidebar navigation and deep-linking:

- `/sources` → Overview
- `/sources/verification` → Verification tools view
- `/sources/enrichment` → Enrichment view
- `/sources/dataset/:name` → Dataset detail
- `/sources/reference/:name` → Reference detail
- `/sources/import` → Import wizard

Browser back/forward should work naturally via URL-driven navigation.

### DataSelection type expansion

The current `DataSelection` union (`overview | dataset | reference | import`) must expand to include `verification` and `enrichment`. This affects URL routing, breadcrumbs, and sidebar highlight logic in [`DataModule.tsx`](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/import/module/DataModule.tsx).

### Empty state

When no data is imported, the existing `SourcesEmptyState` is preserved. The overview layout only renders when data exists.

The sidebar should still show:
- `Overview`
- `Import`

`Verification` and `Enrichment` can be hidden or disabled when empty.

### Signal types and wording

The redesign should distinguish three categories of signals:

1. **Structural alerts**
   - Automatically computed
   - Safe to summarize in the overview
   - Clear and directly actionable
   - Example: imported table is empty

2. **Verification diagnostics**
   - Produced by dedicated tools
   - Potentially nuanced or exploratory
   - Should stay inside Verification unless a later iteration persists and normalizes them
   - Examples: low completeness, numeric outliers, taxonomy duplicates, missing usable geometry

3. **Informational signals**
   - Not issues
   - Useful for orientation and planning
   - Examples: row counts, source counts, enrichment availability

### Status badge priority

When multiple statuses apply to a reference, use this priority order:

1. **Structural alert** — blocking signal, needs review
2. **Enrichment available** — useful next step
3. **Enrichment configured** — stateful progress cue
4. **Imported** — neutral default state

Only the highest-priority status is shown on the row.

### Metric cards data source

The overview cards should reuse the existing `/api/stats/summary` endpoint for lightweight aggregation.

Important limitation:

- The endpoint provides **limited automatic alerts**
- It does **not** justify a global `All good` or `Data quality OK` message
- Detailed verification remains on-demand

If a future iteration stores verification runs and their results, the overview could later show:
- `Last checked`
- `N findings`
- `Needs review since last import`

But that is explicitly outside the scope of this redesign.

### Raw sources scope

The overview must include datasets **and** imported layers so that spatial supporting data stays visible.

This iteration does **not** add:
- a dedicated layer detail route
- a separate layer verification workspace

### Sheet overlay from within dedicated views

If the user is already in the Enrichment full view and clicks `Configure` on a reference row, the `EnrichmentWorkspaceSheet` may still open as a sheet overlay on top of that view. The sheet remains contextual to a specific reference.

## What We're NOT Building

- No global data quality score
- No `All good` wording derived only from `/api/stats/summary`
- No synthetic cross-tool issue counter unless verification results are later persisted and normalized
- No changes to the dataset or reference detail panels
- No changes to the import wizard
- No dedicated layer detail route in this iteration

## Open Questions

1. Should verification results remain purely on-demand, or should the app persist the last run and surface a timestamp in the overview?
2. Should the sidebar navigation items show badges, for example a red dot on `Verification` when structural alerts exist, or a blue dot on `Enrichment` when enrichment is available?
3. Should imported layers eventually get a dedicated detail route, or is overview visibility sufficient for now?
