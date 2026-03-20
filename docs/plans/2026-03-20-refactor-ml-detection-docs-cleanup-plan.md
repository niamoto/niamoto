---
title: Reorganize and translate ML detection documentation
type: refactor
date: 2026-03-20
---

# Reorganize and translate ML detection documentation

## Overview

The `docs/03-ml-detection/` directory contains 17 files mixing obsolete content (December 2024, Random Forest era) with current documentation (March 2026, 3-branch pipeline). Most files are in French and need translation to English. The `experiments/` subdirectory remains untouched.

## Problem Statement

- **9 files describe a system that no longer exists** (Random Forest, 14 types, 500 synthetic examples) — the current system uses TF-IDF + HistGradientBoosting + Fusion with 61 concepts and 2492 real columns
- **All active documentation is in French** — project convention requires English docs
- **README.md index is stale** — doesn't reference recent files, still links to archived content
- **3 external files** have links to soon-to-be-archived files, creating immediate 404s
- **Absolute machine paths** in `branch-architecture.md` are unusable for other contributors

## Proposed Solution

Archive obsolete files, translate active docs to English, fix cross-references, and update the README index. Execute in dependency order to avoid broken intermediate states.

## Technical Considerations

- **File moves via `git mv`** to preserve history
- **Translation in-place** (same filenames) to avoid breaking existing bookmarks
- **Code block comments** translated for consistency
- **Absolute paths** (`/Users/julienbarbe/...`) converted to repo-relative paths during translation
- **Scores in `overview.md`** updated to match latest values from `2026-03-19-ml-integration-status.md`

## Implementation Steps

### Step 1: Archive obsolete files

Create `docs/03-ml-detection/archive/` and move 9 files via `git mv`:

| File | Reason |
|------|--------|
| `current-state.md` | Describes Dec 2024 Random Forest system |
| `roadmap.md` | 8-week plan from Dec 2024, targets surpassed |
| `implementation.md` | Code for `EcologicalColumnDetector` (no longer exists) |
| `training-guide.md` | Pipeline with scripts that have been replaced |
| `detector-usage.md` | References `MLColumnDetector` + hardcoded absolute paths |
| `synthetic-data.md` | Hardcoded NC species, violates genericity rule |
| `auto-config-roadmap.md` | 7-week plan from Dec 2024, superseded |
| `auto-configuration-detection.md` | Speculative approaches not adopted |
| `auto-configuration-realiste.md` | Speculative approaches not adopted |

Create `archive/README.md`:

```markdown
# Archive — ML Detection Documentation

Archived on 2026-03-20. These files describe the initial ML detection system
(December 2024, Random Forest era) which has been replaced by the 3-branch
hybrid pipeline (header + values + fusion).

Content preserved in git history. See `../branch-architecture.md` for current architecture.
```

### Step 2: Merge academic content from semantic-detection.md

Extract the comparison table (Sherlock, Sato, Pythagoras, GAIT, GitTables) from `semantic-detection.md` and add it as a "Related Work" or "Academic References" section in `overview.md`.

**Scope**: Only the comparison matrix (~12 lines). The implementation proposals (AdvancedFeatureExtractor, EcologicalGNN, etc.) are speculative and incompatible with current architecture — do NOT merge those.

Then `git mv semantic-detection.md archive/`.

### Step 3: Move next-session-handoff.md to experiments/

`git mv next-session-handoff.md experiments/2026-03-19-next-session-handoff.md`

This is a session artifact, not permanent documentation. Its runner state has been committed since (commit `066b01e`).

### Step 4: Delete obsolete roadmap outside perimeter

```bash
git rm docs/10-roadmaps/ml-column-detection-evaluation.md
```

November 2024 document, completely superseded. No external references found.

### Step 5: Translate 6 active files to English

Translate in-place (same filenames). During translation, also:

| File | Extra fixes |
|------|------------|
| `overview.md` | Update scores to latest values (ProductScore 80.04, NiamotoOfflineScore 78.6). Add academic references section from Step 2 |
| `branch-architecture.md` | Convert all absolute paths (`/Users/julienbarbe/...`) to repo-relative paths (`src/niamoto/...`) |
| `2026-03-19-ml-integration-status.md` | Translate as-is, no structural changes |
| `autoresearch-surrogate-loop.md` | Translate as-is |
| `acquisition-plan.md` | Translate as-is |
| `candidate-data-sources.md` | Translate as-is |

**Code blocks**: translate inline French comments for consistency.

### Step 6: Rewrite README.md

Complete rewrite of `docs/03-ml-detection/README.md` reflecting the cleaned structure:

```
docs/03-ml-detection/
  README.md                              # Index
  overview.md                            # What, why, how — user-facing
  branch-architecture.md                 # Technical architecture reference
  2026-03-19-ml-integration-status.md    # Current integration state & decisions
  autoresearch-surrogate-loop.md         # Autoresearch loop design
  acquisition-plan.md                    # Data acquisition plan & tracking
  candidate-data-sources.md              # Source selection rationale
  experiments/                           # Session logs & evaluation results
  archive/                               # Obsolete docs (Dec 2024 era)
```

### Step 7: Fix external broken links

**`docs/README.md`** (2 fixes):
- Line 48: `03-ml-detection/training-guide.md` → `03-ml-detection/overview.md`
- Line 74: `03-ml-detection/auto-config-roadmap.md` → `03-ml-detection/branch-architecture.md`

**`docs/08-configuration/README.md`** (1 fix):
- Line 10: `../03-ml-detection/auto-config-roadmap.md` → `../03-ml-detection/branch-architecture.md`
- Line 65: link to `../03-ml-detection/README.md` — still valid, no change

**`docs/07-tutorials/ml-training-example.md`** (rewrite):
- Line 6: `../03-ml-detection/training-guide.md` → `../03-ml-detection/overview.md`
- Line 7: `../03-ml-detection/auto-config-roadmap.md` → `../03-ml-detection/branch-architecture.md`

## Acceptance Criteria

- [x] 9 obsolete files moved to `docs/03-ml-detection/archive/` with `archive/README.md`
- [x] `semantic-detection.md` academic table merged into `overview.md`, then archived
- [x] `next-session-handoff.md` moved to `experiments/` with date prefix
- [x] `docs/10-roadmaps/ml-column-detection-evaluation.md` deleted
- [x] 6 files translated to English (overview, branch-architecture, integration-status, autoresearch, acquisition-plan, candidate-data-sources)
- [x] Absolute paths in `branch-architecture.md` converted to repo-relative
- [x] Scores in `overview.md` updated to latest values
- [x] `docs/03-ml-detection/README.md` rewritten as clean index
- [x] 3 external files updated with corrected links
- [x] `experiments/` directory content unchanged
- [x] All links in README verified working

## Dependencies & Risks

**Dependencies:**
- Steps 1-4 must complete before Step 6 (README rewrite needs final file list)
- Step 2 must complete before Step 5 (overview.md translation includes merged content)
- Steps 1-4 are independent and can run in parallel

**Risks:**
- **Translation quality**: ML/ecological terminology must remain precise. Domain terms (e.g., `dbh`, `taxon`, `concept`) stay as-is.
- **Score drift**: Values hardcoded in translated `overview.md` will become stale. Mitigate by referencing the experiment log for latest numbers.
- **Second-pass dependency**: User plans a second pass on archived files to extract valuable content. Archive must be cleanly organized for this.

## References

### Active files (post-cleanup)
- `docs/03-ml-detection/overview.md` — user-facing documentation
- `docs/03-ml-detection/branch-architecture.md` — architecture reference
- `docs/03-ml-detection/2026-03-19-ml-integration-status.md` — integration state
- `docs/03-ml-detection/autoresearch-surrogate-loop.md` — autoresearch design
- `docs/03-ml-detection/acquisition-plan.md` — data acquisition tracking
- `docs/03-ml-detection/candidate-data-sources.md` — source rationale

### External files to fix
- `docs/README.md:48,74`
- `docs/08-configuration/README.md:10`
- `docs/07-tutorials/ml-training-example.md:6-7`
