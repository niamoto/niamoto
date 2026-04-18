---
date: 2026-04-18
topic: desktop-ui-user-guide
---

# Desktop UI User Guide

## Problem Frame

Niamoto already documents the desktop product in several places, but the current material is split between short user-guide pages, architecture notes, code READMEs, and older roadmap documents. That makes the desktop experience harder to understand than it should be, especially because the current UI has a strong visual workflow that is already captured in `docs/plans/caps/`.

The immediate need is not a generic "GUI doc refresh". The first need is a public, desktop-first user guide that matches the real interface, uses the current product vocabulary, and helps a reader follow the main path from app launch to publication. A second, separate need exists for maintainers: clarify where the runtime and frontend architecture are documented, and keep that material distinct from the public user guide.

## Visual Map

| Layer | Audience | Primary location | Purpose |
| --- | --- | --- | --- |
| Quick start | New desktop user | `docs/01-getting-started/` | Short orientation and first-use entry points |
| Desktop user guide | Desktop end user | `docs/02-user-guide/` | Detailed desktop walkthrough and module-level guidance |
| GUI runtime architecture | Maintainer | `docs/07-architecture/` | React, FastAPI, and Tauri runtime model |
| GUI code structure and dev workflow | Maintainer | `src/niamoto/gui/README.md`, `src/niamoto/gui/ui/README.md` | Directory structure, conventions, local development |

## Requirements

**Public Desktop Guide**
- R1. The first implementation pass must focus on the public desktop user guide, not the maintainer architecture docs.
- R2. The guide must document the main desktop path only: welcome, project creation/opening, import, collections, site, and publication.
- R3. The guide must be desktop-only for the first pass. Web-specific behavior is out of scope except where a brief note materially helps avoid confusion.
- R4. `docs/02-user-guide/README.md` must become the main entry point for a desktop tour, with a short linear walkthrough at the top and module-level navigation below it.
- R5. `docs/01-getting-started/` must keep a short version of the onboarding path, while `docs/02-user-guide/` becomes the detailed desktop reference.

**Page Model And Vocabulary**
- R6. The public guide must use current UI vocabulary as the reader-facing source of truth.
- R7. "Collections" must replace "Transform" as the primary user-facing term in the user guide.
- R8. "Publish" must replace "Export" as the primary user-facing term in the user guide.
- R9. The current `docs/02-user-guide/transform.md` page must be replaced by `docs/02-user-guide/collections.md`, with a redirect from the old URL.
- R10. The current `docs/02-user-guide/export.md` page must be replaced by `docs/02-user-guide/publish.md`, with a redirect from the old URL.
- R11. The first pass must add a dedicated `docs/02-user-guide/site.md` page for the Site Builder instead of burying it inside preview or publication content.

**Use Of Screenshots**
- R12. The guide must be strongly visual, but it must not become a brittle storyboard of every screen state.
- R13. The screenshots in `docs/plans/caps/` must be treated as the visual source of truth for the desktop product path in this documentation pass.
- R14. Each major step in the main path should be anchored by one or more representative screenshots when that materially improves comprehension.
- R15. Screenshots should illustrate decisive transitions and module identity, not every intermediate state.

**Bridges To Configuration**
- R16. The user guide must remain UI-first.
- R17. The guide should include light bridges to `import.yml`, `transform.yml`, and `export.yml` only where that helps explain what the interface is editing or driving.
- R18. The guide must not turn into a pipeline reference or a maintainer document.

**Maintainer Documentation Follow-Up**
- R19. The maintainer documentation for the GUI must remain a separate follow-up track from the first public-guide pass.
- R20. In that follow-up track, `docs/07-architecture/` must serve as the primary home for runtime and system-layer GUI architecture.
- R21. In that follow-up track, `src/niamoto/gui/README.md` and `src/niamoto/gui/ui/README.md` must serve as the primary home for code structure, conventions, and local development workflow.

## Success Criteria

- A reader can understand the desktop app's main path from launch to publication by reading `docs/02-user-guide/README.md` and the linked module pages.
- The public guide vocabulary matches the current desktop UI, especially for Collections, Site, and Publish.
- The guide uses real screenshots from `docs/plans/caps/` to anchor the most important steps without becoming screen-by-screen brittle.
- `docs/01-getting-started/` and `docs/02-user-guide/` no longer compete for the same level of detail.
- Redirects preserve old user-guide URLs where terminology changed.
- Planning can proceed without inventing the intended doc structure, audience split, or scope boundaries.

## Scope Boundaries

- No full web-parity documentation in the first pass.
- No detailed documentation yet for secondary desktop areas such as settings, tools, explorer, or plugins.
- No attempt to rewrite all GUI maintainer docs in the same first pass.
- No screenshot-for-every-state storyboard.
- No deep implementation-level architecture inside the public user guide.

## Key Decisions

- Public desktop guide first: the most urgent gap is helping readers understand the real app they use.
- Desktop-only first pass: the available screenshots and the current product positioning support a cleaner desktop-first guide.
- Mixed structure: a short linear journey plus module-level pages is better than either a pure narrative or a pure gallery.
- Existing user-guide pages should be rewritten, not merely supplemented by an extra gallery page.
- Screenshot-driven but not storyboard-driven: the guide should be visually grounded without becoming too expensive to maintain.
- "Collections" and "Publish" are the canonical user-facing terms.
- Maintainer docs should be split cleanly between runtime architecture in `docs/07-architecture/` and codebase/development guidance in the GUI READMEs.

## Dependencies / Assumptions

- The screenshots in `docs/plans/caps/` remain broadly representative of the current desktop UI.
- Redirect support remains available through the docs build configuration.
- The desktop app continues to be the primary end-user interface for Niamoto documentation.

## Outstanding Questions

### Resolve Before Planning

None.

### Deferred To Planning

- [Affects R12][Needs research] Decide the exact screenshot set to include in each rewritten page so the guide stays visual without becoming noisy.
- [Affects R4][Technical] Decide whether `docs/02-user-guide/README.md` should embed screenshots directly or stay mostly textual with tighter links into the module pages.
- [Affects R19][Technical] Decide whether the maintainer follow-up should include a new dedicated GUI architecture index page or reuse the current `docs/07-architecture/README.md` structure with stronger GUI signposting.
- [Affects R21][Technical] Decide whether the GUI README refresh should happen in one follow-up pass or be split between `src/niamoto/gui/README.md` and `src/niamoto/gui/ui/README.md`.

## Next Steps

-> /ce:plan for structured implementation planning
