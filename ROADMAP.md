# Niamoto Roadmap

_Last updated: 2026-04-20 — reviewed at each minor release._

## Vision

Niamoto is a generic ecological data platform. It turns heterogeneous datasets into publishable web portals through a configurable **Import → Transform → Export** pipeline, running locally with no cloud dependency. The desktop app (Tauri) and the CLI share the same engine and the same plugins.

## Recently shipped

Highlights from the last ~3 months:

- **macOS signing & notarization pipeline** (v0.15.5, April 2026)
- **In-app feedback system** ([plan](docs/plans/2026-04-04-feat-in-app-feedback-system-plan.md))
- **Rich multi-source enrichment**: GBIF, CoL, iNaturalist, BHL, GN TaxRef, Tropicos, spatial v1 ([specs](docs/superpowers/specs/))
- **Sources dashboard & mission control redesign** ([plan](docs/plans/2026-04-01-refactor-sources-dashboard-redesign-plan.md))
- **Transform & export parallelization** ([transform spec](docs/superpowers/specs/2026-03-27-transform-parallelization-design.md), [export spec](docs/superpowers/specs/2026-03-27-export-parallelization-design.md))
- **Frontend architecture refactor** to `src/app`, `src/features`, `src/shared` ([plan](docs/plans/2026-03-25-refactor-frontend-feature-architecture-plan.md))
- **Release automation** via the `niamoto-release` skill ([plan](docs/plans/2026-03-25-feat-niamoto-release-automation-skill-plan.md))

## GBIF Ebbe Nielsen Challenge 2026 ⭐

**Deadline: 26 June 2026.**

**Pitch — _Niamoto: Local-First Intelligence_.** Combine local intelligent curation (classical ML + fuzzy matching + optional SLM) with automatic generation of web portals from GBIF data, **with no cloud dependency**. The differentiating angle from 2024–2025 winners (who rely on remote LLMs).

**Core deliverables activated for the challenge:**

1. **GBIF rich enrichment** — taxonomic and spatial enrichment via GBIF APIs ([plan](docs/plans/2026-04-09-feat-gbif-rich-enrichment-plan.md) · [spec](docs/superpowers/specs/2026-04-09-gbif-rich-enrichment-design.md))
2. **GBIF registry publication** — publish Niamoto as a referenced tool ([plan](docs/plans/2026-03-13-feat-gbif-registry-publication-plan.md))
3. **Challenge presentation page** — dedicated landing for submission ([plan](docs/plans/2026-03-13-feat-gbif-challenge-presentation-page-plan.md))

**Optional bonuses (time-permitting):**

- BDQ validation (12 Tier-1 tests — covers ~60% of real data-quality issues)
- Local schema detection for Darwin Core imports
- Optional local SLM (Liquid AI LFM2 or Qwen3 via Ollama)

**References:**

- Full opportunity report: [docs/plans/2026-03-11-feat-gbif-ebbe-nielsen-challenge-2026-opportunity-report.md](docs/plans/2026-03-11-feat-gbif-ebbe-nielsen-challenge-2026-opportunity-report.md)
- Standalone presentation (HTML): [docs/08-roadmaps/gbif-challenge-2026.html](docs/08-roadmaps/gbif-challenge-2026.html)

## Now (April – June 2026)

In flight or imminent. Excludes GBIF-specific deliverables listed above.

**Desktop & distribution**

- Desktop update harness & auto-updater ([spec](docs/superpowers/specs/2026-04-08-desktop-update-harness-design.md))
- Binary-size audit & reduction ([plan](docs/plans/2026-04-19-001-refactor-desktop-size-audit-strategy-plan.md))

**Documentation**

- Desktop-first documentation overhaul — user guide, in-app docs, public docs, team/partners page ([plan 1](docs/plans/2026-04-17-refactor-documentation-desktop-first-plan.md), [plan 2](docs/plans/2026-04-18-001-refactor-desktop-user-guide-plan.md), [plan 3](docs/plans/2026-04-18-002-feat-in-app-user-docs-plan.md), [plan 4](docs/plans/2026-04-18-003-feat-in-app-public-documentation-plan.md), [plan 5](docs/plans/2026-04-18-004-feat-about-team-partners-plan.md))

**Marketing site**

- Landing page refresh + hybrid teaser video ([landing refonte](docs/plans/2026-04-14-feat-landing-teaser-refonte-plan.md), [hybrid teaser](docs/plans/2026-04-14-feat-landing-teaser-hybride-plan.md), [teaser video](docs/plans/2026-04-14-feat-landing-teaser-video-plan.md), [marketing site](docs/plans/2026-04-14-feat-niamoto-marketing-site-plan.md))

**UI polish**

- Enrichment tab UX redesign ([plan](docs/plans/2026-04-10-refactor-enrichment-tab-ux-redesign-plan.md))
- UI density compaction & rendering smoothness ([density](docs/plans/2026-04-12-refactor-ui-density-compaction-plan.md), [smoothness](docs/plans/2026-04-12-refactor-ui-rendering-smoothness-plan.md))

## Soon (Summer 2026)

Planned but not yet started.

- **Niamoto Doctor** — unified diagnostics (CLI + GUI) ([ideation](docs/ideation/2026-04-12-open-ideation.md))
- **Starter project templates** — `niamoto init --template` with real starter kits ([ideation](docs/ideation/2026-04-12-open-ideation.md))
- **Export contract pack** — JSON schema on the export side
- **ML model regeneration pipeline** ([spec](docs/superpowers/specs/2026-03-27-ml-model-regeneration-design.md))
- Transform parallelization phase 2

## Later (H2 2026 and beyond)

Identified in ideation, not yet planned.

- **Example & fixture certification pipeline** — docs and fixtures as executable contracts
- **Suggestion explainability layer** — attached evidence for every auto-suggestion (matched fields, confidence band, override paths)
- **Transform provenance explorer** — dependency graph across import → transform → export
- **Desktop v1.0** — iteration round after the GBIF submission

## Not planned

## How to contribute
