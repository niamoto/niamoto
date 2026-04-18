---
date: 2026-04-18
topic: about-team-partners
---

# About, Team, Partners, and Funders

## Problem Frame

Niamoto already has credible public material about the people and institutions behind the project, but that information is fragmented. The desktop app still exposes a minimal `À propos` block focused on versioning, while the root `README.md` has no real institutional section. This leaves two important entry points without a clear answer to basic trust questions: who builds Niamoto, who supports it, and which organizations are involved.

The immediate need is not to mirror the showcase page mechanically. The need is to create one repo-owned, bilingual source of truth for `Niamoteam` and `Partenaires & financeurs`, then render it coherently in the app and in `README.md` without introducing another copy/paste content path.

## Requirements

**Canonical content**
- R1. Niamoto must have one canonical, repo-owned content source for the institutional `About` content, rather than treating the public showcase as the live source of truth.
- R2. The canonical content must be bilingual (`fr` and `en`) so the app can respect its language switch and the root `README.md` can reuse the English version.
- R3. The canonical content must cover two editorial blocks only for this pass: `Niamoteam` and `Partenaires & financeurs`.
- R4. The `Niamoteam` block must keep names and roles, omit photos, and replace the current `Indépendant` wording for Julien with a developer role.
- R5. The `Partenaires & financeurs` block must include both text and logos, with no visual split into separate partner and funder sub-sections.

**Desktop app**
- R6. The desktop app must expose this content inside `Settings`, by enriching the existing `À propos` area instead of creating a separate page or modal in this first pass.
- R7. The app `À propos` surface must keep version and update information available; the new institutional content extends the current panel rather than displacing core update actions.
- R8. In the app, names and logos in `Niamoteam` and `Partenaires & financeurs` must be clickable when a relevant external profile or organization site exists.

**README**
- R9. The root `README.md` must include the same institutional content at a similar editorial level as the app, not a heavily reduced summary.
- R10. In `README.md`, the new section must appear in the lower part of the document as a dedicated `About` block, not in the opening hero area.
- R11. In `README.md`, the partner and funder logos must be shown directly, not reduced to text-only mentions.

**Content behavior and consistency**
- R12. The content must be shaped by the current showcase, but the implementation must not depend on scraping or reading the showcase at runtime.
- R13. The rendered structure must stay intentionally simple: `Niamoteam`, then one merged `Partenaires & financeurs` section.
- R14. The same named people, organizations, roles, links, and logos must stay consistent between the app and `README.md`.

## Success Criteria

- A desktop user can open `Settings > À propos` and immediately understand who builds Niamoto and which organizations support it.
- A GitHub or PyPI reader can find the same institutional information in `README.md` without leaving the repository context.
- The project gains one canonical content source for this institutional material, so app and README do not drift independently.
- The new section increases project credibility without adding a second documentation maintenance path.

## Scope Boundaries

- This pass does not redesign the entire `Settings` page.
- This pass does not add team photos.
- This pass does not turn the app `À propos` into a dedicated screen or modal.
- This pass does not make the showcase page the runtime data source.
- This pass does not attempt to unify all marketing, website, and documentation copy across every public surface.

## Key Decisions

- Canonical repo-owned content, not showcase mirroring: the showcase is the reference input for this pass, but the maintained source of truth must live in the repository.
- Same content level in app and README: both surfaces should carry real institutional weight, not a rich app version plus a token README footnote.
- Bilingual source: the app needs `fr/en`, and the README can consume the English variant.
- `Settings` enrichment first: this keeps the scope tight and improves an existing discoverable surface instead of creating a new help destination.
- No photos in `Niamoteam`: names and roles are enough for this product surface, while photos would raise maintenance cost and visual noise.
- One merged `Partenaires & financeurs` section: the user-facing goal is institutional recognition, not a taxonomy exercise.

## Dependencies / Assumptions

- Existing partner and funder logos already present under `docs/assets/funders/` can be reused for this pass.
- The current showcase contains a team composition and partner/funder phrasing worth normalizing into repo-owned content.
- The exact `Niamoteam` roster is not yet established as a local canonical dataset in the repo and will need to be captured during implementation planning or execution.

## Outstanding Questions

### Deferred to Planning

- [Affects R4][Needs research] Capture the exact current `Niamoteam` roster and titles from the showcase, then normalize them into the canonical bilingual content source.
- [Affects R5][Needs research] Decide how much of the showcase wording for `Partenaires & financeurs` should be reused verbatim versus tightened for the app and `README.md`.
- [Affects R8][Technical] Decide the exact fallback behavior when a team member has no public profile link but still needs to appear in `Niamoteam`.
- [Affects R11][Technical] Decide the exact README rendering pattern for the logo grid so it remains legible on GitHub and PyPI.

## Next Steps

-> /ce:plan for structured implementation planning
