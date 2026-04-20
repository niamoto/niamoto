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

## Soon (Summer 2026)

## Later (H2 2026 and beyond)

## Not planned

## How to contribute
