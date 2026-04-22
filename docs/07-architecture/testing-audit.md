# Testing Audit

This report inventories the current automated test surface for the repository.

## Coverage Artifacts

- Python coverage: **stale** — coverage.xml only matches 16/30 tracked files in the current repository.
- Frontend coverage: **missing** — Vitest coverage summary was not found.

## Snapshot

- Python source files tracked: **201**
- Python test files tracked: **176**
- Frontend source files tracked: **416**
- Frontend test files tracked: **31**

## Python Domain Summary

| Area | Source files | Files with direct tests | Direct-test density | Coverage line rate |
|------|--------------|-------------------------|---------------------|--------------------|
| `cli/commands` | 11 | 10 | 90.9% | 40.2% |
| `cli/utils` | 3 | 3 | 100.0% | 40.0% |
| `common` | 12 | 8 | 66.7% | 72.6% |
| `common/utils` | 5 | 4 | 80.0% | 69.9% |
| `core` | 3 | 2 | 66.7% | n/a |
| `core/imports` | 26 | 15 | 57.7% | n/a |
| `core/plugins` | 10 | 8 | 80.0% | n/a |
| `core/plugins/deployers` | 7 | 2 | 28.6% | n/a |
| `core/plugins/loaders` | 10 | 6 | 60.0% | n/a |
| `core/plugins/transformers` | 36 | 23 | 63.9% | n/a |
| `core/plugins/widgets` | 17 | 17 | 100.0% | n/a |
| `core/services` | 6 | 5 | 83.3% | 36.2% |
| `core/utils` | 1 | 1 | 100.0% | n/a |
| `gui` | 4 | 3 | 75.0% | n/a |
| `gui/api/routers` | 25 | 23 | 92.0% | n/a |
| `gui/api/services` | 18 | 14 | 77.8% | n/a |
| `gui/api/utils` | 3 | 2 | 66.7% | n/a |
| `gui/help_content` | 1 | 0 | 0.0% | n/a |
| `root` | 3 | 1 | 33.3% | 34.4% |

## Highest-ROI Python Gaps

- `src/niamoto/core/plugins/deployers/cloudflare.py` (300 lines, area `core/plugins/deployers`, related tests: none)
- `src/niamoto/gui/api/routers/layers.py` (294 lines, area `gui/api/routers`, related tests: none)
- `src/niamoto/gui/api/routers/deploy.py` (270 lines, area `gui/api/routers`, related tests: none)
- `src/niamoto/core/plugins/deployers/vercel.py` (207 lines, area `core/plugins/deployers`, related tests: none)
- `src/niamoto/core/plugins/deployers/render.py` (202 lines, area `core/plugins/deployers`, related tests: none)
- `src/niamoto/core/plugins/deployers/netlify.py` (192 lines, area `core/plugins/deployers`, related tests: none)
- `src/niamoto/core/plugins/deployers/ssh.py` (123 lines, area `core/plugins/deployers`, related tests: none)
- `src/niamoto/core/imports/multi_field_detector.py` (681 lines, area `core/imports`, related tests: none)
- `src/niamoto/gui/api/services/templates/utils/entity_finder.py` (582 lines, area `gui/api/services`, related tests: none)
- `src/niamoto/gui/api/services/templates/utils/data_loader.py` (413 lines, area `gui/api/services`, related tests: none)

## Frontend Area Summary

| Area | Source files | Test files | Test-file density |
|------|--------------|------------|-------------------|
| `app` | 5 | 0 | 0.0% |
| `collections` | 21 | 3 | 14.3% |
| `components` | 139 | 4 | 2.9% |
| `dashboard` | 13 | 1 | 7.7% |
| `feedback` | 22 | 5 | 22.7% |
| `help` | 7 | 1 | 14.3% |
| `import` | 61 | 4 | 6.6% |
| `other` | 32 | 2 | 6.2% |
| `publish` | 10 | 2 | 20.0% |
| `shared` | 37 | 5 | 13.5% |
| `site` | 44 | 2 | 4.5% |
| `tools` | 19 | 1 | 5.3% |
| `welcome` | 6 | 1 | 16.7% |

## Highest-ROI Frontend Gaps

- `src/niamoto/gui/ui/src/features/import/hooks/useEnrichmentState.ts` (1249 lines, area `import`, sibling tests: none)
- `src/niamoto/gui/ui/src/features/site/hooks/useSiteBuilderState.ts` (909 lines, area `site`, sibling tests: none)
- `src/niamoto/gui/ui/src/hooks/useJobPolling.ts` (354 lines, area `other`, sibling tests: none)
- `src/niamoto/gui/ui/src/shared/hooks/site-config/siteConfigApi.ts` (302 lines, area `shared`, sibling tests: none)
- `src/niamoto/gui/ui/src/shared/hooks/site-config/types.ts` (266 lines, area `shared`, sibling tests: none)
- `src/niamoto/gui/ui/src/features/site/hooks/useUnifiedSiteTree.ts` (265 lines, area `site`, sibling tests: none)
- `src/niamoto/gui/ui/src/features/welcome/hooks/useWelcomeScreen.ts` (238 lines, area `welcome`, sibling tests: none)
- `src/niamoto/gui/ui/src/features/collections/hooks/useApiExportConfigs.ts` (209 lines, area `collections`, sibling tests: none)
- `src/niamoto/gui/ui/src/shared/hooks/useProjectSwitcher.ts` (205 lines, area `shared`, sibling tests: none)
- `src/niamoto/gui/ui/src/features/tools/hooks/useConfig.ts` (192 lines, area `tools`, sibling tests: none)

## Recommended First Pass

1. Add direct tests for backend deploy adapters, shared helpers, and uncovered GUI API routes.
2. Extend the import-suggestion suite into uncovered decision seams before refactoring heuristics.
3. Add Vitest coverage and first-pass tests for frontend hooks, API normalization helpers, and runtime-dependent state flows.
