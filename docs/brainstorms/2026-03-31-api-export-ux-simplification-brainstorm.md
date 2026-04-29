---
date: 2026-03-31
updated: 2026-04-29
topic: api-export-ux-simplification
status: Ready for planning
---

# API Export UX Simplification

## Summary

Improve the Collections > Export experience for static API exports by making auto-configuration reviewable, field editing visual, and raw JSON editing available as an advanced synchronized view. The goal is to keep the current power of JSON API and Darwin Core exports while preventing users from starting with an empty or opaque JSON field.

---

## Problem Frame

The API export tab now exposes static API configuration in the right place: inside a collection, next to content and list configuration. That is better than YAML-only configuration, but the most technical parts still ask users to understand raw JSON structures, source paths, generators, and Darwin Core mappings before they can make a confident choice.

The affected users are botanists, ecologists, project maintainers, and advanced integrators. Non-technical users need a safe default they can review and accept. Technical users still need an escape hatch where they can inspect and edit the underlying JSON without losing the convenience of the visual editor.

---

## Actors

- A1. Collection editor: configures collection exports from the GUI and needs readable defaults.
- A2. Advanced integrator: understands JSON configuration and may prefer direct editing for precise changes.
- A3. Downstream implementer: uses this document to plan UI behavior without inventing product scope.

---

## Key Flows

- F1. Review auto-configuration for an export
  - **Trigger:** A user activates or edits a static API export and wants a suggested configuration.
  - **Actors:** A1
  - **Steps:** The user requests auto-configuration, reviews the proposed index, detail, JSON options, and Darwin Core mapping when applicable, then applies or rejects the proposal.
  - **Outcome:** The export card has an understandable draft configuration without silently overwriting user choices.
  - **Covered by:** R1, R2, R3, R4

- F2. Edit fields visually, then inspect JSON
  - **Trigger:** A user wants to change what appears in index or detail API files.
  - **Actors:** A1, A2
  - **Steps:** The user edits fields in visual controls, switches to JSON view, sees the corresponding JSON, optionally edits it, and returns to the visual view.
  - **Outcome:** Both views represent the same configuration and validation prevents saving invalid JSON.
  - **Covered by:** R5, R6, R9, R10, R11, R12

- F3. Keep simple JSON export broad when desired
  - **Trigger:** A user configures a simple JSON API export and does not want a curated field subset.
  - **Actors:** A1, A2
  - **Steps:** The user keeps or selects the option to export all transformed data, then optionally configures index fields separately.
  - **Outcome:** Simple JSON export remains a low-friction publication path.
  - **Covered by:** R13, R14, R15

---

## Requirements

**Auto-configuration**
- R1. Static API exports must offer an auto-configuration action that generates a proposal instead of silently applying changes.
- R2. The auto-configuration proposal must cover the full static API export surface: index fields, detail fields, JSON formatting options, and Darwin Core mapping when the export uses Darwin Core.
- R3. The proposal must be reviewable before application, with a clear distinction between accepting the whole proposal, editing it, or cancelling it.
- R4. Auto-configuration must not remove or overwrite an existing custom configuration without an explicit user action.

**Visual field editing**
- R5. Index fields must be editable through structured interface controls rather than requiring raw JSON.
- R6. Detail fields must be editable through structured interface controls when the user chooses a curated detail payload.
- R7. Darwin Core mapping must remain editable through a guided interface that is more understandable than editing the mapping as raw JSON.
- R8. Field editors must preserve advanced cases such as generated values or custom parameters without hiding them from advanced users.

**JSON view**
- R9. Each relevant export section must provide a synchronized JSON view for the same configuration represented by the visual editor.
- R10. The visual editor remains the default editing mode; JSON is an advanced view, not the primary path for normal users.
- R11. JSON edits must validate before they update the visual editor or become saveable.
- R12. When JSON and visual forms cannot be reconciled, the UI must make the problem visible and protect the last valid configuration.

**Simple JSON export**
- R13. Simple JSON API exports must always keep the option to export all transformed data.
- R14. Auto-configuration may suggest a curated detail payload, but it must not remove the user's ability to keep pass-through detail export.
- R15. Index configuration and detail configuration must remain separate choices so users can expose a compact listing while keeping full detail files.

**User understanding**
- R16. Export cards must summarize the current configuration in domain language, including whether detail export is pass-through, curated, or Darwin Core-based.
- R17. Auto-configuration proposals must explain why the suggested fields or mappings are useful at a level understandable to ecology project users.
- R18. Advanced controls should remain available through progressive disclosure rather than being removed or made mandatory.

---

## Acceptance Examples

- AE1. **Covers R1, R2, R3, R4.** Given an existing static API export with custom fields, when the user asks for auto-configuration, the UI shows a proposal for review and does not change the saved configuration until the user applies it.
- AE2. **Covers R5, R6, R9, R11.** Given a user adds a detail field through the visual editor, when they open JSON view, the new field appears in the JSON representation; when they enter invalid JSON, the UI blocks applying it and keeps the last valid visual state.
- AE3. **Covers R7, R8.** Given a Darwin Core export contains generated values, when the user opens the mapping editor, those generated mappings remain visible and editable without requiring raw JSON as the only path.
- AE4. **Covers R13, R14, R15.** Given a simple JSON API export, when auto-configuration suggests curated detail fields, the user can still choose "Export all transformed data" and keep a separate compact index configuration.

---

## Success Criteria

- A non-technical project user can create or update a static API export without hand-writing JSON.
- An advanced user can inspect and edit the JSON representation without losing synchronization with the visual editor.
- The simple JSON export path remains fast and broad for users who want all transformed data.
- A planner can proceed from this document without inventing product behavior for auto-configuration, JSON mode, or pass-through export.

---

## Scope Boundaries

- In scope: auto-configuration proposals for static API exports.
- In scope: visual editors for index fields, detail fields, and Darwin Core mapping.
- In scope: synchronized editable JSON views for advanced users.
- In scope: preserving the option to export all transformed data for simple JSON API exports.
- Out of scope for this V2: final generated JSON preview.
- Out of scope for this V2: running an export test directly from an export card.
- Out of scope for this V2: a full rewrite of the export engine.
- Out of scope for this V2: forcing all users through JSON mode.

---

## Key Decisions

- Auto-configuration is review-first rather than automatic: this reduces surprise and avoids overwriting custom export choices.
- Visual editing is the primary experience: it fits the project goal of keeping workflows understandable to ecology domain users.
- JSON remains editable: advanced users keep a precise escape hatch without making raw JSON the normal path.
- Simple JSON pass-through remains first-class: exporting all transformed data is a useful, low-friction publication mode and should not be treated as a legacy fallback.
- Darwin Core receives guided treatment: its value depends on reliable standard mapping, so the UI should help users understand and adjust the mapping rather than exposing only raw structure.

---

## Dependencies / Assumptions

- Static API export targets already exist in the GUI and can be enabled per collection.
- Existing field suggestions for collection index configuration can inform auto-configuration, but planning should verify whether they are sufficient for detail fields and Darwin Core mapping.
- The synchronized JSON view must reflect the same saved configuration as the visual editor.
- Existing documentation in `docs/brainstorms/2026-03-30-api-export-gui-brainstorm.md` remains useful background for the original API export tab shape.

---

## Outstanding Questions

### Deferred to Planning

- [Affects R2, R17][Technical] What confidence signals should auto-configuration expose when suggestions are partial or uncertain?
- [Affects R7, R8][Technical] Which Darwin Core mappings can be suggested safely from current project data, and which should be shown as unresolved?
- [Affects R9, R11, R12][Technical] What validation boundary best prevents JSON edits from corrupting the visual editor state?
