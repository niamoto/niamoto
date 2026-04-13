---
title: Make Collections widget editing responsive on low-power hardware
type: refactor
date: 2026-04-12
status: active
---

# Make Collections widget editing responsive on low-power hardware

## Overview

The `Collections` page currently feels almost instant on a high-end machine, but becomes slow enough on low-power hardware to hurt the whole desktop app. The problem is not a single slow request. The `Blocs` tab currently behaves like a dense live preview wall: sortable cards, multiple `iframe` previews, resize observers, representative-entity switching, and a detail panel that can keep refreshing preview output while the user edits form fields.

This plan treats the problem as a rendering-architecture issue inside the existing React 19, TanStack Query, and Tauri 2 stack. The goal is not to preserve maximum preview fidelity everywhere. The goal is to keep `Collections` responsive on weak hardware, then reintroduce fidelity only where it materially helps the editing workflow.

Execution posture: characterize first, then optimize. This work should begin with targeted measurement and strict preview budgets, not a broad memoization sweep.

## Problem Frame

The hot path is `Collections -> Blocs`, not the overall router or the transform pipeline:

- `src/niamoto/gui/ui/src/features/collections/components/CollectionPanel.tsx` mounts `ContentTab` when the active tab is `content`.
- `src/niamoto/gui/ui/src/components/content/ContentTab.tsx` keeps both the widget list and the right-hand panel mounted.
- `src/niamoto/gui/ui/src/components/content/LayoutOverview.tsx` renders the layout grid, representative selector, drag-and-drop, navigation preview, and one preview card per widget.
- Each widget card builds a `PreviewDescriptor` with `mode: 'full'`, even though the preview contract already supports `thumbnail` for tiles and lists in `src/niamoto/gui/ui/src/lib/preview/types.ts` and `docs/06-gui/reference/preview-api.md`.
- `src/niamoto/gui/ui/src/components/preview/usePreviewVisibility.ts` sets `hasBeenVisible` permanently after first intersection, so scrolling through the overview eventually makes every seen preview eligible forever.
- `src/niamoto/gui/ui/src/components/preview/PreviewPane.tsx` remounts each iframe when container width changes.
- `src/niamoto/gui/ui/src/components/content/WidgetDetailPanel.tsx` and `src/niamoto/gui/ui/src/components/widgets/WidgetConfigForm.tsx` couple form edits to preview updates, so preview work can continue while the user types.
- `src/niamoto/gui/ui/src/lib/preview/usePreviewFrame.ts` limits concurrent preview fetches, but not the browser-side parse and execution cost of the iframes themselves.

On a weak Windows laptop or mini PC, this turns one configuration screen into a multi-surface CPU workload, and the whole Tauri window feels blocked because the webview main thread is saturated.

## Requirements Trace

Derived from the user request and current Collections behavior:

1. Opening `Collections -> Blocs` must stay responsive on low-power hardware, even for collections with many widgets.
2. Reordering widgets and opening widget details must not depend on all previews finishing first.
3. Editing widget parameters must keep text input and controls responsive while preview work is pending or deferred.
4. Strong machines may still expose richer previews, but weaker machines must degrade gracefully instead of freezing.
5. The plan must stay inside the current stack and preserve transform/export semantics.
6. Verification must include a real low-power device or an explicit fallback profile, not only a fast Mac.

## Scope Boundaries

### In scope

- `Collections` `Blocs` tab performance and perceived responsiveness
- Overview preview strategy in `LayoutOverview`
- Detail-panel preview strategy in `WidgetDetailPanel`
- Preview lifecycle and scheduling in the UI layer
- Lightweight preview diagnostics in the UI and preview API

### Out of scope

- A rewrite of the transform engine or export pipeline
- Generic React-wide memoization campaigns
- Unrelated page-level smoothness work already covered by `docs/plans/2026-04-12-refactor-ui-rendering-smoothness-plan.md`
- Full list virtualization as the first move for the sortable widget grid

### Non-goals

- Preserve full interactive previews in every overview card
- Make all hardware classes behave identically
- Turn the plan into a Tauri-specific workaround instead of fixing the Collections feature design

## Context and Research

### Related local context

- `docs/plans/2026-03-31-refactor-groups-to-collections-plan.md` defines the Collections information architecture and confirms that `Blocs` is a layout/configuration surface, not a published dashboard.
- `docs/06-gui/architecture/preview-system.md` already distinguishes lightweight preview tiles from full preview panes.
- `docs/06-gui/reference/preview-api.md` already documents `thumbnail` and `full` preview modes, with `thumbnail` intended for tiles and lists.

### Local findings that materially shape the plan

1. `LayoutOverview` uses `mode: 'full'` for overview cards and the navigation sidebar, even though the API contract already has a lower-cost preview mode.
2. `usePreviewVisibility` is one-way: once a preview has been visible, it stays effectively “hot” for the rest of the session.
3. Each `PreviewPane` owns a `ResizeObserver` and can remount its iframe when width changes, which multiplies resize work across the grid.
4. The current preview semaphore gates HTML fetch timing, not the actual browser-side iframe execution cost.
5. `WidgetDetailPanel` keeps live preview updates tied to debounced form changes, so low-power machines continue to do rendering work during parameter editing.
6. The preview backend runs locally via threadpool in `src/niamoto/gui/api/routers/preview.py` and `src/niamoto/gui/api/services/preview_engine/engine.py`, so the same weak machine pays both API-side and browser-side CPU costs.

### External validation

External guidance confirms the direction of the plan:

- React’s official `<Profiler>` API is appropriate for measuring subtree render cost via `actualDuration` and `baseDuration`.
- React’s `startTransition` and `useDeferredValue` help defer non-urgent React rendering work, but they do not make controlled inputs asynchronous and they do not solve heavy iframe execution by themselves.
- MDN documents `content-visibility: auto` as a way to skip offscreen rendering work, but it cannot help if the application intentionally keeps every preview mounted after first visibility.
- MDN documents `HTMLIFrameElement.loading`, which gives the browser a native lazy-loading hint for offscreen iframes.
- MDN documents `navigator.hardwareConcurrency` as a baseline, widely available signal that can be used cautiously in an adaptive preview policy.

## Key Technical Decisions

1. **Treat `Blocs` as a layout editor first, not a live dashboard wall.** Users need quick layout recognition, drag-and-drop, and fast access to details. They do not need every card to run a full interactive widget preview simultaneously.
2. **Exploit the existing `thumbnail` vs `full` preview contract before inventing new preview types.** The current code is paying `full` preview cost in places that are semantically list/grid surfaces.
3. **Default to a conservative, adaptive preview policy.** On weak devices or large collections, overview cards should default to metadata-only or lightweight thumbnail previews. Full preview belongs in the detail panel.
4. **Do not start with virtualization of the sortable grid.** Sortable grids plus virtualization are easy to destabilize. Remove live iframe pressure first, then revisit virtualization only if the remaining DOM size still hurts.
5. **Stop coupling parameter editing to unconditional preview refresh.** Preview can be staged, manually refreshed, or deferred; text input cannot.
6. **Fix preview lifecycle, not just preview fetches.** Cached HTML may remain in TanStack Query, but offscreen iframes should be allowed to unmount.
7. **Use measurement to gate any backend preview work.** If UI-side changes recover responsiveness, avoid broad preview-engine refactors.

## Open Questions

These questions are useful but not blocking for planning:

- Should the navigation sidebar preview stay live in overview mode, or should it also follow the adaptive preview policy?
- Does the product want a visible “Performance mode” preference later, or is a per-device automatic default plus a local override enough?
- What widget-count threshold best separates “normal” and “heavy” collections in real projects?

The plan assumes these will be resolved during implementation by instrumentation and short product review, not by reopening requirements work.

## Implementation Units

### Unit 1 — Add measurement and explicit Collections performance budgets

**Goal**

Establish a measurable baseline for the `Blocs` tab so later optimizations are validated on both strong and weak hardware.

**Requirements**

- R1
- R3
- R6

**Dependencies**

- None

**Files**

- Create: `src/niamoto/gui/ui/src/features/collections/performance/collectionsPerf.ts`
- Create: `src/niamoto/gui/ui/src/features/collections/performance/collectionsPerf.test.ts`
- Modify: `src/niamoto/gui/ui/src/features/collections/components/CollectionPanel.tsx`
- Modify: `src/niamoto/gui/ui/src/components/content/LayoutOverview.tsx`
- Modify: `src/niamoto/gui/ui/src/components/content/WidgetDetailPanel.tsx`
- Modify: `src/niamoto/gui/api/routers/preview.py`
- Test: `src/niamoto/gui/ui/src/features/collections/performance/collectionsPerf.test.ts`

**Approach**

- Add a dev-only instrumentation module for Collections that records:
  - tab switch latency into `content`
  - mounted preview count
  - preview request duration
  - detail preview refresh duration
- Wrap the expensive UI subtrees in React `<Profiler>` only in development.
- Add lightweight timing headers or logs in the preview API so frontend and backend costs can be separated during diagnosis.
- Define soft budgets for the workflow:
  - `Blocs` chrome visible immediately, before previews finish
  - widget list remains interactive while previews are pending
  - typing in widget config remains responsive even when preview is stale

**Patterns to follow**

- `src/niamoto/gui/ui/src/features/feedback/lib/api-tracker.ts` for lightweight `performance.now()`-based timing
- `src/niamoto/gui/ui/src/lib/preview/usePreviewFrame.ts` for central preview request tracking

**Test scenarios**

1. The performance helper classifies device and collection load without throwing when optional browser signals are absent.
2. Dev instrumentation is a no-op in production builds.
3. Preview timing metadata can be captured without changing the preview response body contract.

**Verification**

- Capture a baseline trace for:
  - a strong machine
  - the low-power target device
  - a fallback throttled profile if the target device is temporarily unavailable
- Save the baseline numbers in the implementation PR description so follow-up units can be compared against the same workflow.

### Unit 2 — Introduce an adaptive overview preview policy

**Goal**

Reduce the number and fidelity of overview previews so the page remains usable before any live widget render completes.

**Requirements**

- R1
- R2
- R4

**Dependencies**

- Unit 1

**Files**

- Create: `src/niamoto/gui/ui/src/components/content/previewPolicy.ts`
- Create: `src/niamoto/gui/ui/src/components/content/previewPolicy.test.ts`
- Modify: `src/niamoto/gui/ui/src/components/content/LayoutOverview.tsx`
- Modify: `src/niamoto/gui/ui/src/components/content/ContentTab.tsx`
- Modify: `src/niamoto/gui/ui/src/features/collections/components/CollectionPanel.tsx`
- Test: `src/niamoto/gui/ui/src/components/content/previewPolicy.test.ts`
- Test: `src/niamoto/gui/ui/src/components/content/LayoutOverview.test.tsx`

**Approach**

- Replace the current boolean `showPreviews` toggle with an explicit policy, for example:
  - `off`: metadata cards only
  - `thumbnail`: lightweight overview tiles
  - `focused`: only the selected or inspected card gets a live preview
- Use the existing `thumbnail` preview mode for overview cards. Do not use `full` previews in the grid.
- Derive the default policy from:
  - widget count
  - `navigator.hardwareConcurrency`
  - optional future signals such as remembered user override
- Keep the detail panel as the primary place for `full` preview.
- Automatically drop to `off` or `focused` during drag-and-drop.
- Persist the user’s override locally so a strong machine can opt back into richer previews without penalizing weaker devices by default.

**Patterns to follow**

- `docs/06-gui/reference/preview-api.md` for the `thumbnail` vs `full` contract
- The existing preview toggle flow in `src/niamoto/gui/ui/src/components/content/LayoutOverview.tsx`

**Test scenarios**

1. A heavy collection on a low-capability device defaults to `off` or `focused`, not `thumbnail`.
2. A small collection on a normal device can still default to `thumbnail`.
3. Switching preview policy updates only the intended cards.
4. During drag-and-drop, live card previews are not remounted.

**Verification**

- On the low-power device, entering `Blocs` shows the widget grid immediately and stays scrollable before any preview finishes.
- On the strong machine, users can still opt into richer previews without breaking correctness.

### Unit 3 — Fix preview lifecycle and remount churn

**Goal**

Prevent the overview from accumulating live iframe work as the user scrolls, resizes, or revisits cards.

**Requirements**

- R1
- R2
- R4

**Dependencies**

- Unit 2

**Files**

- Create: `src/niamoto/gui/ui/src/components/preview/usePreviewVisibility.test.ts`
- Create: `src/niamoto/gui/ui/src/components/preview/PreviewPane.test.tsx`
- Create: `src/niamoto/gui/ui/src/lib/preview/usePreviewFrame.test.ts`
- Modify: `src/niamoto/gui/ui/src/components/preview/usePreviewVisibility.ts`
- Modify: `src/niamoto/gui/ui/src/components/preview/PreviewPane.tsx`
- Modify: `src/niamoto/gui/ui/src/lib/preview/usePreviewFrame.ts`
- Modify: `src/niamoto/gui/ui/src/components/content/LayoutOverview.tsx`
- Test: `src/niamoto/gui/ui/src/components/preview/usePreviewVisibility.test.ts`
- Test: `src/niamoto/gui/ui/src/components/preview/PreviewPane.test.tsx`
- Test: `src/niamoto/gui/ui/src/lib/preview/usePreviewFrame.test.ts`

**Approach**

- Replace the current one-way `hasBeenVisible` logic with visibility hysteresis:
  - mount near the viewport
  - unmount when far enough away
  - keep HTML cached, but release iframe DOM and JS work
- Add `loading="lazy"` to preview iframes as a browser-level hint.
- Debounce or bucket width-driven remounts so a window resize does not cause a burst remount across every preview card.
- Revisit the preview scheduler so it controls iframe insertion timing, not only preview fetch timing. The current semaphore does not directly cap browser execution cost.

**Patterns to follow**

- The existing preview cache model in `src/niamoto/gui/ui/src/lib/preview/usePreviewFrame.ts`
- `docs/06-gui/architecture/preview-system.md`, especially the separation between frontend cache and iframe lifecycle

**Test scenarios**

1. A preview can become invisible again and unmount without losing cached HTML identity.
2. Scrolling through a long collection does not leave every previously seen preview mounted.
3. A resize event does not remount every preview on every observer callback.
4. Lazy iframe hints do not break preview rendering correctness.

**Verification**

- Scroll through a collection with many widgets on the low-power device and confirm that iframe count does not grow without bound.
- Resize the window and confirm that the page remains responsive instead of triggering a preview storm.

### Unit 4 — Decouple widget editing from unconditional live preview refresh

**Goal**

Keep the detail editor responsive while still allowing accurate preview inspection.

**Requirements**

- R2
- R3
- R4

**Dependencies**

- Unit 1

**Files**

- Create: `src/niamoto/gui/ui/src/components/content/WidgetDetailPanel.test.tsx`
- Create: `src/niamoto/gui/ui/src/components/widgets/WidgetConfigForm.test.tsx`
- Modify: `src/niamoto/gui/ui/src/components/content/WidgetDetailPanel.tsx`
- Modify: `src/niamoto/gui/ui/src/components/widgets/WidgetConfigForm.tsx`
- Test: `src/niamoto/gui/ui/src/components/content/WidgetDetailPanel.test.tsx`
- Test: `src/niamoto/gui/ui/src/components/widgets/WidgetConfigForm.test.tsx`

**Approach**

- Separate form draft state from preview state.
- Replace unconditional debounced live preview updates with one of these flows:
  - explicit “Refresh preview”
  - auto-refresh on idle only in normal mode
  - always-manual refresh in low-power mode
- Keep `title` and other cheap text metadata independent from heavy preview recomputation where possible.
- Use `useDeferredValue` or `startTransition` only for non-urgent preview-side UI state, never for controlled input state itself.
- Keep preview invalidation after save so persisted changes still refresh correctly.

**Patterns to follow**

- `src/niamoto/gui/ui/src/components/widgets/AddWidgetModal.tsx`, which already uses `startTransition` and `useDeferredValue` in a targeted way
- React guidance that transitions defer rendering work but should not be used to control input state

**Test scenarios**

1. Typing in a config field updates form state immediately without forcing a preview refresh on every debounce cycle.
2. Manual preview refresh reuses the latest draft state.
3. Saving clears the dirty preview state and refreshes persisted preview output.
4. Switching widgets resets draft and preview state without leaking the previous widget’s state.

**Verification**

- On the low-power device, typing in the detail form remains smooth while preview is stale or pending.
- The user can still request an accurate preview before saving.

### Unit 5 — Tighten preview-engine diagnostics and thumbnail guarantees only if still needed

**Goal**

Reduce backend preview cost only where measurement shows the API remains a dominant bottleneck after Units 2 to 4.

**Requirements**

- R1
- R4
- R5

**Dependencies**

- Units 1 to 4

**Files**

- Modify: `src/niamoto/gui/api/routers/preview.py`
- Modify: `src/niamoto/gui/api/services/preview_engine/models.py`
- Modify: `src/niamoto/gui/api/services/preview_engine/engine.py`
- Modify: `src/niamoto/gui/ui/src/lib/preview/types.ts`
- Modify: `docs/06-gui/reference/preview-api.md`
- Test: `tests/gui/api/routers/test_preview.py`
- Test: `tests/gui/api/services/preview_engine/test_models.py`
- Test: `tests/gui/api/services/preview_engine/test_engine.py`

**Approach**

- Confirm that `thumbnail` mode really delivers a lower-cost render path in practice, not only a different frontend presentation.
- If measurement still shows backend preview cost dominating, add explicit thumbnail-focused shortcuts that do not alter `full` preview correctness.
- Keep this unit conditional. Do not widen preview-engine complexity if UI-side policy changes already recover responsiveness.

**Patterns to follow**

- Existing preview API mode handling documented in `docs/06-gui/reference/preview-api.md`
- Existing preview-engine tests under `tests/gui/api/services/preview_engine/`

**Test scenarios**

1. `thumbnail` mode preserves the HTTP contract and remains distinct from `full`.
2. Any backend shortcut for thumbnail mode does not alter `full` mode output.
3. Preview timing metadata stays optional and does not break existing consumers.

**Verification**

- Compare preview endpoint timing before and after the unit on the low-power target.
- Skip this unit entirely if Units 2 to 4 already meet the responsiveness target.

## Recommended Sequencing

1. Unit 1
2. Unit 2
3. Unit 3
4. Unit 4
5. Unit 5 only if measurement still justifies it

This order matters. The biggest likely win is to stop rendering `full` live previews across the entire overview grid. Lifecycle fixes come next. Detail-panel live preview changes matter, but they should not be used to compensate for a fundamentally over-active overview.

## System-Wide Impact

- The Collections UX becomes explicitly adaptive by hardware and collection size.
- The preview system will align better with its documented `thumbnail` vs `full` split.
- The frontend test suite gains coverage in a part of the UI that currently has almost no direct tests beyond route helpers.
- The preview API may gain timing observability, which will also help future performance work outside Collections.

## Risks and Dependencies

### Main risks

- Over-correcting into a “dead” overview that no longer gives enough confidence about widget layout.
- Making the preview policy too opaque if the automatic mode changes are not visible or overridable.
- Regressing preview correctness if `thumbnail` and `full` semantics drift.
- Adding too much complexity to the preview engine before proving that backend cost is still the bottleneck.

### Mitigations

- Keep one clear user override in the `Blocs` toolbar.
- Preserve `full` preview in the detail panel as the authoritative inspection surface.
- Gate backend preview work behind Unit 1 measurements and post-Unit-4 comparison.
- Document the mode split in GUI architecture docs once implementation stabilizes.

### Dependencies

- The existing preview mode contract in `src/niamoto/gui/ui/src/lib/preview/types.ts` and `docs/06-gui/reference/preview-api.md`
- Reliable access to at least one weak target device, or a documented fallback verification profile

## Documentation and Operational Notes

If Units 2 to 5 land, update:

- `docs/06-gui/architecture/preview-system.md`
- `docs/06-gui/reference/preview-api.md`
- `src/niamoto/gui/ui/README.md` if it references Collections editing behavior or preview expectations

The documentation update should explain:

- why overview previews are adaptive
- when `thumbnail` vs `full` is used
- why full live preview is intentionally concentrated in the detail panel

## Sources and References

### Local code and docs

- `src/niamoto/gui/ui/src/features/collections/components/CollectionPanel.tsx`
- `src/niamoto/gui/ui/src/components/content/ContentTab.tsx`
- `src/niamoto/gui/ui/src/components/content/LayoutOverview.tsx`
- `src/niamoto/gui/ui/src/components/content/WidgetDetailPanel.tsx`
- `src/niamoto/gui/ui/src/components/widgets/WidgetConfigForm.tsx`
- `src/niamoto/gui/ui/src/components/preview/usePreviewVisibility.ts`
- `src/niamoto/gui/ui/src/components/preview/PreviewPane.tsx`
- `src/niamoto/gui/ui/src/lib/preview/types.ts`
- `src/niamoto/gui/ui/src/lib/preview/usePreviewFrame.ts`
- `src/niamoto/gui/api/routers/preview.py`
- `src/niamoto/gui/api/services/preview_engine/engine.py`
- `docs/06-gui/architecture/preview-system.md`
- `docs/06-gui/reference/preview-api.md`
- `docs/plans/2026-03-31-refactor-groups-to-collections-plan.md`

### External references

- [React `<Profiler>`](https://react.dev/reference/react/Profiler)
- [React `startTransition`](https://react.dev/reference/react/startTransition)
- [React `useDeferredValue`](https://react.dev/reference/react/useDeferredValue)
- [MDN `HTMLIFrameElement.loading`](https://developer.mozilla.org/en-US/docs/Web/API/HTMLIFrameElement/loading)
- [MDN `content-visibility`](https://developer.mozilla.org/en-US/docs/Web/CSS/content-visibility)
- [MDN `navigator.hardwareConcurrency`](https://developer.mozilla.org/en-US/docs/Web/API/NavigatorConcurrentHardware/hardwareConcurrency)
