# Niamoto Roadmap

_Last updated: 2026-04-20 — reviewed at each minor release._

## Vision

Niamoto is a generic ecological data platform. It turns heterogeneous datasets into publishable web portals through a configurable **Import → Transform → Export** pipeline, running locally with no cloud dependency. The desktop app (currently Tauri, under evaluation) and the CLI share the same engine and the same plugins.

## Recently shipped

Highlights from the last ~3 months:

- **macOS signing & notarization pipeline** (v0.15.5, April 2026)
- **In-app feedback system**
- **Rich multi-source enrichment**: GBIF, CoL, iNaturalist, BHL, GN TaxRef, Tropicos, spatial v1
- **Sources dashboard & mission control redesign**
- **Transform & export parallelization**
- **Frontend architecture refactor** to `src/app`, `src/features`, `src/shared`
- **Release automation** via the `niamoto-release` skill

## GBIF Ebbe Nielsen Challenge 2026 ⭐

**Deadline: 26 June 2026.**

**Pitch — _Niamoto: Local-First Intelligence_.** Combine local intelligent curation (classical ML + fuzzy matching + optional SLM) with automatic generation of web portals from GBIF data, **with no cloud dependency**. The differentiating angle from 2024–2025 winners (who rely on remote LLMs).

**Core deliverables activated for the challenge:**

1. **GBIF rich enrichment** — taxonomic and spatial enrichment via GBIF APIs
2. **GBIF registry publication** — publish Niamoto as a referenced tool
3. **Challenge presentation page** — dedicated landing for submission

**Optional bonuses (time-permitting):**

- BDQ validation (12 Tier-1 tests — covers ~60% of real data-quality issues)
- Local schema detection for Darwin Core imports
- Optional local SLM (Liquid AI LFM2 or Qwen3 via Ollama)
- GBIF portal auto-configuration, powered by the generic transform/export auto-config described in [Now → Configuration intelligence](#now-april--june-2026)

**References:**

- Standalone presentation (HTML): [docs/08-roadmaps/gbif-challenge-2026.html](docs/08-roadmaps/gbif-challenge-2026.html)

## Now (April – June 2026)

In flight or imminent. Excludes GBIF-specific deliverables listed above.

**Desktop & distribution**

- Desktop update harness & auto-updater
- Binary-size audit & reduction
- **Desktop shell evaluation — Tauri vs Electron** — decision-grade analysis driven by Linux stability issues, cross-platform rendering consistency, and packaging size. Informs whether the shell stays on Tauri or migrates to Electron.

**Documentation**

- Desktop-first documentation overhaul — user guide, in-app docs, public docs, team/partners page

**Institutional site**

- Landing page refresh + hybrid teaser video

**UI polish**

- Enrichment tab UX redesign
- UI density compaction & rendering smoothness

**Configuration intelligence**

- **Auto-config for collection transform/export pairs** — extend the auto-configuration approach already available for imports and for index pages to the transform/export pairs inside each collection. Fully generic across datasets, taxonomies, and domain values. Feeds directly into the GBIF portal auto-configuration used for the challenge demo, but remains a general capability for any data source.

## Soon (Summer 2026)

Planned but not yet started.

- **Niamoto Doctor** — unified diagnostics (CLI + GUI)
- **Starter project templates** — `niamoto init --template` with real starter kits
- **Export contract pack** — JSON schema on the export side
- **ML model regeneration pipeline**
- Transform parallelization phase 2

## Later (H2 2026 and beyond)

Identified in ideation, not yet planned.

- **Example & fixture certification pipeline** — docs and fixtures as executable contracts
- **Suggestion explainability layer** — attached evidence for every auto-suggestion (matched fields, confidence band, override paths)
- **Transform provenance explorer** — dependency graph across import → transform → export
- **Desktop v1.0** — iteration round after the GBIF submission
- **Plugin platform overhaul** — three related workstreams: (a) a real plugin **marketplace** for discovering, installing, and updating community plugins, (b) **R-language plugin support** alongside the current Python plugins, and (c) an **in-app plugin creator** that walks users through scaffolding a new plugin without leaving the desktop app.
- **Niamoto MCP server** — expose Niamoto's capabilities (data analysis, entity registry, import/transform/export configuration, plugin scaffolding) through a Model Context Protocol server so an AI agent can configure a complete instance end-to-end: inspect the user's raw data, propose a project structure, wire imports and transforms, generate portals, and — when needed — create a dedicated plugin for that instance. Builds on the plugin platform overhaul above. Secondary benefit: MCP tool-use traces become a training and evaluation harness for the local SLMs explored in the GBIF track — structured agent traces feed fine-tuning, ground-truth configurations anchor benchmarks, and each tool doubles as a verifiable eval task. This makes the local-first intelligence direction self-reinforcing.
- **Hosted Niamoto (exploratory)** — optional dynamic deployment to serve the Niamoto API (and, if needed, the generated pages) online. Scenarios being considered: self-hosted multi-instance portals, optional hosting on `niamoto.org` for users who want it, publication of static sites to `niamoto.org` with sync back to the local instance, and a reproducible self-host setup for teams that prefer their own infrastructure. Large scope, exploratory — the desktop app and static publication remain the primary path.

## Not planned

These directions are not on the roadmap. Not hard "nevers", but not actively planned:

- **Native mobile app** — generated portals are responsive; no iOS/Android client planned.
- **Real-time multi-user collaboration** — outside the "one analyst, one instance" model.
- **Replacing DuckDB** — DuckDB remains the core engine.

## How to contribute

- Read [CONTRIBUTING.md](CONTRIBUTING.md).
- Open an issue or a discussion before large changes.
