# ROADMAP.md Implementation Plan

> **For Claude:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a public-facing `ROADMAP.md` at the root of the Niamoto repository that surfaces vision, recent deliveries, the GBIF Challenge 2026 milestone, and three temporal horizons.

**Architecture:** Single static Markdown document, written in English, with relative links to existing brainstorms, plans, specs, and the GBIF opportunity report. No automation, no translation, no refactor of other docs. Section structure locked by [docs/superpowers/specs/2026-04-20-roadmap-md-design.md](../specs/2026-04-20-roadmap-md-design.md).

**Tech Stack:** Plain GitHub-flavored Markdown.

**Note on TDD:** This plan produces a documentation file — there is no executable behavior to test. Instead of test-first cycles, each task includes an explicit **verification step** (link check, rendered preview, or structural diff) before commit.

---

## Chunk 1: Write and verify ROADMAP.md

### Task 1: Scaffold ROADMAP.md with all section headings

**Files:**
- Create: `ROADMAP.md`
- Reference: `docs/superpowers/specs/2026-04-20-roadmap-md-design.md`

- [ ] **Step 1: Create the file with only the top-level structure**

Write this exact skeleton to `ROADMAP.md` (empty body under each heading, we fill in next tasks):

```markdown
# Niamoto Roadmap

_Last updated: 2026-04-20 — reviewed at each minor release._

## Vision

## Recently shipped

## GBIF Ebbe Nielsen Challenge 2026 ⭐

## Now (April – June 2026)

## Soon (Summer 2026)

## Later (H2 2026 and beyond)

## Not planned

## How to contribute
```

- [ ] **Step 2: Verify the skeleton renders in GitHub-flavored Markdown**

Run locally: `glow ROADMAP.md` or open on GitHub preview.
Expected: 8 headings visible, no broken formatting.
Fallback if `glow` unavailable: `cat ROADMAP.md` and eyeball.

- [ ] **Step 3: Commit the skeleton**

```bash
git add ROADMAP.md
git commit -m "docs: scaffold root ROADMAP.md"
```

---

### Task 2: Fill Vision and Recently shipped sections

**Files:**
- Modify: `ROADMAP.md`

- [ ] **Step 1: Write the Vision section**

Under `## Vision`, add:

```markdown
Niamoto is a generic ecological data platform. It turns heterogeneous datasets into publishable web portals through a configurable **Import → Transform → Export** pipeline, running locally with no cloud dependency. The desktop app (Tauri) and the CLI share the same engine and the same plugins.
```

- [ ] **Step 2: Write the Recently shipped section (reverse chronological)**

Under `## Recently shipped`, add:

```markdown
Highlights from the last ~3 months:

- **macOS signing & notarization pipeline** (v0.15.5, April 2026)
- **In-app feedback system** ([plan](docs/plans/2026-04-04-feat-in-app-feedback-system-plan.md))
- **Rich multi-source enrichment**: GBIF, CoL, iNaturalist, BHL, GN TaxRef, Tropicos, spatial v1 ([specs](docs/superpowers/specs/))
- **Sources dashboard & mission control redesign** ([plan](docs/plans/2026-04-01-refactor-sources-dashboard-redesign-plan.md))
- **Transform & export parallelization** ([transform spec](docs/superpowers/specs/2026-03-27-transform-parallelization-design.md), [export spec](docs/superpowers/specs/2026-03-27-export-parallelization-design.md))
- **Frontend architecture refactor** to `src/app`, `src/features`, `src/shared` ([plan](docs/plans/2026-03-25-refactor-frontend-feature-architecture-plan.md))
- **Release automation** via the `niamoto-release` skill ([plan](docs/plans/2026-03-25-feat-niamoto-release-automation-skill-plan.md))
```

- [ ] **Step 3: Verify every link resolves**

For each link in the two sections, run:

```bash
while read -r f; do test -f "$f" && echo "OK  $f" || echo "MISSING $f"; done <<'EOF'
docs/plans/2026-04-04-feat-in-app-feedback-system-plan.md
docs/superpowers/specs/2026-03-27-transform-parallelization-design.md
docs/superpowers/specs/2026-03-27-export-parallelization-design.md
docs/plans/2026-04-01-refactor-sources-dashboard-redesign-plan.md
docs/plans/2026-03-25-refactor-frontend-feature-architecture-plan.md
docs/plans/2026-03-25-feat-niamoto-release-automation-skill-plan.md
EOF
```

Expected: every line prints `OK`. If `MISSING`, replace or remove the link before commit.

- [ ] **Step 4: Commit**

```bash
git add ROADMAP.md
git commit -m "docs: add vision and recently shipped to ROADMAP.md"
```

---

### Task 3: Fill the GBIF Challenge section

**Files:**
- Modify: `ROADMAP.md`

- [ ] **Step 1: Write the GBIF section**

Under `## GBIF Ebbe Nielsen Challenge 2026 ⭐`, add:

```markdown
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
```

- [ ] **Step 2: Verify GBIF links resolve**

```bash
while read -r f; do test -f "$f" && echo "OK  $f" || echo "MISSING $f"; done <<'EOF'
docs/plans/2026-04-09-feat-gbif-rich-enrichment-plan.md
docs/superpowers/specs/2026-04-09-gbif-rich-enrichment-design.md
docs/plans/2026-03-13-feat-gbif-registry-publication-plan.md
docs/plans/2026-03-13-feat-gbif-challenge-presentation-page-plan.md
docs/plans/2026-03-11-feat-gbif-ebbe-nielsen-challenge-2026-opportunity-report.md
docs/08-roadmaps/gbif-challenge-2026.html
EOF
```

Expected: every line prints `OK`.

- [ ] **Step 3: Commit**

```bash
git add ROADMAP.md
git commit -m "docs: add GBIF Challenge 2026 milestone to ROADMAP.md"
```

---

### Task 4: Fill the three horizon sections

**Files:**
- Modify: `ROADMAP.md`

- [ ] **Step 1: Write the "Now" section**

Under `## Now (April – June 2026)`, add:

```markdown
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
```

- [ ] **Step 2: Write the "Soon" section**

Under `## Soon (Summer 2026)`, add:

```markdown
Planned but not yet started.

- **Niamoto Doctor** — unified diagnostics (CLI + GUI) ([ideation](docs/ideation/2026-04-12-open-ideation.md))
- **Starter project templates** — `niamoto init --template` with real starter kits ([ideation](docs/ideation/2026-04-12-open-ideation.md))
- **Export contract pack** — JSON schema on the export side
- **ML model regeneration pipeline** ([spec](docs/superpowers/specs/2026-03-27-ml-model-regeneration-design.md))
- Transform parallelization phase 2
```

- [ ] **Step 3: Write the "Later" section**

Under `## Later (H2 2026 and beyond)`, add:

```markdown
Identified in ideation, not yet planned.

- **Example & fixture certification pipeline** — docs and fixtures as executable contracts
- **Suggestion explainability layer** — attached evidence for every auto-suggestion (matched fields, confidence band, override paths)
- **Transform provenance explorer** — dependency graph across import → transform → export
- **Desktop v1.0** — iteration round after the GBIF submission
```

- [ ] **Step 4: Verify horizon links resolve**

```bash
while read -r f; do test -f "$f" && echo "OK  $f" || echo "MISSING $f"; done <<'EOF'
docs/superpowers/specs/2026-04-08-desktop-update-harness-design.md
docs/plans/2026-04-19-001-refactor-desktop-size-audit-strategy-plan.md
docs/plans/2026-04-17-refactor-documentation-desktop-first-plan.md
docs/plans/2026-04-18-001-refactor-desktop-user-guide-plan.md
docs/plans/2026-04-18-002-feat-in-app-user-docs-plan.md
docs/plans/2026-04-18-003-feat-in-app-public-documentation-plan.md
docs/plans/2026-04-18-004-feat-about-team-partners-plan.md
docs/plans/2026-04-14-feat-landing-teaser-refonte-plan.md
docs/plans/2026-04-14-feat-landing-teaser-hybride-plan.md
docs/plans/2026-04-14-feat-landing-teaser-video-plan.md
docs/plans/2026-04-14-feat-niamoto-marketing-site-plan.md
docs/plans/2026-04-10-refactor-enrichment-tab-ux-redesign-plan.md
docs/plans/2026-04-12-refactor-ui-density-compaction-plan.md
docs/plans/2026-04-12-refactor-ui-rendering-smoothness-plan.md
docs/ideation/2026-04-12-open-ideation.md
docs/superpowers/specs/2026-03-27-ml-model-regeneration-design.md
EOF
```

Expected: every line prints `OK`.

- [ ] **Step 5: Commit**

```bash
git add ROADMAP.md
git commit -m "docs: add Now/Soon/Later horizons to ROADMAP.md"
```

---

### Task 5: Fill "Not planned" and "How to contribute"

**Files:**
- Modify: `ROADMAP.md`

- [ ] **Step 1: Write the Not planned section**

Under `## Not planned`, add:

```markdown
These directions are not on the roadmap. Not hard "nevers", but not actively planned:

- **Multi-tenant cloud hosting** — Niamoto stays local-first; the desktop app is the primary distribution channel.
- **Native mobile app** — generated portals are responsive; no iOS/Android client planned.
- **Real-time multi-user collaboration** — outside the "one analyst, one instance" model.
- **Replacing DuckDB** — DuckDB remains the core engine.
```

- [ ] **Step 2: Write the How to contribute section**

Under `## How to contribute`, add:

```markdown
- Read [CONTRIBUTING.md](CONTRIBUTING.md).
- Browse ongoing design work in [docs/brainstorms/](docs/brainstorms/), [docs/plans/](docs/plans/), [docs/superpowers/specs/](docs/superpowers/specs/), and open ideation in [docs/ideation/](docs/ideation/).
- Open an issue or a discussion before large changes.
```

- [ ] **Step 3: Verify the final file**

Run:

```bash
wc -l ROADMAP.md
```

Expected: ~120–170 lines (target ~150).

```bash
grep -c '^## ' ROADMAP.md
```

Expected: `8` (Vision, Recently shipped, GBIF, Now, Soon, Later, Not planned, How to contribute).

- [ ] **Step 4: Visually inspect the rendered output**

Open `ROADMAP.md` in a Markdown preview (VS Code preview, GitHub preview, or `glow`).

Checklist:
- [ ] All 8 top-level headings present
- [ ] GBIF block visually emphasized (⭐ in heading)
- [ ] No broken link indicators (`[text](missing)` paths)
- [ ] "Last updated" date at the top reads `2026-04-20`

- [ ] **Step 5: Commit**

```bash
git add ROADMAP.md
git commit -m "docs: add not-planned and contribute sections to ROADMAP.md"
```

---

### Task 6: Cross-reference from README.md

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Locate an appropriate section in `README.md` for the link**

Read `README.md` and identify the "documentation" or "getting started" area where a roadmap pointer fits naturally.

- [ ] **Step 2: Add a single-line link to the roadmap**

Insert, in the most relevant section (likely near "Documentation" or near the top-of-file badges):

```markdown
- 📍 **Roadmap:** see [ROADMAP.md](ROADMAP.md) for vision, current priorities, and the GBIF Challenge 2026 milestone.
```

If the README style avoids emojis in that section, omit the `📍`.

- [ ] **Step 3: Verify the README still renders cleanly**

```bash
glow README.md | head -60
```

Or open GitHub preview. Expected: the new line is visible and not inside a code block.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: link ROADMAP.md from README"
```

---

## Completion criteria

- [ ] `ROADMAP.md` exists at repo root
- [ ] All eight sections populated
- [ ] Every relative link resolves to an existing file
- [ ] `README.md` points to `ROADMAP.md`
- [ ] Six commits on the branch, each scoped to one logical change
