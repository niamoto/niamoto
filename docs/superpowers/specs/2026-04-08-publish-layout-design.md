# Publish Layout Redesign

## Goal

Redesign the GUI `Publish` module so that:

- publication actions remain visible without excessive page scrolling
- the generated-site preview behaves as an autonomous workspace
- nested scrolling conflicts between the page and the preview are removed
- desktop and mobile layouts remain intentional rather than being scaled versions of the same page

The redesign must preserve the current publish capabilities:

- generate the site
- inspect build status and freshness
- deploy to configured platforms
- access recent history
- preview the generated site across devices

## Problem Summary

The current page stacks too many cards vertically. This creates two issues:

1. The user must scroll the parent page to reach actions and status information.
2. The preview lives inside the same long page, so interactions around scrolling feel unstable. When the preview itself needs scrolling, the parent page can also move, which makes the preview feel unreliable.

The current layout treats the preview as one card among others. The redesign will instead treat it as a primary workspace next to the publish controls.

## Chosen Direction

### Desktop

Use a two-column fixed-height layout:

- left column: actions and operational state
- right column: generated-site preview

Each column scrolls independently. The page itself should not become a long scrolling document in normal desktop use.

### Tablet and Mobile

Use a mode switch:

- `Actions`
- `Preview`

Default to `Actions`.

This avoids forcing a cramped two-column layout on smaller screens while still making the preview easy to access.

## Rejected Alternatives

### Single-column page with sticky header

Rejected because it keeps the preview embedded in a long parent page. The scroll conflict remains, only slightly reduced.

### Preview in a modal or drawer

Rejected because the preview becomes secondary and detached from the publish workflow. The user explicitly wants both actions and preview to matter.

## Information Architecture

### Desktop Left Column

The left column is the operational panel. It should remain compact and action-oriented.

Keep:

- site generation block
- publication/deployment block
- recent history summary

Reduce:

- decorative or repetitive metrics that do not affect a decision
- large cards that restate status already visible elsewhere

The left column should answer:

- Can I generate now?
- Is the output up to date?
- Can I deploy now?
- What happened recently?

### Desktop Right Column

The right column is the preview workspace.

Keep:

- device switcher
- refresh action
- open in browser action
- preview viewport

The preview viewport should take the remaining height of the column and behave like an isolated surface. The iframe scroll stays inside the iframe.

### Tablet and Mobile

The page becomes a two-mode screen:

- `Actions`: generation, deploy, compact history
- `Preview`: preview toolbar plus viewport

The user enters the page on `Actions`, because that is the operational default.

## Component Design

### `PublishOverview`

Refactor from a vertically stacked card page into a responsive shell with:

- desktop two-column layout
- mobile/tablet segmented switch

The component remains the page coordinator and keeps existing hooks/stores.

### Left-Column Sections

Reuse the existing build/deploy/history content, but reorganize it into compact sections rather than full-width cards that assume a vertical page.

History becomes a short recent summary, not the complete history page.

### `StaticSitePreview`

Keep it as the preview surface, but embed it inside a container that:

- owns the right-column height
- keeps its toolbar visible
- isolates scroll behavior from the parent page

The preview frame should not force the outer page to grow taller than the viewport on desktop.

## Interaction Rules

### Desktop

- The whole publish page fills the available module height.
- The parent page does not become the main scrolling context.
- Left column scrolls only if its own content overflows.
- Right column scrolls only inside its own preview area.
- Interacting with the preview must not scroll the left column or the page shell.

### Tablet and Mobile

- The `Actions / Preview` switch changes the main content area.
- `Actions` opens by default.
- Each mode has its own content height and scrolling context.

## State and Data Flow

No backend changes are required.

Existing data sources remain:

- publish store for build/deploy jobs
- pipeline status for freshness
- site config hooks for preview metadata and languages

The redesign is a presentation-layer change only. It should not alter build/deploy semantics or API contracts.

## Error Handling

Existing errors remain visible inside the relevant section:

- build errors in the generation area
- deploy errors in the deployment area
- preview load issues inside the preview container

The redesign must avoid hiding preview errors below the fold. On desktop, preview errors should remain visible inside the right column without requiring page scrolling.

## Accessibility and Motion

- Keyboard navigation must still reach all actions in logical order.
- The `Actions / Preview` switch on smaller screens must be keyboard operable and screen-reader labeled.
- Desktop split layout must preserve focus visibility in both columns.
- No new decorative motion is required for this redesign.

## Testing

### Manual

- Desktop: no long parent-page scrolling in normal use
- Desktop: preview scroll stays inside iframe/preview area
- Desktop: generation/deploy actions remain visible while preview is present
- Tablet/mobile: `Actions` opens by default
- Tablet/mobile: switching to `Preview` shows the full preview workspace
- Preview toolbar actions still work

### Automated

At minimum:

- frontend build passes

If layout logic is extracted into small helpers or mode-selection functions, add focused unit tests for that logic.

## Implementation Notes

- Prefer reusing current section components over rewriting the publish workflow.
- Keep the refactor scoped to the `Publish` feature and shared preview primitives only if strictly necessary.
- Avoid introducing new global layout patterns unless they clearly benefit other modules too.

## Out of Scope

- changing publish APIs
- changing build/deploy job semantics
- redesigning the separate full history view
- redesigning site preview internals beyond layout containment
